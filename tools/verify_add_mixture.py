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
