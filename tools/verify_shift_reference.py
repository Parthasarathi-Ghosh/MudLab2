#!/usr/bin/env python
"""Shift Pattern dialog reference line: the old app drew a fixed dotted vertical
at the reference reflection's target 2theta so the user can line the shifted peak
up against it; MudLab2 never ported it (the dialog opened but no line showed).

This covers the fix (MainWindow.set_shift_reference / clear_shift_reference ->
PatternPlot draws a dotted vertical at that 2theta, driven by ShiftPatternDialog):

  - opening the dialog draws the line at the selected reference's 2theta;
  - choosing a different reference moves it; Manual mode clears it;
  - the shift VALUE does not move the line (it is fixed at the target);
  - closing the dialog (OK or Cancel) clears it.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_shift_reference.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication

from mudlab.calculations import get_2t_from_nm
from mudlab.file_parsers.mud_project import load_mud
from mudlab.line_dialogs import (
    SHIFT_MANUAL_INDEX, SHIFT_POSITIONS, ShiftPatternDialog,
)
from mudlab.main_window import MainWindow
from mudlab.plot_controller import SHIFT_REFERENCE_COLOR

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    fixtures = [os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")]
    fixtures += sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud")))
    seen = set()
    for path in fixtures:
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        project = load_mud(path)
        for i, spec in enumerate(project.specimens):
            if spec is not None and spec.has_experimental_data:
                return path, i
    return None, None


PATH, ROW = _fixture()
if PATH is None:
    print("No fixture with a specimen with data; skipping (exit 2).")
    raise SystemExit(2)


def _has_ref_line(plot) -> bool:
    return any(
        ln.get_color() == SHIFT_REFERENCE_COLOR and ln.get_linestyle() == ":"
        for ln in plot.axes.get_lines()
    )


def main():
    project = load_mud(PATH)
    spec = project.specimens[ROW]
    print("fixture: %s (specimen row #%d, lambda=%.5f nm)"
          % (os.path.basename(PATH), ROW, spec.wavelength))

    win = MainWindow()
    win._set_project(project)
    win.select_specimen_row(ROW)
    win.show_specimen_plots([spec])
    plot = win.pattern_plots[0]

    dlg = ShiftPatternDialog(win, specimen=spec)
    dlg.ui.shift_position.setCurrentIndex(0)  # first reference reflection
    dlg.show()                                # -> showEvent -> reference line
    app.processEvents()

    want0 = get_2t_from_nm(SHIFT_POSITIONS[0], spec.wavelength)
    check("opening the dialog sets the reference position",
          plot._shift_reference is not None
          and abs(plot._shift_reference - want0) < 1e-6)
    check("a dotted reference line is drawn on the plot", _has_ref_line(plot))

    # Choosing another reference moves the line.
    dlg.ui.shift_position.setCurrentIndex(1)
    want1 = get_2t_from_nm(SHIFT_POSITIONS[1], spec.wavelength)
    check("choosing another reference moves the line",
          plot._shift_reference is not None
          and abs(plot._shift_reference - want1) < 1e-6)

    # The shift VALUE must not move the reference line (it is fixed at target).
    before = plot._shift_reference
    dlg.ui.spin_shift_value.setValue(dlg.ui.spin_shift_value.value() + 0.2)
    check("the shift value does not move the reference line",
          plot._shift_reference == before)

    # Manual mode clears it (no reference reflection).
    dlg.ui.shift_position.setCurrentIndex(SHIFT_MANUAL_INDEX)
    check("Manual mode clears the reference line",
          plot._shift_reference is None and not _has_ref_line(plot))

    # Cancel clears it.
    dlg.ui.shift_position.setCurrentIndex(0)
    check("reference restored before closing", plot._shift_reference is not None)
    dlg.reject()
    check("Cancel clears the reference line",
          plot._shift_reference is None and not _has_ref_line(plot))

    # OK (accept) also clears it.
    dlg2 = ShiftPatternDialog(win, specimen=spec)
    dlg2.ui.shift_position.setCurrentIndex(0)
    dlg2.show()
    app.processEvents()
    check("reopened dialog re-draws the line", plot._shift_reference is not None)
    dlg2.accept()
    check("OK clears the reference line",
          plot._shift_reference is None and not _has_ref_line(plot))

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- Shift reference-line verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
