"""The "default state" of a project's phases, for the composition comparison.

A phase starts life as one of the reference clays the app ships (Add phase ->
Default phase). Adding it to a mixture and optimising leave it untouched; the
first REFINEMENT changes it - atom relations rewrite the atoms' occupancies and
stacking probabilities change the component weights, and both feed the oxide
composition. So "what did refinement do to the chemistry?" is answered by
comparing the phases as they are now against the same phases as the catalog
ships them, weighted by the fractions the fit actually found.

WHY THE MAPPING IS USER-SUPPLIED. It cannot be derived:
  - a catalog build mints FRESH uuids every time (measured), so a project
    phase's uuid says nothing about its origin;
  - the phase records nothing about where it came from;
  - names are unreliable - users rename freely, and a real project's
    "IS R0 Ca-AD" is the catalog's "Illite-Smectite R0 Ca-AD".
So the user states it once, and `Project.default_phase_map` remembers it.

CUSTOM DEFAULTS. The shipped catalog cannot cover a reference clay the user
built themselves, so a `.phs` can be imported as a default too. Those phases
live on the project (`Project.custom_default_phases`), NOT in `project.phases` -
a default is a yardstick, not part of the model - and they are saved with the
project, so the comparison still works when the original `.phs` is not to hand.
A custom default SHADOWS a shipped one of the same name (the user's own
reference is the more specific answer).

A BASELINE IS FROZEN. Every stored reference is snapshotted and detached:
inherited values are baked into its own storage and its `based_on` /
`linked_with` links are severed, so nothing that happens to the project later
can move it. This is not optional - measured, a naive copy of an inheriting
phase reported Fe2O3 39.9 where the phase actually resolves to 167.7, because a
copy without its parent silently falls back to its own (stale) stored values.
A live link would be worse still: refining the PARENT would move the baseline.

CAPTURE AT ENTRY. The moment a phase enters the model is the only moment it is
PROVABLY pristine, so that is when its reference is recorded (`capture_*`
below). Afterwards a phase may have been refined, and snapshotting it then would
quietly record the refined state as the baseline - a comparison that always
reads "no change", which is worse than having no baseline at all. Nothing is
captured for a phase built from scratch: there is no reference to capture.

This module is the bridge between the catalog (file_parsers) and the
composition calc (calculations), which deliberately does not depend on it.
"""

from __future__ import annotations

from mudlab.calculations.composition import mixture_composition
from mudlab.file_parsers.atom_type_library import (
    atom_type_library_map, load_atom_type_library,
)
from mudlab.file_parsers.default_catalog import (
    build_catalog_entry_by_name, build_default_phase, default_phase_index,
)
from mudlab.file_parsers.phs_phases import load_phs


def structural_phases(project) -> list:
    """The project's phases that HAVE a composition - only a structural
    ``Phase`` has atoms. A raw-pattern or non-clay accessory is skipped, as it
    is in the composition calc itself."""
    return [phase for phase in project.phases
            if getattr(phase, "type", None) == "Phase"]


def _resolution_map(project) -> dict:
    """Atom-type resolution for a baseline copy: the project's own types first,
    the built-in library behind them (both keyed by uuid AND name)."""
    return {**atom_type_library_map(), **project.atom_type_uuid_map()}


def freeze_baseline(phase, atom_type_map: dict) -> None:
    """Bake `phase`'s inherited values into its own storage and cut every link,
    IN PLACE. Only ever called on a copy the caller owns.

    Order matters: the values can only be baked while the links still resolve,
    so snapshot first and sever afterwards. `Component.snapshot_inherited` bakes
    atom lists by SHARING the template's atom objects (safe in its original
    caller, where the template is being deleted), so any component that was
    linked is re-cloned afterwards - otherwise the "frozen" baseline would still
    hold the live phase's atoms and move with them.
    """
    linked = [component for component in phase.components
              if getattr(component, "linked_with", None) is not None]
    phase.snapshot_inherited()
    for component in phase.components:
        component.snapshot_inherited()
    phase.set_based_on(None)
    for component in phase.components:
        component.set_linked_with(None)
    for component in linked:
        component.reclone_atoms(atom_type_map)


