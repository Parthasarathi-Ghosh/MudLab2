#!/usr/bin/env python
"""PROTOTYPE - non-clay decomposition, Stage 1 + Stage 2. NOT a regression
harness: it is the throwaway experiment behind docs/non-clay-analysis-notes.md,
kept so the numbers in that document can be reproduced and re-argued. It needs
local (gitignored) sample data and will not run on a clean clone.

Runs entirely in memory on the local Dh537A.mud + the Raw-pattern-phase
reference curves. Writes NOTHING back; the clay calc/optimize path is used
exactly as shipped (no code touched).

  Stage 1  residual = experimental - clay calc; clay : non-clay area split.
  Stage 2  non-negative fit of measured non-clay REFERENCE patterns to that
           residual (L2 / L2-on-clipped / L1-Rp variants).
  Stage 3  spike validation: add a KNOWN amount of quartz, re-run the clay
           fit, and see how much Stage 1 + Stage 2 recover (the bias number).
           Also the de-biased variant that excludes the quartz peak windows
           from the clay Rp fit.

    ./python/python.exe tools/prototype_nonclay.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
from scipy.optimize import fmin_l_bfgs_b, nnls

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.calculations.goniometer import get_machine_correction_range  # noqa: E402
from mudlab.calculations.specimen import calculate_phase_intensities  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.models.raw_pattern_phase import RawPatternPhase  # noqa: E402

MUD = os.path.join(_REPO, "tools", "sample_projects", "Dh537A.mud")
REF_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "Raw pattern phases")
QUARTZ = "quartz.txt"
# The other measured references sitting next to quartz.txt - used only for the
# multi-reference selectivity check (does Stage 2 pick quartz out of a set?).
OTHER_REFS = ("talc.txt", "Albite_LargeCS_Bis-1.txt", "Orthoclase_LargeCS.txt",
              "Corundum_LargeCS.txt")
# Opening widths (in points) tried for the residual baseline strip. The step is
# ~0.0131 deg, so 60 / 115 / 230 pts ~ 0.8 / 1.5 / 3.0 deg - the first is about
# one quartz peak wide, the last is wide enough to keep only very sharp features.
BASELINE_WIDTHS = (60, 115, 230)


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _read_text(path: str) -> list[str]:
    """Encoding-tolerant read. NOTE: 7 of the 9 reference curves in the user's
    'Raw pattern phases' folder are UTF-16 LE, which the shipped
    csv_io._read_lines (hardcoded utf-8-sig) cannot read - flagged separately."""
    with open(path, "rb") as stream:
        blob = stream.read()
    for bom, enc in ((b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16"),
                     (b"\xef\xbb\xbf", "utf-8-sig")):
        if blob.startswith(bom):
            return blob.decode(enc).splitlines()
    return blob.decode("utf-8", errors="replace").splitlines()


def load_reference(filename: str) -> RawPatternPhase:
    """A measured reference curve as a RawPatternPhase (what the real feature
    would use as its non-clay container)."""
    xs, ys = [], []
    for line in _read_text(os.path.join(REF_DIR, filename)):
        parts = [p for p in line.replace(";", ",").split(",") if p.strip()]
        if len(parts) < 2:
            continue
        try:
            xs.append(float(parts[0]))
            ys.append(float(parts[1]))
        except ValueError:
            continue
    phase = RawPatternPhase(name=os.path.splitext(filename)[0])
    phase.set_raw_pattern(np.array(xs), np.array(ys))
    return phase


def reference_basis(specimen, phases) -> np.ndarray:
    """Per-reference intensity rows on the specimen's own 2theta grid, through
    the SHIPPED calc path (so the basis is exactly what those phases would
    contribute if they sat in a mixture slot: wavelength distribution applied,
    no LP factor / machine correction for a raw phase)."""
    x, _ = specimen.experimental_pattern
    theta = np.radians(x * 0.5)
    gonio = specimen.goniometer
    correction = get_machine_correction_range(gonio, theta)
    return calculate_phase_intensities(
        theta, gonio.wavelength, gonio.wavelength_distribution,
        gonio.soller1, gonio.soller2, gonio.mcr_2theta, correction, phases,
    )


def area(y, x) -> float:
    return float(np.trapezoid(np.asarray(y, dtype=float), x))


def stage1(specimen) -> dict:
    """Split the specimen into clay / background / residual and area them up.

    clay  = sum of the fitted phase contributions (total - background)
    resid = experimental - total calculated   (the non-clay + misfit part)
    """
    x, exp = specimen.experimental_pattern
    total = specimen.calculated_pattern[1]
    pp = specimen.phase_patterns or []
    clay = (np.sum([curve for _, curve in pp], axis=0) if pp
            else np.zeros_like(total))
    background = total - clay
    residual = exp - total
    pos = np.clip(residual, 0.0, None)
    neg = np.clip(-residual, 0.0, None)
    a_clay, a_pos = area(clay, x), area(pos, x)
    return {
        "x": x, "exp": exp, "clay": clay, "bg": background,
        "residual": residual,
        "A_exp": area(exp, x), "A_clay": a_clay, "A_bg": area(background, x),
        "A_pos": a_pos, "A_neg": area(neg, x),
        # Stage-1-only (crude) non-clay share: positive residual vs clay.
        "nonclay_pct_raw": 100.0 * a_pos / (a_clay + a_pos) if a_clay else 0.0,
    }


def fit_nonnegative(basis: np.ndarray, target: np.ndarray, mode: str) -> np.ndarray:
    """Non-negative amplitudes for the reference rows against `target`.

    mode 'l2'      least squares on the raw residual
    mode 'l2clip'  least squares on the positively-clipped residual
    mode 'l1'      L1 (the Rp numerator) on the raw residual - matches the
                   metric the app's own optimizer minimises
    """
    A = basis.T
    if mode == "l2":
        return nnls(A, target)[0]
    if mode == "l2clip":
        return nnls(A, np.clip(target, 0.0, None))[0]
    if mode == "l1":
        start = nnls(A, np.clip(target, 0.0, None))[0]

        def objective(a):
            return float(np.sum(np.abs(target - A @ a)))

        best, _f, _d = fmin_l_bfgs_b(
            objective, start, approx_grad=True,
            bounds=[(0.0, None)] * A.shape[1], epsilon=1e-6,
            maxfun=2000, maxiter=500,
        )
        return np.asarray(best, dtype=float)
    raise ValueError(mode)


def baseline_open(y, width_pts: int):
    """Morphological opening (rolling min then rolling max) + smoothing = a
    baseline that follows the BROAD structure and passes under the SHARP peaks.
    Subtracting it is the cheap stand-in for ORPL's growing-bubble baseline
    (methodology #1B), used here to strip the clay MISFIT drift out of the
    Stage-1 residual before the non-clay references are fitted."""
    from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d

    w = max(3, int(width_pts))
    base = minimum_filter1d(np.asarray(y, dtype=float), w, mode="nearest")
    base = maximum_filter1d(base, w, mode="nearest")
    return uniform_filter1d(base, w, mode="nearest")


def signed_projection(basis_row, target) -> float:
    """The UNCONSTRAINED least-squares amplitude - the same number NNLS clips
    at zero. Its value on an un-spiked pattern is the estimator's offset."""
    denom = float(np.dot(basis_row, basis_row))
    return float(np.dot(basis_row, target) / denom) if denom else 0.0


def stage2(specimen, basis, names, mode="l2", baseline_width=0) -> dict:
    """Fit the non-clay references to the Stage-1 residual and turn the fitted
    amplitudes into areas / percentages of the (clay + non-clay) signal.

    ``baseline_width`` > 0 opens (see baseline_open) BOTH the residual and the
    reference rows first, so the amplitude compares peaks against peaks with the
    broad misfit drift removed. Areas are always taken on the UNcorrected
    reference curve - the amplitude is a scale factor on the real reference."""
    s1 = stage1(specimen)
    x, residual = s1["x"], s1["residual"]
    fit_target, fit_basis = residual, basis
    if baseline_width:
        fit_target = residual - baseline_open(residual, baseline_width)
        fit_basis = np.array([row - baseline_open(row, baseline_width)
                              for row in basis])
    amps = fit_nonnegative(fit_basis, fit_target, mode)
    curves = (amps * basis.T).T
    areas = np.array([area(c, x) for c in curves], dtype=float)
    a_nc = float(areas.sum())
    a_clay = s1["A_clay"]
    # How much of the (possibly baseline-corrected) target the model explains (L1).
    fit_model = (amps * fit_basis.T).T.sum(axis=0)
    denom = float(np.sum(np.abs(fit_target)))
    explained = (100.0 * (1.0 - np.sum(np.abs(fit_target - fit_model)) / denom)
                 if denom else 0.0)
    return {
        "amps": amps, "areas": areas, "names": names,
        "A_nonclay": a_nc, "A_clay": a_clay,
        "nonclay_pct": 100.0 * a_nc / (a_clay + a_nc) if (a_clay + a_nc) else 0.0,
        "explained_pct": explained, "stage1": s1,
        "signed_amps": [signed_projection(row, fit_target) for row in fit_basis],
    }


def peak_windows(phase, lo, hi, rel_threshold=0.03, margin=0.25):
    """2theta windows where a reference pattern is significantly above zero -
    the regions to EXCLUDE from the clay Rp fit so the clay model stops
    absorbing the non-clay peaks (uses the existing exclusion-range feature)."""
    x, y = phase.raw_pattern_x, phase.raw_pattern_y
    inside = (x >= lo) & (x <= hi)
    x, y = x[inside], y[inside]
    if y.size == 0:
        return []
    strong = y > rel_threshold * y.max()
    windows, start = [], None
    for i, flag in enumerate(strong):
        if flag and start is None:
            start = x[i]
        elif not flag and start is not None:
            windows.append((start - margin, x[i - 1] + margin))
            start = None
    if start is not None:
        windows.append((start - margin, x[-1] + margin))
    # merge overlaps
    merged = []
    for w in sorted(windows):
        if merged and w[0] <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], w[1]))
        else:
            merged.append(list(w) if False else (w[0], w[1]))
            merged[-1] = (w[0], w[1])
    return merged


