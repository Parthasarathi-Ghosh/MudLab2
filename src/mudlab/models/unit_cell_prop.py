"""Unit-cell property (UCP) model - a component's cell length a or b.

Ported from the old mudlab.phases.models.unit_cell_prop.UnitCellProperty
(calc subset). A UCP is either:

- **fixed** (``enabled=False``): the user types the cell length directly, or
- **derived** (``enabled=True``): ``value = factor * <prop> + constant``, where
  ``prop`` references another property by uuid - typically the same
  component's ``cell_b`` (so ``cell_a = 0.57735 * cell_b``, a = b/sqrt(3)) or
  an octahedral cation's ``pn`` (the b-cell <-> iron-content relationship).

IMPORTANT (golden-calc safety): the .mud stores a resolved ``value`` that can
be **stale** (``factor*prop+constant`` does not always reproduce it), and the
old app's stored calculated pattern was computed from those stored values. So
this model keeps the stored ``value`` on load and only recomputes it
(``update_value``) when the user edits the derivation in the UCP editor. It is
NOT recomputed at load time.
"""

from __future__ import annotations

import uuid as _uuid


class UnitCellProperty:
    def __init__(
        self,
        name: str = "",
        value: float = 0.0,
        enabled: bool = False,
        factor: float = 1.0,
        constant: float = 0.0,
    ) -> None:
        self.name = name          # display only (old app: not persisted)
        self.value = float(value)  # the resolved cell length (nm)
        self.enabled = bool(enabled)
        self.factor = float(factor)
        self.constant = float(constant)
        # Derivation source: a resolved (object, attr) tuple once linked, or
        # None. `_prop_ref` holds the stored [uuid, attr] until resolve_prop.
        self.prop: tuple | None = None
        self._prop_ref = None
        self._prop_dirty = False  # True once the editor rewrites the prop ref
        self.uuid = _uuid.uuid4().hex  # overwritten from the .mud on load
        # Verbatim .mud UCP dict so unmodeled fields (uuid, value_ref_info,
        # the prop reference) survive a round-trip.
        self.raw_properties: dict = {}

    @classmethod
    def from_dict(cls, data: dict) -> "UnitCellProperty":
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        ucp = cls(
            value=props.get("value", 0.0),
            enabled=bool(props.get("enabled", False)),
            factor=props.get("factor", 1.0),
            constant=props.get("constant", 0.0),
        )
        ucp.raw_properties = dict(props)
        ucp._prop_ref = props.get("prop")  # [uuid, attr] or None
        if "uuid" in props:
            ucp.uuid = props["uuid"]
        return ucp

    def resolve_prop(self, object_map: dict) -> None:
        """Resolve the stored [uuid, attr] derivation source against a
        project-wide {uuid: object} map (components + atoms). Call after all
        components/atoms exist. A broken/missing reference stays unresolved
        (prop = None), so update_value leaves the value untouched."""
        ref = self._prop_ref
        if isinstance(ref, (list, tuple)) and len(ref) >= 2 and ref[0]:
            obj = object_map.get(ref[0])
            if obj is not None:
                self.prop = (obj, ref[1])

    def set_prop(self, obj, attr) -> None:
        """Point the derivation at a new source (an atom's pn, or a cell). Marks
        the reference dirty so to_dict rewrites the [uuid, attr] pair."""
        if obj is None:
            self.prop = None
            self._prop_ref = None
        else:
            self.prop = (obj, attr)
            self._prop_ref = [obj.uuid, attr]
        self._prop_dirty = True

    def get_prop_value(self) -> float:
        if self.prop is not None:
            obj, attr = self.prop
            try:
                return float(getattr(obj, attr))
            except (AttributeError, TypeError, ValueError):
                return 0.0
        return 0.0

    def update_value(self) -> None:
        """Recompute the derived value (only when enabled AND the derivation
        source is resolved). A fixed UCP keeps its user-set value; an enabled
        UCP with an unresolved prop is left untouched (cannot compute)."""
        if self.enabled and self.prop is not None:
            self.value = float(self.factor * self.get_prop_value() + self.constant)

    def to_dict(self) -> dict:
        """Serialize back to a .mud UCP dict, overwriting the modeled fields
        (value/enabled/factor/constant) on top of the verbatim raw properties.
        The prop reference, uuid and value_ref_info are preserved verbatim (the
        editor rewrites prop when the derivation source changes)."""
        props = dict(self.raw_properties)
        props["uuid"] = self.uuid  # persist identity (new UCPs would lose it)
        props["value"] = self.value
        props["enabled"] = self.enabled
        props["factor"] = self.factor
        props["constant"] = self.constant
        # The prop reference is kept verbatim unless the editor changed it (so
        # an unedited UCP round-trips byte-for-byte, incl. an absent prop key).
        if self._prop_dirty:
            props["prop"] = self._prop_ref
        return {"type": "UnitCellProperty", "properties": props}
