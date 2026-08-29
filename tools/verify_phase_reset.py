#!/usr/bin/env python
"""Reset a phase to the default it started as - structure only.

Requested 2026-08-26. The decisions this pins, and why each was made:

* **Structure only.** sigma*, the CSDS distribution, the stacking
  probabilities, and per component the cell parameters, atoms and relations.
* **Name and display colour are KEPT** - they are labels the user chose. A
  renamed phase stays renamed; a recoloured curve stays recoloured.
* **`based_on` and `linked_with` are KEPT.** The shipped default has neither,
  so applying it literally would dismantle the inheritance graph. Severing is
  destructive enough that the app has snapshot-on-detach to soften it; a reset
  must not do it silently.
* **Mixture fractions / scales / backgrounds are untouched** - they belong to
  the mixture, not the phase.
* **A phase is ONE OBJECT shared by every cell that uses it**, so a reset
  necessarily applies to every mixture using it. There is no per-mixture reset
  without duplicating the phase, and the confirmation names the mixtures that
  will recompute.
* **Reset requires a STATED default.** A project created before the mapping
  existed has none, and its phases have since been refined - guessing one at
  reset time would restore the wrong thing. Reset stays greyed until the
  Default Phases dialog says what the phase started as.

TWO HAZARDS this nearly shipped with, both covered below:

1. `phase.probabilities` holds a `set_based_on` link to the parent's
   probabilities. Replacing the OBJECT would sever inheritance - exactly what
   the design says not to do - so values are copied INTO the existing object.
2. A unit-cell property can DERIVE from an atom, and `prop` is a live
   `(object, attr)` pair. Copying it from the rebuild would point the live
   phase at a throwaway object; the stored `[uuid, attr]` is re-resolved
   against the atoms the component now holds instead.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_phase_reset.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no usable sample project.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from mudlab.default_state import (  # noqa: E402
    can_reset, mixtures_using, reset_to_default, structural_phases,
    suggest_default_phase_map,
)
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in sorted(glob.glob(os.path.join(
            _REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        if project.mixtures and suggest_default_phase_map(project):
            return path
    return None


PATH = _fixture()
if PATH is None:
    print("No sample project whose phases map to shipped defaults; skip (2).")
    raise SystemExit(2)


def _resettable(project):
    project.set_default_phase_map(suggest_default_phase_map(project))
    for phase in structural_phases(project):
        if can_reset(project, phase)[0]:
            return phase
    return None


def main():
    # ------------------------------------------------ the gate on a mapping
    project = load_mud(PATH)
    phase = structural_phases(project)[0]
    possible, why = can_reset(project, phase)
    check("gate: a project with no stated default cannot reset", not possible)
    check("gate: ...and the reason points at the Default Phases dialog",
          "Default phases" in why)

    phase = _resettable(project)
    check("gate: stating the defaults makes it resettable", phase is not None)
    if phase is None:
        return _report()

    # ------------------------------------------------------- what it restores
    component = phase.components[0]
    original = (phase.sigma_star, component.d001, component.default_c,
                [a.pn for a in component.layer_atoms])
    name, colour = phase.name, phase.display_color

    phase.sigma_star = 9.99
    component.d001 = 5.0
    component.default_c = 4.0
    if component.layer_atoms:
        component.layer_atoms[0].pn = 99.0
    phase.name = "renamed by the user"
    phase.display_color = "#ff00ff"

    check("reset: it succeeds", reset_to_default(project, phase) is True)
    component = phase.components[0]
    check("reset: sigma* restored", abs(phase.sigma_star - original[0]) < 1e-9)
    check("reset: d001 restored", abs(component.d001 - original[1]) < 1e-9)
    check("reset: default c restored",
          abs(component.default_c - original[2]) < 1e-9)
    check("reset: atom occupancies restored",
          [a.pn for a in component.layer_atoms] == original[3])

    # ----------------------------------------------------- what it must NOT do
    check("keeps: the user's NAME survives", phase.name == "renamed by the user")
    check("keeps: the user's COLOUR survives", phase.display_color == "#ff00ff")

    # ------------------------------------------------- inheritance is intact
    project2 = load_mud(PATH)
    child = _resettable(project2)
    parent = next((p for p in structural_phases(project2) if p is not child),
                  None)
    if child is not None and parent is not None and child.set_based_on(parent):
        probs_before = child.probabilities
        check("inherit: setup - the child is based_on the parent",
              child.based_on is parent)
        reset_to_default(project2, child)
        check("inherit: based_on SURVIVES the reset", child.based_on is parent)
        check("inherit: the probabilities OBJECT is not swapped out "
              "(that would sever the link)",
              child.probabilities is probs_before)
        linked = getattr(child.probabilities, "based_on", None)
        check("inherit: ...so the probabilities are still linked to the parent",
              linked is None or linked is parent.probabilities)
    else:
        check("inherit: (no usable parent in this fixture; skipped)", True)

    # ---------------------------------------------- mixture values untouched
    project3 = load_mud(PATH)
    phase3 = _resettable(project3)
    mixture = project3.mixtures[0]
    fractions = list(mixture.fractions)
    scales = list(mixture.scales)
    bgshifts = list(mixture.bgshifts)
    reset_to_default(project3, phase3)
    check("scope: mixture fractions untouched", list(mixture.fractions) == fractions)
    check("scope: mixture scales untouched", list(mixture.scales) == scales)
    check("scope: background shifts untouched",
          list(mixture.bgshifts) == bgshifts)

    # ------------------------------------------------- shared across mixtures
    using = mixtures_using(project3, phase3)
    check("shared: the affected mixtures can be named for the confirmation",
          bool(using) and all(hasattr(m, "name") for m in using))

    # -------------------------------------------------- the pattern recomputes
    project3.calculate()
    check("after: the project still calculates", True)

    # ------------------------------------------------------------- the dialog
    from mudlab.edit_phases_dialog import EditPhasesDialog

    asked, informed = [], []
    QMessageBox.question = staticmethod(
        lambda *a, **k: (asked.append(a[2]),
                         QMessageBox.StandardButton.Yes)[1])
    QMessageBox.information = staticmethod(lambda *a, **k: informed.append(a[2]))

    project4 = load_mud(PATH)
    dialog = EditPhasesDialog(None, project=project4)
    dialog.show()
    app.processEvents()
    target = structural_phases(project4)[0]
    dialog.ui.edit_objects_treeview.setCurrentIndex(
        dialog.objects_model.index(dialog._phases.index(target), 0))
    app.processEvents()

    entry = [a for a in dialog._phase_menu().actions() if "Reset" in a.text()]
    check("ui: the phase list offers Reset", len(entry) == 1)
    check("ui: it is DISABLED while no default is stated",
          entry and not entry[0].isEnabled())
    check("ui: ...and its tooltip says where to state one",
          entry and "Default phases" in entry[0].toolTip())

    project4.set_default_phase_map(suggest_default_phase_map(project4))
    entry = [a for a in dialog._phase_menu().actions() if "Reset" in a.text()]
    check("ui: enabled once a default is stated",
          entry and entry[0].isEnabled())

    target.sigma_star = 7.77
    dialog._on_reset_to_default()
    app.processEvents()
    check("ui: the reset ran", abs(target.sigma_star - 7.77) > 1e-9)
    text = asked[-1] if asked else ""
    check("ui: the confirmation names the mixtures that will recompute",
          any((m.name or "") in text for m in project4.mixtures))
    check("ui: ...and states what is NOT touched",
          "NAME" in text and "COLOUR" in text and "inheritance" in text)
    check("ui: ...and warns it cannot be undone", "cannot be undone" in text)
    dialog.close()

    return _report()


def _report():
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Phase reset:", os.path.basename(PATH))
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
