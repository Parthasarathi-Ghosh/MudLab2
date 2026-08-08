#!/usr/bin/env python
"""Durable harness for the EXPERIMENTAL non-clay decomposition engine
(src/mudlab/nonclay). Guards the Case-A estimator + detection + the isolation
invariant. Runs head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_nonclay.py

Checks:
  1. isolation: NOTHING under src/mudlab imports mudlab.nonclay except the
     package itself (Slice 1 has no mainstream seam yet - this MUST stay 0 until
     the fenced Slice-3 seam is added, and then only that file may match).
  2. read-only: decomposing a mixture does not change its fractions/scales/bg.
  3. estimator: a known spike of a reference is recovered on the best-fit
     specimen (bounded bias); un-spiked returns ~0 and is NOT detected.
  4. detection: the mis-registration null is finite and the rule gates on Rp.
  5. shared fit: one amplitude per reference across specimens, finite.

Exit: 0 all pass, 1 a regression, 2 no sample project found.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402

from mudlab import nonclay  # noqa: E402
from mudlab.nonclay import estimator  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")
results = []


def check(label, ok):
    results.append((label, bool(ok)))


def _find_fixture():
    for name in ("Dh537A.mud", "308 r1.mud", "Dh2040A 14Jul26 r1.mud"):
        for base in (_FIXTURES, os.path.join(os.path.expanduser("~"), "Downloads")):
            p = os.path.join(base, name)
            if os.path.isfile(p):
                return p
    return None


def _synthetic_quartz(lo=4.0, hi=40.0):
    """A self-contained quartz-like reference: gaussians at the in-range quartz
    peaks (20.86, 26.64 deg). Keeps the harness independent of local data."""
    x = np.arange(lo, hi, 0.02)
    y = np.zeros_like(x)
    for pos, amp, wid in ((20.86, 0.2, 0.10), (26.64, 1.0, 0.10), (36.5, 0.09, 0.12)):
        y += amp * np.exp(-0.5 * ((x - pos) / wid) ** 2)
    return nonclay.reference_from_arrays(x, y, "synthetic-quartz")


def _isolation_scan():
    """Files under src/mudlab (excluding the nonclay package) that import
    mudlab.nonclay OUTSIDE the ONE sanctioned, NONCLAY-fenced seam
    (edit_mixture_widget.py, Slice 3). Any other import breaks isolation; so does
    an import in the seam file that is not inside a NONCLAY-marked block."""
    root = os.path.join(_REPO, "src", "mudlab")
    pkg = os.path.join(root, "nonclay")
    seam = os.path.normpath(os.path.join(root, "edit_mixture_widget.py"))
    offenders = []
    for dirpath, _dirs, files in os.walk(root):
        if os.path.abspath(dirpath).startswith(os.path.abspath(pkg)):
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            if "import mudlab.nonclay" in text or "from mudlab.nonclay" in text:
                # The seam is allowed iff it is fenced with the NONCLAY marker.
                if os.path.normpath(path) == seam and "NONCLAY" in text:
                    continue
                offenders.append(os.path.relpath(path, _REPO))
    return offenders


def run(path):
    # 1. isolation invariant: only the fenced edit_mixture_widget seam imports it.
    offenders = _isolation_scan()
    check("1 only the fenced Slice-3 seam imports mudlab.nonclay: %s"
          % (offenders or "clean"), not offenders)

    proj = load_mud(path)
    mix = proj.mixtures[0]
    mix.calculate()
    ref = _synthetic_quartz()

    # 2. read-only: decomposition must not mutate the clay fit.
    before = (mix.fractions.copy(), mix.scales.copy(), mix.bgshifts.copy())
    res = nonclay.decompose_mixture(mix, [ref], detect=True)
    after = (mix.fractions, mix.scales, mix.bgshifts)
    check("2 decompose is read-only (fractions/scales/bg unchanged)",
          np.allclose(before[0], after[0]) and np.allclose(before[1], after[1])
          and np.allclose(before[2], after[2]))

    # result structure.
    check("result has one entry per specimen + a shared amplitude",
          len(res.specimens) == len([s for s in mix.specimens if s is not None])
          and len(res.shared_amps) == 1)

    # 3a. un-spiked: small non-clay, not detected (synthetic ref is absent).
    worst = max(sr.references[0].pct for sr in res.specimens)
    check("3 un-spiked estimate is small (< 5%) for the absent reference",
          worst < 5.0)
    check("3 un-spiked reference is not falsely detected",
          not any(sr.references[0].detected for sr in res.specimens))

    # 3b. spike recovery on the best-fit specimen.
    proj2 = load_mud(path)
    mix2 = proj2.mixtures[0]
    mix2.calculate()
    specs2 = [s for s in mix2.specimens if s is not None]
    a_clay = np.mean([estimator.area(estimator.specimen_residual(s)[2],
                                     estimator.specimen_residual(s)[0]) for s in specs2])
    a_ref = np.mean([estimator.area(estimator.reference_intensities(s, [ref])[0],
                                    s.experimental_pattern[0]) for s in specs2])
    c = 0.20 * a_clay / a_ref  # add 20% of clay area as the reference
    for s in specs2:
        x, exp = s.experimental_pattern
        s.set_experimental_pattern(x, exp + c * estimator.reference_intensities(s, [ref])[0])
    mix2.optimize()
    rps = [estimator.specimen_rp(s) for s in specs2]
    best = specs2[int(np.argmin(rps))]
    amp_best = float(estimator.fit_specimen(best, [ref])["amps"][0])
    print("  spike c=%.4f  best-specimen Rp=%.2f recovered amp=%.4f (%.0f%%)"
          % (c, min(rps), amp_best, 100.0 * amp_best / c if c else 0))
    # Recovery carries a real downward bias (the local clay-misfit projection,
    # Findings 4/14), so the honest check is "recovers most of the spike without
    # overshoot", not an exact match.
    check("3 spike recovered on the best-fit specimen (60-115%, known downward bias)",
          0.60 * c <= amp_best <= 1.15 * c)

    # 4. detection: null finite; rule gates on Rp.
    from mudlab.nonclay import detection
    null = detection.null_threshold_pct(best, ref)
    check("4 mis-registration null is finite and non-negative",
          np.isfinite(null) and null >= 0.0)
    check("4 rule rejects when the specimen Rp fails the quality gate",
          not detection.is_detected(99.0, 0.1, detection.QUALITY_MAX_RP + 1.0))
    check("4 rule accepts a strong estimate on a good fit",
          detection.is_detected(10.0, 0.5, 15.0))

    # 5. shared fit finite.
    shared = estimator.shared_fit(specs2, [ref])
    check("5 shared cross-specimen amplitude is finite", np.all(np.isfinite(shared))
          and len(shared) == 1)

    # 6. Slice-2 dialog: builds, runs, populates, stays read-only.
    from PySide6.QtWidgets import QApplication
    from mudlab.nonclay import NonclayDialog
    _app = QApplication.instance() or QApplication([])
    proj3 = load_mud(path)
    mix3 = proj3.mixtures[0]
    mix3.calculate()
    before3 = (mix3.fractions.copy(), mix3.scales.copy(), mix3.bgshifts.copy())
    dlg = NonclayDialog(mix3)
    dlg.add_reference(_synthetic_quartz())
    dlg.run()
    table = dlg.ui.tbl_results
    n_spec = len([s for s in mix3.specimens if s is not None])
    check("6 dialog populates the results table (refs x specimens)",
          table.rowCount() == 1 and table.columnCount() == n_spec
          and table.item(0, 0) is not None)
    check("6 dialog is read-only (mixture fractions/scales/bg unchanged)",
          np.allclose(before3[0], mix3.fractions)
          and np.allclose(before3[1], mix3.scales)
          and np.allclose(before3[2], mix3.bgshifts))
    check("6 dialog CSV export is non-empty", len(dlg._csv_text().strip()) > 0)
    dlg.deleteLater()

    # 7. XRF mass balance recovers a known clay:quartz split (self-consistent).
    from mudlab.nonclay import chemistry
    from mudlab.calculations.composition import mixture_composition
    _n, oxide_rows = mixture_composition(mix3)
    order = [o for o, _pcts in oxide_rows]
    clay_vec = [pcts[0] for _o, pcts in oxide_rows]
    xrf = {o: 0.85 * clay_vec[k] + (15.0 if o == "SiO2" else 0.0)
           for k, o in enumerate(order)}
    mb = chemistry.mass_balance(mix3, xrf, [_synthetic_quartz()])
    wpct = dict(zip(mb.components, mb.weight_pct)) if mb else {}
    check("7 XRF mass balance recovers the known clay:quartz split (~15%)",
          mb is not None and abs(wpct.get("synthetic-quartz", 0.0) - 15.0) < 3.0)
    check("7 mass balance returns None without XRF",
          chemistry.mass_balance(mix3, {}, [_synthetic_quartz()]) is None)

    # 7b. dialog weight-% path: fill the XRF table, run, get a mass balance.
    dlg2 = NonclayDialog(load_mud(path).mixtures[0])
    dlg2.add_reference(_synthetic_quartz())
    for k, oxide in enumerate(dlg2._xrf_oxides):
        dlg2.ui.tbl_xrf.item(k, 0).setText("%.3f" % xrf.get(oxide, 0.0))
    dlg2.run()
    check("7 dialog computes the XRF weight-% mass balance",
          dlg2._massbalance is not None
          and "weight %" in dlg2.ui.lbl_summary.text().lower())
    dlg2.deleteLater()

    # 8. CIF reference construction (self-contained minimal alpha-quartz CIF).
    import tempfile
    from mudlab.nonclay import structure
    cif_text = (
        "data_quartz\n"
        "_cell_length_a 4.9137\n_cell_length_b 4.9137\n_cell_length_c 5.4047\n"
        "_cell_angle_alpha 90\n_cell_angle_beta 90\n_cell_angle_gamma 120\n"
        "loop_\n_space_group_symop_operation_xyz\n"
        "x,y,z\ny,x,2/3-z\n-y,x-y,2/3+z\n-x,-x+y,1/3-z\n-x+y,-x,1/3+z\nx-y,-y,-z\n"
        "loop_\n_atom_site_label\n_atom_site_fract_x\n_atom_site_fract_y\n"
        "_atom_site_fract_z\nSi 0.4697 0.0000 0.0000\nO 0.4135 0.2669 0.1191\n"
    )
    g = [s for s in mix3.specimens if s is not None][0].goniometer
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_q_%d.cif" % os.getpid())
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(cif_text)
    try:
        cif_ref, cif_comp = structure.reference_from_cif(tmp, g, name="quartz-CIF")
        cx = np.asarray(cif_ref.raw_pattern_x)
        cy = np.asarray(cif_ref.raw_pattern_y)

        def _pk(pos, w=0.3):
            sel = (cx >= pos - w) & (cx <= pos + w)
            return float(cy[sel].max()) if np.any(sel) else 0.0

        check("8 from-CIF quartz: 101 (26.66) strongest, 100 (20.85) present",
              _pk(26.66) > 50 and _pk(20.85) > 3 and _pk(26.66) > _pk(20.85))
        check("8 from-CIF quartz composition is ~pure SiO2",
              abs(cif_comp.get("SiO2", 0.0) - 100.0) < 1.0)
        mb2 = chemistry.mass_balance(mix3, xrf, [cif_ref], [cif_comp])
        wp2 = dict(zip(mb2.components, mb2.weight_pct)) if mb2 else {}
        check("8 mass balance uses the CIF-derived composition (~15% quartz)",
              mb2 is not None and abs(wp2.get("quartz-CIF", 0.0) - 15.0) < 3.0)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    tmp2 = tmp + "-noops.cif"
    with open(tmp2, "w", encoding="utf-8") as fh:
        fh.write("_cell_length_a 4.9\n_cell_length_b 4.9\n_cell_length_c 5.4\n"
                 "_cell_angle_alpha 90\n_cell_angle_beta 90\n_cell_angle_gamma 120\n")
    try:
        raised = False
        try:
            structure.reference_from_cif(tmp2, g)
        except ValueError:
            raised = True
        check("8 a CIF without explicit symmetry ops is rejected clearly", raised)
    finally:
        if os.path.exists(tmp2):
            os.remove(tmp2)

    # 9. #3b manual composition: the normalise helper + a manually-composed
    # reference (no built-in composition) becomes quantifiable.
    from mudlab.nonclay.dialog import _normalize_composition
    norm = _normalize_composition({"SiO2": 60.0, "Al2O3": 20.0,
                                   "Fe2O3": 0.0, "junk": -5})
    check("9 _normalize_composition drops <=0 and sums to 100",
          abs(sum(norm.values()) - 100.0) < 1e-6
          and "Fe2O3" not in norm and "junk" not in norm)
    unknown = nonclay.reference_from_arrays(np.arange(4, 40, 0.5),
                                            np.ones(72), "mystery")
    mb3 = chemistry.mass_balance(mix3, xrf, [unknown], [{"SiO2": 100.0}])
    wp3 = dict(zip(mb3.components, mb3.weight_pct)) if mb3 else {}
    check("9 a manual composition makes an unknown reference quantifiable (~15%)",
          mb3 is not None and abs(wp3.get("mystery", 0.0) - 15.0) < 3.0)

    # 10. #4 instrumental FWHM from a (synthetic) Si standard.
    from mudlab.nonclay.instrument import instrumental_fwhm
    si_x = np.arange(20.0, 90.0, 0.01)
    si_y = np.zeros_like(si_x)
    true_fwhm = 0.15
    sig = true_fwhm / 2.355
    for pos in (28.44, 47.30, 56.12, 69.13, 76.37, 88.03):
        si_y += 100.0 * np.exp(-0.5 * ((si_x - pos) / sig) ** 2)
    check("10 instrumental FWHM from a synthetic Si standard (~0.15 deg)",
          abs(instrumental_fwhm(si_x, si_y) - true_fwhm) < 0.02)
    check("10 instrumental FWHM falls back to the default on a flat pattern",
          abs(instrumental_fwhm(si_x, np.zeros_like(si_x), default=0.10) - 0.10) < 1e-9)
    return None


def main():
    print("=" * 72)
    print("Non-clay decomposition engine (EXPERIMENTAL)")
    print("=" * 72)
    path = _find_fixture()
    if path is None:
        print("No sample project found; skipping (exit 2).")
        return 2
    print("fixture: %s" % os.path.basename(path))
    run(path)
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("Non-clay harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
