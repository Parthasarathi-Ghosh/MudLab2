"""Export a MudLab2 project to the OLD GTK MudLab's `.mud`, or to PyXRD's
`.pyxrd`.

Why these exist
---------------
MudLab2's own `.mud` is the old app's format plus a few MudLab2-only additions.
The old app deserialises with `cls(**properties)` and raises `TypeError` on ANY
unknown key, so those additions - `composition`, `default_phase_map`,
`custom_default_phases` - make a MudLab2 file unreadable there, and the
MudLab2-only `NonClayPhase` TYPE fails with `KeyError` outright. Exporting
strips them on the way out, which is what lets MudLab2 store whatever it needs
natively.

Two separate writers, not one conditional one: the two targets diverge in
different directions, and a shared writer would hide that.

What is measured, and what is not
---------------------------------
* **The old-app exporter is verified against the old app itself** - the export
  is loaded under `C:\\GitHub\\MudLab\\data\\bin\\python.exe` by
  `tools/verify_exporters.py` when that interpreter is present.
* **The PyXRD exporter is verified STRUCTURALLY**, against a corpus of 12 real
  `.pyxrd` files: every type and key it writes must appear in real PyXRD files.
  PyXRD itself is not installed here and has never been run against the output.
  Treat it as best-effort.

The PyXRD schema divergence (measured across those 12 files)
------------------------------------------------------------
This is NOT just a matter of extra keys. Old MudLab restructured PyXRD's model:

* `sample_length` and `absorption` live on the **Specimen** in PyXRD; MudLab
  moved them onto the **Goniometer**.
* PyXRD's goniometer carries `wavelength` plus an automatic-divergence-slit
  group (`has_ads`, `ads_const`, `ads_fact`, `ads_phase_fact`,
  `ads_phase_shift`); MudLab replaced these with `divergence_mode`, a
  `wavelength_distribution`, an absorption-correction group, soller toggles and
  `mcr_2theta`.
* PyXRD's mixture has `refine_method`; MudLab has `refine_method_index`.

Quantities that do NOT survive the trip are listed per export in
`ExportReport.notes`, and the UI shows them - a lossy export that says nothing
is worse than one that refuses.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import zipfile

from mudlab.file_parsers.mud_project import (
    DEFAULT_FILE_VERSION, MULTI_PARTS, build_project_properties,
)

# ---------------------------------------------------------------------------
# What each target cannot take
# ---------------------------------------------------------------------------

#: Project-level keys MudLab2 added. Neither target knows them.
MUDLAB2_PROJECT_KEYS = ("composition", "default_phase_map",
                        "custom_default_phases")

#: MudLab2-only phase type. Exported as the RawPatternPhase it is built on, so
#: its pattern still contributes and the mixture cells that name it still
#: resolve - dropping it would leave dangling uuids in the mixture grid.
NONCLAY_TYPE = "NonClayPhase"

#: Keys `NonClayPhase` adds on top of `RawPatternPhase`.
NONCLAY_EXTRA_KEYS = ("oxides", "reflections", "fwhm", "caglioti", "bulk",
                      "formula", "source_file")

#: Per-type keys that appear in NO real PyXRD file (measured over 12 of them).
PYXRD_STRIP = {
    "Goniometer": ("absorption", "divergence_mode", "has_absorption_correction",
                   "has_soller1", "has_soller2", "mcr_2theta", "sample_length",
                   "sample_surf_density", "wavelength_distribution"),
    # NB refine_options is NOT here: real PyXRD files carry it, in the very
    # same shape (a dict keyed by method index). It is cleaned instead - see
    # _pyxrd_mixture. An earlier version stripped it on the assumption that it
    # was a MudLab addition; measuring the corpus said otherwise.
    "Mixture": ("auto_scales", "fractions_mask", "refine_method_index"),
    "Specimen": ("source",),
    "Component": ("lattice_d", "linked_with"),
    "Atom": ("stretch_z",),
    "CalculatedLine": ("z_data",),
    "ExperimentalLine": ("z_data",),
}

#: PyXRD's automatic-divergence-slit group. MudLab has only the on/off state
#: (`divergence_mode`), so the shape parameters take PyXRD's own defaults.
PYXRD_ADS_DEFAULTS = {"ads_const": 0.0, "ads_fact": 1.0,
                      "ads_phase_fact": 1.0, "ads_phase_shift": 0.0}

#: PyXRD Specimen fields MudLab keeps on the goniometer instead.
PYXRD_SPECIMEN_DEFAULT_ABSORPTION = 0.9


class ExportReport:
    """What an export changed on the way out.

    Carried back to the caller so the UI can say what was lost. An export that
    silently drops the user's measured composition is not a kindness.
    """

    def __init__(self, target: str) -> None:
        self.target = target
        self.notes: list[str] = []

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)

    def __bool__(self) -> bool:
        return bool(self.notes)


# ---------------------------------------------------------------------------
# Shared plumbing
# ---------------------------------------------------------------------------

def _walk_objects(node, visit) -> None:
    """Call `visit(type, properties)` for every serialised object in `node`."""
    if isinstance(node, dict):
        kind = node.get("type")
        props = node.get("properties")
        if kind and isinstance(props, dict):
            visit(node, props)
            for value in list(props.values()):
                _walk_objects(value, visit)
        else:
            for value in node.values():
                _walk_objects(value, visit)
    elif isinstance(node, list):
        for value in node:
            _walk_objects(value, visit)


def _write_archive(path: str, properties: dict, version: str | None) -> None:
    """Write the ZIP the way `save_mud` does - temp file, then a `~` backup of
    whatever was there - but WITHOUT touching the project: an export must not
    make the app think the project now lives at the exported path.

    `version=None` omits the entry entirely, which is what PyXRD needs: it has
    no `version` member, and the loader injects every archive entry as a Project
    property, so an unexpected one is fatal.
    """
    content_props = {
        key: (f"file://{key}" if key in MULTI_PARTS else value)
        for key, value in properties.items()
    }
    content = {"type": "Project", "properties": content_props}

    temp_path = path + ".tmp"
    try:
        with zipfile.ZipFile(temp_path, "w",
                             compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("content",
                             json.dumps(content, separators=(",", ":")))
            if version is not None:
                archive.writestr("version", json.dumps(version))
            for part in MULTI_PARTS:
                archive.writestr(
                    part, json.dumps(properties.get(part, []),
                                     separators=(",", ":")))
    except BaseException:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    if os.path.exists(path):
        shutil.move(path, path + "~")
    shutil.move(temp_path, path)


def _strip_project_keys(properties: dict, report: ExportReport) -> None:
    friendly = {
        "composition": "the measured (XRF) composition",
        "default_phase_map": "which default each phase started as",
        "custom_default_phases": "imported reference phases",
    }
    for key in MUDLAB2_PROJECT_KEYS:
        if properties.pop(key, None) is not None:
            report.note("Dropped %s - a MudLab2-only feature the target does "
                        "not know." % friendly[key])


def _demote_nonclay(properties: dict, report: ExportReport) -> None:
    """Rewrite `NonClayPhase` entries as the `RawPatternPhase` they extend.

    Both targets fail outright on the unknown type. The pattern and the phase's
    identity survive; only the oxide chemistry (and the computed-phase
    machinery) is lost, so the mixture still resolves the cells that name it.
    """
    for entry in properties.get("phases") or []:
        if isinstance(entry, dict) and entry.get("type") == NONCLAY_TYPE:
            entry["type"] = "RawPatternPhase"
            props = entry.get("properties") or {}
            for key in NONCLAY_EXTRA_KEYS:
                props.pop(key, None)
            report.note(
                "Non-clay phases were exported as plain measured-pattern "
                "phases: their oxide composition is not part of the target "
                "format. Their patterns and mixture positions are kept.")


# ---------------------------------------------------------------------------
# Old GTK MudLab
# ---------------------------------------------------------------------------

def export_old_mud(project, path: str) -> ExportReport:
    """Write `project` as a `.mud` the old GTK MudLab can open.

    Everything else about the format is already the old app's, so this is
    exactly: drop the MudLab2-only project keys, and demote `NonClayPhase`.
    """
    report = ExportReport("MudLab (old app)")
    properties = copy.deepcopy(build_project_properties(project))
    _strip_project_keys(properties, report)
    _demote_nonclay(properties, report)
    version = getattr(project, "file_version", None) or DEFAULT_FILE_VERSION
    _write_archive(path, properties, version)
    return report


# ---------------------------------------------------------------------------
# PyXRD
# ---------------------------------------------------------------------------

#: MudLab's refinement-method index -> PyXRD's. MudLab kept only two methods
#: and renumbered them (0 = L-BFGS-B, 1 = Basin Hopping); PyXRD's numbering is
#: the original 0..6, where Basin Hopping is 4. MudLab's own `refine_options`
#: dict is still keyed by the ORIGINAL numbering, which is how this was
#: confirmed: its "4" entry holds niter/T/stepsize, i.e. scipy basinhopping.
PYXRD_METHOD_BY_INDEX = {0: 0, 1: 4}

#: Per-method option keys MudLab added inside `refine_options`.
MUDLAB_OPTION_KEYS = ("inner_maxfun", "inner_maxiter")


def _pyxrd_mixture(props: dict, report: ExportReport) -> None:
    """Translate a mixture's refinement settings into PyXRD's spelling."""
    if "refine_method_index" in props:
        index = props.get("refine_method_index")
        mapped = PYXRD_METHOD_BY_INDEX.get(index)
        if mapped is None:
            report.note("Refinement method %r has no PyXRD equivalent; PyXRD's "
                        "default was written." % (index,))
        else:
            props["refine_method"] = mapped
    options = props.get("refine_options")
    if isinstance(options, dict):
        cleaned = {}
        dropped = False
        for key, value in options.items():
            if isinstance(value, dict):
                trimmed = {k: v for k, v in value.items()
                           if k not in MUDLAB_OPTION_KEYS}
                dropped = dropped or len(trimmed) != len(value)
                cleaned[key] = trimmed
            else:
                cleaned[key] = value
        props["refine_options"] = cleaned
        if dropped:
            report.note("MudLab's inner-iteration refinement limits were "
                        "removed from the saved options; PyXRD has no such "
                        "setting. The rest of the options are kept.")


def _pyxrd_goniometer(props: dict, report: ExportReport) -> dict:
    """MudLab's goniometer -> PyXRD's, returning the Specimen fields PyXRD
    keeps on the specimen instead."""
    moved = {
        "sample_length": props.get("sample_length", 1.25),
        # MudLab's absorption is a different quantity from PyXRD's (mass
        # absorption vs the 0-1 factor PyXRD stores), so it is NOT converted -
        # PyXRD's own default goes out and the difference is reported.
        "absorption": PYXRD_SPECIMEN_DEFAULT_ABSORPTION,
    }
    if props.get("has_absorption_correction"):
        report.note(
            "Absorption correction is not carried over: PyXRD stores a "
            "different quantity, so its default was written instead.")
    if props.get("wavelength_distribution"):
        report.note(
            "The emission spectrum was reduced to PyXRD's single `wavelength` "
            "(the strongest line) - PyXRD has no wavelength distribution.")
    if not (props.get("has_soller1", True) and props.get("has_soller2", True)):
        report.note(
            "PyXRD has no soller on/off switches, so the soller values were "
            "written as they stand.")

    props["has_ads"] = str(props.get("divergence_mode", "FIXED")).upper() \
        == "AUTOMATIC"
    props.update(PYXRD_ADS_DEFAULTS)
    return moved


def export_pyxrd(project, path: str) -> ExportReport:
    """Write `project` as a `.pyxrd`.

    Best-effort: verified structurally against 12 real PyXRD files, never run
    through PyXRD itself. See the module docstring.
    """
    report = ExportReport("PyXRD")
    properties = copy.deepcopy(build_project_properties(project))
    _strip_project_keys(properties, report)
    _demote_nonclay(properties, report)

    # RawPatternPhase has no counterpart in the PyXRD corpus at all, so a
    # measured-pattern phase cannot be represented. Say so rather than write a
    # type PyXRD will fail on.
    raw_names = [
        (e.get("properties") or {}).get("name") or "(unnamed)"
        for e in (properties.get("phases") or [])
        if isinstance(e, dict) and e.get("type") == "RawPatternPhase"
    ]

    # Specimens first: PyXRD keeps `sample_length` and `absorption` on the
    # SPECIMEN, while MudLab moved them onto the goniometer, so the goniometer
    # mapping hands them back to their owning specimen.
    for specimen in properties.get("specimens") or []:
        if not isinstance(specimen, dict):
            continue
        sprops = specimen.get("properties") or {}
        gonio = sprops.get("goniometer")
        if isinstance(gonio, dict) and isinstance(gonio.get("properties"), dict):
            gprops = gonio["properties"]
            # PyXRD wants one wavelength where MudLab keeps a distribution.
            gprops["wavelength"] = _dominant_wavelength(gprops)
            sprops.update(_pyxrd_goniometer(gprops, report))

    for mixture in properties.get("mixtures") or []:
        if isinstance(mixture, dict) and isinstance(mixture.get("properties"), dict):
            _pyxrd_mixture(mixture["properties"], report)

    # Then drop, everywhere, the keys no real PyXRD file contains. This runs
    # AFTER the goniometer and mixture mappings, which read several of them.
    for part in MULTI_PARTS:
        _walk_objects(properties.get(part), _strip_only)

    if raw_names:
        report.note(
            "Measured-pattern phases (%s) have no PyXRD equivalent; PyXRD may "
            "refuse the file." % ", ".join(raw_names))
    report.note("PyXRD export is best-effort: it matches 12 real PyXRD files "
                "structurally, but has not been opened in PyXRD itself.")

    # PyXRD archives carry no `version` member.
    _write_archive(path, properties, None)
    return report


def _strip_only(node, props) -> None:
    for key in PYXRD_STRIP.get(node["type"], ()):
        props.pop(key, None)


def _dominant_wavelength(gonio_props: dict) -> float:
    """The strongest line of a MudLab wavelength distribution, in nm."""
    distribution = gonio_props.get("wavelength_distribution")
    pairs = []
    if isinstance(distribution, str):
        try:
            pairs = json.loads(distribution)
        except ValueError:
            pairs = []
    elif isinstance(distribution, list):
        pairs = distribution
    best = None
    for pair in pairs or ():
        try:
            wavelength, fraction = float(pair[0]), float(pair[1])
        except (TypeError, ValueError, IndexError):
            continue
        if best is None or fraction > best[1]:
            best = (wavelength, fraction)
    return best[0] if best else 0.154056


def suggested_name(project, extension: str) -> str:
    """A default file name for the save dialog."""
    base = (getattr(project, "name", "") or "").strip() or "project"
    for bad in '\\/:*?"<>|':
        base = base.replace(bad, "-")
    return "%s%s" % (base, extension)


__all__ = [
    "ExportReport", "export_old_mud", "export_pyxrd", "suggested_name",
]
