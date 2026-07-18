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

    # -- serialization / inheritance (used by Phase.to_dict / set_based_on) --
    def write_properties(self, props: dict) -> dict:
        """Write the OWN F values + per-F inherit flags into a probabilities
        properties dict, preserving its other keys (uuid, ref_info). Own (not
        read-through) values, so a based_on child round-trips byte-identically
        and keeps its stored stale F - as the old app does."""
        props = dict(props)
        for i in range(self.n_independents):
            props["F%d" % (i + 1)] = self.own_f_value(i)
            props["inherit_F%d" % (i + 1)] = bool(
                self.inherit_F[i] if i < len(self.inherit_F) else False
            )
        return props

    def clear_inheritance(self) -> None:
        """Drop every inherit flag (old detach: a phase no longer based_on
        anything inherits nothing)."""
        self.inherit_F = [False for _ in range(self.n_independents)]

    @property
    def type_name(self) -> str:
        """The .mud store id (old R0G<g>Model), used when a newly created
        phase has no stored probabilities dict yet."""
        return "R0G%dModel" % self.G

    def refinable_params(self) -> list:
        """The independent parameters exposed to the refiner, model-agnostic:
        (label, getter, setter, ref_info_key, default_bounds, inherited). An
        inherited parameter is flagged so the caller skips it (refining a
        read-through value is a no-op)."""
        out = []
        for i in range(self.n_independents):
            out.append((
                "F%d" % (i + 1),
                (lambda i=i: self.f_value(i)),
                (lambda v, i=i: self.set_f(i, v)),
                "F%d_ref_info" % (i + 1),
                (0.0, 1.0),
                self.is_f_inherited(i),
            ))
        return out

    def _set_f_inherited(self, index: int, value: bool) -> None:
        while len(self.inherit_F) <= index:
            self.inherit_F.append(False)
        self.inherit_F[index] = bool(value)

    def editable_params(self) -> list:
        """Descriptors for the probabilities editor, model-agnostic. Each is a
        dict: label, tooltip, get (effective value), set (own value),
        inherited (bool), set_inherited, inherit_tooltip. The editor builds one
        spin + Inherit checkbox per entry and shows the derived W/P below."""
        out = []
        for i in range(self.n_independents):
            out.append({
                "label": "F%d" % (i + 1),
                "tooltip": "W%d / sum(W%d..W%d)" % (i + 1, i + 1, self.G),
                "get": (lambda i=i: self.f_value(i)),
                "set": (lambda v, i=i: self.set_f(i, v)),
                "inherited": self.is_f_inherited(i),
                "set_inherited": (lambda b, i=i: self._set_f_inherited(i, b)),
                "inherit_tooltip": 'Take F%d from the "based on" phase.' % (i + 1),
            })
        return out

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

    # -- serialization / inheritance (same contract as R0Probability) --
    def write_properties(self, props: dict) -> dict:
        """Write the OWN W1 / P11_or_P22 + their inherit flags into a
        probabilities properties dict, preserving its other keys (uuid,
        ref_info). Own (not read-through) values, so an inherited child
        round-trips byte-identically and keeps its stored stale value."""
        props = dict(props)
        props["W1"] = self.W1
        props["P11_or_P22"] = self.P11_or_P22
        props["inherit_W1"] = bool(self.inherit_W1)
        props["inherit_P11_or_P22"] = bool(self.inherit_P11_or_P22)
        return props

    def clear_inheritance(self) -> None:
        self.inherit_W1 = False
        self.inherit_P11_or_P22 = False

    @property
    def type_name(self) -> str:
        return "R1G2Model"

    def refinable_params(self) -> list:
        """Same contract as R0Probability.refinable_params. The setter writes
        the OWN value; only non-inherited params are refined (the caller skips
        the inherited ones), so own == effective there."""
        return [
            (
                "W1",
                (lambda: self.w1_value()),
                (lambda v: setattr(self, "W1", float(v))),
                "W1_ref_info",
                (0.0, 1.0),
                self._inherited("W1"),
            ),
            (
                "P11_or_P22",
                (lambda: self.p11_value()),
                (lambda v: setattr(self, "P11_or_P22", float(v))),
                "P11_or_P22_ref_info",
                (0.0, 1.0),
                self._inherited("P11_or_P22"),
            ),
        ]

    def editable_params(self) -> list:
        """Descriptors for the probabilities editor (see R0Probability). Two
        rows: W1 and the free junction probability P11/P22."""
        return [
            {
                "label": "W1",
                "tooltip": "Weight fraction of layer 1 (W2 = 1 - W1).",
                "get": (lambda: self.w1_value()),
                "set": (lambda v: setattr(self, "W1", float(v))),
                "inherited": self._inherited("W1"),
                "set_inherited": (
                    lambda b: setattr(self, "inherit_W1", bool(b))),
                "inherit_tooltip": 'Take W1 from the "based on" phase.',
            },
            {
                "label": "P11 / P22",
                "tooltip": "Junction probability: P11 when W1 <= 0.5, else P22 "
                           "(the other entries follow from detailed balance).",
                "get": (lambda: self.p11_value()),
                "set": (lambda v: setattr(self, "P11_or_P22", float(v))),
                "inherited": self._inherited("P11_or_P22"),
                "set_inherited": (
                    lambda b: setattr(self, "inherit_P11_or_P22", bool(b))),
                "inherit_tooltip": 'Take P11/P22 from the "based on" phase.',
            },
        ]

    @classmethod
    def from_dict(cls, data: dict, G: int = 2) -> "R1G2Probability":
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        return cls(
            W1=props.get("W1", 0.75),
            P11_or_P22=props.get("P11_or_P22", 0.5),
            inherit_W1=bool(props.get("inherit_W1", False)),
            inherit_P11_or_P22=bool(props.get("inherit_P11_or_P22", False)),
        )


