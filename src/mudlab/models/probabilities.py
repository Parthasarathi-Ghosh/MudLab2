"""Layer-stacking probability models.

Ported from the old mudlab.probabilities. Only Reichweite-0 (R0) models
are implemented so far - independent/random stacking, which is what the
sample projects use (R0G1..R0G6). Higher Reichweite (R1-R3 Markovian
models) are ported when a project needs them.

An R0 model has (G-1) independent F parameters and produces:
- W: the g×g diagonal weight-fraction matrix (Wii = fraction of layer i),
- P: the g×g transition matrix where Pij = Wj (stacking is independent).
"""

from __future__ import annotations

import numpy as np


class R0Probability:
    """Reichweite-0 stacking probabilities for G components.

    An F parameter can be **inherited** from a `based_on` phase's probability
    model (old `inherit_F<i>` flags): the child stores its own - often stale -
    F value but reads the parent's. This is load-bearing for the calculated
    pattern: in a refined multi-treatment project the parent's refined F is the
    one that must be used (see the phase-inheritance notes in ui/WIRING.md).

    W and P are therefore derived on demand from the EFFECTIVE F values, so a
    change to the parent (an edit or a refinement step) is picked up at once.
    """

    def __init__(
        self,
        G: int,
        f_params: list[float] | None = None,
        inherit_f: list[bool] | None = None,
    ) -> None:
        self.G = G
        self.R = 0
        # (G-1) independent variables Fi = Wi / sum(Wi..Wg); default 0.8.
        self.F = list(f_params or [])
        # Per-F inherit flags + the based_on phase's probability model.
        self.inherit_F = list(inherit_f or [])
        self.based_on_probs: "R0Probability | None" = None

    def set_based_on(self, parent_probs) -> None:
        """Point the inherited F params at a based_on phase's probabilities."""
        self.based_on_probs = parent_probs if parent_probs is not self else None

    # ------------------------------------------------------------------
    @property
    def n_independents(self) -> int:
        """Number of independent F parameters = G - 1."""
        return max(self.G - 1, 0)

    def is_f_inherited(self, index: int) -> bool:
        """True when Fi reads through to the based_on phase's model."""
        inherited = index < len(self.inherit_F) and bool(self.inherit_F[index])
        return inherited and self.based_on_probs is not None

    def own_f_value(self, index: int) -> float:
        """This model's OWN stored Fi (what gets serialised), ignoring
        inheritance - may be stale when Fi is inherited."""
        return self.F[index] if index < len(self.F) else 0.8

    def own_f_params(self) -> list[float]:
        return [self.own_f_value(i) for i in range(self.n_independents)]

    def f_value(self, index: int) -> float:
        """The EFFECTIVE i-th independent variable Fi = Wi / sum(Wi..Wg),
        read through to the based_on model when inherited."""
        if self.is_f_inherited(index):
            return self.based_on_probs.f_value(index)
        return self.own_f_value(index)

    def f_params(self) -> list[float]:
        return [self.f_value(i) for i in range(self.n_independents)]

    def set_f(self, index: int, value: float) -> None:
        """Update this model's own i-th independent variable."""
        while len(self.F) <= index:
            self.F.append(0.8)
        self.F[index] = float(value)

    # ------------------------------------------------------------------
    def _weights(self) -> np.ndarray:
        """The g-vector of weight fractions, derived from the EFFECTIVE F
        params (so an inherited F follows its parent)."""
        G = self.G
        mW = np.zeros(G, dtype=float)
        if G > 1:
            for i in range(G - 1):
                f = self.f_value(i)
                if i > 0:
                    mW[i] = f * (1.0 - np.sum(mW[0:i]))
                else:
                    mW[0] = f
            mW[G - 1] = 1.0 - np.sum(mW[:-1])
        else:
            mW[0] = 1.0
        return mW

    @property
    def valid(self) -> bool:
        """Whether W and P are valid (old phase.valid_probs = all W_valid and
        all P_valid). For R0 that means the weight fractions lie in [0, 1] and
        sum to 1, and every P row is stochastic."""
        mW = self._weights()
        if np.any(mW < 0.0) or np.any(mW > 1.0):
            return False
        if not np.isclose(np.sum(mW), 1.0):
            return False
        return bool(np.allclose(np.sum(np.tile(mW, (self.G, 1)), axis=1), 1.0))

    def get_distribution_matrix(self) -> np.ndarray:
        return np.diag(self._weights())

    def get_distribution_array(self) -> np.ndarray:
        return self._weights()

    def get_probability_matrix(self) -> np.ndarray:
        # Independent stacking: every row of P is the weight-fraction vector.
        return np.tile(self._weights(), (self.G, 1))

    @classmethod
    def from_dict(cls, data: dict, G: int) -> "R0Probability":
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        # F params are stored 1-based (F1, F2, ...); (G-1) of them, each with
        # an optional inherit_F<i> flag (set when the phase is based_on another).
        f_params = [props.get("F%d" % (i + 1), 0.8) for i in range(G - 1)]
        inherit_f = [
            bool(props.get("inherit_F%d" % (i + 1), False)) for i in range(G - 1)
        ]
        return cls(G, f_params, inherit_f)


def probabilities_from_dict(data: dict, G: int):
    """Build a probability model from a .mud probabilities dict. Only R0
    (type 'R0G<g>Model') is supported so far."""
    prob_type = data.get("type", "") if isinstance(data, dict) else ""
    if prob_type.startswith("R0G"):
        return R0Probability.from_dict(data, G)
    # Fallback: treat as R0 (independent) until higher-R models are ported.
    return R0Probability.from_dict(data, G)
