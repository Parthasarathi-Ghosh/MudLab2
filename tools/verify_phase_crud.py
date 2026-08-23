#!/usr/bin/env python
"""Durable harness for adding and removing phases (Batch P1).

Removing a phase is the operation with teeth: a project points at its phases
from four places, and a missed one leaves a dangling reference that either
crashes the calc or - far worse - silently keeps a deleted object in the fit.
The old Project.on_phase_removed cascade-clears rather than refusing, and this
harness holds MudLab2 to the same contract:

  1. the removed phase's own based_on link,
  2. any phase based_on the removed one (dependants fall back to their OWN
     stored values - inheritance is a read-time overlay, so they just stop
     reading through),
  3. any component elsewhere linked_with one of the removed phase's
     components,
  4. every mixture cell holding it (the slot stays, the cell empties),
  5. and it must PERSIST: both add and remove have to survive save/reload.

Point 5 is the one that bites. The mixture grid is stored twice (resolved
objects + uuid lists) and the saver walks the RAW phase list, so an
add/remove can look perfect in-session and silently revert on reload.

Also guards remove_specimen, which had the same defect: it left the specimen
in the mixture, so the optimiser kept fitting against a deleted specimen and
the residual did not change at all.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_phase_crud.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample projects.
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.models.phase import Phase  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")
_app = QApplication.instance() or QApplication([])


def _default_projects():
    out = []
    for name in (
        "308 r1.mud",
        "Dh2040A 14Jul26.mud",
        "Dh2040A 14Jul26 r1.mud",
        "Dh2040A 14Jul26 r2.mud",
    ):
        in_repo = os.path.join(_FIXTURES, name)
        dl = os.path.join(os.path.expanduser("~"), "Downloads", name)
        out.append(in_repo if os.path.isfile(in_repo) else dl)
    return out


def _roundtrip(project):
    """save -> load, cleaning up after itself."""
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_phase_crud.mud")
    try:
        save_mud(project, tmp)
        return load_mud(tmp)
    finally:
        for p in (tmp, tmp + "~"):
            if os.path.exists(p):
                os.remove(p)


def check_add(path, results):
    """1. A new phase is added, persists, and keeps its identity."""
    project = load_mud(path)
    before = len(project.phases)
    new = Phase(name="Harness New Phase", G=1)
    project.add_phase(new)
    results.append(("1 add_phase appends", len(project.phases) == before + 1))

    reloaded = _roundtrip(project)
    names = [p.name for p in reloaded.phases]
    results.append(("1 added phase survives save/reload",
                    "Harness New Phase" in names))
    results.append(("1 added phase count is right", len(names) == before + 1))
    match = [p for p in reloaded.phases if p.name == "Harness New Phase"]
    results.append(("1 added phase keeps its uuid (no renumbering)",
                    bool(match) and match[0].uuid == new.uuid))
    # Existing phases must be untouched by the addition.
    results.append(("1 existing phases still present",
                    all(p.name in names for p in project.phases
                        if p.name != "Harness New Phase")))
    results.append(("1 mixtures still compute after an add",
                    (not reloaded.mixtures)
                    or np.isfinite(reloaded.mixtures[0].current_residual())))


def check_remove_in_use(path, results):
    """4. A phase a mixture uses is NOT deletable - the project refuses and the
    grid is untouched. Freed, the same delete goes through and leaves no uuid
    behind (a stale uuid would revive the phase on the next load)."""
    project = load_mud(path)
    if not project.mixtures:
        return
    mixture = project.mixtures[0]
    target = None
    for row in mixture.phase_matrix:
        for phase in row:
            if phase is not None:
                target = phase
                break
        if target:
            break
    if target is None:
        return

    removed = project.remove_phase(target)
    results.append(("4 deleting a phase a mixture uses is REFUSED",
                    removed is False and target in project.phases))
    still_resolved = any(p is target for row in mixture.phase_matrix for p in row)
    results.append(("4 its mixture cells are untouched by the refusal",
                    still_resolved))
    results.append(("4 phase_usage names the mixture holding it",
                    any(m is mixture for m, _cells in project.phase_usage(target))))

    # Free it the way the user would, then delete for real.
    for other in project.mixtures:
        other.unset_phase(target)
    results.append(("4 a freed phase deletes", project.remove_phase(target) is True))
    results.append(("4 phase gone from the project", target not in project.phases))
    still_uuid = any(u == target.uuid for row in mixture.phase_uuids for u in row)
    results.append(("4 no mixture uuid still names it (else save revives it)",
                    not still_uuid))
    results.append(("4 residual still computable after removal",
                    np.isfinite(mixture.current_residual())))
    # The slot must survive - only the cell empties (old unset_phase).
    results.append(("4 the phase SLOT stays (fractions/labels keep meaning)",
                    len(mixture.phase_labels) == len(mixture.fractions)))


def check_remove_cascades_based_on(path, results):
    """1+2. based_on links clear, and dependants keep the RESOLVED values they
    were showing (snapshot-on-detach bakes them in before severing, so the
    calculated pattern does not shift)."""
    project = load_mud(path)
    parent = None
    for phase in project.phases:
        if any(other.based_on is phase for other in project.phases):
            parent = phase
            break
    if parent is None:
        return
    dependants = [p for p in project.phases if p.based_on is parent]
    # The effective (read-through) F values a dependant is showing WHILE it still
    # inherits - these must survive the removal, not revert to stale own values.
    resolved_f_before = [
        [d.probabilities.f_value(i)
         for i in range(d.probabilities.n_independents)]
        for d in dependants
    ]

    # In a real project the parent is usually IN a mixture, and that is now a
    # refusal - so free it first; the cascade being tested here is the
    # inheritance one, which is unrelated to mixture membership.
    for mixture in project.mixtures:
        mixture.unset_phase(parent)
    results.append(("2 the freed parent deletes",
                    project.remove_phase(parent) is True))
    results.append(("2 dependants' based_on cleared",
                    all(d.based_on is None for d in dependants)))
    results.append(("2 dependants keep their RESOLVED F values (snapshot-on-detach)",
                    all(
                        all(abs(d.probabilities.f_value(i) - resolved_f_before[n][i]) < 1e-12
                            for i in range(d.probabilities.n_independents))
                        for n, d in enumerate(dependants)
                    )))
    results.append(("2 nothing still reports the removed phase as its parent",
                    not any(p.based_on is parent for p in project.phases)))
    results.append(("1 removed phase's own based_on cleared",
                    parent.based_on is None))

    reloaded = _roundtrip(project)
    results.append(("2 removal persists (phase does NOT come back)",
                    parent.name not in [p.name for p in reloaded.phases]))
    results.append(("2 no reloaded phase dangles a based_on",
                    all(p.based_on is not None or not p._based_on_uuid
                        for p in reloaded.phases)))


def check_remove_clears_links(path, results):
    """3. Components linked to the removed phase's components are unlinked."""
    project = load_mud(path)
    # Find a phase whose components are used as a template elsewhere.
    target, dependants = None, []
    for phase in project.phases:
        ids = {id(c) for c in phase.components}
        deps = [
            comp for other in project.phases if other is not phase
            for comp in other.components
            if comp.linked_with is not None and id(comp.linked_with) in ids
        ]
        if deps:
            target, dependants = phase, deps
            break
    if target is None:
        return
    for mixture in project.mixtures:
        mixture.unset_phase(target)
    results.append(("3 the freed template phase deletes",
                    project.remove_phase(target) is True))
    results.append(("3 components linked to the removed phase are unlinked (%d)"
                    % len(dependants),
                    all(c.linked_with is None for c in dependants)))
    results.append(("3 unlinked components cleared their inherit flags",
                    all(not c.inherit_layer_atoms for c in dependants)))


