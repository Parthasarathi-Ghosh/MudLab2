#!/usr/bin/env python
"""Batch 1 of snapshot-on-detach: Phase.snapshot_inherited().

When a phase's based_on parent is deleted (or it is explicitly detached), the
child normally reverts to its OWN stored values, which can differ from the
values it was showing through inheritance - a silent shift in the calculated
pattern (per-phase audit finding #5 / scenario 4). snapshot_inherited() bakes
the resolved values into own storage first, so a detach is value-preserving.

This forces a real inheritance scenario on a fixture's based_on child (distinct
parent values, distinct own values, all inherit flags on), then checks:

  - the resolved sigma* / CSDS mean / display_color / stacking params are
    UNCHANGED across snapshot() and the following detach;
  - the inherit flags and based_on pointer are cleared;
  - the CSDS distribution is COPIED, not shared (so sibling variants can't alias
    one object);
  - after the parent is mutated, the child does not move (no read-through left);
  - a phase with no inheritance is a no-op.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_snapshot_detach.py

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
from mudlab.models.csds import DritsCSDSDistribution
from mudlab.models.phase import Phase

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _prob_params(phase):
    return [r["get"]() for r in phase.probabilities.editable_params()]


def _find_parent_child():
    """A (path, parent, child) where child.based_on is parent and both are real
    Phase models (they carry sigma*/CSDS/probabilities)."""
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        for child in project.phases:
            parent = getattr(child, "based_on", None)
            if (isinstance(child, Phase) and isinstance(parent, Phase)
                    and child is not parent):
                return path, project, parent, child
    return None, None, None, None


PATH, PROJECT, PARENT, CHILD = _find_parent_child()
if CHILD is None:
    print("No fixture has a Phase based_on another Phase; skipping (exit 2).")
    raise SystemExit(2)


def main():
    print("fixture: %s  (child %r based_on %r)"
          % (os.path.basename(PATH), CHILD.name, PARENT.name))

    # --- Force a meaningful inheritance scenario -----------------------
    # Parent: distinctive own values, inheriting nothing itself.
    PARENT.inherit_sigma_star = False
    PARENT.inherit_CSDS_distribution = False
    PARENT.inherit_display_color = False
    PARENT.probabilities.clear_inheritance()
    PARENT._sigma_star = 0.137
    PARENT._CSDS = DritsCSDSDistribution(41.0)
    PARENT._display_color = "#123456"
    for k, row in enumerate(PARENT.probabilities.editable_params()):
        row["set"](0.20 + 0.05 * k)

    # Child: different OWN values, then inherit everything from the parent.
    CHILD._sigma_star = 0.999
    CHILD._CSDS = DritsCSDSDistribution(3.0)
    CHILD._display_color = "#fedcba"
    for row in CHILD.probabilities.editable_params():
        row["set"](0.9)
    CHILD.probabilities.set_based_on(PARENT.probabilities)
    CHILD.inherit_sigma_star = True
    CHILD.inherit_CSDS_distribution = True
    CHILD.inherit_display_color = True
    CHILD.probabilities.inherit_all()

    # Sanity: the child is really reading the parent right now.
    res_sigma = CHILD.sigma_star
    res_csds = CHILD.CSDS.average
    res_color = CHILD.display_color
    res_probs = _prob_params(CHILD)
    check("precondition: child inherits the parent's sigma*",
          res_sigma == 0.137)
    check("precondition: child inherits the parent's CSDS mean",
          res_csds == 41.0)
    check("precondition: child inherits the parent's colour",
          res_color == "#123456")
    check("precondition: child inherits the parent's stacking params",
          res_probs == _prob_params(PARENT))

    # --- Snapshot -----------------------------------------------------
    baked = CHILD.snapshot_inherited()
    check("snapshot: reports it baked something", baked is True)
    check("snapshot: resolved sigma* unchanged", CHILD.sigma_star == res_sigma)
    check("snapshot: resolved CSDS mean unchanged", CHILD.CSDS.average == res_csds)
    check("snapshot: resolved colour unchanged", CHILD.display_color == res_color)
    check("snapshot: resolved stacking params unchanged",
          _prob_params(CHILD) == res_probs)
    check("snapshot: phase inherit flags cleared",
          not CHILD.inherit_sigma_star and not CHILD.inherit_CSDS_distribution
          and not CHILD.inherit_display_color)
    check("snapshot: probability inherit flags cleared",
          all(not r["inherited"] for r in CHILD.probabilities.editable_params()))
    check("snapshot: CSDS is a copy, not the parent's object",
          CHILD._CSDS is not PARENT._CSDS and CHILD.CSDS.average == PARENT.CSDS.average)

    # --- Detach -------------------------------------------------------
    CHILD.set_based_on(None)
    check("detach: based_on cleared", CHILD.based_on is None)
    check("detach: resolved sigma* still unchanged", CHILD.sigma_star == res_sigma)
    check("detach: resolved CSDS mean still unchanged", CHILD.CSDS.average == res_csds)
    check("detach: resolved colour still unchanged", CHILD.display_color == res_color)
    check("detach: resolved stacking params still unchanged",
          _prob_params(CHILD) == res_probs)

    # --- Independence: mutating the (soon-deleted) parent must not move us --
    PARENT._sigma_star = 0.0
    PARENT._CSDS = DritsCSDSDistribution(1.0)
    PARENT._display_color = "#000000"
    for row in PARENT.probabilities.editable_params():
        row["set"](0.01)
    check("independence: child sigma* unaffected by parent edit",
          CHILD.sigma_star == res_sigma)
    check("independence: child CSDS mean unaffected by parent edit",
          CHILD.CSDS.average == res_csds)
    check("independence: child colour unaffected by parent edit",
          CHILD.display_color == res_color)
    check("independence: child stacking params unaffected by parent edit",
          _prob_params(CHILD) == res_probs)

    # --- No-op on a phase that inherits nothing -----------------------
    plain = next((p for p in PROJECT.phases
                  if isinstance(p, Phase) and p.based_on is None), None)
    if plain is not None:
        before = (plain.sigma_star, plain.CSDS.average, plain.display_color,
                  _prob_params(plain))
        did = plain.snapshot_inherited()
        after = (plain.sigma_star, plain.CSDS.average, plain.display_color,
                 _prob_params(plain))
        check("no-op: snapshot on a non-inheriting phase reports nothing baked",
              did is False)
        check("no-op: its values are unchanged", before == after)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- snapshot-on-detach (phase) verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
