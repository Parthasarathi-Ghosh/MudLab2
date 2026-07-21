#!/usr/bin/env python
"""Durable harness for the data-operation dialogs (Batch D2), run head-less.

These dialogs shipped for a long time looking finished while applying
nothing: they opened, accepted OK, and silently discarded the input. So this
harness does not check that they *open* - it drives each one against a real
project and asserts the experimental pattern **actually changed** (and that
Peak Properties, a measurement, changes nothing).

It also covers the refusal paths, because a dialog that closes on a refusal is
indistinguishable from one that worked - the same failure this batch removed.
Each refusal must (a) leave the data untouched, (b) keep the dialog open, and
(c) tell the user why.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_data_op_dialogs.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project. The
underlying numerics are guarded by tools/verify_pattern_ops.py.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication, QMessageBox

# The refusal paths pop a modal QMessageBox, which blocks forever with nobody
# to dismiss it. Record the calls instead of showing them.
_boxes = []
QMessageBox.warning = staticmethod(
    lambda parent, title, text, *a, **k: _boxes.append((title, text))
)
QMessageBox.information = staticmethod(
    lambda parent, title, text, *a, **k: _boxes.append((title, text))
)

from mudlab.edit_specimen_dialog import EditSpecimenDialog
from mudlab.file_parsers.mud_project import load_mud
from mudlab.file_parsers.xrd_import import parse_pattern
from mudlab.line_dialogs import (
    AddNoiseDialog, PeakPropertiesDialog, RemoveBackgroundDialog,
    ShiftPatternDialog, SmoothDataDialog, StripPeakDialog,
)
from mudlab.models.marker import Marker
from mudlab.specimen_dialogs import TrimDataDialog

_FIXTURE_NAME = "308 r1.mud"
FIXTURE = os.path.join(_REPO, "tools", "sample_projects", _FIXTURE_NAME)
if not os.path.isfile(FIXTURE):
    FIXTURE = os.path.join(os.path.expanduser("~"), "Downloads", _FIXTURE_NAME)
if not os.path.isfile(FIXTURE):
    print("No sample project found; skipping (exit 2).")
    raise SystemExit(2)

app = QApplication([])
results = []


def check(label, ok):
    results.append((label, bool(ok)))


def fresh_specimen():
    """A freshly loaded project per case: these operations are destructive, so
    reusing one specimen would let each case see the previous one's damage."""
    project = load_mud(FIXTURE)
    spec = next(s for s in project.specimens if s.has_experimental_data)
    return project, spec


# --- Remove background (linear) ---
_, spec = fresh_specimen()
_, before = spec.experimental_pattern
before = before.copy()
dlg = RemoveBackgroundDialog(None, specimen=spec)
check("bg: position pre-filled with min(y)",
      abs(dlg.ui.bg_position.value() - float(np.min(before))) < 1e-4)
dlg.ui.bg_type.setCurrentIndex(0)
dlg.ui.bg_position.setValue(10.0)
dlg._on_accept()
_, after = spec.experimental_pattern
check("bg: subtracted the flat value", np.allclose(after, before - 10.0))
check("bg: dialog accepted", dlg.result() == 1)

# --- Background from a pattern FILE goes through the shared xrd_import
#     dispatcher, so every import format works here too (tested with .uxd). ---
import tempfile  # noqa: E402
from PySide6.QtWidgets import QFileDialog  # noqa: E402
_, spec = fresh_specimen()
_bgdir = tempfile.mkdtemp(prefix="mudlab_bgimport_")
_uxd = os.path.join(_bgdir, "bg.uxd")
with open(_uxd, "w", encoding="utf-8") as fh:
    fh.write("_STEPTIME=1.0\n_2THETACOUNTS\n"
             + "\n".join("%g %g" % (5.0 + i * 0.02, 100 + i) for i in range(50))
             + "\n")
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (_uxd, ""))
dlg = RemoveBackgroundDialog(None, specimen=spec)
dlg._browse_pattern()
check("bg: browse imports a .uxd via the shared dispatcher (parse_pattern)",
      getattr(dlg, "_bg_pattern", None) is not None
      and dlg.ui.bg_pattern_file.text() == _uxd)
os.remove(_uxd)
os.rmdir(_bgdir)

# --- Smooth ---
_, spec = fresh_specimen()
_, before = spec.experimental_pattern
before = before.copy()
dlg = SmoothDataDialog(None, specimen=spec)
check("smooth: degree pre-filled from type", dlg.ui.spin_degree.value() > 0)
dlg.ui.smooth_type.setCurrentIndex(2)  # Gaussian
check("smooth: degree updates with type", dlg.ui.spin_degree.value() == 3)
dlg._on_accept()
_, after = spec.experimental_pattern
check("smooth: pattern changed", not np.array_equal(before, after))
check("smooth: scatter reduced",
      float(np.std(np.diff(after))) < float(np.std(np.diff(before))))