def make_baseline_copy(project, phase):
    """An independent, frozen snapshot of `phase` exactly as it is now.

    The copy is re-attached to the LIVE parent and templates only long enough to
    bake their resolved values in, then cut loose. Afterwards it shares no
    object with the project and reads no value from it.
    """
    from mudlab.models.phase import Phase

    atom_type_map = _resolution_map(project)
    copy = Phase.from_dict(phase.to_dict(), atom_type_map)
    copy.set_based_on(getattr(phase, "based_on", None))
    for own, live in zip(copy.components, phase.components):
        template = getattr(live, "linked_with", None)
        if template is not None:
            own.set_linked_with(template)
    freeze_baseline(copy, atom_type_map)
    return copy


def set_as_baseline(project, phase) -> bool:
    """Record `phase`'s CURRENT state as its own baseline.

    The deliberate, user-invoked counterpart to capture-at-entry, for a phase
    that never had a reference (built from scratch) or whose captured one is no
    longer the right starting point. Everything already done to the phase
    becomes part of the baseline - which is why this is never automatic.
    """
    if getattr(phase, "type", None) != "Phase":
        return False
    copy = make_baseline_copy(project, phase)
    copy.name = _baseline_name(project, phase)
    project.add_custom_default_phase(copy)
    _remember_defaults(project, {phase.uuid: copy.name})
    return True


def _baseline_name(project, phase) -> str:
    """A name for `phase`'s captured baseline that reads clearly in the
    drop-down and cannot collide with another phase's.

    Suffixed rather than reusing the phase's own name so it is obvious in the
    list that this is a captured state, and numbered if two phases share a name
    - which nothing prevents, and which would otherwise make the second capture
    silently overwrite the first's baseline.
    """
    base = "%s (baseline)" % (phase.name or "Phase")
    mapping = project.default_phase_map
    taken = {name for uuid_, name in mapping.items() if uuid_ != phase.uuid}
    if base not in taken:
        return base
    index = 2
    while "%s %d" % (base, index) in taken:
        index += 1
    return "%s %d" % (base, index)


def _load_phs_standalone(path: str) -> list:
    """Phases from a .phs, built WITHOUT touching any real project.

    Loaded into a throwaway project seeded with the atom-type library, so the
    atoms resolve (by name) without the caller having to adopt foreign atom
    types into their own project.
    """
    from mudlab.models.project import Project

    scratch = Project()
    for atom_type in load_atom_type_library():
        scratch.add_atom_type(atom_type)
    phases, _missing = load_phs(path, scratch)
    return phases


def phases_used_in_mixtures(project) -> set:
    """uuids of the phases that actually sit in some mixture's phase grid.

    Only these can affect a composition - `mixture_composition` reads
    `phase_matrix` and nothing else - so a phase in the project but in no
    mixture cannot contribute a column, and stating its default is busywork.
    """
    used = set()
    for mixture in project.mixtures:
        for row in mixture.phase_matrix:
            for phase in row:
                if phase is not None:
                    used.add(phase.uuid)
    return used


def custom_default_names(project) -> list:
    """The names of the project's imported reference phases, sorted."""
    return sorted(getattr(phase, "name", "")
                  for phase in getattr(project, "custom_default_phases", ()))


def available_default_names(project) -> list:
    """Every name that can be chosen as a default: the project's imported
    references first, then the shipped catalog (minus any a custom one
    shadows), so the list never offers the same name twice."""
    custom = custom_default_names(project)
    shipped = [name for name in sorted(default_phase_index())
               if name not in set(custom)]
    return custom + shipped


def resolve_default_phase(project, name: str):
    """The phase for a default NAME - a custom import first, then the shipped
    catalog. Returns None when neither has it (a project naming a custom
    default whose import was later removed)."""
    for phase in getattr(project, "custom_default_phases", ()):
        if getattr(phase, "name", "") == name:
            return phase
    return build_default_phase(name)


