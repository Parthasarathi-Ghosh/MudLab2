"""Case-A non-clay estimator — fit reference patterns to the clay-subtracted
residual. READ-ONLY over the clay path.

After the clay fit, a specimen's residual is approximately

    residual = exp - clay_total ~= sum_i a_i * ref_i
                                   + d_scale * clay_shape + d_bg * correction

(Findings 2-4): the clay optimizer cannot grow a sharp accessory peak, but it
DOES re-absorb intensity through the two global knobs it is free to move - the
specimen ``scale`` (multiplies the clay shape) and ``bgshift`` (multiplies the
machine-correction shape). So the references are fit with ``clay_shape`` and
``correction`` added as FREE (sign-unconstrained) nuisance columns while the
reference amplitudes stay >= 0 - a bounded linear least-squares (bvls). This
inverts the clay re-adjustment WITHOUT touching a line of the clay code
(Finding 3). ``shared_fit`` fits one amplitude per reference across a mixture's
specimens (Finding 14: shared-unweighted is the robust default).

Nothing here mutates a model; it only reads ``experimental_pattern``,
``calculated_pattern``, ``phase_patterns`` and the shipped
``calculate_phase_intensities`` / ``get_machine_correction_range``.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import lsq_linear

from mudlab.calculations.goniometer import get_machine_correction_range
from mudlab.calculations.specimen import calculate_phase_intensities
from mudlab.calculations.statistics import Rp


def area(y, x) -> float:
    """Trapezoid area of an intensity curve over its 2theta grid."""
    return float(np.trapezoid(np.asarray(y, dtype=float), np.asarray(x, dtype=float)))


def specimen_residual(specimen):
    """``(x, residual, clay, correction)`` for a specimen whose clay fit is
    current. ``residual = experimental - total calculated``; ``clay`` is the sum
    of the per-phase patterns (``total - background``); ``correction`` is the
    machine-correction shape (the ``bgshift`` carrier)."""
    x, exp = specimen.experimental_pattern
    x = np.asarray(x, dtype=float)
    total = np.asarray(specimen.calculated_pattern[1], dtype=float)
    pp = specimen.phase_patterns or []
    clay = (np.sum([np.asarray(curve, dtype=float) for _, curve in pp], axis=0)
            if pp else np.zeros_like(total))
    correction = get_machine_correction_range(specimen.goniometer, np.radians(x * 0.5))
    return x, np.asarray(exp, dtype=float) - total, clay, np.asarray(correction, dtype=float)


def reference_intensities(specimen, references) -> np.ndarray:
    """Per-reference intensity rows on the specimen's own 2theta grid, through
    the shipped calc path - exactly what those reference phases would contribute
    from a mixture slot (wavelength distribution applied; a RawPatternPhase gets
    no LP / machine correction, matching a measured accessory)."""
    x, _ = specimen.experimental_pattern
    theta = np.radians(np.asarray(x, dtype=float) * 0.5)
    g = specimen.goniometer
    correction = get_machine_correction_range(g, theta)
    return calculate_phase_intensities(
        theta, g.wavelength, g.wavelength_distribution, g.soller1, g.soller2,
        g.mcr_2theta, correction, references)


def _bvls(design, target, n_ref, signed=False):
    """Bounded LSQ: first ``n_ref`` columns >= 0 (reference amplitudes), the rest
    free (nuisance). ``signed`` drops the non-negativity, to read the estimator's
    noise floor / bias (used by the mis-registration null)."""
    lower = np.full(design.shape[1], -np.inf)
    upper = np.full(design.shape[1], np.inf)
    if not signed:
        lower[:n_ref] = 0.0
    return lsq_linear(design, target, bounds=(lower, upper), method="bvls").x


def fit_specimen(specimen, references, basis=None, signed=False) -> dict:
    """Fit ``references`` to one specimen's residual with free clay + correction
    nuisance columns. Returns amplitudes, per-reference areas, and the non-clay
    percentage of the modelled (clay + non-clay) signal."""
    x, residual, clay, correction = specimen_residual(specimen)
    if basis is None:
        basis = reference_intensities(specimen, references)
    basis = np.asarray(basis, dtype=float)
    n = basis.shape[0]
    design = np.column_stack([basis.T, clay, correction])
    amps = np.asarray(_bvls(design, residual, n, signed=signed)[:n], dtype=float)
    areas = np.array([area(a * row, x) for a, row in zip(amps, basis)], dtype=float)
    a_clay = area(clay, x)
    a_nc = float(areas.sum())
    return {
        "amps": amps, "areas": areas, "a_clay": a_clay, "a_nonclay": a_nc,
        "nonclay_pct": 100.0 * a_nc / (a_clay + a_nc) if (a_clay + a_nc) else 0.0,
    }


def shared_fit(specimens, references) -> np.ndarray:
    """One amplitude per reference SHARED across the specimens, each specimen
    keeping its own free clay + correction nuisance columns (Finding 14). Returns
    the shared amplitude vector (length ``len(references)``)."""
    specimens = [s for s in specimens if s is not None]
    blocks = []
    total_rows = 0
    n = len(references)
    for s in specimens:
        x, residual, clay, correction = specimen_residual(s)
        basis = reference_intensities(s, references)
        blocks.append((np.asarray(basis, float), residual, clay, correction))
        total_rows += len(residual)
    n_cols = n + 2 * len(specimens)
    A = np.zeros((total_rows, n_cols))
    tgt = np.zeros(total_rows)
    row = 0
    for i, (basis, residual, clay, correction) in enumerate(blocks):
        m = len(residual)
        sl = slice(row, row + m)
        A[sl, :n] = basis.T
        A[sl, n + 2 * i] = clay
        A[sl, n + 2 * i + 1] = correction
        tgt[sl] = residual
        row += m
    lower = np.full(n_cols, -np.inf)
    lower[:n] = 0.0
    upper = np.full(n_cols, np.inf)
    sol = lsq_linear(A, tgt, bounds=(lower, upper), method="bvls")
    return np.asarray(sol.x[:n], dtype=float)


def specimen_rp(specimen) -> float:
    """The specimen's clay-fit Rp (%) - the quality gate input (Finding 9)."""
    _x, exp = specimen.experimental_pattern
    total = specimen.calculated_pattern[1]
    return float(Rp(np.asarray(exp, dtype=float), np.asarray(total, dtype=float)))
