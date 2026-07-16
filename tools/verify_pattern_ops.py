#!/usr/bin/env python
"""Durable harness for the experimental-pattern operations (Batch D1).

Guards calculations/pattern_ops.py + the Specimen methods that apply them:
background removal, smoothing, noise, shifting, peak stripping, peak
properties and trim.

Unlike the phase/inheritance harnesses there is no golden .mud to diff
against - the old app applies these operations destructively and stores only
the result, so a processed pattern carries no record of what produced it.
Verification therefore leans on three independent references instead:

  1. **The live old code.** The old mudlab/calculations/math_tools.py is pure
     numpy, so it is loaded BY PATH (the old tree's numpy is a MinGW build
     that will not import here) and its smooth()/add_noise() are diffed
     against ours point-for-point on real fixture patterns. This is a true
     differential test against the old app's own source.
  2. **Analytic ground truth.** Peak area and FWHM are checked on a synthetic
     Gaussian whose area (A*sigma*sqrt(2*pi)) and FWHM (2*sqrt(2*ln2)*sigma)
     are known in closed form, and the displacement shift is checked against
     the Bragg/geometry formula evaluated independently. Neither reference
     comes from the port, so a transcription error cannot hide.
  3. **Invariants on real fixture data.** No-op guards, range containment,
     marker/exclusion handling and non-destructiveness of the preview
     (compute_*) calls.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_pattern_ops.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample projects.
"""

from __future__ import annotations

import importlib.util
import math
import os
import sys
import tempfile

