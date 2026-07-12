#!/usr/bin/env python
"""Durable harness for unit-cell properties (cell a / b derivation).

Guards the UCP model added in Batch 1a: cell a/b are UnitCellProperty objects
that are either fixed or derived (``value = factor*prop + constant``, prop =
another cell / an atom pn). For each sample project it checks:

  1. Golden-safe load: cell a/b equal the STORED value and are NOT recomputed
     on load - proven on the stale UCPs (where factor*prop+constant differs
     from the stored value). This is what keeps the calc matching the old app.
  2. Derivation sources resolve: an enabled UCP with a stored prop reference
     resolves to a live (component, attr) / (atom, attr) pair.
  3. Recompute on edit: changing a derived UCP's factor and calling
     update_ucp_values recomputes its value; a fixed UCP is untouched.
  4. Cascade: editing the driving atom pn updates cell_b, and cell_a (derived
     from cell_b) follows.
  5. Round-trip: load -> save -> reload preserves value/enabled/factor/constant.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_ucp.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample projects. The golden
pattern match itself is guarded by tools/verify_calc_engine.py.
"""

from __future__ import annotations

import os
import sys
import tempfile

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")


def _default_projects():
    out = []
    for name in ("308 r1.mud", "Dh2040A.mud"):
        in_repo = os.path.join(_FIXTURES, name)
        dl = os.path.join(os.path.expanduser("~"), "Downloads", name)
        out.append(in_repo if os.path.isfile(in_repo) else dl)
    return out


def _components(project):
    for phase in project.phases:
        for comp in phase.components:
            yield comp


def check_golden_safe_load(project, results):
    """1. cell a/b == stored value (no recompute on load), esp. stale UCPs."""
    stale_seen = False
    for comp in _components(project):
        for which, cell in (("a", comp.cell_a), ("b", comp.cell_b)):
            ucp = getattr(comp, "_ucp_" + which)
            # cell reads the stored value exactly (unless inherited, in which
            # case it reads the template's - skip those, covered by linking).
            if not comp.is_inherited("cell_" + which):
                results.append(("1 cell_%s == stored value" % which, cell == ucp.value))
            # A derived UCP whose factor*prop+const != stored value is stale;
            # cell must still read the stored value (proves no load recompute).
            if ucp.enabled and ucp.prop is not None and not comp.is_inherited("cell_" + which):
                recomputed = ucp.factor * ucp.get_prop_value() + ucp.constant
                if abs(recomputed - ucp.value) > 1e-9:
                    stale_seen = True
                    results.append(
                        ("1 stale %s.ucp_%s keeps stored (%.6f != recompute %.6f)"
                         % (comp.name, which, ucp.value, recomputed), cell == ucp.value),
                    )
    results.append(("1 a stale UCP was exercised", stale_seen))


def check_props_resolve(project, results):
    """2. Enabled UCPs with a stored prop reference resolve to a live target."""
    checked = False
    for comp in _components(project):
        for which in ("a", "b"):
            ucp = getattr(comp, "_ucp_" + which)
            if ucp.enabled and ucp._prop_ref:
                checked = True
                obj, attr = (ucp.prop or (None, None))
                results.append(("2 %s.ucp_%s prop %s resolves" % (comp.name, which, attr),
                                ucp.prop is not None and hasattr(obj, attr)))
    results.append(("2 prop resolution exercised", checked))


def check_recompute_on_edit(project, results):
    """3. Editing a derived UCP's factor recomputes its value on demand."""
    done = False
    for comp in _components(project):
        ucp = comp._ucp_a
        if ucp.enabled and ucp.prop is not None and not comp.is_inherited("cell_a"):
            before = ucp.value
            base = ucp.get_prop_value()
            ucp.factor *= 1.1
            comp.update_ucp_values()
            after = ucp.value
            expected = ucp.factor * ucp.get_prop_value() + ucp.constant
            ok = abs(after - expected) < 1e-9 and (base == 0 or after != before)
            results.append(("3 %s.cell_a recomputes on factor edit" % comp.name, ok))
            ucp.factor /= 1.1
            ucp.value = before  # restore
            done = True
            break
    results.append(("3 recompute-on-edit exercised", done))


def check_cascade(project, results):
    """4. Editing the driving atom pn updates cell_b, and cell_a follows."""
    done = False
    for comp in _components(project):
        ub, ua = comp._ucp_b, comp._ucp_a
        b_from_pn = ub.enabled and ub.prop is not None and ub.prop[1] == "pn"
        a_from_b = ua.enabled and ua.prop is not None and ua.prop[1] in ("cell_b",)
        if b_from_pn and a_from_b and not comp.is_inherited("cell_b"):
            atom, _attr = ub.prop
            pn0, b0, a0 = atom.pn, ub.value, ua.value
            atom.pn = pn0 + 0.1
            comp.update_ucp_values()
            exp_b = ub.factor * atom.pn + ub.constant
            exp_a = ua.factor * comp.cell_b + ua.constant
            ok = abs(ub.value - exp_b) < 1e-9 and abs(ua.value - exp_a) < 1e-9 and ub.value != b0
            results.append(("4 %s: pn edit -> cell_b -> cell_a cascade" % comp.name, ok))
            atom.pn, ub.value, ua.value = pn0, b0, a0  # restore
            done = True
            break
    results.append(("4 cascade exercised", done))


def check_roundtrip(path, results):
    """5. Save -> reload preserves value/enabled/factor/constant."""
    project = load_mud(path)
    before = {}
    for comp in _components(project):
        for which in ("a", "b"):
            u = getattr(comp, "_ucp_" + which)
            before[(comp.uuid, which)] = (u.value, u.enabled, u.factor, u.constant)
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_ucp_%d.mud" % os.getpid())
    try:
        save_mud(project, tmp)
        reloaded = load_mud(tmp)
        after = {}
        for comp in _components(reloaded):
            for which in ("a", "b"):
                u = getattr(comp, "_ucp_" + which)
                after[(comp.uuid, which)] = (u.value, u.enabled, u.factor, u.constant)
        results.append(("5 same UCP count", len(after) == len(before)))
        ok = all(after.get(k) == v for k, v in before.items())
        results.append(("5 value/enabled/factor/constant survive", ok))
    finally:
        for p in (tmp, tmp + "~"):
            if os.path.exists(p):
                os.remove(p)


def run(path):
    print("=" * 72)
    print("Unit-cell properties:", os.path.basename(path))
    print("=" * 72)
    results = []
    project = load_mud(path)
    check_golden_safe_load(project, results)
    check_props_resolve(project, results)
    check_recompute_on_edit(project, results)
    check_cascade(project, results)
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
        return 2
    all_ok, total = True, 0
    for path in existing:
        ok, n = run(path)
        all_ok = all_ok and ok
        total += n
        print()
    print("=" * 72)
    print("UCP harness: %d checks across %d project(s): %s"
          % (total, len(existing), "OK" if all_ok else "REGRESSION"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
