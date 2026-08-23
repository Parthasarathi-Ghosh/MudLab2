#!/usr/bin/env python
"""Batch 3 of snapshot-on-detach: Project.remove_phase bakes dependants.

Deleting a base phase used to silently shift every dependant's calculated
pattern (a variant based_on it, or a component linked to its components) once the
base had been edited. remove_phase now snapshots each dependant before severing,
so the patterns are preserved; a rare aliasing case (two components sharing one
template) is de-duplicated with fresh-uuid clones.

Checks:

  - after editing a base and then deleting it, a specimen that uses a DEPENDANT
    (not the base itself) keeps the SAME calculated pattern;
  - the dependants are detached (based_on / linked_with cleared);
  - synthetic aliasing: two components linked to the same template component end
    up with DISJOINT atoms and no duplicate atom uuids after the base is deleted.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_remove_phase_snapshot.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication

from mudlab.file_parsers.mud_project import load_mud
from mudlab.models.csds import DritsCSDSDistribution
from mudlab.models.phase import Phase

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _owner_map(project):
    return {id(c): ph for ph in project.phases for c in getattr(ph, "components", [])}


def _depends(D, B, b_comp_ids):
    if getattr(D, "based_on", None) is B:
        return True
    return any(c.linked_with is not None and id(c.linked_with) in b_comp_ids
               for c in getattr(D, "components", []))


def _find_base_dependent_specimen(project):
    """(base B, dependant D, mixture, specimen) where the specimen uses D but not
    B, so deleting B should leave that specimen's pattern untouched."""
    for B in project.phases:
        b_comp_ids = {id(c) for c in getattr(B, "components", [])}
        for D in project.phases:
            if D is B or not _depends(D, B, b_comp_ids):
                continue
            for mix in project.mixtures:
                for i, spec in enumerate(mix.specimens):
                    if spec is not None and D in mix.phase_matrix[i] \
                            and B not in mix.phase_matrix[i]:
                        return B, D, mix, spec
    return None, None, None, None


def _edit_base(B):
    """Perturb everything a dependant might inherit from B (phase params + its
    components' scalars), so a dependant that reverts on detach would shift."""
    B._sigma_star = B._sigma_star + 0.05
    B._CSDS = DritsCSDSDistribution(B.CSDS.average + 15.0)
    for row in B.probabilities.editable_params():
        row["set"](min(0.95, row["get"]() + 0.1))
    for c in getattr(B, "components", []):
        c._d001 += 0.30
        c._default_c += 0.30
        c._delta_c += 0.05
        c._lattice_d += 0.02
        c._ucp_a.value += 0.05
        c._ucp_b.value += 0.05


def _find_fixture():
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        if _find_base_dependent_specimen(load_mud(path))[0] is not None:
            return path
    return None


PATH = _find_fixture()
if PATH is None:
    print("No fixture with a base + dependant-only specimen; skipping (exit 2).")
    raise SystemExit(2)


def _delete_after_freeing(project, phase):
    """Delete `phase` the way the UI now requires.

    A phase a mixture still uses is refused outright, and in a real fixture
    almost every phase sits in one - so free its cells first. Mixture membership
    is orthogonal to what this harness tests (the inheritance / component-link
    cascade), and the specimen these checks watch never has `phase` in its row.
    """
    for mixture in project.mixtures:
        mixture.unset_phase(phase)
    removed = project.remove_phase(phase)
    check("setup: the freed phase %r deletes" % (phase.name,), removed is True)
    return removed


