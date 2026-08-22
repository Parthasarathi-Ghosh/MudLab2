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

    _check_per_specimen_curves(dlg)

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


def _check_refinables_tree(dlg):
    """The refinables view is a foldable TREE (the old app's design), not a flat
    table: a group row per phase, a nested group per component, and one leaf per
    parameter showing ONLY its own title. That is what lets the name column be
    narrow - the path lives on the group rows instead of being repeated on every
    row - and group rows must stay inert."""
    tree = dlg.ui.tree_refinables
    check("tree: the refinables view is a tree with fold arrows",
          tree.topLevelItemCount() > 0 and tree.rootIsDecorated())
    groups = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    check("tree: top-level rows are phases, each with children",
          all(g.childCount() > 0 for g in groups))
    check("tree: opens FOLDED (phase names are the overview)",
          not any(g.isExpanded() for g in groups))
    tree.expandAll()
    app.processEvents()
    check("tree: Expand all unfolds every branch",
          all(g.isExpanded() for g in groups))
    tree.collapseAll()
    app.processEvents()
    check("tree: Fold all folds them again",
          not any(g.isExpanded() for g in groups))
    check("tree: the branch indent is tighter than Qt's default",
          0 < tree.indentation() < 20)

    # A leaf shows only its own title, never the full path.
    leaves = list(dlg._leaf_items())
    check("tree: every refinable has a leaf", len(leaves) == len(dlg._refinables))
    check("tree: a leaf shows only its own title, with the path in a tooltip",
          all(item.text(0) == ref.title and item.toolTip(0) == ref.label
              for item, ref in leaves))
    check("tree: leaves are checkable (the Refine box) and editable",
          all(item.flags() & Qt.ItemFlag.ItemIsUserCheckable
              and item.flags() & Qt.ItemFlag.ItemIsEditable
              for item, _ref in leaves))
    check("tree: group rows are inert - not editable, not checkable",
          all(not (g.flags() & Qt.ItemFlag.ItemIsEditable)
              and not (g.flags() & Qt.ItemFlag.ItemIsUserCheckable)
              for g in groups))
    check("tree: group rows map to no refinable",
          all(id(g) not in dlg._items for g in groups))

    # AUDIT REGRESSION: names are NOT unique - nothing stops two phases (or two
    # components of one phase) sharing one. Grouping by NAME merged their
    # parameters into a single branch, with no way to tell which phase a row
    # belonged to; the tree groups by Refinable.group_key (stable ids) instead.
    phases, seen = [], set()
    for row in MIX.phase_matrix:
        for ph in row:
            if ph is not None and hasattr(ph, "components") and id(ph) not in seen:
                seen.add(id(ph))
                phases.append(ph)
    if len(phases) >= 2:
        original = phases[1].name
        phases[1].name = phases[0].name          # deliberate duplicate
        try:
            dup_dlg = RefinementDialog(mixture=MIX)
            dup_dlg.show()
            app.processEvents()
            dup_tree = dup_dlg.ui.tree_refinables
            tops = [dup_tree.topLevelItem(i)
                    for i in range(dup_tree.topLevelItemCount())]
            same_named = [t for t in tops if t.text(0) == phases[0].name]
            check("tree: two phases sharing a name get SEPARATE branches",
                  len(same_named) == 2)
            check("tree: ...and every refinable still has exactly one leaf",
                  len(list(dup_dlg._leaf_items())) == len(dup_dlg._refinables))
            dup_dlg._dirty = False
            dup_dlg.close()
            app.processEvents()
        finally:
            phases[1].name = original

    # Editing a leaf writes through to the model; a bad number reverts.
    item, ref = leaves[0]
    before = ref.refine
    item.setCheckState(4, Qt.CheckState.Checked if not before
                       else Qt.CheckState.Unchecked)
    app.processEvents()
    check("tree: ticking Refine writes the model", ref.refine != before)
    item.setCheckState(4, Qt.CheckState.Checked if before
                       else Qt.CheckState.Unchecked)
    keep_min = ref.minimum
    item.setText(2, "%.4f" % (keep_min + 1.5))
    app.processEvents()
    check("tree: editing Min writes the model",
          abs(ref.minimum - (keep_min + 1.5)) < 1e-9)
    item.setText(2, "rubbish")
    app.processEvents()
    check("tree: a non-numeric edit reverts to the model value",
          abs(ref.minimum - (keep_min + 1.5)) < 1e-9
          and item.text(2) == "%.4f" % ref.minimum)
    ref.set_ref_info(minimum=keep_min)

    # The right-click menu replaced the Auto-restrict / Randomize buttons.
    check("menu: the tree has a custom context menu",
          tree.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu)
    check("menu: the Auto-restrict / Randomize BUTTONS are gone",
          not hasattr(dlg.ui, "btn_auto_restrict")
          and not hasattr(dlg.ui, "btn_randomize"))

    # _tree_menu() BUILDS the menu; _on_tree_menu() shows it. Testing the
    # builder keeps this out of a modal exec() loop.
    def entries(menu):
        return {a.text(): a.isEnabled() for a in menu.actions() if a.text()}

    idle = entries(dlg._tree_menu())
    check("menu: offers all six entries",
          list(idle) == ["Expand all", "Fold all", "Select all",
                         "Unselect all", "Auto restrict", "Randomise"])
    check("menu: everything is enabled while idle", all(idle.values()))

    # While a refinement runs the model-touching entries grey out.
    dlg._thread = object()          # a stand-in for a live QThread
    try:
        busy = entries(dlg._tree_menu())
    finally:
        dlg._thread = None          # ...never leave it set: close() would use it
    check("menu: folding stays available during a run",
          busy["Expand all"] and busy["Fold all"])
    check("menu: select / restrict / randomise grey out during a run",
          not busy["Select all"] and not busy["Unselect all"]
          and not busy["Auto restrict"] and not busy["Randomise"])

    # Select all / Unselect all drive every parameter's Refine flag, and UNFOLD
    # so the result is visible rather than hidden behind collapsed branches.
    tree.collapseAll()
    app.processEvents()
    dlg._set_all_refine(True)
    app.processEvents()
    check("menu: Select all ticks every parameter",
          all(ref.refine for _item, ref in dlg._leaf_items())
          and all(item.checkState(4) == Qt.CheckState.Checked
                  for item, _ref in dlg._leaf_items()))
    check("menu: Select all also expands the tree",
          all(g.isExpanded() for g in groups))
    check("count: the label reports every parameter selected",
          dlg.ui.lbl_selected.text() == "%d of %d selected"
          % (len(dlg._refinables), len(dlg._refinables)))
    tree.collapseAll()
    app.processEvents()
    dlg._set_all_refine(False)
    app.processEvents()
    check("menu: Unselect all clears them",
          not any(ref.refine for _item, ref in dlg._leaf_items()))
    check("menu: Unselect all also expands the tree",
          all(g.isExpanded() for g in groups))
    check("count: ...and the label drops back to none selected",
          dlg.ui.lbl_selected.text() == "0 of %d selected" % len(dlg._refinables))

    # The counter follows a single tick from the tree itself, too.
    one_item, _one_ref = leaves[0]
    one_item.setCheckState(4, Qt.CheckState.Checked)
    app.processEvents()
    check("count: one tick in the tree updates the label",
          dlg.ui.lbl_selected.text() == "1 of %d selected" % len(dlg._refinables))
    one_item.setCheckState(4, Qt.CheckState.Unchecked)
    app.processEvents()

    check("layout: the Refine column is spelled out, not abbreviated",
          tree.headerItem().text(4) == "Refine")

    # Value, Min and Max may be edited; Parameter may NOT. The item's
    # ItemIsEditable flag applies to every column, so without the delegate the
    # Parameter cell opens an editor too - and a typed name would stay on screen
    # while the model kept its own.
    from PySide6.QtWidgets import QStyleOptionViewItem

    delegate = tree.itemDelegate()
    option = QStyleOptionViewItem()
    model = tree.model()
    editable = {}
    for col in range(5):
        index = model.index(0, col, model.index(0, 0).parent())
        editor = delegate.createEditor(tree.viewport(), option, index)
        editable[col] = editor is not None
        if editor is not None:
            editor.deleteLater()
    check("edit: the Parameter cell refuses an editor", not editable[0])
    check("edit: Value, Min and Max open one",
          editable[1] and editable[2] and editable[3])

    _check_value_editing(dlg)

    # The evaluation budget readout, for the current method + options +
    # selection. It is also the only place the silent "ticked but Min >= Max, so
    # not actually refined" case becomes visible.
    dlg.ui.cmb_method.setCurrentIndex(dlg.ui.cmb_method.findData(0))
    dlg._set_all_refine(False)
    app.processEvents()
    check("budget: says so when nothing is selected",
          "No parameters selected" in dlg.ui.lbl_budget.text())
    picked = []
    for leaf, ref in dlg._leaf_items():
        if len(picked) >= 3:
            break
        if ref.minimum < ref.maximum:
            leaf.setCheckState(4, Qt.CheckState.Checked)
            picked.append((leaf, ref))
    app.processEvents()
    n = len(picked)
    dlg._option_spins["maxiter"][0].setValue(5)
    dlg._option_spins["maxfun"][0].setValue(500)
    app.processEvents()
    # It must NOT claim a total: measuring proved maxfun/maxiter count scipy's
    # own solver steps, not model evaluations (maxiter=3 produced 28 against a
    # predicted 9), so it states the parameter count and each method's limits.
    text = dlg.ui.lbl_budget.text()
    check("budget: states the parameter count and the method's own limits",
          "%d parameters" % n in text and "5 " in text and "solver steps" in text)
    check("budget: does NOT claim a total number of evaluations",
          "Up to" not in text)
    check("budget: a degenerate range drops out of the effective count",
          dlg._effective_parameters() == n)
    keep = (picked[0][1].minimum, picked[0][1].maximum)
    picked[0][1].set_ref_info(minimum=9.0, maximum=1.0)
    dlg._update_budget()
    check("budget: ...so a ticked Min >= Max parameter is counted out",
          dlg._effective_parameters() == n - 1)
    picked[0][1].set_ref_info(minimum=keep[0], maximum=keep[1])
    dlg.ui.cmb_method.setCurrentIndex(dlg.ui.cmb_method.findData(1))
    app.processEvents()
    niter = int(dlg._option_spins["niter"][0].value())
    dlg._option_spins["local_maxfun"][0].setValue(50)
    app.processEvents()
    bh = dlg.ui.lbl_budget.text()
    check("budget: Basin Hopping reports its local runs and per-run limit",
          "%d local runs" % (niter + 1) in bh and "50 solver steps" in bh)
    check("budget: ...and warns it is the slow method", "slower" in bh)
    check("budget: Basin Hopping claims no total either", "Up to" not in bh)
    dlg.ui.cmb_method.setCurrentIndex(dlg.ui.cmb_method.findData(0))
    dlg._set_all_refine(False)
    app.processEvents()

    # The three keep buttons sit side by side (they used to be stacked).
    ui = dlg.ui
    buttons = (ui.btn_apply_initial, ui.btn_apply_best, ui.btn_apply_last)
    check("layout: the three keep buttons are side by side",
          len({b.y() for b in buttons}) == 1
          and [b.x() for b in buttons] == sorted(b.x() for b in buttons))


