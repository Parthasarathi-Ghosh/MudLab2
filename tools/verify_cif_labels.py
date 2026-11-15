#!/usr/bin/env python
"""Durable harness for three CIF-reading bugs found while testing the curated
structure collection (2026-11-15), run head-less.

1. The non-clay reference builder read water oxygens labelled ``Wat1`` as W -
   TUNGSTEN (Z = 74) - so vermiculite's and sepiolite's water scattered as a
   heavy metal; ``H2O`` labels read as hydrogen.
2. The clay-component importer dropped those water sites, and deuterium sites
   (``D1``, ``DZW1*1``), WITHOUT A WORD - an imported vermiculite lost its
   interlayer water. Unrecognised sites are now recorded and reported.
3. The clay importer took the first symmetry tag of a loop as the operation
   column, which in COD's common layout is an ID (`_space_group_symop_id`,
   `_symmetry_equiv_pos_site_id`): no operations were read and the structure
   was silently taken as P1.

Everything here is synthetic, so it runs anywhere (CI included). A last group
re-reads real files: three from the shipped structure collection (in the repo,
so they always run) and two from the user's AMCSD corpus, which is skipped -
not failed - on a machine that does not have it.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_cif_labels.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.file_parsers import cif_component as cc  # noqa: E402
from mudlab.file_parsers.cif_labels import label_element  # noqa: E402
from mudlab.models.goniometer import Goniometer  # noqa: E402
from mudlab.nonclay import structure as nst  # noqa: E402

results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


_WK, _KNOWN = nst._load_wk()

CORPUS = os.environ.get("MUDLAB_CIF_CORPUS",
                        r"C:\GitHub\CIF builder\Clay structures\RRUFF AMCSD")
# The shipped collection (structures/Clays, structures/Non-clays).
CURATED = os.environ.get("MUDLAB_CURATED_STRUCTURES",
                         os.path.join(_REPO, "structures"))


def curated(name):
    """`name` wherever it sits under the collection (it is split by kind)."""
    for folder, _dirs, files in os.walk(CURATED):
        if name in files:
            return os.path.join(folder, name)
    return os.path.join(CURATED, name)


def cif(sites, symmetry_loop=None, cell=(5.2, 9.0, 10.0, 90.0, 100.0, 90.0),
        type_symbols=False):
    """A minimal CIF: `sites` are (label, type, x, y, z); `symmetry_loop` is a
    list of lines for a symmetry loop, or None for none at all."""
    a, b, c, al, be, ga = cell
    lines = ["data_synthetic", "_chemical_name_mineral 'Synthetic'",
             "_cell_length_a %.4f" % a, "_cell_length_b %.4f" % b,
             "_cell_length_c %.4f" % c, "_cell_angle_alpha %.2f" % al,
             "_cell_angle_beta %.2f" % be, "_cell_angle_gamma %.2f" % ga]
    if symmetry_loop:
        lines += symmetry_loop
    lines += ["loop_", "_atom_site_label"]
    if type_symbols:
        lines.append("_atom_site_type_symbol")
    lines += ["_atom_site_fract_x", "_atom_site_fract_y", "_atom_site_fract_z",
              "_atom_site_occupancy"]
    for label, typ, x, y, z in sites:
        row = [label] + ([typ] if type_symbols else []) + ["%.4f" % x, "%.4f" % y, "%.4f" % z, "1.0"]
        lines.append(" ".join(row))
    return "\n".join(lines) + "\n"


P1 = ["loop_", "_symmetry_equiv_pos_as_xyz", "'x, y, z'"]

# A 2:1 layer with interlayer water labelled the AMCSD way.
LAYER = [("O1", "O", 0.00, 0.00, 0.00), ("Si1", "Si", 0.05, 0.11, 0.06),
         ("O2", "O", 0.10, 0.22, 0.23), ("Oh1", "O", 0.15, 0.33, 0.24),
         ("Mg1", "Mg", 0.20, 0.44, 0.34), ("Oh2", "O", 0.25, 0.55, 0.44),
         ("O3", "O", 0.30, 0.66, 0.45), ("Si2", "Si", 0.35, 0.77, 0.61),
         ("O4", "O", 0.40, 0.88, 0.67)]


# ----------------------------------------------------------------------
def check_label_rule():
    cases = {"Wat1": "O", "WAT2": "O", "wat": "O", "H2O3": "O", "h2o": "O",
             "D1": "H", "DZW1*1": "H", "d2": "H", "D": "H",
             "W1": None, "Dy1": None, "Ds": None, "Db1": None, "Si1": None,
             "O-H": None, "OW1": None, "Ca1": None, "": None, None: None}
    bad = {k: (label_element(k), v) for k, v in cases.items() if label_element(k) != v}
    check("label rule: water -> O, deuterium -> H, real elements untouched %s"
          % (bad or ""), not bad)


def check_nonclay_elements():
    want = {"Wat10": "O", "Wat1": "O", "H2O": "O", "D1": "H", "DZW1*1": "H",
            "W1": "W", "Dy1": "Dy", "OW1": "O", "Ca1": "Ca", "O-H": "O"}
    got = {k: nst._element_of(k, _KNOWN) for k in want}
    check("non-clay reader: 'Wat10' is oxygen, not tungsten", got["Wat10"] == "O")
    check("non-clay reader: 'H2O' is oxygen, not hydrogen", got["H2O"] == "O")
    check("non-clay reader: deuterium labels are hydrogen", got["D1"] == "H" and got["DZW1*1"] == "H")
    check("non-clay reader: a tungstate's 'W1' is still tungsten, 'Dy1' still Dy",
          got["W1"] == "W" and got["Dy1"] == "Dy")
    check("non-clay reader: ordinary labels unchanged", all(got[k] == want[k] for k in ("OW1", "Ca1", "O-H")))

    # The pattern itself: a water site labelled 'Wat1' must scatter exactly as
    # one labelled 'O9' - and visibly unlike one labelled as tungsten.
    gon = Goniometer()

    def refl(label):
        text = cif(LAYER + [(label, "O", 0.0, 0.5, 0.84)], symmetry_loop=P1)
        r = nst.reflections_from_cif_text(text, gon)
        return r[0] if isinstance(r, tuple) else r
    as_wat, as_o, as_w = refl("Wat1"), refl("O9"), refl("W9")
    same = len(as_wat) == len(as_o) and all(
        abs(a[0] - b[0]) < 1e-12 and abs(a[1] - b[1]) < 1e-9 for a, b in zip(as_wat, as_o))
    check("non-clay pattern: 'Wat1' water == 'O9' oxygen, reflection for reflection", same)
    differs = any(abs(a[1] - b[1]) > 1e-3 for a, b in zip(as_wat, as_w))
    check("non-clay pattern: ...and != the same site read as tungsten (the old result)", differs)


def check_clay_element_rule():
    want = {"Wat1": "O", "H2O1": "O", "D1": "H", "SiT1": "Si", "Fe2+M": "Fe",
            "O-H3": "O", "OW1": "O", "AlM2": "Al", "Ca1": "Ca", "Cl1": "Cl",
            # must NOT regress: ammonium stays nitrogen (not nihonium), a
            # hydroxyl hydrogen labelled HO1 stays hydrogen (not holmium)
            "NH4": "N", "HO1": "H",
            # unsupported real elements are UNRECOGNISED, not their first letter
            "Pb1": None, "Ce1": None, "Sn1": None, "Sb1": None, "Dy1": None,
            "W1": None, "Xx1": None}
    got = {k: cc.element_of(k) for k in want}
    wrong = {k: (got[k], v) for k, v in want.items() if got[k] != v}
    check("clay importer element rule (Pb1 no longer phosphorus, NH4 still N) %s"
          % (wrong or ""), not wrong)


def check_clay_water_and_deuterium():
    text = cif(LAYER + [("Wat1", "?", 0.0, 0.5, 0.84), ("D1", "?", 0.1, 0.5, 0.88)],
               symmetry_loop=P1)
    st = cc.parse_cif(text)
    labels = {s.label: s.element for s in st.sites}
    check("clay importer: a 'Wat1' site is kept, as oxygen", labels.get("Wat1") == "O")
    check("clay importer: a 'D1' site is kept, as hydrogen", labels.get("D1") == "H")
    check("clay importer: nothing skipped when every label is understood", getattr(st, "skipped", None) == [])


def check_clay_skipped_reported():
    text = cif(LAYER + [("Pb1", "Pb", 0.0, 0.5, 0.84), ("Xx2", "Xx", 0.1, 0.5, 0.86)],
               symmetry_loop=P1)
    st = cc.parse_cif(text)
    check("clay importer: unrecognised sites are recorded, not silently dropped",
          getattr(st, "skipped", None) == ["Pb1", "Xx2"])
    _rows, rep = cc.project(st)
    warned = [w for w in rep.warnings if "left out" in w]
    check("clay importer: the review shows a warning naming them",
          len(warned) == 1 and "Pb1" in warned[0] and "Xx2" in warned[0])
    try:
        cc.parse_cif(cif([("Pb1", "Pb", 0, 0, 0)], symmetry_loop=P1))
        raised = ""
    except ValueError as e:
        raised = str(e)
    check("clay importer: a file of only unrecognised sites says which",
          raised.startswith("CIF has no atom sites") and "Pb1" in raised)


def check_symmetry_columns():
    ops = ["'x, y, z'", "'-x, -y, -z'"]
    layouts = {
        "_space_group_symop_id + _operation_xyz":
            ["loop_", "_space_group_symop_id", "_space_group_symop_operation_xyz",
             "1 " + ops[0], "2 " + ops[1]],
        "_symmetry_equiv_pos_site_id + _as_xyz":
            ["loop_", "_symmetry_equiv_pos_site_id", "_symmetry_equiv_pos_as_xyz",
             "1 " + ops[0], "2 " + ops[1]],
        "_as_xyz alone":
            ["loop_", "_symmetry_equiv_pos_as_xyz"] + ops,
        "_operation_xyz alone":
            ["loop_", "_space_group_symop_operation_xyz"] + ops,
    }
    for name, loop in layouts.items():
        st = cc.parse_cif(cif(LAYER, symmetry_loop=loop))
        check("clay importer: symmetry read from %s (2 operations)" % name,
              len(st.symmetry) == 2 and st.symmetry[1] == ["-x", "-y", "-z"])
    st = cc.parse_cif(cif(LAYER, symmetry_loop=layouts["_space_group_symop_id + _operation_xyz"]))
    _rows, rep = cc.project(st)
    check("clay importer: no false 'read as P1' warning when operations are listed",
          not any("read as P1" in w for w in rep.warnings))
    st = cc.parse_cif(cif(LAYER, symmetry_loop=None))
    _rows, rep = cc.project(st)
    check("clay importer: a file with NO operations still warns it was read as P1",
          any("read as P1" in w for w in rep.warnings))


def check_real_files():
    """The curated files that exposed the bugs, when present on this machine."""
    targets = [
        ("vermiculite (Wat)", os.path.join(CORPUS, "Vermiculite__0020497.cif")),
        ("sepiolite (Wat)", os.path.join(CORPUS, "Sepiolite__0004269.cif")),
        ("gypsum (symmetry ids)", curated("Gypsum__COD-2300259.cif")),
        ("jarosite (symmetry ids)", curated("Jarosite__COD-1557931.cif")),
        ("laumontite (deuterium)", curated("Laumontite__COD-9005147.cif")),
    ]
    # The collection ships in the repo, so its files must be there; only the
    # corpus may be absent.
    for name, path in targets[2:]:
        check("shipped collection holds the %s file" % name, os.path.isfile(path))
    present = [(n, p) for n, p in targets if os.path.isfile(p)]
    if not present:
        print("Real files not found on this machine: real-file checks skipped.")
        return
    for name, path in present:
        text = open(path, encoding="utf-8", errors="replace").read()
        _cell, sym, atoms = nst._parse_cif(text, _KNOWN)
        st = cc.parse_cif(text)
        no_w = all(a[0] != "W" for a in atoms)
        check("real %s: no tungsten in the non-clay reading; clay reader skips nothing"
              % name, no_w and getattr(st, "skipped", None) == [])
        if "symmetry ids" in name:
            check("real %s: clay reader finds the same %d operations as the non-clay reader"
                  % (name, len(sym)), len(st.symmetry) == len(sym) > 1)


def main():
    check_label_rule()
    check_nonclay_elements()
    check_clay_element_rule()
    check_clay_water_and_deuterium()
    check_clay_skipped_reported()
    check_symmetry_columns()
    check_real_files()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- CIF label / symmetry verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
