#!/usr/bin/env python
"""Durable harness for the probability-model factory + create_empty (Batch 1 of
exposing the higher-R stacking models).

The R0-R3 probability models were already ported + golden-validated
(verify_higher_r); this guards the NEW-phase creation path that exposes them:
`create_probability(R, G)` / `is_supported_rg` (MudLab2's RGbounds) and
`Phase.create_empty(G, R)`.

  1. is_supported_rg matches the old RGbounds: R0 G1-6, R1 G2-4, R2 G2-3, R3 G2;
     rejects R1G5, R2G4, R3G3, etc.
  2. create_probability builds the right model per (R, G), each valid + the
     correct type / matrix shape, and rejects an unsupported (R, G).
  3. create_empty builds a phase with that model AND G blank components, for
     every supported (R, G) - and the phase is structurally consistent
     (probabilities G == component count).

Run head-less from the repo root:

    ./python/python.exe tools/verify_probability_factory.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.models.phase import Phase  # noqa: E402
from mudlab.models.probabilities import (  # noqa: E402
    UnsupportedProbabilityModel, create_probability, is_supported_rg,
    supported_g_range,
)

results = []


def check(label, ok):
    results.append((label, bool(ok)))


# The old app's RGbounds, spelled out.
_SUPPORTED = {(0, g) for g in range(1, 7)} | {(1, 2), (1, 3), (1, 4),
                                              (2, 2), (2, 3), (3, 2)}
_EXPECT_TYPE = {
    (1, 2): "R1G2Model", (1, 3): "R1G3Model", (1, 4): "R1G4Model",
    (2, 2): "R2G2Model", (2, 3): "R2G3Model", (3, 2): "R3G2Model",
}


def run():
    # 1. is_supported_rg == RGbounds.
    ok_support = True
    for r in range(4):
        for g in range(1, 8):
            if is_supported_rg(r, g) != ((r, g) in _SUPPORTED):
                ok_support = False
    check("1 is_supported_rg matches the old RGbounds", ok_support)
    check("1 supported_g_range: R1 -> (2,4), R2 -> (2,3), R3 -> (2,2), R0 -> (1,6)",
          supported_g_range(1) == (2, 4) and supported_g_range(2) == (2, 3)
          and supported_g_range(3) == (2, 2) and supported_g_range(0) == (1, 6))

    # 2. create_probability builds a valid model of the right type per (R, G).
    ok_factory = True
    for (r, g) in sorted(_SUPPORTED):
        model = create_probability(r, g)
        want_g = model.get_distribution_matrix().shape[0] >= g  # g or g**R
        typ_ok = (r == 0 and model.type_name == "R0G%dModel" % g) or \
                 (r > 0 and model.type_name == _EXPECT_TYPE[(r, g)])
        if not (model.valid and typ_ok and want_g):
            ok_factory = False
    check("2 create_probability builds a valid, correctly-typed model per (R,G)",
          ok_factory)
    # rejects the unsupported ones
    rejected = 0
    for (r, g) in [(1, 5), (1, 6), (2, 4), (3, 3), (3, 4)]:
        try:
            create_probability(r, g)
        except UnsupportedProbabilityModel:
            rejected += 1
    check("2 create_probability rejects unsupported (R, G)", rejected == 5)

    # 3. create_empty builds a consistent phase for every supported (R, G).
    ok_empty = True
    for (r, g) in sorted(_SUPPORTED):
        phase = Phase.create_empty(G=g, R=r, name="X")
        probs = phase.probabilities
        # probabilities G must equal the component count
        pg = getattr(probs, "G", None)
        if not (len(phase.components) == g and pg == g and probs.valid):
            ok_empty = False
    check("3 create_empty: phase + G components + a valid model, every (R,G)",
          ok_empty)
    # R1 no longer forces G=2 (the old stale behaviour)
    r1g3 = Phase.create_empty(G=3, R=1, name="X")
    check("3 create_empty(G=3, R=1) really is R1G3 (no longer forced to G2)",
          r1g3.G == 3 and r1g3.probabilities.type_name == "R1G3Model")
    return None


def main():
    print("=" * 72)
    print("Probability-model factory + create_empty")
    print("=" * 72)
    run()
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("Probability-factory harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