def _check_value_editing(dlg):
    """Hand-editing the Value column, and the warning line it drives.

    The Value column was read-only (the delegate refused an editor) because
    nothing wrote a typed number back. It is editable again - as the old GTK app
    always had it - so this pins BOTH halves: the model really moves, and the
    user is told that a direct model write just happened."""
    tree = dlg.ui.tree_refinables
    warning = dlg.ui.lbl_param_warning
    leaves = list(dlg._leaf_items())
    item, ref = leaves[0]

    dlg._set_all_refine(False)
    dlg._hand_edited = set()
    dlg._update_warning()
    app.processEvents()
    check("warn: hidden when there is nothing to report",
          not warning.isVisible() and warning.text() == "")

    # 1. A typed Value writes through to the model.
    before = ref.value
    item.setText(1, "%.4f" % (before + 0.5))
    app.processEvents()
    check("value: a typed Value writes through to the model",
          abs(ref.value - (before + 0.5)) < 1e-9)
    check("value: ...and the row is marked as hand-set",
          id(ref) in dlg._hand_edited)
    check("warn: the hand-edit warning appears",
          warning.isVisible() and "set by hand" in warning.text())

    # 2. Garbage reverts to the model's own number, as Min/Max always did.
    item.setText(1, "rubbish")
    app.processEvents()
    check("value: a non-numeric edit reverts and leaves the model alone",
          abs(ref.value - (before + 0.5)) < 1e-9
          and item.text(1) == "%.4f" % ref.value)

    # 3. Min >= Max on a TICKED parameter is the refiner's silent skip: the
    #    warning is the only place it is visible before a run starts.
    keep = (ref.minimum, ref.maximum)
    ref.set_ref_info(refine=True, minimum=5.0, maximum=5.0)
    dlg._refresh_values()
    app.processEvents()
    check("warn: a ticked Min >= Max parameter is named",
          "Min not below Max" in warning.text() and ref.label in warning.text())
    check("warn: ...and the refiner would indeed skip it",
          dlg._effective_parameters() == 0)
    marked = item.background(2).style() != Qt.BrushStyle.NoBrush
    check("warn: ...and its Min/Max cells are tinted", marked)

    # 4. Fixing the bounds RESETS the warning and the tint - the marks describe
    #    the current state, never a stale one.
    ref.set_ref_info(minimum=keep[0], maximum=keep[1])
    dlg._refresh_values()
    app.processEvents()
    check("warn: fixing the bounds clears that message",
          "Min not below Max" not in warning.text())
    check("warn: ...and clears the cell tint",
          item.background(2).style() == Qt.BrushStyle.NoBrush)

    # 5. A value outside its own bounds: the search clips the start value, so
    #    the run does not begin where the cell says it does.
    ref.set_ref_info(refine=True, minimum=ref.value + 10.0,
                     maximum=ref.value + 20.0)
    dlg._refresh_values()
    app.processEvents()
    check("warn: a value outside its Min/Max is called out",
          "Outside Min/Max" in warning.text())
    check("warn: ...with the reason in the cell's own tooltip",
          "nearest bound" in item.toolTip(1))

    # 6. Everything resets together when the state is clean again.
    ref.set_ref_info(refine=False, minimum=keep[0], maximum=keep[1])
    ref.value = before
    dlg._hand_edited = set()
    dlg._refresh_values()
    app.processEvents()
    check("warn: hides again once nothing is wrong",
          not warning.isVisible() and warning.text() == "")
    check("value: the tree mirrors the restored model value",
          item.text(1) == "%.4f" % before)
    tree.collapseAll()


