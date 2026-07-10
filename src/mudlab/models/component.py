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

import uuid as _uuid


class Atom:
    """One atom projected onto the c-axis (old Atom model, calc subset)."""

    def __init__(
        self,
        name: str = "",
        pn: float = 0.0,
        default_z: float = 0.0,
        atom_type=None,
        stretch_z: bool = False,
    ) -> None:
        self.name = name
        self.pn = pn               # number of atoms projected to this z
        self.default_z = default_z  # default z coordinate
        self.atom_type = atom_type  # AtomType model (scattering factors)
        self.z = default_z          # working z, set during get_factors
        self.stretch_z = stretch_z  # interlayer atoms rescale z with d-spacing
        self.uuid = _uuid.uuid4().hex
        # Verbatim .mud atom dict so unmodeled fields (uuid, ref_info) survive.
        self.raw_properties: dict = {}

    @classmethod
    def from_dict(cls, data: dict, atom_type_map: dict) -> "Atom":
        props = data.get("properties", {})
        atom = cls(
            name=props.get("name", ""),
            pn=props.get("pn", 0.0),
            default_z=props.get("default_z", 0.0),
            atom_type=atom_type_map.get(props.get("atom_type_uuid")),
            stretch_z=bool(props.get("stretch_z", False)),
        )
        atom.raw_properties = dict(props)
        if "uuid" in props:
            atom.uuid = props["uuid"]
        return atom

    def to_dict(self) -> dict:
        """Serialize back to a .mud atom dict, overwriting the modeled fields
        (name, default_z, pn, atom_type_uuid) on top of the verbatim raw
        properties. An unresolved atom type keeps its original uuid so the
        reference is not lost."""
        props = dict(self.raw_properties)
        props["name"] = self.name
        props["default_z"] = self.default_z
        props["pn"] = self.pn
        props["stretch_z"] = self.stretch_z
        if self.atom_type is not None:
            props["atom_type_uuid"] = self.atom_type.uuid
        else:
            props.setdefault("atom_type_uuid", props.get("atom_type_uuid", ""))
        props["uuid"] = self.uuid
        return {"type": "Atom", "properties": props}


class Component:
    """One clay layer (old Component model, calc subset)."""

    def __init__(self, name: str = "") -> None:
        self.name = name
        self.d001 = 1.0        # actual d-spacing / cell length c (nm)
        self.default_c = 1.0   # default d-spacing (nm)
        self.delta_c = 0.0     # d-spacing variation (nm)
        self.lattice_d = 0.0   # silicate lattice height (nm)
        self.cell_a = 0.0      # unit-cell length a (nm), from ucp_a
        self.cell_b = 0.0      # unit-cell length b (nm), from ucp_b
        self.layer_atoms: list[Atom] = []
        self.interlayer_atoms: list[Atom] = []
        # Full .mud component dict kept verbatim so unmodeled fields (ucp_a/b,
        # atom_relations, inherit flags, linked_with, ref_info, uuid, and -
        # until the atom lists are wired - the atoms) survive a round-trip.
        self.raw_properties: dict = {}

    @property
    def volume(self) -> float:
        """Unit-cell volume a·b·c (nm³), floored at 1e-25 to avoid
        division-by-zero in the absolute-scale calculation (old
        Component.get_volume; cell_c == d001)."""
        return max(self.cell_a * self.cell_b * self.d001, 1e-25)

    @property
    def weight(self) -> float:
        """Total atomic weight = Σ pn·atom_type.weight over all atoms (old
        Component weight; atoms with no resolved atom type contribute 0)."""
        total = 0.0
        for atom in self.layer_atoms + self.interlayer_atoms:
            if atom.atom_type is not None:
                total += atom.pn * atom.atom_type.weight
        return total

    @staticmethod
    def _ucp_value(ucp) -> float:
        """Resolved unit-cell length from a ucp_a/ucp_b entry. The .mud stores
        the already-recalculated `value` (the old app runs update_value on
        load), so the calc reads it directly rather than re-deriving it from
        the factor/constant/linked-property machinery."""
        if isinstance(ucp, dict):
            return float(ucp.get("properties", {}).get("value", 0.0))
        if isinstance(ucp, (int, float)):
            return float(ucp)
        return 0.0

    def compute_charge_balance(self) -> tuple[float, float, float]:
        """(layer charge, interlayer charge, net) per unit cell = Σ pn·charge
        over each atom list (old Component.compute_charge_balance). Atoms with
        no resolved atom type are skipped; a neutral model nets ~0."""
        def _sum(atoms):
            return sum(
                a.pn * a.atom_type.charge
                for a in atoms
                if a.atom_type is not None
            )
        layer = _sum(self.layer_atoms)
        interlayer = _sum(self.interlayer_atoms)
        return layer, interlayer, layer + interlayer

    def to_dict(self) -> dict:
        """Serialize back to a .mud component dict, overwriting the modeled
        fields (name, c-axis scalars, layer + interlayer atom lists) on top of
        the verbatim raw properties. Cell a/b (ucp), atom relations, inherit
        flags and uuid are preserved (their editors come later)."""
        props = dict(self.raw_properties)
        props["name"] = self.name
        props["d001"] = self.d001
        props["default_c"] = self.default_c
        props["delta_c"] = self.delta_c
        props["layer_atoms"] = [a.to_dict() for a in self.layer_atoms]
        props["interlayer_atoms"] = [a.to_dict() for a in self.interlayer_atoms]
        return {"type": "Component", "properties": props}

    @classmethod
    def from_dict(cls, data: dict, atom_type_map: dict) -> "Component":
        props = data.get("properties", {})
        comp = cls(name=props.get("name", ""))
        comp.raw_properties = dict(props)
        comp.d001 = props.get("d001", 1.0)
        comp.default_c = props.get("default_c", comp.d001)
        comp.delta_c = props.get("delta_c", 0.0)
        comp.lattice_d = props.get("lattice_d", 0.0)
        comp.cell_a = cls._ucp_value(props.get("ucp_a"))
        comp.cell_b = cls._ucp_value(props.get("ucp_b"))
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
