#!/usr/bin/env python
"""E1c - validate the from-CIF calculator on a SECOND mineral (corundum) and
use it to DECIDE the E1 gate on the provided Corundum_LargeCS.txt.

Two things at once:
  (1) calculator generalisation: compute corundum from a COD CIF and compare to
      ICDD 46-1212 (a HIGH-confidence standard). Flat ratio => the calculator is
      not a quartz fluke.
  (2) decisive E1 gate: compare the PROVIDED Corundum_LargeCS.txt to the
      from-CIF (LP-included) pattern. Flat ratio => the provided file is
      observed-space (CLEAR it); a positive ramp => it lacks LP (flag it). Since
      all 7 CS files came from one pipeline, corundum's verdict is strong
      evidence for albite/orthoclase/clinoptilolite too.

Robust CIF parser (handles occupancy / extra atom-site columns / symop index).
"""
from __future__ import annotations

import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO, "tools"))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
import prototype_nonclay as P  # noqa: E402

LAMBDA = 1.540598
SCAT_CSV = os.path.join(_REPO, "src", "mudlab", "data", "atomic_scattering_factors.csv")
CORUNDUM_ICDD = ((25.58, 45), (35.15, 100), (37.78, 21), (43.36, 66),
                 (52.55, 34), (57.50, 89), (61.12, 14), (66.52, 34), (68.21, 54))


def load_wk_all():
    wk, elements = {}, set()
    with open(SCAT_CSV, encoding="utf-8") as fh:
        header = fh.readline().split(",")
        idx = {n: i for i, n in enumerate(header)}
        for line in fh:
            p = line.split(",")
            if p[idx["charge"]].strip() != "0":
                continue
            name = p[idx["name"]]
            wk[name] = (float(p[idx["par_c"]]),
                        np.array([float(p[idx["par_a%d" % i]]) for i in range(1, 6)]),
                        np.array([float(p[idx["par_b%d" % i]]) for i in range(1, 6)]))
            elements.add(name)
    return wk, elements


def element_of(token, known):
    alpha = re.match(r"[A-Za-z]+", token.strip()).group()
    if alpha[:2].capitalize() in known:
        return alpha[:2].capitalize()
    if alpha[:1].upper() in known:
        return alpha[:1].upper()
    return None


def parse_cif(text, known):
    def num(key):
        m = re.search(r"^%s\s+([-0-9.eE()]+)" % re.escape(key), text, re.M)
        return float(re.sub(r"\(.*?\)", "", m.group(1))) if m else None
    cell = (num("_cell_length_a"), num("_cell_length_b"), num("_cell_length_c"),
            num("_cell_angle_alpha"), num("_cell_angle_beta"), num("_cell_angle_gamma"))
    lines = text.splitlines()
    sym, atoms, i = [], [], 0
    while i < len(lines):
        if lines[i].strip() == "loop_":
            j, tags = i + 1, []
            while j < len(lines) and lines[j].strip().startswith("_"):
                tags.append(lines[j].strip()); j += 1
            rows = []
            while j < len(lines):
                s = lines[j].strip()
                if s == "" or s == "loop_" or s.startswith("_") \
                        or s.startswith("data_") or s.startswith("#") or s.startswith(";"):
                    break
                rows.append(s); j += 1
            i = j
            if any("symop" in t or "equiv_pos" in t for t in tags):
                for r in rows:
                    m = re.search(r"([\-+xyz0-9/.]+\s*,\s*[\-+xyz0-9/.]+\s*,\s*[\-+xyz0-9/.]+)",
                                  r.replace("'", " ").replace('"', " "))
                    if m:
                        sym.append([c.strip() for c in m.group(1).split(",")])
            elif any(t == "_atom_site_fract_x" for t in tags):
                col = {t: k for k, t in enumerate(tags)}
                ix, iy, iz = col["_atom_site_fract_x"], col["_atom_site_fract_y"], col["_atom_site_fract_z"]
                il = col.get("_atom_site_type_symbol", col.get("_atom_site_label"))
                iocc = col.get("_atom_site_occupancy")
                for r in rows:
                    tok = r.split()
                    if len(tok) < len(tags):
                        continue
                    el = element_of(tok[il], known)
                    if el is None:
                        continue
                    fx = float(re.sub(r"\(.*?\)", "", tok[ix]))
                    fy = float(re.sub(r"\(.*?\)", "", tok[iy]))
                    fz = float(re.sub(r"\(.*?\)", "", tok[iz]))
                    occ = float(re.sub(r"\(.*?\)", "", tok[iocc])) if iocc is not None else 1.0
                    atoms.append((el, fx, fy, fz, occ))
        else:
            i += 1
    return cell, sym, atoms


def expand(atoms, sym):
    out = []
    for el, x, y, z, occ in atoms:
        seen = set()
        for parts in sym:
            v = [eval(p, {"__builtins__": {}}, {"x": x, "y": y, "z": z}) % 1.0 for p in parts]
            key = tuple(round(q, 4) for q in v)
            if key not in seen:
                seen.add(key)
                out.append((el, v[0], v[1], v[2], occ))
    return out


def metric(cell):
    a, b, c, al, be, ga = cell
    al, be, ga = np.radians([al, be, ga])
    G = np.array([[a * a, a * b * np.cos(ga), a * c * np.cos(be)],
                  [a * b * np.cos(ga), b * b, b * c * np.cos(al)],
                  [a * c * np.cos(be), b * c * np.cos(al), c * c]])
    return np.linalg.inv(G)


