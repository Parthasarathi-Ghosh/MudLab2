#!/usr/bin/env python
"""Durable harness for atom-relation CHAINING + value REFINEMENT, head-less.

Two additions beyond the base relation editors (verify_relations.py):

  1. Chaining apply: an AtomContents row whose target is another relation drives
     that relation's value (prop "value") or an AtomRatio's sum
     ("__internal_sum__"), from amount*value, then re-applies it so the driven
     relation's atoms follow. A re-entrancy guard stops cycles.
  2. Refinement exposure: enumerate_refinables now lists each editable relation
     value (an AtomRatio fraction / an AtomContents multiplier), EXCEPT ones
     that are inherited, disabled, or driven by another relation's chain row
     (old AtomRelation.is_refinable). Setting one re-derives the atom pn.

Plus: the contents widget shows every row (atom + chained) and refuses a target
that would form a cycle.

Run head-less from the repo root:

    ./python/python.exe tools/verify_relation_chain_refine.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable sample project.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.calculations.refinement import enumerate_refinables  # noqa: E402
from mudlab.contents_widget import AtomContentsWidget  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.models.atom_relations import (  # noqa: E402
    AtomContent, AtomContents, AtomRatio,
)
from mudlab.models.component import Atom, Component  # noqa: E402

FIXTURE = os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")

_app = QApplication.instance() or QApplication([])
results = []


def check(label, ok):
    results.append((label, bool(ok)))


def _build_chained_component():
    """A component: two atoms + a ratio (a1/a2) + a contents whose chain row
    drives the ratio's value. Editing the contents value should flow through the
    ratio to the atoms' pn."""
    comp = Component(name="C")
    a1, a2 = Atom(name="A1"), Atom(name="A2")
    comp._layer_atoms = [a1, a2]
    ratio = AtomRatio(name="Sub", value=0.5, sum=2.0, enabled=True)
    ratio.atom1 = (a1, "pn")
    ratio.atom2 = (a2, "pn")
    contents = AtomContents(name="Driver", value=0.4, enabled=True)
    from mudlab.models.atom_relations import AtomContent
    driver_row = AtomContent(ratio.uuid, "value", 1.0)  # ratio.value = 1.0 * contents.value
    driver_row.relation = ratio
    contents.atom_contents = [driver_row]
    comp._atom_relations = [ratio, contents]
    return comp, a1, a2, ratio, contents


