#!/usr/bin/env python
"""Durable harness for the data-op dialogs' live preview wiring (Batch 2),
run head-less.

Each line/data-op dialog should, while open, push a live preview of its result
to the main plot and clear it on close. This drives every dialog against a stub
main window that records the preview / clear calls and asserts:

  - showing the dialog pushes a preview for the bound specimen;
  - the pushed (x, y) equals the specimen's non-destructive preview_* result
    (so the overlay matches what OK would apply);
  - a parameter change updates the preview;
  - Smooth's "show original" checkbox drives the show_original flag;
  - Strip with a too-narrow range pushes no preview;
  - Peak Properties (a measurement) pushes no preview;
  - closing (reject) and accepting both clear the preview.

The preview numerics are guarded by verify_pattern_preview; this checks the
UI wiring.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_data_op_preview.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

# Refusals pop a modal box; record instead of block.
QMessageBox.warning = staticmethod(lambda *a, **k: None)

from mudlab.calculations import pattern_ops
from mudlab.file_parsers.mud_project import load_mud
from mudlab.line_dialogs import (
    AddNoiseDialog, PeakPropertiesDialog, RemoveBackgroundDialog,
    ShiftPatternDialog, SmoothDataDialog, StripPeakDialog,
    SHIFT_POSITIONS, SMOOTH_TYPES,
)

_FIXTURE_NAME = "308 r1.mud"
FIXTURE = os.path.join(_REPO, "tools", "sample_projects", _FIXTURE_NAME)
if not os.path.isfile(FIXTURE):
    FIXTURE = os.path.join(os.path.expanduser("~"), "Downloads", _FIXTURE_NAME)
if not os.path.isfile(FIXTURE):
    print("No sample project found; skipping (exit 2).")
    raise SystemExit(2)

app = QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


class StubMainWindow(QWidget):
    """Records the preview overlay calls the dialogs make."""

    def __init__(self):
        super().__init__()
        self.previews: list = []
        self.clears = 0

    def set_pattern_preview(self, specimen, x, y, show_original=True):
        self.previews.append(
            (specimen, np.asarray(x, float), np.asarray(y, float), show_original)
        )

    def clear_pattern_preview(self):
        self.clears += 1

    @property
    def last(self):
        return self.previews[-1] if self.previews else None


def fresh_specimen():
    project = load_mud(FIXTURE)
    return next(s for s in project.specimens if s.has_experimental_data)


# ----------------------------------------------------------------------
def check_remove_background():
    mw, spec = StubMainWindow(), fresh_specimen()
    dlg = RemoveBackgroundDialog(mw, specimen=spec)
    dlg.show()  # -> showEvent -> initial preview
    check("bg: shows a preview on open", mw.last is not None and mw.last[0] is spec)
    ex, ey = spec.preview_remove_background(
        pattern_ops.BG_LINEAR, dlg.ui.bg_position.value())
    check("bg: preview == preview_remove_background",
          np.allclose(mw.last[1], ex) and np.allclose(mw.last[2], ey))
    n = len(mw.previews)
    dlg.ui.bg_position.setValue(dlg.ui.bg_position.value() + 5.0)
    check("bg: parameter change updates the preview", len(mw.previews) > n)
    dlg.reject()
    check("bg: reject clears the preview", mw.clears >= 1)
    dlg.deleteLater()


def check_smooth():
    mw, spec = StubMainWindow(), fresh_specimen()
    dlg = SmoothDataDialog(mw, specimen=spec)
    dlg.show()
    ex, ey = spec.preview_smooth(
        SMOOTH_TYPES[dlg.ui.smooth_type.currentIndex()], dlg.ui.spin_degree.value())
    check("smooth: preview == preview_smooth",
          mw.last is not None and np.allclose(mw.last[1], ex) and np.allclose(mw.last[2], ey))
    check("smooth: show_original on by default", mw.last[3] is True)
    dlg.ui.smooth_show_original.setChecked(False)
    check("smooth: unchecking show_original propagates", mw.last[3] is False)
    dlg.reject()
    check("smooth: reject clears the preview", mw.clears >= 1)
    dlg.deleteLater()


def check_shift():
    mw, spec = StubMainWindow(), fresh_specimen()
    dlg = ShiftPatternDialog(mw, specimen=spec)
    dlg.show()
    idx = dlg.ui.shift_position.currentIndex()
    ex, ey = spec.preview_shift(dlg.ui.spin_shift_value.value(), SHIFT_POSITIONS[idx])
    check("shift: preview == preview_shift",
          mw.last is not None and np.allclose(mw.last[1], ex) and np.allclose(mw.last[2], ey))
    dlg.reject()
    check("shift: reject clears the preview", mw.clears >= 1)
    dlg.deleteLater()


def check_add_noise():
    mw, spec = StubMainWindow(), fresh_specimen()
    dlg = AddNoiseDialog(mw, specimen=spec)
    dlg.show()
    x, _ = spec.experimental_pattern
    check("noise: shows a preview of the right shape for this specimen",
          mw.last is not None and mw.last[0] is spec and mw.last[2].shape == x.shape)
    dlg.reject()
    check("noise: reject clears the preview", mw.clears >= 1)
    dlg.deleteLater()


def check_strip():
    mw, spec = StubMainWindow(), fresh_specimen()
    dlg = StripPeakDialog(mw, specimen=spec)
    dlg.show()
    # Default 0/0 range is too narrow -> compute_strip_pattern is None -> no
    # preview pushed (a clear instead).
    check("strip: no preview for a zero-width range", mw.last is None)
    x, _ = spec.experimental_pattern
    dlg.ui.strip_startx.setValue(float(x[len(x) // 3]))
    dlg.ui.strip_endx.setValue(float(x[len(x) // 3 + 25]))
    check("strip: a valid range pushes a preview",
          mw.last is not None and mw.last[0] is spec)
    # The strip replaces the peak with a noisy background line (random), so
    # assert the shape and that the region between the endpoints actually
    # changed, rather than an exact match.
    xx, orig_y = spec.experimental_pattern
    region = (xx >= dlg.ui.strip_startx.value()) & (xx <= dlg.ui.strip_endx.value())
    check("strip: preview strips the selected region",
          mw.last[2].shape == orig_y.shape and region.any()
          and not np.allclose(mw.last[2][region], orig_y[region]))
    dlg.reject()
    check("strip: reject clears the preview", mw.clears >= 1)
    dlg.deleteLater()


def check_peak_properties_no_preview():
    mw, spec = StubMainWindow(), fresh_specimen()
    dlg = PeakPropertiesDialog(mw, specimen=spec)
    dlg.show()
    check("peak props: pushes no preview (a measurement)", mw.last is None)
    dlg.reject()
    dlg.deleteLater()


def check_accept_clears():
    mw, spec = StubMainWindow(), fresh_specimen()
    dlg = AddNoiseDialog(mw, specimen=spec)
    dlg.show()
    before = mw.clears
    dlg._on_accept()  # applies + should clear the preview
    check("accept clears the preview after applying", mw.clears > before)
    dlg.deleteLater()


def main():
    check_remove_background()
    check_smooth()
    check_shift()
    check_add_noise()
    check_strip()
    check_peak_properties_no_preview()
    check_accept_clears()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- data-op dialog preview-wiring verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
