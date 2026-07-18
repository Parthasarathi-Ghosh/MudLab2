#!/usr/bin/env python
"""Durable harness for R2 (Reichweite-2) stacking - the R2G2 model.

R2 = a layer depends on the TWO before it, so the state is a pair of layers
and the W / P matrices are g²xg² = 4x4. This is the first model that exercises
the calc's reps>1 path (reps = 4 // 2 = 2); the golden-calc integration proof
lives in verify_calc_engine.py (Illite-Smectite R2 G2[.mud / MPDO], which
reproduce at corr 1.000000). This harness guards the R2G2 MODEL internals:

  1. dispatch - an R2G2Model dict loads as R2G2Probability (not refused);
  2. analytic matrices - W (4x4 diagonal pair-weights) and P (4x4) match an
     INDEPENDENT re-derivation of R2G2Model.update, for the fixture's params
     and for synthetic values covering both if/else branches;
  3. it is genuinely R2 - P has the block-sparse pair structure (a transition
     from state (i,j) is only allowed to (j,k)), rows are stochastic, and the
     weights are a valid stationary distribution;
  4. inheritance - each of the 4 params reads through to a based_on model
     (tested synthetically: the fixture is single-phase);
  5. round-trip - the R2G2 probabilities survive save/reload byte-identical,
     and an edited parameter persists.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_r2.py

Exit codes: 0 = all pass, 1 = a regression, 2 = the R2G2 fixture is absent.
"""

from __future__ import annotations

import json
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
    R2G2Probability, probabilities_from_dict,
)

_app = QApplication.instance() or QApplication([])
_FIXTURE = "Illite-Smectite R2 G2.mud"


def _fixture_path():
    for base in (os.path.join(_REPO, "tools", "sample_projects"),
                 os.path.join(os.path.expanduser("~"), "Downloads", "PyXRD test projects")):
        path = os.path.join(base, _FIXTURE)
        if os.path.isfile(path):
            return path
    return None


def _reference_matrices(W1, P112_or_P211, P21, P122_or_P221):
    """Independent re-derivation of R2G2Model.update (do NOT call the model's
    own _matrices). Returns (W diag vector, P 4x4)."""
    W2 = 1.0 - W1
    P22 = 1.0 - P21
    W10 = W2 * P21
    W11 = W2 * P22
    W01 = W10
    W00 = W1 - W10
    if W1 <= 2.0 / 3.0:
        P001 = P112_or_P211
        P100 = (P001 * W00 / W10) if W10 != 0 else 0.0
    else:
        P100 = P112_or_P211
        P001 = (P100 * W10 / W00) if W00 != 0 else 0.0
    P101, P000 = 1.0 - P100, 1.0 - P001
    if P21 <= 0.5:
        P011 = P122_or_P221
        P110 = (P011 * W01 / W11) if W11 != 0 else 0.0
    else:
        P110 = P122_or_P221
        P011 = (P110 * W11 / W01) if W01 != 0 else 0.0
    P010, P111 = 1.0 - P011, 1.0 - P110
    w = np.array([W00, W01, W10, W11])
    P = np.array([[P000, P001, 0, 0], [0, 0, P010, P011],
                  [P100, P101, 0, 0], [0, 0, P110, P111]], dtype=float)
    return w, P


def _r2_phase(project):
    for phase in project.phases:
        if isinstance(phase.probabilities, R2G2Probability):
            return phase
    return None


def check_dispatch(project, results):
    """1. R2G2Model dicts load as R2G2Probability."""
    phase = _r2_phase(project)
    results.append(("1 fixture has an R2G2 phase", phase is not None))
    if phase is not None:
        results.append(("1 R2G2 carries G=2, R=2, 4 independents",
                        phase.probabilities.G == 2 and phase.probabilities.R == 2
                        and phase.probabilities.n_independents == 4))
    m = probabilities_from_dict(
        {"type": "R2G2Model", "properties": {"W1": 0.6}}, 2)
    results.append(("1 dispatch picks R2G2Probability",
                    isinstance(m, R2G2Probability)))


