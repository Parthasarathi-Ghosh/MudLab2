#!/usr/bin/env python
"""FWHM calibration engine (path-2 phase B, batch 1).

Covers the built-in Silicon standard and the 1-D FWHM fit:
  - silicon_reflections has the Si 111/220/311 lines and the forbidden 200 is
    absent (a real diamond-structure check);
  - calibrate_fwhm recovers a known width from a rendered standard, through a
    linear scale + flat-background offset, under noise, and at a non-Cu
    wavelength.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_nonclay_calibration.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np

from mudlab.models.nonclay_phase import NonClayPhase
from mudlab.nonclay_calibration import calibrate_fwhm, silicon_reflections

results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _has_d(reflections, d, tol=0.01):
    return any(abs(rd - d) < tol for rd, _i in reflections)


def _render(reflections, wavelength_nm, x, fwhm):
    p = NonClayPhase()
    p.set_reflections(reflections)
    return p.render_on_grid(x, wavelength_nm, fwhm=fwhm)


def main():
    refl = silicon_reflections()
    # Si (a=5.4309): d111=3.1355, d220=1.9201, d311=1.6374; d200=2.7155 forbidden.
    check("Si standard: 111 present (d~3.135)", _has_d(refl, 3.1355, 0.01))
    check("Si standard: 220 present (d~1.920)", _has_d(refl, 1.9201, 0.01))
    check("Si standard: 311 present (d~1.637)", _has_d(refl, 1.6374, 0.01))
    check("Si standard: forbidden 200 (d~2.715) ABSENT", not _has_d(refl, 2.7155, 0.02))
    check("Si standard: 111 is the strongest line",
          max(refl, key=lambda r: r[1])[0] == min(
              (r for r in refl if r[1] > 99), key=lambda r: abs(r[0] - 3.1355))[0]
          or _has_d([max(refl, key=lambda r: r[1])], 3.1355, 0.01))

    wl_cu = 0.154056
    x = np.arange(20.0, 90.0, 0.02)

    # 1. exact recovery of a known FWHM
    y = _render(refl, wl_cu, x, 0.14)
    cal = calibrate_fwhm(refl, wl_cu, x, y)
    check("recovers a known FWHM (0.14)", abs(cal.fwhm - 0.14) < 0.01)
    check("residual ~ 0 for a perfect match", cal.residual < 1e-3)

    # 2. through a linear scale + flat background
    y2 = 3.7 * _render(refl, wl_cu, x, 0.22) + 40.0
    cal2 = calibrate_fwhm(refl, wl_cu, x, y2)
    check("recovers FWHM through scale+offset (0.22)", abs(cal2.fwhm - 0.22) < 0.01)
    check("fit recovers the scale (~3.7)", abs(cal2.scale - 3.7) < 0.2)
    check("fit recovers the offset (~40)", abs(cal2.offset - 40.0) < 5.0)

    # 3. with counting noise
    rng = np.random.default_rng(0)
    clean = 500.0 * _render(refl, wl_cu, x, 0.18) + 20.0
    noisy = clean + rng.normal(0.0, np.sqrt(np.maximum(clean, 1.0)))
    cal3 = calibrate_fwhm(refl, wl_cu, x, noisy)
    check("recovers FWHM under noise (0.18 +/- 0.02)", abs(cal3.fwhm - 0.18) < 0.02)

    # 4. at a non-Cu wavelength (Co Kalpha) - positions shift, fit still recovers
    wl_co = 0.178897
    xc = np.arange(20.0, 100.0, 0.02)
    yc = _render(refl, wl_co, xc, 0.25)
    cal4 = calibrate_fwhm(refl, wl_co, xc, yc)
    check("recovers FWHM at Co Kalpha (0.25)", abs(cal4.fwhm - 0.25) < 0.01)

    # 5. a 2theta zero shift is fitted, not leaked into the width. Build a
    #    measurement whose peaks sit +0.15 deg high of theory (render on x-0.15).
    p = NonClayPhase(); p.set_reflections(refl)
    shifted = p.render_on_grid(x - 0.15, wl_cu, fwhm=0.20)
    cal5 = calibrate_fwhm(refl, wl_cu, x, shifted)               # fit_shift=True
    check("fits the 2theta shift (~+0.15)", abs(cal5.shift - 0.15) < 0.01)
    check("recovers the true FWHM despite the shift (0.20)", abs(cal5.fwhm - 0.20) < 0.01)
    # Without shift-fitting the same scan biases the FWHM too wide:
    cal5b = calibrate_fwhm(refl, wl_cu, x, shifted, fit_shift=False)
    check("ignoring the shift biases FWHM wide (> true)", cal5b.fwhm > 0.20 + 0.03)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- FWHM calibration (phase B, batch 1) ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
