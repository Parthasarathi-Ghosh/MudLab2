#!/usr/bin/env python
"""Durable harness for the phase display colour (Edit Phases), head-less.

The phase plot colour is now a modeled property that behaves like sigma*: it
is editable, it round-trips through the .mud, and a based_on child reads it
through the parent when inherit_display_color is set.

  1. model: Phase.display_color get/set; a based_on child with
     inherit_display_color reads the PARENT's colour, and clears it on detach;
     to_dict / from_dict round-trip the OWN value.
  2. widget: the colour button + inherit checkbox are enabled and bound; a
     based_on child greys the colour button when it inherits; toggling
     inherit_display_color flips the effective colour and the greying.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_phase_color.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable sample project.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.edit_phase_widget import EditPhaseWidget  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.models.phase import Phase  # noqa: E402

# This fixture has a based_on chain (IS R0 Ca-AD -> EG / 350) that shares a
# colour by inheritance - the discriminating case.
_FIXTURE = "Dh2040A 14Jul26 r1.mud"
FIXTURE = os.path.join(_REPO, "tools", "sample_projects", _FIXTURE)

_app = QApplication.instance() or QApplication([])
results = []


def check(label, ok):
    results.append((label, bool(ok)))


def run():
    project = load_mud(FIXTURE)
    child = next((p for p in project.phases
                  if getattr(p, "based_on", None) is not None
                  and getattr(p, "inherit_display_color", False)), None)
    if child is None:
        print("No based_on child inheriting its colour; skipping (exit 2).")
        return 2
    parent = child.based_on

    # 1. Model.
    check("1 an inheriting child reads the parent's colour",
          child.display_color == parent.display_color)
    parent.display_color = "#123456"
    check("1 changing the parent flows through to the inheriting child",
          child.display_color == "#123456")
    own = "#abcdef"
    child._display_color = own  # its own (stale) stored value, hidden while inherited
    check("1 while inherited the child still shows the parent's colour",
          child.display_color == "#123456")
    child.inherit_display_color = False
    check("1 clearing inherit reveals the child's own colour",
          child.display_color == own)

    # New phase default + round-trip of the own value.
    fresh = Phase.create_empty(G=1, name="Fresh")
    fresh.display_color = "#ff8800"
    clone = Phase.from_dict(fresh.to_dict(), {})
    check("1 display_color round-trips through to_dict/from_dict",
          clone.display_color == "#ff8800")

    # 2. Widget.
    cand = [(p.name, p) for p in project.phases]
    widget = EditPhaseWidget()
    # A child that DOES inherit its colour: button greyed, checkbox on.
    inh = next(p for p in project.phases
               if getattr(p, "based_on", None) is not None)
    inh.inherit_display_color = True
    widget.bind_phase(inh, phase_candidates=cand, atom_types=list(project.atom_types))
    check("2 colour button + inherit checkbox are enabled (a based_on child)",
          widget.ui.phase_inherit_display_color.isEnabled())
    check("2 an inheriting child greys the colour button",
          not widget.ui.phase_display_color.isEnabled()
          and widget.ui.phase_inherit_display_color.isChecked())
    check("2 the button shows the effective (parent) colour",
          widget.color.hex().lower() == inh.display_color.lower())
    # Toggle inherit off -> button re-enabled, shows the child's own colour.
    widget.ui.phase_inherit_display_color.setChecked(False)
    check("2 un-inheriting re-enables the colour button",
          widget.ui.phase_display_color.isEnabled()
          and not inh.inherit_display_color)

    # A standalone phase: picking a colour writes the model.
    solo = next(p for p in project.phases if getattr(p, "based_on", None) is None)
    widget.bind_phase(solo, phase_candidates=cand, atom_types=list(project.atom_types))
    check("2 standalone phase: colour button enabled, checkbox disabled",
          widget.ui.phase_display_color.isEnabled()
          and not widget.ui.phase_inherit_display_color.isEnabled())
    from PySide6.QtGui import QColor
    widget._on_color_picked(QColor("#00ff7f"))
    check("2 picking a colour writes it to the phase model",
          solo.display_color == "#00ff7f")
    widget.deleteLater()
    return None


def main():
    print("=" * 72)
    print("Phase display colour")
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
    print("Phase-colour harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