def check_matrices(project, results):
    """2/3. W and P match the independent re-derivation; structure is real R2."""
    phase = _r2_phase(project)
    if phase is None:
        return
    pr = phase.probabilities
    w_ref, P_ref = _reference_matrices(
        pr.value("W1"), pr.value("P112_or_P211"),
        pr.value("P21"), pr.value("P122_or_P221"))
    W = pr.get_distribution_array()
    P = pr.get_probability_matrix()
    results.append(("2 fixture: W matches the formula",
                    np.allclose(W, w_ref, atol=1e-12)))
    results.append(("2 fixture: P (4x4) matches the formula",
                    P.shape == (4, 4) and np.allclose(P, P_ref, atol=1e-12)))
    # Block-sparse pair structure: from state x=2i+j, only cols 2j+0 / 2j+1 may
    # be nonzero (the middle layer must carry over).
    ok_struct = True
    for i in range(2):
        for j in range(2):
            x = 2 * i + j
            allowed = {2 * j + 0, 2 * j + 1}
            for col in range(4):
                if col not in allowed and P[x, col] != 0.0:
                    ok_struct = False
    results.append(("3 P has the R2 pair structure (block-sparse)", ok_struct))
    results.append(("3 W is a valid stationary distribution + P stochastic",
                    abs(np.diag(pr.get_distribution_matrix()).sum() - 1.0) < 1e-12
                    and np.allclose(P.sum(axis=1), 1.0) and pr.valid))
    results.append(("3 rank 4 -> the calc's reps = rank // G = 2",
                    P.shape[0] // pr.G == 2))


def check_synthetic_branches(results):
    """2b. Both if/else branches (W1<=>2/3, P21<=>1/2) match the formula, and
    the edge params that appear in the fixture do not divide by zero."""
    for (w1, p112, p21, p122) in [
        (0.6, 0.5, 1.0, 0.0),      # the fixture (W1<=2/3, P21>1/2, W11=0)
        (0.8, 0.3, 0.25, 0.7),     # W1>2/3, P21<=1/2
        (0.55, 0.9, 0.9, 0.1),     # W1<=2/3, P21>1/2
        (0.9, 0.1, 0.4, 0.9),      # W1>2/3, P21<=1/2
    ]:
        m = R2G2Probability(W1=w1, P112_or_P211=p112, P21=p21, P122_or_P221=p122)
        w_ref, P_ref = _reference_matrices(w1, p112, p21, p122)
        W = m.get_distribution_array()
        P = m.get_probability_matrix()
        ok = (np.allclose(W, w_ref, atol=1e-12)
              and np.allclose(P, P_ref, atol=1e-12)
              and np.all(np.isfinite(P)))
        results.append(("2b W1=%.2f P21=%.2f matches formula (finite)"
                        % (w1, p21), ok))


def check_inheritance(results):
    """4. Each parameter reads through to a based_on model (synthetic: the
    fixture is single-phase)."""
    parent = R2G2Probability(W1=0.62, P112_or_P211=0.4, P21=0.3, P122_or_P221=0.8)
    child = R2G2Probability(W1=0.9, P112_or_P211=0.9, P21=0.9, P122_or_P221=0.9,
                            inherit_W1=True, inherit_P21=True)
    child.set_based_on(parent)
    results.append(("4 inherited W1 reads the parent value",
                    abs(child.value("W1") - 0.62) < 1e-12
                    and abs(child.value("W1") - child.W1) > 1e-9))
    results.append(("4 inherited P21 reads the parent value",
                    abs(child.value("P21") - 0.3) < 1e-12))
    results.append(("4 non-inherited P112 keeps its own value",
                    abs(child.value("P112_or_P211") - 0.9) < 1e-12))
    # A parent edit propagates.
    parent.W1 = 0.55
    results.append(("4 a parent W1 edit propagates to the child",
                    abs(child.value("W1") - 0.55) < 1e-12))
    # Detach clears the R2 flags.
    child.clear_inheritance()
    results.append(("4 clear_inheritance drops the flags -> own value",
                    not child.inherit_W1 and abs(child.value("W1") - 0.9) < 1e-12))


def check_refinement_and_editor(project, results):
    """4b. The refiner and editor enumerate the 4 R2 params."""
    from mudlab.calculations.refinement import enumerate_refinables

    phase = _r2_phase(project)
    if phase is None or not project.mixtures:
        return
    labels = [r.label for r in enumerate_refinables(project.mixtures[0])]
    for p in ("W1", "P112 / P211", "P21", "P122 / P221"):
        results.append(("4b refinable: %s | %s" % (phase.name, p),
                        "%s | %s" % (phase.name, p) in labels))
    specs = phase.probabilities.editable_params()
    results.append(("4b editor shows the 4 R2 params",
                    [s["label"] for s in specs]
                    == ["W1", "P112 / P211", "P21", "P122 / P221"]))


def check_roundtrip(path, results):
    """5. R2G2 probabilities byte-identical through save/reload; an edit
    persists."""
    def _probs(mud):
        z = zipfile.ZipFile(mud)
        data = json.loads(z.read("phases").decode("utf-8"))
        items = data if isinstance(data, list) else [data]
        return {it["properties"]["name"]: it["properties"].get("probabilities")
                for it in items if isinstance(it, dict)}

    project = load_mud(path)
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_r2_rt.mud")
    try:
        save_mud(project, tmp)
        before, after = _probs(path), _probs(tmp)
        for name, probs in before.items():
            if isinstance(probs, dict) and probs.get("type") == "R2G2Model":
                results.append(("5 %s: R2G2 probs byte-identical after reload"
                                % name, before[name] == after[name]))
        # Edit persists.
        project2 = load_mud(path)
        p2 = _r2_phase(project2)
        p2.probabilities.W1 = 0.66
        p2.probabilities.P21 = 0.33
        save_mud(project2, tmp)
        reloaded = _r2_phase(load_mud(tmp))
        results.append(("5 edited W1/P21 persist",
                        abs(reloaded.probabilities.W1 - 0.66) < 1e-9
                        and abs(reloaded.probabilities.P21 - 0.33) < 1e-9))
    finally:
        for p in (tmp, tmp + "~"):
            if os.path.exists(p):
                os.remove(p)


def run(path):
    print("=" * 72)
    print("R2 stacking:", os.path.basename(path))
    print("=" * 72)
    results = []
    project = load_mud(path)
    check_dispatch(project, results)
    check_matrices(project, results)
    check_synthetic_branches(results)
    check_inheritance(results)
    check_refinement_and_editor(project, results)
    check_roundtrip(path, results)
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
        print("R2G2 fixture (%s) not found; skipping (exit 2)." % _FIXTURE)
        return 2
    ok, total = run(path)
    print("=" * 72)
    print("R2 harness: %d checks: %s" % (total, "OK" if ok else "REGRESSION"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