def stage2_nuisance(specimen, basis, names, baseline_width=0, signed=False) -> dict:
    """Stage 2 with the clay-fit NUISANCE terms in the design matrix.

    Rationale (what the spike test exposed): the clay fit does not absorb a
    non-clay spike through its phase fractions - it cannot grow a sharp peak -
    but it DOES absorb part of it through the two global knobs the optimizer is
    free to move, the specimen ``scale`` (multiplies the clay shape) and the
    ``bgshift`` (multiplies the machine-correction shape). So the Stage-1
    residual is not just (non-clay + noise); it is

        residual = da * clay_shape + db * correction_shape + sum_i a_i * ref_i

    Putting clay_shape and correction_shape in as FREE (sign-unconstrained)
    nuisance columns, with the reference amplitudes still non-negative, is the
    exact inverse of that re-adjustment - it should recover a_i unbiased
    without touching a single line of the clay code."""
    from scipy.optimize import lsq_linear

    s1 = stage1(specimen)
    x, residual = s1["x"], s1["residual"]
    theta = np.radians(x * 0.5)
    correction = get_machine_correction_range(specimen.goniometer, theta)
    clay = s1["clay"]

    target, refs = residual, basis
    if baseline_width:
        target = residual - baseline_open(residual, baseline_width)
        refs = np.array([row - baseline_open(row, baseline_width) for row in basis])
        clay = clay - baseline_open(clay, baseline_width)
        correction = correction - baseline_open(correction, baseline_width)

    n_ref = refs.shape[0]
    A = np.column_stack([refs.T, clay, correction])
    lower = np.array([0.0] * n_ref + [-np.inf, -np.inf])
    upper = np.full(n_ref + 2, np.inf)
    if signed:  # drop the non-negativity, to read the estimator's noise floor
        lower = np.full(n_ref + 2, -np.inf)
    solution = lsq_linear(A, target, bounds=(lower, upper), method="bvls")
    amps = np.asarray(solution.x[:n_ref], dtype=float)

    curves = (amps * basis.T).T
    areas = np.array([area(c, x) for c in curves], dtype=float)
    a_nc, a_clay = float(areas.sum()), s1["A_clay"]
    denom = float(np.sum(np.abs(target)))
    explained = (100.0 * (1.0 - np.sum(np.abs(target - A @ solution.x)) / denom)
                 if denom else 0.0)
    return {
        "amps": amps, "areas": areas, "names": names,
        "A_nonclay": a_nc, "A_clay": a_clay,
        "nonclay_pct": 100.0 * a_nc / (a_clay + a_nc) if (a_clay + a_nc) else 0.0,
        "explained_pct": explained, "stage1": s1,
        "nuisance": tuple(float(v) for v in solution.x[n_ref:]),
        # Signed % per reference (meaningful when signed=True): a NEGATIVE value
        # means the clay model over-predicts under that reference's peaks, so
        # this much of that mineral would be cancelled before any is detected -
        # i.e. the detection floor for that mineral in that specimen.
        "signed_pct": [100.0 * a / (a_clay + abs(a)) if a_clay else 0.0
                       for a in areas],
    }


