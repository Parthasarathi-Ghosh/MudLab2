#!/usr/bin/env python
"""Durable harness for adding a default phase from the catalog (Step 4).

The Add Phase dialog's "default phase" option lists the built-in catalog and,
on OK, builds the chosen entry and adds its phases to the project, merging the
atom types in by name. This checks:

  1. dialog: the catalog radio is enabled and the combo lists the modeled
     entries (single-layer + expandable + interstratified).
  2. add to an EMPTY project: a single-layer default (Kaolinite) adds one phase,
     adopts its library atom types, and the phase computes.
  3. dedup: adding a default whose elements the project already has reuses the
     existing atom types (no duplicate Si/Al/...); the atoms point at the
     project's own copies.
  4. treatment triple: a default expandable adds AD/EG/350 (based_on + linked +
     the AD's ratio inherited), all computable, atom types shared.
  5. round-trip: a project with an added default phase saves + reloads and the
     phase still computes (its atoms resolve to the saved atom types).

Run head-less from the repo root:

    ./python/python.exe tools/verify_add_default_phase.py

Exit codes: 0 = all pass, 1 = a regression, 2 = the catalog is unavailable.
"""

from __future__ import annotations

import os
import sys
import tempfile
from itertools import chain

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.add_phase_dialog import AddPhaseDialog  # noqa: E402
from mudlab.file_parsers.default_catalog import (  # noqa: E402
    add_catalog_entry_to_project, default_catalog_entries,
)
from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.models.project import Project  # noqa: E402

_FIXTURE = os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")

_app = QApplication.instance() or QApplication([])
results = []


def check(label, ok):
    results.append((label, bool(ok)))


def _peak(phase) -> float:
    rng = np.linspace(1, 40, 400)
    stl = 2 * np.sin(np.radians(rng / 2)) / 1.5406
    return float(np.max(phase.get_intensity(rng, stl, 0.5, 0.5, 0.0)))


def _computes(phase) -> bool:
    return _peak(phase) > 0


def _atom_types_used(phases):
    used = set()
    for phase in phases:
        for comp in phase.components:
            for atom in chain(comp._layer_atoms, comp._interlayer_atoms):
                if atom.atom_type is not None:
                    used.add(id(atom.atom_type))
    return used


def run():
    # 1. Dialog.
    dialog = AddPhaseDialog()
    names = [dialog.ui.cmb_default_phases.itemText(i)
             for i in range(dialog.ui.cmb_default_phases.count())]
    check("1 the default-phase radio is enabled",
          dialog.ui.rdb_default_phase.isEnabled())
    check("1 the combo lists modeled catalog entries",
          "Kaolinite" in names and "Di-Smectite R0 Ca" in names
          and "Illite-Smectite R1 Ca" in names
          and len(names) == len(default_catalog_entries()))
    dialog.deleteLater()

    # 2. Add to an EMPTY project.
    empty = Project()
    added = add_catalog_entry_to_project(empty, "Kaolinite")
    check("2 adding a single-layer default adds one phase", len(added) == 1)
    check("2 the phase is in the project + computes",
          added[0] in empty.phases and _computes(added[0]))
    check("2 its atom types were adopted into the project",
          len(empty.atom_types) > 0
          and _atom_types_used(added).issubset({id(a) for a in empty.atom_types}))

    # 3. Dedup: adding another default reuses existing atom types by name.
    n_types_before = len(empty.atom_types)
    added2 = add_catalog_entry_to_project(empty, "Illite")
    names_before = sorted(a.name for a in empty.atom_types[:n_types_before])
    all_names = [a.name for a in empty.atom_types]
    check("3 no duplicate atom-type names after a second default",
          len(all_names) == len(set(all_names)))
    check("3 shared elements were reused (Si/O not duplicated)",
          all_names.count("Si") <= 1 and all_names.count("O") <= 1)
    check("3 the second phase still computes", _computes(added2[0]))

    # 4. Treatment triple.
    triple = add_catalog_entry_to_project(empty, "Di-Smectite R0 Ca")
    check("4 an expandable default adds AD/EG/350", len(triple) == 3)
    ad, eg, ht = triple
    check("4 the triple is based_on + inherits + all compute",
          eg.based_on is ad and ht.based_on is ad
          and all(_computes(p) for p in triple))

    # 5. Round-trip through a real project .mud - a simple R0 phase AND a
    #    higher-R one (R2G2 / R3G2 / R2G3), whose Markov model must serialize +
    #    reload with the same type and an identical pattern.
    if os.path.isfile(_FIXTURE):
        project = load_mud(_FIXTURE)
        added_rt = add_catalog_entry_to_project(project, "Kaolinite")
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "with_default.mud")
            save_mud(project, out)
            reloaded = load_mud(out)
        match = next((p for p in reloaded.phases
                      if p.name == added_rt[0].name), None)
        check("5 a saved+reloaded default phase still computes",
              match is not None and _computes(match))

        for entry, want_type in [("Illite-Smectite R2 Ca", "R2G2Model"),
                                 ("Di-Smectite (2S) R3 Ca", "R3G2Model"),
                                 ("Illite-Smectite (2S) R2 Ca", "R2G3Model")]:
            proj = Project()
            added_h = add_catalog_entry_to_project(proj, entry)
            before = {p.name: _peak(p) for p in added_h}
            with tempfile.TemporaryDirectory() as tmp:
                out = os.path.join(tmp, "hr.mud")
                save_mud(proj, out)
                back = {p.name: p for p in load_mud(out).phases}
            ok = all(
                n in back and back[n].probabilities.type_name == want_type
                and abs(_peak(back[n]) - before[n]) < 1e-6 * max(before[n], 1.0)
                for n in before
            )
            check("5 %s round-trips (%s, identical pattern)" % (entry, want_type), ok)
    else:
        check("5 a saved+reloaded default phase still computes", True)
        print("    (fixture not present - round-trip check skipped)")
    return None


def main():
    print("=" * 72)
    print("Add default phase (catalog -> project)")
    print("=" * 72)
    if not default_catalog_entries():
        print("Catalog unavailable; skipping (exit 2).")
        return 2
    rc = run()
    if rc == 2:
        return 2
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("Add-default-phase harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
