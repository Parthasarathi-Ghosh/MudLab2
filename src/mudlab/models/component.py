"""Atom and Component models for the layer structure-factor calculation.

Ported from the old mudlab.phases.models (Atom / Component). A Component is
one clay layer: its layer and interlayer atoms plus the d-spacing terms
consumed by `calculations.components.get_factors`. Atoms reference a
project AtomType by uuid.

These are calculation models loaded from the .mud and bound to the Edit
Phases component editor: the modeled fields (name, c-axis scalars, layer/
interlayer atoms) save via to_dict, while unmodeled fields (ucp a/b, atom
relations, uuid, ref_info) round-trip verbatim through raw_properties.
"""

from __future__ import annotations

import uuid as _uuid

from mudlab.models.atom_relations import AtomRatio
from mudlab.models.unit_cell_prop import UnitCellProperty


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
    """One clay layer (old Component model, calc subset).

    A component may be *linked* to a template component in another phase (the
    old ``linked_with`` + per-property ``inherit_*`` flags): the same clay
    layer reused across phases (e.g. an illite layer appearing both in a
    discrete illite phase and inside an illite-smectite mixed-layer phase).

    Inheritance is a **read-time overlay** - an inherited property reads
    through to the template's value, while the component keeps its own stored
    copy for serialisation (so round-trips stay byte-identical). It is
    **per-property**: a smectite child typically inherits cell a/b + delta_c +
    layer atoms from its 2-water template but keeps its own d001 / interlayer
    atoms (the air-dried -> glycolated -> heated swelling states).
    """

    #: read-through attr -> the inherit flag that gates it. NOTE: d001 is
    #: gated by inherit_default_c, matching the old app (its separate
    #: inherit_d001 flag is carried for round-trip but does not gate d001
    #: there either; the two always move together in real projects).
    _INHERIT_MAP = {
        "cell_a": "inherit_ucp_a",
        "cell_b": "inherit_ucp_b",
        "d001": "inherit_default_c",
        "default_c": "inherit_default_c",
        "delta_c": "inherit_delta_c",
        "lattice_d": "inherit_layer_atoms",
        "layer_atoms": "inherit_layer_atoms",
        "interlayer_atoms": "inherit_interlayer_atoms",
        "atom_relations": "inherit_atom_relations",
    }

    def __init__(self, name: str = "") -> None:
        self.name = name
        self.uuid = _uuid.uuid4().hex  # overwritten from the .mud on load
        # Component linking (old linked_with + inherit_* flags). linked_with is
        # resolved from _linked_with_uuid once every phase's components exist
        # (see mud_project.load_mud); the eight flags pick which properties
        # read through to the template.
        self.linked_with: "Component | None" = None
        self._linked_with_uuid = ""
        self.inherit_ucp_a = False
        self.inherit_ucp_b = False
        self.inherit_d001 = False
        self.inherit_default_c = False
        self.inherit_delta_c = False
        self.inherit_layer_atoms = False
        self.inherit_interlayer_atoms = False
        self.inherit_atom_relations = False
        # Own stored values (overlaid by the read-through getters below when
        # the matching inherit flag is set and a template is resolved).
        self._d001 = 1.0        # actual d-spacing / cell length c (nm)
        self._default_c = 1.0   # default d-spacing (nm)
        self._delta_c = 0.0     # d-spacing variation (nm)
        self._lattice_d = 0.0   # silicate lattice height (nm)
        # Cell lengths a / b are unit-cell properties (fixed or derived from
        # cell_b / an atom pn). cell_a / cell_b read their resolved `value`.
        self._ucp_a = UnitCellProperty(name="cell length a")
        self._ucp_b = UnitCellProperty(name="cell length b")
        self._layer_atoms: list[Atom] = []
        self._interlayer_atoms: list[Atom] = []
        # Atom relations (AtomRatio objects; AtomContents + any other type kept
        # as verbatim dicts until Batch 3). They derive atom pn values; applied
        # only on an edit (the stored pn is used on load - golden-safe).
        self._atom_relations: list = []
        # Full .mud component dict kept verbatim so unmodeled fields (ucp_a/b,
        # ref_info, the inlined linked_with copy, and unmodeled relations)
        # survive a round-trip.
        self.raw_properties: dict = {}

    # ------------------------------------------------------------------
    # Component linking (read-through overlay)
    # ------------------------------------------------------------------
    def _resolved_own(self, attr: str):
        """Walk the linked_with chain until a component that does NOT inherit
        `attr`, then return that component's own stored value. Iterative and
        cycle-guarded, so a broken or looping link degrades to a local value
        instead of recursing forever."""
        node = self
        seen: set[int] = set()
        while True:
            flag = getattr(node, self._INHERIT_MAP[attr])
            nxt = node.linked_with
            if flag and nxt is not None and nxt is not node and id(node) not in seen:
                seen.add(id(node))
                node = nxt
                continue
            return node._own_value(attr)

    def _own_value(self, attr: str):
        """This component's own (un-inherited) value of `attr`. Cell a/b live
        on their UnitCellProperty objects; the rest are plain `_attr`."""
        if attr == "cell_a":
            return self._ucp_a.value
        if attr == "cell_b":
            return self._ucp_b.value
        return getattr(self, "_" + attr)

    # -- unit-cell properties (fixed or derived) ------------------------
    @property
    def ucp_a(self) -> UnitCellProperty:
        return self._ucp_a

    @property
    def ucp_b(self) -> UnitCellProperty:
        return self._ucp_b

    def resolve_ucp_props(self, object_map: dict) -> None:
        """Resolve the ucp_a / ucp_b derivation sources (cell_b / an atom pn)
        against a project-wide {uuid: object} map. Does NOT recompute values -
        the stored (possibly stale) value is kept for golden-calc fidelity."""
        self._ucp_a.resolve_prop(object_map)
        self._ucp_b.resolve_prop(object_map)

    def update_ucp_values(self) -> None:
        """Recompute the derived cell lengths after an edit. cell_b may derive
        from an atom pn and cell_a from cell_b, so update b before a."""
        self._ucp_b.update_value()
        self._ucp_a.update_value()

    # -- atom relations (derive atom pn) --------------------------------
    @property
    def atom_relations(self) -> list:
        return self._resolved_own("atom_relations")

    @atom_relations.setter
    def atom_relations(self, value) -> None:
        self._atom_relations = value

    def resolve_relations(self, atom_map: dict) -> None:
        """Resolve the modeled relations' atom references against a {uuid: Atom}
        map (call once every atom exists). Does NOT apply them - the stored pn
        is kept for golden-calc fidelity."""
        for relation in self._atom_relations:
            resolve = getattr(relation, "resolve", None)
            if callable(resolve):
                resolve(atom_map)

    def apply_atom_relations(self) -> None:
        """Re-apply the modeled relations in order (setting their atoms' pn),
        then recompute the derived cell lengths (a pn may drive cell_b). Called
        after a relation edit, not on load."""
        for relation in self._atom_relations:
            apply = getattr(relation, "apply_relation", None)
            if callable(apply):
                apply()
        self.update_ucp_values()

    def is_inherited(self, attr: str) -> bool:
        """True when `attr` currently reads through to a linked template (so it
        is not independently editable / refinable on this component)."""
        flag = getattr(self, self._INHERIT_MAP.get(attr, ""), False)
        return bool(flag) and self.linked_with is not None and self.linked_with is not self

    def resolve_link(self, component_map: dict) -> None:
        """Resolve linked_with from the stored template uuid against a
        project-wide {uuid: Component} map (call after all phases load)."""
        if self._linked_with_uuid:
            target = component_map.get(self._linked_with_uuid)
            if target is not None and target is not self:
                self.linked_with = target

    def set_linked_with(self, target) -> bool:
        """Link this component to a template (or None to unlink). Rejects a
        self-link or one that would create a cycle. Unlinking clears the eight
        inherit flags (old app: linked_with setter resets them). Returns True
        if the link was applied."""
        if target is self:
            return False
        # Cycle guard: walking the target's own chain must not reach self.
        node, seen = target, set()
        while node is not None and id(node) not in seen:
            if node is self:
                return False
            seen.add(id(node))
            node = node.linked_with
        self.linked_with = target
        self._linked_with_uuid = target.uuid if target is not None else ""
        if target is None:
            self.inherit_ucp_a = self.inherit_ucp_b = False
            self.inherit_d001 = self.inherit_default_c = self.inherit_delta_c = False
            self.inherit_layer_atoms = self.inherit_interlayer_atoms = False
            self.inherit_atom_relations = False
        return True

    # -- read-through c-axis / cell scalars (own value when not inherited) --
    @property
    def d001(self) -> float:
        return self._resolved_own("d001")

    @d001.setter
    def d001(self, value) -> None:
        self._d001 = float(value)

    @property
    def default_c(self) -> float:
        return self._resolved_own("default_c")

    @default_c.setter
    def default_c(self, value) -> None:
        self._default_c = float(value)

    @property
    def delta_c(self) -> float:
        return self._resolved_own("delta_c")

    @delta_c.setter
    def delta_c(self, value) -> None:
        self._delta_c = float(value)

    @property
    def lattice_d(self) -> float:
        return self._resolved_own("lattice_d")

    @lattice_d.setter
    def lattice_d(self, value) -> None:
        self._lattice_d = float(value)

    @property
    def cell_a(self) -> float:
        return self._resolved_own("cell_a")

    @cell_a.setter
    def cell_a(self, value) -> None:
        self._ucp_a.value = float(value)

    @property
    def cell_b(self) -> float:
        return self._resolved_own("cell_b")

    @cell_b.setter
    def cell_b(self, value) -> None:
        self._ucp_b.value = float(value)

    @property
    def layer_atoms(self) -> list:
        return self._resolved_own("layer_atoms")

    @layer_atoms.setter
    def layer_atoms(self, value) -> None:
        self._layer_atoms = value

    @property
    def interlayer_atoms(self) -> list:
        return self._resolved_own("interlayer_atoms")

    @interlayer_atoms.setter
    def interlayer_atoms(self, value) -> None:
        self._interlayer_atoms = value

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
    def _make_ucp(raw, name: str) -> UnitCellProperty:
        """Build a UnitCellProperty from a ucp_a/ucp_b entry. A dict is the full
        UCP (fixed or derived); a bare float is the old fixed-value form. The
        stored `value` is kept as-is (NOT recomputed) so the calc reproduces
        the old app's stored pattern - see the UnitCellProperty docstring."""
        if isinstance(raw, dict):
            return UnitCellProperty.from_dict(raw)
        ucp = UnitCellProperty(name=name)
        if isinstance(raw, (int, float)):
            ucp.value = float(raw)
        return ucp

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
        fields (name, c-axis scalars, layer + interlayer atom lists, and the
        component-linking state) on top of the verbatim raw properties.

        The scalars/atoms are written from this component's OWN stored values
        (``_d001`` etc.), never the inherited read-through values, so a linked
        child round-trips byte-identically. Cell a/b (ucp), atom relations and
        the inlined ``linked_with`` copy are preserved verbatim."""
        props = dict(self.raw_properties)
        props["name"] = self.name
        props["d001"] = self._d001
        props["default_c"] = self._default_c
        props["delta_c"] = self._delta_c
        props["layer_atoms"] = [a.to_dict() for a in self._layer_atoms]
        props["interlayer_atoms"] = [a.to_dict() for a in self._interlayer_atoms]
        # Unit-cell properties (fixed or derived cell a/b). Written from the own
        # UCP objects; unedited they reproduce the raw dicts byte-for-byte.
        props["ucp_a"] = self._ucp_a.to_dict()
        props["ucp_b"] = self._ucp_b.to_dict()
        # Atom relations: AtomRatio via to_dict, other types verbatim.
        props["atom_relations"] = [
            r.to_dict() if hasattr(r, "to_dict") else r for r in self._atom_relations
        ]
        # Component linking: the eight inherit flags + the template uuid. The
        # inlined linked_with copy (if present) stays verbatim in props.
        props["inherit_ucp_a"] = self.inherit_ucp_a
        props["inherit_ucp_b"] = self.inherit_ucp_b
        props["inherit_d001"] = self.inherit_d001
        props["inherit_default_c"] = self.inherit_default_c
        props["inherit_delta_c"] = self.inherit_delta_c
        props["inherit_layer_atoms"] = self.inherit_layer_atoms
        props["inherit_interlayer_atoms"] = self.inherit_interlayer_atoms
        props["inherit_atom_relations"] = self.inherit_atom_relations
        props["linked_with_uuid"] = (
            self.linked_with.uuid if self.linked_with is not None
            else self._linked_with_uuid
        )
        return {"type": "Component", "properties": props}

    @classmethod
    def from_dict(cls, data: dict, atom_type_map: dict) -> "Component":
        props = data.get("properties", {})
        comp = cls(name=props.get("name", ""))
        comp.raw_properties = dict(props)
        if "uuid" in props:
            comp.uuid = props["uuid"]
        comp.d001 = props.get("d001", 1.0)
        comp.default_c = props.get("default_c", comp._d001)
        comp.delta_c = props.get("delta_c", 0.0)
        comp.lattice_d = props.get("lattice_d", 0.0)
        comp._ucp_a = cls._make_ucp(props.get("ucp_a"), "cell length a")
        comp._ucp_b = cls._make_ucp(props.get("ucp_b"), "cell length b")
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
        # Atom relations: model AtomRatio; keep any other type (AtomContents
        # until Batch 3) as a verbatim dict so it round-trips untouched.
        comp._atom_relations = [
            AtomRatio.from_dict(r) if isinstance(r, dict) and r.get("type") == "AtomRatio"
            else r
            for r in (props.get("atom_relations") or [])
        ]
        # Component-linking state. linked_with is resolved later (once every
        # phase's components exist); the flags gate the read-through overlay.
        comp._linked_with_uuid = props.get("linked_with_uuid", "") or ""
        comp.inherit_ucp_a = bool(props.get("inherit_ucp_a", False))
        comp.inherit_ucp_b = bool(props.get("inherit_ucp_b", False))
        comp.inherit_d001 = bool(props.get("inherit_d001", False))
        comp.inherit_default_c = bool(props.get("inherit_default_c", False))
        comp.inherit_delta_c = bool(props.get("inherit_delta_c", False))
        comp.inherit_layer_atoms = bool(props.get("inherit_layer_atoms", False))
        comp.inherit_interlayer_atoms = bool(props.get("inherit_interlayer_atoms", False))
        comp.inherit_atom_relations = bool(props.get("inherit_atom_relations", False))
        return comp

    def get_factors(self, range_stl):
        """(structure factor, phase difference) over 2·sin(θ)/λ (nm⁻¹)."""
        from mudlab.calculations.components import get_factors

        return get_factors(range_stl, self)