# ----------------------------------------------------------------------
# Detection threshold
# ----------------------------------------------------------------------
# Offsets (degrees 2theta) at which a reference is deliberately mis-registered
# to build a null distribution. |delta| >= 0.6 so a shifted copy never overlaps
# its own true peaks.
NULL_OFFSETS = tuple(np.concatenate([
    np.arange(-4.0, -0.55, 0.4), np.arange(0.6, 4.05, 0.4)
]))
NULL_PERCENTILE = 95.0
# Absolute honesty floor: below this share of the modelled signal nothing is
# reported regardless of the null test. Integrated-intensity XRD without RIRs
# or an internal standard cannot defend a sub-0.5% accessory phase, and on a
# near-perfect fit (the synthetic goldens) the null band collapses far below
# that, letting bare interpolation residue read as a detection.
MIN_PCT = 0.5
# You cannot measure a 1% accessory against a clay model that is 50% wrong.
QUALITY_MAX_RP = 40.0


def _shifted(phase, delta):
    copy = RawPatternPhase(name="%s%+.1f" % (phase.name, delta))
    copy.set_raw_pattern(phase.raw_pattern_x + delta, phase.raw_pattern_y)
    return copy


def null_threshold_pct(specimen, phase) -> float:
    """Detection threshold for `phase` in `specimen`, as a % of the modelled
    signal: the NULL_PERCENTILE of the spurious amplitude a MIS-REGISTERED copy
    of that reference picks up.

    Why not a least-squares standard error: the Stage-1 residual is the clay
    misfit, which is smooth and strongly autocorrelated, so the textbook sigma
    (which assumes white noise over ~2300 points) is wildly optimistic. Shifting
    the reference to where its peaks do NOT belong and fitting it identically
    gives a non-parametric band that reflects what this particular misfit can
    manufacture for a curve with these peak shapes.

    NOTE this is NOT the same thing as the signed/unclipped fit: that measures
    the estimator's BIAS (how far the misfit displaces the answer) and equals
    the fitted amplitude itself whenever the amplitude is positive, so it can
    never serve as a threshold."""
    s1 = stage1(specimen)
    values = []
    for delta in NULL_OFFSETS:
        basis = reference_basis(specimen, [_shifted(phase, delta)])
        if not np.any(basis[0]):
            continue  # shifted entirely out of the measured range
        fit = stage2_nuisance(specimen, basis, ["null"], signed=True)
        amp_area = abs(float(fit["areas"][0]))
        values.append(100.0 * amp_area / (s1["A_clay"] + amp_area))
    return float(np.percentile(values, NULL_PERCENTILE)) if values else 0.0


