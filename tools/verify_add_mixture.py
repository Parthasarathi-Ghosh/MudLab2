#!/usr/bin/env python
"""Durable harness for adding / removing mixtures from the Edit Mixtures shell.

The Edit Mixtures window's Add button creates a blank regular mixture directly
(the old app's Add Mixture type-chooser dialog was abandoned dead code - in-situ
mixtures were never finished - so create_new_object_proxy just returns a blank
Mixture). Remove deletes the selected mixture. This checks:

  1. model: Project.add_mixture / remove_mixture add and drop a mixture; remove
     of a non-member is a no-op (no cascade - nothing back-references a mixture).
  2. Add (dialog): the button creates a blank "New Mixture", appends it to the
     project and the list, selects it, and binds an EMPTY editor grid.
  3. the new mixture is usable: the editor's Add both grows its grid.
  4. Remove (dialog): drops the selected mixture from the project + list and
     reselects a neighbour; removing the last one unbinds the editor.

Run head-less from the repo root:

    ./python/python.exe tools/verify_add_mixture.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from mudlab.edit_mixture_widget import _FIRST_PHASE_ROW, _FIRST_SPEC_COL  # noqa: E402
from mudlab.edit_mixtures_dialog import EditMixturesDialog  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.models.mixture import Mixture  # noqa: E402

FIXTURE = os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")

_app = QApplication.instance() or QApplication([])
# Auto-confirm the Remove dialog so the head-less run does not block.
QMessageBox.question = staticmethod(
    lambda *a, **k: QMessageBox.StandardButton.Yes
)
results = []


def check(label, ok):
    results.append((label, bool(ok)))


def check_removal_persists():
    """AUDIT: deleting the LAST mixture did not persist.

    `save_mud` guarded the write with `if project.mixtures:`, so an empty live
    list left the STALE raw list in the file and the mixture came back on
    reload - silent data loss on an action the app calls irreversible. Phases
    carried the identical guard and lost it in ae75d60; this one was left.
    """
    import tempfile

    from mudlab.file_parsers.mud_project import save_mud

    tmp = os.path.join(tempfile.gettempdir(),
                       "verify_add_mixture_%d.mud" % os.getpid())
    try:
        # The last mixture.
        project = load_mud(FIXTURE)
        check("removal: the fixture has a mixture to delete",
              len(project.mixtures) == 1)
        project.remove_mixture(project.mixtures[0])
        save_mud(project, tmp)
        check("removal: deleting the LAST mixture persists",
              len(load_mud(tmp).mixtures) == 0)

        # One of several - this always worked, and must keep working.
        project = load_mud(FIXTURE)
        project.add_mixture(Mixture(name="Second"))
        save_mud(project, tmp)
        project = load_mud(tmp)
        project.remove_mixture(project.mixtures[0])
        save_mud(project, tmp)
        back = load_mud(tmp)
        check("removal: deleting one of several still persists",
              [m.name for m in back.mixtures] == ["Second"])
    finally:
        for leftover in (tmp, tmp + "~"):
            if os.path.exists(leftover):
                os.remove(leftover)


def check_add_remove_signal():
    """AUDIT: neither add nor remove signalled, so the window stayed CLEAN and
    closing threw the change away with no prompt."""
    project = load_mud(FIXTURE)
    fired = []
    project.data_changed.connect(lambda: fired.append(1))
    added = project.add_mixture(Mixture(name="Signalled"))
    check("signal: adding a mixture announces the change", len(fired) == 1)
    project.remove_mixture(added)
    check("signal: removing one announces it too", len(fired) == 2)
    # Removing something that is not there must stay silent.
    project.remove_mixture(added)
    check("signal: removing a mixture that is not there is silent",
          len(fired) == 2)


def check_orphaned_patterns():
    """Deleting a mixture leaves its specimens holding the curve IT produced -
    a calculated pattern with no model behind it, which is then saved.

    Cleared, but only for specimens no REMAINING mixture drives: a specimen can
    sit in several mixtures, and the others still produce its curve. And only
    for the specimens THIS deletion detached - sweeping every specimen would
    also clear a curve that was already orphaned long before and has nothing to
    do with this edit (308 r1.mud carries exactly such a specimen).
    """
    # 1. the plain case
    project = load_mud(FIXTURE)
    project.calculate()
    mixture = project.mixtures[0]
    driven = [s for s in mixture.specimens if s is not None]
    check("orphan: the mixture's specimens have curves to begin with",
          driven and all(s.has_calculated_data for s in driven))
    project.remove_mixture(mixture)
    check("orphan: deleting the mixture clears them",
          not any(s.has_calculated_data for s in driven))

    # 2. a specimen SHARED with another mixture keeps its curve
    project = load_mud(FIXTURE)
    project.calculate()
    first = project.mixtures[0]
    shared = first.specimens[0]
    second = Mixture(name="Second")
    second.add_specimen_slot(shared)
    second.add_phase_slot()
    project.add_mixture(second)
    project.calculate()
    others = [s for s in first.specimens if s is not None and s is not shared]
    project.remove_mixture(first)
    check("orphan: a specimen another mixture still drives KEEPS its curve",
          shared.has_calculated_data)
    check("orphan: ...while the rest are cleared",
          not any(s.has_calculated_data for s in others))

    # 3. an already-orphaned specimen is not collateral damage
    project = load_mud(FIXTURE)
    project.calculate()
    in_a_mixture = {id(s) for m in project.mixtures for s in m.specimens
                    if s is not None}
    stale = [s for s in project.specimens
             if s is not None and s.has_calculated_data
             and id(s) not in in_a_mixture]
    if stale:
        project.remove_mixture(project.mixtures[0])
        check("orphan: an ALREADY-orphaned specimen is left alone",
              stale[0].has_calculated_data)
    else:
        check("orphan: (no already-orphaned specimen in this fixture)", True)

    # 4. the helper's own contract
    project = load_mud(FIXTURE)
    project.calculate()
    mixture = project.mixtures[0]
    still_driven = [s for s in mixture.specimens if s is not None]
    cleared = project.clear_orphaned_patterns(still_driven)
    check("orphan: a specimen its mixture still drives is never cleared",
          cleared == [] and all(s.has_calculated_data for s in still_driven))


def _selected_row(dialog):
    rows = dialog.ui.edit_objects_treeview.selectionModel().selectedRows(0)
    return rows[0].row() if rows else -1


def run():
    # 1. Model.
    project = load_mud(FIXTURE)
    n0 = len(project.mixtures)
    m = Mixture(name="M")
    project.add_mixture(m)
    check("1 add_mixture appends", len(project.mixtures) == n0 + 1
          and project.mixtures[-1] is m)
    project.remove_mixture(m)
    check("1 remove_mixture drops it", len(project.mixtures) == n0
          and m not in project.mixtures)
    project.remove_mixture(m)  # not a member any more
    check("1 remove of a non-member is a no-op", len(project.mixtures) == n0)

    # 2. Add via the dialog.
    dialog = EditMixturesDialog(project=project)
    list_before = dialog.objects_model.rowCount()
    dialog._on_add_mixture()
    added = project.mixtures[-1]
    check("2 Add creates a blank 'New Mixture' in the project",
          len(project.mixtures) == n0 + 1 and added.name == "New Mixture"
          and added.n == 0 and added.m == 0)
    check("2 Add appends a list row and selects it",
          dialog.objects_model.rowCount() == list_before + 1
          and _selected_row(dialog) == list_before)
    check("2 the editor binds the new (empty) mixture",
          dialog.mixture_widget._mixture is added
          and dialog.mixture_widget.ui.tbl_matrix.columnCount() == _FIRST_SPEC_COL
          and dialog.mixture_widget.ui.tbl_matrix.rowCount() == _FIRST_PHASE_ROW)

    # 3. The new mixture is usable via the editor's structural buttons.
    dialog.mixture_widget._on_add_both()
    check("3 Add both grows the new mixture", added.n == 1 and added.m == 1)

    # 4. Remove via the dialog.
    row = _selected_row(dialog)
    rows_before = dialog.objects_model.rowCount()
    dialog._on_remove_mixture()
    check("4 Remove drops the mixture from the project + list",
          added not in project.mixtures
          and dialog.objects_model.rowCount() == rows_before - 1)
    check("4 a neighbour stays selected", _selected_row(dialog) >= 0
          and dialog.mixture_widget._mixture is not None)

    # Remove down to empty -> editor unbinds.
    while dialog._mixtures:
        dialog.ui.edit_objects_treeview.setCurrentIndex(
            dialog.objects_model.index(0, 0))
        dialog._on_remove_mixture()
    check("4 removing the last mixture unbinds the editor",
          dialog.objects_model.rowCount() == 0
          and dialog.mixture_widget._mixture is None)
    dialog.deleteLater()
    return None


def main():
    print("=" * 72)
    print("Add / remove mixture (Edit Mixtures shell)")
    print("=" * 72)
    if not os.path.isfile(FIXTURE):
        print("No sample project found; skipping (exit 2).")
        return 2
    rc = run()
    if rc == 2:
        return 2
    check_removal_persists()
    check_add_remove_signal()
    check_orphaned_patterns()
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("Add-mixture harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
