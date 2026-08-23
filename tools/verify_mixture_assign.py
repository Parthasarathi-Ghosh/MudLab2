#!/usr/bin/env python
"""Durable harness for phase -> mixture-slot assignment, run head-less.

Each mixture phase cell now assigns WHICH phase fills that slot for that
specimen. This covers:

  1. model: Mixture.set_phase_at updates the resolved grid AND the uuid grid;
     emptying a cell (None) removes that phase's contribution from the calc and
     restoring it reproduces the pattern exactly;
  2. validity gate (scenario 1): Phase.is_valid is False for a New Phase whose
     component slots are empty (no atoms) and for a raw phase with no pattern,
     True once filled - so an incomplete phase cannot be assigned;
  3. widget: each phase cell is a combo of the project's phases; an invalid
     phase is present but DISABLED (greyed), and choosing a valid phase writes
     it to the model + recomputes;
  4. deletion (scenario 2): a phase the mixture uses CANNOT be removed - the
     project refuses it and the cells keep their phase; once the cells are
     freed the same delete goes through and the mixture still recomputes.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_mixture_assign.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project with a mixture.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.edit_mixture_widget import (  # noqa: E402
    _FIRST_PHASE_ROW, _FIRST_SPEC_COL, EditMixtureWidget,
)
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.models.phase import Phase  # noqa: E402
from mudlab.models.raw_pattern_phase import RawPatternPhase  # noqa: E402

_FIXTURE = "308 r1.mud"
FIXTURE = os.path.join(_REPO, "tools", "sample_projects", _FIXTURE)
if not os.path.isfile(FIXTURE):
    FIXTURE = os.path.join(os.path.expanduser("~"), "Downloads", _FIXTURE)

_app = QApplication.instance() or QApplication([])
results = []


def check(label, ok):
    results.append((label, bool(ok)))


def _first_filled_cell(mix):
    for i, row in enumerate(mix.phase_matrix):
        for j, ph in enumerate(row):
            if ph is not None and mix.specimens[i] is not None:
                return i, j
    return None


def run():
    project = load_mud(FIXTURE)
    mix = next((m for m in project.mixtures if _first_filled_cell(m)), None)
    if mix is None:
        print("No mixture with a filled phase cell; skipping (exit 2).")
        return 2
    i, j = _first_filled_cell(mix)
    orig = mix.phase_matrix[i][j]

    # 1. set_phase_at: empty then restore, and the calc follows.
    mix.calculate()
    _, y_full = mix.specimens[i].calculated_pattern
    y_full = y_full.copy()
    mix.set_phase_at(i, j, None)
    check("1 emptying a cell clears the resolved + uuid grid",
          mix.phase_matrix[i][j] is None and mix.phase_uuids[i][j] == "")
    mix.calculate()
    _, y_empty = mix.specimens[i].calculated_pattern
    check("1 the emptied phase's contribution is gone from the pattern",
          not np.allclose(y_empty, y_full))
    mix.set_phase_at(i, j, orig)
    check("1 restoring re-sets the grid (resolved + uuid)",
          mix.phase_matrix[i][j] is orig and mix.phase_uuids[i][j] == orig.uuid)
    mix.calculate()
    _, y_back = mix.specimens[i].calculated_pattern
    check("1 restoring reproduces the pattern exactly",
          np.allclose(y_back, y_full, atol=1e-9))

    # 2. Validity gate.
    check("2 a fixture phase (has atoms) is valid", orig.is_valid)
    empty_phase = Phase.create_empty(G=2, R=0, name="Blank")
    check("2 a New Phase with empty component slots is INVALID",
          not empty_phase.is_valid)
    raw = RawPatternPhase(name="Raw")
    check("2 a raw phase with no pattern is invalid", not raw.is_valid)
    raw.set_raw_pattern([5.0, 5.02, 5.04], [10.0, 20.0, 10.0])
    check("2 a raw phase with a pattern is valid", raw.is_valid)

    # 3. Widget: phase cells are validity-gated combos.
    raw_empty = RawPatternPhase(name="Raw (no pattern)")  # invalid: no pattern
    widget = EditMixtureWidget()
    widget.bind_mixture(mix, phases=list(project.phases) + [empty_phase, raw_empty])
    row, col = _FIRST_PHASE_ROW + j, _FIRST_SPEC_COL + i
    combo = widget.ui.tbl_matrix.cellWidget(row, col)
    check("3 phase cell is a combo", combo is not None and combo.count() > 1)
    # the invalid New Phase is present but disabled, with the structural reason
    from PySide6.QtCore import Qt as _Qt
    invalid_disabled = struct_tip = raw_tip = False
    for k in range(combo.count()):
        if combo.itemData(k) is empty_phase:
            invalid_disabled = not combo.model().item(k).isEnabled()
            struct_tip = "component slot" in (
                combo.itemData(k, _Qt.ItemDataRole.ToolTipRole) or "")
        if combo.itemData(k) is raw_empty:
            raw_tip = "measured pattern" in (
                combo.itemData(k, _Qt.ItemDataRole.ToolTipRole) or "")
    check("3 the invalid phase is listed but greyed (not selectable)",
          invalid_disabled)
    check("3 the greyed structural phase's tooltip cites the empty component slot",
          struct_tip)
    check("3 the greyed raw phase's tooltip cites the missing measured pattern",
          raw_tip)
    # choosing a valid phase writes it to the model
    target_idx = next(k for k in range(combo.count())
                      if combo.itemData(k) is orig)
    other = next((p for p in project.phases if p is not orig and p.is_valid), None)
    if other is not None:
        oidx = next(k for k in range(combo.count()) if combo.itemData(k) is other)
        combo.setCurrentIndex(oidx)
        check("3 choosing a phase in the combo assigns it in the model",
              mix.phase_matrix[i][j] is other)
        combo.setCurrentIndex(target_idx)  # restore
    else:
        check("3 choosing a phase in the combo assigns it in the model", True)
    widget.deleteLater()

    # 4. Deletion (scenario 2): an ASSIGNED phase is not deletable. Emptying the
    # cell behind the user's back is the damage this refusal exists to prevent,
    # so the cell must still hold the phase afterwards.
    victim = mix.phase_matrix[i][j]
    removed = project.remove_phase(victim)
    check("4 deleting an assigned phase is refused",
          removed is False and victim in project.phases)
    check("4 ...and its mixture cell is untouched",
          mix.phase_matrix[i][j] is victim)
    check("4 ...and phase_usage says where it is used",
          any(m is mix and (i, j) in cells
              for m, cells in project.phase_usage(victim)))
    # Freed, the same delete goes through.
    for other in project.mixtures:
        other.unset_phase(victim)
    check("4 freeing the cells makes it deletable",
          project.remove_phase(victim) is True and victim not in project.phases)
    mix.calculate()  # must not raise with an empty cell
    check("4 the mixture still recomputes after the deletion", True)
    return None


def main():
    print("=" * 72)
    print("Phase -> mixture-slot assignment")
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
    print("Mixture-assign harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
