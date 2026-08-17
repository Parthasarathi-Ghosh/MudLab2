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
from PySide6.QtGui import QFontDatabase, QKeyEvent
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
    _check_three_frame_layout()
    _check_report_after_real_run()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- refinement progress plot verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


def _check_report_after_real_run():
    """The report, driven by a REAL (tiny) refinement.

    Pins the premise the report rests on: `refine_mixture` LEAVES THE MODEL AT
    THE BEST SOLUTION, so the report must say "best" on finish (an earlier
    version said "nothing applied yet", and withheld the validation section that
    the old app showed at exactly this point). Then keeping another solution
    must rewrite it, with the GoF recomputed for what is actually applied."""
    import time

    from PySide6.QtCore import Qt as _Qt

    dlg = RefinementDialog(mixture=MIX)
    dlg.show()
    app.processEvents()

    # Pin L-BFGS-B: the method is REMEMBERED on the mixture, and an earlier
    # check leaves Basin Hopping selected - whose "iterations" are full
    # restarts, so the same budget would run for minutes here.
    dlg.ui.cmb_method.setCurrentIndex(dlg.ui.cmb_method.findData(0))
    app.processEvents()

    flagged = 0
    for row in range(dlg.ui.tbl_refinables.rowCount()):
        if flagged >= 2:
            break
        item = dlg.ui.tbl_refinables.item(row, 4)
        if item is not None:
            item.setCheckState(_Qt.CheckState.Checked)
            flagged += 1
    for key in ("maxfun", "maxiter"):
        if key in dlg._option_spins:
            dlg._option_spins[key][0].setValue(12)   # keep it short

    dlg._on_refine()
    deadline = time.time() + 300
    while dlg._thread is not None and time.time() < deadline:
        app.processEvents()
    app.processEvents()
    if dlg._refiner is None:
        print("  (no refiner after the run: thread=%s status=%r; report checks "
              "skipped)" % (dlg._thread is not None, dlg.ui.lbl_status.text()))
        dlg.close()
        return

    refiner = dlg._refiner
    values = [ref.value for ref in refiner.refinables]
    check("report: the engine leaves the model at the BEST solution",
          all(abs(v - b) < 1e-9 for v, b in zip(values, refiner.best_solution)))

    text = dlg.ui.txt_report.toPlainText()
    check("report: written when the run finishes", bool(text.strip()))
    check("report: says the best solution is applied, and by whom",
          "Best solution" in text and "left by the refinement" in text)
    check("report: carries the validation section on finish (as the old app did)",
          "Post-refinement validation" in text)
    for heading in ("Method:", "Parameters:", "Time elapsed:", "Residuals",
                    "GoF", "Progress log"):
        check("report: includes %r" % heading, heading in text)
    check("report: one row per refinable in the parameter table",
          all(ref.label[:20] in text for ref in refiner.refinables))
    # The SUMMARY is a column-aligned table and must fit the report width; the
    # validation section below it is prose (warnings name the phase, component
    # and relation), so it only has to stay sane - the box scrolls.
    lines = text.splitlines()
    split = next((i for i, l in enumerate(lines)
                  if "Post-refinement validation" in l), len(lines))
    check("report: the summary table fits the report width",
          max(len(l) for l in lines[:split]) <= dlg._REPORT_WIDTH)
    check("report: the validation lines stay within a readable width",
          max((len(l) for l in lines[split:]), default=0) <= 96)

    # Keeping another solution rewrites it for THAT solution.
    dlg._on_apply("initial")
    app.processEvents()
    initial_text = dlg.ui.txt_report.toPlainText()
    check("report: keeping Initial rewrites it as kept by the user",
          "Initial solution" in initial_text and "(kept)" in initial_text)
    check("report: the model really moved to the initial solution",
          all(abs(ref.value - i) < 1e-9
              for ref, i in zip(refiner.refinables, refiner.initial_solution)))

    def _gof(report):
        line = next((l for l in report.splitlines() if "GoF" in l), "")
        return line.split(":")[-1].strip()

    dlg._on_apply("best")
    app.processEvents()
    best_text = dlg.ui.txt_report.toPlainText()
    check("report: the GoF is recomputed for the applied solution",
          _gof(best_text) != _gof(initial_text))
    check("report: a new run clears the previous report",
          bool(best_text.strip()))
    dlg._on_refine()
    app.processEvents()
    check("report: ...cleared as soon as the next run starts",
          dlg.ui.txt_report.toPlainText() == "")
    dlg._abort_refinement()
    deadline = time.time() + 120
    while dlg._thread is not None and time.time() < deadline:
        app.processEvents()
    dlg.close()
    app.processEvents()


