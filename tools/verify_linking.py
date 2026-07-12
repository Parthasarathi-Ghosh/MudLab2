#!/usr/bin/env python
"""Durable harness for component linking (shared clay layers).

Guards the component-linking overlay added in Batch L1: a component can be
linked to a template component in another phase (old ``linked_with`` +
per-property ``inherit_*`` flags), and an inherited property reads through to
the template's value while the child keeps its own stored copy. For each
sample project it checks:

  1. Links resolve: every child carrying a linked_with_uuid resolves to the
     template component with that uuid.
  2. Read-through: for each inherited property, the child's value equals the
     template's.
  3. Selective inheritance: a NON-inherited property reads the child's own
     value (proven where it differs from the template - e.g. a glycolated
     smectite keeps its own d001 while inheriting the layer from its 2-water
     template).
  4. Propagation: editing the template's value changes the child's inherited
     value live (then it is restored).
  5. Refinables skip inherited scalars: an inherited d001/delta_c is not an
     independent refinable on the child (only the template's is).
  6. Round-trip: load -> save -> reload preserves the links and the inherited
     values.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_linking.py
    ./python/python.exe tools/verify_linking.py "a.mud" "b.mud"

Exit codes: 0 = all checks pass, 1 = a regression, 2 = no sample projects.
The golden calc match itself is guarded by tools/verify_calc_engine.py; run
that too after touching the models.
"""

from __future__ import annotations

import os
import sys
import tempfile

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.calculations.refinement import _phase_refinables  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.models.component import Component  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")

# The scalar/list attributes that participate in component inheritance.
_SCALARS = ("cell_a", "cell_b", "d001", "default_c", "delta_c")
_LISTS = ("layer_atoms", "interlayer_atoms")


def _default_projects():
    projects = []
    for name in ("308 r1.mud", "Dh2040A.mud"):
        in_repo = os.path.join(_FIXTURES, name)
        downloads = os.path.join(os.path.expanduser("~"), "Downloads", name)
        projects.append(in_repo if os.path.isfile(in_repo) else downloads)
    return projects


def _all_components(project):
    for phase in project.phases:
        for comp in phase.components:
            yield phase, comp


def _linked_children(project):
    return [c for _p, c in _all_components(project) if c.linked_with is not None]


def check_links_resolve(project, results):
    """1. Every child with a linked_with_uuid resolves to that template."""
    children = _linked_children(project)
    results.append(("1 has linked children", len(children) > 0))
    for comp in children:
        ok = comp.linked_with is not None and comp.linked_with.uuid == comp._linked_with_uuid
        results.append(("1 %-22s -> %s" % (comp.name, comp.linked_with.name), ok))


def check_read_through(project, results):
    """2. Inherited property reads equal the template's value."""
    for comp in _linked_children(project):
        tmpl = comp.linked_with
        for attr in _SCALARS:
            if comp.is_inherited(attr):
                ok = getattr(comp, attr) == getattr(tmpl, attr)
                results.append(("2 %s.%s == template" % (comp.name, attr), ok))
        for attr in _LISTS:
            if comp.is_inherited(attr):
                ok = getattr(comp, attr) is getattr(tmpl, attr) or \
                    getattr(comp, attr) == getattr(tmpl, attr)
                results.append(("2 %s.%s is template list" % (comp.name, attr), ok))


def check_selective(project, results):
    """3. A non-inherited scalar reads the child's OWN value. Proven strongest
    where the child's own value differs from the template's."""
    proven = False
    for comp in _linked_children(project):
        tmpl = comp.linked_with
        for attr in _SCALARS:
            if not comp.is_inherited(attr):
                own = getattr(comp, "_" + attr)
                ok = getattr(comp, attr) == own
                results.append(("3 %s.%s reads own" % (comp.name, attr), ok))
                if own != getattr(tmpl, attr):
                    proven = True
    # At least one linked child should keep an own value that differs from its
    # template (otherwise inheritance is indistinguishable from copying).
    results.append(("3 selective inheritance observed", proven))


def check_propagation(project, results):
    """4. Editing the template propagates to the child's inherited value."""
    done = False
    for comp in _linked_children(project):
        tmpl = comp.linked_with
        for attr in _SCALARS:
            if comp.is_inherited(attr) and tmpl is not comp:
                before = getattr(comp, attr)
                bumped = getattr(tmpl, "_" + attr) + 0.0125
                setattr(tmpl, attr, bumped)  # writes the template's own value
                after = getattr(comp, attr)
                setattr(tmpl, attr, before)  # restore
                restored = getattr(comp, attr)
                ok = (after == bumped) and (restored == before)
                results.append(("4 %s.%s follows template edit" % (comp.name, attr), ok))
                done = True
                break
        if done:
            break
    results.append(("4 propagation exercised", done))


def check_refinables_skip_inherited(project, results):
    """5. Inherited d001/delta_c are not independent refinables on the child."""
    checked = False
    for phase in project.phases:
        labels = {r.label for r in _phase_refinables(phase)}
        for comp in phase.components:
            for attr in ("d001", "delta_c"):
                label = "%s | %s | %s" % (phase.name, comp.name, attr)
                if comp.is_inherited(attr):
                    results.append(("5 skip %s|%s|%s" % (phase.name, comp.name, attr),
                                    label not in labels))
                    checked = True
                else:
                    results.append(("5 keep %s|%s|%s" % (phase.name, comp.name, attr),
                                    label in labels))
    results.append(("5 inherited-skip exercised", checked))


def check_roundtrip(path, results):
    """6. Save -> reload preserves the links and inherited values."""
    project = load_mud(path)
    before = {
        c.uuid: (c.linked_with.uuid, {a: getattr(c, a) for a in _SCALARS})
        for c in _linked_children(project)
    }
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_link_%d.mud" % os.getpid())
    try:
        save_mud(project, tmp)
        reloaded = load_mud(tmp)
        after = {c.uuid: c for c in _linked_children(reloaded)}
        results.append(("6 same # linked children", len(after) == len(before)))
        for uid, (tmpl_uuid, scalars) in before.items():
            comp = after.get(uid)
            ok = (comp is not None
                  and comp.linked_with is not None
                  and comp.linked_with.uuid == tmpl_uuid
                  and all(getattr(comp, a) == v for a, v in scalars.items()))
            results.append(("6 %-22s survives" % (comp.name if comp else uid), ok))
    finally:
        for p in (tmp, tmp + "~"):
            if os.path.exists(p):
                os.remove(p)


def run(path):
    print("=" * 72)
    print("Component linking:", os.path.basename(path))
    print("=" * 72)
    results = []
    project = load_mud(path)
    check_links_resolve(project, results)
    check_read_through(project, results)
    check_selective(project, results)
    check_propagation(project, results)
    check_refinables_skip_inherited(project, results)
    check_roundtrip(path, results)

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
        print("Looked for:", ", ".join(paths))
        return 2
    all_ok = True
    total = 0
    for path in existing:
        ok, n = run(path)
        all_ok = all_ok and ok
        total += n
        print()
    print("=" * 72)
    print("Component-linking harness: %d checks across %d project(s): %s"
          % (total, len(existing), "OK" if all_ok else "REGRESSION"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