def is_detected(pct: float, threshold: float) -> bool:
    """The calibrated rule: clear the null band AND the absolute honesty floor.
    (The caller applies the QUALITY_MAX_RP gate on the specimen first.)"""
    return pct > max(threshold, MIN_PCT)


# ----------------------------------------------------------------------
# Reference intensity-space check (see Finding 11 in the notes)
# ----------------------------------------------------------------------
# Standard alpha-quartz powder pattern (ICDD 46-1045, Cu Ka): 2theta -> relative
# intensity. These are OBSERVED intensities - the Lorentz-polarisation factor is
# already in them.
_QUARTZ_STANDARD = (
    (20.860, 16), (26.640, 100), (36.544, 9), (39.465, 8), (40.300, 4),
    (42.450, 6), (45.793, 4), (50.139, 13), (59.960, 9), (67.744, 7),
    (68.144, 8),
)


def check_reference_space(phase, standard=_QUARTZ_STANDARD, window=0.35):
    """Is `phase`'s stored curve in OBSERVED-intensity space (LP included), as
    the Stage-2 fit requires?

    The residual keeps its LP weighting - subtraction removes the clay TERM, not
    a common factor - so a reference lacking LP would be fitted against an
    LP-weighted target and misweighted badly (LP spans 35x over 4.6-35 deg).

    Compares peak heights against a standard powder pattern whose intensities
    already include LP. Returns (rows, trend) where rows are
    (2theta, standard, normalised, ratio) and `trend` is the slope of ratio vs
    2theta: ~0 means the angular factors agree, a strong slope means they do not.
    The spike test CANNOT catch this - it generates and fits through the same
    path - so this is the only check standing between a structure-factor
    reference and silently wrong numbers."""
    x = np.asarray(phase.raw_pattern_x, dtype=float)
    y = np.asarray(phase.raw_pattern_y, dtype=float)
    rows = []
    for pos, std in standard:
        sel = (x >= pos - window) & (x <= pos + window)
        rows.append([pos, std, float(y[sel].max()) if np.any(sel) else 0.0])
    peak = max(r[2] for r in rows) or 1.0
    out = [(p, s, 100.0 * h / peak, (100.0 * h / peak) / s if s else float("nan"))
           for p, s, h in rows]
    good = [(p, r) for p, _s, _n, r in out if np.isfinite(r)]
    trend = float(np.polyfit([p for p, _ in good], [r for _, r in good], 1)[0]) \
        if len(good) > 1 else 0.0
    return out, trend