def import_custom_defaults(project, path: str) -> tuple:
    """Import a `.phs` as reference (default) phases for `project`.

    Returns ``(added_names, shadowed_names)``: what was imported, and which of
    those shadow a shipped catalog name - worth telling the user, since the
    custom one then wins.

    The .phs is loaded into a THROWAWAY project seeded with the atom-type
    library, never into `project`: importing a yardstick must not add phases to
    the model, nor quietly extend the project's atom-type list. The atoms keep
    their names, and `Atom.from_dict` resolves by name, so the phases still read
    back correctly after a save (see mud_project).
    """
    phases = _load_phs_standalone(path)
    atom_type_map = _resolution_map(project)
    shipped = default_phase_index()
    added, shadowed = [], []
    for phase in phases:
        # Only structural phases have a composition to compare against.
        if getattr(phase, "type", None) != "Phase":
            continue
        freeze_baseline(phase, atom_type_map)
        project.add_custom_default_phase(phase)
        added.append(phase.name)
        if phase.name in shipped:
            shadowed.append(phase.name)
    return added, shadowed


def _remember_defaults(project, mapping: dict) -> None:
    """Merge `mapping` into the project's default-phase map (never replace: a
    capture must not discard what the user stated earlier)."""
    if mapping:
        project.set_default_phase_map({**project.default_phase_map, **mapping})


def capture_catalog_defaults(project, phases, entry_name: str | None = None) -> list:
    """Record the default for phases just added from the SHIPPED catalog.

    No copy is stored: the catalog can rebuild these on demand, so only the
    mapping is needed. At this instant `phase.name` IS the catalog phase name -
    a later rename does not matter, because the mapping is keyed by uuid.
    Returns the names recorded.

    `entry_name` is the catalog entry the phases came from. Given it, the names
    are checked against THAT ONE entry (a few milliseconds); without it the
    whole catalog index has to be built, which costs about 1.2 s the first time
    - measured, and enough to make Add-phase feel broken. The check is worth
    keeping either way: it stops a caller recording a mapping to a name the
    catalog cannot rebuild, which would fail silently at comparison time.
    """
    if entry_name is not None:
        known = {phase.name for phase in build_catalog_entry_by_name(entry_name)}
    else:
        known = set(default_phase_index())
    mapping = {}
    for phase in phases:
        if getattr(phase, "type", None) == "Phase" and phase.name in known:
            mapping[phase.uuid] = phase.name
    _remember_defaults(project, mapping)
    return sorted(mapping.values())


def capture_imported_defaults(project, path: str, imported) -> list:
    """Record references for phases just imported into the model from `path`.

    A SECOND, independent copy is loaded from the same file rather than reusing
    the objects now in the project: those are the working phases, and a
    refinement rewrites them in place - a reference sharing their components or
    atoms would be refined along with them and the comparison would collapse to
    "no change".

    Pairs the two loads BY POSITION: both read the archive members in the same
    order, and a .phs may legitimately contain two phases with one name, which
    name-matching would confuse. Returns the names recorded.
    """
    try:
        pristine = _load_phs_standalone(path)
    except Exception:  # noqa: BLE001 - capture is a convenience, never fatal
        return []
    atom_type_map = _resolution_map(project)
    mapping = {}
    for phase, reference in zip(imported, pristine):
        if getattr(phase, "type", None) != "Phase":
            continue
        if getattr(reference, "type", None) != "Phase":
            continue
        # Freeze even though these came from a throwaway load: a .phs may carry
        # a whole family, and each reference is persisted on its own - a
        # based_on pointing at a sibling would dangle on reload and silently
        # fall back to stale own values.
        freeze_baseline(reference, atom_type_map)
        project.add_custom_default_phase(reference)
        mapping[phase.uuid] = reference.name
    _remember_defaults(project, mapping)
    return sorted(mapping.values())


def suggest_default_phase_map(project) -> dict:
    """A best-effort ``{phase uuid: default phase name}`` for pre-filling the
    mapping dialog, by exact name match against the available defaults.

    Only a starting point: on a real project this matches the unrenamed
    single-clay phases and misses the mixed-layer ones, which is precisely why
    the user gets to correct it. Imported custom defaults are included, which is
    what makes importing a `.phs` named after the phase immediately useful.
    """
    available = set(available_default_names(project))
    return {phase.uuid: phase.name
            for phase in structural_phases(project)
            if phase.name in available}