def stick(cell, atoms, wk, hmax=10, tt_lo=10, tt_hi=70, Bdef=0.5):
    Gstar = metric(cell)
    els = np.array([a[0] for a in atoms])
    xyz = np.array([[a[1], a[2], a[3]] for a in atoms])
    occ = np.array([a[4] for a in atoms])
    acc = {}
    rng = range(-hmax, hmax + 1)
    for h in rng:
        for k in rng:
            for l in rng:
                if h == k == l == 0:
                    continue
                hkl = np.array([h, k, l], float)
                dstar2 = float(hkl @ Gstar @ hkl)
                if dstar2 <= 0:
                    continue
                d = 1 / np.sqrt(dstar2)
                s = LAMBDA / (2 * d)
                if s >= 1:
                    continue
                theta = np.arcsin(s); tt = np.degrees(2 * theta)
                if not (tt_lo <= tt <= tt_hi):
                    continue
                s2 = (0.5 / d) ** 2
                fcache = {e: (wk[e][0] + np.sum(wk[e][1] * np.exp(-wk[e][2] * s2)))
                          for e in set(els)}
                f = np.array([fcache[e] for e in els]) * np.exp(-Bdef * s2) * occ
                phase = 2 * np.pi * (xyz @ hkl)
                F = np.sum(f * np.exp(1j * phase))
                lp = (1 + np.cos(2 * theta) ** 2) / (np.sin(theta) ** 2 * np.cos(theta))
                key = round(tt, 2)
                acc[key] = acc.get(key, 0.0) + abs(F) ** 2 * lp
    return sorted(acc.items())


def probe_corundum(known):
    for cid in (1000032, 9005248, 1200015, 1526870, 9007634, 5000198):
        try:
            cif = urllib.request.urlopen(urllib.request.Request(
                "https://www.crystallography.net/cod/%d.cif" % cid,
                headers={"User-Agent": "mudlab"}), timeout=20).read().decode("utf-8", "replace")
        except Exception:
            continue
        f = re.search(r"_chemical_formula_sum\s+'?([^'\n]+)", cif)
        formula = f.group(1).replace(" ", "") if f else ""
        if "Al2O3" in formula or ("Al" in formula and "O3" in formula):
            cell, sym, atoms = parse_cif(cif, known)
            if cell[0] and 4.6 < cell[0] < 4.9 and len(sym) >= 6:
                print("chose corundum COD %d  formula=%s  a=%.4f c=%.4f  ops=%d"
                      % (cid, formula, cell[0], cell[2], len(sym)))
                return cell, sym, atoms
    return None


def sticks_norm(peaks):
    imax = max(v for _, v in peaks) or 1.0
    return [(tt, 100 * v / imax) for tt, v in peaks]


def near(tbl, pos, w=0.4):
    vals = [v for t, v in tbl if abs(t - pos) <= w]
    return max(vals) if vals else 0.0


def main():
    wk, known = load_wk_all()
    got = probe_corundum(known)
    if not got:
        print("no corundum CIF fetched"); return 1
    cell, sym, atoms = got
    from collections import Counter
    full = expand(atoms, sym)
    print("expanded atoms: %s" % dict(Counter(a[0] for a in full)))
    comp = sticks_norm(stick(cell, full, wk, Bdef=0.4))
    cprov = P.load_reference("Corundum_LargeCS.txt")
    px, py = np.asarray(cprov.raw_pattern_x), np.asarray(cprov.raw_pattern_y)

    def prov(pos, w=0.4):
        sel = (px >= pos - w) & (px <= pos + w)
        return float(py[sel].max()) if np.any(sel) else 0.0

    cmax = max(near(comp, p) for p, _ in CORUNDUM_ICDD) or 1.0
    pmax = max(prov(p) for p, _ in CORUNDUM_ICDD) or 1.0
    print("\n%8s %8s %10s %12s %10s %12s"
          % ("2theta", "ICDD", "fromCIF", "providedCS", "cif/ICDD", "prov/cif"))
    r_cal, r_gate = [], []
    for pos, icdd in CORUNDUM_ICDD:
        cc = 100 * near(comp, pos) / cmax
        pp = 100 * prov(pos) / pmax
        rc = cc / icdd if icdd else 0
        rg = (pp / cc) if cc else float("nan")
        r_cal.append((pos, rc))
        if np.isfinite(rg) and cc > 3:
            r_gate.append((pos, rg))
        print("%8.2f %8d %10.1f %12.1f %10.2f %12.2f" % (pos, icdd, cc, pp, rc, rg))
    s_cal = np.polyfit([p for p, _ in r_cal], [r for _, r in r_cal], 1)[0]
    s_gate = np.polyfit([p for p, _ in r_gate], [r for _, r in r_gate], 1)[0]
    print("\n(1) calculator check:  fromCIF/ICDD slope %+.5f  ->  %s"
          % (s_cal, "calculator OK (generalises)" if abs(s_cal) < 0.012
             else "calculator off for corundum"))
    print("(2) E1 gate on provided file:  providedCS/fromCIF slope %+.5f  ->  %s"
          % (s_gate, "provided IS observed-space (CLEAR)" if abs(s_gate) < 0.012
             else "provided lacks a matching LP weighting (FLAG)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
