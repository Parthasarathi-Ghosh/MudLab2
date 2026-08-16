#!/usr/bin/env python
"""Strip Peak / Peak Properties range selection.

These two dialogs used to pick their [start, end] range with two eye-dropper
"Sample" buttons (one click per endpoint). That is replaced by dragging across
the pattern: the dialog arms the main window's range pick while it is shown, and
a left-drag on the plot reuses the crosshair drag-highlight to sweep the range,
filling BOTH spinboxes on release (the boxes stay editable for fine-tuning).

This covers the reuse end to end:
  - the dialogs are range-select dialogs and no longer carry Sample buttons;
  - showing a dialog arms the range pick and enables range-select on the plot,
    independent of the Crosshair toggle;
  - a left-drag highlights the swept span and fills start/end ASCENDING (either
    drag direction); a plain click (no movement) changes nothing;
  - closing the dialog disarms the pick and disables range-select on the plot.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_range_select.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication

from mudlab.file_parsers.mud_project import load_mud
from mudlab.line_dialogs import (
    PeakPropertiesDialog, StripPeakDialog, _RangeSelectMixin,
)
from mudlab.main_window import MainWindow

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        for i, spec in enumerate(project.specimens):
            if spec is not None and spec.has_experimental_data:
                return path, i, project
    return None, None, None


PATH, ROW, PROJECT = _fixture()
if PATH is None:
    print("No fixture with a specimen with data; skipping (exit 2).")
    raise SystemExit(2)


def main():
    spec = PROJECT.specimens[ROW]
    win = MainWindow()
    win._set_project(PROJECT)
    win.select_specimen_row(ROW)
    win.show_specimen_plots([spec])
    plot = win.pattern_plots[0]

    x, _ = spec.experimental_pattern
    # Spinboxes store 2 decimals, so compare against the rounded targets.
    xa = round(float(x[len(x) // 4]), 2)
    xb = round(float(x[len(x) // 2]), 2)
    tol = 5e-3
    print("fixture: %s (row #%d)  xa=%.2f  xb=%.2f" % (os.path.basename(PATH), ROW, xa, xb))

    def ev(xdata, button=1, dbl=False):
        return types.SimpleNamespace(
            button=button, inaxes=plot.axes, xdata=xdata, dblclick=dbl)

    def drag(x0, x1):
        """Simulate a left press at x0, motion to x1, release at x1. Returns
        whether the swept span was highlighted mid-drag."""
        plot._on_button_press(ev(x0))
        plot._on_motion_event(ev(x1))
        highlighted = bool(plot._drag_highlight_lines) and any(
            ln.get_visible() for ln in plot._drag_highlight_lines)
        plot._on_button_release(ev(x1))
        app.processEvents()
        return highlighted

    # ---- Strip Peak ---------------------------------------------------
    dlg = StripPeakDialog(win, specimen=spec)
    check("strip is a range-select dialog", isinstance(dlg, _RangeSelectMixin))
    check("strip: no Sample buttons remain",
          not hasattr(dlg.ui, "cmd_sample_start")
          and not hasattr(dlg.ui, "cmd_sample_end"))
    dlg.show()
    app.processEvents()
    check("strip: showing arms the range pick", win._range_pick_callback is not None)
    check("strip: range-select enabled on the plot", plot._range_select_enabled is True)
    check("strip: crosshair stays OFF (independent of the toggle)",
          plot._crosshair_enabled is False)

    highlighted = drag(xa, xb)
    check("strip: the drag highlighted the swept span (crosshair off)", highlighted)
    check("strip: drag filled start (ascending)",
          abs(dlg.ui.strip_startx.value() - xa) < tol)
    check("strip: drag filled end (ascending)",
          abs(dlg.ui.strip_endx.value() - xb) < tol)

    drag(xb, xa)  # reverse drag -> still ascending
    check("strip: reverse drag keeps start ascending",
          abs(dlg.ui.strip_startx.value() - xa) < tol)
    check("strip: reverse drag keeps end ascending",
          abs(dlg.ui.strip_endx.value() - xb) < tol)

    s0, e0 = dlg.ui.strip_startx.value(), dlg.ui.strip_endx.value()
    drag(xa, xa)  # a plain click (no movement) reports nothing
    check("strip: a plain click leaves the range unchanged",
          dlg.ui.strip_startx.value() == s0 and dlg.ui.strip_endx.value() == e0)

    dlg.reject()
    app.processEvents()
    check("strip: closing disarms the range pick", win._range_pick_callback is None)
    check("strip: closing disables range-select on the plot",
          plot._range_select_enabled is False)

    # ---- Peak Properties ---------------------------------------------
    dlg2 = PeakPropertiesDialog(win, specimen=spec)
    check("props: no Sample buttons remain",
          not hasattr(dlg2.ui, "cmd_sample_start")
          and not hasattr(dlg2.ui, "cmd_sample_end"))
    dlg2.show()
    app.processEvents()
    check("props: showing arms the range pick", win._range_pick_callback is not None)
    drag(xa, xb)
    check("props: drag filled start", abs(dlg2.ui.peak_startx.value() - xa) < tol)
    check("props: drag filled end", abs(dlg2.ui.peak_endx.value() - xb) < tol)
    check("props: results recomputed after the drag",
          dlg2.ui.peak_area_result.text() not in ("", "0.0"))
    dlg2.reject()
    app.processEvents()
    check("props: closing disarms the range pick", win._range_pick_callback is None)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- Range-select verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
