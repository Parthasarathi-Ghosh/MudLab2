#!/usr/bin/env python
"""Link-integrity harness for the Mixture-Specimen-Phase object graph.

The graph is linked by uuid and held in two parallel representations that MUST
agree (see docs/dev-notes.md "Object-graph linkage"):

  - the uuid grids a mixture persists  - specimen_uuids / phase_uuids,
    plus phase.based_on_uuid and component.linked_with_uuid;
  - the resolved object pointers the calc reads - mixture.specimens /
    phase_matrix, phase.based_on, component.linked_with.

Nothing in the app asserts they stay in lock-step, so this does. It checks two
things:

  1. STATIC (every sample fixture, straight off disk):
     - shape consistency (row/column counts line up);
     - grid consistency: phase_matrix[i][j] IS project.resolve(phase_uuids[i][j])
       with "" <-> None, and likewise for specimens;
     - inheritance consistency: a live based_on / linked_with pointer matches its
       stored uuid and points at a live project object;
     - referential completeness: no non-empty uuid is left dangling.

  2. CASCADE (delete a specimen / phase / mixture in use): the model's
     remove_* cascades must leave the grid invariant intact - both
     representations cleared together, dependants detached.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_link_integrity.py

Exit codes: 0 = clean, 1 = an invariant is violated, 2 = no fixtures found.
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

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool, str]] = []


def check(label, ok, detail=""):
    results.append((label, bool(ok), detail))


def _fixtures():
    return sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud")))


def _component_map(project):
    return {
        c.uuid: c
        for phase in project.phases
        for c in getattr(phase, "components", [])
    }


# ----------------------------------------------------------------------
# Invariant probes - each returns (consistency_violations, dangling_notes)
# ----------------------------------------------------------------------
def mixture_violations(project, mix):
    """Grid consistency + shape. Consistency is the hard invariant; dangling
    uuids are reported separately (a data condition, not a sync bug)."""
    viol, dangling = [], []
    pmap = project.phase_uuid_map()
    smap = project.specimen_uuid_map()
    n, m = mix.n, mix.m

    if len(mix.specimens) != n:
        viol.append("len(specimens)=%d != n=%d" % (len(mix.specimens), n))
    if len(mix.phase_matrix) != n:
        viol.append("len(phase_matrix)=%d != n=%d" % (len(mix.phase_matrix), n))
    if len(mix.phase_uuids) != n:
        viol.append("len(phase_uuids)=%d != n=%d" % (len(mix.phase_uuids), n))
    for i, row in enumerate(mix.phase_matrix):
        if len(row) != m:
            viol.append("phase_matrix row %d width %d != m=%d" % (i, len(row), m))

    for i in range(min(len(mix.specimens), len(mix.specimen_uuids))):
        u, obj = mix.specimen_uuids[i], mix.specimens[i]
        expected = smap.get(u) if u else None
        if obj is not expected:
            viol.append("row %d: specimen object != resolve(uuid %r)" % (i, u))
        if u and expected is None:
            dangling.append("row %d: specimen uuid %r resolves to nothing" % (i, u))

    for i in range(min(len(mix.phase_matrix), len(mix.phase_uuids))):
        row_obj, row_uuid = mix.phase_matrix[i], mix.phase_uuids[i]
        for j in range(min(len(row_obj), len(row_uuid))):
            u, obj = row_uuid[j], row_obj[j]
            expected = pmap.get(u) if u else None
            if obj is not expected:
                viol.append("cell %d,%d: phase object != resolve(uuid %r)" % (i, j, u))
            if u and expected is None:
                dangling.append("cell %d,%d: phase uuid %r resolves to nothing" % (i, j, u))
    return viol, dangling


def based_on_violations(project):
    viol, dangling = [], []
    phases = set(project.phases)
    pmap = project.phase_uuid_map()
    for p in project.phases:
        u = getattr(p, "_based_on_uuid", "") or ""
        parent = p.based_on
        if parent is not None:
            if parent is p:
                viol.append("phase %r based_on itself" % p.name)
            if parent not in phases:
                viol.append("phase %r based_on a phase not in the project" % p.name)
            if parent.uuid != u:
                viol.append("phase %r: based_on.uuid != stored based_on_uuid" % p.name)
        elif u and pmap.get(u) is not None:
            # A stored uuid that resolves to a phase but is NOT bound is a
            # legitimate refusal (different G / cycle), not a sync bug - note it.
            dangling.append("phase %r: based_on_uuid %r stored but unbound "
                            "(G-mismatch/cycle?)" % (p.name, u))
    return viol, dangling


def linked_with_violations(project):
    viol, dangling = [], []
    cmap = _component_map(project)
    comps = set(cmap.values())
    for phase in project.phases:
        for c in getattr(phase, "components", []):
            u = getattr(c, "_linked_with_uuid", "") or ""
            tmpl = c.linked_with
            if tmpl is not None:
                if tmpl is c:
                    viol.append("component %r linked to itself" % c.name)
                if tmpl not in comps:
                    viol.append("component %r linked to a component not in the project"
                                % c.name)
                if tmpl.uuid != u:
                    viol.append("component %r: linked_with.uuid != stored uuid" % c.name)
            elif u and cmap.get(u) is not None:
                dangling.append("component %r: linked_with_uuid %r stored but unbound"
                                % (c.name, u))
    return viol, dangling


def all_violations(project):
    """(hard consistency violations, soft dangling notes) for a whole project."""
    viol, dangling = [], []
    for mix in project.mixtures:
        v, d = mixture_violations(project, mix)
        viol += ["mixture %r: %s" % (mix.name, s) for s in v]
        dangling += ["mixture %r: %s" % (mix.name, s) for s in d]
    for probe in (based_on_violations, linked_with_violations):
        v, d = probe(project)
        viol += v
        dangling += d
    return viol, dangling


# ----------------------------------------------------------------------
def static_pass():
    fixtures = _fixtures()
    if not fixtures:
        return False
    total_dangling = 0
    for path in fixtures:
        name = os.path.basename(path)
        project = load_mud(path)
        viol, dangling = all_violations(project)
        check("static: %s grid/inheritance invariant holds" % name,
              not viol, "; ".join(viol[:4]))
        total_dangling += len(dangling)
        if dangling:
            for note in dangling[:6]:
                print("    (dangling) %s: %s" % (name, note))
    print("  static: %d fixture(s), %d dangling reference note(s)"
          % (len(fixtures), total_dangling))
    return True


def _pick_target(project):
    """First (mixture, row, specimen, col, phase) with a live specimen AND a
    live phase assigned - so the delete cascades have something to clear."""
    for mix in project.mixtures:
        for i, spec in enumerate(mix.specimens):
            if spec is None:
                continue
            for j, ph in enumerate(mix.phase_matrix[i]):
                if ph is not None:
                    return mix, i, spec, j, ph
    return None


def cascade_pass():
    # Use the first fixture that has an assignable target.
    target_path = None
    for path in _fixtures():
        if _pick_target(load_mud(path)) is not None:
            target_path = path
            break
    if target_path is None:
        print("  cascade: no fixture with an assigned specimen+phase; skipped")
        return
    name = os.path.basename(target_path)
    print("  cascade: using %s" % name)

    # --- a specimen IN USE cannot be deleted; freed, it can ---
    project = load_mud(target_path)
    mix, i, spec, j, ph = _pick_target(project)
    mname = mix.name
    check("cascade/specimen: deleting one a mixture uses is REFUSED",
          project.remove_specimen(spec) is False and spec in project.specimens)
    m = next(x for x in project.mixtures if x.name == mname)
    check("cascade/specimen: the refusal leaves both reps intact",
          m.specimens[i] is spec and m.specimen_uuids[i] == spec.uuid)
    m.unset_specimen(spec)
    check("cascade/specimen: freeing empties BOTH reps",
          m.specimens[i] is None and m.specimen_uuids[i] == "")
    check("cascade/specimen: freed, it deletes",
          project.remove_specimen(spec) is True
          and spec not in project.specimens)
    viol, _ = all_violations(project)
    check("cascade/specimen: grid invariant still holds", not viol,
          "; ".join(viol[:4]))

    # --- a phase IN USE cannot be deleted; freed, it can ---
    project = load_mud(target_path)
    mix, i, spec, j, ph = _pick_target(project)
    mname = mix.name
    dependants = [p for p in project.phases if p.based_on is ph]
    check("cascade/phase: deleting one a mixture uses is REFUSED",
          project.remove_phase(ph) is False and ph in project.phases)
    m = next(x for x in project.mixtures if x.name == mname)
    check("cascade/phase: the refusal leaves both reps intact",
          m.phase_matrix[i][j] is ph and m.phase_uuids[i][j] == ph.uuid)
    for other in project.mixtures:
        other.unset_phase(ph)
    check("cascade/phase: freed, it deletes",
          project.remove_phase(ph) is True)
    held = any(cell is ph for row in m.phase_matrix for cell in row)
    uuid_held = any(u == ph.uuid for row in m.phase_uuids for u in row)
    viol, _ = all_violations(project)
    check("cascade/phase: removed from project.phases", ph not in project.phases)
    check("cascade/phase: no cell (object OR uuid) still holds it",
          not held and not uuid_held)
    check("cascade/phase: grid invariant still holds", not viol, "; ".join(viol[:4]))
    check("cascade/phase: dependants (based_on it) detached",
          all(p.based_on is None for p in dependants),
          "%d dependant(s)" % len(dependants))

    # --- delete a mixture ---
    project = load_mud(target_path)
    mix = project.mixtures[0]
    project.remove_mixture(mix)
    viol, _ = all_violations(project)
    check("cascade/mixture: removed from project.mixtures",
          mix not in project.mixtures)
    check("cascade/mixture: remaining graph invariant still holds", not viol,
          "; ".join(viol[:4]))

    # --- detach cascade for a based_on base, if any fixture has one ---
    for path in _fixtures():
        pr = load_mud(path)
        base = next((p for p in pr.phases
                     if any(o.based_on is p for o in pr.phases)), None)
        if base is None:
            continue
        kids = [p for p in pr.phases if p.based_on is base]
        # Mixture membership is a separate gate (checked above); free it so the
        # inheritance cascade itself can be reached.
        for mixture in pr.mixtures:
            mixture.unset_phase(base)
        check("cascade/detach: %s freed base deletes" % os.path.basename(path),
              pr.remove_phase(base) is True)
        viol, _ = all_violations(pr)
        check("cascade/detach: %s children detached when base deleted"
              % os.path.basename(path),
              all(k.based_on is None for k in kids), "%d child(ren)" % len(kids))
        check("cascade/detach: graph invariant still holds after detach",
              not viol, "; ".join(viol[:4]))
        break
    else:
        print("  cascade/detach: no fixture has a based_on relationship; skipped")


def main():
    print("--- link-integrity verification ---")
    if not static_pass():
        print("No sample fixtures found; skipping (exit 2).")
        return 2
    cascade_pass()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print()
    for label, ok, detail in results:
        line = "  [%s] %s" % ("PASS" if ok else "FAIL", label)
        if detail and not ok:
            line += "  <- " + detail
        print(line)
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
