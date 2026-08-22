"""MudLab .mud project files, compatible with the old app's format.

A .mud file is a deflated ZIP:
- 'content': {"type": "Project", "properties": {...}} where multi-part
  properties hold "file://<entry>" placeholders,
- 'version': a JSON string,
- 'specimens', 'phases', 'atom_types', 'mixtures': the referenced parts.

Loading maps the modeled subset onto the Qt models and keeps everything
else verbatim (raw passthrough on the models), so saving a project that
was created by the old app does NOT lose the parts MudLab2 does not model
yet (phases, mixtures, atom types, goniometers, markers, exclusion
ranges, line properties, uuids).
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
import zipfile

import numpy as np

from mudlab.models import (
    AtomType, Composition, Goniometer, Marker, Mixture, NonClayPhase, Phase,
    Project, RawPatternPhase, Specimen,
)

# Version tag written for new files (old-app format version we are
# compatible with); round-trips preserve the loaded tag.
DEFAULT_FILE_VERSION = "0.1.10"

MULTI_PARTS = ("specimens", "phases", "atom_types", "mixtures")

# Scalar properties shared 1:1 between the file and the Qt models.
PROJECT_PROPS = (
    "name", "author", "date", "description", "layout_mode",
    "display_exp_color", "display_calc_color",
    "display_exp_lw", "display_calc_lw",
    "display_exp_ls", "display_calc_ls",
    "display_exp_marker", "display_calc_marker",
    "display_plot_offset", "display_group_by", "display_label_pos",
    "axes_xlimit", "axes_xmin", "axes_xmax", "axes_xstretch",
    "axes_ylimit", "axes_ymin", "axes_ymax", "axes_yvisible",
    "axes_ynormalize", "axes_dspacing",
    "display_marker_angle", "display_marker_top_offset",
    "display_marker_style", "display_marker_color",
    "display_marker_base", "display_marker_top", "display_marker_align",
)
SPECIMEN_PROPS = (
    "name", "sample_name", "source",
    "display_experimental", "display_calculated", "display_phases",
    "display_derivatives", "display_residuals", "display_stats_in_lbl",
    "display_vshift", "display_vscale", "display_residual_scale",
)


def _parse_pattern_data(data_string: str) -> tuple[np.ndarray, np.ndarray]:
    """Old pattern lines store their data as a JSON string of rows; the
    calculated line may carry extra per-phase columns - take the first two."""
    rows = json.loads(data_string) if data_string else []
    if len(rows) < 2:
        return np.empty(0), np.empty(0)
    array = np.asarray(rows, dtype=float)
    return array[:, 0], array[:, 1]


def _encode_pattern_data(x: np.ndarray, y: np.ndarray) -> str:
    pairs = [[float(xi), float(yi)] for xi, yi in zip(x, y)]
    return json.dumps(pairs, separators=(",", ":"))


def _parse_exclusion_ranges(value) -> list[tuple[float, float]]:
    """The .mud stores exclusion_ranges as a JSON string of [from, to] 2theta
    rows (old XYListStore serialisation); tolerate an already-decoded list."""
    if isinstance(value, str):
        rows = json.loads(value) if value else []
    elif isinstance(value, list):
        rows = value
    else:
        rows = []
    return [(float(r[0]), float(r[1])) for r in rows if len(r) >= 2]


def _encode_exclusion_ranges(ranges) -> str:
    return json.dumps(
        [[float(a), float(b)] for a, b in ranges], separators=(",", ":")
    )


# ----------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------
def resolve_phase_references(project: Project) -> None:
    """Resolve every phase cross-reference against the whole project: phase-level
    based_on inheritance, component links (linked_with), UCP derivation sources
    and atom relations. Idempotent - safe to call again after adding phases
    (e.g. a .phs import). Stored values are kept (golden-safe); only the object
    links are (re)bound."""
    # based_on: a treated phase (glycolated / heated) reads its parent's
    # treatment-independent params (crucially the stacking probabilities).
    phase_map = {p.uuid: p for p in project.phases}
    for phase in project.phases:
        phase.resolve_based_on(phase_map)

    # Component links + atom maps (linked components are shared clay layers).
    component_map = {}
    atom_map = {}
    for phase in project.phases:
        for comp in getattr(phase, "components", []):
            component_map[comp.uuid] = comp
            for atom in comp._layer_atoms + comp._interlayer_atoms:
                atom_map[atom.uuid] = atom
    for phase in project.phases:
        for comp in getattr(phase, "components", []):
            comp.resolve_link(component_map)
    # UCP sources + atom relations. Resolve against THIS component's OWN atoms
    # first, then the project-wide map (linked components share atom uuids, so
    # the global last-loaded-wins map can otherwise bind the wrong copy).
    object_map = {**component_map, **atom_map}
    for phase in project.phases:
        for comp in getattr(phase, "components", []):
            own = {a.uuid: a for a in comp._layer_atoms + comp._interlayer_atoms}
            comp.resolve_ucp_props({**object_map, **own})
            comp.resolve_relations({**atom_map, **own})


def load_mud(path: str) -> Project:
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        if "content" not in names:
            raise ValueError(f"{path!r} is not a MudLab project file")
        content = json.loads(archive.read("content").decode("utf-8"))
        properties = dict(content.get("properties", {}))
        for name in names:
            if name not in ("content", "version"):
                properties[name] = json.loads(archive.read(name).decode("utf-8"))
        version = (
            json.loads(archive.read("version").decode("utf-8"))
            if "version" in names else None
        )

    project = Project()
    project.raw_properties = properties
    project.file_version = version
    project.filename = path
    for prop in PROJECT_PROPS:
        if prop in properties:
            setattr(project, prop, properties[prop])

    for atom_dict in properties.get("atom_types") or []:
        if isinstance(atom_dict, dict):
            project.add_atom_type(AtomType.from_dict(atom_dict))

    # Phases are calc models (atoms resolve against the atom-type uuid map, so
    # load them after the atom types). A regular "Phase" is computed from its
    # structure; a "RawPatternPhase" carries a stored measured curve (its data
    # is embedded in the archive, so no instrument-format parser is needed).
    # Any other phase type is still kept verbatim (unmodeled).
    atom_type_map = project.atom_type_uuid_map()
    for phase_dict in properties.get("phases") or []:
        if not isinstance(phase_dict, dict):
            continue
        if phase_dict.get("type") == "Phase":
            project.add_phase(Phase.from_dict(phase_dict, atom_type_map))
        elif phase_dict.get("type") == "RawPatternPhase":
            project.add_phase(RawPatternPhase.from_dict(phase_dict))
        elif phase_dict.get("type") == "NonClayPhase":
            project.add_phase(NonClayPhase.from_dict(phase_dict))

    # Resolve every phase cross-reference now that all phases exist (based_on,
    # component links, UCP sources, atom relations). Factored out so .phs phase
    # import can reuse the exact same resolution.
    resolve_phase_references(project)

    for spec_dict in properties.get("specimens") or []:
        spec_props = spec_dict.get("properties", {})
        specimen = Specimen()
        specimen.raw_properties = spec_props
        if "uuid" in spec_props:
            specimen.uuid = spec_props["uuid"]
        for prop in SPECIMEN_PROPS:
            if prop in spec_props:
                setattr(specimen, prop, spec_props[prop])
        gonio_dict = spec_props.get("goniometer")
        if isinstance(gonio_dict, dict):
            specimen.goniometer = Goniometer.from_dict(gonio_dict)
        specimen._exclusion_ranges = _parse_exclusion_ranges(
            spec_props.get("exclusion_ranges")
        )
        for key, setter in (
            ("experimental_pattern", specimen.set_experimental_pattern),
            ("calculated_pattern", specimen.set_calculated_pattern),
        ):
            line = spec_props.get(key)
            if isinstance(line, dict):
                data = line.get("properties", {}).get("data", "")
                x, y = _parse_pattern_data(data)
                if x.size:
                    setter(x, y)
        project.add_specimen(specimen)
        # Markers are now modeled; add them after the specimen has a project
        # so inheritance resolves.
        for marker_dict in spec_props.get("markers") or []:
            if isinstance(marker_dict, dict):
                specimen.add_marker(Marker.from_dict(marker_dict))

    # The optional measured (XRF) composition. Absent from every project written
    # before this feature, and from any project the user never imported one
    # into - so its absence is the normal case, not an error.
    comp_dict = properties.get("composition")
    if isinstance(comp_dict, dict):
        project.set_composition(Composition.from_dict(comp_dict))

    # Which default phase each phase started as - user-stated, so it can only
    # be read back, never recomputed. Set AFTER the phases exist, since unknown
    # uuids are pruned against them.
    # Imported reference ("custom default") phases. Resolved against the
    # project's atom types AND the built-in library by NAME, because these
    # phases came from a .phs whose atom-type uuids are foreign - the name is
    # the stable reference (see Atom.from_dict) - and because a reference phase
    # must not have to pollute the project's atom-type list to be readable.
    custom = properties.get("custom_default_phases")
    if isinstance(custom, list) and custom:
        from mudlab.file_parsers.atom_type_library import atom_type_library_map

        resolve_map = {**atom_type_library_map(), **project.atom_type_uuid_map()}
        for phase_dict in custom:
            if isinstance(phase_dict, dict):
                project.add_custom_default_phase(
                    Phase.from_dict(phase_dict, resolve_map))

    mapping = properties.get("default_phase_map")
    if isinstance(mapping, dict):
        project.set_default_phase_map(mapping)

    # Mixtures resolve their phase-slot grid and specimen rows by uuid, so
    # load them last (calc models; still saved verbatim via raw passthrough).
    phase_map = project.phase_uuid_map()
    specimen_map = project.specimen_uuid_map()
    for mixture_dict in properties.get("mixtures") or []:
        if isinstance(mixture_dict, dict):
            project.add_mixture(
                Mixture.from_dict(mixture_dict, phase_map, specimen_map)
            )

    return project


# ----------------------------------------------------------------------
# Saving
# ----------------------------------------------------------------------
def save_mud(project: Project, path: str) -> None:
    properties = dict(getattr(project, "raw_properties", None) or {})
    for prop in PROJECT_PROPS:
        properties[prop] = getattr(project, prop)
    properties.setdefault("uuid", uuid.uuid4().hex)
    properties["specimens"] = [
        _specimen_to_dict(specimen) for specimen in project.specimens
    ]
    # Atom types and mixtures are modeled: write the live lists back.
    properties["atom_types"] = [at.to_dict() for at in project.atom_types]
    if project.mixtures:
        properties["mixtures"] = [mix.to_dict() for mix in project.mixtures]
    # Phases: "Phase" and "RawPatternPhase" entries are modeled, so the raw
    # list is walked to write the modeled ones from their live models while
    # keeping any other (still-unmodeled) type verbatim and in place.
    #
    # The live list is authoritative for which modeled phases exist:
    #   - a modeled entry with no live model was REMOVED -> drop it.
    #     (Every "Phase"/"RawPatternPhase" entry is modeled on load, so a
    #     missing model can only mean removal - not an unmodeled type.)
    #   - a live phase with no raw entry was ADDED -> append it.
    # Without both halves, Project.add_phase / remove_phase would appear to
    # work in-session and silently revert on reload.
    _MODELED = ("Phase", "RawPatternPhase", "NonClayPhase")
    model_by_uuid = {p.uuid: p for p in project.phases}
    seen_uuids = set()
    rebuilt = []
    for entry in properties.get("phases") or []:
        if isinstance(entry, dict) and entry.get("type") in _MODELED:
            uid = entry.get("properties", {}).get("uuid")
            model = model_by_uuid.get(uid)
            if model is None:
                continue  # removed from the project
            seen_uuids.add(uid)
            rebuilt.append(model.to_dict())
            continue
        rebuilt.append(entry)  # unmodeled type: keep verbatim
    for phase in project.phases:
        if phase.uuid not in seen_uuids:
            rebuilt.append(phase.to_dict())  # newly added
    properties["phases"] = rebuilt
    # The measured composition, when there is one. When there is NOT, the key is
    # REMOVED rather than written as null: a project that never had one must
    # round-trip exactly as it did before this feature, and clearing one must
    # not leave a tombstone behind.
    composition = getattr(project, "composition", None)
    if composition is not None:
        properties["composition"] = composition.to_dict()
    else:
        properties.pop("composition", None)
    # Same rule for the default-phase map: written only when the user has stated
    # one, removed when they have not, so a project that never uses the feature
    # is byte-identical to how it was before it existed.
    mapping = getattr(project, "default_phase_map", None) or {}
    if mapping:
        properties["default_phase_map"] = dict(mapping)
    else:
        properties.pop("default_phase_map", None)
    # ...and the imported reference phases they may point at, so the comparison
    # keeps working when the project is reopened (or opened elsewhere) without
    # the original .phs files being present.
    custom = getattr(project, "custom_default_phases", None) or ()
    if custom:
        properties["custom_default_phases"] = [ph.to_dict() for ph in custom]
    else:
        properties.pop("custom_default_phases", None)
    for part in MULTI_PARTS:
        properties.setdefault(part, [])

    content_props = {
        key: (f"file://{key}" if key in MULTI_PARTS else value)
        for key, value in properties.items()
    }
    content = {"type": "Project", "properties": content_props}
    version = getattr(project, "file_version", None) or DEFAULT_FILE_VERSION

    # Safe write, like the old app: temp file first, existing file
    # becomes a '~' backup.
    temp_path = path + ".tmp"
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("content", json.dumps(content, separators=(",", ":")))
            archive.writestr("version", json.dumps(version))
            for part in MULTI_PARTS:
                archive.writestr(
                    part, json.dumps(properties[part], separators=(",", ":"))
                )
    except BaseException:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    if os.path.exists(path):
        shutil.move(path, path + "~")
    shutil.move(temp_path, path)

    project.raw_properties = properties
    project.filename = path


def _specimen_to_dict(specimen: Specimen) -> dict:
    props = dict(getattr(specimen, "raw_properties", None) or {})
    for prop in SPECIMEN_PROPS:
        props[prop] = getattr(specimen, prop)
    props.setdefault("uuid", uuid.uuid4().hex)
    # Markers are modeled: write the live list back.
    props["markers"] = [marker.to_dict() for marker in specimen.markers]
    # Goniometer is modeled: write it back (wavelength_distribution string
    # is preserved verbatim, so round-trips stay byte-identical).
    if specimen.goniometer is not None:
        props["goniometer"] = specimen.goniometer.to_dict()
    # Exclusion ranges are modeled: write the live list back (JSON string).
    props["exclusion_ranges"] = _encode_exclusion_ranges(specimen.exclusion_ranges)

    # Experimental pattern: update the data inside the (possibly raw) line
    # object so unmodeled line properties (color, lw, inherits, z_data)
    # survive the round-trip.
    exp = props.get("experimental_pattern")
    if not isinstance(exp, dict):
        exp = {
            "type": "ExperimentalLine",
            "properties": {"label": "Experimental Profile", "uuid": uuid.uuid4().hex},
        }
    exp_props = dict(exp.get("properties", {}))
    x, y = specimen.experimental_pattern
    exp_props["data"] = _encode_pattern_data(x, y)
    props["experimental_pattern"] = {
        "type": exp.get("type", "ExperimentalLine"),
        "properties": exp_props,
    }

    # Calculated pattern: kept VERBATIM when the .mud carried one, because its
    # rows may hold extra per-phase intensity columns that the Specimen model
    # does not keep (_parse_pattern_data takes the first two). Re-encoding it
    # from the model would drop the per-phase curves.
    # This means an operation that changes the calculated pattern must clip the
    # raw rows itself, or the change is lost on save: Specimen.trim does
    # (_trim_raw_calculated). It is the only such operation - the line ops all
    # touch the experimental pattern only. Add one and it must do the same.
    if not isinstance(props.get("calculated_pattern"), dict) and specimen.has_calculated_data:
        cx, cy = specimen.calculated_pattern
        props["calculated_pattern"] = {
            "type": "CalculatedLine",
            "properties": {
                "label": "Calculated Profile",
                "uuid": uuid.uuid4().hex,
                "data": _encode_pattern_data(cx, cy),
            },
        }

    return {"type": "Specimen", "properties": props}