# Per-parameter inheritance is the same shape for every higher-R model (a set
# of named float params, each with an inherit_<name> flag that reads through to
# a based_on model), so it is factored out here. Each model lists its own
# PARAMS (name, default) and implements _matrices() (its update() port).
class _MarkovProbability:
    """Shared base for the multi-parameter Markovian (R>=1) models. Subclasses
    set G, R and PARAMS, and implement _matrices() -> (W, P). Everything else -
    read-through inheritance, validity, serialization, the editor/refiner
    descriptors - is generic over PARAMS."""

    G = 2
    R = 1
    PARAMS: tuple = ()   # ((name, default, label, tooltip), ...)

    def __init__(self, **values) -> None:
        self.based_on_probs = None
        for name, default, _label, _tip in self.PARAMS:
            setattr(self, name, float(values.get(name, default)))
            setattr(self, "inherit_" + name,
                    bool(values.get("inherit_" + name, False)))

    # -- inheritance ---------------------------------------------------
    def set_based_on(self, parent_probs) -> None:
        self.based_on_probs = parent_probs if parent_probs is not self else None

    def _inherited(self, name: str) -> bool:
        return (bool(getattr(self, "inherit_" + name))
                and self.based_on_probs is not None)

    def value(self, name: str) -> float:
        """Effective value of a parameter, read through to the based_on model
        when inherited."""
        if self._inherited(name):
            return self.based_on_probs.value(name)
        return float(getattr(self, name))

    def clear_inheritance(self) -> None:
        for name, *_ in self.PARAMS:
            setattr(self, "inherit_" + name, False)

    @property
    def n_independents(self) -> int:
        return len(self.PARAMS)

    # -- matrices (subclass ports update()) ----------------------------
    def _matrices(self):
        raise NotImplementedError

    @property
    def valid(self) -> bool:
        W, P = self._matrices()
        w = np.diag(W)
        if np.any(w < -1e-9) or np.any(w > 1.0 + 1e-9) or not np.isclose(w.sum(), 1.0):
            return False
        if np.any(P < -1e-9) or np.any(P > 1.0 + 1e-9):
            return False
        # P rows must be stochastic only for states with nonzero weight: a
        # zero-weight state never occurs in the stack (its row is multiplied by
        # 0 in the intensity sum), so its transitions are unconstrained and may
        # legitimately be all-zero (e.g. the forbidden pair-states in R2G3).
        active = w > 1e-9
        return bool(np.allclose(P[active].sum(axis=1), 1.0))

    def get_distribution_matrix(self) -> np.ndarray:
        return self._matrices()[0]

    def get_distribution_array(self) -> np.ndarray:
        return np.diag(self._matrices()[0])

    def get_probability_matrix(self) -> np.ndarray:
        return self._matrices()[1]

    # -- serialization / descriptors (generic over PARAMS) -------------
    def write_properties(self, props: dict) -> dict:
        props = dict(props)
        for name, *_ in self.PARAMS:
            props[name] = float(getattr(self, name))          # OWN value
            props["inherit_" + name] = bool(getattr(self, "inherit_" + name))
        return props

    def refinable_params(self) -> list:
        out = []
        for name, _default, label, _tip in self.PARAMS:
            out.append((
                label,
                (lambda n=name: self.value(n)),
                (lambda v, n=name: setattr(self, n, float(v))),
                "%s_ref_info" % name,
                (0.0, 1.0),
                self._inherited(name),
            ))
        return out

    def editable_params(self) -> list:
        out = []
        for name, _default, label, tip in self.PARAMS:
            out.append({
                "label": label,
                "tooltip": tip,
                "get": (lambda n=name: self.value(n)),
                "set": (lambda v, n=name: setattr(self, n, float(v))),
                "inherited": self._inherited(name),
                "set_inherited": (
                    lambda b, n=name: setattr(self, "inherit_" + n, bool(b))),
                "inherit_tooltip": 'Take %s from the "based on" phase.' % label,
            })
        return out

    @classmethod
    def from_dict(cls, data: dict, G: int = None):
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        kwargs = {}
        for name, default, *_ in cls.PARAMS:
            kwargs[name] = props.get(name, default)
            kwargs["inherit_" + name] = bool(props.get("inherit_" + name, False))
        return cls(**kwargs)


