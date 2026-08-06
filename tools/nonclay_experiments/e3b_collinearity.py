#!/usr/bin/env python
"""E3b - collinearity guard, with a KNOWN albite spike so the pathology shows.

E3 found albite L/S cosine 0.979 (Gram cond 140) - genuinely collinear - but on
the un-spiked good-fit AD residual the nuisance + non-negativity fit correctly
returns a stable zero, so there was nothing to split. Here we ADD a known amount
of albite (as the LargeCS curve) to AD's experimental, re-run the shipped clay
fit, then fit [quartz | albite_L | albite_S] + nuisances. Because L and S are
near-duplicates, the ALLOCATION between them is ill-determined: under small
residual noise the mass sloshes L<->S while the SUM is stable. The guard merges
cosine>0.97 columns to one, giving a single stable albite number.

Truth: all the spike is on L (amp c on L, 0 on S), total albite area = c*area(L).
Keep the guard if it (a) makes the albite estimate stable and single-valued and
(b) leaves quartz and the albite TOTAL unchanged.
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
COS_MERGE = 0.97


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na and nb else 0.0


def fit_amps(cols, clay, corr, target):
    k = len(cols)
    A = np.column_stack([*cols, clay, corr])
    lo = np.array([0.0] * k + [-np.inf, -np.inf])
    hi = np.full(k + 2, np.inf)
    return lsq_linear(A, target, bounds=(lo, hi), method="bvls").x[:k]


def main():
    print("=" * 80)
    print("E3b  collinearity guard with a known albite spike (Dh537A AD)")
    print("=" * 80)
    quartz = P.load_reference("quartz.txt")
    albL = P.load_reference("Albite_LargeCS_Bis-1.txt")
    albS = P.load_reference("Albite_SmallCS_Bis-1.txt")

    proj = load_mud(MUD)
    mix = proj.mixtures[0]
    mix.calculate()
    ad = [s for s in mix.specimens if s is not None][0]

    # Spike AD with albite (LargeCS) at ~10% of the clay area, then re-fit clays.
    x0, exp0 = ad.experimental_pattern
    albL_row0 = P.reference_basis(ad, [albL])[0]
    a_clay0 = P.stage1(ad)["A_clay"]
    c = 0.10 * a_clay0 / P.area(albL_row0, x0)
    ad.set_experimental_pattern(x0, exp0 + c * albL_row0)
    mix.optimize()

    s1 = P.stage1(ad)
    x, residual, clay = s1["x"], s1["residual"], s1["clay"]
    corr = get_machine_correction_range(ad.goniometer, np.radians(x * 0.5))
    qrow, lrow, srow = P.reference_basis(ad, [quartz, albL, albS])
    a_l, a_s = P.area(lrow, x), P.area(srow, x)
    true_area = c * a_l
    print("spiked albite (true) area = %.1f  (10%% of clay)" % true_area)
    print("albite L/S cosine %.4f   quartz/albite cosine %.4f"
          % (cosine(lrow, srow), cosine(qrow, lrow)))

    rng = np.random.default_rng(1)
    noise = 0.05 * float(np.sqrt(np.mean(residual ** 2)))

    def perturbed_areas(build):
        rows_area = []
        for _ in range(80):
            tgt = residual + rng.normal(0.0, noise, size=residual.shape)
            cols, areas = build()
            amps = fit_amps(cols, clay, corr, tgt)
            rows_area.append([amp * ar for amp, ar in zip(amps, areas)])
        return np.array(rows_area)

    # --- collinear set: quartz + albite_L + albite_S ---
    coll = perturbed_areas(lambda: ([qrow, lrow, srow],
                                    [P.area(qrow, x), a_l, a_s]))
    q_area, l_area, s_area = coll[:, 0], coll[:, 1], coll[:, 2]
    alb_sum = l_area + s_area
    print("\n-- collinear fit [quartz | albite_L | albite_S] (80 noise draws) --")
    print("   quartz     area %8.1f +/- %6.1f" % (q_area.mean(), q_area.std()))
    print("   albite_L   area %8.1f +/- %6.1f" % (l_area.mean(), l_area.std()))
    print("   albite_S   area %8.1f +/- %6.1f" % (s_area.mean(), s_area.std()))
    print("   albite SUM area %8.1f +/- %6.1f  (true %.1f)"
          % (alb_sum.mean(), alb_sum.std(), true_area))
    print("   allocation instability: std(L)/mean(SUM) = %.1f%%"
          % (100.0 * l_area.std() / alb_sum.mean() if alb_sum.mean() else 0.0))

    # --- guarded set: merge albite_L & albite_S (cosine>0.97) to their mean ---
    merged = 0.5 * (lrow + srow)
    merged_area = 0.5 * (a_l + a_s)
    guard = perturbed_areas(lambda: ([qrow, merged],
                                     [P.area(qrow, x), merged_area]))
    qg, albg = guard[:, 0], guard[:, 1]
    print("\n-- guarded fit [quartz | albite(merged)] --")
    print("   quartz          area %8.1f +/- %6.1f" % (qg.mean(), qg.std()))
    print("   albite(merged)  area %8.1f +/- %6.1f  (true %.1f)"
          % (albg.mean(), albg.std(), true_area))

    print("\n-- verdict --")
    print("   albite allocation std: L %.1f  S %.1f  ->  merged %.1f"
          % (l_area.std(), s_area.std(), albg.std()))
    print("   albite total bias:  collinear %+.1f   guarded %+.1f"
          % (alb_sum.mean() - true_area, albg.mean() - true_area))
    print("   quartz spurious:    collinear %.1f     guarded %.1f"
          % (q_area.mean(), qg.mean()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
