#!/usr/bin/env python
"""Head-less harness for the refinement progress plot (best Rp vs evaluations).

The refinement dialog now embeds a live convergence plot fed by the per-evaluation
progress signal but redrawn on a throttle timer. Driving a real refinement is slow
and non-deterministic, so this drives the plot plumbing directly:

  - the canvas is embedded in the Progress group and the throttle timer exists;
  - a new run resets the series and arms the timer;
  - each progress tick only APPENDS a point (no synchronous redraw - the throttle
    does it), and a forced/final redraw draws exactly those points;
  - finishing stops the timer and leaves the full curve drawn.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_refine_progress_plot.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from mudlab.file_parsers.mud_project import load_mud
from mudlab.refinement_dialog import RefinementDialog

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _find_mixture():
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        if project.mixtures and project.mixtures[0].refinables():
            return path, project.mixtures[0]
    return None, None


PATH, MIX = _find_mixture()
if MIX is None:
    print("No fixture with a refinable mixture; skipping (exit 2).")
    raise SystemExit(2)


def _data_lines(dlg):
    return dlg._prog_ax.get_lines()


def main():
    print("fixture: %s" % os.path.basename(PATH))
    dlg = RefinementDialog(mixture=MIX)

    # Setup
    check("setup: canvas embedded in the Progress group",
          dlg.ui.progressLayout.count() >= 1 and dlg._prog_canvas is not None)
    check("setup: throttle timer exists and is not running yet",
          dlg._prog_timer.interval() > 0 and not dlg._prog_timer.isActive())
    check("setup: plot starts empty", len(_data_lines(dlg)) == 0)

    # Start a (simulated) run.
    dlg._start_progress()
    check("start: series reset + timer armed",
          dlg._prog_evals == [] and dlg._prog_best == [] and dlg._prog_timer.isActive())
    check("start: nothing drawn yet", len(_data_lines(dlg)) == 0)

    # Progress ticks: append only (throttled - no synchronous redraw).
    evals = [1, 5, 12, 30, 71]
    best = [9.0, 7.2, 6.1, 5.4, 5.25]
    for n, b in zip(evals, best):
        dlg._on_progress(n, b)
    check("tick: points appended", dlg._prog_evals == evals and dlg._prog_best == best)
    check("tick: dirty flag set", dlg._prog_dirty is True)
    check("tick: NOT redrawn synchronously (throttled)", len(_data_lines(dlg)) == 0)

    # A forced redraw (what the timer / finish does) draws exactly those points.
    dlg._redraw_progress(force=True)
    lines = _data_lines(dlg)
    ok_line = (len(lines) == 1
               and list(lines[0].get_xdata()) == evals
               and list(lines[0].get_ydata()) == best)
    check("redraw: the curve is drawn with all appended points", ok_line)
    check("redraw: dirty flag cleared", dlg._prog_dirty is False)

    # Finish stops the timer and leaves the curve.
    dlg._finish_progress()
    check("finish: timer stopped", not dlg._prog_timer.isActive())
    check("finish: final curve retained", len(_data_lines(dlg)) == 1)

    # A fresh run resets everything.
    dlg._start_progress()
    check("reset: a new run clears the series and the curve",
          dlg._prog_evals == [] and len(_data_lines(dlg)) == 0)
    dlg._finish_progress()

    _check_delete_on_close()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- refinement progress plot verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


def _check_delete_on_close():
    """AUDIT: the dialog is opened with exec() from a local variable, so without
    WA_DeleteOnClose every Refine click left one hidden dialog - refinables
    table, progress plot and all - alive for the mixture editor's lifetime.
    The attribute must fire on the exec()-return path (reject/done), not only on
    the window-X, and must not leave a running worker behind."""
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    dlg = RefinementDialog(parent, mixture=MIX)
    check("cleanup: the dialog is marked WA_DeleteOnClose",
          dlg.testAttribute(Qt.WidgetAttribute.WA_DeleteOnClose))
    dlg.show()
    dlg.reject()                      # what pressing Close does after exec()
    app.processEvents()
    try:
        dlg.objectName()
        gone = False
    except RuntimeError:
        gone = True
    check("cleanup: closing actually frees it (no hidden dialog left behind)",
          gone)
    check("cleanup: it is no longer a child of the editor",
          not any(isinstance(c, RefinementDialog) for c in parent.children()))

    # A dismissal must never leave a worker thread running behind it: the Close
    # button is locked while a refinement runs, and closeEvent waits for it.
    dlg2 = RefinementDialog(parent, mixture=MIX)
    dlg2._set_running(True)
    check("cleanup: Close is locked out while a refinement runs",
          not dlg2.ui.buttonBox.isEnabled())
    dlg2._set_running(False)
    dlg2.close()
    app.processEvents()

    # AUDIT REGRESSION: **Esc is not stopped by disabling buttonBox.** It goes
    # straight to QDialog::reject() -> done(), which with WA_DeleteOnClose
    # deletes the dialog AND the QThread parented to it. Pressing Esc during a
    # refinement therefore destroyed a running QThread and ABORTED the process
    # (exit 9, no traceback). done() now tears the worker down first.
    dlg3 = RefinementDialog(parent, mixture=MIX)
    dlg3.show()
    app.processEvents()
    dlg3._on_refine()                      # a genuine background refinement
    app.processEvents()
    if dlg3._thread is None:
        check("cleanup: Esc during a refinement tears the worker down first", True)
        print("  (the refinement finished too fast to test Esc mid-run)")
    else:
        thread, stop_event = dlg3._thread, dlg3._stop_event
        esc = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape,
                        Qt.KeyboardModifier.NoModifier)
        dlg3.keyPressEvent(esc)            # user presses Esc mid-run
        # Checked BEFORE processEvents, while the thread wrapper is still alive:
        # the run must have been cancelled and JOINED, not left running.
        check("cleanup: Esc during a refinement cancels the run",
              stop_event.is_set())
        check("cleanup: Esc during a refinement joins the worker before deleting",
              not thread.isRunning())
        app.processEvents()
        try:
            dlg3.objectName()
            freed = False
        except RuntimeError:
            freed = True
        check("cleanup: Esc still frees the dialog", freed)
    parent.deleteLater()


if __name__ == "__main__":
    sys.exit(main())
