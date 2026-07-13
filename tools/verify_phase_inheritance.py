#!/usr/bin/env python
"""Durable harness for PHASE-level inheritance (old `based_on`).

Guards the mechanism that models the same clay under different treatments: a
glycolated / heated phase is `based_on` an air-dried reference phase and
inherits its treatment-independent parameters.

This is load-bearing for the calculated pattern. The child stores its OWN -
often stale - stacking F params but carries `inherit_F<i>` flags; the value
that must be used is the PARENT's (in a refined project the parent's F is the
refined one). Reading the child's stale value produces a visibly wrong pattern:
before this was implemented, the refined fixture's EG/400 specimens missed the
old app's stored pattern (corr 0.83 / 0.97); with it they match to floating
point.

Checks per sample project:

  1. based_on resolves: a phase with a stored based_on_uuid points at that phase.
  2. Read-through: an inherited F param equals the parent's; a NON-inherited one
     reads the child's own value (proven where they differ - the refined fixture
     has parent F1=0.17 vs the children's stale stored 0.8).
  3. W/P follow: the derived weight/transition matrices are built from the
     EFFECTIVE (inherited) F, so they equal the parent's.
  4. Propagation: refining/editing the parent's F moves the child's F and W.
  5. Refinables skip inherited: an inherited F / sigma* / CSDS is not an
     independent refinable on the child (only the parent's is).
  6. Round-trip: based_on + inherit flags survive, and the child still
     serialises its OWN (stale) F - not the inherited one.

Run head-less from the repo root:

    ./python/python.exe tools/verify_phase_inheritance.py

Exit codes: 0 = pass, 1 = regression, 2 = no sample projects. The end-to-end
proof is tools/verify_calc_engine.py (the golden patterns).
"""

from __future__ import annotations

import os
import sys
import tempfile

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402

from mudlab.calculations.refinement import _phase_refinables  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")


def _default_projects():
    out = []
    for name in ("308 r1.mud", "Dh2040A 14Jul26.mud", "Dh2040A 14Jul26 r1.mud"):
        in_repo = os.path.join(_FIXTURES, name)
        dl = os.path.join(os.path.expanduser("~"), "Downloads", name)
        out.append(in_repo if os.path.isfile(in_repo) else dl)
    return out


def _children(project):
    return [p for p in project.phases if p.based_on is not None]


def check_resolve(project, results):
    """1. based_on resolves to the stored parent uuid."""
    kids = _children(project)
    for ph in kids:
        ok = ph.based_on.uuid == ph._based_on_uuid
        results.append(("1 %-14s based_on -> %s" % (ph.name, ph.based_on.name), ok))
    results.append(("1 project has based_on phases", bool(kids)))


def check_read_through(project, results):
    """2. Inherited F reads the parent's; non-inherited reads own.

    Returns True when this project *discriminates* - i.e. some inherited F
    differs from the child's own stale stored value, so read-through is
    observable (only the refined fixture does; in an unrefined project the
    values coincide and inheritance is invisible)."""
    proven = False
    for ph in _children(project):
        parent = ph.based_on
        probs, pprobs = ph.probabilities, parent.probabilities
        for i in range(probs.n_independents):
            if probs.is_f_inherited(i):
                ok = probs.f_value(i) == pprobs.f_value(i)
                results.append(("2 %s F%d == parent (%.4f)"
                                % (ph.name, i + 1, pprobs.f_value(i)), ok))
                # strongest proof: the child's OWN stored value differs
                if abs(probs.own_f_value(i) - pprobs.f_value(i)) > 1e-9:
                    proven = True
            else:
                ok = probs.f_value(i) == probs.own_f_value(i)
                results.append(("2 %s F%d reads own" % (ph.name, i + 1), ok))
        for attr in ("sigma_star", "CSDS"):
            if ph.is_inherited(attr):
                ok = getattr(ph, attr) is getattr(parent, attr) or \
                    getattr(ph, attr) == getattr(parent, attr)
                results.append(("2 %s %s == parent" % (ph.name, attr), ok))
    return proven


def check_matrices_follow(project, results):
    """3. W/P are derived from the EFFECTIVE (inherited) F."""
    for ph in _children(project):
        parent = ph.based_on
        if ph.probabilities.n_independents == 0:
            continue
        if all(ph.probabilities.is_f_inherited(i)
               for i in range(ph.probabilities.n_independents)):
            ok = np.allclose(ph.probabilities.get_distribution_array(),
                             parent.probabilities.get_distribution_array())
            results.append(("3 %s W == parent W (fully inherited F)" % ph.name, ok))


