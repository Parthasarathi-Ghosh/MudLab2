#!/usr/bin/env python
"""Snapshot-on-detach must NOT interfere with ordinary linking / unlinking in the
editors (no base deleted). Drives the real phase + component editor widgets with
the keep/revert prompt monkeypatched to a counter, and asserts:

  - binding a phase / component that inherits does NOT pop the prompt (the
    programmatic combo fill is guarded by _updating);
  - LINKING (picking a based_on / template) never prompts (only an explicit
    detach to "(none)" does);
  - an explicit UNLINK of an inheriting object prompts exactly once, and
    "cancel" leaves the link intact while "keep" detaches and preserves the
    shown value.

This is the head-less stand-in for clicking the combos; the value-preservation
of the keep path is covered in depth by verify_snapshot_detach / _component.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_detach_ui_noninterference.py

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

import mudlab.component_widget as component_widget
import mudlab.edit_phase_widget as edit_phase_widget
from mudlab.component_widget import EditComponentWidget
from mudlab.edit_phase_widget import EditPhaseWidget
from mudlab.file_parsers.mud_project import load_mud
from mudlab.models.phase import Phase

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []

# Monkeypatch the shared prompt in both widget modules with a scripted counter.
PROMPT = {"n": 0, "ret": "cancel"}


def _fake_ask(parent, subject, source):
    PROMPT["n"] += 1
    return PROMPT["ret"]


edit_phase_widget.ask_detach_choice = _fake_ask
component_widget.ask_detach_choice = _fake_ask


def check(label, ok):
    results.append((label, bool(ok)))


def _none_index(combo):
    for i in range(combo.count()):
        if combo.itemData(i) is None:
            return i
    return -1


def _first_candidate_index(combo):
    for i in range(combo.count()):
        if combo.itemData(i) is not None:
            return i
    return -1


def _find():
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        child = next((c for c in project.phases
                      if isinstance(c, Phase) and isinstance(getattr(c, "based_on", None), Phase)), None)
        comp = next((c for ph in project.phases for c in getattr(ph, "components", [])
                     if c.linked_with is not None and c.inherit_layer_atoms), None)
        if child and comp:
            return path, project, child, comp
    return None, None, None, None


PATH, PROJECT, CHILD, COMP = _find()
if CHILD is None:
    print("No fixture with an inheriting phase + linked component; skip (exit 2).")
    raise SystemExit(2)


def phase_checks():
    parent = CHILD.based_on
    CHILD.inherit_sigma_star = True  # ensure it really inherits something
    cands = [(p.name, p) for p in PROJECT.phases]

    w = EditPhaseWidget()
    PROMPT["n"] = 0
    w.bind_phase(CHILD, atom_types=PROJECT.atom_types, link_candidates=[],
                 phase_candidates=cands)
    check("phase: binding an inheriting child does not prompt", PROMPT["n"] == 0)

    combo = w.ui.phase_based_on
    none_i = _none_index(combo)

    # Cancel an explicit unlink -> prompts once, link stays.
    PROMPT["n"], PROMPT["ret"] = 0, "cancel"
    combo.setCurrentIndex(none_i)
    check("phase: explicit unlink prompts exactly once", PROMPT["n"] == 1)
    check("phase: cancel keeps the phase based_on its parent",
          CHILD.based_on is parent)

    # Keep -> prompts, detaches, preserves the shown value.
    resolved_sigma = CHILD.sigma_star
    PROMPT["n"], PROMPT["ret"] = 0, "keep"
    combo.setCurrentIndex(none_i)
    check("phase: keep prompts once and detaches", PROMPT["n"] == 1 and CHILD.based_on is None)
    check("phase: keep preserved the shown sigma*", CHILD.sigma_star == resolved_sigma)

    # Linking (pick a based_on) must NOT prompt.
    w.bind_phase(CHILD, atom_types=PROJECT.atom_types, link_candidates=[],
                 phase_candidates=cands)
    cand_i = _first_candidate_index(combo)
    if cand_i >= 0:
        PROMPT["n"] = 0
        combo.setCurrentIndex(cand_i)
        check("phase: linking to a reference does not prompt", PROMPT["n"] == 0)
    else:
        print("  (no same-G candidate to test phase linking; skipped)")


def component_checks():
    template = COMP.linked_with
    link_cands = [(c.name, c) for ph in PROJECT.phases
                  for c in getattr(ph, "components", [])]

    w = EditComponentWidget()
    PROMPT["n"] = 0
    w.bind_components([COMP], atom_types=PROJECT.atom_types, link_candidates=link_cands)
    check("component: binding a linked component does not prompt", PROMPT["n"] == 0)

    combo = w.ui.component_linked_with
    none_i = _none_index(combo)

    PROMPT["n"], PROMPT["ret"] = 0, "cancel"
    combo.setCurrentIndex(none_i)
    check("component: explicit unlink prompts exactly once", PROMPT["n"] == 1)
    check("component: cancel keeps the component linked", COMP.linked_with is template)

    PROMPT["n"], PROMPT["ret"] = 0, "keep"
    combo.setCurrentIndex(none_i)
    check("component: keep prompts once and unlinks",
          PROMPT["n"] == 1 and COMP.linked_with is None)

    # Re-linking must NOT prompt.
    w.bind_components([COMP], atom_types=PROJECT.atom_types, link_candidates=link_cands)
    cand_i = _first_candidate_index(combo)
    if cand_i >= 0:
        PROMPT["n"] = 0
        combo.setCurrentIndex(cand_i)
        check("component: linking to a template does not prompt", PROMPT["n"] == 0)
    else:
        print("  (no candidate to test component linking; skipped)")


def main():
    print("fixture: %s" % os.path.basename(PATH))
    phase_checks()
    component_checks()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- detach-UI non-interference verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