import numpy as np

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.calculations import pattern_ops  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.models.marker import Marker  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")
_OLD_MATH_TOOLS = (
    r"C:\GitHub\MudLab\data\lib\python3.14\site-packages"
    r"\mudlab\calculations\math_tools.py"
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


def _load_old_math_tools():
    """Load the OLD app's math_tools by path so `import numpy` inside it binds
    to MudLab2's numpy. Returns None when the old tree is not present."""
    if not os.path.isfile(_OLD_MATH_TOOLS):
        return None
    spec = importlib.util.spec_from_file_location("old_math_tools", _OLD_MATH_TOOLS)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    return module


def _specimens_with_data(project):
    return [s for s in project.specimens if s.has_experimental_data]


# ----------------------------------------------------------------------
# 1. Differential against the live old code
# ----------------------------------------------------------------------
def check_old_smooth_differential(project, old, results):
    """1. Blackman smoothing matches the old app's math_tools.smooth exactly."""
    if old is None:
        results.append(("1 old math_tools available", False))
        return
    for spec in _specimens_with_data(project):
        _, y = spec.experimental_pattern
        for degree in (3, 5, 10):
            ours = pattern_ops.smooth_data(y, pattern_ops.SMOOTH_BLACKMAN, degree)
            theirs = old.smooth(np.asarray(y, dtype=float), degree)
            same = ours.shape == theirs.shape and np.allclose(ours, theirs, rtol=0, atol=1e-12)
            results.append(
                ("1 %s: blackman deg=%d == old math_tools.smooth"
                 % (spec.name, degree), same)
            )


def check_old_noise_differential(project, old, results):
    """1. add_noise matches the old app's add_noise for the same RNG draw."""
    if old is None:
        return
    for spec in _specimens_with_data(project):
        _, y = spec.experimental_pattern
        y = np.asarray(y, dtype=float)
        np.random.seed(42)
        ours = pattern_ops.add_noise(y, 0.05)
        np.random.seed(42)
        theirs = old.add_noise(y, 0.05)
        same = np.allclose(ours, theirs, rtol=0, atol=1e-12)
        results.append(("1 %s: add_noise == old math_tools.add_noise" % spec.name, same))


# ----------------------------------------------------------------------
# 2. Analytic ground truth
# ----------------------------------------------------------------------
def check_peak_properties_analytic(results):
    """2. Area/FWHM of a synthetic Gaussian match the closed-form values."""
    # A Gaussian peak on a sloping background: area and FWHM are known exactly,
    # and the sloping background exercises the endpoint-line subtraction.
    amplitude, centre, sigma = 500.0, 10.0, 0.25
    x = np.linspace(6.0, 14.0, 4001)
    peak = amplitude * np.exp(-((x - centre) ** 2) / (2 * sigma ** 2))
    background = 20.0 + 3.0 * (x - x[0])
    y = peak + background

    props = pattern_ops.compute_peak_properties(x, y, 8.0, 12.0)
    results.append(("2 peak properties computed on a Gaussian", props is not None))
    if props is None:
        return

    expected_area = amplitude * sigma * math.sqrt(2 * math.pi)
    expected_fwhm = 2.0 * math.sqrt(2.0 * math.log(2.0)) * sigma
    area_err = abs(props.area - expected_area) / expected_area
    fwhm_err = abs(props.fwhm - expected_fwhm) / expected_fwhm
    results.append(
        ("2 area %.3f ~= analytic %.3f (%.4f%%)"
         % (props.area, expected_area, area_err * 100), area_err < 1e-3)
    )
    results.append(
        ("2 FWHM %.5f ~= analytic %.5f (%.4f%%)"
         % (props.fwhm, expected_fwhm, fwhm_err * 100), fwhm_err < 1e-3)
    )
    # The measurement must not alter the pattern.
    results.append(("2 peak properties leave y untouched",
                    np.array_equal(y, peak + background)))


def check_shift_analytic(results):
    """2. The displacement correction matches the geometry formula, and the
    linear mode is an exact constant offset."""
    x = np.linspace(3.0, 45.0, 2101)
    shift_value, shift_position, radius, wl = 0.03, 0.42574, 24.0, 0.154056

    # Linear: a plain constant subtraction.
    linear = pattern_ops.apply_shift(
        x, shift_value, shift_position, radius, wl, shift_type="Linear"
    )
    results.append(("2 linear shift == x - shift_value",
                    np.allclose(linear, x - shift_value, atol=1e-12)))

    # Displacement: recompute the physics independently here.
    position_t = math.degrees(math.asin(wl / (2.0 * shift_position)))
    displacement = 0.5 * radius * shift_value / math.cos(math.radians(position_t))
    expected = x - 2 * displacement * np.cos(np.radians(x / 2.0)) / radius
    got = pattern_ops.apply_shift(
        x, shift_value, shift_position, radius, wl, shift_type="Displacement"
    )
    results.append(("2 displacement shift == geometry formula",
                    np.allclose(got, expected, atol=1e-12)))
    # The correction must shrink as 2-theta grows (that is the whole point of
    # modelling displacement rather than a flat offset).
    corr = x - got
    results.append(("2 displacement correction decreases with 2-theta",
                    bool(np.all(np.diff(corr) < 0))))


def check_detect_shift_synthetic(results):
    """2. detect_shift recovers a known offset planted in a synthetic peak."""
    wl, shift_position = 0.154056, 0.42574
    true_2t = math.degrees(math.asin(wl / (2.0 * shift_position))) * 2.0
    planted = 0.12
    x = np.linspace(true_2t - 3.0, true_2t + 3.0, 6001)
    y = 100.0 * np.exp(-((x - (true_2t + planted)) ** 2) / (2 * 0.05 ** 2))
    detected = pattern_ops.detect_shift(x, y, shift_position, wl)
    results.append(
        ("2 detect_shift recovers planted offset %.3f (got %.4f)" % (planted, detected),
         abs(detected - planted) < 0.01)
    )
    results.append(("2 detect_shift returns 0 in manual mode",
                    pattern_ops.detect_shift(x, y, 0.0, wl) == 0.0))


# ----------------------------------------------------------------------
# 3. Invariants on real fixture data
# ----------------------------------------------------------------------
def check_noop_guards(project, results):
    """3. Zero-valued parameters change nothing (the old app resets the
    parameter to 0 after applying, so a second OK must be inert)."""
    for spec in _specimens_with_data(project):
        _, y = spec.experimental_pattern
        y = np.asarray(y, dtype=float)
        results.append(("3 %s: smooth degree=0 is a no-op" % spec.name,
                        np.array_equal(pattern_ops.smooth_data(y, 0, 0.0), y)))
        results.append(("3 %s: noise fraction=0 is a no-op" % spec.name,
                        np.array_equal(pattern_ops.add_noise(y, 0.0), y)))
        results.append(("3 %s: linear bg position=0 is a no-op" % spec.name,
                        np.array_equal(
                            pattern_ops.remove_background(y, pattern_ops.BG_LINEAR, 0.0), y)))
        results.append(("3 %s: pattern bg with no pattern is a no-op" % spec.name,
                        np.array_equal(
                            pattern_ops.remove_background(
                                y, pattern_ops.BG_PATTERN, 5.0, None, 1.0), y)))


def check_background(project, results):
    """3. Linear background subtraction floors the pattern at zero when the
    position is the pattern minimum (find_bg_position's suggestion)."""
    for spec in _specimens_with_data(project):
        _, y = spec.experimental_pattern
        y = np.asarray(y, dtype=float)
        bg = pattern_ops.find_bg_position(y)
        out = pattern_ops.remove_background(y, pattern_ops.BG_LINEAR, bg)
        results.append(("3 %s: find_bg_position == min(y)" % spec.name,
                        bg == float(np.min(y))))
        results.append(("3 %s: subtracting min(y) floors at 0" % spec.name,
                        abs(float(np.min(out))) < 1e-9 and bool(np.all(out >= -1e-9))))
        # Pattern mode: subtracting the pattern from itself flattens it.
        out = pattern_ops.remove_background(y, pattern_ops.BG_PATTERN, 0.0, y, 1.0)
        results.append(("3 %s: pattern bg (scale=1, self) flattens to 0" % spec.name,
                        bool(np.allclose(out, 0.0, atol=1e-9))))
        results.append(("3 %s: remove_background leaves the input array alone"
                        % spec.name, y is not out))


def check_smooth_types(project, results):
    """3. Every smoothing type returns a same-length, finite, less-noisy
    pattern (the point of smoothing is reduced point-to-point scatter)."""
    for spec in _specimens_with_data(project)[:1]:  # one specimen is enough
        _, y = spec.experimental_pattern
        y = np.asarray(y, dtype=float)
        roughness = float(np.std(np.diff(y)))
        for stype in range(6):
            degree = pattern_ops.default_smooth_degree(stype)
            out = pattern_ops.smooth_data(y, stype, degree)
            ok_shape = out.shape == y.shape and bool(np.all(np.isfinite(out)))
            results.append(("3 type %d: same length + finite" % stype, ok_shape))
            if ok_shape:
                results.append(
                    ("3 type %d: reduces point-to-point scatter" % stype,
                     float(np.std(np.diff(out))) < roughness)
                )


def check_strip(project, results):
    """3. Stripping replaces only the selected window, and leaves it close to
    the straight line joining the endpoints."""
    for spec in _specimens_with_data(project):
        x, y = spec.experimental_pattern
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        # Pick a window inside the pattern.
        startx = float(x[len(x) // 3])
        endx = float(x[len(x) // 3 + 40])
        strip = pattern_ops.compute_strip_pattern(x, y, startx, endx)
        results.append(("3 %s: strip pattern computed" % spec.name, strip is not None))
        if strip is None:
            continue
        results.append(("3 %s: endpoints snap to real data points" % spec.name,
                        strip.startx in x and strip.endx in x))
        out = pattern_ops.apply_strip(x, y, strip)
        inside = (x >= strip.startx) & (x <= strip.endx)
        results.append(("3 %s: data outside the window is untouched" % spec.name,
                        np.array_equal(out[~inside], y[~inside])))
        results.append(("3 %s: apply_strip leaves the input array alone" % spec.name,
                        out is not y))
        # The patched section follows the endpoint line (within the noise it adds).
        line = strip.slope * (strip.section_x - strip.startx) + strip.avg_starty
        tolerance = abs(strip.avg_endy) * max(strip.noise_level, 1e-9) + 1e-6
        results.append(("3 %s: patched section tracks the endpoint line" % spec.name,
                        bool(np.all(np.abs(out[inside] - line) <= tolerance))))
        # A degenerate range is refused rather than producing garbage.
        results.append(("3 %s: zero-width range refused" % spec.name,
                        pattern_ops.compute_strip_pattern(x, y, startx, startx) is None))
        results.append(("3 %s: unset (0.0) endpoints refused" % spec.name,
                        pattern_ops.compute_strip_pattern(x, y, 0.0, 0.0) is None))
        # compute_* is a preview: it must not touch the data.
        results.append(("3 %s: compute_strip_pattern leaves y untouched" % spec.name,
                        np.array_equal(y, spec.experimental_pattern[1])))


def check_trim(path, results):
    """3. Trim clips the data and drops markers / exclusion ranges that fall
    outside or straddle the new boundary."""
    project = load_mud(path)
    for spec in _specimens_with_data(project):
        x, _ = spec.experimental_pattern
        lo = float(x[len(x) // 4])
        hi = float(x[3 * len(x) // 4])

        # Plant a marker inside and one outside, plus straddling / clean ranges.
        spec.add_marker(Marker(label="inside", position=(lo + hi) / 2))
        spec.add_marker(Marker(label="outside", position=float(x[0])))
        spec.set_exclusion_ranges([
            ((lo + hi) / 2 - 0.5, (lo + hi) / 2 + 0.5),  # fully inside: kept
            (lo - 1.0, lo + 1.0),                        # straddles lo: dropped
            (float(x[0]), float(x[1])),                  # fully outside: dropped
        ])

        n_before = len(x)
        ok = spec.trim(lo, hi)
        nx, ny = spec.experimental_pattern
        results.append(("3 %s: trim returns True" % spec.name, ok))
        results.append(("3 %s: trimmed pattern is shorter" % spec.name,
                        len(nx) < n_before and len(nx) == len(ny)))
        results.append(("3 %s: all points within [lo, hi]" % spec.name,
                        bool(np.all((nx >= lo) & (nx <= hi)))))
        names = [m.label for m in spec.markers]
        results.append(("3 %s: marker inside kept" % spec.name, "inside" in names))
        results.append(("3 %s: marker outside dropped" % spec.name,
                        "outside" not in names))
        results.append(("3 %s: only the fully-inside exclusion range survives"
                        % spec.name, len(spec.exclusion_ranges) == 1))
        if spec.has_calculated_data:
            cx, _ = spec.calculated_pattern
            results.append(("3 %s: calculated pattern clipped too" % spec.name,
                            bool(np.all((cx >= lo) & (cx <= hi)))))
        # An impossible range must change nothing.
        before = spec.experimental_pattern[0].copy()
        refused = spec.trim(hi, lo)  # inverted: leaves < 2 points
        results.append(("3 %s: impossible trim refused, data intact" % spec.name,
                        refused is False
                        and np.array_equal(before, spec.experimental_pattern[0])))


def check_ops_x_calc_engine(path, results):
    """3. The calculation engine survives an op reshaping a specimen.

    The ops change a specimen's shape (trim) or its 2-theta axis (shift); the
    calc path, the mixture and the refiner all hold assumptions about that
    shape. calculate_specimen_pattern follows the experimental grid when
    present, so a trimmed specimen must recalculate onto the trimmed grid
    rather than the goniometer's full range.
    """
    project = load_mud(path)
    if not project.mixtures:
        return
    mixture = project.mixtures[0]
    targets = [
        s for s in mixture.specimens
        if s is not None and s.has_experimental_data
    ]
    if not targets:
        return
    spec = targets[0]
    others = [s for s in targets if s is not spec]

    x, _ = spec.experimental_pattern
    spec.trim(float(x[len(x) // 4]), float(x[3 * len(x) // 4]))
    results.append(("3 residual computable on a trimmed specimen",
                    np.isfinite(mixture.current_residual())))

    mixture.calculate()
    ex, _ = spec.experimental_pattern
    cx, cy = spec.calculated_pattern
    results.append(("3 recalc lands on the TRIMMED grid, not the goniometer range",
                    np.array_equal(ex, cx)))
    results.append(("3 recalculated intensities are finite",
                    bool(np.all(np.isfinite(cy)))))
    results.append(("3 trimmed specimen still yields a real Rp (not 0.0)",
                    spec.statistics.Rp > 0))
    # One specimen's trim must not disturb its neighbours in the mixture.
    results.append(("3 trimming one specimen leaves the others intact",
                    all(len(s.experimental_pattern[0])
                        == len(s.calculated_pattern[0]) for s in others)))

    # The refiner enumerates structural parameters off the phases, not the
    # patterns, so a trim must not change the refinable set - and the residual
    # must still respond to one.
    from mudlab.calculations.refinement import enumerate_refinables

    refinables = enumerate_refinables(mixture)
    results.append(("3 refinables still enumerate after a trim",
                    len(refinables) > 0))
    if refinables:
        base = mixture.current_residual()
        # At least ONE refinable must move the residual - not any given one.
        # A phase at fraction 0 contributes nothing to the pattern, so its
        # parameters correctly move nothing (Dh2040A 14Jul26.mud carries an
        # Illite phase at fraction 0.0 for exactly this reason), and a
        # zero-valued parameter is unmoved by a multiplicative nudge.
        responsive = 0
        restored_ok = True
        for ref in refinables:
            original = ref.value
            ref.value = (original * 1.05) if original else 0.05
            if abs(mixture.current_residual() - base) > 1e-9:
                responsive += 1
            ref.value = original
            if abs(mixture.current_residual() - base) > 1e-9:
                restored_ok = False
                break
        results.append(
            ("3 residual responds to a refinable on a trimmed grid (%d/%d live)"
             % (responsive, len(refinables)), responsive > 0)
        )
        results.append(("3 restoring every refinable restores the residual",
                        restored_ok))


def check_specimen_wiring(path, results):
    """3. The Specimen methods mutate the pattern and emit data_changed once
    (the plot and the fit statistics both hang off that signal)."""
    project = load_mud(path)
    specimens = _specimens_with_data(project)
    if not specimens:
        return
    spec = specimens[0]
    fired = []
    spec.data_changed.connect(lambda: fired.append(1))

    _, before = spec.experimental_pattern
    before = before.copy()
    spec.smooth_data(pattern_ops.SMOOTH_BLACKMAN, 5)
    _, after = spec.experimental_pattern
    results.append(("3 Specimen.smooth_data changes the pattern",
                    not np.array_equal(before, after)))
    results.append(("3 Specimen.smooth_data emits data_changed once",
                    len(fired) == 1))

    fired.clear()
    spec.smooth_data(pattern_ops.SMOOTH_BLACKMAN, 0)  # no-op degree
    _, unchanged = spec.experimental_pattern
    results.append(("3 Specimen.smooth_data(degree=0) leaves data alone",
                    np.array_equal(after, unchanged)))

    fired.clear()
    spec.apply_shift(0.0)
    results.append(("3 Specimen.apply_shift(0) is inert (no signal)",
                    len(fired) == 0))

    # Statistics must be invalidated by an operation (they hang off
    # data_changed) - a stale Rp after an op would be a silent wrong answer.
    # Check the VALUE moves: merely re-reading .statistics would pass even
    # with a completely stale cache.
    if spec.has_calculated_data:
        rp_before = spec.statistics.Rp
        spec.add_noise(0.2)  # large enough to shift Rp well past rounding
        rp_after = spec.statistics.Rp
        results.append(
            ("3 statistics recomputed after an op (Rp %.3f -> %.3f)"
             % (rp_before, rp_after),
             rp_before > 0 and abs(rp_after - rp_before) > 1e-6)
        )


def check_trim_persistence(path, results):
    """3. A trim survives save/reload - including the RAW calculated pattern.

    Regression guard: the saver keeps the calculated line verbatim from
    raw_properties (its rows may carry per-phase columns the model drops), so
    trim must clip those rows itself. When it did not, a reloaded project
    paired a trimmed experimental pattern with a full-range calculated one,
    and the size-mismatch guard in SpecimenStatistics reported Rp = 0.00 - a
    *perfect fit*, not an error.
    """
    import json

    from mudlab.file_parsers.mud_project import save_mud

    project = load_mud(path)
    targets = [
        s for s in project.specimens
        if s.has_experimental_data and s.has_calculated_data
    ]
    if not targets:
        return
    spec = targets[0]
    raw_line = spec.raw_properties.get("calculated_pattern")
    n_cols_before = 0
    if isinstance(raw_line, dict):
        rows = json.loads(raw_line.get("properties", {}).get("data") or "[]")
        n_cols_before = len(rows[0]) if rows else 0

    x, _ = spec.experimental_pattern
    lo, hi = float(x[len(x) // 4]), float(x[3 * len(x) // 4])
    spec.trim(lo, hi)
    rp_trimmed = spec.statistics.Rp
    n_exp, n_calc = len(spec.experimental_pattern[0]), len(spec.calculated_pattern[0])
    results.append(("3 trim clips exp and calc to the same length",
                    n_exp == n_calc))

    tmp = os.path.join(tempfile.gettempdir(), "mudlab_trim_persist.mud")
    try:
        save_mud(project, tmp)
        reloaded = load_mud(tmp)
        names = [s.name for s in reloaded.specimens]
        spec2 = reloaded.specimens[names.index(spec.name)]
        n_exp2 = len(spec2.experimental_pattern[0])
        n_calc2 = len(spec2.calculated_pattern[0])
        results.append(("3 trimmed exp survives save/reload", n_exp2 == n_exp))
        results.append(("3 trimmed CALC survives save/reload (not full-range)",
                        n_calc2 == n_calc))
        results.append(("3 reloaded Rp %.3f == pre-save Rp %.3f (not a fake 0.0)"
                        % (spec2.statistics.Rp, rp_trimmed),
                        abs(spec2.statistics.Rp - rp_trimmed) < 1e-6
                        and spec2.statistics.Rp > 0))
        # The per-phase columns are the reason the raw line is kept verbatim.
        raw2 = spec2.raw_properties.get("calculated_pattern")
        if isinstance(raw2, dict) and n_cols_before:
            rows2 = json.loads(raw2.get("properties", {}).get("data") or "[]")
            results.append(
                ("3 per-phase calc columns preserved through trim (%d)"
                 % n_cols_before,
                 bool(rows2) and len(rows2[0]) == n_cols_before)
            )
    finally:
        for p in (tmp, tmp + "~"):
            if os.path.exists(p):
                os.remove(p)


def run(path, old):
    print("=" * 72)
    print("Pattern operations:", os.path.basename(path))
    print("=" * 72)
    results = []
    project = load_mud(path)
    check_old_smooth_differential(project, old, results)
    check_old_noise_differential(project, old, results)
    check_noop_guards(project, results)
    check_background(project, results)
    check_smooth_types(project, results)
    check_strip(project, results)
    check_trim(path, results)
    check_trim_persistence(path, results)
    check_ops_x_calc_engine(path, results)
    check_specimen_wiring(path, results)
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("%d/%d checks passed" % (passed, len(results)))
    return passed == len(results), len(results)


def run_analytic():
    print("=" * 72)
    print("Pattern operations: analytic references (no project needed)")
    print("=" * 72)
    results = []
    check_peak_properties_analytic(results)
    check_shift_analytic(results)
    check_detect_shift_synthetic(results)
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("%d/%d checks passed" % (passed, len(results)))
    return passed == len(results), len(results)


def main(argv):
    old = _load_old_math_tools()
    print("Old app math_tools: %s\n"
          % ("loaded (differential checks active)" if old else "NOT FOUND"))
    all_ok, total = run_analytic()
    print()

    paths = argv[1:] or _default_projects()
    existing = [p for p in paths if os.path.isfile(p)]
    if not existing:
        print("No sample projects found; analytic checks only (exit 2).")
        return 2
    for path in existing:
        ok, n = run(path, old)
        all_ok = all_ok and ok
        total += n
        print()
    print("=" * 72)
    print("Pattern-ops harness: %d checks across %d project(s): %s"
          % (total, len(existing), "OK" if all_ok else "REGRESSION"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
