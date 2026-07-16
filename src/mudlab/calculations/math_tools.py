"""Signal helpers, ported as-is from the old mudlab/calculations/math_tools.py."""

from __future__ import annotations

from math import exp, log, pi, sqrt

import numpy as np

# Constants used by the goniometer Lorentz-polarisation factor.
sqrtpi = sqrt(pi)
sqrt2pi = sqrt(2 * pi)
sqrt8 = sqrt(8)

_WINDOWS = ("flat", "hanning", "hamming", "bartlett", "blackman")


def lognormal(T, a, b):
    """Log-normal probability density (old math_tools.lognormal)."""
    return exp(-(log(T) - a) ** 2 / (2.0 * (b ** 2))) / (sqrt2pi * abs(b) * T)


def mmult(A, B):
    """Batched matrix multiply: A[i]·B[i] over the leading axis.

    Used by the phase-intensity stacking summation to multiply the stack of
    per-(2θ) matrices (old math_tools.mmult)."""
    return np.einsum("ijk,ikl->ijl", A, B)


def add_noise(x: np.ndarray, noise_fraction: float = 0.05) -> np.ndarray:
    """Add Gaussian noise scaled to a fraction of the signal maximum.

    Ported as-is from the old math_tools.add_noise: the standard deviation is
    ``noise_fraction * max(x)``, so the noise scales with the pattern's
    strongest reflection rather than with each point's own counts.
    """
    x = np.asarray(x, dtype=float)
    if x.size > 0:
        abs_value = noise_fraction * np.amax(x)
        return x + np.random.standard_normal(x.shape) * abs_value
    return x


def smooth(x: np.ndarray, half_window_len: int = 3, window: str = "blackman") -> np.ndarray:
    """Smooth a 1D signal by convolving it with a scaled window.

    The signal is padded with reflected copies at both ends so transients
    are minimised. ``window_len = 2*half_window_len + 1`` (always odd).
    ``window`` is one of flat / hanning / hamming / bartlett / blackman
    (flat = moving average).
    """
    window_len = half_window_len * 2 + 1

    x = np.asarray(x, dtype=float)
    if x.ndim != 1:
        x = np.ndarray.flatten(x)
    if x.size < window_len:
        raise ValueError("Input vector needs to be bigger than window size.")
    if window_len < 3:
        return x
    if window not in _WINDOWS:
        raise ValueError(f"Window is one of {_WINDOWS}")

    s = np.r_[x[window_len - 1:0:-1], x, x[-1:-window_len:-1]]
    if window == "flat":  # moving average
        w = np.ones(window_len, "d")
    else:
        w = getattr(np, window)(window_len)

    y = np.convolve(w / w.sum(), s, mode="valid")
    return y[half_window_len:-half_window_len]
