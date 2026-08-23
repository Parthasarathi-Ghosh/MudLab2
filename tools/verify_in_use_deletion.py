#!/usr/bin/env python
"""In-use deletion is refused, in the model AND through both UI paths.

Deleting a phase or a specimen that a mixture still holds used to succeed and
cascade: the mixture's cells were emptied behind the user's back, and the model
they had built quietly changed shape. It now refuses, and says where the object
is used so the user can go and free it.

What this covers:

  1. model: Project.phase_usage / specimen_usage report every mixture cell (or
     row) holding the object, and nothing when it is free;
  2. model: remove_phase / remove_specimen return False and change NOTHING while
     the object is in use - not the project list, not either grid
     representation, not the mixture's residual;
  3. model: freed, the same call returns True and removes it;
  4. message: in_use_message names the mixture, counts the places, and tells the
     user where to go;
  5. UI (Edit Phases): _on_remove_phase shows the refusal, never asks for
     confirmation, and leaves the list row in place;
  6. UI (main window): _remove_specimens refuses BEFORE the confirm prompt, and
     a mixed selection is refused wholesale - nothing is half-deleted;
  7. inheritance is NOT membership: a phase that is only a based_on parent or a
     link template is still deletable (its dependants are snapshotted, which
     verify_remove_phase_snapshot covers).

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_in_use_deletion.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no usable sample project.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

# Both refusals are modal boxes: record them instead of blocking the run.
_informed: list[str] = []
_asked: list[str] = []
QMessageBox.information = staticmethod(lambda *a, **k: _informed.append(a[2]))
QMessageBox.question = staticmethod(
    lambda *a, **k: (_asked.append(a[2]), QMessageBox.StandardButton.Yes)[1]
)

from mudlab.edit_phases_dialog import EditPhasesDialog  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.main_window import MainWindow  # noqa: E402
from mudlab.models.mixture import Mixture  # noqa: E402
from mudlab.qt_utils import in_use_message  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")
_app = QApplication.instance() or QApplication([])

results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    """The first sample project with a mixture that actually holds a phase and
    a specimen - the only kind this feature has anything to say about."""
    if not os.path.isdir(_FIXTURES):
        return None
    for name in sorted(os.listdir(_FIXTURES)):
        if not name.endswith(".mud"):
            continue
        path = os.path.join(_FIXTURES, name)
        project = load_mud(path)
        for mixture in project.mixtures:
            has_phase = any(c is not None for row in mixture.phase_matrix
                            for c in row)
            has_spec = any(s is not None for s in mixture.specimens)
            if has_phase and has_spec:
                return path
    return None


PATH = _fixture()
if PATH is None:
    print("No sample project with a populated mixture; skipping (exit 2).")
    raise SystemExit(2)


def _used_phase(project):
    for mixture in project.mixtures:
        for row in mixture.phase_matrix:
            for cell in row:
                if cell is not None:
                    return cell, mixture
    return None, None


def _used_specimen(project):
    for mixture in project.mixtures:
        for spec in mixture.specimens:
            if spec is not None:
                return spec, mixture
    return None, None


# ----------------------------------------------------------------- 1 + 2 + 3
def check_model_phase():
    project = load_mud(PATH)
    phase, mixture = _used_phase(project)
    usage = project.phase_usage(phase)
    cells = [(i, j) for i, row in enumerate(mixture.phase_matrix)
             for j, c in enumerate(row) if c is phase]
    check("usage/phase: reports the mixture holding it",
          any(m is mixture for m, _c in usage))
    check("usage/phase: reports every cell, and only those",
          any(m is mixture and c == cells for m, c in usage))

    before_phases = list(project.phases)
    before_grid = [list(row) for row in mixture.phase_matrix]
    before_uuids = [list(row) for row in mixture.phase_uuids]
    before_residual = mixture.current_residual()
    removed = project.remove_phase(phase)
    check("refuse/phase: remove_phase returns False", removed is False)
    check("refuse/phase: the project still has it",
          list(project.phases) == before_phases)
    check("refuse/phase: the resolved grid is untouched",
          [list(r) for r in mixture.phase_matrix] == before_grid)
    check("refuse/phase: the uuid grid is untouched",
          [list(r) for r in mixture.phase_uuids] == before_uuids)
    check("refuse/phase: the residual did not move",
          mixture.current_residual() == before_residual)

    for other in project.mixtures:
        other.unset_phase(phase)
    check("free/phase: usage is empty once freed", project.phase_usage(phase) == [])
    check("free/phase: remove_phase returns True",
          project.remove_phase(phase) is True)
    check("free/phase: it is gone", phase not in project.phases)


def check_model_specimen():
    project = load_mud(PATH)
    spec, mixture = _used_specimen(project)
    rows = [i for i, s in enumerate(mixture.specimens) if s is spec]
    usage = project.specimen_usage(spec)
    check("usage/specimen: reports the mixture holding it",
          any(m is mixture for m, _r in usage))
    check("usage/specimen: reports every row, and only those",
          any(m is mixture and r == rows for m, r in usage))

    before = list(project.specimens)
    before_rows = list(mixture.specimens)
    removed = project.remove_specimen(spec)
    check("refuse/specimen: remove_specimen returns False", removed is False)
    check("refuse/specimen: the project still has it",
          list(project.specimens) == before)
    check("refuse/specimen: the mixture row is untouched",
          list(mixture.specimens) == before_rows)
    check("refuse/specimen: the uuid row is untouched",
          mixture.specimen_uuids[rows[0]] == spec.uuid)

    for other in project.mixtures:
        other.unset_specimen(spec)
    check("free/specimen: usage is empty once freed",
          project.specimen_usage(spec) == [])
    check("free/specimen: remove_specimen returns True",
          project.remove_specimen(spec) is True)
    check("free/specimen: it is gone", spec not in project.specimens)


def check_absent_object():
    """A phase that was never in the project is not "in use" - it is simply not
    there, and the answer must be False, not a refusal."""
    project = load_mud(PATH)
    stray = load_mud(PATH).phases[0]     # a phase of a DIFFERENT project
    check("absent/phase: removing a phase not in the project returns False",
          project.remove_phase(stray) is False)
    stray_spec = load_mud(PATH).specimens[0]
    check("absent/specimen: removing a specimen not in the project returns False",
          project.remove_specimen(stray_spec) is False)


# ----------------------------------------------------------------------- 4
def check_message():
    project = load_mud(PATH)
    phase, mixture = _used_phase(project)
    usage = project.phase_usage(phase)
    msg = in_use_message(phase.name, "phase", usage)
    n = sum(len(c) for _m, c in usage)
    check("message: names the object", (phase.name or "") in msg)
    check("message: names the mixture", (mixture.name or "") in msg)
    check("message: counts the places", str(n) in msg)
    check("message: singular/plural agree",
          ("1 cell)" in msg) if n == 1 else ("%d cells)" % n in msg))
    check("message: says where to go", "Edit Mixtures" in msg)
    # A phase occupies CELLS and is freed via the phase slot; a specimen
    # occupies ROWS and is freed from the row header. Naming the wrong unit -
    # or a menu item that does not exist - sends the user to the wrong place.
    check("message: the phase wording is about cells/slots",
          "cell" in msg and "phase slot" in msg and "row" not in msg)

    spec, smix = _used_specimen(project)
    smsg = in_use_message(spec.name, "specimen", project.specimen_usage(spec))
    check("message: the specimen wording is about rows",
          "row" in smsg and "cell" not in smsg and "phase slot" not in smsg)
    check("message: the specimen wording names a REAL menu item",
          '"Remove specimen"' in smsg and "row header" in smsg)

    # Grammar: a multi-object, multi-mixture refusal must not read
    # "A, B is still used by ... remove it ... from the mixture".
    many = in_use_message("A, B", "specimen",
                          [(smix, [0, 1]), (smix, [0])], subjects=2)
    check("message: plural subjects read 'are ... them'",
          "are still used by" in many and "Remove them" in many
          and "delete them here" in many)
    check("message: several mixtures read 'the mixtures'",
          "from the mixtures first" in many)
    check("message: a single subject still reads 'is ... it'",
          "is still used by" in smsg and "Remove it" in smsg
          and "from the mixture first" in smsg)
    one_row = in_use_message("A", "specimen", [(smix, [0])])
    check("message: one row is not pluralised",
          "(1 row)" in one_row and "rows)" not in one_row)
    check("message: an unnamed object still reads sensibly",
          in_use_message("", "phase", usage).startswith("This phase"))


# ----------------------------------------------------------------------- 5
def check_phase_dialog():
    project = load_mud(PATH)
    dialog = EditPhasesDialog(None, project=project)
    phase, mixture = _used_phase(project)
    row = dialog._phases.index(phase)
    dialog.ui.edit_objects_treeview.setCurrentIndex(
        dialog.objects_model.index(row, 0))
    _app.processEvents()

    n_rows = dialog.objects_model.rowCount()
    _informed.clear()
    _asked.clear()
    dialog._on_remove_phase()
    _app.processEvents()
    check("ui/phase: the phase survives", phase in project.phases)
    check("ui/phase: the list row survives",
          dialog.objects_model.rowCount() == n_rows)
    check("ui/phase: a refusal was shown", len(_informed) == 1)
    check("ui/phase: it names the mixture",
          bool(_informed) and (mixture.name or "") in _informed[-1])
    check("ui/phase: the user was NEVER asked to confirm", not _asked)

    # Freed, the same click deletes - with the confirmation, and no refusal.
    for other in project.mixtures:
        other.unset_phase(phase)
    _informed.clear()
    _asked.clear()
    dialog._on_remove_phase()
    _app.processEvents()
    check("ui/phase: a freed phase deletes", phase not in project.phases)
    check("ui/phase: ...after confirming", len(_asked) == 1)
    check("ui/phase: ...with no refusal", not _informed)
    check("ui/phase: the list row goes with it",
          dialog.objects_model.rowCount() == n_rows - 1)
    dialog.deleteLater()


# ----------------------------------------------------------------------- 6
def check_main_window():
    window = MainWindow()
    window._set_project(load_mud(PATH))
    _app.processEvents()
    project = window.project
    spec, mixture = _used_specimen(project)
    n = len(project.specimens)

    _informed.clear()
    _asked.clear()
    window._remove_specimens([spec])
    _app.processEvents()
    check("ui/specimen: the specimen survives", len(project.specimens) == n)
    check("ui/specimen: a refusal was shown", len(_informed) == 1)
    check("ui/specimen: it names the mixture",
          bool(_informed) and (mixture.name or "") in _informed[-1])
    check("ui/specimen: refused BEFORE the confirm prompt", not _asked)

    free = [s for s in project.specimens
            if s is not None and not project.specimen_usage(s)]
    if free:
        # A mixed selection is refused whole: half-deleting a multi-select is
        # worse than doing nothing.
        _informed.clear()
        _asked.clear()
        window._remove_specimens([spec, free[0]])
        _app.processEvents()
        check("ui/specimen: a mixed selection removes NOTHING",
              len(project.specimens) == n)
        check("ui/specimen: ...and is refused, not confirmed",
              len(_informed) == 1 and not _asked)
    else:
        check("ui/specimen: (fixture has no free specimen for the mixed case)",
              True)

    if free:
        _informed.clear()
        _asked.clear()
        window._remove_specimens([free[0]])
        _app.processEvents()
        check("ui/specimen: a free specimen deletes",
              len(project.specimens) == n - 1)
        check("ui/specimen: ...after confirming, with no refusal",
              len(_asked) == 1 and not _informed)
    else:
        check("ui/specimen: (fixture has no free specimen; skipped)", True)
    # Two blocked specimens in DIFFERENT mixtures must BOTH be listed - the
    # refusal used to show only the first one's usage, sending the user to the
    # wrong mixture for the rest. No sample project ships with two mixtures, so
    # build the second one here rather than skip the case.
    survivors = [s for s in project.specimens if s is not None
                 and project.specimen_usage(s)]
    if len(survivors) >= 2 and project.mixtures:
        first = project.mixtures[0]
        s1, s2 = survivors[0], survivors[1]
        second = Mixture(name="Harness Second Mixture")
        second.add_specimen_slot(s2)
        second.add_phase_slot()
        project.add_mixture(second)
        _informed.clear()
        _asked.clear()
        window._remove_specimens([s1, s2])
        _app.processEvents()
        check("ui/specimen: a refusal spanning two mixtures names BOTH",
              bool(_informed)
              and (first.name or "") in _informed[-1]
              and "Harness Second Mixture" in _informed[-1])
        check("ui/specimen: ...and still removes nothing",
              s1 in project.specimens and s2 in project.specimens)
    else:
        check("ui/specimen: (not enough in-use specimens for the 2-mixture case)",
              True)
    window.close()


# ----------------------------------------------------------------------- 7
def check_inheritance_is_not_use():
    """Being a based_on parent or a link template is NOT "in use": that
    relationship is severed safely (snapshot-on-detach), and the delete
    confirmation already names the dependants."""
    project = load_mud(PATH)
    base = next((p for p in project.phases
                 if any(o.based_on is p for o in project.phases)), None)
    if base is None:
        check("inheritance: (no based_on relationship in this fixture)", True)
        return
    for mixture in project.mixtures:
        mixture.unset_phase(base)
    check("inheritance: a parent phase with no mixture cell is NOT in use",
          project.phase_usage(base) == [])
    check("inheritance: ...so it deletes", project.remove_phase(base) is True)


def main():
    print("=" * 72)
    print("In-use deletion:", os.path.basename(PATH))
    print("=" * 72)
    check_model_phase()
    check_model_specimen()
    check_absent_object()
    check_message()
    check_phase_dialog()
    check_main_window()
    check_inheritance_is_not_use()

    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += ok
    print("-" * 72)
    print("In-use deletion harness: %d/%d checks: %s"
          % (passed, len(results),
             "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
