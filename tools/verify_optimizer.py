#!/usr/bin/env python
"""Durable regression harness for the mixture refinement optimizer.

The optimizer is the most numerically fragile part of the app (L-BFGS-B over
fractions/scales/background). This guards it against silent breakage - the
kind where a bad scipy call or a swallowed exception makes "optimize" quietly
do nothing. For each sample project it checks:

  1. Re-optimising the stored (already-fitted) solution does not WORSEN the
     residual (optimum is a fixed point, within tolerance).
  2. From a deliberately perturbed start (scales -> 1, background -> 0, which
     inflates the residual) the optimizer RECOVERS a much lower residual.
  3. The optimised solution is valid: fractions sum to 1 and lie in [0, 1],
     scales are strictly positive, nothing is NaN/inf.
  4. Edge case: a mixture with no free variables optimises to a no-op without
     crashing.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_optimizer.py
    ./python/python.exe tools/verify_optimizer.py "a.mud" "b.mud"

No QApplication needed. Exit codes: 0 = all pass, 1 = a regression,
2 = no sample projects found.
"""

from __future__ import annotations

import os
import sys

import numpy as np

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")

# The stored solutions come from the old app; re-optimising may improve them
# slightly but must never worsen them by more than this (residual is in %).
_NO_WORSEN_TOL = 1e-2
# A perturbed start must recover to within this of the stored optimum.
_RECOVER_TOL = 1.0


def _default_projects():
    projects = []
    for name in ("308 r1.mud", "Dh2040A 14Jul26.mud", "Dh2040A 14Jul26 r1.mud"):
        in_repo = os.path.join(_FIXTURES, name)
        downloads = os.path.join(os.path.expanduser("~"), "Downloads", name)
        projects.append(in_repo if os.path.isfile(in_repo) else downloads)
    return projects


def _check(results, label, ok):
    results.append((label, bool(ok)))


def check_project(path):
    print("=" * 72)
    print(os.path.basename(path))
    results = []

    for mi in range(len(load_mud(path).mixtures)):
        # 1 + 3. Re-optimise the stored solution: must not worsen; stays valid.
        proj = load_mud(path)
        mix = proj.mixtures[mi]
        stored = mix.current_residual()
        reopt = mix.optimize()
        print("  mixture %d: stored=%.4f  re-optimised=%.4f" % (mi, stored, reopt))
        _check(results, "M%d re-optimise does not worsen" % mi,
               reopt <= stored + _NO_WORSEN_TOL)
        _check(results, "M%d fractions sum to 1" % mi,
               np.isclose(np.sum(mix.fractions), 1.0))
        _check(results, "M%d fractions in [0,1]" % mi,
               np.all(mix.fractions >= -1e-9) and np.all(mix.fractions <= 1 + 1e-9))
        _check(results, "M%d scales positive & finite" % mi,
               np.all(mix.scales > 0) and np.all(np.isfinite(mix.scales)))
        _check(results, "M%d bg finite" % mi, np.all(np.isfinite(mix.bgshifts)))

        # 2. Perturb, then recover.
        proj = load_mud(path)
        mix = proj.mixtures[mi]
        mix.scales = np.ones_like(mix.scales)
        mix.bgshifts = np.zeros_like(mix.bgshifts)
        perturbed = mix.current_residual()
        recovered = mix.optimize()
        print("     perturbed=%.4f -> recovered=%.4f (stored=%.4f)"
              % (perturbed, recovered, stored))
        _check(results, "M%d recovers below perturbed" % mi, recovered < perturbed)
        _check(results, "M%d recovers near stored optimum" % mi,
               recovered <= stored + _RECOVER_TOL)

        # 4. No free variables -> no-op, no crash.
        proj = load_mud(path)
        mix = proj.mixtures[mi]
        mix.raw_properties["fractions_mask"] = [0] * mix.m
        mix.raw_properties["auto_scales"] = False
        mix.raw_properties["auto_bg"] = False
        try:
            mix.optimize()
            _check(results, "M%d no-free-vars is a safe no-op" % mi, True)
        except Exception as exc:  # noqa: BLE001 - report, don't hide
            print("     no-free-vars raised:", exc)
            _check(results, "M%d no-free-vars is a safe no-op" % mi, False)

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
    print("Ran %d optimizer checks across %d project(s): %d passed, %d FAILED"
          % (total, len(projects) - missing, total - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
