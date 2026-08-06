"""Detection rule for non-clay estimates (Findings 8, 9).

A least-squares standard error is useless here: the residual is the clay misfit,
which is smooth and strongly autocorrelated, so a textbook sigma over ~2300
points is wildly optimistic. Instead the threshold is a MIS-REGISTRATION NULL -
shift a reference to where its peaks do NOT belong and fit it identically; any
amplitude that comes back is spurious, the noise band of this particular misfit
for a curve with these peak shapes. Report a mineral only when the estimate
clears (1) a specimen quality gate (Rp <= 40), (2) its mis-registration null,
and (3) an absolute 0.5% floor (integrated-intensity XRD without RIRs cannot
defend a sub-0.5% accessory).

READ-ONLY: builds transient shifted RawPatternPhase copies of the reference and
re-fits; never mutates the specimen or the reference.
"""

from __future__ import annotations

import numpy as np

from mudlab.models.raw_pattern_phase import RawPatternPhase
from mudlab.nonclay.estimator import (
    area, fit_specimen, reference_intensities, specimen_residual,
)

# Offsets (deg 2theta) that mis-register a reference; |delta| >= 0.6 so a shifted
# copy never overlaps its own true peaks.
NULL_OFFSETS = tuple(np.concatenate([
    np.arange(-4.0, -0.55, 0.4), np.arange(0.6, 4.05, 0.4),
]))
NULL_PERCENTILE = 95.0
MIN_PCT = 0.5          # absolute honesty floor (% of the modelled signal)
QUALITY_MAX_RP = 40.0  # clay fit must be this good to quantify against


def _shifted(reference, delta):
    copy = RawPatternPhase(name="%s%+.1f" % (reference.name, delta))
    copy.set_raw_pattern(np.asarray(reference.raw_pattern_x, dtype=float) + delta,
                         np.asarray(reference.raw_pattern_y, dtype=float))
    return copy


def null_threshold_pct(specimen, reference) -> float:
    """The 95th-percentile spurious non-clay % a mis-registered copy of
    ``reference`` picks up in ``specimen`` - the detection threshold."""
    x, _residual, clay, _corr = specimen_residual(specimen)
    a_clay = area(clay, x)
    values = []
    for delta in NULL_OFFSETS:
        basis = reference_intensities(specimen, [_shifted(reference, delta)])
        if not np.any(basis[0]):
            continue  # shifted out of the measured range
        fit = fit_specimen(specimen, [None], basis=basis, signed=True)
        amp_area = abs(float(fit["areas"][0]))
        values.append(100.0 * amp_area / (a_clay + amp_area) if a_clay else 0.0)
    return float(np.percentile(values, NULL_PERCENTILE)) if values else 0.0


def is_detected(pct, null_threshold, specimen_rp) -> bool:
    """The calibrated rule: the specimen fit is good enough (Rp gate) AND the
    estimate clears both its mis-registration null and the absolute floor."""
    if specimen_rp > QUALITY_MAX_RP:
        return False
    return pct > max(null_threshold, MIN_PCT)