def _check_per_specimen_curves(dlg):
    """The progress plot draws each specimen's Rp under the mean.

    The reported Rp is the MEAN over the mixture's specimens, so one curve
    cannot show a run that improves one specimen by degrading another. Fed from
    the same progress signal, so the thin curves always average to the bold
    one."""
    dlg._start_progress()
    points = [
        (1, 10.0, [("A", 8.0), ("B", 12.0)]),
        (4, 9.0, [("A", 7.0), ("B", 11.0)]),
        (9, 8.5, [("A", 5.0), ("B", 12.0)]),   # mean improves, B gets worse
    ]
    for n, best, parts in points:
        dlg._on_progress(n, best, parts)
    check("per-specimen: a series is kept per specimen",
          sorted(dlg._prog_series) == ["A", "B"])
    check("per-specimen: each series follows the mean's evaluation axis",
          all(evals == [1, 4, 9] for evals, _v in dlg._prog_series.values()))
    check("per-specimen: the mean of the curves IS the plotted best",
          all(abs((dlg._prog_series["A"][1][i] + dlg._prog_series["B"][1][i]) / 2
                  - dlg._prog_best[i]) < 1e-9 for i in range(3)))

    dlg._redraw_progress(force=True)
    lines = dlg._prog_ax.get_lines()
    labels = [l.get_label() for l in lines]
    check("per-specimen: one line per specimen plus the mean",
          len(lines) == 3 and "mean" in labels
          and "A" in labels and "B" in labels)
    mean_line = lines[labels.index("mean")]
    thin = [l for l in lines if l.get_label() != "mean"]
    check("per-specimen: the mean stays the boldest line",
          all(mean_line.get_linewidth() > l.get_linewidth() for l in thin))
    check("per-specimen: the legend names them", dlg._prog_ax.get_legend() is not None)

    # A run with no breakdown (an older signal, or a mixture with no usable
    # specimen) must still draw the mean and nothing else.
    dlg._start_progress()
    dlg._on_progress(1, 5.0)
    dlg._on_progress(2, 4.0)
    dlg._redraw_progress(force=True)
    check("per-specimen: absent breakdown still draws just the mean",
          len(dlg._prog_ax.get_lines()) == 1 and dlg._prog_series == {})
    dlg._finish_progress()


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
    for item, _ref in dlg._leaf_items():
        if flagged >= 2:
            break
        item.setCheckState(4, _Qt.CheckState.Checked)
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
    # Every Rp in the report is a mean over the specimens; the breakdown says so.
    from mudlab.calculations.mixture import per_specimen_residuals
    per = per_specimen_residuals(MIX)
    check("report: breaks the mean Rp down per specimen",
          "Rp per specimen" in text
          and all(name[:20] in text for name, _v in per))
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
    # The tree's Value column is a LIVE view of the model: it must follow the
    # refinement and each keep, or it would show pre-refinement numbers next to
    # a refined plot.
    check("tree: the Value column follows the applied solution",
          all(item.text(1) == "%.4f" % ref.value
              for item, ref in dlg._leaf_items()))
    # Keyed by POSITION, never by leaf title: titles repeat across phases (every
    # phase has a "sigma*"), so a title-keyed dict silently compares the wrong
    # rows. Only the full path is unique.
    shown_initial = [item.text(1) for item, _r in dlg._leaf_items()]
    dlg._on_apply("best")
    app.processEvents()
    shown_best = [item.text(1) for item, _r in dlg._leaf_items()]
    # The contract is "the column mirrors the model", not "the optimiser
    # improved" - a 12-evaluation run may legitimately end where it started, and
    # asserting otherwise would be testing scipy, not the UI.
    moved = any(abs(b - i) > 5e-5 for b, i
                in zip(refiner.best_solution, refiner.initial_solution))
    check("tree: ...and re-renders for the newly kept solution",
          all(item.text(1) == "%.4f" % ref.value
              for item, ref in dlg._leaf_items())
          and (shown_best != shown_initial if moved else True))
    if not moved:
        print("  (the short run ended at its start; only the mirroring was checked)")
    dlg._on_apply("initial")
    app.processEvents()

    def _gof(report):
        line = next((l for l in report.splitlines() if "GoF" in l), "")
        return line.split(":")[-1].strip()

    dlg._on_apply("best")
    app.processEvents()
    best_text = dlg.ui.txt_report.toPlainText()
    check("report: the GoF is recomputed for the applied solution",
          _gof(best_text) != _gof(initial_text))

    # A hand-edited Value moves the model AWAY from the solution the report
    # names. Saying only "Best solution" would then describe a state that is no
    # longer there - the same lie an earlier version told with "nothing applied".
    hand_item, hand_ref = list(dlg._leaf_items())[0]
    hand_item.setText(1, "%.4f" % (hand_ref.value + 0.25))
    app.processEvents()
    hand_text = dlg.ui.txt_report.toPlainText()
    check("report: a hand edit is disclosed on the Applied line",
          "changed by hand since" in hand_text)
    check("report: ...and the GoF is recomputed for the edited model",
          _gof(hand_text) != _gof(best_text))
    dlg._on_apply("best")
    app.processEvents()
    check("report: keeping a solution clears that disclosure",
          "changed by hand since" not in dlg.ui.txt_report.toPlainText()
          and not dlg._hand_edited)
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
        "grpParameters": (ui.tree_refinables,),
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
    check("layout: Basin Hopping's options wrap onto a second row",
          len(dlg._option_spins) == 4 and rows == {0, 1})
    # Basin Hopping was selected to INSPECT its layout, never to run: its
    # "iterations" are full restarts. The choice persists on the mixture, so put
    # L-BFGS-B back before anything downstream actually refines.
    dlg.ui.cmb_method.setCurrentIndex(dlg.ui.cmb_method.findData(0))
    app.processEvents()
    check("layout: the run method is left at L-BFGS-B, never Basin Hopping",
          int(dlg.ui.cmb_method.currentData()) == 0)
    check("layout: every option spin carries an explanatory tooltip",
          all(spin.toolTip() for spin, _kind in dlg._option_spins.values()))

    # Long parameter names elide on one line (rather than doubling row height)
    # and keep their full text in a tooltip.
    _check_refinables_tree(dlg)

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
    tree = dlg.ui.tree_refinables
    check("layout: at minimum size the tree still fits its frame",
          dlg.minimumWidth() >= dlg.minimumSizeHint().width()
          and tree.width() <= ui.grpParameters.width())
    check("layout: the tree does not need a horizontal scrollbar",
          tree.horizontalScrollBar().maximum() == 0)
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
    # L-BFGS-B with a tiny budget: never drive a test with Basin Hopping.
    dlg3.ui.cmb_method.setCurrentIndex(dlg3.ui.cmb_method.findData(0))
    for key in ("maxfun", "maxiter"):
        if key in dlg3._option_spins:
            dlg3._option_spins[key][0].setValue(8)
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
