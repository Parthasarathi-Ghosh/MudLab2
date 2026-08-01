#!/usr/bin/env python
"""Batch 5 of snapshot-on-detach: the explicit-detach keep/revert choice.

When the user detaches a phase from its based_on reference (or a component from
its linked template) in the editors, they are offered: keep the current values
(snapshot) or revert to own. The modal itself is not head-less-testable, so this
covers the gating + the message:

  - Phase.has_inherited_values() / Component.has_inherited_values() are True only
    while something actually reads through (so the prompt appears only when a
    detach would really change values), and go False after a snapshot;
  - detach_choice_message names the subject and the source and offers both paths.

The keep-path baking itself is covered by verify_snapshot_detach /
verify_snapshot_component.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_detach_choice.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication

from mudlab.file_parsers.mud_project import load_mud
from mudlab.inheritance_detach import detach_choice_message
from mudlab.models.phase import Phase

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _find():
    """(path, project, phase-child, phase-parent, linked-component, plain-phase,
    plain-component) from the first fixture that has them."""
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        child = next((c for c in project.phases
                      if isinstance(c, Phase) and isinstance(getattr(c, "based_on", None), Phase)), None)
        comp = next((c for ph in project.phases for c in getattr(ph, "components", [])
                     if c.linked_with is not None and c.inherit_layer_atoms), None)
        plain_phase = next((p for p in project.phases
                            if isinstance(p, Phase) and p.based_on is None), None)
        plain_comp = next((c for ph in project.phases for c in getattr(ph, "components", [])
                           if c.linked_with is None), None)
        if child and comp and plain_phase and plain_comp:
            return path, project, child, child.based_on, comp, plain_phase, plain_comp
    return (None,) * 7


PATH, PROJECT, CHILD, PARENT, COMP, PLAIN_PHASE, PLAIN_COMP = _find()
if CHILD is None:
    print("No fixture with the needed phases/components; skipping (exit 2).")
    raise SystemExit(2)


def main():
    print("fixture: %s" % os.path.basename(PATH))

    # --- Phase gating -------------------------------------------------
    check("phase: not based on anything -> no inherited values",
          not PLAIN_PHASE.has_inherited_values())
    CHILD.inherit_sigma_star = True  # force at least one live inheritance
    check("phase: while inheriting -> has_inherited_values True",
          CHILD.has_inherited_values())
    CHILD.snapshot_inherited()
    check("phase: after snapshot -> has_inherited_values False",
          not CHILD.has_inherited_values())

    # --- Component gating ---------------------------------------------
    check("component: not linked -> no inherited values",
          not PLAIN_COMP.has_inherited_values())
    check("component: while inheriting -> has_inherited_values True",
          COMP.has_inherited_values())
    COMP.snapshot_inherited()
    check("component: after snapshot -> has_inherited_values False",
          not COMP.has_inherited_values())

    # --- Message ------------------------------------------------------
    m = detach_choice_message("phase", "IS R0 Ca-AD")
    check("message: names the subject", "phase" in m)
    check("message: names the source", "IS R0 Ca-AD" in m)
    check("message: offers keep and revert", "Keep" in m and "revert" in m.lower())
    mc = detach_choice_message("component", "")
    check("message: tolerates an empty source name",
          "component" in mc and "its reference" in mc)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- explicit-detach choice verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