def check_remove_specimen(path, results):
    """5. A specimen a mixture is fitting against is NOT deletable; freed, it
    deletes and the mixture stops fitting it.

    Regression guard behind the second half: remove_specimen once left the row
    in place, so the optimiser kept fitting a deleted specimen - the residual
    was byte-identical before and after.
    """
    project = load_mud(path)
    if not project.mixtures:
        return
    mixture = project.mixtures[0]
    rows = [s for s in mixture.specimens if s is not None and s.has_experimental_data]
    if len(rows) < 2:
        return
    spec = rows[0]
    before = mixture.current_residual()
    results.append(("5 deleting a specimen a mixture uses is REFUSED",
                    project.remove_specimen(spec) is False
                    and spec in project.specimens))
    results.append(("5 the refusal leaves the mixture row alone",
                    any(s is spec for s in mixture.specimens)
                    and mixture.current_residual() == before))
    results.append(("5 specimen_usage names the mixture holding it",
                    any(m is mixture for m, _rows in project.specimen_usage(spec))))

    for other in project.mixtures:
        other.unset_specimen(spec)
    results.append(("5 a freed specimen deletes",
                    project.remove_specimen(spec) is True))
    after = mixture.current_residual()
    results.append(("5 removed specimen is gone from the project",
                    spec not in project.specimens))
    results.append(("5 no mixture row still holds it",
                    not any(s is spec for s in mixture.specimens)))
    results.append(("5 no mixture uuid still names it",
                    spec.uuid not in mixture.specimen_uuids))
    results.append(("5 residual CHANGES (%.4f -> %.4f) - it no longer fits a "
                    "deleted specimen" % (before, after),
                    abs(before - after) > 1e-9))


def run(path):
    print("=" * 72)
    print("Phase add/remove:", os.path.basename(path))
    print("=" * 72)
    results = []
    check_add(path, results)
    check_remove_in_use(path, results)
    check_remove_cascades_based_on(path, results)
    check_remove_clears_links(path, results)
    check_remove_specimen(path, results)
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("%d/%d checks passed" % (passed, len(results)))
    return passed == len(results), len(results)


def main(argv):
    paths = argv[1:] or _default_projects()
    existing = [p for p in paths if os.path.isfile(p)]
    if not existing:
        print("No sample projects found; skipping (exit 2).")
        return 2
    all_ok, total = True, 0
    for path in existing:
        ok, n = run(path)
        all_ok = all_ok and ok
        total += n
        print()
    print("=" * 72)
    print("Phase CRUD harness: %d checks across %d project(s): %s"
          % (total, len(existing), "OK" if all_ok else "REGRESSION"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
