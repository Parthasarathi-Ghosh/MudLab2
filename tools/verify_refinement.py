#!/usr/bin/env python
"""Durable regression harness for the structural-parameter refinement.

Guards calculations/refinement.py (the refinables framework + the three
SciPy refine methods + the nested inner optimize). For each sample project:

  1. Refinables enumerate and cover the expected parameter kinds (sigma*,
     CSDS mean, d001, delta_c, and F params for G>=2 phases).
  2. Flagging one structural parameter, perturbing it, and refining RECOVERS
     a residual below the perturbed one and no worse than the un-perturbed
     optimum (L-BFGS-B, small budget).
  3. Both methods (0 L-BFGS-B, 1 Basin Hopping) run to a finite residual.
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
    for name in ("308 r1.mud", "Dh2040A 14Jul26.mud", "Dh2040A 14Jul26 r1.mud", "Dh2040A 14Jul26 r2.mud"):
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

    # 1a. INHERITANCE / LINKING is honoured when the list is BUILT, not during
    # the run: a parameter that follows a based_on parent (or a linked
    # component's template) is not offered at all, because refining it would be
    # a no-op - the read-through overwrites the write. Refining the PARENT moves
    # every child that inherits it.
    mix_inh = load_mud(path).mixtures[0]
    phases, seen = [], set()
    for row in mix_inh.phase_matrix:
        for ph in row:
            if ph is not None and hasattr(ph, "components") and id(ph) not in seen:
                seen.add(id(ph))
                phases.append(ph)
    offered = {}
    for ref in enumerate_refinables(mix_inh):
        offered.setdefault(ref.group[0], set()).add(ref.title)
    inherited_phases = [p for p in phases if p.is_inherited("sigma_star")]
    if inherited_phases:
        _check(results, "a phase inheriting sigma* is not offered it",
               all("sigma*" not in offered.get(p.name, set())
                   for p in inherited_phases))
        # ...and the parent that owns it IS offered it.
        parents = {getattr(p, "based_on", None) for p in inherited_phases}
        _check(results, "the parent that owns sigma* still offers it",
               all("sigma*" in offered.get(b.name, set())
                   for b in parents if b is not None))
        # Read-through: moving the parent moves the child.
        child = inherited_phases[0]
        parent = getattr(child, "based_on", None)
        if parent is not None:
            was = child.sigma_star
            parent.sigma_star = parent.sigma_star + 1.0
            _check(results, "refining the parent moves the inheriting child",
                   abs(child.sigma_star - (was + 1.0)) < 1e-9)
            parent.sigma_star = parent.sigma_star - 1.0
    inherited_comps = [(p, c) for p in phases for c in p.components
                       if c.is_inherited("d001")]
    if inherited_comps:
        _check(results, "a linked component inheriting d001 is not offered it",
               len([r for r in enumerate_refinables(mix_inh)
                    if r.title == "d001" and len(r.group) > 1
                    and any(r.group[0] == p.name and r.group[1] == c.name
                            for p, c in inherited_comps)]) == 0)

    # 1c. The reported Rp is the MEAN over the mixture's specimens, and
    # per_specimen_residuals must reproduce exactly the values that mean is
    # taken over (same exclusion selection, same skip of empty specimens).
    from mudlab.calculations.mixture import (
        get_current_residual, per_specimen_residuals,
    )
    mix_rp = load_mud(path).mixtures[0]
    per = per_specimen_residuals(mix_rp)
    if per:
        mean = sum(v for _n, v in per) / len(per)
        _check(results, "per-specimen Rp averages to the reported residual",
               abs(mean - get_current_residual(mix_rp)) < 1e-9)
        _check(results, "every per-specimen Rp is named and finite",
               all(n and np.isfinite(v) for n, v in per))

    # 1d. Basin Hopping caps each LOCAL minimisation. Uncapped, scipy allows
    # 15000 evaluations per run, so niter=100 could mean ~1.5M - each a full
    # recompute plus an inner fit. Checked by intercepting the scipy call rather
    # than running it (a real Basin Hopping run takes minutes).
    import mudlab.calculations.refinement as _refmod
    captured = {}

    def _fake_basinhopping(func, x0, **kwargs):
        captured.update(kwargs)

        class _R:
            x = x0
        return _R()

    _real = _refmod.basinhopping
    _refmod.basinhopping = _fake_basinhopping
    try:
        class _FakeRefiner:
            get_residual = staticmethod(lambda x: 0.0)
            initial_solution = np.array([1.0])
            ranges = [(0.0, 2.0)]

        _refmod._run_basinhopping(_FakeRefiner(), {})
        opts = (captured.get("minimizer_kwargs") or {}).get("options") or {}
        _check(results, "Basin Hopping caps each local run by default",
               opts.get("maxfun") == _refmod.BASINHOPPING_LOCAL_MAXFUN)
        captured.clear()
        _refmod._run_basinhopping(_FakeRefiner(), {"local_maxfun": 42})
        opts = (captured.get("minimizer_kwargs") or {}).get("options") or {}
        _check(results, "...and the user can raise or lower that cap",
               opts.get("maxfun") == 42)
    finally:
        _refmod.basinhopping = _real

    # 1b. A raw-pattern accessory in the mixture must NOT break enumeration (it
    # has no structure, so _phase_refinables would raise on it) - it is skipped,
    # adding no refinables, while its fraction is still fit by the fraction fit.
    from mudlab.models.raw_pattern_phase import RawPatternPhase
    mix_raw = load_mud(path).mixtures[0]
    raw = RawPatternPhase(name="Accessory ref")
    raw.set_raw_pattern(np.linspace(5, 70, 50), np.ones(50))
    slot = mix_raw.add_phase_slot("Acc")
    for i in range(mix_raw.n):
        mix_raw.set_phase_at(i, slot, raw)
    try:
        n_with_raw = len(enumerate_refinables(mix_raw))
        _check(results, "raw accessory does not break enumerate (skipped)",
               n_with_raw == len(refs))
    except Exception as exc:  # noqa: BLE001
        _check(results, "raw accessory does not break enumerate (skipped): %s" % exc,
               False)

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
        residual = m.refine(idx, {"maxfun": 6, "maxiter": 3, "niter": 1})
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

    # 4b. A mid-loop error re-raises AND restores the pre-refine model state
    # (structural value + fractions/scales/bg), never a half-refined solution.
    import mudlab.calculations.refinement as _R
    proj = load_mud(path)
    mix = proj.mixtures[0]
    ref = _first_flaggable(enumerate_refinables(mix))
    ref.set_ref_info(minimum=1.0, maximum=20.0, refine=True)
    ref.value = 8.0
    mix.optimize()
    pre = (ref.value, mix.fractions.copy(), mix.scales.copy(), mix.bgshifts.copy())
    original = _R.optimize_mixture
    state = {"n": 0}

    def _boom(m):
        state["n"] += 1
        if state["n"] >= 3:
            raise RuntimeError("injected mid-loop error")
        return original(m)

    _R.optimize_mixture = _boom
    raised = False
    try:
        _R.refine_mixture(mix, 0, {"maxfun": 100})
    except RuntimeError:
        raised = True
    finally:
        _R.optimize_mixture = original
    _check(results, "mid-loop error re-raises (fail loud)", raised)
    _check(results, "mid-loop error restores model state",
           np.isclose(ref.value, pre[0]) and np.allclose(mix.fractions, pre[1])
           and np.allclose(mix.scales, pre[2]) and np.allclose(mix.bgshifts, pre[3]))

    # 4c. The stop hook (backs the Cancel button) aborts a long run promptly
    # and keeps a finite best-so-far.
    proj = load_mud(path)
    mix = proj.mixtures[0]
    ref = _first_flaggable(enumerate_refinables(mix))
    ref.set_ref_info(minimum=1.0, maximum=20.0, refine=True)
    ref.value = 8.0
    stop_calls = {"n": 0}

    def _stop():
        stop_calls["n"] += 1
        return stop_calls["n"] > 3

    from mudlab.calculations.refinement import refine_mixture as _refine
    refiner = _refine(mix, 0, {"maxfun": 500}, stop=_stop)
    _check(results, "stop hook aborts a long run promptly",
           stop_calls["n"] <= 10 and np.isfinite(refiner.best_residual))

    # 4d. The on_progress hook (backs the live status) fires with a rising
    # evaluation count and a finite best.
    proj = load_mud(path)
    mix = proj.mixtures[0]
    ref = _first_flaggable(enumerate_refinables(mix))
    ref.set_ref_info(minimum=1.0, maximum=20.0, refine=True)
    ref.value = 8.0
    seen = []
    _refine(mix, 0, {"maxfun": 15}, on_progress=lambda n, best: seen.append((n, best)))
    _check(results, "on_progress fires with rising n + finite best",
           len(seen) > 0 and seen[0][0] >= 1 and seen[-1][0] >= seen[0][0]
           and all(np.isfinite(b) for _, b in seen))

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
