#!/usr/bin/env python
"""Durable harness for the Add / Remove Phase dialog wiring (Batch P2), run
head-less.

The model layer (add_phase / remove_phase and its cascades) is guarded by
tools/verify_phase_crud.py. This covers only what lives in the UI and cannot
be seen from the model:

  1. the buttons are in the right state - Add/Remove enabled, Import/Export
     honestly disabled with a reason;
  2. the Add dialog offers ONLY the ported path - empty phase, R locked to 0,
     the default-catalog and raw-pattern options disabled;
  3. Add builds a real phase (G blank components) and keeps the three views in
     lock-step: project.phases, the dialog's _phases snapshot, and the tree
     rows;
  4. Remove confirms first, then removes and keeps the three in lock-step,
     reselecting a neighbour;
  5. an Add followed by a Remove leaves the project exactly as it was.

Point 3/4 is the trap: the dialog holds its own list snapshot alongside the
tree model and the project, and a drift between them binds the editor to the
wrong phase.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_phase_dialogs.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample projects.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtCore import QItemSelectionModel  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

# The dialogs are modal: stub the Add dialog's exec and the Remove
# confirmation so nothing blocks. _confirm holds the answer the next
# QMessageBox.question returns, so a "user says No" case can be exercised too.
_confirm = {"answer": QMessageBox.StandardButton.Yes}
QMessageBox.question = staticmethod(lambda *a, **k: _confirm["answer"])

from mudlab.add_phase_dialog import AddPhaseDialog  # noqa: E402
from mudlab.edit_phases_dialog import EditPhasesDialog  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")
_app = QApplication.instance() or QApplication([])


def _fixture():
    for name in ("308 r1.mud", "Dh2040A 14Jul26 r1.mud"):
        for base in (_FIXTURES, os.path.join(os.path.expanduser("~"), "Downloads")):
            path = os.path.join(base, name)
            if os.path.isfile(path):
                return path
    return None


def _make_add_dialog_return(G):
    """Patch AddPhaseDialog.exec to accept with a chosen G (no real UI)."""
    def _exec(self):
        self.ui.G.setValue(G)
        return QDialog.DialogCode.Accepted
    AddPhaseDialog.exec = _exec


def _select_row(dialog, row):
    dialog.ui.edit_objects_treeview.selectionModel().select(
        dialog.objects_model.index(row, 0),
        QItemSelectionModel.SelectionFlag.ClearAndSelect
        | QItemSelectionModel.SelectionFlag.Rows,
    )


def _in_sync(dialog, project):
    return (
        len(dialog._phases)
        == dialog.objects_model.rowCount()
        == len(project.phases)
    )


def check_button_state(project, results):
    """1. Add/Remove enabled; Import/Export disabled with a tooltip."""
    dialog = EditPhasesDialog(None, project=project)
    results.append(("1 Add enabled", dialog.ui.button_add_object.isEnabled()))
    results.append(("1 Remove enabled", dialog.ui.button_del_object.isEnabled()))
    results.append(("1 Import disabled", not dialog.ui.button_load_object.isEnabled()))
    results.append(("1 Export disabled", not dialog.ui.button_save_object.isEnabled()))
    results.append(("1 Import says why",
                    bool(dialog.ui.button_load_object.toolTip())))
    dialog.deleteLater()


def check_add_dialog_restrictions(results):
    """2. The Add dialog offers only the ported empty-phase path."""
    dialog = AddPhaseDialog(None)
    results.append(("2 empty phase preselected",
                    dialog.ui.rdb_empty_phase.isChecked()))
    results.append(("2 default-catalog option disabled",
                    not dialog.ui.rdb_default_phase.isEnabled()))
    results.append(("2 raw-pattern option disabled",
                    not dialog.ui.rdb_raw_pattern.isEnabled()))
    results.append(("2 R locked to 0", dialog.ui.R.value() == 0
                    and not dialog.ui.R.isEnabled()))
    results.append(("2 phase_type resolves to 'empty'",
                    dialog.phase_type == "empty"))
    dialog.deleteLater()


def check_add(project, results):
    """3. Add builds a real phase and keeps project / snapshot / tree in sync."""
    dialog = EditPhasesDialog(None, project=project)
    n0 = len(project.phases)
    _make_add_dialog_return(4)
    dialog._on_add_phase()

    results.append(("3 project gained a phase", len(project.phases) == n0 + 1))
    new = project.phases[-1]
    results.append(("3 new phase has G blank components",
                    new.G == 4 and len(new.components) == 4))
    results.append(("3 components are named Component 1..G",
                    [c.name for c in new.components]
                    == ["Component %d" % i for i in range(1, 5)]))
    results.append(("3 views in lock-step after add", _in_sync(dialog, project)))
    results.append(("3 new row is selected + bound in the editor",
                    getattr(dialog.phase_widget, "_phase", None) is new))
    dialog.deleteLater()


def check_remove_confirmed(project, results):
    """4. Remove confirms, removes, and keeps the three views in sync."""
    dialog = EditPhasesDialog(None, project=project)
    n0 = len(project.phases)
    target_name = project.phases[1].name
    _select_row(dialog, 1)

    _confirm["answer"] = QMessageBox.StandardButton.Yes
    dialog._on_remove_phase()
    results.append(("4 project lost a phase", len(project.phases) == n0 - 1))
    results.append(("4 the right phase went",
                    target_name not in [p.name for p in project.phases]))
    results.append(("4 views in lock-step after remove", _in_sync(dialog, project)))
    results.append(("4 a neighbour is reselected (editor still bound)",
                    project.phases and dialog.phase_widget._phase in project.phases))
    dialog.deleteLater()


def check_remove_declined(project, results):
    """4b. Answering No to the confirmation changes nothing."""
    dialog = EditPhasesDialog(None, project=project)
    n0 = len(project.phases)
    names = [p.name for p in project.phases]
    _select_row(dialog, 0)
    _confirm["answer"] = QMessageBox.StandardButton.No
    dialog._on_remove_phase()
    results.append(("4b declining leaves the count unchanged",
                    len(project.phases) == n0))
    results.append(("4b declining leaves the phases unchanged",
                    [p.name for p in project.phases] == names))
    results.append(("4b declining keeps the views in sync", _in_sync(dialog, project)))
    dialog.deleteLater()


def check_add_then_remove_roundtrips(project, results):
    """5. Add then Remove of the new phase returns the project to its start."""
    dialog = EditPhasesDialog(None, project=project)
    before = [p.uuid for p in project.phases]
    _make_add_dialog_return(2)
    dialog._on_add_phase()
    _select_row(dialog, len(dialog._phases) - 1)
    _confirm["answer"] = QMessageBox.StandardButton.Yes
    dialog._on_remove_phase()
    results.append(("5 add-then-remove restores the phase set",
                    [p.uuid for p in project.phases] == before))
    results.append(("5 views back in sync", _in_sync(dialog, project)))
    dialog.deleteLater()


def run(path):
    print("=" * 72)
    print("Phase dialogs:", os.path.basename(path))
    print("=" * 72)
    results = []
    # Each check gets its own freshly loaded project (Add/Remove are
    # destructive, and a shared project would let one case taint the next).
    check_button_state(load_mud(path), results)
    check_add_dialog_restrictions(results)
    check_add(load_mud(path), results)
    check_remove_confirmed(load_mud(path), results)
    check_remove_declined(load_mud(path), results)
    check_add_then_remove_roundtrips(load_mud(path), results)
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("%d/%d checks passed" % (passed, len(results)))
    return passed == len(results), len(results)


def main(argv):
    path = argv[1] if len(argv) > 1 else _fixture()
    if not path or not os.path.isfile(path):
        print("No sample project found; skipping (exit 2).")
        return 2
    ok, total = run(path)
    print("=" * 72)
    print("Phase-dialog harness: %d checks: %s"
          % (total, "OK" if ok else "REGRESSION"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
