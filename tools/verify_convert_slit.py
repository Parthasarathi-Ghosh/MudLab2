#!/usr/bin/env python
"""Fixed <-> ADS divergence-slit conversion (old Specimen.convert_to_fixed /
convert_to_ads; Data menu "Convert data to fixed slit" / "Convert data to ADS").

An automatic divergence slit collects ~sin(theta) times the intensity a fixed
slit would at the same angle, so fixed -> ADS multiplies by sin(theta) and
ADS -> fixed divides by it. This covers the pure transform (pattern_ops.
convert_slit) and the Specimen model methods:

  - the factor is exactly sin(theta): x ADS = fixed, / ADS = fixed;
  - the two directions are inverse (a round trip is identity where theta > 0);
  - theta = 0 never divides by zero;
  - Specimen.convert_to_ads / convert_to_fixed apply it in place, emit
    data_changed, and are inverses; empty data is a safe no-op.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_convert_slit.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication

from mudlab.calculations import pattern_ops
from mudlab.models.specimen import Specimen

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def main():
    x = np.linspace(5.0, 70.0, 400)          # a normal 2-theta range (theta > 0)
    y = 100.0 + 50.0 * np.sin(x / 4.0) ** 2  # an arbitrary positive pattern
    sin_theta = np.sin(np.radians(x * 0.5))

    to_ads = pattern_ops.convert_slit(x, y, to_ads=True)
    to_fixed = pattern_ops.convert_slit(x, y, to_ads=False)
    check("fixed -> ADS multiplies by sin(theta)",
          np.allclose(to_ads, y * sin_theta))
    check("ADS -> fixed divides by sin(theta)",
          np.allclose(to_fixed, y / sin_theta))
    check("the two directions are not the same (real rescale)",
          not np.allclose(to_ads, to_fixed))

    # A round trip is the identity wherever theta > 0.
    round_trip = pattern_ops.convert_slit(x, to_ads, to_ads=False)
    check("ADS(fixed) round-trips to the original",
          np.allclose(round_trip, y, atol=1e-9))
    round_trip2 = pattern_ops.convert_slit(x, to_fixed, to_ads=True)
    check("fixed(ADS) round-trips to the original",
          np.allclose(round_trip2, y, atol=1e-9))

    # x is never mutated; result is a fresh array.
    check("the input y is not mutated",
          np.allclose(y, 100.0 + 50.0 * np.sin(x / 4.0) ** 2))

    # theta = 0 must not divide by zero; that point is left unchanged.
    x0 = np.array([0.0, 10.0, 20.0])
    y0 = np.array([7.0, 8.0, 9.0])
    fixed0 = pattern_ops.convert_slit(x0, y0, to_ads=False)
    check("theta = 0 never yields inf/nan", np.all(np.isfinite(fixed0)))
    check("theta = 0 point is left unchanged", fixed0[0] == 7.0)

    check("empty pattern is a safe no-op",
          pattern_ops.convert_slit(np.empty(0), np.empty(0), to_ads=True).size == 0)

    # --- Specimen model methods -------------------------------------------
    spec = Specimen(name="S")
    spec.set_experimental_pattern(x, y)
    fired = {"n": 0}
    spec.data_changed.connect(lambda: fired.__setitem__("n", fired["n"] + 1))

    spec.convert_to_ads()
    ex, ey = spec.experimental_pattern
    check("Specimen.convert_to_ads applies the transform",
          np.allclose(ey, y * sin_theta))
    check("convert_to_ads emits data_changed", fired["n"] == 1)

    spec.convert_to_fixed()
    _ex, ey2 = spec.experimental_pattern
    check("convert_to_fixed inverts convert_to_ads (round trip)",
          np.allclose(ey2, y, atol=1e-9))
    check("convert_to_fixed emits data_changed", fired["n"] == 2)

    empty = Specimen(name="E")
    empty.convert_to_ads()  # no experimental data
    check("converting a specimen with no data does not crash",
          not empty.has_experimental_data)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("--- fixed <-> ADS slit-conversion verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
