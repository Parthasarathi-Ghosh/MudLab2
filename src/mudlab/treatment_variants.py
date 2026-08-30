"""Derive the glycolated and heated states of a clay from its air-dried one.

A CIF is one structure in one state. The published record for a clay is almost
always the air-dried form; nobody deposits a separate refinement of the same
sample after ethylene-glycol solvation, so the treated states a clay-science
workflow needs cannot be imported - they have to be built.

They can be, because the treatments do not change the layer. Solvation and
heating change what sits in the **gallery** between layers and therefore the
basal spacing; the 2:1 layer itself is the same object throughout. MudLab's own
shipped smectites are built exactly this way - all six states of Di-Smectite
carry the identical ten layer atoms and differ only in `d001` and
`interlayer_atoms`.

So a derived state takes:

* its **layer** from the imported component, by LINK rather than by copy
  (`linked_with` + inherit ucp_a / ucp_b / delta_c / layer_atoms), so refining
  the base refines every state with it - which is the point of modelling a
  treatment series at all;
* its **gallery** from the corresponding shipped state - the interlayer species
  and the space they occupy.

The gallery is transplanted by HEIGHT, not by absolute z. A shipped 2:1 layer
tops out at 0.654 nm and an imported one at, say, 0.671; copying interlayer
positions verbatim would push the guests 0.017 nm into the layer beneath them.
What carries over is the gallery's thickness - `d001` minus the layer top -
which is the quantity the treatment actually changes.

What this cannot decide, and so does not guess: whether a 2:1 clay is a
smectite or a vermiculite (a layer-charge distinction, invisible in a single
structure), and which state the imported CIF already represents - the four
montmorillonite structures in the reference corpus project to 0.97, 1.11, 1.22
and 1.22 nm, which is dehydrated through one-water-layer. Both are asked.
"""

from __future__ import annotations

import copy
import os

#: Shipped hydration ladders, by family. Each entry is
#: ``(state key, component file, human name)``.
FAMILIES = {
    "Di-Smectite": "Di-Smectite/Di-Smectite - Ca %s.cmp",
    "Tri-Smectite": "Tri-Smectite/Tri-Smectite - Ca %s.cmp",
    "Di-Vermiculite": "Di-Vermiculite/Di-Vermiculite - Ca %s.cmp",
}

#: The states MudLab ships for each family, in swelling order.
STATES = (
    ("2WAT", "two water layers"),
    ("1WAT", "one water layer"),
    ("Dehydr", "dehydrated"),
    ("2GLY", "two glycol layers"),
    ("1GLY", "one glycol layer"),
    ("Heated", "heated (350 °C)"),
)

#: What a treatment series needs: the air-dried, glycolated and heated states.
#: The air-dried member is whichever state the user says the CIF represents.
TREATMENTS = (("EG", "2GLY"), ("350", "Heated"))

#: Component properties a treated state inherits from the air-dried one. The
#: shipped catalog uses exactly this set (`default_catalog._INHERIT_S`): the
#: layer and the cell are shared, the gallery is not.
INHERIT_FROM_BASE = (
    "inherit_ucp_a", "inherit_ucp_b", "inherit_delta_c", "inherit_layer_atoms",
)

_COMPONENT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "default components")


def layer_top(component) -> float:
    """Height of the top of the layer, in nm - where the gallery begins."""
    heights = [atom.default_z for atom in component.layer_atoms]
    return max(heights) if heights else 0.0


def gallery_height(component) -> float:
    """Thickness of the interlayer gallery: the repeat less the layer."""
    return float(component.d001) - layer_top(component)


def shipped_state(family: str, state: str, atom_type_map: dict):
    """Load one shipped hydration state, or None when it is not bundled."""
    pattern = FAMILIES.get(family)
    if pattern is None:
        return None
    path = os.path.join(_COMPONENT_DIR, pattern % state)
    if not os.path.isfile(path):
        return None
    from mudlab.file_parsers.cmp_components import load_cmp

    components, _missing = load_cmp(path, atom_type_map)
    return components[0] if components else None


def _fresh_uuid() -> str:
    import uuid as _uuid

    return _uuid.uuid4().hex


def transplant_gallery(base, donor, atom_type_map: dict):
    """A copy of `base` wearing `donor`'s gallery.

    Built through the same serialise/deserialise round-trip the `.cmp` importer
    uses rather than by deep-copying the objects: an atom's `atom_type` is a
    live shared model object, and duplicating it would give the copy its own
    scattering factors, silently detached from the project's. Going through
    the dict re-resolves every type by name against `atom_type_map`, which is
    what keeps one library behind the whole project.
    """
    from mudlab.models.component import Component

    shift = layer_top(base) - layer_top(donor)
    new_d001 = layer_top(base) + gallery_height(donor)

    data = base.to_dict()
    properties = data["properties"]
    properties["d001"] = new_d001
    properties["default_c"] = new_d001

    guests = []
    for entry in donor.to_dict()["properties"].get("interlayer_atoms") or []:
        guest = {"type": entry.get("type", "Atom"),
                 "properties": dict(entry.get("properties", {}))}
        guest["properties"]["default_z"] = (
            float(guest["properties"].get("default_z", 0.0)) + shift)
        guests.append(guest)
    properties["interlayer_atoms"] = guests

    # A treated state is its own object: nothing may share a uuid with the
    # component it was derived from, or the two would alias on save.
    _refresh_uuids(data)

    variant = Component.from_dict(data, atom_type_map)
    variant.set_linked_with(None)
    return variant


