#!/usr/bin/env python
"""E4-prep - validate the from-CIF calculator + LP against a REAL same-instrument
measurement (NIST SRM 640f Si) and confirm the instrument match (Finding 21).

Computes Si from the NIST-certified structure (a=5.431144, B_iso=0.556, diamond
cubic) and compares to the user's measured Si standard (PANalytical Empyrean,
fixed slits, NO monochromator). A flat measured/computed ratio => the calculator
+ conventional LP are correct for this instrument, so from-CIF reference
generation is valid for its samples, and the measured/computed scale is the E4
instrument constant for RIR-free absolute accessory quant.

Reads local (gitignored) data: ~/Downloads/'Si std 18-12-2025.xrdml' and a
343-family .mud (same instrument as the Si run - radius 24 cm = 240 mm, fixed
0.5 deg divergence, 0.0167 deg step, Cu). Needs no internet.
"""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
import structure_pattern as SP  # noqa: E402  (the graduated from-CIF calculator)
from mudlab.file_parsers.xrdml_parser import parse_xrdml  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

_DL = os.path.join(os.path.expanduser("~"), "Downloads")
SI_XRDML = os.path.join(_DL, "Si std 18-12-2025.xrdml")
SAME_INSTRUMENT_MUD = "343 2 r3.mud"   # same rig as the Si run
A = 5.431144   # NIST SRM 640f certified
B_ISO = 0.556
# Diamond-cubic Si, 8 atoms (|F|^2 is origin-independent).
DIAMOND = [(0, 0, 0), (0.5, 0.5, 0), (0.5, 0, 0.5), (0, 0.5, 0.5),
           (0.25, 0.25, 0.25), (0.75, 0.75, 0.25), (0.75, 0.25, 0.75), (0.25, 0.75, 0.75)]


def _find_mud(name):
    for base in (os.path.join(_REPO, "tools", "sample_projects"), _DL):
        p = os.path.join(base, name)
        if os.path.isfile(p):
            return p
    return None


def main():
    if not os.path.isfile(SI_XRDML):
        print("Si xrdml not found (local data); skipping."); return 2
    x, y = parse_xrdml(SI_XRDML)
    x, y = np.asarray(x, float), np.asarray(y, float)
    print("measured Si: %d pts  2th %.2f-%.2f  Imax %.0f @ %.3f"
          % (x.size, x.min(), x.max(), y.max(), x[y.argmax()]))

    mud = _find_mud(SAME_INSTRUMENT_MUD)
    if mud:
        g = [s for s in load_mud(mud).mixtures[0].specimens if s is not None][0].goniometer
        print("%s goniometer: wavelength=%.5f nm  radius=%.1f (cm; x10 = mm)  div=%s deg"
              % (SAME_INSTRUMENT_MUD, g.wavelength, getattr(g, "radius", float("nan")),
                 getattr(g, "divergence", "?")))

    wk, _known = SP.load_wk_all()
    atoms = [("Si", px, py, pz, 1.0) for (px, py, pz) in DIAMOND]
    comp = SP.stick((A, A, A, 90.0, 90.0, 90.0), atoms, wk,
                    hmax=6, tt_lo=25.0, tt_hi=80.0, Bdef=B_ISO)
    imax = max(v for _, v in comp) or 1.0
    comp = [(tt, 100 * v / imax) for tt, v in comp if 100 * v / imax > 0.5]

    labels = [(28.44, "111"), (47.30, "220"), (56.12, "311"),
              (69.13, "400"), (76.37, "331")]

    def meas_area(pos, w=0.6):
        sel = (x >= pos - w) & (x <= pos + w)
        if not np.any(sel):
            return 0.0, pos
        xs, ys = x[sel], y[sel]
        return float(np.trapezoid(ys - ys.min(), xs)), float(xs[ys.argmax()])

    def comp_at(pos, w=0.5):
        vals = [v for t, v in comp if abs(t - pos) <= w]
        return max(vals) if vals else 0.0

    m0 = meas_area(28.44)[0] or 1.0
    c0 = comp_at(28.44) or 1.0
    print("\n%5s %9s %10s %10s %10s %8s"
          % ("hkl", "2th_ideal", "2th_meas", "measured", "computed", "ratio"))
    rows = []
    for pos, name in labels:
        ma, mpos = meas_area(pos)
        ca = comp_at(pos)
        mn, cn = 100 * ma / m0, 100 * ca / c0
        r = mn / cn if cn else float("nan")
        rows.append((pos, r, mpos))
        print("%5s %9.2f %10.3f %10.1f %10.1f %8.2f" % (name, pos, mpos, mn, cn, r))

    good = [(p, r) for p, r, _ in rows if np.isfinite(r) and r > 0]
    slope = np.polyfit([p for p, _ in good], [r for _, r in good], 1)[0]
    off = float(np.mean([mp - p for p, _, mp in rows]))
    print("\nmean 2theta offset (meas - ideal): %+.3f deg (sample displacement/zero)" % off)
    print("measured/computed ratio-vs-2theta slope: %+.5f  ->  %s"
          % (slope, "LP + calculator MATCH the real instrument (flat)"
             if abs(slope) < 0.02 else "deviation - inspect"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
