#!/usr/bin/env python
"""E1d - confirm the E1 gate on a triclinic feldspar (albite): does the provided
Albite_LargeCS.txt match a from-CIF (LP-included) albite pattern?

No hand-entered standard needed: the DECISIVE test is provided-vs-fromCIF slope.
Flat => the provided file is observed-space (CLEAR). Reuses the robust parser +
stick calculator from exp_e1c_corundum. This is also the parser stress-test
(triclinic cell, Al/Si sites, occupancies).
"""
from __future__ import annotations

import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCR)
sys.path.insert(0, os.path.join(_REPO, "tools"))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
import prototype_nonclay as P  # noqa: E402
import structure_pattern as C  # noqa: E402  (reuse parser + calculator)


def probe_albite(known):
    for cid in (9000525, 9000526, 2107372, 9000527, 1556998):
        try:
            cif = urllib.request.urlopen(urllib.request.Request(
                "https://www.crystallography.net/cod/%d.cif" % cid,
                headers={"User-Agent": "mudlab"}), timeout=20).read().decode("utf-8", "replace")
        except Exception:
            continue
        f = re.search(r"_chemical_formula_sum\s+'?([^'\n]+)", cif)
        formula = (f.group(1).replace(" ", "") if f else "")
        nm = re.search(r"_chemical_name_mineral\s+'?([^'\n]+)", cif)
        mineral = (nm.group(1).strip() if nm else "")
        if "Al" in formula and "Si3" in formula and "Na" in formula:
            cell, sym, atoms = C.parse_cif(cif, known)
            if cell[0] and 7.5 < cell[0] < 8.5:
                print("chose albite COD %d  formula=%s (%s)  a=%.3f b=%.3f c=%.3f"
                      " angles %.1f %.1f %.1f  ops=%d"
                      % (cid, formula, mineral, cell[0], cell[1], cell[2],
                         cell[3], cell[4], cell[5], len(sym)))
                return cell, sym, atoms
    return None


def main():
    wk, known = C.load_wk_all()
    got = probe_albite(known)
    if not got:
        print("no albite CIF fetched"); return 1
    cell, sym, atoms = got
    from collections import Counter
    full = C.expand(atoms, sym)
    print("expanded atoms: %s" % dict(Counter(a[0] for a in full)))

    comp = C.sticks_norm(C.stick(cell, full, wk, hmax=10, Bdef=0.7))
    # strongest computed peaks (albite has no single dominant line)
    top = sorted(comp, key=lambda kv: -kv[1])[:12]
    peak_pos = sorted(p for p, _ in top)

    print("\n-- provided Albite_LargeCS/SmallCS vs from-CIF, at the computed top peaks --")
    print("%8s %10s %12s %12s" % ("2theta", "fromCIF", "provLargeCS", "provSmallCS"))
    provs = {n: P.load_reference("Albite_%sCS_Bis-1.txt" % n) for n in ("Large", "Small")}

    def hmax_at(ph, pos, w=0.4):
        x, y = np.asarray(ph.raw_pattern_x), np.asarray(ph.raw_pattern_y)
        sel = (x >= pos - w) & (x <= pos + w)
        return float(y[sel].max()) if np.any(sel) else 0.0

    cmax = max(C.near(comp, p) for p in peak_pos) or 1.0
    lmax = max(hmax_at(provs["Large"], p) for p in peak_pos) or 1.0
    smax = max(hmax_at(provs["Small"], p) for p in peak_pos) or 1.0
    ratios_L, ratios_S = [], []
    for pos in peak_pos:
        cc = 100 * C.near(comp, pos) / cmax
        ll = 100 * hmax_at(provs["Large"], pos) / lmax
        ss = 100 * hmax_at(provs["Small"], pos) / smax
        if cc > 5:
            ratios_L.append((pos, ll / cc)); ratios_S.append((pos, ss / cc))
        print("%8.2f %10.1f %12.1f %12.1f" % (pos, cc, ll, ss))
    sL = np.polyfit([p for p, _ in ratios_L], [r for _, r in ratios_L], 1)[0]
    sS = np.polyfit([p for p, _ in ratios_S], [r for _, r in ratios_S], 1)[0]
    print("\nE1 gate (provided/fromCIF slope):  LargeCS %+.5f   SmallCS %+.5f"
          % (sL, sS))
    print("=> %s" % ("both observed-space (CLEAR) - CS files carry LP"
                     if abs(sL) < 0.012 and abs(sS) < 0.012
                     else "at least one deviates - inspect"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
