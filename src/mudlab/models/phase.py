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
        self.name = name
        self.G = G
        self.sigma_star = sigma_star
        self.apply_lpf = apply_lpf  # apply the Lorentz-polarisation factor
        self.components: list[Component] = []
        self.CSDS = DritsCSDSDistribution()
        self.probabilities = probabilities_from_dict({}, G)

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

    @classmethod
    def from_dict(cls, data: dict, atom_type_map: dict) -> "Phase":
        props = data.get("properties", {})
        phase = cls(
            name=props.get("name", ""),
            G=int(props.get("G", 1)),
            sigma_star=props.get("sigma_star", 3.0),
        )
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
        return phase