def default_substitutes(project, atom_type_map: dict | None = None) -> dict:
    """``{phase uuid: freshly built default phase}`` for every mapped phase.

    Phases the user has not mapped are absent, so they fall through to their
    CURRENT selves in the comparison - a partial mapping degrades to a partial
    answer rather than a wrong one.
    """
    out = {}
    for uuid_, name in (project.default_phase_map or {}).items():
        phase = resolve_default_phase(project, name)
        if phase is not None:
            out[uuid_] = phase
    return out


def default_state_composition(mixture, project, conversion: dict | None = None):
    """``(specimen_names, oxide_rows)`` for the mixture as if every mapped phase
    were still in its shipped default state.

    The mixture's own FRACTIONS are used - that is the question being asked:
    what would this sample's chemistry be if the phases had never been refined,
    in the proportions the fit found? Returns ``(names, [])`` when nothing is
    mapped, so a caller can tell "no answer" from "an answer of zero".
    """
    substitutes = default_substitutes(project)
    if not substitutes:
        names, _rows = mixture_composition(mixture, conversion)
        return names, []
    return mixture_composition(mixture, conversion, substitutes=substitutes)


def mapping_is_complete(project) -> bool:
    """True when every structural phase has a default that actually resolves."""
    return bool(structural_phases(project)) and not unmapped_phases(project)


def unmapped_phases(project) -> list:
    """The structural phases the comparison cannot put a default against -
    named in the dialog so the user sees exactly what it is leaving out.

    A phase whose stated default no longer RESOLVES counts as unmapped: the
    reference may have been removed since, and `default_substitutes` then skips
    it. Counting it as mapped would report "all stated" while quietly showing
    that phase at its current state - an answer that looks complete and is not.
    """
    mapping = project.default_phase_map or {}
    return [phase for phase in structural_phases(project)
            if phase.uuid not in mapping
            or resolve_default_phase(project, mapping[phase.uuid]) is None]


# ---------------------------------------------------------------------------
# Reset a phase to the state it was shipped in
# ---------------------------------------------------------------------------

#: Phase-level values a reset restores. NAME and DISPLAY_COLOR are deliberately
#: absent: they are labels the user chose, not structure. `based_on` is absent
#: too - see reset_to_default.
_PHASE_STRUCTURE = ("sigma_star", "CSDS", "probabilities")

#: Component-level values a reset restores. `linked_with` is absent for the
#: same reason as `based_on`; `name` because a renamed component is still that
#: component.
_COMPONENT_SCALARS = ("d001", "default_c", "delta_c")


def can_reset(project, phase) -> tuple:
    """``(possible, reason)`` for resetting `phase` to its shipped default.

    A phase can only be reset if the project SAYS what it started as. That
    mapping is recorded automatically when a phase is added from the catalog,
    and can be stated by hand in the Default Phases dialog - which is the only
    route for a project created before the mapping existed, where nothing was
    captured and the phases have since been refined. Guessing a default by name
    at reset time is exactly the wrong moment to guess.
    """
    if getattr(phase, "type", None) != "Phase":
        return False, "Only a structural phase has a shipped default."
    name = (getattr(project, "default_phase_map", None) or {}).get(phase.uuid)
    if not name:
        return False, ("This phase has no stated default. Use "
                       "Composition \u2192 Default phases to say which "
                       "default it started as, then Reset becomes available.")
    if resolve_default_phase(project, name) is None:
        return False, ("Its stated default %r is not available any more - the "
                       "import it came from is gone." % name)
    return True, name


