"""Phase file (*.phs) import / export.

A .phs is a ZIP whose members are ``<index>###<uuid>`` -> a Phase JSON dict (the
same serialisation a .mud uses for its `phases` entries). Multiple phases in one
file form a based_on family (a reference phase plus its glycolated / heated
treatment variants). Atoms reference atom types by NAME, so a .phs resolves
against whatever atom types the importing project already holds (MudLab2's
name-fallback), which is how the old app's default-phase library works.

Ported from old mudlab (AbstractPhase.save_phases + PhasesController.load_phases)
minus its ObjectPool: on export a phase whose based_on is not also exported is
written standalone (based_on dropped, inherit flags cleared); on import a phase
whose uuid collides with the project is given a fresh uuid (and any based_on
within the imported set is repointed), which is the clean equivalent of the old
app's re-uuid-on-collision.
"""

from __future__ import annotations

import json
import zipfile

from mudlab.file_parsers.mud_project import resolve_phase_references
from mudlab.file_parsers.uuid_remap import project_uuids, remap_uuids
from mudlab.models.phase import Phase
from mudlab.models.raw_pattern_phase import RawPatternPhase

# Qt getOpenFileName / getSaveFileName filter for phase files. Only .phs is
# offered - no "All files" option, since import reads nothing else and export
# always writes .phs.
PHS_FILTERS = "Phase files (*.phs)"

_INHERIT_FLAGS = (
    "inherit_sigma_star", "inherit_CSDS_distribution", "inherit_display_color",
)


def _member_index(name: str) -> int:
    head = name.split("###", 1)[0]
    try:
        return int(head)
    except ValueError:
        return 0


def _order_parents_first(phases: list) -> list:
    """Order so every phase comes after its based_on parent (parents must be
    written / loaded first). Stable, cycle-safe."""
    ordered: list = []
    in_set = set(id(p) for p in phases)
    seen: set = set()

    def visit(p):
        if id(p) in seen:
            return
        seen.add(id(p))
        parent = getattr(p, "based_on", None)
        if parent is not None and id(parent) in in_set:
            visit(parent)
        ordered.append(p)

    for p in phases:
        visit(p)
    return ordered


def _clear_inheritance(props: dict) -> None:
    """Make a phase dict standalone: drop based_on and every inherit flag (the
    phase then uses its own stored values)."""
    props["based_on_uuid"] = ""
    for flag in _INHERIT_FLAGS:
        if flag in props:
            props[flag] = False
    probs = props.get("probabilities")
    if isinstance(probs, dict):
        pprops = probs.get("properties")
        if isinstance(pprops, dict):
            for key in list(pprops):
                if key.startswith("inherit_"):
                    pprops[key] = False


def _make_portable(entry: dict, phase) -> None:
    """Stamp each atom's resolved atom_type NAME into the exported dict, so the
    .phs imports by name into any project (atom-type uuids are project-local -
    a name-based .phs is what the old app's default library uses). Mutates only
    the freshly built export dict, never the source model."""
    comps = entry.get("properties", {}).get("components")
    live = getattr(phase, "components", None)
    if not isinstance(comps, list) or live is None:
        return
    for cdict, cmodel in zip(comps, live):
        cprops = cdict.get("properties", {})
        for key, atoms in (("layer_atoms", cmodel._layer_atoms),
                           ("interlayer_atoms", cmodel._interlayer_atoms)):
            adicts = cprops.get(key)
            if not isinstance(adicts, list):
                continue
            for adict, amodel in zip(adicts, atoms):
                if getattr(amodel, "atom_type", None) is not None:
                    adict.setdefault("properties", {})["atom_type_name"] = \
                        amodel.atom_type.name


def save_phs(phases, path: str) -> None:
    """Export `phases` (Phase / RawPatternPhase models) to a .phs file. A phase
    whose based_on is not also in `phases` is written standalone. Atom types are
    referenced by name so the file is portable across projects."""
    phases = list(phases)
    in_set = set(id(p) for p in phases)
    ordered = _order_parents_first(phases)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for i, phase in enumerate(ordered):
            entry = phase.to_dict()
            props = entry["properties"]
            parent = getattr(phase, "based_on", None)
            if parent is not None and id(parent) in in_set:
                props["based_on_uuid"] = parent.uuid
            elif entry.get("type") == "Phase":
                _clear_inheritance(props)  # standalone
            _make_portable(entry, phase)
            archive.writestr(
                "%d###%s" % (i, phase.uuid),
                json.dumps(entry, separators=(",", ":")),
            )


def load_phs(path: str, project) -> tuple[list, list]:
    """Import phases from a .phs into `project`: resolve the based_on family
    within the file, resolve atom types by name, and add the phases.

    DEEP uuid-collision remap: any uuid in the file that already exists in the
    project - a phase, component OR atom uuid - is replaced by a fresh one
    consistently across every member, BEFORE the models are built. uuids are
    32-hex, so a plain string replace over the serialised member catches every
    reference (own uuid, based_on_uuid, linked_with, atom relations, UCP
    derivation sources) without knowing the schema, so the import stays
    internally consistent and can never alias an existing phase / component /
    atom (e.g. re-importing the same .phs into the same project). A file whose
    uuids do not collide keeps them unchanged.

    Returns (imported_phases, missing_atom_type_names) - the latter lists atom
    types the project does not have, whose atoms have zero structure factor
    until they are added."""
    with zipfile.ZipFile(path) as archive:
        members = sorted(archive.namelist(), key=_member_index)
        texts = [archive.read(m).decode("utf-8") for m in members]

    # Deep collision remap: only uuids that already exist in the project are
    # replaced (a file whose uuids do not collide keeps them).
    texts, _ = remap_uuids(texts, project_uuids(project))

    atom_type_map = project.atom_type_uuid_map()
    imported = []
    for text in texts:
        entry = json.loads(text)
        if entry.get("type") == "RawPatternPhase":
            imported.append(RawPatternPhase.from_dict(entry))
        else:
            imported.append(Phase.from_dict(entry, atom_type_map))

    for phase in imported:
        project.add_phase(phase)
    resolve_phase_references(project)

    # Report atom types the project is missing (atoms left unresolved).
    missing: list[str] = []
    for phase in imported:
        for comp in getattr(phase, "components", []):
            for atom in comp._layer_atoms + comp._interlayer_atoms:
                if atom.atom_type is None:
                    name = atom.raw_properties.get("atom_type_name")
                    if name and name not in missing:
                        missing.append(name)
    return imported, missing
