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


class R1G2Probability:
    """Reichweite-1, 2-component stacking probabilities (old R1G2Model).

    R1 = each layer depends on the one immediately before it (nearest-
    neighbour ordering), so - unlike R0 - the rows of the junction matrix P
    differ. Two independent parameters:

    - ``W1``: the weight fraction of layer 1 (``W2 = 1 - W1``),
    - ``P11_or_P22``: the junction probability - ``P11`` when ``W1 <= 0.5``,
      else ``P22`` - the remaining P entries follow from detailed balance
      (old R1G2Model.update, ported verbatim below).

    Either parameter can be **inherited** from a based_on phase's model (old
    ``inherit_W1`` / ``inherit_P11_or_P22``), read through on demand exactly
    like R0's per-F inheritance, so a refined/edited parent is picked up at
    once. The matrix is still G×G (2×2), so the intensity summation consumes
    it unchanged (``rank == G``, ``reps == 1``).
    """

    def __init__(
        self,
        W1: float = 0.75,
        P11_or_P22: float = 0.5,
        inherit_W1: bool = False,
        inherit_P11_or_P22: bool = False,
    ) -> None:
        self.G = 2
        self.R = 1
        self.W1 = float(W1)
        self.P11_or_P22 = float(P11_or_P22)
        self.inherit_W1 = bool(inherit_W1)
        self.inherit_P11_or_P22 = bool(inherit_P11_or_P22)
        self.based_on_probs: "R1G2Probability | None" = None

    def set_based_on(self, parent_probs) -> None:
        """Point the inherited params at a based_on phase's probabilities."""
        self.based_on_probs = parent_probs if parent_probs is not self else None

    @property
    def n_independents(self) -> int:
        return 2  # W1 and P11_or_P22

    # -- effective (read-through) parameter values ---------------------
    def _inherited(self, attr: str) -> bool:
        flag = getattr(self, "inherit_" + attr)
        return bool(flag) and self.based_on_probs is not None

    def w1_value(self) -> float:
        """Effective W1, read through to the parent when inherited."""
        if self._inherited("W1"):
            return self.based_on_probs.w1_value()
        return self.W1

    def p11_value(self) -> float:
        """Effective P11_or_P22, read through to the parent when inherited."""
        if self._inherited("P11_or_P22"):
            return self.based_on_probs.p11_value()
        return self.P11_or_P22

    # -- W / P matrices (old R1G2Model.update) -------------------------
    def _weights(self) -> np.ndarray:
        w1 = self.w1_value()
        return np.array([w1, 1.0 - w1], dtype=float)

    def _pmatrix(self) -> np.ndarray:
        w1 = self.w1_value()
        w2 = 1.0 - w1
        p = self.p11_value()
        mP = np.zeros((2, 2), dtype=float)
        # Ported verbatim from R1G2Model.update: the free junction probability
        # is P11 for the minority-1 case and P22 otherwise; the other three
        # entries follow from row-stochasticity + detailed balance
        # (Wi*Pij = Wj*Pji).
        if w1 <= 0.5:
            mP[0, 0] = p
            mP[0, 1] = 1.0 - mP[0, 0]
            mP[1, 0] = (w1 * mP[0, 1] / w2) if w2 else 0.0
            mP[1, 1] = 1.0 - mP[1, 0]
        else:
            mP[1, 1] = p
            mP[1, 0] = 1.0 - mP[1, 1]
            mP[0, 1] = (w2 * mP[1, 0] / w1) if w1 else 0.0
            mP[0, 0] = 1.0 - mP[0, 1]
        return mP

    @property
    def valid(self) -> bool:
        mW = self._weights()
        if np.any(mW < 0.0) or np.any(mW > 1.0) or not np.isclose(np.sum(mW), 1.0):
            return False
        mP = self._pmatrix()
        if np.any(mP < 0.0) or np.any(mP > 1.0):
            return False
        return bool(np.allclose(np.sum(mP, axis=1), 1.0))

    def get_distribution_matrix(self) -> np.ndarray:
        return np.diag(self._weights())

    def get_distribution_array(self) -> np.ndarray:
        return self._weights()

    def get_probability_matrix(self) -> np.ndarray:
        return self._pmatrix()

    @classmethod
    def from_dict(cls, data: dict, G: int = 2) -> "R1G2Probability":
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        return cls(
            W1=props.get("W1", 0.75),
            P11_or_P22=props.get("P11_or_P22", 0.5),
            inherit_W1=bool(props.get("inherit_W1", False)),
            inherit_P11_or_P22=bool(props.get("inherit_P11_or_P22", False)),
        )


def probabilities_from_dict(data: dict, G: int):
    """Build a probability model from a .mud probabilities dict.

    Dispatches on the stored type string. R0 (any G) and R1G2 are modeled;
    other higher-R types are not ported yet and fall back to R0 - which
    silently mis-models them, so a project using an unported type must be
    caught before this point (there is no fixture for one yet)."""
    prob_type = data.get("type", "") if isinstance(data, dict) else ""
    if prob_type == "R1G2Model":
        return R1G2Probability.from_dict(data, G)
    if prob_type.startswith("R0G"):
        return R0Probability.from_dict(data, G)
    # Fallback: treat as R0 (independent) until higher-R models are ported.
    return R0Probability.from_dict(data, G)