# --- Add noise ---
_, spec = fresh_specimen()
_, before = spec.experimental_pattern
before = before.copy()
dlg = AddNoiseDialog(None, specimen=spec)
dlg.ui.spin_fraction.setValue(0.05)
dlg._on_accept()
_, after = spec.experimental_pattern
check("noise: pattern changed", not np.array_equal(before, after))
check("noise: scatter increased",
      float(np.std(np.diff(after))) > float(np.std(np.diff(before))))

# --- Shift ---
_, spec = fresh_specimen()
before_x, _ = spec.experimental_pattern
before_x = before_x.copy()
dlg = ShiftPatternDialog(None, specimen=spec)
check("shift: value disabled for a reference preset",
      not dlg.ui.spin_shift_value.isEnabled())
# Silicon: this fixture's silicon line sits ~0.49 deg below its theoretical
# position, so auto-detect must report that - a non-trivial detection.
dlg.ui.shift_position.setCurrentIndex(1)
check("shift: auto-detects the real offset (%.4f)"
      % dlg.ui.spin_shift_value.value(),
      abs(dlg.ui.spin_shift_value.value() - (-0.49307609)) < 1e-4)
dlg.ui.shift_position.setCurrentIndex(6)  # Manual
check("shift: value enabled in manual mode", dlg.ui.spin_shift_value.isEnabled())
check("shift: manual resets to 0 (not the previous reference's offset)",
      dlg.ui.spin_shift_value.value() == 0.0)
dlg.ui.spin_shift_value.setValue(0.05)
dlg._on_accept()
after_x, _ = spec.experimental_pattern
check("shift: x axis moved", not np.array_equal(before_x, after_x))
check("shift: manual mode subtracts a constant",
      np.allclose(after_x, before_x - 0.05))

# --- Strip peak ---
_, spec = fresh_specimen()
x, before = spec.experimental_pattern
before = before.copy()
dlg = StripPeakDialog(None, specimen=spec)
dlg.ui.strip_startx.setValue(float(x[500]))
dlg.ui.strip_endx.setValue(float(x[560]))
check("strip: noise level auto-estimated", dlg.ui.noise_level.value() != 0.0)
dlg._on_accept()
_, after = spec.experimental_pattern
inside = (x >= float(x[500])) & (x <= float(x[560]))
check("strip: window changed", not np.array_equal(before[inside], after[inside]))
check("strip: outside untouched", np.array_equal(before[~inside], after[~inside]))

# --- Peak properties (read-only) ---
_, spec = fresh_specimen()
_, before = spec.experimental_pattern
before = before.copy()
dlg = PeakPropertiesDialog(None, specimen=spec)
dlg.ui.peak_startx.setValue(float(x[500]))
dlg.ui.peak_endx.setValue(float(x[560]))
area = float(dlg.ui.peak_area_result.text())
fwhm = float(dlg.ui.peak_fwhm_result.text())
check("peak props: area computed live", area > 0)
check("peak props: fwhm computed live", fwhm > 0)
_, after = spec.experimental_pattern
check("peak props: pattern untouched (read-only)", np.array_equal(before, after))

