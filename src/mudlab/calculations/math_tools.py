"""Signal helpers, ported as-is from the old mudlab/calculations/math_tools.py."""

from __future__ import annotations

from math import pi, sqrt

import numpy as np

# Constants used by the goniometer Lorentz-polarisation factor.
sqrtpi = sqrt(pi)
sqrt2pi = sqrt(2 * pi)
sqrt8 = sqrt(8)

_WINDOWS = ("flat", "hanning", "hamming", "bartlett", "blackman")


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