def check_propagation(project, results):
    """4. Editing the parent's F moves the child's F and W."""
    done = False
    for ph in _children(project):
        parent = ph.based_on
        for i in range(ph.probabilities.n_independents):
            if ph.probabilities.is_f_inherited(i):
                before_f = ph.probabilities.f_value(i)
                before_w = ph.probabilities.get_distribution_array().copy()
                parent.probabilities.set_f(i, before_f * 0.5 + 0.05)
                moved = (ph.probabilities.f_value(i) != before_f
                         and not np.allclose(ph.probabilities.get_distribution_array(),
                                             before_w))
                parent.probabilities.set_f(i, before_f)  # restore
                restored = (ph.probabilities.f_value(i) == before_f)
                results.append(("4 %s F%d follows the parent's edit"
                                % (ph.name, i + 1), moved and restored))
                done = True
                break
        if done:
            break
    results.append(("4 propagation exercised", done))


def check_refinables_skip(project, results):
    """5. Inherited F / sigma* / CSDS are not refinable on the child."""
    checked = False
    for ph in project.phases:
        labels = {r.label for r in _phase_refinables(ph)}
        for i in range(ph.probabilities.n_independents):
            label = "%s | F%d" % (ph.name, i + 1)
            if ph.probabilities.is_f_inherited(i):
                results.append(("5 skip %s" % label, label not in labels))
                checked = True
            else:
                results.append(("5 keep %s" % label, label in labels))
        for attr, lbl in (("sigma_star", "sigma*"), ("CSDS", "CSDS mean")):
            label = "%s | %s" % (ph.name, lbl)
            if ph.is_inherited(attr):
                results.append(("5 skip %s" % label, label not in labels))
                checked = True
            else:
                results.append(("5 keep %s" % label, label in labels))
    results.append(("5 inherited-skip exercised", checked))


def check_roundtrip(path, results):
    """6. based_on + flags survive; the child re-serialises its OWN stale F."""
    project = load_mud(path)
    before = {}
    for ph in _children(project):
        before[ph.uuid] = (
            ph.based_on.uuid,
            list(ph.probabilities.own_f_params()),
            list(ph.probabilities.inherit_F),
            ph.inherit_sigma_star,
            ph.inherit_CSDS_distribution,
        )
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_pinh_%d.mud" % os.getpid())
    try:
        save_mud(project, tmp)
        reloaded = load_mud(tmp)
        after = {p.uuid: p for p in _children(reloaded)}
        results.append(("6 same # based_on phases", len(after) == len(before)))
        for uid, (puuid, own_f, inh_f, i_sig, i_csds) in before.items():
            ph = after.get(uid)
            ok = (ph is not None
                  and ph.based_on is not None
                  and ph.based_on.uuid == puuid
                  and list(ph.probabilities.own_f_params()) == own_f
                  and list(ph.probabilities.inherit_F) == inh_f
                  and ph.inherit_sigma_star == i_sig
                  and ph.inherit_CSDS_distribution == i_csds)
            results.append(("6 %-14s survives (own F kept stale)"
                            % (ph.name if ph else uid), ok))
    finally:
        for p in (tmp, tmp + "~"):
            if os.path.exists(p):
                os.remove(p)


def run(path):
    print("=" * 72)
    print("Phase-level inheritance:", os.path.basename(path))
    print("=" * 72)
    results = []
    project = load_mud(path)
    if not _children(project):
        print("  (no based_on phases in this project - skipping)\n")
        return True, 0, False
    check_resolve(project, results)
    discriminating = check_read_through(project, results)
    check_matrices_follow(project, results)
    check_propagation(project, results)
    check_refinables_skip(project, results)
    check_roundtrip(path, results)
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    if discriminating:
        print("  (this project DISCRIMINATES: an inherited F differs from the"
              " child's stale stored value)")
    print("-" * 72)
    print("%d/%d checks passed" % (passed, len(results)))
    return passed == len(results), len(results), discriminating


def main(argv):
    paths = argv[1:] or _default_projects()
    existing = [p for p in paths if os.path.isfile(p)]
    if not existing:
        print("No sample projects found; skipping (exit 2).")
        return 2
    all_ok, total, any_discriminating = True, 0, False
    for path in existing:
        ok, n, disc = run(path)
        all_ok = all_ok and ok
        total += n
        any_discriminating = any_discriminating or disc
        print()
    # At least ONE fixture must make inheritance observable, otherwise this
    # harness could pass with the read-through silently broken.
    print("=" * 72)
    print("  %s  a discriminating fixture exists (inherited F != stale stored F)"
          % ("PASS" if any_discriminating else "FAIL"))
    all_ok = all_ok and any_discriminating
    total += 1
    print("Phase-inheritance harness: %d checks across %d project(s): %s"
          % (total, len(existing), "OK" if all_ok else "REGRESSION"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
