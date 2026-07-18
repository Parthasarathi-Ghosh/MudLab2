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

Two convergent SciPy methods are kept: 0 = L-BFGS-B (local), 1 = Basin
Hopping (global). The old deap-based CMA-ES / MPSO / PS-CMA-ES are dropped
(deap is not available), and Brute force was removed too - it is a coarse
fixed-grid scan with no convergence and a combinatorial runtime, so Basin
Hopping strictly dominates it for global search. (Its only niche was
visualising the residual landscape, which belongs with the deferred progress
plot; a constrained grid scan can be reintroduced then.) L-BFGS-B stays 0, so
a .mud with refine_method_index 0 still maps correctly.

Robustness & long runs (this is the heaviest, most fragile operation):
- Cost: each outer trial does a FULL per-phase recompute plus an inner
  fraction/scale/bg optimise. Rough worst cases - L-BFGS-B (maxfun 500):
  seconds to ~2 min; Basin Hopping (niter 100 = 100 local minimisations):
  minutes to tens of minutes. It is SYNCHRONOUS - it blocks its caller - so
  the GUI must run it under a busy cursor now and move it to a worker thread
  later (Phase C).
- Cancellation: pass a `stop` callable (returns True to abort); it is checked
  before every trial and unwinds cleanly, keeping the best-so-far solution.
  This is the hook the Refinement window's Cancel button will use.
- Numerical guards: a non-finite residual becomes _PENALTY (never NaN to
  scipy); degenerate ranges (min>=max) are skipped and the start value is
  clipped into bounds.
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

import numpy as np
from scipy.optimize import basinhopping, fmin_l_bfgs_b

from mudlab.calculations.mixture import get_current_residual, optimize_mixture

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
    # A phase-level inherited parameter follows its based_on parent - refining
    # it on the child would be a no-op (the read-through overrides the write),
    # so only the parent's copy is an independent refinable.
    out = []
    if not phase.is_inherited("sigma_star"):
        out.append(Refinable(
            "%s | sigma*" % phase.name,
            lambda p=phase: p.sigma_star,
            lambda v, p=phase: setattr(p, "sigma_star", v),
            raw, "sigma_star_ref_info", default_bounds=(0.0, 90.0),
        ))
    if not phase.is_inherited("CSDS"):
        out.append(Refinable(
            "%s | CSDS mean" % phase.name,
            lambda p=phase: p.CSDS.average,
            lambda v, p=phase: setattr(p.CSDS, "average", v),
            _nested(raw, "CSDS_distribution", "properties"),
            "average_ref_info", default_bounds=(1.0, 200.0),
        ))
    # Stacking probabilities: the model lists its own independent parameters
    # (R0 -> F1..Fn, R1G2 -> W1 / P11_or_P22), so the refiner does not need to
    # know which model it is. An inherited parameter follows its based_on
    # parent, so it is skipped here (only the parent's copy is independent).
    prob_params = phase.probabilities.refinable_params()
    if prob_params:
        prob_props = _nested(raw, "probabilities", "properties")
        for label, getter, setter, ref_key, bounds, inherited in prob_params:
            if inherited:
                continue
            out.append(Refinable(
                "%s | %s" % (phase.name, label),
                getter, setter, prob_props, ref_key, default_bounds=bounds,
            ))
    for comp in phase.components:
        craw = comp.raw_properties
        # An inherited scalar follows its linked template - refining it on the
        # child would be a no-op (the read-through overrides the write), so it
        # is not an independent refinable here (old is_refinable = not inherited).
        if not comp.is_inherited("d001"):
            out.append(Refinable(
                "%s | %s | d001" % (phase.name, comp.name),
                lambda c=comp: c.d001,
                lambda v, c=comp: setattr(c, "d001", v),
                craw, "d001_ref_info", default_bounds=(0.0, 5.0),
            ))
        if not comp.is_inherited("delta_c"):
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
    def __init__(self, mixture, refinables, stop=None, on_progress=None):
        self.mixture = mixture
        # `stop`, if given, is a no-arg callable returning True to abort. It is
        # checked before each (expensive) trial so a long refinement can be
        # cancelled (the GUI will pass a threading.Event.is_set here).
        self._stop = stop
        # `on_progress(n_evaluations, best_residual)`, if given, is called after
        # each outer trial for a live status readout. It runs on whatever thread
        # drives the refinement; the GUI passes a callback that only emits a
        # queued Qt signal (no GUI access here).
        self._on_progress = on_progress
        self._n_evals = 0
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
        # The three "keep this solution" points the Refinement window offers
        # (Initial / Best / Last) are tracked as explicit fields here, NOT
        # derived from the history - so they survive with the progress-plot
        # history disabled. Only the full trajectory (for the Show-plot button)
        # lives in the history hook below.
        self.best_solution = self.initial_solution.copy()
        self.last_solution = self.initial_solution.copy()
        self.initial_residual = None
        self.best_residual = None
        self.last_residual = None

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
        self._n_evals += 1
        self.apply_solution(x)
        residual = optimize_mixture(self.mixture)
        if not np.isfinite(residual):
            residual = _PENALTY
        self.update(x, residual)
        return residual

    def update(self, x, residual) -> None:
        x = np.atleast_1d(np.asarray(x, dtype=float)).copy()
        if self.record_history:  # deferred progress-plot hook (disabled)
            self.history.append((float(residual), x.copy()))
        self.last_solution = x
        self.last_residual = float(residual)
        if self.best_residual is None or residual < self.best_residual:
            self.best_residual = float(residual)
            self.best_solution = x.copy()
        if self._on_progress is not None:
            self._on_progress(self._n_evals, self.best_residual)

    # The Refinement window's Initial / Best / Last buttons apply one of the
    # three tracked solutions; each sets the structural params then inner-fits
    # fractions/scales/background so the mixture lands at that solution's fit.
    # They return the ACTUALLY-ACHIEVED residual (which, because the inner fit
    # warm-starts from the mixture's current fractions, need not equal the
    # residual recorded for that solution during the search).
    def apply_best(self) -> float:
        self.apply_solution(self.best_solution)
        return float(optimize_mixture(self.mixture))

    def apply_last(self) -> float:
        self.apply_solution(self.last_solution)
        return float(optimize_mixture(self.mixture))

    def apply_initial(self) -> float:
        self.apply_solution(self.initial_solution)
        return float(optimize_mixture(self.mixture))


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


