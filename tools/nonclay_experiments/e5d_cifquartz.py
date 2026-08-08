#!/usr/bin/env python
"""Q1 / E5d - CIF quartz reference constructed with the SPECIMEN GONIOMETER vs
the measured quartz curve, in the decomposition.

The goniometer here is single-wavelength Ka1 (0.154056 nm), so the clays were
computed without a Ka2 doublet. Construct the quartz reference the SAME way: from
the CIF structure factors (LP included) at the goniometer's Ka1 positions,
broadened to the instrumental width (~0.11 deg FWHM from Si). This keeps quartz
in the SAME computational space as the clay model. Fit both the measured curve
and this CIF curve to a modeled specimen's residual and compare - including the
clean 100 (0.426) vs illite-003-contaminated 101 (0.334) contributions (F28).
"""
from __future__ import annotations

import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
import structure_pattern as SP  # noqa: E402
from mudlab import nonclay  # noqa: E402
from mudlab.nonclay import estimator  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

DIR = os.path.join(os.path.expanduser("~"), "Downloads", "MudLab Test")
REF_Q = os.path.join(os.path.expanduser("~"), "Downloads", "Raw pattern phases", "quartz.txt")
FWHM = 0.11  # instrumental, from the Si standard


def cif_quartz_reference(gonio):
    cif = urllib.request.urlopen(urllib.request.Request(
        "https://www.crystallography.net/cod/9000775.cif",
        headers={"User-Agent": "mudlab"}), timeout=25).read().decode("utf-8", "replace")
    wk, known = SP.load_wk_all()
    cell, sym, atoms = SP.parse_cif(cif, known)
    sticks = SP.stick(cell, SP.expand(atoms, sym), wk, hmax=6, tt_lo=15.0, tt_hi=40.0, Bdef=0.5)
    # re-map to the goniometer's Ka1 (nm) and broaden to the instrumental width
    lam = gonio.wavelength * 10.0  # nm -> Angstrom (structure_pattern uses Angstrom)
    x = np.arange(4.0, 40.0, 0.01)
    y = np.zeros_like(x)
    sig = FWHM / 2.355
    for tt, inten in sticks:
        d = 1.540598 / (2 * np.sin(np.radians(tt / 2)))          # d from the calc's Ka1
        tt_g = 2 * np.degrees(np.arcsin(lam / (2 * d)))          # re-place at the gonio Ka1
        y += inten * np.exp(-0.5 * ((x - tt_g) / sig) ** 2)
    y = 100.0 * y / y.max()
    return nonclay.reference_from_arrays(x, y, "quartz-CIF")


def main():
    mix = load_mud(os.path.join(DIR, "348.mud")).mixtures[0]
    mix.calculate()
    ad = [s for s in mix.specimens if s is not None][0]
    print("specimen: %s   clay Rp=%.2f" % (ad.name, estimator.specimen_rp(ad)))

    measured = nonclay.load_reference(REF_Q, name="quartz-measured")
    cif = cif_quartz_reference(ad.goniometer)

    print("\n%-16s %10s %8s %8s   %s"
          % ("reference", "quartz%", "null%", "detect", "peak split (100:101 of ref)"))
    for ref in (measured, cif):
        sr = nonclay.decompose_specimen(ad, [ref], detect=True)
        rr = sr.references[0]
        # the reference's own 100:101 balance on the specimen grid
        row = estimator.reference_intensities(ad, [ref])[0]
        x, _ = ad.experimental_pattern
        x = np.asarray(x)

        def a(pos, w=0.35):
            sel = (x >= pos - w) & (x <= pos + w)
            return float(np.trapezoid(np.clip(row[sel], 0, None), x[sel])) if np.any(sel) else 0.0
        r100, r101 = a(20.86), a(26.66)
        print("%-16s %9.2f%% %7.2f%% %8s   100/101=%.2f"
              % (ref.name, rr.pct, rr.null_pct, rr.detected,
                 r100 / r101 if r101 else 0))
    print("\nBoth references carry BOTH quartz peaks with a fixed 100/101 ratio, so the "
          "clean 100 anchors the amplitude (F28). CIF = same Ka1 space as the clay model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