def banner(text):
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


# ----------------------------------------------------------------------
# Stage 1 + 2 on the real, as-fitted project
# ----------------------------------------------------------------------
def run_stages_1_2(quartz, others):
    banner("STAGE 1 + 2  |  Dh537A as stored (clay fit untouched)")
    proj = load_mud(MUD)
    mix = proj.mixtures[0]
    mix.calculate()
    print("stored mean Rp: %.4f" % mix.current_residual())
    print("fractions %s  scales %s  bg %s"
          % (np.round(mix.fractions, 4), np.round(mix.scales, 4),
             np.round(mix.bgshifts, 3)))

    for specimen in mix.specimens:
        if specimen is None:
            continue
        s1 = stage1(specimen)
        print("\n--- %s ---" % specimen.name)
        print("  areas: exp %.1f = clay %.1f + background %.1f + residual %.1f"
              % (s1["A_exp"], s1["A_clay"], s1["A_bg"],
                 s1["A_exp"] - s1["A_clay"] - s1["A_bg"]))
        print("  residual: +%.1f / -%.1f  (|res| %.1f, %.1f%% of the clay area)"
              % (s1["A_pos"], s1["A_neg"], s1["A_pos"] + s1["A_neg"],
                 100.0 * (s1["A_pos"] + s1["A_neg"]) / s1["A_clay"]))
        print("  STAGE 1 crude non-clay share (positive residual): %.2f%%"
              % s1["nonclay_pct_raw"])

        basis_q = reference_basis(specimen, [quartz])
        for mode in ("l2", "l2clip", "l1"):
            r = stage2(specimen, basis_q, ["quartz"], mode)
            print("  STAGE 2 quartz-only [%-6s] amp %.5f (signed %+.5f) -> "
                  "non-clay %.2f%% (explained %.1f%%)"
                  % (mode, r["amps"][0], r["signed_amps"][0],
                     r["nonclay_pct"], r["explained_pct"]))
        for w in BASELINE_WIDTHS:
            r = stage2(specimen, basis_q, ["quartz"], "l2", baseline_width=w)
            print("  STAGE 2 quartz-only [l2 + open %3d pts (%.2f deg)] amp %.5f "
                  "(signed %+.5f) -> non-clay %.2f%% (explained %.1f%%)"
                  % (w, w * float(np.diff(s1["x"]).mean()), r["amps"][0],
                     r["signed_amps"][0], r["nonclay_pct"], r["explained_pct"]))

        r = stage2_nuisance(specimen, basis_q, ["quartz"])
        print("  STAGE 2 quartz-only [nuisance] amp %.5f -> non-clay %.2f%% "
              "(explained %.1f%%, d_scale %+.4f d_bg %+.4f)"
              % (r["amps"][0], r["nonclay_pct"], r["explained_pct"],
                 r["nuisance"][0], r["nuisance"][1]))
        rs = stage2_nuisance(specimen, basis_q, ["quartz"], signed=True)
        print("  DETECTION FLOOR [nuisance, unclipped] signed quartz %+.2f%% "
              "<- how far the clay misfit alone displaces the estimate"
              % rs["signed_pct"][0])

        # Selectivity: does the fit pick quartz out of a set of references?
        refs = [quartz] + others
        names = [p.name for p in refs]
        basis_all = reference_basis(specimen, refs)
        r = stage2_nuisance(specimen, basis_all, names)
        print("  STAGE 2 multi-reference [nuisance] -> total non-clay %.2f%% "
              "(explained %.1f%%)" % (r["nonclay_pct"], r["explained_pct"]))
        for name, amp, a in zip(names, r["amps"], r["areas"]):
            share = (100.0 * a / (r["A_clay"] + r["A_nonclay"])
                     if r["A_nonclay"] else 0.0)
            print("      %-26s amp %.5f  area %8.1f  %5.2f%%" % (name, amp, a, share))
        for w in (0, BASELINE_WIDTHS[1]):
            r = stage2(specimen, basis_all, names, "l2", baseline_width=w)
            print("  STAGE 2 multi-reference [l2%s] -> total non-clay %.2f%% "
                  "(explained %.1f%%)"
                  % (" + open" if w else "", r["nonclay_pct"], r["explained_pct"]))
            for name, amp, a in zip(names, r["amps"], r["areas"]):
                share = (100.0 * a / (r["A_clay"] + r["A_nonclay"])
                         if r["A_nonclay"] else 0.0)
                print("      %-26s amp %.5f  area %8.1f  %5.2f%%"
                      % (name, amp, a, share))