class R2G2Probability(_MarkovProbability):
    """Reichweite-2, 2-component stacking (old R2G2Model). The state is a PAIR
    of layers, so W and P are g²×g² = 4×4 (the calc's reps = 4//2 = 2 path).
    Four independent parameters; the other pair-weights and 3-layer junction
    probabilities follow from detailed balance (ported verbatim from
    R2G2Model.update)."""

    G = 2
    R = 2
    _TWOTHIRDS = 2.0 / 3.0
    PARAMS = (
        ("W1", 0.75, "W1", "Weight fraction of layer 1 (> 0.5)."),
        ("P112_or_P211", 0.75, "P112 / P211",
         "Junction P112 when W1 <= 2/3, else P211."),
        ("P21", 0.75, "P21", "Two-layer junction probability P21."),
        ("P122_or_P221", 0.75, "P122 / P221",
         "Junction P122 when P21 <= 1/2, else P221."),
    )
    #: .mud state order for the 4 pair-states is x = 2*i + j:
    #: 0=(0,0) 1=(0,1) 2=(1,0) 3=(1,1).
    type_name = "R2G2Model"

    def _matrices(self):
        W1 = self.value("W1")
        P21 = self.value("P21")
        P112_or_P211 = self.value("P112_or_P211")
        P122_or_P221 = self.value("P122_or_P221")
        W2 = 1.0 - W1
        P22 = 1.0 - P21
        # Pair weights (mW[i,j]).
        W10 = W2 * P21
        W11 = W2 * P22
        W01 = W10
        W00 = W1 - W10
        # First triplet: P00x / P10x (the free one is P112 or P211 by W1).
        if W1 <= self._TWOTHIRDS:
            P001 = P112_or_P211
            P100 = (P001 * W00 / W10) if W10 != 0.0 else 0.0
        else:
            P100 = P112_or_P211
            P001 = (P100 * W10 / W00) if W00 != 0.0 else 0.0
        P101 = 1.0 - P100
        P000 = 1.0 - P001
        # Second triplet: P01x / P11x (the free one is P122 or P221 by P21).
        if P21 <= 0.5:
            P011 = P122_or_P221
            P110 = (P011 * W01 / W11) if W11 != 0.0 else 0.0
        else:
            P110 = P122_or_P221
            P011 = (P110 * W11 / W01) if W01 != 0.0 else 0.0
        P010 = 1.0 - P011
        P111 = 1.0 - P110
        # W is the 4x4 diagonal of pair weights; P[2i+j, 2j+k] = P_ijk, else 0.
        W = np.diag([W00, W01, W10, W11])
        P = np.array([
            [P000, P001, 0.0,  0.0],
            [0.0,  0.0,  P010, P011],
            [P100, P101, 0.0,  0.0],
            [0.0,  0.0,  P110, P111],
        ], dtype=float)
        return W, P


