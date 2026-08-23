#!/usr/bin/env python
"""The Peaks dialog: its name, getting out of the way of the plot, and ordering.

Three changes requested 2026-08-23 (item #9):

  a) it is called **Peaks** now, not "Edit Markers" - the window, the toolbar
     button and the specimens context menu. MARKER stays the model name and the
     .mud key; only what the user reads changed;
  b) it **steps aside** while the user has to interact with the plot: for a
     Sample pick, and for as long as Match Minerals is open (which draws
     reference peaks on the very pattern this window covers);
  c) the list is kept in **position order**. Peak detection appends in ascending
     2theta so a detected set is already ordered, but a hand-added peak lands at
     the end at position 0 - it moves into place when its position is COMMITTED.

The load-bearing detail behind (b): hiding is only safe because a pick can now
be CANCELLED. `arm_position_pick` gained `on_cancel`, and Esc fires it. Before
that, an armed pick could only ever end in a plot click, so a hidden dialog
whose user changed their mind would have been stranded with no way back - the
checks below pin the cancel path for exactly that reason.

And behind (c): the position spin box writes on `valueChanged`, i.e. per
keystroke, so sorting there would move the row under the cursor mid-type
("25" would jump the selection once at "2"). Sorting happens on COMMIT only.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_peaks_dialog.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no specimen with markers.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.main_window import MainWindow  # noqa: E402
from mudlab.models.marker import Marker  # noqa: E402

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in sorted(glob.glob(os.path.join(
            _REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        for specimen in project.specimens:
            if specimen is not None and specimen.markers:
                return path, project, specimen
    return None, None, None


PATH, PROJECT, SPECIMEN = _fixture()
if PATH is None:
    print("No specimen with markers; skipping (exit 2).")
    raise SystemExit(2)


def main():
    window = MainWindow()
    window._set_project(PROJECT)
    app.processEvents()
    specimen = next(s for s in window.project.specimens
                    if s is not None and s.markers)
    window.show_specimen_plots([specimen])
    app.processEvents()

    # ------------------------------------------------------------- (a) name
    check("name: the toolbar action reads Peaks",
          window.ui.actionEditMarkers.text() == "Peaks")
    check("name: its tooltip no longer says 'Edit Markers'",
          "Edit Markers" not in window.ui.actionEditMarkers.toolTip())
    menu = window._build_specimens_menu()
    check("name: the specimens context menu says Peaks",
          any(a.text() == "Peaks" for a in menu.actions()))
    check("name: ...and no longer says Edit markers",
          not any("Edit markers" == a.text() for a in menu.actions()))

    window._open_edit_markers(specimen)
    app.processEvents()
    dialog = window._edit_markers_dialog
    check("name: the window title starts with Peaks",
          dialog.windowTitle().startswith("Peaks"))
    check("name: ...and still names the specimen",
          specimen.name in dialog.windowTitle())
    check("name: the first column is headed Peak",
          dialog.objects_model.horizontalHeaderItem(0).text() == "Peak")

    # The MODEL keeps its name - this is a labelling change, not a rename of
    # the .mud key, which the old app also reads.
    check("name: the model is still markers (file compatibility)",
          hasattr(specimen, "markers") and isinstance(specimen.markers, tuple))

    # ----------------------------------------------------- (b) sample picks
    dialog.ui.edit_objects_treeview.setCurrentIndex(
        dialog.objects_model.index(0, 0))
    app.processEvents()
    check("aside: the dialog starts visible", dialog.isVisible())

    dialog._on_sample_position()
    app.processEvents()
    check("aside: it hides for the pick", not dialog.isVisible())
    check("aside: the pick is armed", window._pending_pick is not None)
    check("aside: the hint says Esc cancels",
          "Esc" in window.ui.statusBar.currentMessage())

    marker = dialog.marker_widget._marker
    window._on_plot_click(window.pattern_plots[0], 12.5)
    app.processEvents()
    check("aside: a click brings it back", dialog.isVisible())
    check("aside: ...and the click set the position",
          abs(marker.position - 12.5) < 1e-9)
    check("aside: the pick disarmed", window._pending_pick is None)

    # THE CANCEL PATH - the reason hiding is safe at all.
    dialog._on_sample_position()
    app.processEvents()
    check("cancel: hidden again", not dialog.isVisible())
    window.cancel_position_pick()
    app.processEvents()
    check("cancel: Esc/cancel brings the dialog back", dialog.isVisible())
    check("cancel: ...and disarms the pick", window._pending_pick is None)
    check("cancel: ...and clears the status hint",
          not window.ui.statusBar.currentMessage())

    # Cancelling when nothing is armed must be a harmless no-op.
    window.cancel_position_pick()
    app.processEvents()
    check("cancel: cancelling an unarmed pick is a no-op", dialog.isVisible())

    # Arming a SECOND pick must release the first, or its owner waits forever.
    released = []
    window.arm_position_pick(lambda *a: None, "one",
                             on_cancel=lambda: released.append(True))
    window.arm_position_pick(lambda *a: None, "two")
    check("cancel: re-arming releases the previous owner", released == [True])
    window.cancel_position_pick()

    # A dialog the user CLOSED while it was out of the way must not come back.
    dialog._on_sample_position()
    app.processEvents()
    dialog._hidden_for_plot = False          # as if the user had closed it
    window.cancel_position_pick()
    app.processEvents()
    check("aside: a dialog dismissed while hidden is not resurrected",
          not dialog.isVisible())
    dialog.show()
    app.processEvents()

    # ---------------------------------------------------- (b) match minerals
    dialog._on_match_minerals()
    app.processEvents()
    check("aside: it hides while Match Minerals is open", not dialog.isVisible())
    check("aside: the match dialog is up",
          dialog._match_dialog is not None and dialog._match_dialog.isVisible())
    dialog._match_dialog.reject()
    app.processEvents()
    check("aside: closing Match Minerals brings it back", dialog.isVisible())

    # ------------------------------------------------------------ (c) order
    positions = [m.position for m in specimen.markers]
    check("order: detected peaks are already in position order",
          positions == sorted(positions))

    count = len(specimen.markers)
    dialog._on_add_marker()
    app.processEvents()
    added = dialog.marker_widget._marker
    check("order: a new peak is appended at the end",
          specimen.markers.index(added) == count)
    check("order: ...at position 0 until the user sets one",
          added.position == 0.0)

    # Typing must NOT move the row - only committing does.
    dialog.marker_widget.ui.spb_position.setValue(15.0)
    app.processEvents()
    check("order: typing a position does not move the row mid-edit",
          specimen.markers.index(added) == count)

    dialog.marker_widget.ui.spb_position.editingFinished.emit()
    app.processEvents()
    row = specimen.markers.index(added)
    ordered = [m.position for m in specimen.markers]
    check("order: committing sorts it into place (row %d of %d)"
          % (row, len(specimen.markers)), 0 < row < count)
    check("order: the whole list is in position order",
          ordered == sorted(ordered))
    check("order: the moved peak stays selected",
          dialog.ui.edit_objects_treeview.currentIndex().row() == row)

    # A sample pick commits a position too, so it sorts as well.
    dialog._on_sample_position()
    app.processEvents()
    window._on_plot_click(window.pattern_plots[0], 4.0)
    app.processEvents()
    ordered = [m.position for m in specimen.markers]
    check("order: a Sample pick also sorts", ordered == sorted(ordered))
    check("order: ...and keeps the peak selected",
          dialog.ui.edit_objects_treeview.currentIndex().row()
          == specimen.markers.index(added))

    # ------------------------------------------------ the model-level sort
    check("model: sort_markers reports False when nothing moves",
          specimen.sort_markers() is False)
    specimen.add_marker(Marker(label="Out of order", position=1.0))
    check("model: ...and True when it does", specimen.sort_markers() is True)
    ordered = [m.position for m in specimen.markers]
    check("model: sorted ascending by position", ordered == sorted(ordered))

    dialog.close()
    # Clear the dirty flag FIRST: this harness has edited marker positions, and
    # MainWindow.close() on a dirty project raises the modal "save changes?"
    # prompt, which hangs a head-less run forever (it looks like a slow
    # harness, not a blocked one).
    window._dirty = False
    window.close()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Peaks dialog:", os.path.basename(PATH), "-", specimen.name)
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
