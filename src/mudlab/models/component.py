"""Atom and Component models for the layer structure-factor calculation.

Ported from the old mudlab.phases.models (Atom / Component). A Component is
one clay layer: its layer and interlayer atoms plus the d-spacing terms
consumed by `calculations.components.get_factors`. Atoms reference a
project AtomType by uuid.

These are calculation models loaded from the .mud; the phase editor UI is
wired later, so phases/components are still saved verbatim (raw
passthrough) for now.
"""

from __future__ import annotations


class Atom:
    """One atom projected onto the c-axis (old Atom model, calc subset)."""

    def __init__(
        self,
        name: str = "",
        pn: float = 0.0,
        default_z: float = 0.0,
        atom_type=None,
    ) -> None:
        self.name = name
        self.pn = pn               # number of atoms projected to this z
        self.default_z = default_z  # default z coordinate
        self.atom_type = atom_type  # AtomType model (scattering factors)
        self.z = default_z          # working z, set during get_factors

    @classmethod
    def from_dict(cls, data: dict, atom_type_map: dict) -> "Atom":
        props = data.get("properties", {})
        return cls(
            name=props.get("name", ""),
            pn=props.get("pn", 0.0),
            default_z=props.get("default_z", 0.0),
            atom_type=atom_type_map.get(props.get("atom_type_uuid")),
        )


class Component:
    """One clay layer (old Component model, calc subset)."""

    def __init__(self, name: str = "") -> None:
        self.name = name
        self.d001 = 1.0        # actual d-spacing (nm)
        self.default_c = 1.0   # default d-spacing (nm)
        self.delta_c = 0.0     # d-spacing variation (nm)
        self.lattice_d = 0.0   # silicate lattice height (nm)
        self.layer_atoms: list[Atom] = []
        self.interlayer_atoms: list[Atom] = []

    @classmethod
    def from_dict(cls, data: dict, atom_type_map: dict) -> "Component":
        props = data.get("properties", {})
        comp = cls(name=props.get("name", ""))
        comp.d001 = props.get("d001", 1.0)
        comp.default_c = props.get("default_c", comp.d001)
        comp.delta_c = props.get("delta_c", 0.0)
        comp.lattice_d = props.get("lattice_d", 0.0)
        comp.layer_atoms = [
            Atom.from_dict(a, atom_type_map)
            for a in (props.get("layer_atoms") or [])
            if isinstance(a, dict)
        ]
        comp.interlayer_atoms = [
            Atom.from_dict(a, atom_type_map)
            for a in (props.get("interlayer_atoms") or [])
            if isinstance(a, dict)
        ]
        return comp

    def get_factors(self, range_stl):
        """(structure factor, phase difference) over 2·sin(θ)/λ (nm⁻¹)."""
        from mudlab.calculations.components import get_factors

        return get_factors(range_stl, self)
