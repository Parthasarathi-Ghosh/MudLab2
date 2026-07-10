"""Phase model for the pattern-calculation engine.

Ported from the old mudlab.phases.models.Phase (calc subset). A phase is a
stack of clay-layer components interstratified according to a layer-stacking
probability model, with a CSDS crystallite-size distribution and a sigma*
orientation factor. It produces one phase's diffracted intensity via
`calculations.phases.get_intensity`.

Only the regular "Phase" type is modeled (RawPatternPhase comes later). The
phase editor UI is wired with a later batch, so phases are still saved
verbatim (raw passthrough in the file parser); this model is load + calc.
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
        self.sigma_star = sigma_star
        self.apply_lpf = apply_lpf  # apply the Lorentz-polarisation factor
        self.apply_correction = True  # apply the machine correction range
        self.components: list[Component] = []
        self.CSDS = DritsCSDSDistribution()
        self.probabilities = probabilities_from_dict({}, G)
        # Full .mud phase dict kept verbatim so unmodeled fields (components,
        # probabilities, ref_info, display_color, based_on, inherit flags,
        # uuid) survive a load/save round-trip; to_dict writes the modeled
        # values (name, sigma*, CSDS mean) back into it.
        self.raw_properties: dict = {}

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
        props["sigma_star"] = self.sigma_star
        # Components are modeled: write the live list back (each preserves its
        # own unmodeled fields verbatim). Only when the phase actually has
        # component models, so a phase loaded without them stays untouched.
        if self.components:
            props["components"] = [c.to_dict() for c in self.components]
        csds = dict(props.get("CSDS_distribution") or {})
        csds.setdefault("type", "DritsCSDSDistribution")
        csds_props = dict(csds.get("properties") or {})
        csds_props["average"] = self.CSDS.average
        csds["properties"] = csds_props
        props["CSDS_distribution"] = csds
        # R0 stacking: write the (G-1) independent F variables back into the
        # probabilities dict (keeping its uuid / ref_info / inherit flags).
        f_params = getattr(self.probabilities, "f_params", None)
        probs = props.get("probabilities")
        if callable(f_params) and isinstance(probs, dict):
            probs = dict(probs)
            probs_props = dict(probs.get("properties") or {})
            for i, value in enumerate(f_params()):
                probs_props["F%d" % (i + 1)] = value
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
            phase.CSDS = DritsCSDSDistribution.from_dict(csds)

        phase.probabilities = probabilities_from_dict(
            props.get("probabilities") or {}, phase.G
        )
        if "uuid" in props:
            phase.uuid = props["uuid"]
        return phase
