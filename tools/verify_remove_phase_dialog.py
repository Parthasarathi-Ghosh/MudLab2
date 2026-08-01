#!/usr/bin/env python
"""Batch 4 of snapshot-on-detach: the dependant-aware delete confirmation.

Deleting a base phase now warns and names the phases that depend on it (they are
detached but their values are baked in first, so their patterns are preserved).
The modal box itself is not unit-testable head-less, so this covers the two
pieces of logic behind it:

  - Project.phase_dependants(phase): the DIRECT dependants (based_on children +
    components linked to its components), excluding the phase itself, no
    transitive or false hits;
  - deletion_confirm_message(phase, dependants): names the dependants when there
    are any, and falls back to the plain irreversible warning when there are none.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_remove_phase_dialog.py

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

from mudlab.edit_phases_dialog import deletion_confirm_message
from mudlab.file_parsers.mud_project import load_mud

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _find_base_and_leaf(project):
    """A base phase with >=1 dependant, and a leaf phase with none."""
    base = leaf = None
    for phase in project.phases:
        deps = project.phase_dependants(phase)
        if deps and base is None:
            base = phase
        if not deps and leaf is None:
            leaf = phase
    return base, leaf


def _find_fixture():
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        base, leaf = _find_base_and_leaf(load_mud(path))
        if base is not None and leaf is not None:
            return path
    return None


PATH = _find_fixture()
if PATH is None:
    print("No fixture with both a base and a leaf phase; skipping (exit 2).")
    raise SystemExit(2)


def main():
    project = load_mud(PATH)
    base, leaf = _find_base_and_leaf(project)
    deps = project.phase_dependants(base)
    print("fixture: %s  (base %r -> %d dependant(s), leaf %r)"
          % (os.path.basename(PATH), base.name, len(deps), leaf.name))

    # phase_dependants
    check("dependants: the base has at least one", len(deps) >= 1)
    check("dependants: the base is not its own dependant", base not in deps)
    check("dependants: every listed dependant really reads from the base",
          all(d.based_on is base
              or any(c.linked_with is not None
                     and c.linked_with in list(getattr(base, "components", []))
                     for c in getattr(d, "components", []))
              for d in deps))
    check("dependants: a leaf phase has none",
          project.phase_dependants(leaf) == [])

    # message text
    msg_base = deletion_confirm_message(base, deps)
    check("message: names the reference phase", (base.name or "") in msg_base)
    check("message: mentions how many depend on it", str(len(deps)) in msg_base)
    check("message: lists each dependant by name",
          all((d.name or "(unnamed)") in msg_base for d in deps))
    check("message: reassures the patterns will not change",
          "will not change" in msg_base)

    msg_leaf = deletion_confirm_message(leaf, [])
    check("message: leaf falls back to the plain irreversible warning",
          "irreversible" in msg_leaf and "reference for" not in msg_leaf)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- remove-phase confirmation verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
