"""Mixture fraction/scale/background optimizer, ported from the old
mudlab/calculations/mixture.py (the non-linear refinement of a mixture's
solution) and adapted to MudLab2's array-based specimen calc.

L-BFGS-B minimises the mean Rp residual across the mixture's specimens over
a solution vector ``x = [free fractions | free scales | free bg-shifts]``.
The expensive per-phase diffracted intensities do NOT depend on the
solution, so they are computed once per specimen into a local context and
the optimiser then iterates cheaply over calculate_scaled_intensities.

Masks (which variables are free vs static):
- fractions_mask comes from the .mud (per phase slot: 1 = refine),
- scales_mask / bgshifts_mask are all-ones when the mixture's auto_scales /
  auto_bg flags are set, else all-zeros (the old model derives them the
  same way).

Only the Rp residual is used (settings.RESIDUAL_METHOD default); a specimen's
exclusion ranges (specimen.exclusion_selector) mask the excluded 2theta
regions out of the residual (all observations when there are none).
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import fmin_l_bfgs_b

from mudlab.calculations.goniometer import get_machine_correction_range
from mudlab.calculations.specimen import (
    calculate_phase_intensities, calculate_scaled_intensities,
)
from mudlab.calculations.statistics import Rp

# Inner optimiser limits (old mudlab.calculations.mixture defaults).
INNER_MAXFUN = 250
INNER_MAXITER = 150

# Finite penalty substituted for a non-finite residual so the optimiser
# never sees NaN/inf (which would abort L-BFGS-B).
_PENALTY = 1.0e6


class _SpecimenContext:
    """The 2theta-independent data one specimen contributes to the objective:
    its per-phase intensities, machine correction, observed pattern and the
    exclusion selector (boolean mask, all-True with no exclusion ranges), plus
    its row index for scale/bg lookup."""

    __slots__ = ("index", "correction", "phase_intensities", "observed", "selected")

    def __init__(self, index, correction, phase_intensities, observed, selected):
        self.index = index
        self.correction = correction
        self.phase_intensities = phase_intensities
        self.observed = observed
        self.selected = selected


class _Problem:
    """Everything the optimiser needs for one mixture: the per-specimen
    contexts and the free-variable layout (kept separate from the model's own
    m/n so the model's totals are never mutated)."""

    def __init__(self, mixture):
        self.mixture = mixture
        self.fractions = np.array(mixture.fractions, dtype=float)
        self.scales = np.array(mixture.scales, dtype=float)
        self.bgshifts = np.array(mixture.bgshifts, dtype=float)

        n_slots = len(self.fractions)
        n_spec = len(self.scales)
        raw = mixture.raw_properties
        fractions_mask = np.asarray(
            raw.get("fractions_mask") or [1] * n_slots, dtype=float
        )
        auto_scales = bool(raw.get("auto_scales", True))
        auto_bg = bool(raw.get("auto_bg", True))
        scales_mask = np.ones(n_spec) if auto_scales else np.zeros(n_spec)
        bgshifts_mask = np.ones(n_spec) if auto_bg else np.zeros(n_spec)

        # Indices of the free variables in each array.
        self.free_fractions = np.nonzero(fractions_mask)[0]
        self.free_scales = np.nonzero(scales_mask)[0]
        self.free_bgshifts = np.nonzero(bgshifts_mask)[0]
        self.nf = len(self.free_fractions)
        self.ns = len(self.free_scales)
        self.nb = len(self.free_bgshifts)

        # Fixed portion of the fractions that stays constant during refinement.
        total = float(np.sum(self.fractions))
        static = total - float(np.sum(np.take(self.fractions, self.free_fractions)))
        if (total != 1.0 and static < 0.0) or static > 1.0:
            if total != 0.0:
                self.fractions = self.fractions / total
                total = 1.0
        self.sum_static = total - float(
            np.sum(np.take(self.fractions, self.free_fractions))
        )

        self.contexts = self._build_contexts()

    # ------------------------------------------------------------------
    def _build_contexts(self):
        contexts = []
        mixture = self.mixture
        for i, specimen in enumerate(mixture.specimens):
            if specimen is None:
                continue
            exp_x, exp_y = specimen.experimental_pattern
            if exp_x.size <= 1:
                continue
            gonio = specimen.goniometer
            range_theta = np.radians(exp_x * 0.5)
            correction = get_machine_correction_range(gonio, range_theta)
            phases = mixture.phase_matrix[i] if i < len(mixture.phase_matrix) else []
            phase_intensities = calculate_phase_intensities(
                range_theta, gonio.wavelength, gonio.wavelength_distribution,
                gonio.soller1, gonio.soller2, gonio.mcr_2theta,
                correction, phases,
            )
            # Exclude the masked 2theta regions from the residual (all-True
            # when the specimen has no exclusion ranges).
            selected = specimen.exclusion_selector(exp_x)
            contexts.append(
                _SpecimenContext(i, correction, phase_intensities, exp_y, selected)
            )
        return contexts

    # ------------------------------------------------------------------
    def get_solution(self):
        """Current free-variable vector (the optimiser's start point)."""
        return np.concatenate((
            np.take(self.fractions, self.free_fractions),
            np.take(self.scales, self.free_scales),
            np.take(self.bgshifts, self.free_bgshifts),
        ))

    def get_bounds(self):
        return (
            [(0.0, 1.0)] * self.nf          # fractions in [0, 1]
            + [(1e-3, None)] * self.ns      # scales strictly positive
            + [(0.0, None)] * self.nb       # bg-shifts non-negative
        )

    def parse_solution(self, x):
        """Expand a free-variable vector into full fractions/scales/bg arrays.
        The free fractions are renormalised so the whole vector sums to 1."""
        fractions = self.fractions.copy()
        scales = self.scales.copy()
        bgshifts = self.bgshifts.copy()
        if self.nf:
            head = np.asarray(x[:self.nf], dtype=float)
            total = float(np.sum(head))
            if total <= 0.0:  # guard: all free fractions collapsed to zero
                scaled = np.full(self.nf, (1.0 - self.sum_static) / self.nf)
            else:
                scaled = head * (1.0 - self.sum_static) / total
            np.put(fractions, self.free_fractions, scaled)
        np.put(scales, self.free_scales, x[self.nf:self.nf + self.ns])
        np.put(bgshifts, self.free_bgshifts, x[self.nf + self.ns:])
        return fractions, scales, bgshifts

    def residual(self, x):
        """Mean Rp across specimens for the solution ``x`` (a large finite
        penalty replaces any non-finite value)."""
        fractions, scales, bgshifts = self.parse_solution(x)
        values = []
        for ctx in self.contexts:
            total, _, _ = calculate_scaled_intensities(
                ctx.phase_intensities, ctx.correction,
                float(scales[ctx.index]), fractions, float(bgshifts[ctx.index]),
            )
            observed = ctx.observed[ctx.selected]
            calculated = total[ctx.selected]
            denom = float(np.sum(np.abs(observed)))
            if denom <= 0.0:
                continue  # zero-observation specimen: undefined Rp, skip
            r = Rp(observed, calculated)
            values.append(r if np.isfinite(r) else _PENALTY)
        if not values:
            return 0.0
        mean = float(np.mean(values))
        return mean if np.isfinite(mean) else _PENALTY


def get_current_residual(mixture) -> float:
    """Mean Rp of the mixture's current (un-optimised) solution."""
    problem = _Problem(mixture)
    return problem.residual(problem.get_solution())


def optimize_mixture(mixture) -> float:
    """Optimise the mixture's fractions / scales / background shifts in place
    (L-BFGS-B on the free variables) and return the achieved mean residual.

    The objective is guarded to stay finite (see _PENALTY), and a diverged
    solve (non-finite result) leaves the model at its current solution. Any
    OTHER exception is deliberately NOT swallowed here - it is a bug to fix,
    and the GUI wraps this call to keep the app alive without hiding it.
    """
    problem = _Problem(mixture)
    x0 = problem.get_solution()

    if len(x0) == 0 or not problem.contexts:
        # Nothing free to refine (or nothing to fit against): leave as-is.
        return problem.residual(x0) if problem.contexts else 0.0

    # scipy 1.18's fmin_l_bfgs_b is silent by default (no iprint/disp arg).
    best_x, residual, _info = fmin_l_bfgs_b(
        problem.residual, x0,
        approx_grad=True, bounds=problem.get_bounds(),
        maxfun=INNER_MAXFUN, maxiter=INNER_MAXITER,
    )

    if not np.isfinite(residual):
        return problem.residual(x0)  # diverged: keep the current solution

    fractions, scales, bgshifts = problem.parse_solution(best_x)
    fractions = fractions.flatten()
    sum_frac = float(np.sum(fractions))
    if sum_frac == 0.0 and len(fractions) > 0:  # prevent NaN on normalise
        fractions[0] = 1.0
        sum_frac = 1.0
    fractions = np.around(fractions / sum_frac, 6)
    scales = np.around(scales * sum_frac, 6)

    mixture.fractions = fractions
    mixture.scales = scales
    mixture.bgshifts = bgshifts
    return float(residual)