# ----------------------------------------------------------------------
# Stage 3: spike validation (the bias number)
# ----------------------------------------------------------------------
def run_spike_test(quartz, targets=(0.0, 0.01, 0.02, 0.05, 0.10, 0.20),
                   exclude=False):
    banner("STAGE 3  |  spike recovery%s"
           % ("  (quartz peak windows EXCLUDED from the clay fit)" if exclude
              else "  (clay fit sees the whole pattern)"))
    print("%-8s %-14s %8s %8s %8s %8s %8s %8s %8s"
          % ("spike", "specimen", "true%", "S1 raw%", "S2 l2%", "S2 l1%",
             "S2 open%", "S2 nuis%", "Rp"))
    rows = []
    for target in targets:
        proj = load_mud(MUD)
        mix = proj.mixtures[0]
        mix.calculate()

        # Build the spike from the ORIGINAL fit: for each specimen add
        # c * I_quartz with c chosen so the added area is `target` x the
        # fitted clay area. That makes the truth exactly known.
        spikes, truths = {}, {}
        for specimen in mix.specimens:
            if specimen is None:
                continue
            s1 = stage1(specimen)
            x, exp = specimen.experimental_pattern
            i_q = reference_basis(specimen, [quartz])[0]
            a_q = area(i_q, x)
            c = target * s1["A_clay"] / a_q
            spikes[id(specimen)] = c * i_q
            truths[id(specimen)] = 100.0 * (c * a_q) / (s1["A_clay"] + c * a_q)
            specimen.set_experimental_pattern(x, exp + c * i_q)
            if exclude:
                specimen.set_exclusion_ranges(
                    peak_windows(quartz, float(x.min()), float(x.max()))
                )

        t0 = time.time()
        rp = mix.optimize()          # the SHIPPED clay fit, unchanged
        elapsed = time.time() - t0

        for specimen in mix.specimens:
            if specimen is None:
                continue
            basis_q = reference_basis(specimen, [quartz])
            s1 = stage1(specimen)
            r_l2 = stage2(specimen, basis_q, ["quartz"], "l2")
            r_l1 = stage2(specimen, basis_q, ["quartz"], "l1")
            r_op = stage2(specimen, basis_q, ["quartz"], "l2",
                          baseline_width=BASELINE_WIDTHS[1])
            r_nu = stage2_nuisance(specimen, basis_q, ["quartz"])
            print("%-8s %-14s %8.2f %8.2f %8.2f %8.2f %8.2f %8.2f %8.3f"
                  % ("%.0f%%" % (target * 100), specimen.name,
                     truths[id(specimen)], s1["nonclay_pct_raw"],
                     r_l2["nonclay_pct"], r_l1["nonclay_pct"],
                     r_op["nonclay_pct"], r_nu["nonclay_pct"], rp))
            rows.append((target, specimen.name, truths[id(specimen)],
                         s1["nonclay_pct_raw"], r_l2["nonclay_pct"],
                         r_l1["nonclay_pct"], r_op["nonclay_pct"],
                         r_nu["nonclay_pct"]))
        print("         (clay re-fit in %.1f s, mean Rp %.3f) fractions %s "
              "scales %s bg %s"
              % (elapsed, rp, np.round(mix.fractions, 4),
                 np.round(mix.scales, 4), np.round(mix.bgshifts, 3)))
    return rows


