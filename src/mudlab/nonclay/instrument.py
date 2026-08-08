"""Instrumental peak width from a Si-standard measurement (read-only).

The from-CIF reference calculator (structure.py) produces sticks; to match a
measured residual they must be broadened to the instrument's real width. A Si
standard (NIST SRM 640) gives that width directly - measure the FWHM of its
sharp, well-separated peaks (Finding 21). This returns a single representative
FWHM (deg 2theta) for the Gaussian broadening; a full Caglioti 2theta-dependence
is a later refinement. Nothing here touches a model.
"""

from __future__ import annotations

import numpy as np

# Si (Cu Ka) peak 2theta positions.
_SI_PEAKS = (28.44, 47.30, 56.12, 69.13, 76.37, 88.03)


def _peak_fwhm(x, y, pos, window=1.0):
    """FWHM (deg) of the peak near ``pos`` by half-max interpolation, or None."""
    sel = (x >= pos - window) & (x <= pos + window)
    if not np.any(sel):
        return None
    xs = x[sel]
    ys = y[sel] - float(y[sel].min())
    imax = int(np.argmax(ys))
    peak = float(ys[imax])
    if peak <= 0:
        return None
    half = peak / 2.0

    li = imax
    while li > 0 and ys[li] > half:
        li -= 1
    if ys[li] > half:
        return None
    xl = float(np.interp(half, [ys[li], ys[li + 1]], [xs[li], xs[li + 1]]))

    ri = imax
    while ri < len(ys) - 1 and ys[ri] > half:
        ri += 1
    if ys[ri] > half:
        return None
    xr = float(np.interp(half, [ys[ri], ys[ri - 1]], [xs[ri], xs[ri - 1]]))
    return abs(xr - xl)


def instrumental_fwhm(x, y, default=0.10):
    """Representative instrumental FWHM (deg 2theta) = median of the measurable
    Si peak FWHMs; ``default`` if none can be measured."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    widths = []
    for pos in _SI_PEAKS:
        w = _peak_fwhm(x, y, pos)
        if w is not None and 0.01 < w < 2.0:
            widths.append(w)
    return float(np.median(widths)) if widths else default
