"""CSDS (Coherent Scattering Domain Size) distribution, ported as-is from
the old mudlab/calculations/CSDS.py.

Returns the log-normal crystallite-size distribution (an array indexed by
number of layers T) and its arithmetic mean, from a CSDS object exposing
minimum / maximum / average and the alpha/beta log-normal parameters.
"""

from __future__ import annotations

from math import log, sqrt

import numpy as np

from mudlab.calculations.math_tools import lognormal

_csds_cache: dict = {}


def calculate_distribution(csds):
    key = (
        csds.minimum, csds.maximum, csds.average,
        csds.alpha_scale, csds.alpha_offset,
        csds.beta_scale, csds.beta_offset,
    )
    if key in _csds_cache:
        return _csds_cache[key]

    a = csds.alpha_scale * log(csds.average) + csds.alpha_offset
    b = sqrt(csds.beta_scale * log(csds.average) + csds.beta_offset)

    steps = int(csds.maximum - csds.minimum) + 1

    max_t = 0
    smq = 0.0
    tq_distr: dict = {}
    for i in range(steps):
        t = max(csds.minimum + i, 1e-50)
        q = lognormal(t, a, b)
        smq += q
        tq_distr[int(t)] = q
        max_t = t

    tq_arr = np.zeros(shape=(int(max_t) + 1,), dtype=float)
    r_mean = 0.0
    for t, q in tq_distr.items():
        tq_arr[t] = q / smq
        r_mean += t * q
    r_mean /= smq

    _csds_cache[key] = (tq_arr, r_mean)
    return tq_arr, r_mean