def check_preserves_pattern():
    project = load_mud(PATH)
    B, D, mix, spec = _find_base_dependent_specimen(project)
    print("fixture: %s  (base %r, dependant %r)"
          % (os.path.basename(PATH), B.name, D.name))
    mix.calculate()
    pre = spec.calculated_pattern[1].copy()
    _edit_base(B)
    mix.calculate()
    baseline = spec.calculated_pattern[1].copy()
    check("setup: editing the base moves the dependant's specimen pattern",
          not np.allclose(baseline, pre))

    _delete_after_freeing(project, B)
    mix.calculate()
    after = spec.calculated_pattern[1]
    check("remove_phase: dependant specimen pattern preserved (snapshot worked)",
          after.shape == baseline.shape and np.allclose(after, baseline))
    check("remove_phase: base removed from project", B not in project.phases)
    check("remove_phase: dependant based_on no longer points at the base",
          D.based_on is not B)
    b_comp_ids = {id(c) for c in getattr(B, "components", [])}
    check("remove_phase: dependant components no longer link the base",
          all(c.linked_with is None or id(c.linked_with) not in b_comp_ids
              for c in getattr(D, "components", [])))


def check_aliasing_dedup():
    project = load_mud(PATH)
    owner = _owner_map(project)
    # Find a cross-phase linked component and a second, different component we
    # can re-point at the SAME template component, to force aliasing.
    linker = None
    for ph in project.phases:
        for c in getattr(ph, "components", []):
            if c.linked_with is not None and c.inherit_layer_atoms:
                linker = c
                break
        if linker:
            break
    if linker is None:
        print("  (no linked component to build the aliasing case; skipped)")
        return
    template = linker.linked_with
    base_phase = owner[id(template)]
    # A second component in a different phase, not already the template/linker.
    second = None
    for ph in project.phases:
        if ph is base_phase:
            continue
        for c in getattr(ph, "components", []):
            if c is not linker and c is not template:
                second = c
                break
        if second:
            break
    if second is None or not second.set_linked_with(template):
        print("  (could not build a second linker; skipped aliasing check)")
        return
    second.inherit_layer_atoms = True
    second.inherit_interlayer_atoms = True

    _delete_after_freeing(project, base_phase)

    # NB: duplicate atom uuids across linked components are a benign, pre-existing
    # norm here (the old app inlined each linked copy keeping the template's
    # uuids). What must NOT happen is two live components sharing atom OBJECTS
    # (edit one, mutate the other) - the dedup reclones the second to prevent it.
    l_ids = {id(a) for a in linker._layer_atoms + linker._interlayer_atoms}
    s_ids = {id(a) for a in second._layer_atoms + second._interlayer_atoms}
    check("aliasing: the two ex-linkers no longer share atom objects",
          l_ids.isdisjoint(s_ids))
    l_uuids = {a.uuid for a in linker._layer_atoms + linker._interlayer_atoms}
    s_uuids = {a.uuid for a in second._layer_atoms + second._interlayer_atoms}
    check("aliasing: the recloned component got fresh atom uuids (no clash)",
          bool(s_uuids) and l_uuids.isdisjoint(s_uuids))


def check_midchain_deletion():
    """A<-B<-C: deleting the MIDDLE node B must keep C's transitively-resolved
    values (snapshot must read through B while its own based_on is still intact)."""
    project = load_mud(PATH)
    kids = [p for p in project.phases if isinstance(p, Phase) and p.based_on is not None]
    if len(kids) < 2:
        print("  (no two based_on children to build a mid-chain; skipped)")
        return
    B = kids[0]
    A = B.based_on
    C = kids[1]
    if not C.set_based_on(B):  # re-parent C onto B -> A <- B <- C
        print("  (could not build a 3-level chain; skipped)")
        return
    C.inherit_sigma_star = B.inherit_sigma_star = True
    A._sigma_star = 0.111  # a value distinct from B's / C's own
    before = C.sigma_star   # reads through B -> A
    _delete_after_freeing(project, B)  # delete the middle node
    check("mid-chain: deleting the middle node keeps C's resolved value",
          abs(C.sigma_star - before) < 1e-12 and C.based_on is not B)


def main():
    check_preserves_pattern()
    check_aliasing_dedup()
    check_midchain_deletion()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- remove_phase snapshot verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
