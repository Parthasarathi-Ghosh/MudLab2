"""Atom relations - links that derive atom occupancies (pn) from a parameter.

Ported from the old mudlab.phases.models.atom_relations (calc subset). Only
AtomRatio is modeled so far (Batch 2); AtomContents comes with Batch 3 and its
entries round-trip verbatim until then.

An **AtomRatio** splits an occupancy between two atoms - a substitution such as
octahedral Fe-for-Mg: ``atom1.pn = value * sum`` and ``atom2.pn = (1-value) *
sum`` (value in [0, 1], the substituting fraction). It drives the atoms' pn,
which feed the structure factor and, where a cell length derives from a pn, the
unit-cell dimensions.

Golden-calc safety: the .mud stores the already-applied pn, so relations are
NOT applied on load (the stored pn is kept and reproduces the old app's
pattern); ``apply_relation`` runs only on an edit.
"""

from __future__ import annotations

import uuid as _uuid


class AtomRatio:
    def __init__(
        self,
        name: str = "",
        value: float = 0.0,
        sum: float = 1.0,
        enabled: bool = True,
    ) -> None:
        self.name = name
        self.value = float(value)   # substituting fraction, in [0, 1]
        self.sum = float(sum)       # total occupancy shared by the two atoms
        self.enabled = bool(enabled)
        # Resolved (Atom, attr) pairs; None until resolve() runs. `_ref` holds
        # the stored [uuid, attr] pair.
        self.atom1: tuple | None = None
        self.atom2: tuple | None = None
        self._atom1_ref = None
        self._atom2_ref = None
        self.uuid = _uuid.uuid4().hex
        self.raw_properties: dict = {}

    @property
    def type(self) -> str:
        return "AtomRatio"

    @classmethod
    def from_dict(cls, data: dict) -> "AtomRatio":
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        r = cls(
            name=props.get("name", ""),
            value=props.get("value", 0.0),
            sum=props.get("sum", 1.0),
            enabled=bool(props.get("enabled", True)),
        )
        r.raw_properties = dict(props)
        r._atom1_ref = props.get("atom1")
        r._atom2_ref = props.get("atom2")
        if "uuid" in props:
            r.uuid = props["uuid"]
        return r

    def resolve(self, atom_map: dict) -> None:
        """Resolve the atom1 / atom2 [uuid, attr] references against a
        {uuid: Atom} map (call once every atom exists). A broken reference
        stays (None, attr) and is skipped when applying."""
        for ref, name in ((self._atom1_ref, "atom1"), (self._atom2_ref, "atom2")):
            if isinstance(ref, (list, tuple)) and len(ref) >= 2 and ref[0]:
                setattr(self, name, (atom_map.get(ref[0]), ref[1]))

    def apply_relation(self) -> None:
        """Set the two atoms' occupancy from the ratio: atom1 gets
        ``value * sum``, atom2 gets ``(1 - value) * sum``. A disabled relation
        or an unresolved atom is left alone."""
        if not self.enabled:
            return
        for frac, target in (
            (self.value, self.atom1),
            (1.0 - self.value, self.atom2),
        ):
            if target is not None and target[0] is not None:
                setattr(target[0], target[1], float(frac * self.sum))

    def _ref_of(self, target, stored):
        if target is not None and target[0] is not None:
            return [target[0].uuid, target[1]]
        return stored

    def to_dict(self) -> dict:
        """Serialize back to a .mud AtomRatio dict, overwriting the modeled
        fields on top of the verbatim raw properties (value_ref_info and uuid
        are preserved)."""
        props = dict(self.raw_properties)
        props["name"] = self.name
        props["value"] = self.value
        props["sum"] = self.sum
        props["enabled"] = self.enabled
        props["atom1"] = self._ref_of(self.atom1, self._atom1_ref)
        props["atom2"] = self._ref_of(self.atom2, self._atom2_ref)
        return {"type": "AtomRatio", "properties": props}
