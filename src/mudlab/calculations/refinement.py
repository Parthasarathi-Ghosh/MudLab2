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

Robustness & long runs (this is the heaviest, most fragile operation):
- Cost: each outer trial does a FULL per-phase recompute plus an inner
  fraction/scale/bg optimise. Rough worst cases - L-BFGS-B (maxfun 500):
  seconds to ~2 min; Basin Hopping (niter 100 = 100 local minimisations):
  minutes to tens of minutes; Brute force: C(n,2)*num_samples^2 trials, which
  explodes with the number of flagged params. It is SYNCHRONOUS - it blocks
  its caller - so the GUI must run it under a busy cursor now and move it to a
  worker thread later (Phase C).
- Cancellation: pass a `stop` callable (returns True to abort); it is checked
  before every trial and unwinds cleanly, keeping the best-so-far solution.
  This is the hook the Refinement window's Cancel button will use.
- Numerical guards: a non-finite residual becomes _PENALTY (never NaN to
  scipy); degenerate ranges (min>=max) are skipped and the start value is
  clipped into bounds; brute force needs num_samples>=2 (guarded).
- Fail-loud: only _RefinementStopped is caught here; any other exception
  propagates (a bug to fix) and the GUI wraps the call. On such an error the
  model may be left at a mid-trial solution - the caller should rebind/recompute.
- Not thread-safe: it mutates the shared model in place, so a threaded Phase C
  must own the mixture while refining. Re-entrancy (a second Refine while one
  runs) must be prevented by the UI.
- Deferred: the refinement PROGRESS PLOT (old RefineHistory / refine_results)
  - Refiner.update() has a disabled record_history hook for it.
"""

from __future__ import annotations

from itertools import combinations, product

import numpy as np
from scipy.optimize import basinhopping, fmin_l_bfgs_b

from mudlab.calculations.mixture import optimize_mixture

_PENALTY = 1.0e6  # finite substitute for a non-finite residual


class _RefinementStopped(Exception):
    """Raised from the objective when the caller's stop callback fires, to
    abort the SciPy method cleanly (the exception unwinds out of scipy) and
    keep the best-so-far solution."""


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
    def __init__(self, mixture, refinables, stop=None):
        self.mixture = mixture
        # `stop`, if given, is a no-arg callable returning True to abort. It is
        # checked before each (expensive) trial so a long refinement can be
        # cancelled (the GUI will pass a threading.Event.is_set here).
        self._stop = stop
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

        # DEFERRED FEATURE - refinement progress plot (old RefineHistory +
        # refine_results.glade / get_plot_samples). update() is the recording
        # point: with record_history on it would append every trial's
        # (residual, solution) for a post-run residual-vs-iteration / parameter
        # plot. Kept OFF so a long refinement never grows an unbounded history
        # in memory; enable this and add a plot consumer when that UI is built.
        self.record_history = False
        self.history: list = []

    def apply_solution(self, x) -> None:
        x = np.atleast_1d(np.asarray(x, dtype=float))
        for i, ref in enumerate(self.refinables):
            ref.value = float(x[i])

    def get_residual(self, x) -> float:
        """Set the structural refinables to x, inner-optimise fractions/scales/
        background, and return that residual (guarded finite)."""
        if self._stop is not None and self._stop():
            raise _RefinementStopped()
        self.apply_solution(x)
        residual = optimize_mixture(self.mixture)
        if not np.isfinite(residual):
            residual = _PENALTY
        self.update(x, residual)
        return residual

    def update(self, x, residual) -> None:
        if self.record_history:  # deferred progress-plot hook (disabled)
            self.history.append(
                (float(residual), np.atleast_1d(np.asarray(x, dtype=float)).copy())
            )
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
    num_samples = max(int(options.get("num_samples", 11)), 2)  # /(n-1): need >=2
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


def refine_mixture(mixture, method_index=0, options=None, stop=None) -> float:
    """Refine the mixture's flagged structural parameters with the chosen
    SciPy method, leaving the model at the best solution (structural params +
    inner-fitted fractions/scales/background). Returns the best residual.

    With nothing flagged (or all ranges degenerate) it simply inner-optimises
    fractions/scales/background, matching a plain Optimize. `stop` is an
    optional no-arg callable returning True to cancel (see Refiner); on cancel
    the best-so-far solution is applied. Other exceptions are not swallowed
    here (fail loud); the GUI wraps this call.
    """
    options = options or {}
    refiner = Refiner(mixture, enumerate_refinables(mixture), stop=stop)
    if not refiner.refinables:
        return optimize_mixture(mixture)

    try:
        # Seed the best with the starting point, then run the outer search.
        refiner.get_residual(refiner.initial_solution)
        runner = REFINE_METHODS.get(method_index, REFINE_METHODS[0])[1]
        runner(refiner, options)
    except _RefinementStopped:
        pass  # cancelled: fall through and apply the best solution so far

    refiner.apply_best()
    return float(refiner.best_residual)
