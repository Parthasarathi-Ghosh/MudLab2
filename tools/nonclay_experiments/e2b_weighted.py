#!/usr/bin/env python
"""E2b - is the right cross-specimen combination QUALITY-WEIGHTED, not naive?

E2 showed the per-specimen error is a constant OFFSET set by clay-fit quality
(AD~0, EG~-0.50, 400~-0.10), and that an unweighted shared fit just AVERAGES it
(~-0.19), helping the worst specimen but hurting the best. Averaging fixes
variance, not bias. So compare four estimators of the shared quartz amplitude c:

  per-spec-mean : mean of the independent a_i          (naive)
  shared-unw    : joint fit, all specimens equal        (E2)
  shared-wRp    : joint fit, each specimen weighted 1/Rp^2 (observable quality)
  best-Rp       : the single specimen with the lowest Rp (use the best fit only)

Weighting uses the OBSERVABLE per-specimen Rp (no truth needed). Keep the
estimator with the smallest |bias| across spike levels.
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
from scipy.optimize import lsq_linear  # noqa: E402
import prototype_nonclay as P  # noqa: E402
from mudlab.calculations.goniometer import get_machine_correction_range  # noqa: E402
from mudlab.calculations import statistics as ST  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

MUD = os.path.join(_REPO, "tools", "sample_projects", "Dh537A.mud")


def specimen_rp(s):
    x, exp = s.experimental_pattern
    total = s.calculated_pattern[1]
    return float(ST.Rp(np.asarray(exp), np.asarray(total)))


def blocks_for(specimens, quartz):
    out = []
    for s in specimens:
        s1 = P.stage1(s)
        x = s1["x"]
        corr = get_machine_correction_range(s.goniometer, np.radians(x * 0.5))
        q = P.reference_basis(s, [quartz])[0]
        out.append((s1["residual"], q, s1["clay"], corr, specimen_rp(s)))
    return out


def shared(blocks, weighted):
    """Joint fit of one shared quartz amplitude + per-specimen [clay|corr].
    weighted=True scales each specimen block by 1/Rp^2 (sqrt in the LSQ)."""
    S = len(blocks)
    n_tot = sum(len(b[0]) for b in blocks)
    A = np.zeros((n_tot, 1 + 2 * S))
    tgt = np.zeros(n_tot)
    row = 0
    for i, (r, q, clay, corr, rp) in enumerate(blocks):
        n = len(r)
        w = (1.0 / rp ** 2) if weighted else 1.0
        sw = np.sqrt(w)
        sl = slice(row, row + n)
        A[sl, 0] = q * sw
        A[sl, 1 + 2 * i] = clay * sw
        A[sl, 1 + 2 * i + 1] = corr * sw
        tgt[sl] = r * sw
        row += n
    lower = np.array([0.0] + [-np.inf] * (2 * S))
    upper = np.full(1 + 2 * S, np.inf)
    return float(lsq_linear(A, tgt, bounds=(lower, upper), method="bvls").x[0])


def main():
    print("=" * 82)
    print("E2b  quality-weighted vs naive cross-specimen combination (Dh537A)")
    print("=" * 82)
    quartz = P.load_reference("quartz.txt")

    proj0 = load_mud(MUD)
    mix0 = proj0.mixtures[0]
    mix0.calculate()
    specs0 = [s for s in mix0.specimens if s is not None]
    a_clay = np.mean([P.stage1(s)["A_clay"] for s in specs0])
    a_q = np.mean([P.area(P.reference_basis(s, [quartz])[0],
                          s.experimental_pattern[0]) for s in specs0])

    print("%8s %6s %10s %11s %11s %11s %11s"
          % ("c", "Rps", "per-mean", "shared-unw", "shared-wRp", "best-Rp", "winner"))
    tally = {"per-mean": 0, "shared-unw": 0, "shared-wRp": 0, "best-Rp": 0}
    for target in (0.02, 0.05, 0.10, 0.20):
        c = target * a_clay / a_q
        proj = load_mud(MUD)
        mix = proj.mixtures[0]
        mix.calculate()
        specs = [s for s in mix.specimens if s is not None]
        for s in specs:
            x, exp = s.experimental_pattern
            s.set_experimental_pattern(x, exp + c * P.reference_basis(s, [quartz])[0])
        mix.optimize()

        blocks = blocks_for(specs, quartz)
        rps = [b[4] for b in blocks]
        a_i = [float(P.stage2_nuisance(s, P.reference_basis(s, [quartz]),
                                       ["quartz"])["amps"][0]) for s in specs]
        est = {
            "per-mean": float(np.mean(a_i)),
            "shared-unw": shared(blocks, weighted=False),
            "shared-wRp": shared(blocks, weighted=True),
            "best-Rp": a_i[int(np.argmin(rps))],
        }
        errs = {k: abs(v - c) for k, v in est.items()}
        winner = min(errs, key=errs.get)
        tally[winner] += 1
        print("%8.4f %6s %10.4f %11.4f %11.4f %11.4f %11s"
              % (c, "/".join("%.0f" % r for r in rps),
                 est["per-mean"], est["shared-unw"], est["shared-wRp"],
                 est["best-Rp"], winner))
        print("%8s %6s %10s %+11.4f %+11.4f %+11.4f  (bias vs c)"
              % ("", "", "", est["shared-unw"] - c, est["shared-wRp"] - c,
                 est["best-Rp"] - c))

    print("\nwins by estimator: %s" % tally)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
