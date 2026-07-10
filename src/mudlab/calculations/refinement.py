"""General parameter refinement, ported from the old mudlab.refinement
(refiner.py + methods/) and adapted to MudLab2's models.

This refines the *structural* refinable parameters of a mixture's phases -
sigma*, the CSDS mean, the R0 F params, and per-component d001 / delta_c -
each with a [min, max, refine] triple stored in the .mud as `<name>_ref_info`
(preserved verbatim in the models' raw_properties). It is distinct from the
mixture Optimize, which only fits fractions/scales/background.

Architecture (matches the old app): an outer search method varies the
FLAGGED refinables; each trial sets those values and then INNER-optimises
the fractions/scales/background via calculations.mixture.optimize_mixture
(the old get_optimized_residual). So refining a structural parameter costs
one full per-phase recompute plus an inner fit per trial - heavy, but
correct.

Only the three SciPy methods are ported (the old deap-based CMA-ES / MPSO /
PS-CMA-ES are dropped - deap is not available); the indices are renumbered
contiguously: 0 = L-BFGS-B, 1 = Basin Hopping, 2 = Brute force. L-BFGS-B
stays 0, so a .mud with refine_method_index 0 still maps correctly.
"""

from __future__ import annotations

from itertools import combinations, product

import numpy as np
from scipy.optimize import basinhopping, fmin_l_bfgs_b

from mudlab.calculations.mixture import optimize_mixture

_PENALTY = 1.0e6  # finite substitute for a non-finite residual


# ----------------------------------------------------------------------
# Refinable parameter
# ----------------------------------------------------------------------
class Refinable:
    """One refinable model parameter: a label, a value get/set into the live
    model, and its [min, max, refine] triple read/written into the owning
    raw-properties dict (so flags/bounds round-trip through to_dict)."""

    __slots__ = ("label", "_get", "_set", "_owner", "_key", "_default_bounds")

    def __init__(self, label, getter, setter, ref_info_owner, ref_info_key,
                 default_bounds=(0.0, 1.0)):
        self.label = label
        self._get = getter
        self._set = setter
        self._owner = ref_info_owner
        self._key = ref_info_key
        self._default_bounds = default_bounds

    @property
    def value(self) -> float:
        return float(self._get())

    @value.setter
    def value(self, v) -> None:
        self._set(float(v))

    def _ref_info(self):
        info = self._owner.get(self._key)
        if isinstance(info, (list, tuple)) and len(info) >= 3:
            return [float(info[0]), float(info[1]), bool(info[2])]
        lo, hi = self._default_bounds
        return [float(lo), float(hi), False]

    @property
    def minimum(self) -> float:
        return self._ref_info()[0]

    @property
    def maximum(self) -> float:
        return self._ref_info()[1]

    @property
    def refine(self) -> bool:
        return self._ref_info()[2]

    def set_ref_info(self, minimum=None, maximum=None, refine=None) -> None:
        """Write flag / bounds back into the raw-properties ref_info (used by
        the Refinement window; round-trips via the phase/component to_dict)."""
        info = self._ref_info()
        if minimum is not None:
            info[0] = float(minimum)
        if maximum is not None:
            info[1] = float(maximum)
        if refine is not None:
            info[2] = bool(refine)
        self._owner[self._key] = info


def _nested(raw: dict, *keys: str) -> dict:
    """Return raw[keys[0]][keys[1]]..., creating empty dicts as needed, so a
    ref_info can be written into a nested .mud structure (CSDS / probabilities)
    that survives to_dict."""
    node = raw
    for key in keys:
        child = node.get(key)
        if not isinstance(child, dict):
            child = {}
            node[key] = child
        node = child
    return node


def _phase_refinables(phase) -> list[Refinable]:
    raw = phase.raw_properties
    out = [
        Refinable(
            "%s | sigma*" % phase.name,
            lambda p=phase: p.sigma_star,
            lambda v, p=phase: setattr(p, "sigma_star", v),
            raw, "sigma_star_ref_info", default_bounds=(0.0, 90.0),
        ),
        Refinable(
            "%s | CSDS mean" % phase.name,
            lambda p=phase: p.CSDS.average,
            lambda v, p=phase: setattr(p.CSDS, "average", v),
            _nested(raw, "CSDS_distribution", "properties"),
            "average_ref_info", default_bounds=(1.0, 200.0),
        ),
    ]
    if phase.G >= 2:
        prob_props = _nested(raw, "probabilities", "properties")
        for i in range(phase.probabilities.n_independents):
            out.append(Refinable(
                "%s | F%d" % (phase.name, i + 1),
                lambda p=phase, i=i: p.probabilities.f_value(i),
                lambda v, p=phase, i=i: p.probabilities.set_f(i, v),
                prob_props, "F%d_ref_info" % (i + 1), default_bounds=(0.0, 1.0),
            ))
    for comp in phase.components:
        craw = comp.raw_properties
        out.append(Refinable(
            "%s | %s | d001" % (phase.name, comp.name),
            lambda c=comp: c.d001,
            lambda v, c=comp: setattr(c, "d001", v),
            craw, "d001_ref_info", default_bounds=(0.0, 5.0),
        ))
        out.append(Refinable(
            "%s | %s | delta_c" % (phase.name, comp.name),
            lambda c=comp: c.delta_c,
            lambda v, c=comp: setattr(c, "delta_c", v),
            craw, "delta_c_ref_info", default_bounds=(0.0, 0.05),
        ))
    return out


