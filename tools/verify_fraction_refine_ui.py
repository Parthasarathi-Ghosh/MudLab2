#!/usr/bin/env python
"""Batch 2 of the per-phase fraction refine flag: the Edit-Mixtures checkbox.

The fraction cell in the mixture matrix (tbl_matrix) carries a checkbox bound to
Mixture.fraction_refine / set_fraction_refine (old app: fractions_mask). Checked
= Optimize refines this phase's fraction; unchecked = held fixed for manual
setting. This drives the real EditMixtureWidget head-less and checks:

  - every phase-row fraction cell is user-checkable and its initial check state
    mirrors the model; scale / bg / phase-name cells are NOT checkable;
  - ticking / un-ticking a cell writes the mask and fires on_changed (recompute);
  - the toggle leaves the fraction VALUE untouched and the mask the right length;
  - editing the fraction text does not disturb the refine flag.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_fraction_refine_ui.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from mudlab.edit_mixture_widget import (
    EditMixtureWidget, _COL_FRACTION, _FIRST_PHASE_ROW, _FIRST_SPEC_COL,
    _ROW_BG, _ROW_SCALE,
)
from mudlab.file_parsers.mud_project import load_mud

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in [os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")] + \
            sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        if not os.path.isfile(path):
            continue
        project = load_mud(path)
        if project.mixtures and project.mixtures[0].m >= 2:
            return path, project
    return None, None


PATH, PROJECT = _fixture()
if PROJECT is None:
    print("No fixture with a >=2-slot mixture; skipping (exit 2).")
    raise SystemExit(2)


def main():
    mix = PROJECT.mixtures[0]
    print("fixture: %s  (%d phase slots)" % (os.path.basename(PATH), mix.m))

    calls = {"n": 0}
    w = EditMixtureWidget()
    w.bind_mixture(mix, phases=PROJECT.phases, specimens=PROJECT.specimens,
                   on_changed=lambda: calls.__setitem__("n", calls["n"] + 1))
    table = w.ui.tbl_matrix

    CHECKABLE = Qt.ItemFlag.ItemIsUserCheckable

    # --- every phase-row fraction cell is checkable + mirrors the model -------
    ok_flag = ok_state = True
    for j in range(mix.m):
        item = table.item(_FIRST_PHASE_ROW + j, _COL_FRACTION)
        ok_flag &= bool(item.flags() & CHECKABLE)
        want = Qt.CheckState.Checked if mix.fraction_refine(j) else Qt.CheckState.Unchecked
        ok_state &= item.checkState() == want
    check("every fraction cell is user-checkable", ok_flag)
    check("initial check state mirrors fraction_refine", ok_state)

    # --- scale / bg / phase-name cells must NOT sprout a checkbox ------------
    non_frac = [table.item(_ROW_SCALE, _FIRST_SPEC_COL),
                table.item(_ROW_BG, _FIRST_SPEC_COL),
                table.item(_FIRST_PHASE_ROW, _FIRST_SPEC_COL)]  # a phase combo cell
    check("scale / bg / phase cells are not checkable",
          all(it is None or not (it.flags() & CHECKABLE) for it in non_frac))

    # --- ticking / un-ticking writes the mask + recomputes -------------------
    item0 = table.item(_FIRST_PHASE_ROW, _COL_FRACTION)
    frac0_before = float(item0.text())
    start_calls = calls["n"]
    want_refine = not mix.fraction_refine(0)
    item0.setCheckState(Qt.CheckState.Checked if want_refine else Qt.CheckState.Unchecked)
    check("toggle writes the model flag", mix.fraction_refine(0) == want_refine)
    check("toggle fired on_changed (recompute)", calls["n"] > start_calls)
    check("toggle left the fraction value untouched",
          abs(float(item0.text()) - frac0_before) < 1e-12)
    check("toggle back restores the flag",
          (item0.setCheckState(Qt.CheckState.Checked if not want_refine
                               else Qt.CheckState.Unchecked)
           or mix.fraction_refine(0) == (not want_refine)))
    check("mask stays one-per-slot after toggling",
          len(mix.raw_properties.get("fractions_mask", [])) == mix.m)

    # --- editing the fraction text leaves the refine flag alone --------------
    mix.set_fraction_refine(1, False)
    w.bind_mixture(mix, phases=PROJECT.phases, specimens=PROJECT.specimens,
                   on_changed=lambda: calls.__setitem__("n", calls["n"] + 1))
    table = w.ui.tbl_matrix
    item1 = table.item(_FIRST_PHASE_ROW + 1, _COL_FRACTION)
    item1.setText("0.1234")
    check("editing fraction text keeps refine=False", not mix.fraction_refine(1))
    check("edited fraction value took effect",
          abs(float(mix.fractions[1]) - 0.1234) < 1e-9)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- fraction-refine checkbox (UI) verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
