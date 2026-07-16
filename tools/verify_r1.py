#!/usr/bin/env python
"""Durable harness for R1 (Reichweite-1) stacking - Batch R1a.

R1 = each layer depends on the one immediately before it, so the junction
matrix P has DIFFERENT rows (R0's are all identical). The intensity summation
was already R-agnostic; R1a adds the R1G2 probability MODEL that produces the
R1 W/P matrices, plus dispatch and per-parameter inheritance.

The golden-calc integration proof lives in verify_calc_engine.py (Dh537A.mud:
the R0-fallback failed it at corr 0.984, the R1G2 model reproduces it at
corr 1.000000). This harness guards the R1 model INTERNALS that the golden
calc alone would not localise:

  1. dispatch - an R1G2Model dict loads as R1G2Probability, not R0;
  2. analytic matrices - W and P match the old R1G2Model.update formula for
     the stored parameters, re-derived here independently;
  3. it is genuinely R1 - the P rows differ (an R0 collapse would make them
     equal), and detailed balance holds (Wi*Pij == Wj*Pji);
  4. inheritance - the treated phases read W1/P11 through to their based_on
     parent, and a change to the parent is picked up;
  5. discrimination - an R0 model with the same weights produces a DIFFERENT
     P, so the fixture can actually detect a broken R1 port (guards against
     it silently degrading to the non-discriminating case);
  6. round-trip - the R1 probabilities survive save/reload byte-identical
     (currently via the verbatim raw passthrough; R1b models the write-back).

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_r1.py

Exit codes: 0 = all pass, 1 = a regression, 2 = the R1 fixture is absent.
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.models.probabilities import (  # noqa: E402
    R0Probability, R1G2Probability, probabilities_from_dict,
)

_app = QApplication.instance() or QApplication([])
_FIXTURE = "Dh537A.mud"


def _fixture_path():
    for base in (os.path.join(_REPO, "tools", "sample_projects"),
                 os.path.join(os.path.expanduser("~"), "Downloads")):
        path = os.path.join(base, _FIXTURE)
        if os.path.isfile(path):
            return path
    return None


def _r1_g2_reference(w1, p):
    """The old R1G2Model.update, re-implemented here as an INDEPENDENT
    reference (do not import the model's own _pmatrix)."""
    w2 = 1.0 - w1
    mP = [[0.0, 0.0], [0.0, 0.0]]
    if w1 <= 0.5:
        mP[0][0] = p
        mP[0][1] = 1.0 - mP[0][0]
        mP[1][0] = w1 * mP[0][1] / w2
        mP[1][1] = 1.0 - mP[1][0]
    else:
        mP[1][1] = p
        mP[1][0] = 1.0 - mP[1][1]
        mP[0][1] = w2 * mP[1][0] / w1
        mP[0][0] = 1.0 - mP[0][1]
    return np.array([w1, w2]), np.array(mP)


def _r1_phases(project):
    return [p for p in project.phases
            if isinstance(p.probabilities, R1G2Probability)]


def check_dispatch(project, results):
    """1. R1G2Model dicts load as R1G2Probability."""
    r1 = _r1_phases(project)
    results.append(("1 fixture has R1G2 phases", len(r1) >= 1))
    results.append(("1 R1 phases carry R=1",
                    all(p.probabilities.R == 1 for p in r1)))
    # A stray R1G2 dict must not fall back to R0.
    m = probabilities_from_dict(
        {"type": "R1G2Model", "properties": {"W1": 0.3, "P11_or_P22": 0.6}}, 2)
    results.append(("1 dispatch picks R1G2Probability",
                    isinstance(m, R1G2Probability)))


def check_analytic_matrices(project, results):
    """2/3. W and P match the independent formula; P is genuinely R1."""
    for phase in _r1_phases(project):
        pr = phase.probabilities
        w1, p = pr.w1_value(), pr.p11_value()
        W_ref, P_ref = _r1_g2_reference(w1, p)
        W = pr.get_distribution_array()
        P = pr.get_probability_matrix()
        results.append(("2 %s: W matches formula" % phase.name,
                        np.allclose(W, W_ref, atol=1e-12)))
        results.append(("2 %s: P matches formula" % phase.name,
                        np.allclose(P, P_ref, atol=1e-12)))
        # Genuinely R1: the two rows of P differ (equal rows == R0 collapse).
        results.append(("3 %s: P rows differ (real R1, not R0)" % phase.name,
                        not np.allclose(P[0], P[1], atol=1e-9)))
        # Detailed balance: W0*P01 == W1*P10.
        results.append(("3 %s: detailed balance holds" % phase.name,
                        abs(W[0] * P[0, 1] - W[1] * P[1, 0]) < 1e-12))
        # P rows are stochastic and the model reports valid.
        results.append(("3 %s: P rows stochastic + valid" % phase.name,
                        np.allclose(P.sum(axis=1), 1.0) and pr.valid))


def check_inheritance(project, results):
    """4. Treated phases read W1/P11 through to their based_on parent."""
    for phase in _r1_phases(project):
        pr = phase.probabilities
        if phase.based_on is None:
            continue
        parent = phase.based_on.probabilities
        if pr.inherit_W1:
            results.append(("4 %s: W1 reads through to parent" % phase.name,
                            abs(pr.w1_value() - parent.w1_value()) < 1e-12))
            # ... and it is a READ-THROUGH, not a copy of the stored own value.
            if abs(pr.W1 - parent.w1_value()) > 1e-9:
                results.append(("4 %s: inherited W1 != its own stale value "
                                "(proves read-through)" % phase.name,
                                abs(pr.w1_value() - pr.W1) > 1e-9))
        if pr.inherit_P11_or_P22:
            results.append(("4 %s: P11 reads through to parent" % phase.name,
                            abs(pr.p11_value() - parent.p11_value()) < 1e-12))

    # A parent edit propagates to the inheritors at once.
    parents = [p for p in _r1_phases(project)
               if any(o.based_on is p for o in _r1_phases(project))]
    if parents:
        parent = parents[0]
        deps = [o for o in _r1_phases(project)
                if o.based_on is parent and o.probabilities.inherit_W1]
        if deps:
            before = [d.probabilities.w1_value() for d in deps]
            parent.probabilities.W1 = parent.probabilities.W1 * 0.5
            after = [d.probabilities.w1_value() for d in deps]
            results.append(("4 a parent W1 edit propagates to inheritors",
                            all(abs(a - parent.probabilities.w1_value()) < 1e-12
                                for a in after) and before != after))
            parent.probabilities.W1 = parent.probabilities.W1 * 2.0  # restore


def check_discrimination(project, results):
    """5. An R0 model with the same weights gives a DIFFERENT P - so R1
    genuinely matters and the fixture can detect a broken port."""
    for phase in _r1_phases(project):
        pr = phase.probabilities
        w1 = pr.w1_value()
        r0 = R0Probability(2, [w1])  # F1 = W1: the closest R0 with this weight
        P_r1 = pr.get_probability_matrix()
        P_r0 = r0.get_probability_matrix()
        results.append(("5 %s: R1 P differs from the R0 collapse" % phase.name,
                        not np.allclose(P_r1, P_r0, atol=1e-6)))


def check_edit_persists(path, results):
    """7 (R1b). An edited W1 / P11 survives save/reload.

    Until R1b the R1 dict round-tripped verbatim, so an edit was silently
    lost. to_dict now writes each model's OWN modeled params back, so an edit
    persists AND a loaded (unedited) project stays byte-identical.
    """
    project = load_mud(path)
    r1 = _r1_phases(project)
    # Edit a phase that owns its W1 (not inheriting), so the edit is its own.
    owner = next((p for p in r1 if not p.probabilities.inherit_W1), r1[0])
    name = owner.name
    owner.probabilities.W1 = 0.4237
    owner.probabilities.P11_or_P22 = 0.1234

    tmp = os.path.join(tempfile.gettempdir(), "mudlab_r1_edit.mud")
    try:
        save_mud(project, tmp)
        reloaded = load_mud(tmp)
        r = next(p for p in reloaded.phases if p.name == name)
        results.append(("7 edited W1 persists (%.4f)" % r.probabilities.W1,
                        abs(r.probabilities.W1 - 0.4237) < 1e-9))
        results.append(("7 edited P11 persists (%.4f)" % r.probabilities.P11_or_P22,
                        abs(r.probabilities.P11_or_P22 - 0.1234) < 1e-9))
        # The recomputed matrix reflects the edit (0.4237 < 0.5 -> IF branch,
        # so this ALSO exercises the branch the fixture otherwise never hits).
        _, P_ref = _r1_g2_reference(0.4237, 0.1234)
        results.append(("7 P matrix reflects the edited params",
                        np.allclose(r.probabilities.get_probability_matrix(),
                                    P_ref, atol=1e-12)))
    finally:
        for p in (tmp, tmp + "~"):
            if os.path.exists(p):
                os.remove(p)


def check_detach_clears_flags(project, results):
    """8 (R1b). Detaching an R1 child clears its R1 inherit flags.

    Regression guard: Phase.set_based_on(None) used to set inherit_F on the
    model - a no-op stray attribute on R1G2Probability - and left the real
    inherit_W1 / inherit_P11_or_P22 flags set, so a detached R1 child kept
    reading through to a parent it no longer had.
    """
    r1 = _r1_phases(project)
    child = next(
        (p for p in r1 if p.based_on is not None
         and (p.probabilities.inherit_W1 or p.probabilities.inherit_P11_or_P22)),
        None,
    )
    if child is None:
        return
    own_w1_before = child.probabilities.W1
    child.set_based_on(None)
    results.append(("8 detach drops based_on", child.based_on is None))
    results.append(("8 detach clears inherit_W1",
                    not child.probabilities.inherit_W1))
    results.append(("8 detach clears inherit_P11_or_P22",
                    not child.probabilities.inherit_P11_or_P22))
    # With nothing to read through to, the effective value is its own again.
    results.append(("8 detached child reads its OWN W1",
                    abs(child.probabilities.w1_value() - own_w1_before) < 1e-12))


def check_refinement(path, results):
    """9 (R1c-1). The refiner enumerates R1 params (W1 / P11), skips the
    inherited ones, and a flagged R1 param actually moves the fit."""
    from mudlab.calculations.refinement import enumerate_refinables

    project = load_mud(path)
    if not project.mixtures:
        return
    mixture = project.mixtures[0]
    labels = [r.label for r in enumerate_refinables(mixture)]
    r1 = _r1_phases(project)
    # The non-inheriting R1 phase must contribute W1 and P11 as refinables.
    owner = next((p for p in r1 if not p.probabilities.inherit_W1), None)
    if owner is not None:
        results.append(("9 %s | W1 is refinable" % owner.name,
                        "%s | W1" % owner.name in labels))
        results.append(("9 %s | P11_or_P22 is refinable" % owner.name,
                        "%s | P11_or_P22" % owner.name in labels))
    # An inheriting R1 phase must NOT (its W1/P11 read through to the parent).
    inh = next((p for p in r1 if p.probabilities.inherit_W1), None)
    if inh is not None:
        results.append(("9 inherited %s | W1 is NOT refinable" % inh.name,
                        "%s | W1" % inh.name not in labels))

    # Refining a flagged R1 param must be able to move the residual.
    refs = enumerate_refinables(mixture)
    target = next((r for r in refs if r.label.endswith("| W1")), None)
    if target is not None:
        base = mixture.current_residual()
        v0 = target.value
        target.value = min(max(v0 * 1.1, 0.01), 0.99)
        moved = mixture.current_residual()
        target.value = v0
        results.append(("9 residual responds to an R1 W1 (%.4f -> %.4f)"
                        % (base, moved), abs(moved - base) > 1e-9))
        results.append(("9 restoring W1 restores the residual",
                        abs(mixture.current_residual() - base) < 1e-9))


def check_roundtrip(path, results):
    """6. R1 probabilities survive save/reload byte-identical."""
    def _phase_probs(mud_path):
        z = zipfile.ZipFile(mud_path)
        data = json.loads(z.read("phases").decode("utf-8"))
        items = data if isinstance(data, list) else [data]
        return {
            it["properties"]["name"]: it["properties"].get("probabilities")
            for it in items if isinstance(it, dict)
        }

    project = load_mud(path)
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_r1_rt.mud")
    try:
        save_mud(project, tmp)
        before, after = _phase_probs(path), _phase_probs(tmp)
        for name, probs in before.items():
            if isinstance(probs, dict) and probs.get("type", "").startswith("R1"):
                results.append(("6 %s: R1 probs byte-identical after reload"
                                % name, before[name] == after[name]))
    finally:
        for p in (tmp, tmp + "~"):
            if os.path.exists(p):
                os.remove(p)


def check_unit_matrix_math(results):
    """2b. Spot-check both branches (W1<=0.5 and W1>0.5) on synthetic values.

    Load-bearing: every R1 phase in Dh537A has W1 ~ 0.73, so the golden calc
    only ever exercises the W1>0.5 branch. The W1<=0.5 branch (P11 free, P22
    derived) is guarded ONLY by the synthetic W1=0.30 case here - without it a
    bug in that branch would pass every fixture check.
    """
    for w1, p in ((0.3, 0.6), (0.75, 0.5)):
        pr = R1G2Probability(W1=w1, P11_or_P22=p)
        W_ref, P_ref = _r1_g2_reference(w1, p)
        ok = (np.allclose(pr.get_distribution_array(), W_ref, atol=1e-12)
              and np.allclose(pr.get_probability_matrix(), P_ref, atol=1e-12))
        results.append(("2b synthetic W1=%.2f P=%.2f matches formula"
                        % (w1, p), ok))
    # A degenerate weight must not divide-by-zero.
    edge = R1G2Probability(W1=1.0, P11_or_P22=0.5)
    results.append(("2b W1=1.0 does not blow up",
                    np.all(np.isfinite(edge.get_probability_matrix()))))


def run(path):
    print("=" * 72)
    print("R1 stacking:", os.path.basename(path))
    print("=" * 72)
    results = []
    project = load_mud(path)
    check_dispatch(project, results)
    check_analytic_matrices(project, results)
    check_unit_matrix_math(results)
    check_inheritance(project, results)
    check_discrimination(project, results)
    check_roundtrip(path, results)
    check_edit_persists(path, results)
    check_detach_clears_flags(load_mud(path), results)
    check_refinement(path, results)
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("%d/%d checks passed" % (passed, len(results)))
    return passed == len(results), len(results)


def main(argv):
    path = argv[1] if len(argv) > 1 else _fixture_path()
    if not path or not os.path.isfile(path):
        print("R1 fixture (%s) not found; skipping (exit 2)." % _FIXTURE)
        return 2
    ok, total = run(path)
    print("=" * 72)
    print("R1 harness: %d checks: %s" % (total, "OK" if ok else "REGRESSION"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