def summarise(rows, label):
    banner("RECOVERY SUMMARY  |  %s" % label)
    print("%-8s %-14s %8s %8s %8s %8s %8s %8s %8s"
          % ("spike", "specimen", "true%", "S2 l2%", "err l2", "S2 open%",
             "err open", "S2 nuis%", "err nuis"))
    for target, name, truth, _raw, l2, _l1, op, nu in rows:
        print("%-8s %-14s %8.2f %8.2f %8.2f %8.2f %8.2f %8.2f %8.2f"
              % ("%.0f%%" % (target * 100), name, truth, l2, l2 - truth,
                 op, op - truth, nu, nu - truth))

    # Slope check: the estimator can carry a per-specimen OFFSET (the clay
    # misfit projected onto the reference) yet still track ADDED quartz
    # correctly. Regress recovered vs true per specimen to separate the two.
    # Rows where the non-negativity clipped the answer to 0 are excluded: they
    # sit on the bound, not on the response line, and would fake a low slope.
    print("\nper-specimen linear fit of recovered vs true, CLIPPED (zero) rows "
          "excluded (slope 1 / intercept 0 = unbiased):")
    print("%-14s %6s %10s %10s %10s %10s"
          % ("specimen", "n", "slope l2", "icept l2", "slope nuis", "icept nuis"))
    for name in sorted({r[1] for r in rows}):
        sub = [r for r in rows if r[1] == name and r[2] > 0
               and r[4] > 0 and r[7] > 0]
        if len(sub) < 2:
            print("%-14s %6d   (too few unclipped points)" % (name, len(sub)))
            continue
        truth = np.array([r[2] for r in sub])
        s_l2, i_l2 = np.polyfit(truth, np.array([r[4] for r in sub]), 1)
        s_nu, i_nu = np.polyfit(truth, np.array([r[7] for r in sub]), 1)
        print("%-14s %6d %10.3f %10.3f %10.3f %10.3f"
              % (name, len(sub), s_l2, i_l2, s_nu, i_nu))

    print("\nsame fit over ALL rows (clipped rows included - for comparison):")
    print("%-14s %10s %10s %10s %10s %10s %10s"
          % ("specimen", "slope l2", "icept l2", "slope open", "icept open",
             "slope nuis", "icept nuis"))
    for name in sorted({r[1] for r in rows}):
        sub = [r for r in rows if r[1] == name]
        truth = np.array([r[2] for r in sub])
        s_l2, i_l2 = np.polyfit(truth, np.array([r[4] for r in sub]), 1)
        s_op, i_op = np.polyfit(truth, np.array([r[6] for r in sub]), 1)
        s_nu, i_nu = np.polyfit(truth, np.array([r[7] for r in sub]), 1)
        print("%-14s %10.3f %10.3f %10.3f %10.3f %10.3f %10.3f"
              % (name, s_l2, i_l2, s_op, i_op, s_nu, i_nu))


def main() -> int:
    quartz = load_reference(QUARTZ)
    others = [load_reference(n) for n in OTHER_REFS]
    print("references: %s" % ", ".join([quartz.name] + [p.name for p in others]))

    banner("REFERENCE INTENSITY SPACE  |  quartz.txt vs the standard powder "
           "pattern (Finding 11)")
    rows, trend = check_reference_space(quartz)
    print("%8s %10s %12s %8s" % ("2theta", "standard", "normalised", "ratio"))
    for pos, std, norm, ratio in rows:
        print("%8.3f %10d %12.1f %8.2f" % (pos, std, norm, ratio))
    print("\nratio-vs-2theta slope %+.5f per deg  ->  %s"
          % (trend, "observed-space, LP already included (OK)"
             if abs(trend) < 0.01 else
             "SPACE MISMATCH - reference is not observed-space"))

    run_stages_1_2(quartz, others)
    plain = run_spike_test(quartz, exclude=False)
    summarise(plain, "no exclusion (clay absorbs the spike)")
    excl = run_spike_test(quartz, exclude=True)
    summarise(excl, "quartz windows excluded from the clay fit")

    windows = peak_windows(quartz, 4.5, 35.0)
    print("\nexclusion windows used: %s"
          % ", ".join("%.2f-%.2f" % w for w in windows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
