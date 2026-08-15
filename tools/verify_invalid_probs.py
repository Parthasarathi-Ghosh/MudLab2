#!/usr/bin/env python
"""Regression: an INVALID stacking-probability model must never crash the phase
intensity calc - it yields a blank (zero) pattern.

Guards two things that upstream MudLab (GTK) got wrong (its "Bug B"):
  * `_get_diffracted_intensity` returns zeros before any CSDS / W / P use, and
  * `get_intensity` skips the Lorentz-polarisation factor (which reads
    `sigma_star`) when the model is invalid - so the invalid-matrix guard fires
    before `sigma_star` is dereferenced.

Affected models (R>=1, multi-parameter): R1G3, R1G4, R2G2, R2G3, R3G2. R0* and
R1G2 have an entirely-valid parameter box, so they can never reach the path.

Self-contained (no .mud fixtures): builds empty phases with `Phase.create_empty`
and a default `Goniometer`. Run from the repo root:
    ./python/python.exe tools/verify_invalid_probs.py
"""
from __future__ import annotations

import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, "src")

import numpy as np  # noqa: E402

from mudlab.calculations.phases import get_intensity  # noqa: E402
from mudlab.models.goniometer import Goniometer  # noqa: E402
from mudlab.models.phase import Phase  # noqa: E402
from mudlab.models.probabilities import R0Probability, R1G2Probability  # noqa: E402

# (name, R, G) of every model that CAN produce an invalid junction matrix.
AFFECTED = [("R1G3", 1, 3), ("R1G4", 1, 4), ("R2G2", 2, 2),
            ("R2G3", 2, 3), ("R3G2", 3, 2)]

_results: list[tuple[str, bool]] = []
_rng = np.random.default_rng(0)


def check(label: str, ok: bool) -> None:
    _results.append((label, bool(ok)))


def _make_invalid(model, tries: int = 5000) -> bool:
    """Randomise the model's independent params until it is invalid."""
    names = [p[0] for p in model.PARAMS]
    for _ in range(tries):
        for n in names:
            setattr(model, n, float(_rng.random()))
        if not model.valid:
            return True
    return False


def _never_invalid(model, tries: int = 5000) -> bool:
    for _ in range(tries):
        if hasattr(model, "PARAMS"):
            for n in [p[0] for p in model.PARAMS]:
                setattr(model, n, float(_rng.random()))
        else:  # R0: randomise its F params
            model.F = [float(_rng.random()) for _ in range(model.n_independents)]
        if not model.valid:
            return False
    return True


def main() -> int:
    g = Goniometer()
    x = np.arange(4.0, 40.0, 0.02)
    range_theta = np.radians(x * 0.5)
    wl = getattr(g, "wavelength", 0.15406) or 0.15406
    range_stl = 2.0 * np.sin(range_theta) / wl

    for name, R, G in AFFECTED:
        phase = Phase.create_empty(G=G, R=R, name=name)
        got_invalid = _make_invalid(phase.probabilities)
        check("%s reaches an invalid junction matrix" % name, got_invalid)
        check("%s valid_probs reports invalid" % name, not phase.valid_probs)
        # Root-cause safety: sigma_star must stay a float (upstream nulled it).
        check("%s sigma_star stays a float when invalid" % name,
              isinstance(phase.sigma_star, float))
        crashed, out = False, None
        try:
            out = get_intensity(range_theta, range_stl, g.soller1, g.soller2,
                                g.mcr_2theta, phase)
        except Exception:
            crashed = True
            traceback.print_exc()
        check("%s get_intensity does not crash on an invalid model" % name,
              not crashed)
        check("%s invalid model yields a blank (all-zero, finite) pattern" % name,
              out is not None and np.all(np.isfinite(out)) and np.allclose(out, 0.0))

    # Pin the guard itself: even if sigma_star were None (upstream's nulled-block
    # failure mode), an invalid model must not reach the LP path. Without the
    # `and phase.valid_probs` guard this crashes in get_T (max(None, ...)); with
    # it, the LP factor is skipped.
    phase = Phase.create_empty(G=3, R=1, name="null-sigma")
    _make_invalid(phase.probabilities)
    phase._sigma_star = None  # simulate the upstream Phase.data_object nulling
    crashed = False
    try:
        out = get_intensity(range_theta, range_stl, g.soller1, g.soller2,
                            g.mcr_2theta, phase)
    except Exception:
        crashed = True
        traceback.print_exc()
    check("guard fires before sigma_star (no crash even if sigma_star is None)",
          not crashed and out is not None and np.allclose(out, 0.0))

    # R0 / R1G2 can never reach the invalid path (entirely-valid parameter box).
    check("R0G3 never invalid over random params", _never_invalid(R0Probability(3, [0.8, 0.8])))
    check("R1G2 never invalid over random params", _never_invalid(R1G2Probability()))

    print("=" * 72)
    print("Invalid-probability-model calc guard (Bug B downstream)")
    print("=" * 72)
    passed = 0
    for label, ok in _results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += int(ok)
    print("-" * 72)
    print("verify_invalid_probs: %d/%d checks: %s"
          % (passed, len(_results), "OK" if passed == len(_results) else "FAILED"))
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