# --- Trim ---
project, spec = fresh_specimen()
x, _ = spec.experimental_pattern
lo, hi = float(x[len(x) // 4]), float(x[3 * len(x) // 4])
spec.add_marker(Marker(label="doomed", position=float(x[0])))
dlg = TrimDataDialog(None, specimen=spec, specimens=list(project.specimens))
check("trim: range pre-filled from the specimen",
      abs(dlg.ui.spin_min_2theta.value() - float(np.min(x))) < 0.01)
dlg.ui.spin_min_2theta.setValue(lo)
dlg.ui.spin_max_2theta.setValue(hi)
check("trim: warning names the doomed marker",
      "marker" in dlg.ui.lbl_removal_warning.text())
check("trim: warning visible", dlg.ui.lbl_removal_warning.isVisibleTo(dlg))
dlg._on_accept()
nx, _ = spec.experimental_pattern
check("trim: clipped to range", bool(np.all((nx >= lo) & (nx <= hi))))
check("trim: doomed marker gone", "doomed" not in [m.label for m in spec.markers])

# Trim "all" scope pre-fills the shared range.
project, spec = fresh_specimen()
dlg = TrimDataDialog(None, specimen=spec, specimens=list(project.specimens))
dlg.ui.cmb_scope.setCurrentIndex(1)
check("trim: 'all' scope re-fills the shared range",
      dlg.ui.spin_min_2theta.value() > 0)

# --- Refusal paths: the dialog must STAY OPEN and change nothing ---
dlg = RemoveBackgroundDialog(None)
dlg._on_accept()
check("unbound dialog refuses to accept", dlg.result() != 1)

# Background "Pattern" mode with no file chosen.
_, spec = fresh_specimen()
_, before = spec.experimental_pattern
before = before.copy()
dlg = RemoveBackgroundDialog(None, specimen=spec)
dlg.ui.bg_type.setCurrentIndex(1)  # Pattern, but no file browsed
_boxes.clear()
dlg._on_accept()
check("bg pattern w/o file: dialog stays open", dlg.result() != 1)
check("bg pattern w/o file: user is told why", len(_boxes) == 1)
check("bg pattern w/o file: pattern unchanged",
      np.array_equal(before, spec.experimental_pattern[1]))

# Smoothing degree too large for the pattern (reachable after a hard trim):
# must warn and stay open, not crash with a ValueError traceback.
_, spec = fresh_specimen()
x, _ = spec.experimental_pattern
spec.trim(float(x[1000]), float(x[1050]))  # ~51 points left
_, before = spec.experimental_pattern
before = before.copy()
dlg = SmoothDataDialog(None, specimen=spec)
dlg.ui.smooth_type.setCurrentIndex(0)  # Moving Triangle (Blackman window)
dlg.ui.spin_degree.setValue(600)
_boxes.clear()
try:
    dlg._on_accept()
    check("smooth too-large degree: no traceback", True)
except Exception as e:
    check("smooth too-large degree: no traceback (%s)" % type(e).__name__, False)
check("smooth too-large degree: dialog stays open", dlg.result() != 1)
check("smooth too-large degree: user is told why", len(_boxes) == 1)
check("smooth too-large degree: pattern unchanged",
      np.array_equal(before, spec.experimental_pattern[1]))

# Strip with an unset range.
_, spec = fresh_specimen()
_, before = spec.experimental_pattern
before = before.copy()
dlg = StripPeakDialog(None, specimen=spec)
dlg._on_accept()  # both endpoints still 0.0
check("strip w/o range: dialog stays open", dlg.result() != 1)
check("strip w/o range: pattern unchanged",
      np.array_equal(before, spec.experimental_pattern[1]))

# --- Edit Specimen: experimental data export + import go through the shared
#     xrd_export / xrd_import dispatchers (any format; tested with .uxd) ---
import tempfile as _tf  # noqa: E402
from PySide6.QtWidgets import QFileDialog  # noqa: E402
_, spec = fresh_specimen()
_ex0, _ey0 = spec.experimental_pattern
_sd = EditSpecimenDialog(None)
_sd.bind_specimen(spec)
_edir = _tf.mkdtemp(prefix="mudlab_specexp_")
_uxd = os.path.join(_edir, "exp.uxd")
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (_uxd, ""))
_sd._export_pattern("experimental")
check("specimen: export experimental data wrote a file", os.path.isfile(_uxd))
_rx, _ry = parse_pattern(_uxd)
check("specimen: exported .uxd round-trips the experimental pattern",
      _rx.size == _ex0.size and np.allclose(_ry, _ey0, atol=1e-2))
# The UXD carries the specimen's goniometer setup, not just the curve.
_g = spec.goniometer
_uxd_text = open(_uxd, encoding="utf-8").read()
check("specimen: UXD export includes goniometer params (radius, WL, divergence)",
      ("_GONIOMETER_RADIUS=%.6f" % _g.radius) in _uxd_text
      and ("_WL1=%.6f" % (_g.wavelength * 10.0)) in _uxd_text
      and ("_DIVERGENCE=%.6f" % _g.divergence) in _uxd_text
      and "_SOLLER1=" in _uxd_text)
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (_uxd, ""))
_sd._on_import_experimental()
_ix, _iy = spec.experimental_pattern
check("specimen: import experimental data replaces the pattern via parse_pattern",
      _ix.size == _rx.size and np.allclose(_iy, _ry, atol=1e-6))
_sd.deleteLater()
os.remove(_uxd)
os.rmdir(_edir)

print("=" * 72)
print("Data-operation dialogs:", os.path.basename(FIXTURE))
print("=" * 72)
passed = sum(1 for _, ok in results if ok)
for label, ok in results:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
print("-" * 72)
print("%d/%d checks passed" % (passed, len(results)))
print("Data-op dialog harness: %s"
      % ("OK" if passed == len(results) else "REGRESSION"))
sys.exit(0 if passed == len(results) else 1)
