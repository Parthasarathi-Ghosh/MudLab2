#!/usr/bin/env python
"""E1 - reference-space (LP) quality gate for the non-clay references.

Question: is each reference curve in OBSERVED-intensity space (Lorentz-
polarisation already included), as the Stage-2 residual fit requires? The
residual keeps its LP weighting, so an LP-free (calculated |F|^2) reference
would be misweighted (LP spans ~35x over 4.6-35 deg). The 'LargeCS'/'SmallCS'
naming says these are CALCULATED patterns, so this is not academic.

Test: compare each reference's peak heights to a STANDARD powder pattern whose
intensities already include LP; the slope of ratio(ref/standard) vs 2theta is
~0 when the angular factors agree, and strongly POSITIVE when LP is missing
(measured/standard boosts low angle; an LP-free calc is relatively too strong
at high angle -> ratio rises with 2theta).

Keep/reject gate: a reference is CLEARED if |slope| is small (observed-space);
otherwise flagged for provenance. Verdict anchored on quartz (measured, ICDD
46-1045) + corundum (calculated CS, ICDD 46-1212) - both high-confidence
standards; the others use approximate standards and only corroborate.
"""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO, "tools"))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
import prototype_nonclay as P  # noqa: E402

REFS = [
    "quartz.txt", "talc.txt", "Clinoptilolite_LargeCS.txt",
    "Albite_LargeCS_Bis-1.txt", "Albite_SmallCS_Bis-1.txt",
    "Corundum_LargeCS.txt", "Corundum_SmallCS.txt",
    "Orthoclase_LargeCS.txt", "Orthoclase_SmallCS.txt",
]

# Standard powder patterns (Cu Ka), OBSERVED intensities (LP already in them).
STANDARDS = {
    "quartz": P._QUARTZ_STANDARD,                      # ICDD 46-1045  (HIGH)
    "corundum": ((25.58, 45), (35.15, 100), (37.78, 21), (43.36, 66),
                 (52.55, 34), (57.50, 89), (61.12, 14), (66.52, 34),
                 (68.21, 54)),                          # ICDD 46-1212  (HIGH)
    "talc": ((19.0, 45), (28.6, 80), (34.5, 35), (48.7, 20),
             (54.1, 12), (60.0, 25)),                   # approx
    "albite": ((23.55, 28), (24.28, 24), (27.0, 40), (27.75, 100),
               (30.4, 18), (35.6, 14), (50.9, 10)),     # approx
    "orthoclase": ((21.0, 20), (25.66, 20), (27.0, 45), (27.5, 100),
                   (30.8, 20), (41.7, 12), (50.7, 10)),  # approx
    "clinoptilolite": ((11.15, 25), (22.4, 60), (30.0, 40), (32.7, 20)),  # approx
}
CONF = {"quartz": "HIGH", "corundum": "HIGH", "talc": "approx",
        "albite": "approx", "orthoclase": "approx", "clinoptilolite": "approx"}


def mineral_of(fname):
    low = fname.lower()
    for m in STANDARDS:
        if m in low:
            return m
    return None


def main():
    print("=" * 78)
    print("E1  reference-space (LP) gate")
    print("=" * 78)

    loaded = {}
    print("\n-- load + sanity --")
    for f in REFS:
        ph = P.load_reference(f)
        x, y = np.asarray(ph.raw_pattern_x), np.asarray(ph.raw_pattern_y)
        loaded[f] = ph
        print("%-28s pts %5d  2th %.1f-%.1f  max %.4g  finite %s  %s"
              % (f, x.size, x.min(), x.max(), float(np.max(y)),
                 bool(np.all(np.isfinite(y))),
                 "CALCULATED (CS)" if "cs" in f.lower() else "measured?"))

    print("\n-- reference-space slope test (ratio ref/standard vs 2theta) --")
    print("slope ~ 0  => observed-space, LP present (OK)")
    print("slope >> 0 => LP MISSING (calc |F|^2 only) -> would misweight the fit")
    results = {}
    for f in REFS:
        m = mineral_of(f)
        if m is None:
            print("%-28s  (no standard available)" % f)
            continue
        rows, trend = P.check_reference_space(loaded[f], standard=STANDARDS[m])
        ok = abs(trend) < 0.01
        results[f] = (m, trend, ok)
        print("%-28s [%-6s std] slope %+.5f /deg  ->  %s"
              % (f, CONF[m], trend,
                 "OK (LP present)" if ok else "SUSPECT (space mismatch)"))

    # Full ratio tables for the two HIGH-confidence anchors.
    for f in ("quartz.txt", "Corundum_LargeCS.txt"):
        m = mineral_of(f)
        rows, trend = P.check_reference_space(loaded[f], standard=STANDARDS[m])
        print("\n-- anchor detail: %s vs %s standard (slope %+.5f) --"
              % (f, m, trend))
        print("%8s %10s %12s %8s" % ("2theta", "standard", "ref_norm", "ratio"))
        for pos, std, norm, ratio in rows:
            print("%8.2f %10d %12.1f %8.2f" % (pos, std, norm, ratio))

    # CS-pair agreement: Large vs Small of the same mineral should give the
    # same space verdict (only peak WIDTH differs, not the angular factors).
    print("\n-- Large/Small CS agreement (same mineral, same pipeline) --")
    for m in ("albite", "corundum", "orthoclase"):
        pair = [f for f in results if mineral_of(f) == m]
        if len(pair) == 2:
            slopes = [results[f][1] for f in pair]
            print("%-12s slopes %s  agree=%s"
                  % (m, ["%+.5f" % s for s in slopes],
                     abs(slopes[0] - slopes[1]) < 0.01))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
