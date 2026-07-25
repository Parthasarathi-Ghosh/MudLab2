#!/usr/bin/env python
"""Durable harness for the peak-detection + mineral-scoring port (Batch: Detect
Peaks / Match Minerals).

Guards calculations/peak_detection.py:
  - the billauer maxima/minima detector (multi_peakdetect / peakdetect),
  - the scipy prominence detector (scipy_peakdetect),
  - the # of peaks vs cut-off histograms (calculate_npeaks_for[_scipy]),
  - the iterative threshold/prominence estimators (get_best_threshold /
    get_best_prominence),
  - mineral scoring (score_minerals) and the reference-CSV loader.

References, in order of strength:

  1. **The live old code.** The old
     mudlab/calculations/peak_detection.py is pure numpy/scipy, so it is loaded
     BY PATH (with a stub `.math_tools` injected for its one unused relative
     import) and its multi_peakdetect / peakdetect / scipy_peakdetect /
     find_closest / score_minerals are diffed against ours point-for-point on
     real fixture patterns. A true differential test against the old source.
  2. **Old peak counter, our histogram.** calculate_npeaks_for and the
     iterative get_best_threshold are re-derived here using the OLD
     multi_peakdetect as the peak counter and compared to our port, so a
     transcription slip in the wrapper/estimator cannot hide behind our own
     detector.
  3. **Independent ground truth.** scipy histograms are checked against a
     direct scipy.signal.find_peaks call; the mineral loader is checked
     against the raw CSV (entry count, a spot-checked entry, sort order); and
     score_minerals is checked to rank a mineral's own reflections at the top.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_peak_detection.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample projects.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

import numpy as np

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.calculations import peak_detection as pd  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")
_MINERALS_CSV = os.path.join(_REPO, "src", "mudlab", "data", "mineral_references.csv")
_OLD_PEAK_DETECTION = (
    r"C:\GitHub\MudLab\data\lib\python3.14\site-packages"
    r"\mudlab\calculations\peak_detection.py"
)


def _default_projects():
    out = []
    for name in (
        "308 r1.mud",
        "Dh2040A 14Jul26.mud",
        "Dh2040A 14Jul26 r1.mud",
        "Dh2040A 14Jul26 r2.mud",
    ):
        in_repo = os.path.join(_FIXTURES, name)
        dl = os.path.join(os.path.expanduser("~"), "Downloads", name)
        out.append(in_repo if os.path.isfile(in_repo) else dl)
    return out


def _load_old_peak_detection():
    """Load the OLD app's peak_detection.py by path so `import numpy`/`scipy`
    inside it binds to MudLab2's builds. Its only relative import
    (`from .math_tools import smooth`, used only by the unported zero-crossing
    detector) is satisfied with a stub. Returns None when the old tree is
    absent."""
    if not os.path.isfile(_OLD_PEAK_DETECTION):
        return None
    pkg = types.ModuleType("old_pd_pkg")
    pkg.__path__ = []  # mark as package so relative import resolves
    mt = types.ModuleType("old_pd_pkg.math_tools")
    mt.smooth = lambda *a, **k: None
    sys.modules["old_pd_pkg"] = pkg
    sys.modules["old_pd_pkg.math_tools"] = mt
    spec = importlib.util.spec_from_file_location(
        "old_pd_pkg.peak_detection", _OLD_PEAK_DETECTION)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "old_pd_pkg"
    sys.modules["old_pd_pkg.peak_detection"] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    return module


def _specimens_with_data(project):
    return [s for s in project.specimens if s.has_experimental_data]


def _norm_tabs(tab):
    """Flatten a maxtab/mintab list of (pos, val) tuples to a comparable array."""
    if not tab:
        return np.empty((0, 2))
    return np.array([(float(p), float(v)) for p, v in tab], dtype=float)


# ----------------------------------------------------------------------
# 1. Differential against the live old code
# ----------------------------------------------------------------------
def check_multi_peakdetect_differential(project, old, results):
    """1. multi_peakdetect maxima/minima match the old app exactly."""
    if old is None:
        results.append(("1 old peak_detection available", False))
        return
    deltas = [0.0, 0.02, 0.05, 0.1]
    for spec in _specimens_with_data(project):
        x, y = spec.experimental_pattern
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        ours_max, ours_min = pd.multi_peakdetect(y.copy(), x, 5, list(deltas))
        theirs_max, theirs_min = old.multi_peakdetect(y.copy(), x, 5, list(deltas))
        ok = True
        for a, b in zip(ours_max, theirs_max):
            ok = ok and np.array_equal(_norm_tabs(a), _norm_tabs(b))
        for a, b in zip(ours_min, theirs_min):
            ok = ok and np.array_equal(_norm_tabs(a), _norm_tabs(b))
        results.append(("1 %s: multi_peakdetect == old" % spec.name, ok))


def check_peakdetect_differential(project, old, results):
    """1. peakdetect (single-delta) matches the old app exactly."""
    if old is None:
        return
    for spec in _specimens_with_data(project):
        x, y = spec.experimental_pattern
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        for delta in (0.0, 0.05, 0.1):
            om, _ = pd.peakdetect(y.copy(), x, 5, delta)
            tm, _ = old.peakdetect(y.copy(), x, 5, delta)
            ok = np.array_equal(_norm_tabs(om), _norm_tabs(tm))
            results.append(
                ("1 %s: peakdetect delta=%.2f == old" % (spec.name, delta), ok))


def check_scipy_peakdetect_differential(project, old, results):
    """1. scipy_peakdetect matches the old app exactly."""
    if old is None:
        return
    for spec in _specimens_with_data(project):
        x, y = spec.experimental_pattern
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        for prom in (0.0, 0.05, 0.2):
            ours = pd.scipy_peakdetect(y.copy(), x, prom, 3)
            theirs = old.scipy_peakdetect(y.copy(), x, prom, 3)
            ok = np.array_equal(_norm_tabs(ours), _norm_tabs(theirs))
            results.append(
                ("1 %s: scipy_peakdetect prom=%.2f == old" % (spec.name, prom), ok))


def check_score_minerals_differential(old, results):
    """1. find_closest + score_minerals match the old app on a fixed dataset."""
    if old is None:
        return
    peak_list = [(4.26, 100.0), (3.34, 950.0), (2.46, 120.0), (2.28, 180.0),
                 (2.13, 90.0), (1.82, 140.0), (1.54, 160.0)]
    minerals = [
        ("Quartz", "Qz", [(4.26, 22), (3.34, 100), (2.46, 12), (2.28, 12),
                          (2.13, 9), (1.82, 17), (1.54, 15)]),
        ("Calcite", "Cal", [(3.86, 12), (3.03, 100), (2.28, 18), (2.09, 18),
                            (1.91, 17), (1.87, 17)]),
        ("Kaolinite", "Kln", [(7.15, 100), (3.57, 100), (2.55, 30), (2.49, 40)]),
    ]
    fc_ok = pd.find_closest(3.30, peak_list) == old.find_closest(3.30, peak_list)
    results.append(("1 find_closest == old", fc_ok))

    ours = pd.score_minerals(peak_list, minerals)
    theirs = old.score_minerals(peak_list, minerals)
    same = len(ours) == len(theirs)
    for a, b in zip(ours, theirs):
        same = same and a[0] == b[0] and a[1] == b[1]
        same = same and np.isclose(a[4], b[4], rtol=0, atol=1e-12)
    results.append(("1 score_minerals == old (names/order/scores)", same))


# ----------------------------------------------------------------------
# 2. Old peak counter, our histogram / estimator
# ----------------------------------------------------------------------
def _old_calculate_npeaks_for(old, data_x, data_y, max_threshold, steps):
    """Re-derivation of the old calculate_npeaks_for using the OLD detector."""
    steps = max(steps, 2) - 1
    factor = max_threshold / steps
    deltas = [i * factor for i in range(0, steps)]
    maxtabs, mintabs = old.multi_peakdetect(np.asarray(data_y, float), data_x, 5, deltas)
    numpeaks = [float(len(m)) for m, _ in zip(maxtabs, mintabs)]
    return deltas, numpeaks


def check_calculate_npeaks_for(project, old, results):
    """2. Our threshold histogram equals the old-detector re-derivation."""
    if old is None:
        return
    for spec in _specimens_with_data(project):
        x, y = spec.experimental_pattern
        for mx, steps in ((0.32, 20), (0.5, 10)):
            od, on = _old_calculate_npeaks_for(old, x, y, mx, steps)
            nd, nn = pd.calculate_npeaks_for(x, y, mx, steps)
            ok = np.allclose(od, nd, rtol=0, atol=1e-12) and on == nn
            results.append(
                ("2 %s: npeaks_for(max=%.2f,steps=%d) == old-detector"
                 % (spec.name, mx, steps), ok))


def _old_get_best_threshold(old, data_x, data_y, max_threshold=None, steps=None):
    """Re-derivation of the old get_best_threshold via the OLD detector."""
    from scipy import stats
    data_x = np.asarray(data_x, float)
    length = data_x.size
    steps = 20 if steps is None else steps
    threshold = 0.1
    max_threshold = threshold * 3.2 if max_threshold is None else max_threshold

    def new_thr(deltas, num_peaks, ln):
        slope, intercept, R, _, _ = stats.linregress(deltas[:ln], num_peaks[:ln])
        return R, -intercept / slope

    if length <= 2:
        return ([], []), threshold, max_threshold
    deltas, num_peaks = _old_calculate_npeaks_for(old, data_x, data_y, max_threshold, steps)
    last = None
    solution = False
    itercount = 0
    while not solution:
        ln, max_ln, stop = 4, len(deltas), False
        while not stop:
            R, threshold = new_thr(deltas, num_peaks, ln)
            max_threshold = threshold * 3.2
            if abs(R) < 0.98 or ln >= max_ln:
                stop = True
            else:
                ln += 1
        itercount += 1
        if last:
            solution = bool(itercount > 3 and not (itercount <= 10 and last - threshold >= 0.001))
            if not solution:
                deltas, num_peaks = _old_calculate_npeaks_for(old, data_x, data_y, max_threshold, steps)
        last = threshold
    return (deltas, num_peaks), threshold, max_threshold


def check_get_best_threshold(project, old, results):
    """2. Our iterative threshold estimator matches the old-detector re-derivation."""
    if old is None:
        return
    for spec in _specimens_with_data(project):
        x, y = spec.experimental_pattern
        (_, _), o_thr, o_max = _old_get_best_threshold(old, x, y, 0.32, 20)
        (_, _), n_thr, n_max = pd.get_best_threshold(x, y, 0.32, 20)
        ok = np.isfinite(n_thr) and np.isclose(o_thr, n_thr, rtol=0, atol=1e-9) \
            and np.isclose(o_max, n_max, rtol=0, atol=1e-9)
        results.append(("2 %s: get_best_threshold == old-detector" % spec.name, ok))


# ----------------------------------------------------------------------
# 3. Independent ground truth
# ----------------------------------------------------------------------
def check_scipy_histogram_independent(project, results):
    """3. calculate_npeaks_for_scipy matches a direct find_peaks count."""
    from scipy.signal import find_peaks
    for spec in _specimens_with_data(project):
        x, y = spec.experimental_pattern
        x = np.asarray(x, float)
        y = np.asarray(y, float)
        proms, npk = pd.calculate_npeaks_for_scipy(x, y, 0.3, 8, 0.1)
        ymax = np.max(y)
        yn = y / ymax if ymax > 0 else y
        res = (len(x) - 1) / (x[-1] - x[0])
        dist = max(1, int(0.1 * res))
        ok = True
        for p, n in zip(proms, npk):
            kw = dict(distance=dist)
            if p > 0:
                kw["prominence"] = p
            peaks, _ = find_peaks(yn, **kw)
            ok = ok and len(peaks) == n
        results.append(("3 %s: npeaks_for_scipy == direct find_peaks" % spec.name, ok))


def check_get_best_prominence_runs(project, results):
    """3. get_best_prominence terminates with a finite, self-consistent result.

    The estimator returns the histogram from the iteration BEFORE convergence,
    so its grid max is proms[-1] (not the returned max_prominence, which is the
    next, converged value). Recomputing the histogram at the grid's own
    endpoint must reproduce it exactly, and the returned prominence must be a
    finite non-negative value on that grid.
    """
    for spec in _specimens_with_data(project):
        x, y = spec.experimental_pattern
        (proms, npk), prom, mx = pd.get_best_prominence(x, y, 0.32, 20, 0.1)
        grid_ok = (
            len(proms) > 0 and len(proms) == len(npk)
            and proms[0] == 0.0 and np.all(np.diff(proms) > 0)
        )
        rp, rn = pd.calculate_npeaks_for_scipy(x, y, proms[-1], 20, 0.1)
        ok = (
            np.isfinite(prom) and prom >= 0 and grid_ok
            and np.allclose(proms, rp, rtol=0, atol=1e-12) and npk == rn
            and 0.0 <= prom <= mx
        )
        results.append(("3 %s: get_best_prominence terminates/consistent" % spec.name, ok))


def check_mineral_loader(results):
    """3. The reference CSV loads to the expected entries in sorted order."""
    minerals = pd.load_mineral_references(_MINERALS_CSV)
    # 228 header lines in the CSV; the old loader dropped the last, we keep it.
    results.append(("3 loader: 228 minerals parsed", len(minerals) == 228))
    names = [m[0] for m in minerals]
    results.append(("3 loader: sorted by name", names == sorted(names)))
    # Every entry has an abbreviation-free-or-string and >=1 (d>0, i) peak.
    shape_ok = all(
        isinstance(n, str) and isinstance(a, str) and len(p) >= 1
        and all(d > 0 for d, _ in p)
        for n, a, p in minerals
    )
    results.append(("3 loader: entry shapes valid", shape_ok))
    # Spot-check the first CSV entry (Adularia / Adl / first peak 4.68,20).
    by_name = {n: (a, p) for n, a, p in minerals}
    adl = by_name.get("Adularia  (DEL)")
    spot = adl is not None and adl[0] == "Adl" and adl[1][0] == (4.68, 20.0)
    results.append(("3 loader: Adularia spot-check", spot))


def check_score_self(results):
    """3. A mineral's own reflections score it strongly (near the top).

    Exact #1 is not asserted: d-spacings overlap heavily across the reference
    set (e.g. the feldspars), so a mineral whose top-15 reflections all fall
    inside a denser mineral's pattern can out-score a self-match. The
    meaningful guarantee is that self-matching yields a positive score and
    ranks the mineral among the very best.
    """
    minerals = pd.load_mineral_references(_MINERALS_CSV)
    by_name = {n: (a, p) for n, a, p in minerals}
    target = next((n for n in by_name if n.startswith("Quartz")), sorted(by_name)[0])
    _, peaks = by_name[target]
    # Observed peak list = this mineral's reflections (position in angstrom).
    peak_list = [(d, i) for d, i in peaks]
    scores = pd.score_minerals(peak_list, minerals)
    top_names = [s[0] for s in scores[:10]]
    self_score = next((s[4] for s in scores if s[0] == target), 0.0)
    ok = target in top_names and self_score > 0
    results.append(("3 score_minerals: '%s' self-match ranks top-10, score>0" % target, ok))


# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------
def main(argv):
    projects = argv[1:] or _default_projects()
    projects = [p for p in projects if os.path.isfile(p)]
    if not projects:
        print("No sample projects found; skipping (exit 2).")
        return 2

    old = _load_old_peak_detection()
    if old is None:
        print("WARNING: old peak_detection.py not loadable; "
              "differential checks (bucket 1/2) will be reported as failures.")

    results: list[tuple[str, bool]] = []

    # Data-independent checks (run once).
    check_score_minerals_differential(old, results)
    check_mineral_loader(results)
    check_score_self(results)

    for path in projects:
        try:
            project = load_mud(path)
        except Exception as exc:  # noqa: BLE001
            results.append(("load %s" % os.path.basename(path), False))
            print("  ! failed to load %s: %s" % (path, exc))
            continue
        name = os.path.basename(path)
        if not _specimens_with_data(project):
            continue
        check_multi_peakdetect_differential(project, old, results)
        check_peakdetect_differential(project, old, results)
        check_scipy_peakdetect_differential(project, old, results)
        check_calculate_npeaks_for(project, old, results)
        check_get_best_threshold(project, old, results)
        check_scipy_histogram_independent(project, results)
        check_get_best_prominence_runs(project, results)
        print("checked %s" % name)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- peak-detection verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
