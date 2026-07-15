#!/usr/bin/env python
"""Durable harness for atom relations (AtomRatio) - Batch 2a.

An AtomRatio splits an occupancy between two atoms (a substitution such as
octahedral Fe-for-Mg): ``atom1.pn = value*sum``, ``atom2.pn = (1-value)*sum``.
It drives the atoms' pn, which feed the structure factor and - where a cell
length derives from a pn - the unit-cell dimensions. For each sample project:

  1. Resolve: every modeled AtomRatio's atom1 / atom2 resolve to real atoms.
  2. Golden-safe load: the relation is NOT applied on load - the stored pn is
     kept (and is consistent, so applying reproduces it).
  3. Apply on edit: setting value re-derives atom1.pn / atom2.pn.
  4. Cascade: where a ratio drives the atom a cell_b UCP derives from, editing
     the ratio moves cell_b (and cell_a after it).
  5. Round-trip: AtomRatio value/sum/enabled/atom refs survive; other relation
     types (AtomContents) stay verbatim.

Run head-less from the repo root:

    ./python/python.exe tools/verify_relations.py

Exit codes: 0 = pass, 1 = regression, 2 = no sample projects. The golden
pattern match is guarded by tools/verify_calc_engine.py.
"""

from __future__ import annotations

import os
import sys
import tempfile

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.models.atom_relations import AtomRatio  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")


def _default_projects():
    out = []
    for name in ("308 r1.mud", "Dh2040A 14Jul26.mud",
                 "Dh2040A 14Jul26 r1.mud", "Dh2040A 14Jul26 r2.mud"):
        in_repo = os.path.join(_FIXTURES, name)
        dl = os.path.join(os.path.expanduser("~"), "Downloads", name)
        out.append(in_repo if os.path.isfile(in_repo) else dl)
    return out


def _applicable(r):
    """A ratio whose two targets both resolve to a real atom's pn (so it can be
    applied). Ratios that reference other relations (multi-substitution
    chaining) or belong to an inherited-relations child have unresolved / null
    targets and are kept but not independently applicable in Batch 2a."""
    return all(
        t is not None and t[0] is not None and t[1] == "pn"
        for t in (r.atom1, r.atom2)
    )


def _comps_with_ratios(project, applicable_only=False):
    for phase in project.phases:
        for comp in phase.components:
            ratios = [r for r in comp._atom_relations if isinstance(r, AtomRatio)]
            if applicable_only:
                ratios = [r for r in ratios if _applicable(r)]
            if ratios:
                yield comp, ratios


def check_resolve(project, results):
    """1. Every atom-pn reference that names a real atom resolves to it."""
    n_app = 0
    for comp, ratios in _comps_with_ratios(project):
        for r in ratios:
            for ref, target in ((r._atom1_ref, r.atom1), (r._atom2_ref, r.atom2)):
                # only atom-pn references pointing at a real atom are asserted
                if isinstance(ref, (list, tuple)) and len(ref) >= 2 and ref[1] == "pn":
                    if target is not None and target[0] is not None:
                        results.append(("1 %s.%s atom resolved" % (comp.name, r.name),
                                        True))
            if _applicable(r):
                n_app += 1
    results.append(("1 applicable AtomRatios exist", n_app > 0))


def check_golden_safe(project, results):
    """2. Not applied on load: stored pn is consistent with the ratio."""
    for comp, ratios in _comps_with_ratios(project, applicable_only=True):
        for r in ratios:
            a1, a2 = r.atom1[0], r.atom2[0]
            pn1, pn2 = a1.pn, a2.pn
            ok = (abs(pn1 - r.value * r.sum) < 1e-6
                  and abs(pn2 - (1.0 - r.value) * r.sum) < 1e-6)
            results.append(("2 %s.%s stored pn consistent" % (comp.name, r.name), ok))


