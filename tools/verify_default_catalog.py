#!/usr/bin/env python
"""Durable harness for the default-phase catalog builder (Step 3).

`build_catalog_entry` assembles named default phases from the bundled `.cmp`
components (old generate_default_phases recipe): a component code selects the
components, and per-phase `based_on` / per-component `linked_with` names wire
the Ca-AD -> Ca-EG -> Ca-350 inheritance chains. This checks:

  1. listing: only modeled entries (R0 / R1G2) are offered; the expected clays
     are present.
  2. single-layer: each builds one valid phase that computes a NON-blank
     pattern.
  3. expandable chains: Di-Smectite Ca builds AD/EG/350; EG + 350 are based_on
     AD, their component is linked to AD's (inheriting its layer atoms), each
     phase is valid + computes, and the three states have the RIGHT distinct
     d001 (AD 1.50 / EG 1.686 / 350 0.96 nm) - i.e. the interlayer differs while
     the layer is shared.
  4. gate: is_modeled accepts R0 (any G) and R1G2, rejects R1G3 / R2 / R3.

Run head-less from the repo root:

    ./python/python.exe tools/verify_default_catalog.py

Exit codes: 0 = all pass, 1 = a regression, 2 = the catalog is unavailable.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402

from mudlab.file_parsers.default_catalog import (  # noqa: E402
    build_catalog_entry_by_name, default_catalog_entries, is_modeled,
)

results = []


def check(label, ok):
    results.append((label, bool(ok)))


def _computes(phase) -> bool:
    rng = np.linspace(1, 40, 400)
    stl = 2 * np.sin(np.radians(rng / 2)) / 1.5406
    intensity = phase.get_intensity(rng, stl, 0.5, 0.5, 0.0)
    return bool(np.any(intensity > 0)) and float(np.max(intensity)) > 0


def _d001(phase, component_index=0) -> float:
    return phase.components[component_index].d001


def run():
    entries = dict(default_catalog_entries())

    # 1. Listing.
    check("1 the catalog lists modeled entries",
          len(entries) >= 11)
    check("1 the single-layer clays are all present",
          all(n in entries for n in
              ("Kaolinite", "Illite", "Serpentine", "Talc", "Chlorite",
               "Margarite", "Leucophyllite", "Paragonite")))
    check("1 the expandable families are present",
          all(n in entries for n in
              ("Di-Smectite R0 Ca", "Tri-Smectite R0 Ca", "Di-Vermiculite R0 Ca")))

    # 2. Single-layer entries build one computable phase.
    ok_single = True
    for name in ("Kaolinite", "Illite", "Chlorite", "Talc"):
        phases = build_catalog_entry_by_name(name)
        if not (len(phases) == 1 and phases[0].is_valid and _computes(phases[0])):
            ok_single = False
    check("2 each single-layer entry builds one valid, computable phase", ok_single)

    # 3. Expandable chain: Di-Smectite Ca -> AD / EG / 350.
    smectite = build_catalog_entry_by_name("Di-Smectite R0 Ca")
    check("3 the expandable entry builds three phases (AD/EG/350)",
          len(smectite) == 3)
    ad, eg, ht = smectite
    check("3 AD is standalone; EG + 350 are based_on AD",
          ad.based_on is None and eg.based_on is ad and ht.based_on is ad)
    check("3 the treated components are linked to AD's component",
          eg.components[0].linked_with is ad.components[0]
          and ht.components[0].linked_with is ad.components[0])
    check("3 the treated component inherits AD's layer atoms",
          eg.components[0].is_inherited("layer_atoms"))
    check("3 all three states compute a non-blank pattern",
          all(_computes(p) for p in smectite))
    d_ad, d_eg, d_ht = _d001(ad), _d001(eg), _d001(ht)
    check("3 the three states have the right distinct d001 (AD<EG, 350<AD)",
          abs(d_ad - 1.50) < 0.02 and abs(d_eg - 1.686) < 0.02
          and abs(d_ht - 0.96) < 0.02)
    check("3 the treated phases inherit the parent's sigma* + colour",
          eg.inherit_sigma_star and eg.inherit_display_color
          and eg.inherit_CSDS_distribution)

    # 4. The modeled-stacking gate.
    check("4 is_modeled accepts R0 (any G) and R1G2",
          is_modeled(0, 1) and is_modeled(0, 4) and is_modeled(1, 2))
    check("4 is_modeled rejects R1G3 / R2 / R3",
          not is_modeled(1, 3) and not is_modeled(2, 2) and not is_modeled(3, 2))

    # 5. Interstratified (mixed-layer) families: Illite-Smectite at R0 and R1G2.
    check("5 the interstratified families are listed at R0 and R1",
          all(n in entries for n in
              ("Illite-Smectite R0 Ca", "Illite-Smectite R1 Ca",
               "Kaolinite-Smectite R0 Ca", "Chlorite-Smectite R1 Ca")))
    for label, name, R in [("R0", "Illite-Smectite R0 Ca", 0),
                           ("R1G2", "Illite-Smectite R1 Ca", 1)]:
        phases = build_catalog_entry_by_name(name)
        ad, eg, ht = phases
        # G = 2 (a fixed illite component + a smectite component)
        two_comp = all(len(p.components) == 2 for p in phases)
        # both components of a treated phase are linked to the AD's components
        fixed_linked = (eg.components[0].linked_with is ad.components[0])
        smectite_linked = (eg.components[1].linked_with is ad.components[1])
        # the treated phase reads the AD's stacking ratio through inheritance
        prob_inherited = (
            eg.probabilities.based_on_probs is ad.probabilities
            and eg.probabilities.get_distribution_array()[0]
            == ad.probabilities.get_distribution_array()[0])
        computes = all(_computes(p) for p in phases)
        check("5 %s builds G2 AD/EG/350 with both components linked" % label,
              len(phases) == 3 and two_comp and fixed_linked and smectite_linked)
        check("5 %s treated phases inherit the AD's stacking ratio" % label,
              prob_inherited)
        check("5 %s all three states compute a non-blank pattern" % label,
              computes)

    # 6. Probability inheritance actually reads through (change AD -> child follows).
    phases = build_catalog_entry_by_name("Illite-Smectite R0 Ca")
    ad, eg, _ht = phases
    before = eg.probabilities.get_distribution_array()[0]
    ad.probabilities.set_f(0, 0.33)  # move the AD's illite fraction
    after = eg.probabilities.get_distribution_array()[0]
    check("6 editing the AD's ratio flows through to the treated phase",
          abs(after - before) > 1e-9
          and abs(after - ad.probabilities.get_distribution_array()[0]) < 1e-9)
    return None


def main():
    print("=" * 72)
    print("Default-phase catalog builder")
    print("=" * 72)
    if not default_catalog_entries():
        print("Catalog unavailable; skipping (exit 2).")
        return 2
    rc = run()
    if rc == 2:
        return 2
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("Default-catalog harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
