#!/usr/bin/env python
"""E2 - shared cross-specimen non-clay fraction vs per-specimen.

Quartz is a property of the SAMPLE, not of the AD/EG/400 prep, yet the Stage-2
estimator currently fits each specimen independently. The per-specimen error is
dominated by the clay MISFIT projected onto the reference (Finding 4), which is
a different random draw in each specimen. Fitting ONE shared quartz amplitude
across all specimens (with per-specimen clay/correction nuisance columns still
free) should average that projection down.

Test: spike every specimen with the SAME absolute quartz amplitude c
(c*I_quartz on each specimen's own grid), so the truth a_true = c is genuinely
shared. Re-run the shipped clay optimize. Then recover c two ways:
  (A) per-specimen: stage2_nuisance on each specimen -> a_i   (independent)
  (B) shared      : one bounded LSQ with a single quartz column spanning all
                    specimens + per-specimen [clay | correction] nuisance cols.
Metric: bias and spread of the estimates vs c. Keep 'shared' if it lowers the
RMS error and the c=0 false-positive relative to per-specimen.
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


def specimen_blocks(specimens, quartz):
    """(residual, quartz_row, clay_shape, correction) per specimen, post-fit."""
    blocks = []
    for s in specimens:
        s1 = P.stage1(s)
        x = s1["x"]
        theta = np.radians(x * 0.5)
        corr = get_machine_correction_range(s.goniometer, theta)
        q = P.reference_basis(s, [quartz])[0]
        blocks.append((s1["residual"], q, s1["clay"], corr))
    return blocks


def shared_amplitude(blocks):
    """One quartz amplitude shared across specimens; per-specimen clay+corr
    nuisances free. Returns the shared a (>= 0)."""
    S = len(blocks)
    n_tot = sum(len(r) for r, _, _, _ in blocks)
    A = np.zeros((n_tot, 1 + 2 * S))
    tgt = np.zeros(n_tot)
    row = 0
    for i, (r, q, clay, corr) in enumerate(blocks):
        n = len(r)
        sl = slice(row, row + n)
        A[sl, 0] = q
        A[sl, 1 + 2 * i] = clay
        A[sl, 1 + 2 * i + 1] = corr
        tgt[sl] = r
        row += n
    lower = np.array([0.0] + [-np.inf] * (2 * S))
    upper = np.full(1 + 2 * S, np.inf)
    sol = lsq_linear(A, tgt, bounds=(lower, upper), method="bvls")
    return float(sol.x[0])


def per_specimen_amplitudes(specimens, quartz):
    out = []
    for s in specimens:
        basis = P.reference_basis(s, [quartz])
        fit = P.stage2_nuisance(s, basis, ["quartz"])
        out.append(float(fit["amps"][0]))
    return out


def main():
    print("=" * 78)
    print("E2  shared vs per-specimen quartz amplitude (Dh537A)")
    print("=" * 78)
    quartz = P.load_reference("quartz.txt")

    # Pick c-levels from the un-spiked clay/quartz areas so they are meaningful.
    proj0 = load_mud(MUD)
    mix0 = proj0.mixtures[0]
    mix0.calculate()
    specs0 = [s for s in mix0.specimens if s is not None]
    a_clay = np.mean([P.stage1(s)["A_clay"] for s in specs0])
    a_q = np.mean([P.area(P.reference_basis(s, [quartz])[0],
                          s.experimental_pattern[0]) for s in specs0])
    names = [s.name for s in specs0]
    print("specimens: %s" % ", ".join(names))
    print("mean clay area %.1f, mean quartz-ref area %.1f" % (a_clay, a_q))

    per_rows = []   # (c, [a_i], rmse_per)
    shared_rows = []  # (c, a_shared, err_shared)
    for target in (0.0, 0.02, 0.05, 0.10, 0.20):
        c = target * a_clay / a_q     # SAME absolute amplitude for all specimens
        proj = load_mud(MUD)
        mix = proj.mixtures[0]
        mix.calculate()
        specs = [s for s in mix.specimens if s is not None]
        for s in specs:
            x, exp = s.experimental_pattern
            q = P.reference_basis(s, [quartz])[0]
            s.set_experimental_pattern(x, exp + c * q)
        rp = mix.optimize()

        a_i = per_specimen_amplitudes(specs, quartz)
        blocks = specimen_blocks(specs, quartz)
        a_sh = shared_amplitude(blocks)

        rmse_per = float(np.sqrt(np.mean([(a - c) ** 2 for a in a_i])))
        err_sh = a_sh - c
        per_rows.append((c, a_i, rmse_per))
        shared_rows.append((c, a_sh, err_sh))
        print("\n-- c=%.4f (target %.0f%%, mean Rp %.2f) --"
              % (c, target * 100, rp))
        print("   per-specimen a_i : %s" % ["%.4f" % a for a in a_i])
        print("   per-spec bias    : %s" % ["%+.4f" % (a - c) for a in a_i])
        print("   per-spec RMSE    : %.4f" % rmse_per)
        print("   SHARED a         : %.4f   (bias %+.4f)" % (a_sh, err_sh))

    print("\n" + "=" * 78)
    print("SUMMARY  (a_true = c; want small bias + small spread)")
    print("=" * 78)
    print("%8s %10s %12s %12s %12s %12s"
          % ("c", "per RMSE", "per spread", "shared a", "shared |err|",
             "shared better?"))
    for (c, a_i, rmse_per), (_c, a_sh, err_sh) in zip(per_rows, shared_rows):
        spread = float(np.max(a_i) - np.min(a_i))
        better = abs(err_sh) <= rmse_per
        print("%8.4f %10.4f %12.4f %12.4f %12.4f %12s"
              % (c, rmse_per, spread, a_sh, abs(err_sh), "yes" if better else "no"))

    # Aggregate verdict.
    wins = sum(1 for (_c, _ai, rp), (_c2, _as, es) in zip(per_rows, shared_rows)
               if abs(es) <= rp)
    print("\nshared beat per-specimen RMSE in %d / %d levels" % (wins, len(per_rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
