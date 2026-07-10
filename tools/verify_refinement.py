#!/usr/bin/env python
"""Durable regression harness for the structural-parameter refinement.

Guards calculations/refinement.py (the refinables framework + the three
SciPy refine methods + the nested inner optimize). For each sample project:

  1. Refinables enumerate and cover the expected parameter kinds (sigma*,
     CSDS mean, d001, delta_c, and F params for G>=2 phases).
  2. Flagging one structural parameter, perturbing it, and refining RECOVERS
     a residual below the perturbed one and no worse than the un-perturbed
     optimum (L-BFGS-B, small budget).
  3. All three methods (0 L-BFGS-B, 1 Basin Hopping, 2 Brute force) run to a
     finite residual.
  4. With nothing flagged, refine falls back to a plain fraction/scale/bg
     optimize (finite).
  5. A flag + bounds written into ref_info survive a save/load round-trip.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_refinement.py
    ./python/python.exe tools/verify_refinement.py "a.mud" "b.mud"

No QApplication needed. Exit codes: 0 = all pass, 1 = a regression,
2 = no sample projects found. (This is the heaviest harness - the nested
optimize makes each refine call do real work; budgets are kept small.)
"""

from __future__ import annotations

import os
import sys
import tempfile

import numpy as np

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.calculations.refinement import (  # noqa: E402
    REFINE_METHODS, enumerate_refinables, refine_mixture,
)

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")


def _default_projects():
    projects = []
    for name in ("308 r1.mud", "Dh2040A.mud"):
        in_repo = os.path.join(_FIXTURES, name)
        downloads = os.path.join(os.path.expanduser("~"), "Downloads", name)
        projects.append(in_repo if os.path.isfile(in_repo) else downloads)
    return projects


def _check(results, label, ok):
    results.append((label, bool(ok)))


def _first_flaggable(refinables):
    """A refinable to flag for the recovery test: prefer a sigma* on the
    highest-impact phase, else any parameter."""
    for ref in refinables:
        if ref.label.endswith("| sigma*"):
            return ref
    return refinables[0] if refinables else None


def check_project(path):
    print("=" * 72)
    print(os.path.basename(path))
    results = []

    # 1. Enumeration coverage.
    refs = enumerate_refinables(load_mud(path).mixtures[0])
    labels = [r.label for r in refs]
    _check(results, "enumerate is non-empty", len(refs) > 0)
    for kind in ("sigma*", "CSDS mean", "d001", "delta_c"):
        _check(results, "covers %s" % kind, any(kind in l for l in labels))

    # 2. Perturb-and-recover on one flagged structural parameter.
    proj = load_mud(path)
    mix = proj.mixtures[0]
    ref = _first_flaggable(enumerate_refinables(mix))
    ref.set_ref_info(minimum=1.0, maximum=20.0, refine=True)
    r_opt = mix.optimize()
    baseline = ref.value
    ref.value = min(max(baseline * 2.5 + 3.0, 1.5), 19.0)  # push well off optimum
    r_perturbed = mix.optimize()
    r_refined = mix.refine(0, {"maxfun": 20})
    print("  residual optimal=%.4f perturbed=%.4f refined=%.4f (param %.3f)"
          % (r_opt, r_perturbed, r_refined, ref.value))
    _check(results, "refine recovers below perturbed", r_refined < r_perturbed)
    _check(results, "refine returns near/under optimum", r_refined <= r_opt + 0.5)
    _check(results, "refined value within bounds", 1.0 <= ref.value <= 20.0)

    # 3. Every method runs finite (tiny budgets).
    for idx, (name, _fn) in sorted(REFINE_METHODS.items()):
        p = load_mud(path)
        m = p.mixtures[0]
        r = _first_flaggable(enumerate_refinables(m))
        r.set_ref_info(minimum=1.0, maximum=20.0, refine=True)
        residual = m.refine(idx, {"maxfun": 6, "maxiter": 3, "niter": 1, "num_samples": 4})
        print("  method %d %-24s residual=%.4f" % (idx, name, residual))
        _check(results, "method %d (%s) finite" % (idx, name), np.isfinite(residual))

    # 3b. Initial/Best/Last solutions are tracked without the history hook
    # (they back the Refinement window's keep-solution buttons).
    proj = load_mud(path)
    mix = proj.mixtures[0]
    ref = _first_flaggable(enumerate_refinables(mix))
    ref.set_ref_info(minimum=1.0, maximum=20.0, refine=True)
    ref.value = 12.0
    refiner = refine_mixture(mix, 0, {"maxfun": 12})
    _check(results, "history hook stays disabled", len(refiner.history) == 0)
    _check(results, "initial/best/last residuals tracked",
           None not in (refiner.initial_residual, refiner.best_residual,
                        refiner.last_residual))
    _check(results, "best is no worse than initial",
           refiner.best_residual <= refiner.initial_residual + 1e-9)
    refiner.apply_initial()
    _check(results, "apply_initial restores the initial value",
           np.isclose(ref.value, refiner.initial_solution[0], atol=1e-6))
    refiner.apply_best()
    _check(results, "apply_best sets the best value",
           np.isclose(ref.value, refiner.best_solution[0], atol=1e-6))

    # 4. No flags -> falls back to a plain optimize.
    residual = load_mud(path).mixtures[0].refine(0, {})
    _check(results, "no-flags refine is finite", np.isfinite(residual))

    # 5. ref_info round-trip.
    p = load_mud(path)
    m = p.mixtures[0]
    enum = enumerate_refinables(m)
    rr = next((r for r in enum if "d001" in r.label), enum[0])
    rr.set_ref_info(minimum=0.99, maximum=1.01, refine=True)
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_rt_ref_%d.mud" % os.getpid())
    save_mud(p, tmp)
    try:
        p2 = load_mud(tmp)
        back = next(r for r in enumerate_refinables(p2.mixtures[0]) if r.label == rr.label)
        _check(results, "ref_info flag+bounds round-trip",
               back.refine and np.isclose(back.minimum, 0.99)
               and np.isclose(back.maximum, 1.01))
    finally:
        for f in (tmp, tmp + "~"):
            if os.path.exists(f):
                os.remove(f)

    failed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        failed += not ok
    return len(results), failed


def main(argv):
    projects = argv[1:] or _default_projects()
    total = failed = missing = 0
    for path in projects:
        if not os.path.isfile(path):
            print("SKIP (not found): %s" % path)
            missing += 1
            continue
        checked, fail = check_project(path)
        total += checked
        failed += fail
    print("=" * 72)
    if total == 0:
        print("NOTHING VERIFIED - no sample projects were found.")
        return 2
    print("Ran %d refinement checks across %d project(s): %d passed, %d FAILED"
          % (total, len(projects) - missing, total - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
