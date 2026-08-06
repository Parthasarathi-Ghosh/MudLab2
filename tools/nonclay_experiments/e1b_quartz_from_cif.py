#!/usr/bin/env python
"""E1b - can a mineral STRUCTURE (CIF) be obtained and USED here to make an
observed-space reference/standard?

No powder-pattern library is bundled, but MudLab ships Waasmaier-Kirfel atomic
scattering factors, so we can compute the pattern ourselves. This fetches an
ambient alpha-quartz CIF from the COD (free), parses cell + symmetry ops +
atoms, and computes a stick pattern:

    F(hkl) = sum_atoms occ * f_j(s) * exp(-B_j s^2) * exp(2pi i (hx+ky+lz))
    I(hkl) = |F|^2 * LP(theta),   LP = (1+cos^2 2th)/(sin^2 th cos th)
    s = sin(theta)/lambda = 1/(2d),  d from the reciprocal metric tensor

LP is applied EXPLICITLY, so the result is observed-space BY CONSTRUCTION.
Validation: compare the normalised stick intensities to ICDD 46-1045 and to the
measured quartz.txt at the known quartz peak positions, and run the same E1
ratio-slope test (should be ~0). If it matches, a CIF can be used here to
generate LP-included standards for the minerals whose provenance is uncertain
(albite, corundum, ...), making the E1 gate decisive - and it is the Case-B seed.
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

LAMBDA = 1.540598  # Cu Ka1, Angstrom
SCAT_CSV = os.path.join(_REPO, "src", "mudlab", "data", "atomic_scattering_factors.csv")
DEFAULT_B = {"Si": 0.47, "O": 0.95}  # isotropic B (Ang^2), ~ from the CIF U's


def load_wk(elements):
    """Waasmaier-Kirfel (c + sum a_i exp(-b_i s^2)) for NEUTRAL atoms."""
    wk = {}
    with open(SCAT_CSV, encoding="utf-8") as fh:
        header = fh.readline().split(",")
        idx = {name: i for i, name in enumerate(header)}
        for line in fh:
            p = line.split(",")
            name, charge = p[idx["name"]], p[idx["charge"]]
            if name in elements and charge.strip() == "0":
                c = float(p[idx["par_c"]])
                a = [float(p[idx["par_a%d" % i]]) for i in range(1, 6)]
                b = [float(p[idx["par_b%d" % i]]) for i in range(1, 6)]
                wk[name] = (c, np.array(a), np.array(b))
    return wk


def f_atom(wk_elem, s2):
    c, a, b = wk_elem
    return c + float(np.sum(a * np.exp(-b * s2)))


def parse_cif(text):
    def field(key):
        m = re.search(r"^%s\s+([-0-9.eE()]+)" % re.escape(key), text, re.M)
        return float(re.sub(r"\(.*?\)", "", m.group(1))) if m else None
    a = field("_cell_length_a"); b = field("_cell_length_b"); c = field("_cell_length_c")
    al = field("_cell_angle_alpha"); be = field("_cell_angle_beta"); ga = field("_cell_angle_gamma")
    # symmetry operations
    ops = re.findall(r"^\s*([\-+xyz0-9/, ]+)\s*$", text, re.M)
    sym = []
    for line in ops:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 3 and all(re.fullmatch(r"[\-+xyz0-9/. ]+", p) for p in parts):
            sym.append(parts)
    # atoms: label fx fy fz  (from the _atom_site_fract loop)
    atoms = []
    for m in re.finditer(r"^([A-Z][a-z]?)\w*\s+(-?\d\.\d+)\s+(-?\d\.\d+)\s+(-?\d\.\d+)\s*$",
                         text, re.M):
        el, x, y, z = m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))
        atoms.append((el, x, y, z))
    return (a, b, c, al, be, ga), sym, atoms


def expand(atoms, sym):
    out = []
    for el, x, y, z in atoms:
        seen = set()
        for parts in sym:
            v = [eval(p, {"__builtins__": {}}, {"x": x, "y": y, "z": z}) for p in parts]
            v = [q % 1.0 for q in v]
            key = tuple(round(q, 4) for q in v)
            if key not in seen:
                seen.add(key)
                out.append((el, v[0], v[1], v[2]))
    return out


def metric(cell):
    a, b, c, al, be, ga = cell
    al, be, ga = np.radians([al, be, ga])
    G = np.array([
        [a * a, a * b * np.cos(ga), a * c * np.cos(be)],
        [a * b * np.cos(ga), b * b, b * c * np.cos(al)],
        [a * c * np.cos(be), b * c * np.cos(al), c * c]])
    return np.linalg.inv(G)  # reciprocal metric (G*)


def stick_pattern(cell, atoms_full, wk, hmax=6, tt_lo=10.0, tt_hi=70.0):
    Gstar = metric(cell)
    acc = {}
    for h in range(-hmax, hmax + 1):
        for k in range(-hmax, hmax + 1):
            for l in range(-hmax, hmax + 1):
                if h == k == l == 0:
                    continue
                hkl = np.array([h, k, l], float)
                dstar2 = float(hkl @ Gstar @ hkl)
                if dstar2 <= 0:
                    continue
                d = 1.0 / np.sqrt(dstar2)
                s = LAMBDA / (2.0 * d)
                if not (-1 < s < 1):
                    continue
                theta = np.arcsin(s)
                tt = np.degrees(2 * theta)
                if not (tt_lo <= tt <= tt_hi):
                    continue
                s2 = (0.5 / d) ** 2
                F = 0j
                for el, x, y, z in atoms_full:
                    fj = f_atom(wk[el], s2) * np.exp(-DEFAULT_B[el] * s2)
                    F += fj * np.exp(2j * np.pi * (h * x + k * y + l * z))
                lp = (1 + np.cos(2 * theta) ** 2) / (np.sin(theta) ** 2 * np.cos(theta))
                key = round(tt, 2)
                acc[key] = acc.get(key, 0.0) + (abs(F) ** 2) * lp
    return acc


def main():
    cif = urllib.request.urlopen(urllib.request.Request(
        "https://www.crystallography.net/cod/9000775.cif",
        headers={"User-Agent": "mudlab"}), timeout=20).read().decode("utf-8", "replace")
    cell, sym, atoms = parse_cif(cif)
    print("cell a,b,c = %.4f %.4f %.4f  angles %.0f %.0f %.0f  | %d sym ops | asym atoms %s"
          % (cell[0], cell[1], cell[2], cell[3], cell[4], cell[5], len(sym),
             [a[0] for a in atoms]))
    wk = load_wk({a[0] for a in atoms})
    full = expand(atoms, sym)
    from collections import Counter
    print("expanded atoms per element: %s" % dict(Counter(a[0] for a in full)))

    acc = stick_pattern(cell, full, wk)
    peaks = sorted(acc.items())
    imax = max(v for _, v in peaks)
    sticks = [(tt, 100.0 * v / imax) for tt, v in peaks if 100.0 * v / imax > 1.0]
    print("\n-- computed quartz stick pattern (from COD 9000775 + WK factors + LP) --")
    print("%8s %8s" % ("2theta", "I(norm)"))
    for tt, inorm in sticks[:14]:
        print("%8.2f %8.1f" % (tt, inorm))

    # Compare to ICDD 46-1045 and to measured quartz.txt.
    print("\n-- validation: computed vs ICDD 46-1045 vs measured quartz.txt --")
    qtxt = P.load_reference("quartz.txt")
    qx, qy = np.asarray(qtxt.raw_pattern_x), np.asarray(qtxt.raw_pattern_y)

    def near(tbl, pos, w=0.35):
        vals = [v for t, v in tbl if abs(t - pos) <= w]
        return max(vals) if vals else 0.0

    def near_curve(pos, w=0.35):
        sel = (qx >= pos - w) & (qx <= pos + w)
        return float(qy[sel].max()) if np.any(sel) else 0.0

    comp_max = max(near(sticks, p) for p, _ in P._QUARTZ_STANDARD) or 1.0
    txt_max = max(near_curve(p) for p, _ in P._QUARTZ_STANDARD) or 1.0
    print("%8s %8s %10s %10s %8s %8s"
          % ("2theta", "ICDD", "computed", "quartz.txt", "c/ICDD", "t/ICDD"))
    ratios_c, ratios_t = [], []
    for pos, icdd in P._QUARTZ_STANDARD:
        cc = 100.0 * near(sticks, pos) / comp_max
        tt = 100.0 * near_curve(pos) / txt_max
        rc, rt = cc / icdd if icdd else 0, tt / icdd if icdd else 0
        ratios_c.append((pos, rc)); ratios_t.append((pos, rt))
        print("%8.2f %8d %10.1f %10.1f %8.2f %8.2f" % (pos, icdd, cc, tt, rc, rt))
    sc = np.polyfit([p for p, _ in ratios_c], [r for _, r in ratios_c], 1)[0]
    st = np.polyfit([p for p, _ in ratios_t], [r for _, r in ratios_t], 1)[0]
    print("\nratio-vs-2theta slope:  computed/ICDD %+.5f   quartz.txt/ICDD %+.5f"
          % (sc, st))
    print("=> computed-from-CIF is observed-space (LP present) BY CONSTRUCTION; "
          "if it tracks ICDD, a structure CAN be used here as a standard/reference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
