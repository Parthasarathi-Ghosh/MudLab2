#!/usr/bin/env python
"""PROTOTYPE - specificity survey for the non-clay decomposition estimator.
NOT a regression harness; see docs/non-clay-analysis-notes.md. Needs local
(gitignored) sample data and will not run on a clean clone.

Runs the recommended Stage 1 + Stage 2 (nuisance-column) estimator with the
calibrated detection rule over every sample-project fixture. These samples are
expected to hold LITTLE non-clay, so a trustworthy estimator must return
near-zero and must not invent minerals - especially on the synthetic
single-phase Illite-Smectite goldens, which contain exactly zero non-clay by
construction and are fitted to R2 = 1.000.

    ./python/python.exe tools/prototype_nonclay_survey.py
    ./python/python.exe tools/prototype_nonclay_survey.py --reoptimize
"""
from __future__ import annotations

import os
import sys

import numpy as np

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))
sys.path.insert(0, os.path.join(_REPO, "tools"))

from prototype_nonclay import (  # noqa: E402
    QUALITY_MAX_RP, area, is_detected, load_reference, null_threshold_pct,
    reference_basis, stage1, stage2_nuisance,
)
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

FIXTURES = os.path.join(_REPO, "tools", "sample_projects")
# One variant per mineral - the Large/Small-CS pairs are near-duplicates and
# would be severely collinear in the same design matrix.
REFS = ("quartz.txt", "talc.txt", "Albite_LargeCS_Bis-1.txt",
        "Clinoptilolite_LargeCS.txt", "Corundum_LargeCS.txt",
        "Orthoclase_LargeCS.txt")


def split_areas(specimen) -> dict:
    """Stage 1, but separating STRUCTURAL (clay) phase contributions from any
    RawPatternPhase already sitting in the mixture - a raw phase is a non-clay
    that the clay fit already accounts for, so it must not be counted as clay.

    The nuisance column stays the FULL phase sum: the specimen `scale` the
    optimizer moves multiplies every phase, raw ones included."""
    s1 = stage1(specimen)
    x = s1["x"]
    clay = np.zeros_like(s1["clay"])
    raw = np.zeros_like(s1["clay"])
    raw_names = []
    for phase, curve in (specimen.phase_patterns or []):
        if getattr(phase, "type", "Phase") == "RawPatternPhase":
            raw = raw + curve
            raw_names.append(phase.name)
        else:
            clay = clay + curve
    s1["A_structural"] = area(clay, x)
    s1["A_raw_in_mix"] = area(raw, x)
    s1["raw_names"] = raw_names
    return s1


def survey_project(path, refs, ref_names, reoptimize=False) -> list:
    name = os.path.basename(path)
    try:
        proj = load_mud(path)
    except Exception as exc:
        print("\n%s -- LOAD FAILED: %s" % (name, exc))
        return []
    print("\n" + "=" * 100)
    print("%s   (%d specimen(s), %d phase(s), %d mixture(s))"
          % (name, len(proj.specimens), len(proj.phases), len(proj.mixtures)))
    print("=" * 100)

    detections = []
    for mi, mix in enumerate(proj.mixtures):
        mix.calculate()
        residual = mix.current_residual()
        label = "stored"
        if reoptimize:
            residual = mix.optimize()
            label = "re-optimised"
        slots = []
        for row in mix.phase_matrix:
            for p in row:
                if p is not None and p.name not in slots:
                    slots.append("%s%s" % (p.name,
                                           "*" if p.type == "RawPatternPhase" else ""))
        print("\nmixture[%d] %r  mean Rp %.2f (%s)" % (mi, mix.name, residual, label))
        print("  phases: %s   (* = RawPatternPhase already in the mixture)"
              % ", ".join(slots))

        for specimen in mix.specimens:
            if specimen is None:
                continue
            x, _ = specimen.experimental_pattern
            if x.size < 2:
                continue
            s1 = split_areas(specimen)
            st = specimen.statistics.as_dict()
            rp = st.get("Rp", float("nan"))
            print("\n  --- %s   2th %.1f-%.1f  Rp %.1f  R2 %.3f ---"
                  % (specimen.name, x.min(), x.max(), rp,
                     st.get("R2", float("nan"))))
            print("      areas: clay %.0f | raw-in-mix %.0f | background %.0f "
                  "| residual +%.0f/-%.0f"
                  % (s1["A_structural"], s1["A_raw_in_mix"], s1["A_bg"],
                     s1["A_pos"], s1["A_neg"]))

            if not np.isfinite(rp) or rp > QUALITY_MAX_RP:
                print("      clay fit too poor to quantify non-clays "
                      "(Rp %.1f > %.0f) - NOT REPORTED" % (rp, QUALITY_MAX_RP))
                continue

            basis = reference_basis(specimen, refs)
            fit = stage2_nuisance(specimen, basis, ref_names)
            denom = s1["A_structural"] + s1["A_raw_in_mix"] + float(fit["areas"].sum())

            lines, detected_area = [], 0.0
            for i, (ref_name, ref_phase) in enumerate(zip(ref_names, refs)):
                pct = 100.0 * fit["areas"][i] / denom if denom else 0.0
                threshold = null_threshold_pct(specimen, ref_phase)
                if is_detected(pct, threshold):
                    detected_area += float(fit["areas"][i])
                    detections.append((name, specimen.name, ref_name, pct))
                    lines.append("      %-24s %6.2f%%  (null95 %5.2f%%)  DETECTED"
                                 % (ref_name, pct, threshold))
                elif pct > 0.005:
                    lines.append("      %-24s %6.2f%%  (null95 %5.2f%%)  not reported"
                                 % (ref_name, pct, threshold))
            print("\n".join(lines) if lines else "      (no reference above zero)")

            total_nc = detected_area + s1["A_raw_in_mix"]
            print("      => CLAY %.1f%%  :  NON-CLAY %.1f%%   (reported "
                  "detections only; background excluded)"
                  % (100.0 * (denom - total_nc) / denom if denom else 0.0,
                     100.0 * total_nc / denom if denom else 0.0))
    return detections


def main() -> int:
    refs = [load_reference(n) for n in REFS]
    ref_names = [p.name for p in refs]
    print("reference minerals: %s" % ", ".join(ref_names))
    print("NOTE: percentages are integrated-intensity shares, NOT weight %% "
          "(no RIRs / internal standard) - semi-quantitative only.")

    files = sorted(f for f in os.listdir(FIXTURES) if f.endswith(".mud"))
    reopt = "--reoptimize" in sys.argv
    found = []
    for f in files:
        found.extend(survey_project(os.path.join(FIXTURES, f), refs,
                                    ref_names, reopt))

    print("\n" + "=" * 100)
    if found:
        print("SPECIFICITY: %d detection(s) on samples expected to be "
              "non-clay-poor - review each:" % len(found))
        for fixture, spec, mineral, pct in found:
            print("  %-28s %-16s %-24s %.2f%%" % (fixture, spec, mineral, pct))
    else:
        print("SPECIFICITY: no false positives across %d fixture(s)." % len(files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
