"""Construct a non-clay reference pattern from a crystal structure (CIF).

No powder-pattern library is bundled, but MudLab ships Waasmaier-Kirfel scattering
factors, so the pattern is computed here: parse the CIF (cell + explicit symmetry
operations + atoms), build structure factors F(hkl) with the Lorentz-polarisation
factor, then broaden the sticks to the instrumental width at the SPECIMEN
GONIOMETER's wavelength (Finding 29: a CIF reference so built is cleaner than a
measured curve - correct 100/101 ratio, lower null, instrument-matched).

Requires a CIF with EXPLICIT symmetry operations (a COD / AMCSD export). A CIF
carrying only a space-group number, or a BGMN ``.str`` (space-group number +
Wyckoff letters), needs a space-group operations table and is not supported yet
(Finding 19). LP is applied explicitly, so the reference is in observed-intensity
space (``apply_lpf`` stays False). READ-ONLY: nothing here touches the clay path.
"""

from __future__ import annotations

import os
import re

import numpy as np

from mudlab.nonclay.references import reference_from_arrays

_SCAT_CSV = os.path.join(
    os.path.dirname(__file__), os.pardir, "data", "atomic_scattering_factors.csv")


def _load_wk():
    """Waasmaier-Kirfel (c + sum a_i exp(-b_i s^2)) for NEUTRAL atoms."""
    wk, elements = {}, set()
    with open(_SCAT_CSV, encoding="utf-8") as handle:
        header = handle.readline().split(",")
        idx = {name: i for i, name in enumerate(header)}
        for line in handle:
            p = line.split(",")
            if p[idx["charge"]].strip() != "0":
                continue
            name = p[idx["name"]]
            wk[name] = (
                float(p[idx["par_c"]]),
                np.array([float(p[idx["par_a%d" % i]]) for i in range(1, 6)]),
                np.array([float(p[idx["par_b%d" % i]]) for i in range(1, 6)]),
            )
            elements.add(name)
    return wk, elements


def _element_of(token, known):
    match = re.match(r"[A-Za-z]+", token.strip())
    if not match:
        return None
    alpha = match.group()
    if alpha[:2].capitalize() in known:
        return alpha[:2].capitalize()
    if alpha[:1].upper() in known:
        return alpha[:1].upper()
    return None


def _parse_cif(text, known):
    """Return (cell, symmetry_ops, atoms). Handles occupancy / extra atom-site
    columns / a leading symop index."""
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
                if s in ("", "loop_") or s.startswith(("_", "data_", "#", ";")):
                    break
                rows.append(s); j += 1
            i = j
            if any("symop" in t or "equiv_pos" in t for t in tags):
                for r in rows:
                    m = re.search(
                        r"([\-+xyz0-9/.]+\s*,\s*[\-+xyz0-9/.]+\s*,\s*[\-+xyz0-9/.]+)",
                        r.replace("'", " ").replace('"', " "))
                    if m:
                        sym.append([c.strip() for c in m.group(1).split(",")])
            elif any(t == "_atom_site_fract_x" for t in tags):
                col = {t: k for k, t in enumerate(tags)}
                ix, iy = col["_atom_site_fract_x"], col["_atom_site_fract_y"]
                iz = col["_atom_site_fract_z"]
                il = col.get("_atom_site_type_symbol", col.get("_atom_site_label"))
                iocc = col.get("_atom_site_occupancy")
                for r in rows:
                    tok = r.split()
                    if len(tok) < len(tags):
                        continue
                    el = _element_of(tok[il], known)
                    if el is None:
                        continue
                    def f(idx):
                        return float(re.sub(r"\(.*?\)", "", tok[idx]))
                    occ = f(iocc) if iocc is not None else 1.0
                    atoms.append((el, f(ix), f(iy), f(iz), occ))
        else:
            i += 1
    return cell, sym, atoms


def _expand(atoms, sym):
    out = []
    for el, x, y, z, occ in atoms:
        seen = set()
        for parts in sym:
            v = [eval(p, {"__builtins__": {}}, {"x": x, "y": y, "z": z}) % 1.0
                 for p in parts]
            key = tuple(round(q, 4) for q in v)
            if key not in seen:
                seen.add(key)
                out.append((el, v[0], v[1], v[2], occ))
    return out


def _metric(cell):
    a, b, c, al, be, ga = cell
    al, be, ga = np.radians([al, be, ga])
    G = np.array([[a * a, a * b * np.cos(ga), a * c * np.cos(be)],
                  [a * b * np.cos(ga), b * b, b * c * np.cos(al)],
                  [a * c * np.cos(be), b * c * np.cos(al), c * c]])
    return np.linalg.inv(G)


def _stick(cell, atoms, wk, wavelength, hmax=10, tt_lo=4.0, tt_hi=80.0, b_iso=0.5):
    """(2theta, |F|^2 * LP) sticks at ``wavelength`` (Angstrom)."""
    gstar = _metric(cell)
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
                dstar2 = float(hkl @ gstar @ hkl)
                if dstar2 <= 0:
                    continue
                d = 1.0 / np.sqrt(dstar2)
                s = wavelength / (2.0 * d)
                if s >= 1.0:
                    continue
                theta = np.arcsin(s)
                tt = np.degrees(2 * theta)
                if not (tt_lo <= tt <= tt_hi):
                    continue
                s2 = (0.5 / d) ** 2
                fcache = {e: (wk[e][0] + np.sum(wk[e][1] * np.exp(-wk[e][2] * s2)))
                          for e in set(els)}
                fj = np.array([fcache[e] for e in els]) * np.exp(-b_iso * s2) * occ
                struct = np.sum(fj * np.exp(2j * np.pi * (xyz @ hkl)))
                lp = (1 + np.cos(2 * theta) ** 2) / (np.sin(theta) ** 2 * np.cos(theta))
                key = round(tt, 2)
                acc[key] = acc.get(key, 0.0) + abs(struct) ** 2 * lp
    return sorted(acc.items())


def reference_from_cif(path, goniometer, name=None, fwhm=0.10,
                       tt_lo=4.0, tt_hi=80.0):
    """Build a non-clay reference (RawPatternPhase) from a CIF, at the
    goniometer's wavelength, broadened to ``fwhm`` (deg 2theta). Raises
    ValueError with a clear message if the CIF is unusable."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    wk, known = _load_wk()
    cell, sym, atoms = _parse_cif(text, known)
    if cell[0] is None:
        raise ValueError("The CIF has no unit-cell parameters.")
    if not sym:
        raise ValueError(
            "The CIF has no explicit symmetry operations. Export the structure "
            "from COD or AMCSD; a bare space-group number or a BGMN .str "
            "(Wyckoff-only) is not supported yet.")
    if not atoms:
        raise ValueError("The CIF has no atom sites with recognised elements.")

    full = _expand(atoms, sym)
    wavelength = float(goniometer.wavelength) * 10.0  # nm -> Angstrom
    sticks = _stick(cell, full, wk, wavelength, tt_lo=tt_lo, tt_hi=tt_hi)
    if not sticks:
        raise ValueError("The structure produced no reflections in range.")

    x = np.arange(tt_lo, tt_hi, 0.01)
    y = np.zeros_like(x)
    sigma = fwhm / 2.355
    for tt, inten in sticks:
        y += inten * np.exp(-0.5 * ((x - tt) / sigma) ** 2)
    if y.max() > 0:
        y = 100.0 * y / y.max()
    if name is None:
        name = os.path.splitext(os.path.basename(path))[0]
    return reference_from_arrays(x, y, name)