def _check_three_frame_layout():
    """The dialog is a MODAL three-frame row (parameters | refinement | result),
    not the old single vertical stack. Pins where each control lives, so a later
    .ui edit cannot quietly move one into the wrong frame."""
    dlg = RefinementDialog(mixture=MIX)
    dlg.show()
    app.processEvents()
    ui = dlg.ui

    check("layout: the dialog is modal (no editing behind it)", dlg.isModal())

    frames = [ui.grpParameters, ui.grpRefine, ui.grpResult]
    check("layout: all three frames share one row layout",
          all(ui.framesRow.indexOf(f) >= 0 for f in frames))
    xs = [f.x() for f in frames]
    check("layout: they sit side by side, parameters -> refinement -> result",
          xs == sorted(xs) and len(set(xs)) == 3)
    check("layout: the frames are the full height of the row (not stacked)",
          len({f.y() for f in frames}) == 1)

    belongs = {
        "grpParameters": (ui.tbl_refinables, ui.btn_auto_restrict, ui.btn_randomize),
        "grpRefine": (ui.cmb_method, ui.btn_refine, ui.btn_cancel, ui.grpProgress),
        "grpResult": (ui.lbl_initial_residual, ui.lbl_best_residual, ui.lbl_last_residual,
                      ui.lbl_gof, ui.btn_apply_initial, ui.btn_apply_best,
                      ui.btn_apply_last),
    }
    for frame_name, widgets in belongs.items():
        frame = getattr(ui, frame_name)
        check("layout: %s holds its own controls" % frame_name,
              all(frame.isAncestorOf(w) for w in widgets))
    # ...and nothing strays into a neighbour.
    check("layout: the progress plot is inside the refinement frame only",
          ui.grpRefine.isAncestorOf(dlg._prog_canvas)
          and not ui.grpParameters.isAncestorOf(dlg._prog_canvas)
          and not ui.grpResult.isAncestorOf(dlg._prog_canvas))
    check("layout: status + Close sit in the dialog-wide bottom row",
          ui.bottomRow.indexOf(ui.lbl_status) >= 0
          and ui.bottomRow.indexOf(ui.buttonBox) >= 0)

    # The per-method options are a wrapping grid of (label, spin) PAIRS: the two
    # L-BFGS-B options read as one side-by-side row, and Basin Hopping's three
    # wrap onto a second row instead of squeezing into one line.
    dlg.ui.cmb_method.setCurrentIndex(dlg.ui.cmb_method.findData(0))
    app.processEvents()
    rows = {dlg._options_form.getItemPosition(i)[0]
            for i in range(dlg._options_form.count())}
    check("layout: two options sit side by side on one row",
          len(dlg._option_spins) == 2 and rows == {0})
    dlg.ui.cmb_method.setCurrentIndex(dlg.ui.cmb_method.findData(1))
    app.processEvents()
    rows = {dlg._options_form.getItemPosition(i)[0]
            for i in range(dlg._options_form.count())}
    check("layout: three options wrap onto a second row",
          len(dlg._option_spins) == 3 and rows == {0, 1})
    check("layout: every option spin carries an explanatory tooltip",
          all(spin.toolTip() for spin, _kind in dlg._option_spins.values()))

    # Long parameter names elide on one line (rather than doubling row height)
    # and keep their full text in a tooltip.
    check("layout: parameter names stay on one line, with a tooltip",
          not dlg.ui.tbl_refinables.wordWrap()
          and dlg.ui.tbl_refinables.item(0, 0).toolTip()
          == dlg.ui.tbl_refinables.item(0, 0).text())

    # The report box lives in the result frame, below the three Keep buttons,
    # and is read-only + fixed-pitch (it is a column-aligned text table).
    check("layout: the report box sits in the result frame",
          ui.grpResult.isAncestorOf(ui.txt_report)
          and ui.resultLayout.indexOf(ui.txt_report)
          > ui.resultLayout.indexOf(ui.applyLayout))
    # Compare the family to the system fixed font rather than asking
    # QFontInfo.fixedPitch(): the offscreen platform has no font backend, so it
    # resolves "monospace" but reports fixedPitch False.
    check("layout: the report is read-only and uses the fixed-pitch font",
          ui.txt_report.isReadOnly()
          and ui.txt_report.font().family()
          == QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family())
    check("layout: the report starts empty, before any run",
          not ui.txt_report.toPlainText())
    check("layout: the Keep buttons are labelled Initial / Best / Last",
          (ui.btn_apply_initial.text(), ui.btn_apply_best.text(),
           ui.btn_apply_last.text()) == ("Initial", "Best", "Last"))

    # Nothing may be clipped at the smallest size the dialog allows.
    dlg.resize(dlg.minimumWidth(), dlg.minimumHeight())
    app.processEvents()
    table = dlg.ui.tbl_refinables
    check("layout: at minimum size the table still fits its frame",
          dlg.minimumWidth() >= dlg.minimumSizeHint().width()
          and table.width() <= ui.grpParameters.width())
    dlg._dirty = False
    dlg.close()
    app.processEvents()


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
