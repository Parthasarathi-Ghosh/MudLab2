#!/usr/bin/env python
"""Durable regression harness for the pattern-calculation engine.

Recomputes each sample project's calculated diffractogram from scratch
(atoms -> structure factors -> CSDS -> Markovian stacking -> phase
intensity -> mixture) and compares it against the calculated pattern the
OLD GTK MudLab stored inside the .mud - the reference implementation's own
output, i.e. the gold standard. A match therefore validates the whole
calc-engine port (batches 1-6) end to end.

Run with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_calc_engine.py
    ./python/python.exe tools/verify_calc_engine.py "a.mud" "b.mud"

No QApplication is needed (the models are plain QObjects), so this runs
head-less without QT_QPA_PLATFORM. Exit codes:

    0  every checked specimen is within tolerance
    1  a regression (some specimen drifted from the stored pattern)
    2  no sample projects found - nothing was verified

The two default sample projects are kept locally under tools/sample_projects/
- gitignored (the user's own data, never committed or distributed) - with a
fallback to ~/Downloads; pass paths on the command line to point elsewhere.
"""

from __future__ import annotations

import json
import os
import sys
import zipfile

import numpy as np

# Make `mudlab` importable regardless of the current working directory.
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

# Default sample projects: the in-repo fixtures come first so the harness is
# self-contained; the original Downloads copies are kept as a fallback for
# machines where the fixtures were not committed. Override on the command
# line to point at other projects.
_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")


def _default_projects():
    # Dh537A.mud is the R1G2 fixture (three IS R1 Ca-* phases): it is the
    # golden-calc proof that R1 stacking is modeled - the R0-fallback failed it
    # at corr 0.984, the R1G2 model reproduces it at corr 1.000000.
    names = ["308 r1.mud", "Dh2040A 14Jul26.mud", "Dh2040A 14Jul26 r1.mud",
             "Dh2040A 14Jul26 r2.mud", "Dh537A.mud"]
    projects = []
    for name in names:
        in_repo = os.path.join(_FIXTURES, name)
        downloads = os.path.join(
            os.path.expanduser("~"), "Downloads", name
        )
        projects.append(in_repo if os.path.isfile(in_repo) else downloads)
    return projects


DEFAULT_PROJECTS = _default_projects()

# Pass/fail tolerances, normalised to the reference pattern's peak. The
# known-good state matches to RMS ~1e-7 for 5/6 sample specimens and ~1e-4
# for the 6th (its stored curve is slightly stale); 1e-3 leaves a healthy
# margin over that while still catching real regressions.
RMS_TOL = 1e-3
CORR_TOL = 0.999


def stored_calc(path):
    """{specimen_uuid: (two_theta, total_intensity)} for every specimen in
    the .mud that carries a usable stored calculated pattern (column 0 is
    2-theta, column 1 the total; later columns are per-phase)."""
    out = {}
    with zipfile.ZipFile(path) as archive:
        if "specimens" not in archive.namelist():
            return out
        specimens = json.loads(archive.read("specimens").decode("utf-8"))
    for spec in specimens:
        props = spec.get("properties", {})
        cal = props.get("calculated_pattern")
        if isinstance(cal, dict):
            rows = json.loads(cal.get("properties", {}).get("data") or "[]")
            arr = np.asarray(rows, dtype=float)
            if arr.ndim == 2 and arr.shape[0] > 1 and arr.shape[1] >= 2:
                out[props.get("uuid")] = (arr[:, 0], arr[:, 1])
    return out


def check_project(path):
    """Recompute and compare one project. Returns (n_checked, n_failed)."""
    print("=" * 72)
    print(os.path.basename(path))
    project = load_mud(path)
    gold = stored_calc(path)
    print("  phases=%d  specimens=%d  mixtures=%d  stored-calc specimens=%d"
          % (len(project.phases), len(project.specimens),
             len(project.mixtures), len(gold)))

    n_checked = n_failed = 0
    for mix in project.mixtures:
        print("  mixture %r: %d specimens x %d phase slots %s  fractions=%s"
              % (mix.name, mix.n, mix.m, mix.phase_labels,
                 np.array2string(mix.fractions, precision=3)))
        mix.calculate()  # recompute + store each specimen's calculated pattern

        for i, spec in enumerate(mix.specimens):
            if spec is None:
                print("    [slot %d] specimen did not resolve (uuid missing)" % i)
                continue
            ref = gold.get(spec.uuid)
            if ref is None:
                print("    %-12s no stored pattern to compare against" % spec.name)
                continue
            _, mine = spec.calculated_pattern
            _, refy = ref
            n = min(len(mine), len(refy))
            mine, refy = mine[:n], refy[:n]
            denom = float(np.max(np.abs(refy))) or 1.0
            rms = float(np.sqrt(np.mean((mine - refy) ** 2)) / denom)
            maxerr = float(np.max(np.abs(mine - refy)) / denom)
            corr = float(np.corrcoef(mine, refy)[0, 1]) if n > 1 else 1.0
            ok = rms <= RMS_TOL and corr >= CORR_TOL
            n_checked += 1
            n_failed += not ok
            print("    %-12s %s  scale=%.4f bg=%.3f | RMS=%.2e maxerr=%.2e "
                  "corr=%.6f" % (spec.name, "PASS" if ok else "FAIL",
                                 mix.scales[i], mix.bgshifts[i], rms, maxerr, corr))
    return n_checked, n_failed


def main(argv):
    projects = argv[1:] or DEFAULT_PROJECTS
    total_checked = total_failed = 0
    missing = 0

    for path in projects:
        if not os.path.isfile(path):
            print("SKIP (not found): %s" % path)
            missing += 1
            continue
        checked, failed = check_project(path)
        total_checked += checked
        total_failed += failed

    print("=" * 72)
    if total_checked == 0:
        print("NOTHING VERIFIED - no sample projects were found.")
        print("Pass .mud paths on the command line, e.g.:")
        print("  ./python/python.exe tools/verify_calc_engine.py path/to/project.mud")
        return 2

    print("Checked %d specimen pattern(s) across %d project(s): %d passed, %d FAILED"
          % (total_checked, len(projects) - missing,
             total_checked - total_failed, total_failed))
    print("tolerances: normalised RMS <= %.0e, correlation >= %.4f"
          % (RMS_TOL, CORR_TOL))
    return 1 if total_failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
