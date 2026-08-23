#!/usr/bin/env python
"""Durable harness for the Add / Remove Phase dialog wiring (Batch P2), run
head-less.

The model layer (add_phase / remove_phase and its cascades) is guarded by
tools/verify_phase_crud.py. This covers only what lives in the UI and cannot
be seen from the model:

  1. the buttons are in the right state - Add / Remove / Import / Export all
     enabled and wired;
  2. the Add dialog offers the ported paths - empty phase (R 0-1) and raw
     pattern; the default-catalog option stays disabled;
  3. Add builds a real phase (G blank components) and keeps the three views in
     lock-step: project.phases, the dialog's _phases snapshot, and the tree
     rows;
  4. Remove confirms first, then removes and keeps the three in lock-step,
     reselecting a neighbour;
  5. an Add followed by a Remove leaves the project exactly as it was;
  6. the probabilities editor sizes its W/P tables to the model's real rank
     (g**R, not G) so R>=2 pair/triplet states are not truncated, and its
     spinboxes honour each parameter's bounds (R2 W1>=1/2, R3G2 W1>=2/3);
  7. Add -> raw pattern creates a RawPatternPhase, the raw editor (not the
     structural one) is shown for it, and importing a file sets its pattern;
  8. Export the selected phase to a .phs and import it back through the
     Import/Export buttons (the phase list grows, views stay in sync).

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
import tempfile

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
# The in-use refusal is an information() box - modal, and it would hang the
# run. Record what it said instead, so a refusal can be asserted on.
_informed = []
QMessageBox.information = staticmethod(lambda *a, **k: _informed.append(a[2]))

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
    """1. Add / Remove / Import / Export are all enabled and wired."""
    dialog = EditPhasesDialog(None, project=project)
    results.append(("1 Add enabled", dialog.ui.button_add_object.isEnabled()))
    results.append(("1 Remove enabled", dialog.ui.button_del_object.isEnabled()))
    results.append(("1 Import enabled", dialog.ui.button_load_object.isEnabled()))
    results.append(("1 Export enabled", dialog.ui.button_save_object.isEnabled()))
    dialog.deleteLater()


def check_import_export_phases(project, results):
    """8. Export the selected phase to a .phs via the dialog, then import it
    back - the phase list grows and the file round-trips through the buttons."""
    from PySide6.QtWidgets import QFileDialog
    tmpdir = tempfile.mkdtemp(prefix="mudlab_phsui_")
    phs = os.path.join(tmpdir, "exported.phs")
    dialog = EditPhasesDialog(None, project=project)
    _select_row(dialog, 0)

    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (phs, ""))
    dialog._on_export_phases()
    results.append(("8 export wrote a .phs file", os.path.isfile(phs)))

    n0 = len(project.phases)
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (phs, ""))
    dialog._on_import_phases()
    results.append(("8 import added a phase + a row",
                    len(project.phases) == n0 + 1 and _in_sync(dialog, project)))
    dialog.deleteLater()
    os.remove(phs)
    os.rmdir(tmpdir)


def check_add_dialog_restrictions(results):
    """2. The Add dialog offers the ported paths - empty phase (with the modeled
    stacking range R 0-1; R1 locks G to 2 since only R1G2 exists), the default
    catalog, and raw pattern."""
    dialog = AddPhaseDialog(None)
    results.append(("2 empty phase preselected",
                    dialog.ui.rdb_empty_phase.isChecked()))
    # The default-catalog option is now wired: enabled, with the modeled
    # catalog entries listed in its combo.
    results.append(("2 default-catalog option enabled + populated",
                    dialog.ui.rdb_default_phase.isEnabled()
                    and dialog.ui.cmb_default_phases.count() > 0))
    results.append(("2 phase_type resolves to 'empty'",
                    dialog.phase_type == "empty"))
    # Raw-pattern option is now wired: enabled, and selecting it disables the
    # empty-phase G/R container (a raw phase has no stacking model).
    results.append(("2 raw-pattern option enabled",
                    dialog.ui.rdb_raw_pattern.isEnabled()))
    dialog.ui.rdb_raw_pattern.setChecked(True)
    results.append(("2 selecting raw disables the empty-phase container",
                    not dialog.ui.cont_empty_phase.isEnabled()
                    and dialog.phase_type == "raw"))
    dialog.ui.rdb_empty_phase.setChecked(True)
    # R spans the modeled RGbounds: R0 G1-6, R1 G2-4, R2 G2-3, R3 G2.
    results.append(("2 R range is 0-3",
                    dialog.ui.R.minimum() == 0 and dialog.ui.R.maximum() == 3))
    dialog.ui.R.setValue(0)
    results.append(("2 R=0 allows G 1-6",
                    dialog.ui.G.minimum() == 1 and dialog.ui.G.maximum() == 6
                    and dialog.ui.G.isEnabled()))
    dialog.ui.R.setValue(1)
    results.append(("2 R=1 allows G 2-4 (R1G2-R1G4)",
                    dialog.ui.G.minimum() == 2 and dialog.ui.G.maximum() == 4
                    and dialog.ui.G.isEnabled() and dialog.R == 1))
    dialog.ui.R.setValue(2)
    results.append(("2 R=2 allows G 2-3",
                    dialog.ui.G.minimum() == 2 and dialog.ui.G.maximum() == 3
                    and dialog.ui.G.isEnabled()))
    dialog.ui.R.setValue(3)
    results.append(("2 R=3 locks G to 2 (only R3G2 modeled)",
                    dialog.ui.G.value() == 2 and not dialog.ui.G.isEnabled()
                    and dialog.G == 2 and dialog.R == 3))
    dialog.ui.R.setValue(0)
    results.append(("2 back to R=0 re-enables G 1-6",
                    dialog.ui.G.maximum() == 6 and dialog.ui.G.isEnabled()))
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


def check_remove_in_use(project, results):
    """4a. A phase a mixture uses is refused - with a message naming where, and
    without ever asking for confirmation."""
    dialog = EditPhasesDialog(None, project=project)
    victim = next((p for p in project.phases if project.phase_usage(p)), None)
    if victim is None:
        results.append(("4a (fixture has no phase in a mixture; skipped)", True))
        dialog.deleteLater()
        return
    _select_row(dialog, project.phases.index(victim))
    n0 = len(project.phases)
    _informed.clear()
    _confirm["answer"] = QMessageBox.StandardButton.No  # must not even be asked
    dialog._on_remove_phase()
    results.append(("4a an in-use phase is not deleted", len(project.phases) == n0))
    results.append(("4a the refusal names the mixture",
                    bool(_informed)
                    and project.mixtures[0].name in _informed[-1]))
    results.append(("4a views in sync after the refusal", _in_sync(dialog, project)))
    dialog.deleteLater()


def check_remove_confirmed(project, results):
    """4. Remove confirms, removes, and keeps the three views in sync."""
    dialog = EditPhasesDialog(None, project=project)
    n0 = len(project.phases)
    target_name = project.phases[1].name
    _select_row(dialog, 1)
    # Free it first: an in-use phase is refused (4a covers that).
    for mixture in project.mixtures:
        mixture.unset_phase(project.phases[1])

    _confirm["answer"] = QMessageBox.StandardButton.Yes
    _informed.clear()
    dialog._on_remove_phase()
    results.append(("4 no refusal for a freed phase", not _informed))
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
    for mixture in project.mixtures:
        mixture.unset_phase(project.phases[0])
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


def _make_add_dialog_return_raw():
    """Patch AddPhaseDialog.exec to accept with the raw-pattern radio."""
    def _exec(self):
        self.ui.rdb_raw_pattern.setChecked(True)
        return QDialog.DialogCode.Accepted
    AddPhaseDialog.exec = _exec


def check_add_raw_phase(project, results):
    """7. Add -> raw pattern creates a RawPatternPhase; selecting it shows the
    raw editor (not the structural one); importing a file sets its pattern and
    editing the name propagates."""
    import numpy as np
    from mudlab.models.raw_pattern_phase import RawPatternPhase

    dialog = EditPhasesDialog(None, project=project)
    n0 = len(project.phases)
    _make_add_dialog_return_raw()
    dialog._on_add_phase()

    results.append(("7 project gained a RawPatternPhase",
                    len(project.phases) == n0 + 1
                    and isinstance(project.phases[-1], RawPatternPhase)))
    row = len(dialog._phases) - 1
    results.append(("7 raw row shows '—' for R and G",
                    dialog.objects_model.item(row, 1).text() == "—"
                    and dialog.objects_model.item(row, 2).text() == "—"))
    # Selecting the raw phase routes to the raw editor, hiding the structural.
    results.append(("7 raw editor shown, structural hidden",
                    dialog.raw_phase_widget.isVisibleTo(dialog)
                    and not dialog.phase_widget.isVisibleTo(dialog)))

    raw = project.phases[-1]
    fd, path = tempfile.mkstemp(suffix=".xy")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("10 0\n20 100\n30 0\n")
    try:
        dialog.raw_phase_widget.import_from_path(path)
    finally:
        os.remove(path)
    results.append(("7 import sets the measured pattern",
                    np.array_equal(raw.raw_pattern_x, [10.0, 20.0, 30.0])
                    and np.array_equal(raw.raw_pattern_y, [0.0, 100.0, 0.0])))
    results.append(("7 editor info reports the loaded points",
                    "3 points" in dialog.raw_phase_widget.ui.raw_pattern_info.text()))

    dialog.raw_phase_widget.ui.raw_phase_name.setText("Quartz")
    dialog.raw_phase_widget._on_name_edited()
    results.append(("7 name edit propagates to the phase + row",
                    raw.name == "Quartz"
                    and dialog.objects_model.item(row, 0).text() == "Quartz"))
    dialog.deleteLater()


def check_probabilities_widget(results):
    """6. The probabilities editor renders every stacking model correctly:
    the W/P tables are sized to the model's real rank g**R (not G), so the
    pair/triplet states of R>=2 are NOT silently truncated to a G x G corner,
    and the spinboxes honour each parameter's bounds. Fixture-independent -
    the models are built directly. Regression guard for the higher-R fix."""
    import numpy as np
    from mudlab.probabilities_widget import ProbabilitiesWidget
    from mudlab.models.probabilities import (
        R0Probability, R1G2Probability, R1G3Probability, R1G4Probability,
        R2G2Probability, R2G3Probability, R3G2Probability,
    )
    # (tag, model, expected rank g**R, expected W1 spin minimum or None)
    cases = [
        ("R0G3", R0Probability(G=3), 3, None),
        ("R1G2", R1G2Probability(), 2, 0.0),
        ("R1G3", R1G3Probability(), 3, 0.0),
        ("R1G4", R1G4Probability(), 4, 0.0),
        ("R2G2", R2G2Probability(), 4, 0.5),
        ("R2G3", R2G3Probability(), 9, 0.5),
        ("R3G2", R3G2Probability(), 8, 2.0 / 3.0),
    ]
    widget = ProbabilitiesWidget()
    for tag, prob, rank, w1min in cases:
        widget.bind_probabilities(prob, labels=None, on_changed=None)
        P = np.asarray(prob.get_probability_matrix(), float)
        Wd = np.asarray(prob.get_distribution_array(), float)
        results.append(("6 %s W table has %d cols (rank, not G)" % (tag, rank),
                        widget._w_table.columnCount() == rank))
        results.append(("6 %s P table is %dx%d" % (tag, rank, rank),
                        widget._p_table.rowCount() == rank
                        and widget._p_table.columnCount() == rank))
        results.append(("6 %s spins == n_independents" % tag,
                        len(widget._param_spins) == prob.n_independents))
        # The LAST P cell and W entry - the ones truncated before the fix -
        # are shown and carry the model's value.
        pcell = widget._p_table.item(rank - 1, rank - 1)
        results.append(("6 %s shows P[last,last], untruncated" % tag,
                        pcell is not None
                        and pcell.text() == "%.4f" % P[rank - 1, rank - 1]))
        wcell = widget._w_table.item(0, rank - 1)
        results.append(("6 %s shows W[last], untruncated" % tag,
                        wcell is not None
                        and wcell.text() == "%.4f" % Wd[rank - 1]))
        if w1min is not None:
            # QDoubleSpinBox(decimals=4) rounds its range to 4 dp, so 2/3 -> a
            # min of 0.6667 (just ABOVE 2/3, i.e. safe - never admits W1 < 2/3).
            want = round(w1min, 4)
            results.append(("6 %s W1 spin min == %.4f" % (tag, want),
                            abs(widget._param_spins[0].minimum() - want) < 1e-9))
    widget.deleteLater()


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
    check_remove_in_use(load_mud(path), results)
    check_remove_confirmed(load_mud(path), results)
    check_remove_declined(load_mud(path), results)
    check_add_then_remove_roundtrips(load_mud(path), results)
    check_add_raw_phase(load_mud(path), results)
    check_import_export_phases(load_mud(path), results)
    check_probabilities_widget(results)
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