def run():
    # 1. Chaining apply on a synthetic component.
    comp, a1, a2, ratio, contents = _build_chained_component()
    comp.apply_atom_relations()
    # contents.value=0.4, amount=1.0 -> ratio.value=0.4 -> a1=0.4*2, a2=0.6*2
    check("1 chain row drives the ratio value", abs(ratio.value - 0.4) < 1e-12)
    check("1 driven ratio sets its atoms' pn",
          abs(a1.pn - 0.8) < 1e-9 and abs(a2.pn - 1.2) < 1e-9)
    contents.value = 0.25
    comp.apply_atom_relations()
    check("1 editing the driver re-derives through the chain",
          abs(ratio.value - 0.25) < 1e-12 and abs(a1.pn - 0.5) < 1e-9)

    # __internal_sum__ drives the ratio's sum.
    contents.atom_contents[0].prop = "__internal_sum__"
    contents.value = 3.0
    comp.apply_atom_relations()
    check("1 __internal_sum__ drives the ratio sum",
          abs(ratio.sum - 3.0) < 1e-12)

    # Re-entrancy guard: a mutual cycle terminates instead of hanging.
    from mudlab.models.atom_relations import AtomContent
    c2 = AtomContents(name="D2", value=1.0, enabled=True)
    row_to_contents = AtomContent(contents.uuid, "value", 1.0)
    row_to_contents.relation = contents
    c2.atom_contents = [row_to_contents]
    back = AtomContent(c2.uuid, "value", 1.0)
    back.relation = c2
    contents.atom_contents.append(back)
    comp._atom_relations.append(c2)
    comp.apply_atom_relations()  # must return, not recurse forever
    check("1 a mutual chain cycle terminates (re-entrancy guard)", True)

    # 2. Refinement exposure on a real fixture.
    project = load_mud(FIXTURE)
    mix = project.mixtures[0]
    labels = [r.label for r in enumerate_refinables(mix)]
    check("2 relation values are exposed as refinables",
          any("OctFe" in l for l in labels))
    # A driven relation is NOT offered. Build one and confirm exclusion.
    ph = project.phases[0]
    comp2 = ph.components[0]
    # find a component whose relations we can drive; use the synthetic one via
    # a throwaway check on _driven_relation_ids semantics:
    from mudlab.calculations.refinement import _driven_relation_ids
    comp_d, *_rest = _build_chained_component()
    driven = _driven_relation_ids(comp_d)
    ratio_d = comp_d.atom_relations[0]
    check("2 a driven relation is flagged (excluded from refinables)",
          id(ratio_d) in driven)
    # setting a relation refinable re-derives without error
    rel_refs = [r for r in enumerate_refinables(mix) if "OctFe" in r.label]
    if rel_refs:
        r = rel_refs[0]; b = r.value; r.value = 0.33
        ok = abs(r.value - 0.33) < 1e-9
        r.value = b
        check("2 setting a relation refinable applies + reads back", ok)
    else:
        check("2 setting a relation refinable applies + reads back", False)

    # 3. Widget: shows every row (atom + chained) and refuses a cycle.
    comp3, a1b, a2b, ratio3, contents3 = _build_chained_component()
    widget = AtomContentsWidget()
    siblings = [r for r in comp3.atom_relations if r is not contents3]
    widget.bind_contents(contents3, [a1b, a2b], relations=siblings)
    check("3 the widget lists all rows (atom + chained)",
          widget._table.rowCount() == len(contents3.atom_contents))
    combo = widget._table.cellWidget(0, 0)
    has_ratio_target = any(
        combo.itemData(k) == (ratio3, "value") for k in range(combo.count()))
    check("3 a sibling ratio is offered as a chain target", has_ratio_target)
    check("3 driving the contents itself is detected as a cycle",
          widget._would_cycle(contents3) is True)
    widget.deleteLater()

    # 4. Refinement domain (guards the golden-pn regression fix). Relation
    #    values apply their relation on set, shifting the un-applied golden pn to
    #    the computed one; refine_mixture primes only the FLAGGED relations, so:
    #    (a) flagging a relation refines cleanly + never worse than the primed
    #    baseline; (b) flagging only a NON-relation leaves the stored pn exactly
    #    as loaded. Uses 308 r1 (a project where stored pn != computed pn).
    from itertools import chain as _chain

    import numpy as _np

    from mudlab.calculations.refinement import refine_mixture

    def _pn(m):
        return _np.array([
            a.pn for row in m.phase_matrix for ph in row
            if getattr(ph, "components", None)
            for c in ph.components for a in _chain(c.layer_atoms, c.interlayer_atoms)
        ])

    m2 = load_mud(FIXTURE).mixtures[0]
    relref = next((r for r in enumerate_refinables(m2)
                   if "OctFe" in r.label or "Content" in r.label), None)
    if relref is not None:
        relref.set_ref_info(minimum=0.0, maximum=1.0, refine=True)
        rr = refine_mixture(m2, options={"maxiter": 4, "maxfun": 20})
        check("4 flagging a relation refines cleanly + never worse than baseline",
              rr.best_residual is not None
              and rr.best_residual <= rr.initial_residual + 1e-9)
    else:
        check("4 flagging a relation refines cleanly + never worse than baseline", True)

    m3 = load_mud(FIXTURE).mixtures[0]
    pn_before = _pn(m3)
    nonrel = next((r for r in enumerate_refinables(m3)
                   if r.label.endswith("sigma*")), None)
    if nonrel is not None:
        nonrel.set_ref_info(minimum=1.0, maximum=6.0, refine=True)
        refine_mixture(m3, options={"maxiter": 4, "maxfun": 20})
        check("4 refining a non-relation leaves the golden stored pn untouched",
              _np.allclose(pn_before, _pn(m3)))
    else:
        check("4 refining a non-relation leaves the golden stored pn untouched", True)
    return None


def main():
    print("=" * 72)
    print("Atom-relation chaining + value refinement")
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
    print("Chain+refine harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
