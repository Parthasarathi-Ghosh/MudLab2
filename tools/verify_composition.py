#!/usr/bin/env python
"""Durable harness for the mixture composition summary, head-less.

The Composition button reports each specimen's oxide weight-% composition
(old Mixture.get_composition_matrix). This checks:

  1. analytics: every specimen column normalises to 100 wt% (or is all-zero
     when it has no convertible atoms); the oxide rows follow the conversion
     table's order; a raw-pattern phase / empty cell contributes nothing.
  2. conversion table: the seven expected oxides load in file order.
  3. treated variants (AD / EG / heated of one clay) share a composition -
     glycolation / heating changes the structure, not the chemistry.
  4. CSV: composition_to_csv round-trips the values with a specimen header.
  5. dialog: it builds, fills the table (oxides x specimens), and its CSV copy
     matches the analytics.

Run head-less from the repo root:

    ./python/python.exe tools/verify_composition.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable sample project.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.calculations.composition import (  # noqa: E402
    composition_to_csv, load_conversion_table, mixture_composition,
)
from mudlab.composition_dialog import CompositionDialog  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

FIXTURE = os.path.join(_REPO, "tools", "sample_projects", "Dh2040A 14Jul26 r1.mud")

_app = QApplication.instance() or QApplication([])
results = []


def check(label, ok):
    results.append((label, bool(ok)))


def run():
    # 2. Conversion table.
    conv = load_conversion_table()
    names = [v[0] for v in conv.values()]
    check("2 conversion table loads the seven oxides in order",
          names == ["SiO2", "Al2O3", "Fe2O3", "CaO", "MgO", "Na2O", "K2O"])

    project = load_mud(FIXTURE)
    mix = project.mixtures[0]
    specimen_names, oxide_rows = mixture_composition(mix)

    # A raw-pattern accessory (no structure, type != "Phase") must be excluded:
    # the clay-only composition is unchanged and its fraction is not in the 100%.
    import numpy as np
    from mudlab.models.raw_pattern_phase import RawPatternPhase
    mix_raw = load_mud(FIXTURE).mixtures[0]
    raw = RawPatternPhase(name="Accessory")
    raw.set_raw_pattern(np.linspace(5, 70, 50), np.ones(50))
    slot = mix_raw.add_phase_slot("Acc")
    for i in range(mix_raw.n):
        mix_raw.set_phase_at(i, slot, raw)
    _rn, oxide_rows_raw = mixture_composition(mix_raw)
    check("a raw accessory is excluded (clay-only composition unchanged)",
          all(abs(a - b) < 1e-9
              for (_o1, p1), (_o2, p2) in zip(oxide_rows_raw, oxide_rows)
              for a, b in zip(p1, p2)))

    # 1. Every column normalises to 100 (or all-zero).
    n_spec = len(specimen_names)
    col_sums = [sum(pcts[j] for _o, pcts in oxide_rows) for j in range(n_spec)]
    check("1 each specimen column sums to 100 wt% (or 0)",
          all(abs(s - 100.0) < 0.5 or abs(s) < 1e-9 for s in col_sums))
    check("1 oxide rows follow the conversion order",
          [o for o, _ in oxide_rows] == names)
    check("1 at least one specimen has a real (non-zero) composition",
          any(s > 0 for s in col_sums))

    # 3. Treated variants of one clay share a composition (structure differs,
    #    chemistry does not) - this fixture is AD / EG / 400 of one sample.
    if n_spec >= 2:
        first = [pcts[0] for _o, pcts in oxide_rows]
        same = all(
            abs(pcts[0] - pcts[j]) < 0.05
            for _o, pcts in oxide_rows for j in range(1, n_spec)
        )
        check("3 the treated variants share the same composition", same and any(first))
    else:
        check("3 the treated variants share the same composition", True)

    # 4. CSV.
    csv_text = composition_to_csv(specimen_names, oxide_rows)
    lines = [ln for ln in csv_text.splitlines() if ln]
    check("4 CSV has a header + one line per oxide",
          len(lines) == len(oxide_rows) + 1 and lines[0].startswith(","))
    check("4 CSV header carries the specimen names",
          all(nm in lines[0] for nm in specimen_names))

    # 5. Dialog.
    dialog = CompositionDialog(mix)
    table = dialog.ui.tbl_composition
    check("5 the dialog table is oxides x specimens",
          table.rowCount() == len(oxide_rows) and table.columnCount() == n_spec)
    check("5 a known cell renders to one decimal",
          table.item(0, 0) is not None
          and table.item(0, 0).text() == "%.1f" % oxide_rows[0][1][0])
    check("5 the dialog CSV matches the analytics", dialog._csv_text() == csv_text)
    dialog.deleteLater()

    # 6. Bulk composition (path-2 (c)): non-clay phases contribute, ADDITIVELY
    #    (the clay-only view + the XRF mass balance are untouched).
    from mudlab.calculations.composition import bulk_composition, mixture_has_nonclay
    from mudlab.models.nonclay_phase import NonClayPhase
    mixb = load_mud(FIXTURE).mixtures[0]
    check("6 mixture_has_nonclay is False before adding one", not mixture_has_nonclay(mixb))
    clay_names, clay_rows = mixture_composition(mixb)

    quartz = NonClayPhase(name="Quartz")
    quartz.set_oxides({"SiO2": 100.0})
    quartz.set_raw_pattern(np.linspace(5, 70, 50), np.ones(50))  # -> is_valid
    slot = mixb.add_phase_slot("Qz", fraction=0.5)
    for i in range(mixb.n):
        mixb.set_phase_at(i, slot, quartz)
    check("6 mixture_has_nonclay is True after adding one", mixture_has_nonclay(mixb))

    # ADDITIVE: clay-only composition still excludes the non-clay (unchanged).
    _cn2, clay_rows2 = mixture_composition(mixb)
    check("6 clay-only composition excludes the non-clay (additive, unchanged)",
          all(abs(a - b) < 1e-9
              for (_o1, p1), (_o2, p2) in zip(clay_rows2, clay_rows)
              for a, b in zip(p1, p2)))

    bulk_names, bulk_rows = bulk_composition(mixb)
    bulk_sums = [sum(pcts[j] for _o, pcts in bulk_rows) for j in range(len(bulk_names))]
    check("6 bulk columns normalise to 100 wt% (or 0)",
          all(abs(s - 100.0) < 0.5 or abs(s) < 1e-9 for s in bulk_sums))

    def _sio2(rows):
        return next(p for o, p in rows if o == "SiO2")
    check("6 bulk SiO2 exceeds clay-only (quartz added to the bulk)",
          all(b >= c - 1e-6 for b, c in zip(_sio2(bulk_rows), _sio2(clay_rows2)))
          and any(b > c + 1e-3 for b, c in zip(_sio2(bulk_rows), _sio2(clay_rows2))))

    # Dialog: checkbox enabled with a non-clay, toggling switches the view.
    dlg_b = CompositionDialog(mixb)
    check("6 dialog: bulk checkbox enabled when a non-clay is present",
          dlg_b.ui.chk_bulk.isEnabled())
    clay_csv = dlg_b._csv_text()
    dlg_b.ui.chk_bulk.setChecked(True)
    check("6 dialog: toggling bulk changes the reported composition",
          dlg_b._csv_text() != clay_csv)
    dlg_b.deleteLater()
    dlg_c = CompositionDialog(load_mud(FIXTURE).mixtures[0])
    check("6 dialog: bulk checkbox disabled without a non-clay",
          not dlg_c.ui.chk_bulk.isEnabled())
    dlg_c.deleteLater()

    # 6b. AUDIT: an oxide OUTSIDE the reporting set (only reachable from a
    #     hand-edited .mud - the grid offers just the seven) must be ignored, not
    #     counted in the phase's own total: it used to shrink the phase's share
    #     of its own fraction (a {SiO2 50, TiO2 50} quartz contributed half).
    def _bulk_with(oxides):
        m = load_mud(FIXTURE).mixtures[0]
        nc = NonClayPhase(name="NC")
        nc.set_oxides(oxides)
        nc.set_raw_pattern(np.linspace(5, 70, 50), np.ones(50))
        s = m.add_phase_slot("NC", fraction=0.5)
        for i in range(m.n):
            m.set_phase_at(i, s, nc)
        return bulk_composition(m)[1]

    with_ti, without_ti = _bulk_with({"SiO2": 50.0, "TiO2": 50.0}), _bulk_with({"SiO2": 50.0})
    check("6b a non-reporting oxide is ignored, not counted against the phase",
          all(abs(a - b) < 1e-9
              for (_o1, p1), (_o2, p2) in zip(with_ti, without_ti)
              for a, b in zip(p1, p2)))
    check("6b relative oxide levels are what matter (50 == 100)",
          all(abs(a - b) < 1e-9
              for (_o1, p1), (_o2, p2) in zip(without_ti, _bulk_with({"SiO2": 100.0}))
              for a, b in zip(p1, p2)))

    # 7. Formula parser (path-2 (f)): a chemical formula -> reporting oxides.
    from mudlab.calculations.composition import parse_formula
    ab = parse_formula("NaAlSi3O8")  # albite
    check("7 albite -> Na2O 11.8 / Al2O3 19.4 / SiO2 68.7",
          abs(ab.get("SiO2", 0) - 68.7) < 0.5 and abs(ab.get("Al2O3", 0) - 19.4) < 0.5
          and abs(ab.get("Na2O", 0) - 11.8) < 0.5)
    check("7 calcite CaCO3 -> CaO 100 (C/O dropped)",
          abs(parse_formula("CaCO3").get("CaO", 0) - 100.0) < 0.5)
    dol = parse_formula("CaMg(CO3)2")  # dolomite: parentheses
    check("7 dolomite parentheses -> CaO 58.2 + MgO 41.8",
          abs(dol.get("CaO", 0) - 58.2) < 1.0 and abs(dol.get("MgO", 0) - 41.8) < 1.0)
    check("7 gypsum CaSO4.2H2O -> CaO 100 (S/H dropped, hydrate ok)",
          abs(parse_formula("CaSO4.2H2O").get("CaO", 0) - 100.0) < 0.5)
    check("7 quartz SiO2 -> SiO2 100", abs(parse_formula("SiO2").get("SiO2", 0) - 100.0) < 0.5)
    check("7 no reportable oxide -> empty (TiO2)", parse_formula("TiO2") == {})
    check("7 gibberish -> empty", parse_formula("zz9") == {})

    # 7b. AUDIT: segment ("oxide") notation. A '.' between digits is read as a
    #     decimal point, so "K2O.Al2O3.6SiO2" silently lost the 6x on the silica
    #     (SiO2 23.4 instead of 64.8). '·'/'*' are unambiguous separators, a
    #     leading coefficient multiplies ONLY its own segment, and
    #     formula_dot_is_ambiguous flags the ASCII cases where the reading
    #     actually changes the answer (the oxide grid then asks).
    from mudlab.calculations.composition import formula_dot_is_ambiguous
    ort = parse_formula("KAlSi3O8")                       # orthoclase
    for written in ("K2O·Al2O3·6SiO2", "K2O*Al2O3*6SiO2"):
        seg = parse_formula(written)
        check("7b %s == KAlSi3O8" % written,
              all(abs(seg.get(o, 0) - ort.get(o, 0)) < 0.5
                  for o in ("SiO2", "Al2O3", "K2O")))
    seg_dot = parse_formula("K2O.Al2O3.6SiO2", dot_as_separator=True)
    check("7b dot_as_separator reads the same as '·'",
          all(abs(seg_dot.get(o, 0) - ort.get(o, 0)) < 0.5
              for o in ("SiO2", "Al2O3", "K2O")))
    c3a = parse_formula("3CaO·Al2O3")                # tricalcium aluminate
    check("7b leading coefficient 3CaO·Al2O3 -> CaO 62.3 / Al2O3 37.7",
          abs(c3a.get("CaO", 0) - 62.3) < 1.0 and abs(c3a.get("Al2O3", 0) - 37.7) < 1.0)
    dio = parse_formula("CaO·MgO·2SiO2")        # diopside
    check("7b a middle segment's multiplier stays local (CaO·MgO·2SiO2)",
          all(abs(dio.get(o, 0) - parse_formula("CaMgSi2O6").get(o, 0)) < 0.5
              for o in ("SiO2", "CaO", "MgO")))
    check("7b ambiguity flagged only when it changes the oxides",
          formula_dot_is_ambiguous("K2O.Al2O3.6SiO2")
          and formula_dot_is_ambiguous("Fe0.5Mg0.5SiO3")
          and not formula_dot_is_ambiguous("CaSO4.2H2O")      # water is dropped
          and not formula_dot_is_ambiguous("NaAlSi3O8")       # no dot at all
          and not formula_dot_is_ambiguous("CaSO4·2H2O"))
    pl = parse_formula("Na0.5Ca0.5Al1.5Si2.5O8")          # decimal subscripts
    check("7b decimal subscripts still parse (plagioclase An50)",
          abs(pl.get("SiO2", 0) - 55.6) < 0.5 and abs(pl.get("CaO", 0) - 10.4) < 0.5)

    # 1 (cont.) an empty phase cell / raw phase contributes nothing: emptying a
    # cell must not raise and must keep the column normalised or zero.
    if mix.n and mix.m:
        mix.set_phase_at(0, 0, None)
        _n2, rows2 = mixture_composition(mix)
        s0 = sum(pcts[0] for _o, pcts in rows2)
        check("1 emptying a cell recomputes cleanly (col still 100 or 0)",
              abs(s0 - 100.0) < 0.5 or abs(s0) < 1e-9)
    else:
        check("1 emptying a cell recomputes cleanly (col still 100 or 0)", True)
    return None


def main():
    print("=" * 72)
    print("Mixture composition summary")
    print("=" * 72)
    if not os.path.isfile(FIXTURE):
        print("No sample project found; skipping (exit 2).")
        return 2
    rc = run()
    if rc == 2:
        return 2
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("Composition harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
