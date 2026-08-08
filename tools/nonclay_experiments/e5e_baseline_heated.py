#!/usr/bin/env python
"""(c) - two questions for the quartz strategy:

  Part 1 - does removing the BASELINE from the residual help the quartz fit on
           the MODELED AD/EG specimens? Fit quartz (a) standard nuisance vs
           (b) with a morphological baseline strip of residual + reference.
  Part 2 - on the HEATED, unmodeled, K-saturated specimens (random-powder-like
           for quartz per the user), measure the CLEAN quartz 100 (0.426) share
           of the baseline-stripped pattern across K-AD / K-400 / K-550, and the
           100/101 ratio - does the 101 get MORE contaminated with heating
           (collapsed-smectite 003 piling onto illite 003)?

Uses the measured quartz.txt for speed (reference choice is not the point here).
"""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d  # noqa: E402
from scipy.optimize import lsq_linear  # noqa: E402
from mudlab import nonclay  # noqa: E402
from mudlab.nonclay import estimator  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

DIR = os.path.join(os.path.expanduser("~"), "Downloads", "MudLab Test")
REF_Q = os.path.join(os.path.expanduser("~"), "Downloads", "Raw pattern phases", "quartz.txt")
Q100, Q101 = 20.86, 26.66
PROJECTS = ("348.mud", "416.mud", "AT460 r1.mud")


def baseline(y, w=230):
    w = max(3, int(w))
    b = minimum_filter1d(np.asarray(y, float), w, mode="nearest")
    b = maximum_filter1d(b, w, mode="nearest")
    return uniform_filter1d(b, w, mode="nearest")


def area(x, y, pos, w=0.35):
    sel = (np.asarray(x) >= pos - w) & (np.asarray(x) <= pos + w)
    return float(np.trapezoid(np.clip(np.asarray(y)[sel], 0, None), np.asarray(x)[sel])) if np.any(sel) else 0.0


def fit_quartz(residual, ref_row, clay, corr, strip=False):
    r, q, cl, co = residual.copy(), ref_row.copy(), clay.copy(), corr.copy()
    if strip:
        r = r - baseline(r)
        q = q - baseline(q)
    A = np.column_stack([q, cl, co])
    lo = np.array([0.0, -np.inf, -np.inf]); hi = np.full(3, np.inf)
    return float(lsq_linear(A, r, bounds=(lo, hi), method="bvls").x[0])


def main():
    quartz = nonclay.load_reference(REF_Q, name="quartz")
    print("PART 1 - baseline strip on the MODELED Ca-AD residual (quartz area, arb.)")
    print("%-14s %12s %12s %8s" % ("project", "standard", "baseline-strip", "delta%"))
    for proj in PROJECTS:
        mix = load_mud(os.path.join(DIR, proj)).mixtures[0]; mix.calculate()
        ad = [s for s in mix.specimens if s is not None][0]
        x, residual, clay, corr = estimator.specimen_residual(ad)
        row = estimator.reference_intensities(ad, [quartz])[0]
        a_std = fit_quartz(residual, row, clay, corr, strip=False) * area(x, row, Q101) / 1.0
        amp_std = fit_quartz(residual, row, clay, corr, strip=False)
        amp_bs = fit_quartz(residual, row, clay, corr, strip=True)
        aq_std = estimator.area(amp_std * row, x)
        aq_bs = estimator.area(amp_bs * row, x)
        d = 100 * (aq_bs - aq_std) / aq_std if aq_std else 0
        print("%-14s %12.1f %12.1f %+7.0f%%" % (proj, aq_std, aq_bs, d))

    print("\nPART 2 - heated K-series: clean quartz 100 (0.426) share of the "
          "baseline-stripped pattern, + 100/101")
    print("%-26s %10s %10s %8s" % ("specimen", "Q100 share%", "Q101 share%", "100/101"))
    for proj in PROJECTS:
        P = load_mud(os.path.join(DIR, proj))
        mixids = {id(s) for m in P.mixtures for s in m.specimens if s is not None}
        loose = [s for s in (getattr(P, "specimens", []) or []) if id(s) not in mixids]
        for s in sorted(loose, key=lambda z: z.name):
            x, y = s.experimental_pattern
            x, y = np.asarray(x, float), np.asarray(y, float)
            ybs = np.clip(y - baseline(y), 0, None)
            tot = float(np.trapezoid(ybs, x)) or 1.0
            a100, a101 = area(x, ybs, Q100), area(x, ybs, Q101)
            print("%-26s %9.2f%% %9.2f%% %8.2f"
                  % (s.name, 100 * a100 / tot, 100 * a101 / tot, a100 / a101 if a101 else 0))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
