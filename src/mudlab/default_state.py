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

This module is the bridge between the catalog (file_parsers) and the
composition calc (calculations), which deliberately does not depend on it.
"""

from __future__ import annotations

from mudlab.calculations.composition import mixture_composition
from mudlab.file_parsers.default_catalog import (
    build_default_phase, default_phase_index,
)


def structural_phases(project) -> list:
    """The project's phases that HAVE a composition - only a structural
    ``Phase`` has atoms. A raw-pattern or non-clay accessory is skipped, as it
    is in the composition calc itself."""
    return [phase for phase in project.phases
            if getattr(phase, "type", None) == "Phase"]


def suggest_default_phase_map(project) -> dict:
    """A best-effort ``{phase uuid: default phase name}`` for pre-filling the
    mapping dialog, by exact name match against the catalog.

    Only a starting point: on a real project this matches the unrenamed
    single-clay phases and misses the mixed-layer ones, which is precisely why
    the user gets to correct it.
    """
    index = default_phase_index()
    return {phase.uuid: phase.name
            for phase in structural_phases(project)
            if phase.name in index}


def default_substitutes(project, atom_type_map: dict | None = None) -> dict:
    """``{phase uuid: freshly built default phase}`` for every mapped phase.

    Phases the user has not mapped are absent, so they fall through to their
    CURRENT selves in the comparison - a partial mapping degrades to a partial
    answer rather than a wrong one.
    """
    out = {}
    for uuid_, name in (project.default_phase_map or {}).items():
        phase = build_default_phase(name, atom_type_map)
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
    """True when every structural phase has been mapped to a default phase."""
    phases = structural_phases(project)
    mapping = project.default_phase_map or {}
    return bool(phases) and all(phase.uuid in mapping for phase in phases)


def unmapped_phases(project) -> list:
    """The structural phases with no default stated - named in the dialog so the
    user can see exactly what the comparison is leaving out."""
    mapping = project.default_phase_map or {}
    return [phase for phase in structural_phases(project)
            if phase.uuid not in mapping]