def reset_to_default(project, phase) -> bool:
    """Restore `phase`'s own STRUCTURE from the default it started as.

    WHAT IS RESTORED: sigma*, the CSDS distribution, the stacking
    probabilities, and per component d001 / default c / delta c, the unit-cell
    properties, the atoms and the atom relations.

    WHAT IS NOT, and why:

    * **name and display colour** - labels the user chose. Renaming a phase
      back, or repainting its curve, is not what "reset the structure" means.
    * **`based_on` and `linked_with`** - the shipped default has neither, so
      applying it literally would DISMANTLE the inheritance graph. Severing is
      destructive enough that the app has snapshot-on-detach to soften it; a
      reset should not do it silently. The links are left exactly as they are.
    * **fractions, scales, background shifts** - those belong to the mixture,
      not the phase.

    NOTE the phase is ONE OBJECT shared by every mixture cell that uses it
    (verified: three cells of `308 r1.mud` hold the same Illite object), so a
    reset necessarily applies everywhere it is used. There is no per-mixture
    reset without duplicating the phase. Callers recompute.

    A phase that INHERITS may look unchanged afterwards: its own values are
    restored, but an inherit flag means the editor still reads through to the
    parent. That is correct, and the UI says so before confirming.
    """
    possible, name = can_reset(project, phase)
    if not possible:
        return False
    source = resolve_default_phase(project, name)
    if source is None:
        return False

    # Work on a detached rebuild: `source` may be a live custom-default phase,
    # and nothing of it may end up shared with the phase being reset.
    from mudlab.models.phase import Phase

    atom_type_map = _resolution_map(project)
    fresh = Phase.from_dict(source.to_dict(), atom_type_map)

    # VALIDATE BEFORE MUTATING. The first version zipped the component lists
    # and copied what lined up, so a phase whose shape had diverged from its
    # stated default was reset in PART and still reported success - the worst
    # of both. A mismatch means the mapping is wrong, not that some of it
    # should be applied.
    if len(fresh.components) != len(phase.components):
        return False
    live_probs = getattr(phase, "probabilities", None)
    clean_probs = getattr(fresh, "probabilities", None)
    probability_rows = None
    if live_probs is not None and clean_probs is not None:
        live_rows = live_probs.editable_params()
        clean_rows = clean_probs.editable_params()
        if len(live_rows) != len(clean_rows):
            return False
        probability_rows = list(zip(live_rows, clean_rows))

    # ---- nothing above this line has changed the phase; everything below does
    phase.sigma_star = fresh.sigma_star

    # CSDS and PROBABILITIES are copied BY VALUE into the existing objects,
    # never replaced. `Phase.set_based_on` links this phase's probabilities
    # object to the parent's (`probabilities.set_based_on`), so swapping the
    # object in would quietly sever the inheritance this reset leaves alone.
    live_csds, clean_csds = phase.CSDS, fresh.CSDS
    if live_csds is not None and clean_csds is not None:
        live_csds.average = clean_csds.average
    else:
        phase.CSDS = clean_csds

    for row, clean_row in probability_rows or ():
        row["set"](clean_row["get"]())

    for live, clean in zip(phase.components, fresh.components):
        for attr in _COMPONENT_SCALARS:
            if hasattr(clean, attr):
                setattr(live, attr, getattr(clean, attr))

        # Atoms first: the unit-cell properties may DERIVE from an atom, and
        # that reference has to point at an atom the live component now owns.
        live.layer_atoms = list(clean.layer_atoms)
        live.interlayer_atoms = list(clean.interlayer_atoms)
        live.atom_relations = list(clean.atom_relations)

        atoms = {a.uuid: a for a in live.layer_atoms + live.interlayer_atoms}
        atoms[live.uuid] = live
        for ucp_name in ("ucp_a", "ucp_b"):
            target = getattr(live, ucp_name, None)
            plain = getattr(clean, ucp_name, None)
            if target is None or plain is None:
                continue
            target.value = plain.value
            target.enabled = plain.enabled
            target.factor = plain.factor
            target.constant = plain.constant
            # NOT `target.prop = plain.prop` - that is a live (object, attr)
            # pair pointing into the throwaway rebuild. Re-resolve the stored
            # [uuid, attr] against the atoms this component now holds.
            target.prop = None
            target._prop_ref = getattr(plain, "_prop_ref", None)
            target.resolve_prop(atoms)
        live.update_ucp_values()
        live.apply_atom_relations()

    # The mapping now points at what the phase actually is again. A baseline the
    # user had stored is superseded - that is what "reset" means here.
    _remember_defaults(project, {phase.uuid: name})
    return True


def mixtures_using(project, phase) -> list:
    """Mixtures that would be recalculated by resetting `phase`."""
    return [m for m, _cells in project.phase_usage(phase)]
