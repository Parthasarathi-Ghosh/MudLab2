#!/usr/bin/env python
"""Durable harness for the multi-target Match Minerals workflow, run head-less.

The dialog used to score against whatever arrived at open - in practice ONE
peak, because the Peaks list is single-selection - and nothing inside it could
change that. The redesign (old MudLab 71807ac8's targets panel, as a checkable
dropdown) is pinned here:

  * the Targets dropdown lists every peak, ticked = target, with a
    "<n> of <total> peaks" summary; a click in the popup toggles a tick and the
    popup stays open; every change rescores; the last target cannot go;
  * rescoring keeps the selected mineral and any hand-added rows;
  * Append labels writes onto the CURRENT targets only;
  * the targets are highlighted on the plot (transient, never saved);
  * while the dialog is open the plot is view-only: zoom, pan and reset work,
    a double-click on a peak no longer destroys the dialog, and nothing can
    arm a pick; closing restores everything.

The dialog-only checks use a synthetic quartz specimen, so they run anywhere.
The main-window checks drive the real app on a sample project and are skipped
(not failed) when no project with peaks is present.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_match_targets.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import glob
import os
import sys
import tempfile
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from mudlab.calculations import get_2t_from_nm, peak_detection as pd  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.match_minerals_dialog import (  # noqa: E402
    _INDEX_ROLE, _MANUAL_ROLE, MatchMineralsDialog,
)
from mudlab.models.marker import Marker  # noqa: E402
from mudlab.models.specimen import DEFAULT_WAVELENGTH, Specimen  # noqa: E402
from mudlab.plot_controller import (  # noqa: E402
    MATCH_TARGET_COLOR, MATCH_TARGET_LINEWIDTH, PatternPlot,
)
from mudlab.qt_utils import install_enter_policy  # noqa: E402

app = QApplication.instance() or QApplication([])
install_enter_policy(app)
# A modal box would block a head-less run; none is expected, so record any.
_unexpected_boxes: list[str] = []
for _name in ("question", "information", "warning", "critical"):
    setattr(QMessageBox, _name, staticmethod(
        lambda *a, _n=_name, **k: (_unexpected_boxes.append(_n),
                                   QMessageBox.StandardButton.No)[1]))

results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


_MINERALS = pd.load_mineral_references()
_QUARTZ_IDX = next(i for i, m in enumerate(_MINERALS) if m[0].startswith("Quartz"))
_QUARTZ = _MINERALS[_QUARTZ_IDX][0]


def quartz_specimen():
    """Gaussians + a peak at each of quartz's 8 strongest lines, added in
    intensity order (NOT 2theta order) so ordering assumptions show up."""
    _name, _abbr, peaks = _MINERALS[_QUARTZ_IDX]
    top = sorted(peaks, key=lambda p: p[1], reverse=True)[:8]
    lines = [(get_2t_from_nm(d / 10.0, DEFAULT_WAVELENGTH), i) for d, i in top]
    x = np.linspace(5.0, 80.0, 6000)
    y = np.full_like(x, 2.0)
    for pos, inten in lines:
        y = y + inten * np.exp(-0.5 * ((x - pos) / 0.12) ** 2)
    spec = Specimen(name="quartz-synth")
    spec.set_experimental_pattern(x, y)
    for n, (pos, _i) in enumerate(lines):
        spec.add_marker(Marker(label="pk%d" % n, position=pos))
    return spec


def _rows(dlg):
    m = dlg.matches_model
    return [(m.item(r, 0).text(), m.item(r, 1).text(), float(m.item(r, 2).text()))
            for r in range(m.rowCount())]


def _expected_rows(dlg):
    return [(name, abbr, round(score, 5)) for name, abbr, _mp, _pm, score
            in pd.score_minerals(dlg._marker_peaks, _MINERALS)]


def _ticked(dlg):
    model = dlg.targets_model
    return [model.item(r).data(Qt.ItemDataRole.UserRole + 5)
            for r in range(model.rowCount())
            if model.item(r).checkState() == Qt.CheckState.Checked]


def _click_popup_row(dlg, row):
    view = dlg.ui.cmb_targets.view()
    rect = view.visualRect(dlg.targets_model.index(row, 0))
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier, rect.center())
    app.processEvents()


def _row_of(dlg, marker):
    model = dlg.targets_model
    return next(r for r in range(model.rowCount())
                if model.item(r).data(Qt.ItemDataRole.UserRole + 5) is marker)


# ----------------------------------------------------------------------
# The dropdown: contents, ticking, rescoring
# ----------------------------------------------------------------------
def check_dropdown():
    spec = quartz_specimen()
    first = spec.markers[0]
    dlg = MatchMineralsDialog(specimen=spec, targets=[first])
    dlg.show()
    app.processEvents()
    cmb = dlg.ui.cmb_targets

    by_pos = sorted(spec.markers, key=lambda m: m.position)
    listed = [dlg.targets_model.item(r).data(Qt.ItemDataRole.UserRole + 5)
              for r in range(dlg.targets_model.rowCount())]
    check("dropdown: lists every peak, in 2theta order",
          len(listed) == len(by_pos) and all(a is b for a, b in zip(listed, by_pos)))
    check("dropdown: only the opening peak is ticked",
          len(_ticked(dlg)) == 1 and _ticked(dlg)[0] is first)
    check("dropdown: closed box reads '1 of 8 peaks', not a row's text",
          cmb.placeholderText() == "1 of 8 peaks" and cmb.currentIndex() == -1)
    check("opening target: the scorer sees exactly one peak",
          len(dlg._marker_peaks) == 1)

    # Tick a second peak with a real click in the open popup.
    second = spec.markers[1]
    cmb.showPopup()
    app.processEvents()
    _click_popup_row(dlg, _row_of(dlg, second))
    check("tick: a click in the popup keeps the popup open", cmb.view().isVisible())
    check("tick: the peak becomes a target (appended after the first)",
          len(dlg.targets) == 2 and dlg.targets[0] is first and dlg.targets[1] is second)
    check("tick: summary reads '2 of 8 peaks'", cmb.placeholderText() == "2 of 8 peaks")
    check("tick: the scorer now sees both peaks", len(dlg._marker_peaks) == 2)
    check("tick: matches rescored == score_minerals over the new peak list",
          [(n, a, round(s, 5)) for n, a, s in _rows(dlg)] == _expected_rows(dlg))

    # Space toggles the popup's current row too.
    third = spec.markers[2]
    view = cmb.view()
    view.setCurrentIndex(dlg.targets_model.index(_row_of(dlg, third), 0))
    QTest.keyClick(view, Qt.Key.Key_Space)
    app.processEvents()
    check("Space in the popup toggles the current peak",
          any(t is third for t in dlg.targets) and len(dlg.targets) == 3)

    # Untick: back down.
    _click_popup_row(dlg, _row_of(dlg, third))
    _click_popup_row(dlg, _row_of(dlg, second))
    check("untick: peaks leave the targets and the scores follow",
          len(dlg.targets) == 1 and dlg.targets[0] is first
          and len(dlg._marker_peaks) == 1
          and [(n, a, round(s, 5)) for n, a, s in _rows(dlg)] == _expected_rows(dlg))

    # The last target cannot be removed.
    _click_popup_row(dlg, _row_of(dlg, first))
    check("the last target cannot be unticked",
          len(dlg.targets) == 1 and dlg.targets[0] is first
          and len(_ticked(dlg)) == 1 and cmb.placeholderText() == "1 of 8 peaks")
    cmb.hidePopup()

    # Enter on a popup row (keyboard choice) toggles as well.
    cmb.showPopup()
    app.processEvents()
    view.setCurrentIndex(dlg.targets_model.index(_row_of(dlg, second), 0))
    QTest.keyClick(view, Qt.Key.Key_Return)
    app.processEvents()
    check("Enter in the popup toggles the peak and keeps the summary",
          any(t is second for t in dlg.targets) and cmb.currentIndex() == -1
          and cmb.placeholderText() == "2 of 8 peaks")
    dlg.reject()
    dlg.deleteLater()


def check_rescore_keeps_state():
    spec = quartz_specimen()
    first, second = spec.markers[0], spec.markers[1]
    dlg = MatchMineralsDialog(specimen=spec, targets=[first])

    # Select a mineral that is listed now AND after adding a target, but NOT
    # first after it - otherwise "select the top match" would pass vacuously.
    peaks_one = list(dlg._marker_peaks)
    dlg.targets.append(second)
    peaks_two = dlg._compute_marker_peaks()
    dlg.targets.remove(second)
    after = [idx for idx, _s in dlg._score_all(peaks_two)]
    cand = next((idx for idx in after[1:] if dlg._match_row_for_index(idx) is not None),
                None)
    check("(precondition) a mineral listed before and after, not first after", cand is not None)
    if cand is not None:
        dlg.ui.tv_matches.setCurrentIndex(
            dlg.matches_model.index(dlg._match_row_for_index(cand), 0))
        dlg.toggle_target(second)
        row = dlg._match_row_for_index(cand)
        still = dlg.ui.tv_matches.selectionModel().selectedRows()
        check("rescore: the selected mineral stays selected (its lines stay on the plot)",
              row not in (None, 0) and still and still[0].row() == row)
        dlg.toggle_target(second)

    # A hand-added row survives rescoring. Use a mineral that scores NOTHING
    # against either peak list, so only the keep-hand-added rule can hold it.
    zero = next(i for i, m in enumerate(_MINERALS)
                if not pd.score_minerals(peaks_one, [m])
                and not pd.score_minerals(peaks_two, [m]))
    mrow = next(r for r in range(dlg.minerals_model.rowCount())
                if dlg.minerals_model.item(r, 0).data(_INDEX_ROLE) == zero)
    dlg.ui.tv_minerals.setCurrentIndex(dlg.minerals_model.index(mrow, 0))
    dlg._add_selected_match()
    dlg.toggle_target(second)
    row = dlg._match_row_for_index(zero)
    check("rescore: a hand-added mineral is kept (and flagged as added by hand)",
          row is not None and dlg.matches_model.item(row, 0).data(_MANUAL_ROLE)
          and float(dlg.matches_model.item(row, 2).text()) == 0.0)
    # Adding a mineral that is already listed does not duplicate it.
    qrow = next(r for r in range(dlg.minerals_model.rowCount())
                if dlg.minerals_model.item(r, 0).data(_INDEX_ROLE) == _QUARTZ_IDX)
    before = dlg.matches_model.rowCount()
    dlg.ui.tv_minerals.setCurrentIndex(dlg.minerals_model.index(qrow, 0))
    dlg._add_selected_match()
    check("adding an already-scored mineral by hand does not duplicate it",
          dlg.matches_model.rowCount() == before)
    # Every row previews the FULL reference list, whichever list it is in.
    q = dlg._match_row_for_index(_QUARTZ_IDX)
    check("a scored row carries the mineral's full line list (not the 15 scored)",
          q is not None and dlg.matches_model.item(q, 0).data(Qt.ItemDataRole.UserRole + 3)
          == _MINERALS[_QUARTZ_IDX][2])
    dlg.reject()
    dlg.deleteLater()


def check_apply_and_external_edits():
    spec = quartz_specimen()
    first, second, third = spec.markers[0], spec.markers[1], spec.markers[2]
    dlg = MatchMineralsDialog(specimen=spec, targets=[first])
    dlg.toggle_target(second)
    dlg.toggle_target(third)
    dlg.toggle_target(third)  # third ticked, then unticked
    q = dlg._match_row_for_index(_QUARTZ_IDX)
    dlg.ui.tv_matches.setCurrentIndex(dlg.matches_model.index(q, 0))
    abbr = _MINERALS[_QUARTZ_IDX][1]
    dlg._on_apply()
    check("Append labels: every CURRENT target is labelled",
          first.label.endswith(", " + abbr) and second.label.endswith(", " + abbr))
    check("Append labels: a peak no longer targeted is left alone",
          abbr not in third.label)
    text = dlg.targets_model.item(_row_of(dlg, first)).text()
    check("Append labels: the dropdown shows the new label", abbr in text)

    # A target deleted elsewhere stops counting.
    spec.remove_marker(second)
    app.processEvents()
    check("a target deleted elsewhere leaves the targets and the dropdown",
          len(dlg.targets) == 1 and dlg.targets[0] is first
          and dlg.targets_model.rowCount() == 7 and len(dlg._marker_peaks) == 1)
    dlg.reject()
    dlg.deleteLater()


def check_enter_policy():
    spec = quartz_specimen()
    dlg = MatchMineralsDialog(specimen=spec, targets=[spec.markers[0]])
    dlg.show()
    app.processEvents()
    check("Append labels is never the default button (after a real show)",
          not dlg.ui.btn_apply.autoDefault() and not dlg.ui.btn_apply.isDefault())
    before = [m.label for m in spec.markers]
    dlg.ui.edit_search.setFocus()
    QTest.keyClick(dlg.ui.edit_search, Qt.Key.Key_Return)
    QTest.keyClick(dlg.ui.edit_search, Qt.Key.Key_Enter)
    app.processEvents()
    check("Enter in the search box appends no labels and keeps the dialog open",
          [m.label for m in spec.markers] == before and dlg.isVisible())
    dlg.reject()
    dlg.deleteLater()


def check_highlight_drawing():
    spec = quartz_specimen()
    for m in spec.markers:
        m.inherit_style = False
        m.style = "solid"  # draw a connector line too
    dlg = MatchMineralsDialog(specimen=spec, targets=[spec.markers[0]])
    check("highlight: the targets are set on the specimen while open",
          spec.match_targets is not None and spec.match_targets[0] is spec.markers[0])

    from mudlab.models.project import Project
    project = Project()
    project.add_specimen(spec)
    # A pick handler makes the plot record its peak artists (as in the app).
    plot = PatternPlot([spec], project, on_marker_pick=lambda _m: None)
    target, other = spec.markers[0], spec.markers[1]
    labels = {m: a for a, m in plot._marker_artists.items()
              if a.__class__.__name__ == "Text"}
    lines = {m: a for a, m in plot._marker_artists.items()
             if a.__class__.__name__ == "Line2D"}
    t_box = labels[target].get_bbox_patch()
    check("highlight: a target's label is bold on a highlighter box",
          t_box is not None and labels[target].get_fontweight() in ("bold", 700)
          and t_box.get_facecolor()[:3] == tuple(
              int(MATCH_TARGET_COLOR[i:i + 2], 16) / 255 for i in (1, 3, 5)))
    check("highlight: a non-target label is drawn as before",
          labels[other].get_bbox_patch() is None)
    check("highlight: a target's line is heavier",
          lines[target].get_linewidth() == MATCH_TARGET_LINEWIDTH
          and lines[other].get_linewidth() == 1.0)
    dlg.reject()
    check("highlight: cleared when the dialog closes", spec.match_targets is None)
    plot.draw_pattern()
    boxes = [a.get_bbox_patch() for a, m in plot._marker_artists.items()
             if a.__class__.__name__ == "Text"]
    check("highlight: gone from the plot after closing", all(b is None for b in boxes))
    dlg.deleteLater()


# ----------------------------------------------------------------------
# The real app: view-only plot while the dialog is open
# ----------------------------------------------------------------------
def _fixture():
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        for spec in project.specimens:
            if spec is not None and len(spec.markers) >= 3 and spec.has_experimental_data:
                return path
    return None


def _label_artist(plot, marker):
    plot.canvas.draw()
    app.processEvents()
    return next(a for a, m in plot._marker_artists.items()
                if m is marker and a.__class__.__name__ == "Text")


def _canvas_point(plot, artist):
    bb = artist.get_window_extent(plot.canvas.get_renderer())
    dpr = plot.canvas.devicePixelRatioF()
    return QPoint(int((bb.x0 + bb.x1) / 2 / dpr),
                  int(plot.canvas.height() - (bb.y0 + bb.y1) / 2 / dpr))


def _dblclick(plot, marker):
    QTest.mouseDClick(plot.canvas, Qt.MouseButton.LeftButton,
                      Qt.KeyboardModifier.NoModifier,
                      _canvas_point(plot, _label_artist(plot, marker)))
    app.processEvents()


def _wheel(plot, steps_up=1):
    canvas = plot.canvas
    pos = QPointF(canvas.width() / 2, canvas.height() / 3)
    event = QWheelEvent(pos, canvas.mapToGlobal(pos), QPoint(0, 0),
                        QPoint(0, 120 * steps_up), Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                        False)
    QApplication.sendEvent(canvas, event)
    app.processEvents()


def check_main_window(path):
    from mudlab.main_window import MainWindow
    window = MainWindow()
    window.resize(1500, 950)
    window.show()
    app.processEvents()
    window._set_project(load_mud(path))
    app.processEvents()
    plot = window.pattern_plots[0]
    spec = plot.specimens[0]
    markers = sorted(spec.markers, key=lambda m: m.position)
    first, other = markers[1], markers[len(markers) // 2]

    # Open the real way: double-click a peak label, then Match minerals.
    _dblclick(plot, first)
    peaks = window._edit_markers_dialog
    QTest.mouseClick(peaks.btn_match_minerals, Qt.MouseButton.LeftButton)
    app.processEvents()
    dlg = peaks._match_dialog
    check("app: Match Minerals opens on the double-clicked peak alone",
          dlg is not None and dlg.isVisible() and len(dlg.targets) == 1
          and dlg.targets[0] is first)
    check("app: every plot is view-only while it is open",
          window.plot_interaction_locked
          and all(p.interaction_locked for p in window.pattern_plots))
    check("app: the target is highlighted on the plot",
          _label_artist(plot, first).get_bbox_patch() is not None)

    # A double-click on another peak must not rebuild Peaks / kill the dialog.
    _dblclick(plot, other)
    alive = True
    try:
        visible = dlg.isVisible()
    except RuntimeError:
        alive, visible = False, False
    check("app: double-clicking another peak leaves Match Minerals open",
          alive and visible and window._edit_markers_dialog is peaks
          and not peaks.isVisible())
    check("app: ...and does not change the targets",
          alive and len(dlg.targets) == 1 and dlg.targets[0] is first)

    # Nothing can arm a click-pick meanwhile (e.g. the Select Point button).
    cancelled = []
    window.arm_position_pick(lambda *_a: None, on_cancel=lambda: cancelled.append(1))
    check("app: a position pick is refused while the plot is view-only",
          window._pending_pick is None and cancelled == [1])

    # Zoom, pan and reset still work.
    plot.reset_view()
    home = tuple(plot.axes.get_xlim())
    _wheel(plot, steps_up=2)
    zoomed = tuple(plot.axes.get_xlim())
    check("app: mouse-wheel zoom still works",
          zoomed != home and (zoomed[1] - zoomed[0]) < (home[1] - home[0]))
    plot.canvas.setFocus()
    QTest.keyClick(plot.canvas, Qt.Key.Key_Right)
    app.processEvents()
    panned = tuple(plot.axes.get_xlim())
    check("app: arrow-key pan still works", panned != zoomed)
    QTest.mouseClick(plot.canvas, Qt.MouseButton.RightButton,
                     Qt.KeyboardModifier.NoModifier,
                     QPoint(plot.canvas.width() // 2, plot.canvas.height() // 3))
    app.processEvents()
    check("app: right-click still resets the view",
          np.allclose(plot.axes.get_xlim(), home))

    # A rebuild of the plot keeps both the lock and the highlight.
    window._refresh_plots()
    app.processEvents()
    plot = window.pattern_plots[0]
    check("app: a rebuilt plot is view-only too", plot.interaction_locked)
    check("app: a rebuilt plot still shows the highlight",
          _label_artist(plot, first).get_bbox_patch() is not None)

    # Edit markers from the menu must not rebuild Peaks either.
    window._open_edit_markers(spec)
    app.processEvents()
    check("app: Edit markers while Match Minerals is open keeps both windows",
          window._edit_markers_dialog is peaks and dlg.isVisible())

    # Highlight and lock are transient: never saved.
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "out.mud")
        save_mud(window.project, out)
        with zipfile.ZipFile(out) as zf:
            blob = b"".join(zf.read(n) for n in zf.namelist())
        reloaded = load_mud(out)
    check("app: the target highlight is never written to the .mud",
          b"match_targets" not in blob
          and all(s.match_targets is None for s in reloaded.specimens))

    # Reopening Match Minerals: the OLD dialog's deferred deletion must not
    # unlock the plot under the NEW one.
    peaks._on_match_minerals()
    app.processEvents()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    new = peaks._match_dialog
    check("app: replacing the dialog keeps the plot view-only for the new one",
          new is not dlg and new.isVisible() and window.plot_interaction_locked)
    dlg = new

    # Close: everything restored.
    dlg.reject()
    app.processEvents()
    plot = window.pattern_plots[0]
    check("app: closing unlocks the plot",
          not window.plot_interaction_locked and not plot.interaction_locked)
    check("app: closing clears the highlight and the reference lines",
          spec.match_targets is None and spec.mineral_preview is None
          and _label_artist(plot, first).get_bbox_patch() is None)
    check("app: closing brings the Peaks window back", peaks.isVisible())
    peaks.close()
    app.processEvents()
    _dblclick(plot, other)
    reopened = window._edit_markers_dialog
    check("app: after closing, a double-click opens Peaks again",
          reopened is not None and reopened is not peaks and reopened.isVisible()
          and reopened._selected_markers() == [other])
    reopened.close()
    app.processEvents()


def main():
    check_dropdown()
    check_rescore_keeps_state()
    check_apply_and_external_edits()
    check_enter_policy()
    check_highlight_drawing()
    path = _fixture()
    if path is None:
        print("No sample project with peaks: main-window checks skipped.")
    else:
        check_main_window(path)
    check("no unexpected message box was raised", not _unexpected_boxes)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- Match Minerals targets verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    # Skip interpreter teardown of the live main window (a dirty project's
    # close path is not what this harness tests).
    os._exit(code)
