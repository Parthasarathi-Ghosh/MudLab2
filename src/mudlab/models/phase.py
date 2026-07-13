"""Phase model for the pattern-calculation engine.

Ported from the old mudlab.phases.models.Phase (calc subset). A phase is a
stack of clay-layer components interstratified according to a layer-stacking
probability model, with a CSDS crystallite-size distribution and a sigma*
orientation factor. It produces one phase's diffracted intensity via
`calculations.phases.get_intensity`.

Only the regular "Phase" type is modeled (RawPatternPhase comes later). The
Edit Phases dialog binds this model, so the modeled fields (name, sigma*,
CSDS mean, R0 F params, components) save via to_dict while everything else
round-trips verbatim through raw_properties.
"""

from __future__ import annotations

import uuid as _uuid

from mudlab.models.component import Component
from mudlab.models.csds import DritsCSDSDistribution
from mudlab.models.probabilities import probabilities_from_dict


class Phase:
    """One diffracting clay phase (calc subset of the old Phase model)."""

    def __init__(
        self,
        name: str = "",
        G: int = 1,
        sigma_star: float = 3.0,
        apply_lpf: bool = True,
    ) -> None:
        self.type = "Phase"
        self.uuid = _uuid.uuid4().hex
        self.name = name
        self.G = G
        self.apply_lpf = apply_lpf  # apply the Lorentz-polarisation factor
        self.apply_correction = True  # apply the machine correction range
        self.components: list[Component] = []
        # Phase-level inheritance (old based_on): a treated phase (glycolated /
        # heated) is "based on" a reference phase and inherits its
        # treatment-independent parameters. Resolved from _based_on_uuid once
        # every phase is loaded (mud_project.load_mud).
        self.based_on: "Phase | None" = None
        self._based_on_uuid = ""
        self.inherit_sigma_star = False
        self.inherit_CSDS_distribution = False
        self.inherit_display_color = False
        # Own values (overlaid by the read-through getters below).
        self._sigma_star = sigma_star
        self._CSDS = DritsCSDSDistribution()
        self.probabilities = probabilities_from_dict({}, G)
        # Full .mud phase dict kept verbatim so unmodeled fields (components,
        # probabilities, ref_info, display_color, based_on, inherit flags,
        # uuid) survive a load/save round-trip; to_dict writes the modeled
        # values (name, sigma*, CSDS mean) back into it.
        self.raw_properties: dict = {}

    # ------------------------------------------------------------------
    # Phase-level inheritance (based_on)
    # ------------------------------------------------------------------
    def resolve_based_on(self, phase_map: dict) -> None:
        """Resolve based_on from the stored uuid against a {uuid: Phase} map,
        and point this phase's inherited F params at the parent's probability
        model. Call once every phase is loaded."""
        if not self._based_on_uuid:
            return
        parent = phase_map.get(self._based_on_uuid)
        if parent is None or parent is self:
            return
        # Refuse a cycle (walk the parent's chain; old get_based_on_root).
        node, seen = parent, set()
        while node is not None and id(node) not in seen:
            if node is self:
                return
            seen.add(id(node))
            node = node.based_on
        self.based_on = parent
        self.probabilities.set_based_on(parent.probabilities)

    def is_inherited(self, attr: str) -> bool:
        """True when `attr` reads through to the based_on phase (so it is not
        independently editable / refinable here)."""
        flag = {
            "sigma_star": self.inherit_sigma_star,
            "CSDS": self.inherit_CSDS_distribution,
        }.get(attr, False)
        return bool(flag) and self.based_on is not None and self.based_on is not self

    def _resolved(self, attr: str):
        """Walk the based_on chain to the phase that does NOT inherit `attr`
        and return its own value (iterative + cycle-guarded)."""
        node, seen = self, set()
        while node.is_inherited(attr) and id(node) not in seen:
            seen.add(id(node))
            node = node.based_on
        return getattr(node, "_" + attr)

    @property
    def sigma_star(self) -> float:
        return self._resolved("sigma_star")

    @sigma_star.setter
    def sigma_star(self, value) -> None:
        self._sigma_star = float(value)

    @property
    def CSDS(self):
        return self._resolved("CSDS")

    @CSDS.setter
    def CSDS(self, value) -> None:
        self._CSDS = value

    # Stacking probability matrices (independent stacking for R0). ------
    @property
    def valid_probs(self) -> bool:
        return self.probabilities.valid

    @property
    def W(self):
        """The g×g diagonal weight-fraction matrix."""
        return self.probabilities.get_distribution_matrix()

    @property
    def P(self):
        """The g×g layer-to-layer transition-probability matrix."""
        return self.probabilities.get_probability_matrix()

    # ------------------------------------------------------------------
    def get_intensity(self, range_theta, range_stl, soller1, soller2, mcr_2theta):
        """This phase's diffracted intensity (with the LP factor) over the
        given 2θ / 2·sin(θ)/λ ranges."""
        from mudlab.calculations.phases import get_intensity

        return get_intensity(
            range_theta, range_stl, soller1, soller2, mcr_2theta, self
        )

    def to_dict(self) -> dict:
        """Serialize back to a .mud phase dict, overwriting only the modeled
        fields (name, sigma*, CSDS mean) on top of the verbatim raw
        properties. The CSDS mean is nested in CSDS_distribution.properties,
        whose other keys (uuid, average_ref_info) are preserved."""
        props = dict(self.raw_properties)
        props["name"] = self.name
        # OWN values, never the inherited read-through ones, so a based_on
        # child round-trips byte-identically (it may store a stale value).
        props["sigma_star"] = self._sigma_star
        # Components are modeled: write the live list back (each preserves its
        # own unmodeled fields verbatim). Only when the phase actually has
        # component models, so a phase loaded without them stays untouched.
        if self.components:
            props["components"] = [c.to_dict() for c in self.components]
        csds = dict(props.get("CSDS_distribution") or {})
        csds.setdefault("type", "DritsCSDSDistribution")
        csds_props = dict(csds.get("properties") or {})
        csds_props["average"] = self._CSDS.average
        csds["properties"] = csds_props
        props["CSDS_distribution"] = csds
        # Phase-level inheritance state.
        props["based_on_uuid"] = (
            self.based_on.uuid if self.based_on is not None else self._based_on_uuid
        )
        props["inherit_sigma_star"] = self.inherit_sigma_star
        props["inherit_CSDS_distribution"] = self.inherit_CSDS_distribution
        props["inherit_display_color"] = self.inherit_display_color
        # R0 stacking: write the (G-1) independent F variables back into the
        # probabilities dict (keeping its uuid / ref_info). Own values again -
        # an inherited F keeps its stored (stale) number, as the old app does.
        own_f = getattr(self.probabilities, "own_f_params", None)
        probs = props.get("probabilities")
        if callable(own_f) and isinstance(probs, dict):
            probs = dict(probs)
            probs_props = dict(probs.get("properties") or {})
            for i, value in enumerate(own_f()):
                probs_props["F%d" % (i + 1)] = value
                probs_props["inherit_F%d" % (i + 1)] = bool(
                    self.probabilities.inherit_F[i]
                    if i < len(self.probabilities.inherit_F) else False
                )
            probs["properties"] = probs_props
            props["probabilities"] = probs
        return {"type": "Phase", "properties": props}

    @classmethod
    def from_dict(cls, data: dict, atom_type_map: dict) -> "Phase":
        props = data.get("properties", {})
        phase = cls(
            name=props.get("name", ""),
            G=int(props.get("G", 1)),
            sigma_star=props.get("sigma_star", 3.0),
        )
        phase.raw_properties = dict(props)
        phase.components = [
            Component.from_dict(c, atom_type_map)
            for c in (props.get("components") or [])
            if isinstance(c, dict)
        ]
        # The old Phase.G is the number of components; keep them in step.
        if phase.components:
            phase.G = len(phase.components)

        csds = props.get("CSDS_distribution")
        if isinstance(csds, dict):
            phase._CSDS = DritsCSDSDistribution.from_dict(csds)

        phase.probabilities = probabilities_from_dict(
            props.get("probabilities") or {}, phase.G
        )
        if "uuid" in props:
            phase.uuid = props["uuid"]
        # Phase-level inheritance: based_on is resolved once every phase exists
        # (see mud_project.load_mud); the flags gate the read-through.
        phase._based_on_uuid = props.get("based_on_uuid", "") or ""
        phase.inherit_sigma_star = bool(props.get("inherit_sigma_star", False))
        phase.inherit_CSDS_distribution = bool(
            props.get("inherit_CSDS_distribution", False)
        )
        phase.inherit_display_color = bool(props.get("inherit_display_color", False))
        return phase