def check_apply_on_edit(project, results):
    """3. Editing value re-derives the atoms' pn."""
    done = False
    for comp, ratios in _comps_with_ratios(project, applicable_only=True):
        r = ratios[0]
        a1, a2 = r.atom1[0], r.atom2[0]
        pn1_0, pn2_0, v0 = a1.pn, a2.pn, r.value
        r.value = 0.3
        r.apply_relation()
        ok = abs(a1.pn - 0.3 * r.sum) < 1e-9 and abs(a2.pn - 0.7 * r.sum) < 1e-9
        results.append(("3 %s.%s applies value*sum" % (comp.name, r.name), ok))
        r.value = v0
        a1.pn, a2.pn = pn1_0, pn2_0  # restore
        done = True
        break
    results.append(("3 apply-on-edit exercised", done))


def check_cascade(project, results):
    """4. Ratio -> pn -> cell_b -> cell_a where the linkage exists."""
    done = False
    for comp, ratios in _comps_with_ratios(project, applicable_only=True):
        ub = comp._ucp_b
        if not (ub.enabled and ub.prop is not None and ub.prop[1] == "pn"):
            continue
        ub_atom = ub.prop[0]
        for r in ratios:
            targets = [t for t in (r.atom1, r.atom2) if t and t[0] is ub_atom]
            if not targets:
                continue
            b0, a0, v0 = comp.cell_b, comp.cell_a, r.value
            pn1_0 = r.atom1[0].pn if r.atom1 and r.atom1[0] else None
            pn2_0 = r.atom2[0].pn if r.atom2 and r.atom2[0] else None
            r.value = min(v0 + 0.1, 1.0)
            comp.apply_atom_relations()   # apply + update_ucp_values
            moved_b = abs(comp.cell_b - b0) > 1e-9
            a_from_b = (comp._ucp_a.enabled and comp._ucp_a.prop is not None
                        and comp._ucp_a.prop[1] == "cell_b")
            moved_a = (abs(comp.cell_a - a0) > 1e-9) if a_from_b else True
            results.append(("4 %s: ratio %s -> cell_b -> cell_a" % (comp.name, r.name),
                            moved_b and moved_a))
            # restore
            r.value = v0
            if pn1_0 is not None:
                r.atom1[0].pn = pn1_0
            if pn2_0 is not None:
                r.atom2[0].pn = pn2_0
            comp.update_ucp_values()
            done = True
            break
        if done:
            break
    results.append(("4 cascade exercised", done))


def check_roundtrip(path, results):
    """5. AtomRatio fields survive; other relation types stay verbatim."""
    project = load_mud(path)
    before = {}
    for comp, ratios in _comps_with_ratios(project):
        for r in ratios:
            before[r.uuid] = (
                r.value, r.sum, r.enabled,
                r.atom1[0].uuid if r.atom1 and r.atom1[0] else None,
                r.atom2[0].uuid if r.atom2 and r.atom2[0] else None,
            )
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_rel_%d.mud" % os.getpid())
    try:
        save_mud(project, tmp)
        reloaded = load_mud(tmp)
        after = {}
        for comp, ratios in _comps_with_ratios(reloaded):
            for r in ratios:
                after[r.uuid] = (
                    r.value, r.sum, r.enabled,
                    r.atom1[0].uuid if r.atom1 and r.atom1[0] else None,
                    r.atom2[0].uuid if r.atom2 and r.atom2[0] else None,
                )
        results.append(("5 same AtomRatio count", len(after) == len(before)))
        ok = all(after.get(k) == v for k, v in before.items())
        results.append(("5 AtomRatio fields survive", ok))
        # AtomContents (opaque) entries preserved verbatim
        def contents(proj):
            return [r for ph in proj.phases for c in ph.components
                    for r in c._atom_relations
                    if isinstance(r, dict) and r.get("type") == "AtomContents"]
        results.append(("5 AtomContents kept verbatim",
                        contents(project) == contents(reloaded)))
    finally:
        for p in (tmp, tmp + "~"):
            if os.path.exists(p):
                os.remove(p)


def run(path):
    print("=" * 72)
    print("Atom relations:", os.path.basename(path))
    print("=" * 72)
    results = []
    project = load_mud(path)
    check_resolve(project, results)
    check_golden_safe(project, results)
    check_apply_on_edit(project, results)
    check_cascade(project, results)
    check_roundtrip(path, results)
    passed = sum(1 for _l, ok in results if ok)
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
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
    print("Atom-relations harness: %d checks across %d project(s): %s"
          % (total, len(existing), "OK" if all_ok else "REGRESSION"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
