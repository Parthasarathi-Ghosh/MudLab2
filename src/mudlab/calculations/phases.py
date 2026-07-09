"""Phase diffracted intensity, ported as-is from the old
mudlab/calculations/phases.py.

This is the physics core: it folds a phase's component structure factors
(calculations.components.get_factors), its CSDS crystallite-size
distribution (calculations.csds) and its layer-stacking probability
matrices W/P (models.probabilities) into the diffracted intensity of a
whole phase, via the recursive Markovian stacking summation of Drits &
Tchoubar (1990). The Lorentz-polarisation factor
(calculations.goniometer) is applied on top by `get_intensity`.

Only the regular "Phase" type is ported (all sample projects use it);
RawPatternPhase support and the phase-intensity cache from the old code
are additions that come with their own batches. The old `phase` object is
here the calc Phase model (models.phase), which exposes G, components, W,
P, CSDS, sigma_star, apply_lpf and valid_probs.
"""

from __future__ import annotations

import numpy as np

from mudlab.calculations.components import get_factors
from mudlab.calculations.csds import calculate_distribution
from mudlab.calculations.goniometer import get_lorentz_polarisation_factor
from mudlab.calculations.math_tools import mmult


def get_structure_factors(range_stl, G, comp_list):
    """Structure factor (SF) and phase-difference factor (PF) for each of the
    G components over ``range_stl`` (2·sin(θ)/λ), as complex arrays of shape
    ``range_stl.shape + (G,)``."""
    shape = range_stl.shape + (G,)
    SF = np.zeros(shape, dtype=np.complex128)
    PF = np.zeros(shape, dtype=np.complex128)
    for i, comp in enumerate(comp_list):
        SF[:, i], PF[:, i] = get_factors(range_stl, comp)
    return SF, PF


def get_Q_matrices(Q, CSDS_max):
    """Powers Q¹..Q^CSDS_max of the per-(2θ) stacking matrix Q (Qn[0] == Q)."""
    Qn = np.zeros((CSDS_max + 1,) + Q.shape, dtype=complex)
    Qn[0, ...] = np.copy(Q)
    for n in range(1, CSDS_max + 1):
        Qn[n, ...] = mmult(Qn[n - 1, ...], Q)
    return Qn


def get_absolute_scale(components, CSDS_real_mean, W):
    """Absolute intensity scale for a phase = mean_d001 / mean_mass, where
    the means are weight-fraction (W) averages over the components."""
    W = np.diag(W)
    mean_volume = 0.0
    mean_d001 = 0.0
    mean_density = 0.0

    for i, comp in enumerate(components):
        if comp is not None:
            mean_volume += comp.volume * W[i]
            mean_d001 += comp.d001 * W[i]
            mean_density += (comp.weight * W[i] / comp.volume)

    mean_mass = (CSDS_real_mean * mean_volume ** 2 * mean_density)
    if mean_mass != 0.0:
        return mean_d001 / mean_mass
    return 0.0


def get_diffracted_intensity(range_theta, range_stl, phase):
    """Diffracted intensity for a single phase, without the
    Lorentz-polarisation factor."""
    if phase.type == "Phase":
        return _get_diffracted_intensity(range_theta, range_stl, phase)
    raise NotImplementedError(
        "Only regular Phase intensity is ported (got %r)" % phase.type
    )


def get_intensity(range_theta, range_stl, soller1, soller2, mcr_2theta, phase):
    """Diffracted intensity for a single phase, with the Lorentz-polarisation
    factor applied when ``phase.apply_lpf`` is set."""
    intensity = get_diffracted_intensity(range_theta, range_stl, phase)
    if phase.apply_lpf:
        return intensity * get_lorentz_polarisation_factor(
            range_theta, phase.sigma_star, soller1, soller2, mcr_2theta
        )
    return intensity


def _get_diffracted_intensity(range_theta, range_stl, phase):
    assert phase.type == "Phase", "Must be Phase!"
    # Invalid probability model -> zeros instead of a bogus pattern.
    if not phase.valid_probs:
        return np.zeros_like(range_stl)

    # CSDS crystallite-size distribution + its (real) mean.
    CSDS_arr, CSDS_real_mean = calculate_distribution(phase.CSDS)

    # Per-phase absolute scale.
    abs_scale = get_absolute_scale(phase.components, CSDS_real_mean, phase.W)

    # Helper to 'expand' 2θ-independent arrays across the stl range.
    stl_dim = range_stl.shape[0]
    def repeat_to_stl(arr):
        return np.repeat(arr[np.newaxis, ...], stl_dim, axis=0)

    # Repeat weight fractions W and junction probabilities P.
    W = repeat_to_stl(phase.W).astype(np.complex128)
    P = repeat_to_stl(phase.P).astype(np.complex128)

    # Structure factors and their transpose-conjugate outer product.
    SF, PF = get_structure_factors(range_stl, phase.G, phase.components)
    SFa = np.repeat(SF[..., np.newaxis, :], SF.shape[1], axis=1)
    SFb = np.transpose(np.conjugate(SFa), axes=(0, 2, 1))

    # Repetition factor for higher-R probabilities (1 for R0).
    rank = P.shape[1]
    reps = rank // phase.G

    # Structure factor matrix F.
    F = np.repeat(np.repeat(np.multiply(SFb, SFa), reps, axis=2), reps, axis=1)

    # Q phase-factor matrices and their powers Q¹..Q^max.
    PF = np.repeat(PF[..., np.newaxis, :], PF.shape[1], axis=1)
    Q = np.multiply(np.repeat(np.repeat(PF, reps, axis=2), reps, axis=1), P)
    Qn = get_Q_matrices(Q, phase.CSDS.maximum)

    # Recursive stacking summation (vectorised):
    #   progression_factor(n) = Σ_{m=n+1}^{max} (m-n)·CSDS_arr[m]
    #                         = suffix_weighted[n] - n·suffix_sum[n]
    _idx = np.arange(len(CSDS_arr))
    _suffix_sum = np.cumsum(CSDS_arr[::-1])[::-1]
    _suffix_weighted = np.cumsum((_idx * CSDS_arr)[::-1])[::-1]
    ns = np.arange(phase.CSDS.minimum, phase.CSDS.maximum + 1)
    progression_factors = _suffix_weighted[ns] - ns * _suffix_sum[ns]
    sub_total = 2 * np.einsum("n,nijk->ijk", progression_factors, Qn[ns - 1])

    CSDS_I = repeat_to_stl(np.identity(rank, dtype=np.complex128) * CSDS_real_mean)
    sub_total = (CSDS_I + sub_total)
    sub_total = mmult(mmult(F, W), sub_total)
    intensity = np.real(np.trace(sub_total, axis1=2, axis2=1))

    return intensity * abs_scale
