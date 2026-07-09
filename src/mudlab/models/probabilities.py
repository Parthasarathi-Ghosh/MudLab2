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
    """Reichweite-0 stacking probabilities for G components."""

    def __init__(self, G: int, f_params: list[float] | None = None) -> None:
        self.G = G
        self.R = 0
        # (G-1) independent variables Fi = Wi / sum(Wi..Wg); default 0.8.
        self.F = list(f_params or [])
        self._update()

    def _update(self) -> None:
        G = self.G
        mW = np.zeros(G, dtype=float)
        if G > 1:
            for i in range(G - 1):
                f = self.F[i] if i < len(self.F) else 0.8
                if i > 0:
                    mW[i] = f * (1.0 - np.sum(mW[0:i]))
                else:
                    mW[0] = f
            mW[G - 1] = 1.0 - np.sum(mW[:-1])
        else:
            mW[0] = 1.0
        self._W = np.diag(mW)
        # Independent stacking: every row of P is the weight-fraction vector.
        self._P = np.tile(mW, (G, 1))

    def get_distribution_matrix(self) -> np.ndarray:
        return self._W

    def get_distribution_array(self) -> np.ndarray:
        return np.diag(self._W)

    def get_probability_matrix(self) -> np.ndarray:
        return self._P

    @classmethod
    def from_dict(cls, data: dict, G: int) -> "R0Probability":
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        # F params are stored 1-based (F1, F2, ...); (G-1) of them.
        f_params = [props.get("F%d" % (i + 1), 0.8) for i in range(G - 1)]
        return cls(G, f_params)


def probabilities_from_dict(data: dict, G: int):
    """Build a probability model from a .mud probabilities dict. Only R0
    (type 'R0G<g>Model') is supported so far."""
    prob_type = data.get("type", "") if isinstance(data, dict) else ""
    if prob_type.startswith("R0G"):
        return R0Probability.from_dict(data, G)
    # Fallback: treat as R0 (independent) until higher-R models are ported.
    return R0Probability.from_dict(data, G)