class R3G2Probability(_MarkovProbability):
    """Reichweite-3, 2-component stacking (old R3G2Model). The state is a
    TRIPLET of layers, so W and P are g³×g³ = 8×8 (the calc's reps = 8//2 = 4).
    Two independent parameters (W1 constrained > 2/3 so the (0,0,0) triplet
    weight 3*W1-2 stays >= 0); most junctions are forced (a 1-1 pair cannot be
    followed by another 1 - illite has no such stacking), leaving only the
    (0,0,0)->(0,0,x) / (1,0,0)->(0,0,x) block free (ported from
    R3G2Model.update)."""

    G = 2
    R = 3
    PARAMS = (
        ("W1", 0.85, "W1", "Weight fraction of layer 1 (> 2/3)."),
        ("P1111_or_P2112", 0.75, "P1111 / P2112",
         "Junction P1111 when W1 <= 3/4, else P2112."),
    )
    type_name = "R3G2Model"

    def _matrices(self):
        W1 = self.value("W1")
        P = self.value("P1111_or_P2112")
        W2 = 1.0 - W1

        def clamp(x):
            return max(min(x, 1.0), 0.0)

        # Free block: (0,0,0)->(0,0,x) and (1,0,0)->(0,0,x).
        if W1 <= 0.75:  # P0000 (=P1111) is given
            P0000 = P
            P0001 = clamp(1.0 - P0000)
            P1000 = clamp(P0001 * (W1 - 2.0 * W2) / W2) if W2 != 0 else 0.0
            P1001 = clamp(1.0 - P1000)
        else:  # P1001 (=P2112) is given
            P1001 = P
            P1000 = clamp(1.0 - P1001)
            denom = W1 - 2.0 * W2  # = 3*W1 - 2
            P0000 = clamp(1.0 - P1000 * W2 / denom) if denom != 0 else 0.0
            P0001 = clamp(1.0 - P0000)

        # Triplet weights (mW[i,j,k]); state x = 4i + 2j + k.
        w000 = clamp(3.0 * W1 - 2.0)
        w_edge = clamp(1.0 - W1)  # (0,0,1) (0,1,0) (1,0,0)
        W = np.diag([w000, w_edge, w_edge, 0.0, w_edge, 0.0, 0.0, 0.0])

        # P[4i+2j+k, 4j+2k+l] = P_ijkl, else 0. Forced junctions: any state
        # whose first pair is not (0,0) transitions with certainty (P..0 = 1).
        P8 = np.zeros((8, 8), dtype=float)
        P8[0, 0], P8[0, 1] = P0000, P0001        # (000)->(00x)
        P8[1, 2], P8[1, 3] = 1.0, 0.0            # (001)->(01x)
        P8[2, 4], P8[2, 5] = 1.0, 0.0            # (010)->(10x)
        P8[3, 6], P8[3, 7] = 1.0, 0.0            # (011)->(11x)
        P8[4, 0], P8[4, 1] = P1000, P1001        # (100)->(00x)
        P8[5, 2], P8[5, 3] = 1.0, 0.0            # (101)->(01x)
        P8[6, 4], P8[6, 5] = 1.0, 0.0            # (110)->(10x)
        P8[7, 6], P8[7, 7] = 1.0, 0.0            # (111)->(11x)
        return W, P8