def _refresh_uuids(node) -> None:
    """Give every object in a serialised component a new identity."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "uuid" and isinstance(value, str):
                node[key] = _fresh_uuid()
            else:
                _refresh_uuids(value)
    elif isinstance(node, list):
        for item in node:
            _refresh_uuids(item)


def can_derive(phase) -> tuple:
    """``(possible, reason)`` for building treatment states from `phase`.

    Refuses what cannot swell or cannot be linked one-to-one: a phase without
    exactly one component has no single layer to share, and a 1:1 clay has no
    gallery to fill.
    """
    if phase is None:
        return False, "No phase is selected."
    components = list(getattr(phase, "components", ()) or ())
    if len(components) != 1:
        return False, ("Treatment states are derived for a phase with ONE "
                       "component; this phase has %d." % len(components))
    component = components[0]
    if not component.layer_atoms:
        return False, "This component has no layer atoms."
    from mudlab.file_parsers.cif_component import Row, layer_type

    rows = [Row(atom.name, "", atom.default_z, atom.pn, False)
            for atom in component.layer_atoms]
    kind, sheets = layer_type(rows)
    if kind == "1:1":
        return False, ("This is a 1:1 clay (one tetrahedral sheet). A 1:1 "
                       "layer has no interlayer gallery, so it does not swell "
                       "and has no glycolated state to derive.")
    if kind != "2:1":
        return False, ("This does not look like a 2:1 clay (%d tetrahedral "
                       "sheets found), so there is no gallery to fill."
                       % sheets)
    # Chlorite is 2:1 and still does not swell: its interlayer is a continuous
    # hydroxide (brucite) sheet, not a gallery of exchangeable guests, and
    # octahedral cations sitting there are its signature. Filling it with
    # glycol would model a mineral that does not exist.
    from mudlab.file_parsers.cif_component import OCTAHEDRAL

    brucite = [atom.name for atom in component.interlayer_atoms
               if (atom.name or "").strip() in OCTAHEDRAL]
    if brucite:
        return False, ("The interlayer holds octahedral cations (%s), which "
                       "means a hydroxide sheet rather than an exchangeable "
                       "gallery - a chlorite-like structure. It does not "
                       "swell, so there is no glycolated state to derive."
                       % ", ".join(sorted(set(brucite))))
    return True, ""


def derive(project, phase, family: str, base_state: str,
           atom_type_map: dict) -> list:
    """Create the glycolated and heated phases for `phase`.

    `phase` is treated as the air-dried member and left alone; the new phases
    are based on it and their components link to its component, so refining the
    layer refines the whole series. Returns the phases created.
    """
    possible, reason = can_derive(phase)
    if not possible:
        raise ValueError(reason)

    base_component = phase.components[0]
    stem = phase.name or "Imported"
    created = []
    for label, state in TREATMENTS:
        donor = shipped_state(family, state, atom_type_map)
        if donor is None:
            continue
        variant = transplant_gallery(base_component, donor, atom_type_map)
        variant.name = "%s-%s" % (base_component.name or stem, label)

        new_phase = _clone_phase_shell(phase, "%s-%s" % (stem, label))
        new_phase.components = [variant]

        # The layer is SHARED, not copied: link the component and turn on the
        # same inherit flags the shipped catalog uses for a treated smectite.
        variant.set_linked_with(base_component)
        for flag in INHERIT_FROM_BASE:
            setattr(variant, flag, True)

        new_phase.set_based_on(phase)
        for flag in ("inherit_display_color", "inherit_sigma_star",
                     "inherit_CSDS_distribution"):
            if hasattr(new_phase, flag):
                setattr(new_phase, flag, True)

        project.add_phase(new_phase)
        created.append(new_phase)
    return created


def _clone_phase_shell(phase, name: str):
    """A new phase with `phase`'s settings but no components of its own."""
    from mudlab.models.phase import Phase

    fresh = Phase(name=name)
    fresh.R = getattr(phase, "R", 0)
    for attr in ("sigma_star", "display_color"):
        if hasattr(phase, attr):
            try:
                setattr(fresh, attr, getattr(phase, attr))
            except (AttributeError, TypeError):
                pass
    return fresh
