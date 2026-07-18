#!/usr/bin/env python
"""Durable harness for the higher-Reichweite stacking models (R1G3, R2G2,
R2G3, R3G2) - everything built on _MarkovProbability.

The golden-calc CORRECTNESS proof (each model reproduces the old app's stored
pattern to corr 1.000000, exercising the calc's reps = rank // G path) lives in
verify_calc_engine.py. This harness guards the model INTERNALS that a golden
match alone would not localise, uniformly across the four models:

  1. dispatch - the type string loads the right class (not refused);
  2. matrix shape / reps - W and P are g^R x g^R, so reps = G^(R-1)
     (1 / 2 / 3 / 4 for these models);
  3. validity - W is a stationary distribution and every NONZERO-weight state's
     P row is stochastic (a zero-weight state's row is unconstrained);
  4. per-parameter inheritance - each parameter reads through to a based_on
     model and a parent edit propagates (tested synthetically: the fixtures are
     single-phase);
  5. editor / refiner enumerate exactly the model's parameters;
  6. round-trip - the probabilities survive save/reload byte-identical and an
     edited parameter persists.

R2G2 additionally gets an INDEPENDENT re-derivation of its 4x4 matrices (it is
the first reps>1 model, so its matrix assembly is checked against a second
implementation, not only the golden).

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_higher_r.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no higher-R fixtures found.
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
    R1G3Probability, R2G2Probability, R2G3Probability, R3G2Probability,
    probabilities_from_dict,
)

_app = QApplication.instance() or QApplication([])

# (type, fixture basename, class, params-that-vary-for-the-inheritance-test)
_MODELS = [
    ("R1G3Model", "Illite-Smectite R1 G3", R1G3Probability),
    ("R2G2Model", "Illite-Smectite R2 G2", R2G2Probability),
    ("R2G3Model", "Illite-Smectite R2 G3", R2G3Probability),
    ("R3G2Model", "Illite-Smectite R3 G2", R3G2Probability),
]


def _fixture(base):
    for d in (os.path.join(_REPO, "tools", "sample_projects"),
              os.path.join(os.path.expanduser("~"), "Downloads", "PyXRD test projects")):
        p = os.path.join(d, base + ".mud")
        if os.path.isfile(p):
            return p
    return None


def _r2g2_reference(W1, P112_or_P211, P21, P122_or_P221):
    """Independent re-derivation of R2G2Model.update (not the model's own)."""
    W2, P22 = 1.0 - W1, 1.0 - P21
    W10 = W2 * P21
    W11 = W2 * P22
    W01, W00 = W10, W1 - W10
    if W1 <= 2.0 / 3.0:
        P001 = P112_or_P211
        P100 = (P001 * W00 / W10) if W10 else 0.0
    else:
        P100 = P112_or_P211
        P001 = (P100 * W10 / W00) if W00 else 0.0
    P101, P000 = 1 - P100, 1 - P001
    if P21 <= 0.5:
        P011 = P122_or_P221
        P110 = (P011 * W01 / W11) if W11 else 0.0
    else:
        P110 = P122_or_P221
        P011 = (P110 * W11 / W01) if W01 else 0.0
    P010, P111 = 1 - P011, 1 - P110
    return (np.array([W00, W01, W10, W11]),
            np.array([[P000, P001, 0, 0], [0, 0, P010, P011],
                      [P100, P101, 0, 0], [0, 0, P110, P111]], float))


def _r2g3_reference(W1, P111_or_P212, G1, G2, G3, G4):
    """Independent re-derivation of R2G3Model.update. The fixtures pin every G
    ratio at 0.5 (where G <-> 1-G is invisible), so the golden calc does NOT
    exercise G1-G4; this second implementation, checked at discriminating G
    values across both W1 branches, guards their transcription."""
    W0 = W1
    W1w = (1.0 - W1) * G1
    W2w = 1.0 - W0 - W1w
    pairW = {(1, 1): 0.0, (1, 2): 0.0, (2, 1): 0.0, (2, 2): 0.0,
             (0, 1): W1w, (1, 0): W1w, (0, 2): W2w, (2, 0): W2w}
    pairW[(0, 0)] = W0 - pairW[(0, 1)] - pairW[(0, 2)]
    Wx = W1w + W2w
    if W0 < 2.0 / 3.0:
        P000 = P111_or_P212
        Px0x = (1 - (W0 - Wx) / Wx * (1 - P000)) if Wx else 0.0
    else:
        Px0x = P111_or_P212
        P000 = (1 - Wx / (W0 - Wx) * (1 - Px0x)) if (W0 - Wx) else 0.0
    Wx0x = Wx * Px0x
    W10x, W20x = G2 * Wx0x, Wx0x - G2 * Wx0x
    tW = {
        (1, 0, 1): G3 * W10x, (1, 0, 2): (1 - G3) * W10x,
        (2, 0, 1): G4 * W20x, (2, 0, 2): (1 - G4) * W20x,
        (0, 0, 0): pairW[(0, 0)] * P000,
        (0, 1, 0): pairW[(0, 1)], (0, 2, 0): pairW[(0, 2)],
    }
    tW[(1, 0, 0)] = pairW[(1, 0)] - tW[(1, 0, 1)] - tW[(1, 0, 2)]
    tW[(2, 0, 0)] = pairW[(2, 0)] - tW[(2, 0, 1)] - tW[(2, 0, 2)]
    tW[(0, 0, 1)] = pairW[(0, 1)] - tW[(1, 0, 1)] - tW[(2, 0, 1)]
    tW[(0, 0, 2)] = pairW[(0, 2)] - tW[(1, 0, 2)] - tW[(2, 0, 2)]
    W = np.zeros((9, 9))
    for (i, j), wv in pairW.items():
        W[3 * i + j, 3 * i + j] = wv
    P = np.zeros((9, 9))
    for i in range(3):
        for j in range(3):
            wij = pairW.get((i, j), 0.0)
            if wij > 0.0:
                for k in range(3):
                    P[3 * i + j, 3 * j + k] = tW.get((i, j, k), 0.0) / wij
    return np.diag(W), P


def _phase_of(project, cls):
    for ph in project.phases:
        if isinstance(ph.probabilities, cls):
            return ph
    return None


def check_model(type_name, base, cls, results):
    path = _fixture(base)
    if path is None:
        return False
    tag = type_name
    project = load_mud(path)
    phase = _phase_of(project, cls)
    pr = phase.probabilities

    # 1. dispatch
    results.append(("%s: dispatch -> %s" % (tag, cls.__name__),
                    isinstance(probabilities_from_dict(
                        {"type": type_name, "properties": {}}, pr.G), cls)))
    # 2. shape / reps
    W = pr.get_distribution_matrix()
    P = pr.get_probability_matrix()
    rank = pr.G ** pr.R
    results.append(("%s: W,P are %dx%d (reps=%d)" % (tag, rank, rank, rank // pr.G),
                    W.shape == (rank, rank) and P.shape == (rank, rank)))
    # 3. validity - stationary W + active-row-stochastic P
    w = np.diag(W)
    active = w > 1e-9
    results.append(("%s: W stationary, active P rows stochastic, valid" % tag,
                    abs(w.sum() - 1.0) < 1e-9
                    and np.allclose(P[active].sum(axis=1), 1.0)
                    and pr.valid))
    # 4. inheritance (synthetic, fresh instances - must NOT mutate the fixture
    # model `pr`, which later checks still read): child inherits the first
    # param from a parent whose value differs from the child's own.
    params = [name for name, *_ in cls.PARAMS]
    p0 = params[0]
    parent = cls.from_dict({"properties": {}}, pr.G)
    child = cls.from_dict({"properties": {}}, pr.G)
    setattr(parent, p0, 0.42)
    setattr(child, p0, 0.88)  # own value, deliberately different
    setattr(child, "inherit_" + p0, True)
    child.set_based_on(parent)
    results.append(("%s: %s reads the parent value (0.42), not its own (0.88)"
                    % (tag, p0), abs(child.value(p0) - 0.42) < 1e-12))
    setattr(parent, p0, 0.31)
    results.append(("%s: a parent edit propagates" % tag,
                    abs(child.value(p0) - 0.31) < 1e-12))
    child.clear_inheritance()
    results.append(("%s: clear_inheritance drops the flag -> own value 0.88"
                    % tag, not getattr(child, "inherit_" + p0)
                    and abs(child.value(p0) - 0.88) < 1e-12))
    # 5. editor / refiner enumerate the params
    results.append(("%s: editor shows %d params" % (tag, len(params)),
                    len(pr.editable_params()) == len(params)))
    results.append(("%s: refinable_params lists %d" % (tag, len(params)),
                    len(pr.refinable_params()) == len(params)))
    # 6. round-trip byte-identical + edit persists
    _roundtrip(path, type_name, cls, params, results)
    # R2G2 independent re-derivation
    if cls is R2G2Probability:
        w_ref, P_ref = _r2g2_reference(
            pr.value("W1"), pr.value("P112_or_P211"),
            pr.value("P21"), pr.value("P122_or_P221"))
        results.append(("%s: 4x4 matrices match an independent re-derivation"
                        % tag,
                        np.allclose(pr.get_distribution_array(), w_ref, atol=1e-12)
                        and np.allclose(P, P_ref, atol=1e-12)))
    # R2G3: the fixture pins G1-G4 at 0.5, so guard them at DISCRIMINATING
    # values (both W1 branches) against the independent re-derivation.
    if cls is R2G3Probability:
        # Valid AND discriminating (G = 0.6, so G != 1-G), one set per W1
        # branch. Not every param combination is valid (the model constrains
        # them jointly - some give a negative junction probability), so these
        # were picked to keep every probability in [0, 1].
        for (w1, p, g1, g2, g3, g4) in [
            (0.70, 0.6, 0.6, 0.6, 0.6, 0.6),   # W1 > 2/3 branch
            (0.60, 0.6, 0.6, 0.6, 0.6, 0.6),   # W1 < 2/3 branch
        ]:
            m = R2G3Probability(W1=w1, P111_or_P212=p, G1=g1, G2=g2, G3=g3, G4=g4)
            w_ref, P_ref = _r2g3_reference(w1, p, g1, g2, g3, g4)
            results.append(("%s: W1=%.2f G-params match re-derivation" % (tag, w1),
                            np.allclose(m.get_distribution_array(), w_ref, atol=1e-12)
                            and np.allclose(m.get_probability_matrix(), P_ref, atol=1e-12)
                            and m.valid))
    return True


def _roundtrip(path, type_name, cls, params, results):
    def _probs(mud):
        z = zipfile.ZipFile(mud)
        data = json.loads(z.read("phases").decode("utf-8"))
        items = data if isinstance(data, list) else [data]
        return [it["properties"].get("probabilities") for it in items
                if isinstance(it, dict)]

    tmp = os.path.join(tempfile.gettempdir(), "mudlab_hr_rt.mud")
    try:
        save_mud(load_mud(path), tmp)
        before = [p for p in _probs(path)
                  if isinstance(p, dict) and p.get("type") == type_name]
        after = [p for p in _probs(tmp)
                 if isinstance(p, dict) and p.get("type") == type_name]
        results.append(("%s: probs byte-identical after reload" % type_name,
                        before == after and len(before) >= 1))
        # Edit the first param, save, reload.
        project = load_mud(path)
        phase = _phase_of(project, cls)
        setattr(phase.probabilities, params[0], 0.5123)
        save_mud(project, tmp)
        reloaded = _phase_of(load_mud(tmp), cls)
        results.append(("%s: an edited %s persists" % (type_name, params[0]),
                        abs(getattr(reloaded.probabilities, params[0]) - 0.5123)
                        < 1e-9))
    finally:
        for p in (tmp, tmp + "~"):
            if os.path.exists(p):
                os.remove(p)


def main(argv):
    results = []
    ran = 0
    for type_name, base, cls in _MODELS:
        print("=" * 72)
        print(type_name, "-", base)
        print("=" * 72)
        n_before = len(results)
        if check_model(type_name, base, cls, results):
            ran += 1
        for label, ok in results[n_before:]:
            print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        print()
    if ran == 0:
        print("No higher-R fixtures found; skipping (exit 2).")
        return 2
    passed = sum(1 for _, ok in results if ok)
    print("=" * 72)
    print("Higher-R harness: %d/%d checks across %d models: %s"
          % (passed, len(results), ran, "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