class R1G3Probability(_MarkovProbability):
    """Reichweite-1, 3-component stacking (old R1G3Model). State = one previous
    layer, so W and P are 3×3 (reps = 1). Six parameters (W1, P11_or_P22 and
    four G ratios) fix the single-layer weights and the 3×3 junction matrix via
    detailed balance (ported from R1G3Model.update)."""

    G = 3
    R = 1
    PARAMS = (
        ("W1", 0.8, "W1", "Weight fraction of layer 1."),
        ("P11_or_P22", 0.7, "P11 / P22", "Junction P11 (W1<=1/2) or P22."),
        ("G1", 0.7, "G1", "W2 / (W2 + W3)."),
        ("G2", 0.7, "G2", "(W11+W12) / (W11+W12+W21+W22)."),
        ("G3", 0.7, "G3", "W11 / (W11 + W12)."),
        ("G4", 0.7, "G4", "W21 / (W21 + W22)."),
    )
    type_name = "R1G3Model"

    def _matrices(self):
        W1 = self.value("W1")
        P11_or_P22 = self.value("P11_or_P22")
        G1, G2, G3, G4 = (self.value(n) for n in ("G1", "G2", "G3", "G4"))
        mW0 = W1
        mW1 = (1.0 - mW0) * G1
        mW2 = 1.0 - mW0 - mW1
        W0inv = 1.0 / mW0 if mW0 > 0.0 else 0.0
        if mW0 <= 0.5:  # P00 given
            P00 = P11_or_P22
            Wxx = mW0 * (P00 - 1.0) + mW1 + mW2
        else:  # Pxx given; P00 solved after the off-diagonals
            P00 = None
            Wxx = (1.0 - mW0) * P11_or_P22
        W11 = Wxx * G2 * G3
        W12 = Wxx * G2 * (1.0 - G3)
        W21 = Wxx * (1.0 - G2) * G4
        W22 = Wxx * (1.0 - G2) * (1.0 - G4)
        P11 = W11 / mW1 if mW1 > 0.0 else 0.0
        P12 = W12 / mW1 if mW1 > 0.0 else 0.0
        P10 = 1.0 - P11 - P12
        P21 = W21 / mW2 if mW2 > 0.0 else 0.0
        P22 = W22 / mW2 if mW2 > 0.0 else 0.0
        P20 = 1.0 - P21 - P22
        P01 = (mW1 - W11 - W21) * W0inv
        P02 = (mW2 - W12 - W22) * W0inv
        if mW0 > 0.5:
            P00 = 1.0 - P01 - P02
        W = np.diag([mW0, mW1, mW2])
        P = np.array([[P00, P01, P02],
                      [P10, P11, P12],
                      [P20, P21, P22]], dtype=float)
        return W, P


