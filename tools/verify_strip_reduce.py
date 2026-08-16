#!/usr/bin/env python
"""Strip Peak "Keep peak %".

Strip Peak is a single unified operation: "Keep peak %" attenuates the peak
toward the straight line joining the range endpoints, keeping the chosen
fraction of its height above that line. 0 % is the classic strip (flatten onto
the line); 100 % leaves the data unchanged. Because the endpoints stay on the
line the background is continuous - no notch, unlike scaling the raw y. The
retained Noise level adds endpoint-scaled scatter, so Keep 0 % + noise
reproduces the old straight-line strip.

Covers:
  - pattern_ops.compute_reduce_pattern: endpoints preserved (no notch), keep=0
    == the endpoint line, keep=1 == the original, fractional keep works, the
    noise term is endpoint-scaled scatter around that result, degenerate -> None;
  - StripPeakDialog (one mode): Keep % allows fractions and cannot go below 0,
    defaults to 0 (strip), auto-estimates the noise floor on a range change;
    apply at Keep 0 strips (flattens onto the line), and apply at Keep 30 %
    attenuates the peak while leaving the window edges and the outside unchanged.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_strip_reduce.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication

from mudlab.calculations import pattern_ops as po
from mudlab.file_parsers.mud_project import load_mud
from mudlab.line_dialogs import StripPeakDialog

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


# ----------------------------------------------------------------------
# 1. pattern_ops.compute_reduce_pattern numerics (synthetic peak).
# ----------------------------------------------------------------------
def check_math():
    x = np.linspace(10.0, 30.0, 401)
    bg = 100.0 + 2.0 * (x - 10.0)                     # sloped background
    y = bg + 900.0 * np.exp(-((x - 20.0) / 0.4) ** 2)  # Gaussian peak
    s, e = 18.0, 22.0
    si = int(np.argmin(np.abs(x - s)))
    ei = int(np.argmin(np.abs(x - e)))

    for keep in (0.0, 0.3, 1.0):
        sp = po.compute_reduce_pattern(x, y, s, e, keep)   # no noise
        yn = po.apply_strip(x, y, sp)
        edges = abs(yn[si] - y[si]) < 1e-9 and abs(yn[ei] - y[ei]) < 1e-9
        outside = np.array_equal(yn[:si], y[:si]) and np.array_equal(yn[ei + 1:], y[ei + 1:])
        check("math keep=%.1f: endpoints preserved (no notch)" % keep, edges)
        check("math keep=%.1f: outside the window unchanged" % keep, outside)

    sp0 = po.compute_reduce_pattern(x, y, s, e, 0.0)
    line = sp0.slope * (sp0.section_x - sp0.startx) + sp0.avg_starty
    check("math keep=0 == endpoint background line", np.allclose(sp0.section_y, line))
    sp1 = po.compute_reduce_pattern(x, y, s, e, 1.0)
    orig = np.extract((x >= sp1.startx) & (x <= sp1.endx), y)
    check("math keep=1 == original data", np.allclose(sp1.section_y, orig))

    # Fractional keep (non-integer percentages map to these fractions).
    spf = po.compute_reduce_pattern(x, y, s, e, 0.125)
    linef = spf.slope * (spf.section_x - spf.startx) + spf.avg_starty
    origf = np.extract((x >= spf.startx) & (x <= spf.endx), y)
    check("math fractional keep=0.125 == line + 0.125*(y-line)",
          np.allclose(spf.section_y, linef + 0.125 * (origf - linef)))

    # Noise term: keep=0 + noise is the classic strip = line + scatter, with
    # the scatter bounded by the endpoint-scaled amplitude avg_endy*noise_level.
    spn = po.compute_reduce_pattern(x, y, s, e, 0.0, noise_level=0.2)
    dev = np.abs(spn.section_y - line)
    check("math keep=0 + noise records the noise level", spn.noise_level == 0.2)
    check("math keep=0 + noise = line + bounded scatter",
          np.std(dev) > 0 and dev.max() <= abs(spn.avg_endy) * 0.2 + 1e-9)

    check("math: degenerate range -> None",
          po.compute_reduce_pattern(x, y, 20.0, 20.0, 0.5) is None)


# ----------------------------------------------------------------------
# 2. StripPeakDialog behaviour on a real specimen.
# ----------------------------------------------------------------------
def _fixture_specimen():
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        for spec in project.specimens:
            if spec is not None and spec.has_experimental_data:
                return spec
    return None


def check_dialog():
    spec = _fixture_specimen()
    x, y = (np.asarray(a, float) for a in spec.experimental_pattern)
    peak_i = int(np.argmax(y))
    x0 = float(x[max(0, peak_i - 8)])
    x1 = float(x[min(len(x) - 1, peak_i + 8)])
    win = (x >= min(x0, x1)) & (x <= max(x0, x1))
    si = int(np.argmax(win))
    ei = len(win) - 1 - int(np.argmax(win[::-1]))

    dlg = StripPeakDialog(None, specimen=spec)
    check("no mode combo (single unified operation)", not hasattr(dlg.ui, "strip_mode"))
    check("Keep % allows fractions (decimals >= 1)", dlg.ui.keep_percent.decimals() >= 1)
    check("Keep % defaults to 0 (a plain strip)", dlg.ui.keep_percent.value() == 0.0)
    check("Keep % minimum is 0", dlg.ui.keep_percent.minimum() == 0.0)
    dlg.ui.keep_percent.setValue(-5.0)
    check("Keep % below 0 is not permitted (clamped to 0)", dlg.ui.keep_percent.value() >= 0.0)
    dlg.ui.keep_percent.setValue(12.5)
    check("Keep % accepts a non-integer value (12.5)", abs(dlg.ui.keep_percent.value() - 12.5) < 1e-9)

    # A range change copies compute_strip_pattern's noise estimate into the
    # spinbox (old strip behaviour), whatever its value for this window.
    est = spec.compute_strip_pattern(x0, x1)
    want = round(est.noise_level, 2) if est is not None else 0.0
    dlg.ui.strip_startx.setValue(x0)
    dlg.ui.strip_endx.setValue(x1)
    check("range change auto-estimates the noise floor (strip parity)",
          abs(dlg.ui.noise_level.value() - want) < 1e-2)

    # A hand-set noise value is sticky: later range changes must not clobber it.
    dlg.ui.noise_level.setValue(0.77)
    dlg.ui.strip_endx.setValue(float(x[max(0, peak_i + 6)]))   # nudge the range
    check("hand-set noise survives a range change (auto-estimate defers)",
          abs(dlg.ui.noise_level.value() - 0.77) < 1e-9)
    dlg.ui.strip_startx.setValue(float(x[max(0, peak_i - 10)]))
    check("hand-set noise still survives another range change",
          abs(dlg.ui.noise_level.value() - 0.77) < 1e-9)

    # Keep 0 + noise 0 -> flatten onto the endpoint line (the classic strip).
    spec_a = _fixture_specimen()
    xa, ya = (np.asarray(a, float) for a in spec_a.experimental_pattern)
    dlg_a = StripPeakDialog(None, specimen=spec_a)
    dlg_a.ui.strip_startx.setValue(x0)
    dlg_a.ui.strip_endx.setValue(x1)
    dlg_a.ui.keep_percent.setValue(0.0)
    dlg_a.ui.noise_level.setValue(0.0)
    dlg_a._apply()
    aa = np.asarray(spec_a.experimental_pattern[1], float)
    check("Keep 0 %: window flattened onto the endpoint line",
          abs(aa[si:ei + 1].max() - max(ya[si], ya[ei])) < 1e-6
          and aa[si:ei + 1].max() < ya[si:ei + 1].max())
    check("Keep 0 %: outside the window unchanged",
          np.array_equal(aa[:si], ya[:si]) and np.array_equal(aa[ei + 1:], ya[ei + 1:]))

    # Keep 30 % + noise 0 -> attenuate; edges + outside intact (no notch).
    spec_b = _fixture_specimen()
    xb, yb = (np.asarray(a, float) for a in spec_b.experimental_pattern)
    dlg_b = StripPeakDialog(None, specimen=spec_b)
    dlg_b.ui.strip_startx.setValue(x0)
    dlg_b.ui.strip_endx.setValue(x1)
    dlg_b.ui.noise_level.setValue(0.0)
    dlg_b.ui.keep_percent.setValue(30.0)
    dlg_b._apply()
    ab = np.asarray(spec_b.experimental_pattern[1], float)
    check("Keep 30 %: peak attenuated but still present",
          ab[si:ei + 1].max() < yb[si:ei + 1].max()
          and ab[si:ei + 1].max() > max(yb[si], yb[ei]))
    check("Keep 30 %: window edges unchanged (no notch)",
          abs(ab[si] - yb[si]) < 1e-6 and abs(ab[ei] - yb[ei]) < 1e-6)
    check("Keep 30 %: outside the window unchanged",
          np.array_equal(ab[:si], yb[:si]) and np.array_equal(ab[ei + 1:], yb[ei + 1:]))


def main():
    check_math()
    if _fixture_specimen() is None:
        print("No fixture with a specimen with data; skipping (exit 2).")
        return 2
    check_dialog()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- Strip Peak Keep-%% verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
