#!/usr/bin/env python
"""E5c - XRD-detect leg: is the Finding-24 Fe deficit a discrete Fe-OXIDE
accessory (hematite / goethite) or Fe-in-clays?

Generate hematite (Fe2O3) + goethite (FeOOH) references from COD CIFs via the
from-CIF calculator, broaden the sticks to the instrumental width (~0.12 deg
FWHM from the Si standard), and fit them (+ measured quartz) to each project's
clay-subtracted residual with the detection rule. If hematite/goethite clear
their null -> a discrete Fe-oxide accessory is present.

Detrital MICA is NOT fitted: muscovite 002 = 10 A = illite (absorbed by the
illite fit) AND micas orient like the clays - intrinsically not separable by the
oriented-mount residual method (noted, Finding 25).
"""
from __future__ import annotations

import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO, "tools", "nonclay_experiments"))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
import structure_pattern as SP  # noqa: E402
from mudlab import nonclay  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

DIR = os.path.join(os.path.expanduser("~"), "Downloads", "MudLab Test")
REF_Q = os.path.join(os.path.expanduser("~"), "Downloads", "Raw pattern phases", "quartz.txt")
PROJECTS = [("348.mud", "AT-348/4"), ("416.mud", "AT-416/1"), ("AT460 r1.mud", "AT-460/1")]
FWHM = 0.12  # deg 2theta, ~ instrumental (Si)


def fetch(cid):
    return urllib.request.urlopen(urllib.request.Request(
        "https://www.crystallography.net/cod/%d.cif" % cid,
        headers={"User-Agent": "mudlab"}), timeout=25).read().decode("utf-8", "replace")


def probe(cands, need_elems, known):
    for cid in cands:
        try:
            cif = fetch(cid)
        except Exception:
            continue
        f = re.search(r"_chemical_formula_sum\s+'?([^'\n]+)", cif)
        formula = (f.group(1) if f else "").replace(" ", "")
        if all(e in formula for e in need_elems):
            cell, sym, atoms = SP.parse_cif(cif, known)
            if cell[0] and sym:
                return cid, formula, cell, sym, atoms
    return None


def broadened_reference(cell, atoms, wk, name, lo=4.0, hi=40.0):
    comp = SP.stick(cell, atoms, wk, hmax=10, tt_lo=lo, tt_hi=hi, Bdef=0.5)
    x = np.arange(lo, hi, 0.01)
    y = np.zeros_like(x)
    sig = FWHM / 2.355
    for tt, inten in comp:
        y += inten * np.exp(-0.5 * ((x - tt) / sig) ** 2)
    if y.max() > 0:
        y = 100.0 * y / y.max()
    return nonclay.reference_from_arrays(x, y, name)


def main():
    wk, known = SP.load_wk_all()
    hem = probe([9000139, 9002165, 1011240, 9015964, 5000226], ["Fe2", "O3"], known)
    goe = probe([9002158, 2300147, 9000045, 1011128, 9016369], ["Fe", "O2", "H"], known)
    refs = [nonclay.load_reference(REF_Q, name="quartz")]
    if hem:
        print("hematite  COD %d  %s  a=%.3f c=%.3f" % (hem[0], hem[1], hem[2][0], hem[2][2]))
        refs.append(broadened_reference(hem[2], SP.expand(hem[4], hem[3]), wk, "hematite"))
    if goe:
        print("goethite  COD %d  %s  a=%.3f b=%.3f c=%.3f"
              % (goe[0], goe[1], goe[2][0], goe[2][1], goe[2][2]))
        refs.append(broadened_reference(goe[2], SP.expand(goe[4], goe[3]), wk, "goethite"))
    names = [r.name for r in refs]
    print("references:", names)

    for proj, sample in PROJECTS:
        mix = load_mud(os.path.join(DIR, proj)).mixtures[0]
        mix.calculate()
        ad = [s for s in mix.specimens if s is not None][0]
        sr = nonclay.decompose_specimen(ad, refs, detect=True)
        print("\n=== %s (%s)  [%s] ===" % (proj, sample, ad.name))
        for rr in sr.references:
            print("  %-9s  %6.2f%% (intensity)  null=%.2f%%  detected=%s"
                  % (rr.name, rr.pct, rr.null_pct, rr.detected))
    print("\nNOTE: detrital mica NOT fitted - muscovite 002 = 10 A overlaps illite and "
          "micas orient like clays, so the oriented-mount residual cannot isolate it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