class R2G3Probability(_MarkovProbability):
    """Reichweite-2, 3-component stacking (old R2G3Model). State = a pair of
    layers, so W and P are g²×g² = 9×9 (reps = 9//3 = 3). Illite-smectite
    restrictions forbid consecutive expandable layers, so most pair-states have
    zero weight; six parameters set the rest (ported from R2G3Model.update)."""

    G = 3
    R = 2
    _TWOTHIRDS = 2.0 / 3.0
    PARAMS = (
        ("W1", 0.8, "W1", "Weight fraction of layer 1."),
        ("P111_or_P212", 0.9, "P111 / P212", "Junction P111 (W1<2/3) or P212."),
        ("G1", 0.9, "G1", "W2 / (W2 + W3)."),
        ("G2", 0.9, "G2", "share of the x0x weight going to layer 1."),
        ("G3", 0.9, "G3", "W101 / W10x."),
        ("G4", 0.9, "G4", "W201 / W20x."),
    )
    type_name = "R2G3Model"

    def _matrices(self):
        W1 = self.value("W1")
        P111_or_P212 = self.value("P111_or_P212")
        G1, G2, G3, G4 = (self.value(n) for n in ("G1", "G2", "G3", "G4"))
        # Single-layer weights.
        W0, W1w, W2w = W1, (1.0 - W1) * G1, None
        W2w = 1.0 - W0 - W1w
        # Pair weights (mW[i,j]); state x = 3i + j. Restrictions zero out the
        # consecutive-expandable pairs.
        pairW = {}
        pairW[(1, 1)] = pairW[(1, 2)] = pairW[(2, 1)] = pairW[(2, 2)] = 0.0
        pairW[(0, 1)] = pairW[(1, 0)] = W1w
        pairW[(0, 2)] = pairW[(2, 0)] = W2w
        pairW[(0, 0)] = W0 - pairW[(0, 1)] - pairW[(0, 2)]
        # 3-layer weights on the x0x path.
        Wx = W1w + W2w
        if W0 < self._TWOTHIRDS:
            P000 = P111_or_P212
            Px0x = (1.0 - (W0 - Wx) / Wx * (1.0 - P000)) if Wx != 0 else 0.0
        else:
            Px0x = P111_or_P212
            P000 = (1.0 - Wx / (W0 - Wx) * (1.0 - Px0x)) if (W0 - Wx) != 0 else 0.0
        Wx0x = Wx * Px0x
        W10x = G2 * Wx0x
        W20x = Wx0x - W10x
        tW = {}  # triplet weights mW[i,j,k]
        tW[(1, 0, 1)] = G3 * W10x
        tW[(1, 0, 2)] = (1.0 - G3) * W10x
        tW[(1, 0, 0)] = pairW[(1, 0)] - tW[(1, 0, 1)] - tW[(1, 0, 2)]
        tW[(2, 0, 1)] = G4 * W20x
        tW[(2, 0, 2)] = (1.0 - G4) * W20x
        tW[(2, 0, 0)] = pairW[(2, 0)] - tW[(2, 0, 1)] - tW[(2, 0, 2)]
        tW[(0, 0, 0)] = pairW[(0, 0)] * P000
        tW[(0, 0, 1)] = pairW[(0, 1)] - tW[(1, 0, 1)] - tW[(2, 0, 1)]
        tW[(0, 0, 2)] = pairW[(0, 2)] - tW[(1, 0, 2)] - tW[(2, 0, 2)]
        # The (i,1,*) and (i,2,*) triplets: after an expandable layer only a
        # non-expandable (0) may follow, so (i,j,0) inherits the pair weight.
        tW[(0, 1, 0)] = pairW[(0, 1)]
        tW[(0, 2, 0)] = pairW[(0, 2)]
        # Assemble W (9x9 diag) and P[3i+j, 3j+k] = mW[i,j,k] / mW[i,j].
        W = np.zeros((9, 9), dtype=float)
        for (i, j), w in pairW.items():
            W[3 * i + j, 3 * i + j] = w
        P = np.zeros((9, 9), dtype=float)
        for i in range(3):
            for j in range(3):
                wij = pairW.get((i, j), 0.0)
                if wij <= 0.0:
                    continue
                for k in range(3):
                    P[3 * i + j, 3 * j + k] = tW.get((i, j, k), 0.0) / wij
        return W, P


class UnsupportedProbabilityModel(ValueError):
    """Raised when a .mud carries a layer-stacking model MudLab2 does not
    model yet (any higher-R type other than R0* / R1G2Model). Loading it as R0
    would produce a WRONG pattern with no warning, so the load is refused
    instead. The message is user-facing (shown by the open-project handler)."""

    def __init__(self, prob_type: str) -> None:
        self.prob_type = prob_type
        super().__init__(
            "This project uses the '%s' layer-stacking model, which MudLab2 "
            "does not support yet (modeled: R0 any G, R1G2, R1G3, R2G2, R2G3, "
            "R3G2)." % prob_type
        )


def probabilities_from_dict(data: dict, G: int):
    """Build a probability model from a .mud probabilities dict.

    Dispatches on the stored type string. R0 (any G) and R1G2 are modeled. A
    NEW phase passes an empty dict -> R0 default. Any OTHER recognised type is
    a higher-R model we have not ported: raise UnsupportedProbabilityModel
    rather than silently degrade it to R0 (which would produce a wrong pattern
    - the calc has no way to tell it apart from a real R0 phase)."""
    prob_type = data.get("type", "") if isinstance(data, dict) else ""
    if prob_type == "R1G2Model":
        return R1G2Probability.from_dict(data, G)
    if prob_type == "R2G2Model":
        return R2G2Probability.from_dict(data, G)
    if prob_type == "R3G2Model":
        return R3G2Probability.from_dict(data, G)
    if prob_type == "R1G3Model":
        return R1G3Probability.from_dict(data, G)
    if prob_type == "R2G3Model":
        return R2G3Probability.from_dict(data, G)
    if prob_type.startswith("R0G"):
        return R0Probability.from_dict(data, G)
    if prob_type == "":
        # No stored type: a freshly created phase (Phase.__init__ /
        # create_empty). Default to R0 - the modeled, safe baseline.
        return R0Probability.from_dict(data, G)
    raise UnsupportedProbabilityModel(prob_type)
