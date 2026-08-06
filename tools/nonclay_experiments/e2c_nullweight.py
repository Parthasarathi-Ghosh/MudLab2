#!/usr/bin/env python
"""E2c - is the LOCAL-quality weight (mis-registration null) the right
cross-specimen combiner?

E2/E2b: the per-specimen error is a LOCAL bias at the reference's peaks; global
Rp does NOT discriminate (AD~EG in Rp, opposite bias). The per-specimen
mis-registration NULL (Finding 8) measures exactly that local unreliability -
what the clay misfit can manufacture at the reference's peak shapes. Hypothesis:
weighting/gating specimens by 1/null^2 down-weights the biased specimen (EG) and
recovers c with less bias than shared-unweighted.

Spike all Dh537A specimens with the SAME absolute quartz amplitude c (truth
shared), re-fit clays, then compare estimators of c:
  shared-unw     joint fit, equal weights (E2 default)
  shared-wNull   joint fit, per-specimen weight 1/null^2 (LOCAL quality)
  best-null      the single specimen with the smallest null
Keep null-weighting if it lowers |bias| vs shared-unweighted.
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
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

MUD = os.path.join(_REPO, "tools", "sample_projects", "Dh537A.mud")


def block(s, quartz):
    s1 = P.stage1(s)
    x = s1["x"]
    corr = get_machine_correction_range(s.goniometer, np.radians(x * 0.5))
    q = P.reference_basis(s, [quartz])[0]
    return s1["residual"], q, s1["clay"], corr


def shared(blocks, weights):
    S = len(blocks)
    n = sum(len(b[0]) for b in blocks)
    A = np.zeros((n, 1 + 2 * S)); tgt = np.zeros(n); row = 0
    for i, (r, q, clay, corr) in enumerate(blocks):
        m = len(r); sw = np.sqrt(weights[i]); sl = slice(row, row + m)
        A[sl, 0] = q * sw; A[sl, 1 + 2 * i] = clay * sw
        A[sl, 1 + 2 * i + 1] = corr * sw; tgt[sl] = r * sw; row += m
    lo = np.array([0.0] + [-np.inf] * (2 * S)); hi = np.full(1 + 2 * S, np.inf)
    return float(lsq_linear(A, tgt, bounds=(lo, hi), method="bvls").x[0])


def main():
    print("=" * 84)
    print("E2c  null-weighted cross-specimen combination (Dh537A, quartz)")
    print("=" * 84)
    quartz = P.load_reference("quartz.txt")
    proj0 = load_mud(MUD); mix0 = proj0.mixtures[0]; mix0.calculate()
    specs0 = [s for s in mix0.specimens if s is not None]
    a_clay = np.mean([P.stage1(s)["A_clay"] for s in specs0])
    a_q = np.mean([P.area(P.reference_basis(s, [quartz])[0],
                          s.experimental_pattern[0]) for s in specs0])

    print("%8s %-22s %10s %10s %11s %10s"
          % ("c", "nulls (AD/EG/400)", "shared-unw", "shr-wNull", "best-null", "winner"))
    tally = {"shared-unw": 0, "shr-wNull": 0, "best-null": 0}
    for target in (0.05, 0.10, 0.20):
        c = target * a_clay / a_q
        proj = load_mud(MUD); mix = proj.mixtures[0]; mix.calculate()
        specs = [s for s in mix.specimens if s is not None]
        for s in specs:
            x, exp = s.experimental_pattern
            s.set_experimental_pattern(x, exp + c * P.reference_basis(s, [quartz])[0])
        mix.optimize()

        nulls = [max(P.null_threshold_pct(s, quartz), 1e-6) for s in specs]
        a_i = [float(P.stage2_nuisance(s, P.reference_basis(s, [quartz]),
                                       ["quartz"])["amps"][0]) for s in specs]
        blocks = [block(s, quartz) for s in specs]
        w_eq = [1.0] * len(specs)
        w_null = [1.0 / nu ** 2 for nu in nulls]
        est = {
            "shared-unw": shared(blocks, w_eq),
            "shr-wNull": shared(blocks, w_null),
            "best-null": a_i[int(np.argmin(nulls))],
        }
        errs = {k: abs(v - c) for k, v in est.items()}
        win = min(errs, key=errs.get); tally[win] += 1
        print("%8.4f %-22s %10.4f %10.4f %11.4f %10s"
              % (c, "/".join("%.2f" % nu for nu in nulls),
                 est["shared-unw"], est["shr-wNull"], est["best-null"], win))
        print("%8s %-22s %+10.4f %+10.4f %+11.4f  (bias vs c=%.4f)"
              % ("", "", est["shared-unw"] - c, est["shr-wNull"] - c,
                 est["best-null"] - c, c))
    print("\nwins: %s" % tally)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