REFINE_METHODS = {
    0: ("L-BFGS-B algorithm", _run_lbfgsb),
    1: ("Basin Hopping algorithm", _run_basinhopping),
}


def refine_mixture(mixture, method_index=0, options=None, stop=None,
                   on_progress=None) -> "Refiner":
    """Refine the mixture's flagged structural parameters with the chosen
    SciPy method, leaving the model at the best solution (structural params +
    inner-fitted fractions/scales/background). Returns the Refiner, which
    carries the initial / best / last solutions + residuals and the
    apply_initial/best/last methods the Refinement window wires its buttons to
    (refiner.best_residual is the achieved residual).

    With nothing flagged (or all ranges degenerate) it simply inner-optimises
    fractions/scales/background, matching a plain Optimize. `stop` is an
    optional no-arg callable returning True to cancel (see Refiner); on cancel
    the best-so-far solution is applied.

    End state: normally / on cancel the model is left at the best solution
    (structural params + inner-fitted fractions/scales/background). On any
    OTHER exception the pre-refine state is RESTORED and the exception
    re-raised - so a mid-loop error never leaves the model at a random
    half-refined solution (which could then be saved). It still fails loud;
    the GUI wraps this call to report it.
    """
    options = options or {}
    refiner = Refiner(
        mixture, enumerate_refinables(mixture), stop=stop, on_progress=on_progress
    )
    if not refiner.refinables:
        residual = float(optimize_mixture(mixture))
        refiner.initial_residual = residual
        refiner.best_residual = residual
        refiner.last_residual = residual
        return refiner

    # Snapshot the full mutable state before the search (the flagged structural
    # values plus the mixture's fractions/scales/background, which the inner
    # optimise rewrites every trial) so it can be restored exactly.
    saved_values = [ref.value for ref in refiner.refinables]
    saved_fractions = np.array(mixture.fractions, dtype=float)
    saved_scales = np.array(mixture.scales, dtype=float)
    saved_bgshifts = np.array(mixture.bgshifts, dtype=float)
    # The genuine "before" fit - the residual the user had when they pressed
    # Refine. Measured on the untouched snapshot (get_current_residual does
    # not mutate), so it is the exact number the non-worsening guard compares
    # against below.
    pre_residual = float(get_current_residual(mixture))

    def _restore_snapshot() -> None:
        for ref, value in zip(refiner.refinables, saved_values):
            ref.value = value
        mixture.fractions = saved_fractions
        mixture.scales = saved_scales
        mixture.bgshifts = saved_bgshifts

    try:
        # Seed the best/initial with the starting point, then run the search.
        refiner.initial_residual = refiner.get_residual(refiner.initial_solution)
        runner = REFINE_METHODS.get(method_index, REFINE_METHODS[0])[1]
        runner(refiner, options)
    except _RefinementStopped:
        pass  # cancelled: fall through and apply the best solution so far
    except Exception:
        _restore_snapshot()  # back to the pre-refine state
        raise  # fail loud

    # Non-worsening guarantee. apply_best re-optimises the inner fractions/
    # scales/background from the search's FINAL warm-start, so it can land at a
    # worse inner local optimum than the pre-refine state - i.e. Refine could
    # leave the fit worse than it started, and best_residual (recorded
    # mid-search at a warm-start apply_best cannot reproduce) can overstate the
    # achieved fit. So measure what apply_best actually achieved and, if it is
    # not at least as good as the snapshot, restore the snapshot. Either way
    # best_residual is set to the residual that is genuinely APPLIED, so the
    # Refinement window's number matches the model's real state.
    applied = refiner.apply_best()
    if not np.isfinite(applied) or applied > pre_residual:
        _restore_snapshot()
        refiner.best_solution = np.array(saved_values, dtype=float)
        refiner.best_residual = pre_residual
    else:
        refiner.best_residual = applied
    return refiner
