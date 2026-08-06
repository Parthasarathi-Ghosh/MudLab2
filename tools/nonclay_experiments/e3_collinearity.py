#!/usr/bin/env python
"""E3 - reference-collinearity guard.

The Large/Small-CS reference pairs are near-duplicates (same peaks, different
width). In one design matrix they are severely collinear, and Finding 5 showed
the multi-reference fit then 'invents minerals' - splitting spurious signal
between the collinear columns while chasing the clay misfit.

Demonstrate the pathology and a guard on the un-spiked Dh537A AD residual
(AD has the best clay fit; Dh537A has ~no albite, so any albite is spurious):

  1. collinearity diagnostics: pairwise cosine of the reference rows on the
     specimen grid + condition number of the reference Gram matrix.
  2. instability: perturb the residual with small noise many times, refit the
     collinear set, and show the individual albite-L / albite-S amplitudes have
     huge scatter while their SUM (and quartz) are stable - the collinearity
     signature.
  3. guard: collapse near-duplicate columns (cosine > 0.98) to one, refit, show
     the amplitudes become stable and albite collapses toward 0.

Keep the guard if it removes the split/instability without changing quartz.
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
REFS = ["quartz.txt", "Albite_LargeCS_Bis-1.txt", "Albite_SmallCS_Bis-1.txt"]


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na and nb else 0.0


def fit(refs_rows, clay, corr, target):
    """Bounded LSQ: reference amplitudes >= 0, clay+corr nuisances free."""
    k = len(refs_rows)
    A = np.column_stack([*refs_rows, clay, corr])
    lower = np.array([0.0] * k + [-np.inf, -np.inf])
    upper = np.full(k + 2, np.inf)
    return lsq_linear(A, target, bounds=(lower, upper), method="bvls").x[:k]


def main():
    print("=" * 80)
    print("E3  reference collinearity + guard (Dh537A AD, un-spiked)")
    print("=" * 80)
    refs = [P.load_reference(f) for f in REFS]
    names = [r.name for r in refs]

    proj = load_mud(MUD)
    mix = proj.mixtures[0]
    mix.calculate()
    ad = [s for s in mix.specimens if s is not None][0]
    print("specimen: %s" % ad.name)

    s1 = P.stage1(ad)
    x, residual, clay = s1["x"], s1["residual"], s1["clay"]
    corr = get_machine_correction_range(ad.goniometer, np.radians(x * 0.5))
    rows = P.reference_basis(ad, refs)   # one row per reference on the AD grid

    # 1. Collinearity diagnostics.
    print("\n-- collinearity of the reference columns on the specimen grid --")
    print("%-26s %-26s cosine" % ("ref A", "ref B"))
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            print("%-26s %-26s %.4f" % (names[i], names[j],
                                        cosine(rows[i], rows[j])))
    G = rows @ rows.T
    cond = float(np.linalg.cond(G))
    print("condition number of reference Gram matrix: %.3e" % cond)

    # 2. Instability under small perturbations (collinear set).
    print("\n-- amplitude stability under residual noise (50 draws) --")
    rng = np.random.default_rng(0)
    noise = 0.05 * float(np.sqrt(np.mean(residual ** 2)))
    draws = []
    for _ in range(50):
        tgt = residual + rng.normal(0.0, noise, size=residual.shape)
        draws.append(fit(list(rows), clay, corr, tgt))
    draws = np.array(draws)
    for k, nm in enumerate(names):
        print("   %-26s amp %.4f +/- %.4f" % (nm, draws[:, k].mean(), draws[:, k].std()))
    alb_sum = draws[:, 1] + draws[:, 2]
    print("   %-26s amp %.4f +/- %.4f  <- SUM of the collinear pair"
          % ("albite L+S", alb_sum.mean(), alb_sum.std()))

    # 3. Guard: collapse near-duplicate columns (cosine > 0.98) to their mean.
    print("\n-- guard: merge columns with cosine > 0.98 --")
    keep, merged_into = list(range(len(rows))), {}
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if j in keep and cosine(rows[i], rows[j]) > 0.98 and i in keep:
                keep.remove(j)
                merged_into.setdefault(i, [i]).append(j)
    guard_rows, guard_names = [], []
    for i in keep:
        members = merged_into.get(i, [i])
        guard_rows.append(np.mean([rows[m] for m in members], axis=0))
        guard_names.append("+".join(names[m].split("_")[0] for m in members)
                            if len(members) > 1 else names[i])
    print("   columns after guard: %s" % guard_names)
    draws_g = []
    for _ in range(50):
        tgt = residual + rng.normal(0.0, noise, size=residual.shape)
        draws_g.append(fit(guard_rows, clay, corr, tgt))
    draws_g = np.array(draws_g)
    for k, nm in enumerate(guard_names):
        print("   %-26s amp %.4f +/- %.4f" % (nm, draws_g[:, k].mean(), draws_g[:, k].std()))

    # Quartz must be unchanged by the guard.
    q_before = draws[:, 0].mean()
    q_after = draws_g[:, guard_names.index([n for n in guard_names
                                            if "quartz" in n][0])].mean()
    print("\n   quartz amp:  collinear %.4f  ->  guarded %.4f  (delta %+.4f)"
          % (q_before, q_after, q_after - q_before))
    print("   albite individual std:  %.4f / %.4f  ->  merged std %.4f"
          % (draws[:, 1].std(), draws[:, 2].std(),
             draws_g[:, [i for i, n in enumerate(guard_names)
                         if "Albite" in n or "albite" in n][0]].std()
             if any("lbite" in n for n in guard_names) else float("nan")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
