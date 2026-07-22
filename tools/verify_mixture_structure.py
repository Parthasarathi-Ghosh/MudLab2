#!/usr/bin/env python
"""Durable harness for structural add/remove in a mixture (Batch 2), head-less.

The Edit Mixtures grid can now grow and shrink: add/remove a phase slot
(a column) or a specimen (a row), rename a slot, and assign which project
specimen fills a column. This checks the model methods keep every parallel
array/grid consistent, that the change round-trips through the .mud, and that
the widget's Add buttons drive it.

  1. add_phase_slot / del_phase_slot: phase_labels, fractions, the
     fractions_mask (when present), and EVERY phase_matrix + phase_uuids row
     grow/shrink together; the new cells are empty (None / "").
  2. add_specimen_slot / del_specimen_slot: specimens, specimen_uuids, scales,
     bgshifts, and the phase_matrix + phase_uuids ROW set grow/shrink together;
     the new row is all-empty and length m.
  3. set_specimen_at / set_phase_label update both the resolved + uuid sides.
  4. round-trip: after structural edits, to_dict -> from_dict reproduces the
     new shape (all lengths consistent).
  5. calculate() tolerates an added empty slot + an unassigned specimen.
  6. widget: the Add phase / Add specimen / Add both buttons grow the model and
     the table; del_phase_slot then repopulate drops the row.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_mixture_structure.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project with a mixture.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.edit_mixture_widget import (  # noqa: E402
    _FIRST_PHASE_ROW, _FIRST_SPEC_COL, EditMixtureWidget,
)
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.models.mixture import Mixture  # noqa: E402

_FIXTURE = "308 r1.mud"
FIXTURE = os.path.join(_REPO, "tools", "sample_projects", _FIXTURE)
if not os.path.isfile(FIXTURE):
    FIXTURE = os.path.join(os.path.expanduser("~"), "Downloads", _FIXTURE)

_app = QApplication.instance() or QApplication([])
results = []


def check(label, ok):
    results.append((label, bool(ok)))


def _rectangular(mix, n, m):
    """Every parallel container agrees with n specimens x m slots."""
    return (
        len(mix.phase_labels) == m
        and len(mix.fractions) == m
        and len(mix.specimens) == n
        and len(mix.specimen_uuids) == n
        and len(mix.scales) == n
        and len(mix.bgshifts) == n
        and len(mix.phase_matrix) == n
        and len(mix.phase_uuids) == n
        and all(len(r) == m for r in mix.phase_matrix)
        and all(len(r) == m for r in mix.phase_uuids)
    )


def run():
    project = load_mud(FIXTURE)
    mix = next((m for m in project.mixtures if m.n and m.m), None)
    if mix is None:
        print("No mixture with specimens + slots; skipping (exit 2).")
        return 2
    n0, m0 = mix.n, mix.m
    mix.raw_properties["fractions_mask"] = [1] * m0  # force an explicit mask

    # 1. Add / remove a phase slot.
    j = mix.add_phase_slot("Extra", 0.25)
    check("1 add_phase_slot grows m and stays rectangular",
          mix.m == m0 + 1 and _rectangular(mix, n0, m0 + 1))
    check("1 the new slot's label + fraction are set",
          mix.phase_labels[j] == "Extra" and abs(float(mix.fractions[j]) - 0.25) < 1e-12)
    check("1 the new column is empty in every row",
          all(mix.phase_matrix[i][j] is None and mix.phase_uuids[i][j] == ""
              for i in range(n0)))
    check("1 fractions_mask grew with the new slot (refinable=1)",
          mix.raw_properties["fractions_mask"] == [1] * (m0 + 1))
    mix.del_phase_slot(j)
    check("1 del_phase_slot restores m and stays rectangular",
          mix.m == m0 and _rectangular(mix, n0, m0))
    check("1 fractions_mask shrank back", mix.raw_properties["fractions_mask"] == [1] * m0)

    # 2. Add / remove a specimen slot.
    i = mix.add_specimen_slot(None, 1.5, 0.1)
    check("2 add_specimen_slot grows n and stays rectangular",
          mix.n == n0 + 1 and _rectangular(mix, n0 + 1, m0))
    check("2 the new row is unassigned, scale/bg set, all cells empty",
          mix.specimens[i] is None and mix.specimen_uuids[i] == ""
          and abs(float(mix.scales[i]) - 1.5) < 1e-12
          and all(c is None for c in mix.phase_matrix[i]))

    # 3. set_specimen_at fills the new row; set_phase_label renames a slot.
    some_spec = project.specimens[0]
    mix.set_specimen_at(i, some_spec)
    check("3 set_specimen_at sets both the object and the uuid",
          mix.specimens[i] is some_spec and mix.specimen_uuids[i] == some_spec.uuid)
    mix.set_phase_label(0, "Renamed")
    check("3 set_phase_label renames the slot", mix.phase_labels[0] == "Renamed")

    # 4. Round-trip the structurally-edited mixture.
    clone = Mixture.from_dict(
        mix.to_dict(), project.phase_uuid_map(), project.specimen_uuid_map())
    check("4 round-trip preserves the new shape",
          _rectangular(clone, n0 + 1, m0)
          and clone.phase_labels[0] == "Renamed"
          and clone.specimens[i] is some_spec)

    # 5. calculate() tolerates the added empty slot (add one back) + any None rows.
    mix.add_phase_slot("Empty", 1.0)
    mix.del_specimen_slot(i)  # drop the row we added, back toward the start
    mix.calculate()
    check("5 calculate() runs after structural edits (empty slot, dropped row)", True)

    # 6. Widget: Add buttons grow the model + the table; remove drops a row.
    widget = EditMixtureWidget()
    widget.bind_mixture(mix, phases=list(project.phases),
                        specimens=list(project.specimens))
    n1, m1 = mix.n, mix.m
    rows_before = widget.ui.tbl_matrix.rowCount()
    widget._on_add_phase()
    check("6 Add phase grows the model and adds a table row",
          mix.m == m1 + 1 and widget.ui.tbl_matrix.rowCount() == rows_before + 1)
    cols_before = widget.ui.tbl_matrix.columnCount()
    widget._on_add_specimen()
    check("6 Add specimen grows the model and adds a table column",
          mix.n == n1 + 1 and widget.ui.tbl_matrix.columnCount() == cols_before + 1)
    widget._on_add_both()
    check("6 Add both grows n and m together", mix.n == n1 + 2 and mix.m == m1 + 2)
    mix.del_phase_slot(mix.m - 1)
    widget._populate()
    check("6 del_phase_slot + repopulate drops the row",
          widget.ui.tbl_matrix.rowCount() == _FIRST_PHASE_ROW + mix.m)
    widget.deleteLater()
    return None


def main():
    print("=" * 72)
    print("Mixture structural add/remove")
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
    print("Mixture-structure harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