def enumerate_refinables(mixture) -> list[Refinable]:
    """All refinable parameters of the mixture's (unique) phases, flagged or
    not. The Refinement window shows the whole list; the Refiner uses only the
    flagged ones."""
    refinables = []
    seen = set()
    for row in mixture.phase_matrix:
        for phase in row:
            if phase is None or id(phase) in seen:
                continue
            seen.add(id(phase))
            refinables.extend(_phase_refinables(phase))
    return refinables


# ----------------------------------------------------------------------
# Refiner (the outer-search context)
# ----------------------------------------------------------------------
class Refiner:
    def __init__(self, mixture, refinables):
        self.mixture = mixture
        self.refinables = []
        self.ranges = []
        initial = []
        for ref in refinables:
            if not ref.refine:
                continue
            lo, hi = ref.minimum, ref.maximum
            if not (lo < hi):  # degenerate range: cannot refine
                continue
            self.refinables.append(ref)
            self.ranges.append((lo, hi))
            initial.append(min(max(ref.value, lo), hi))  # clip into bounds
        self.initial_solution = np.array(initial, dtype=float)
        self.best_solution = self.initial_solution.copy()
        self.best_residual = None

    def apply_solution(self, x) -> None:
        x = np.atleast_1d(np.asarray(x, dtype=float))
        for i, ref in enumerate(self.refinables):
            ref.value = float(x[i])

    def get_residual(self, x) -> float:
        """Set the structural refinables to x, inner-optimise fractions/scales/
        background, and return that residual (guarded finite)."""
        self.apply_solution(x)
        residual = optimize_mixture(self.mixture)
        if not np.isfinite(residual):
            residual = _PENALTY
        self.update(x, residual)
        return residual

    def update(self, x, residual) -> None:
        if self.best_residual is None or residual < self.best_residual:
            self.best_residual = residual
            self.best_solution = np.atleast_1d(np.asarray(x, dtype=float)).copy()

    def apply_best(self) -> None:
        """Set the refinables to the best solution found and inner-optimise
        once more so the mixture ends at its best fit."""
        self.apply_solution(self.best_solution)
        optimize_mixture(self.mixture)


# ----------------------------------------------------------------------
# Methods (SciPy only; indices renumbered 0/1/2)
# ----------------------------------------------------------------------
def _run_lbfgsb(refiner, options):
    # epsilon 1e-4 (old value): structural params need a coarser finite-diff
    # step than the default 1e-8. scipy 1.18 is silent (no iprint).
    fmin_l_bfgs_b(
        refiner.get_residual, refiner.initial_solution,
        approx_grad=True, bounds=refiner.ranges, epsilon=1e-4,
        maxfun=int(options.get("maxfun", 500)),
        maxiter=int(options.get("maxiter", 150)),
    )


def _run_basinhopping(refiner, options):
    basinhopping(
        refiner.get_residual, refiner.initial_solution,
        niter=int(options.get("niter", 100)),
        T=float(options.get("T", 1.0)),
        stepsize=float(options.get("stepsize", 0.5)),
        minimizer_kwargs={"method": "L-BFGS-B", "bounds": refiner.ranges},
    )


def _run_bruteforce(refiner, options):
    num_samples = int(options.get("num_samples", 11))
    bounds = np.array(refiner.ranges, dtype=float)
    mins = bounds[:, 0]
    spans = bounds[:, 1] - bounds[:, 0]
    n = len(refiner.ranges)
    if n == 1:
        for index in range(num_samples):
            frac = np.array([index / float(num_samples - 1)])
            refiner.get_residual(mins + spans * frac)
    else:
        # Grid over each pair of parameters, others held at mid-range (old
        # custom_brute); a full n-D grid would explode combinatorially.
        for par1, par2 in combinations(range(n), 2):
            fracs = np.ones(n) * 0.5
            for a, b in product(range(num_samples), repeat=2):
                fracs[par1] = a / float(num_samples - 1)
                fracs[par2] = b / float(num_samples - 1)
                refiner.get_residual(mins + spans * fracs)


REFINE_METHODS = {
    0: ("L-BFGS-B algorithm", _run_lbfgsb),
    1: ("Basin Hopping algorithm", _run_basinhopping),
    2: ("Brute force algorithm", _run_bruteforce),
}


def refine_mixture(mixture, method_index=0, options=None) -> float:
    """Refine the mixture's flagged structural parameters with the chosen
    SciPy method, leaving the model at the best solution (structural params +
    inner-fitted fractions/scales/background). Returns the best residual.

    With nothing flagged (or all ranges degenerate) it simply inner-optimises
    fractions/scales/background, matching a plain Optimize. Exceptions are not
    swallowed here (fail loud); the GUI wraps this call.
    """
    options = options or {}
    refiner = Refiner(mixture, enumerate_refinables(mixture))
    if not refiner.refinables:
        return optimize_mixture(mixture)

    # Seed the history with the starting point, then run the outer search.
    refiner.get_residual(refiner.initial_solution)
    runner = REFINE_METHODS.get(method_index, REFINE_METHODS[0])[1]
    runner(refiner, options)

    refiner.apply_best()
    return float(refiner.best_residual)
