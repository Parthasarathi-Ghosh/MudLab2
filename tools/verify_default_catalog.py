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


# The real calc units (calculations/specimen.py): theta in RADIANS, wavelength
# in nm (d-spacings are nm). Getting these wrong shifts every peak, so the
# peak-position checks below use them faithfully.
_WAVELENGTH_NM = 0.15406


def _pattern(phase, lo=2.0, hi=40.0, n=8000):
    """(2theta-deg grid, intensity) for the phase, in the real calc units."""
    two_theta = np.linspace(lo, hi, n)
    theta = np.radians(two_theta / 2.0)
    stl = 2.0 * np.sin(theta) / _WAVELENGTH_NM
    return two_theta, phase.get_intensity(theta, stl, 2.3, 2.3, 0.0)


def _computes(phase) -> bool:
    _tt, intensity = _pattern(phase, n=400)
    return bool(np.any(intensity > 0)) and float(np.max(intensity)) > 0


def _bragg_2theta(d_angstrom: float) -> float:
    """The 001 basal 2theta (deg) for a d-spacing in Angstrom, Cu Ka (1.5406 A)."""
    return 2.0 * np.degrees(np.arcsin(1.5406 / (2.0 * d_angstrom)))


def _basal_peak(phase, expect_2theta: float, tol: float = 0.5):
    """The prominent peak nearest `expect_2theta` (deg), or None if none within
    `tol` - the basal (001) reflection rides on the low-angle rise, so a
    prominence-based finder is used."""
    from scipy.signal import find_peaks

    two_theta, intensity = _pattern(phase)
    idx, _ = find_peaks(intensity, prominence=0.04 * float(np.max(intensity)))
    if len(idx) == 0:
        return None
    peaks = two_theta[idx]
    nearest = float(peaks[np.argmin(np.abs(peaks - expect_2theta))])
    return nearest if abs(nearest - expect_2theta) < tol else None


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
    check("4 is_modeled accepts the engine's RGbounds (R0 G1-6, R1 G2-4, R2 G2-3, R3 G2)",
          all(is_modeled(0, g) for g in range(1, 7))
          and is_modeled(1, 2) and is_modeled(1, 4)
          and is_modeled(2, 2) and is_modeled(2, 3) and is_modeled(3, 2))
    check("4 is_modeled rejects unsupported stacking (R1G5, R2G4, R3G3)",
          not is_modeled(1, 5) and not is_modeled(2, 4) and not is_modeled(3, 3))

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

    # 7. The higher-order tail: multi-state smectites + multi-clay stacks.
    check("7 the tail families are listed",
          all(n in entries for n in
              ("Di-Smectite (2S) R0 Ca", "Di-Smectite (3S) R0 Ca",
               "Illite-Smectite (2S) R0 Ca",
               "Illite-Chlorite-Smectite R0 Ca",
               "Kaolinite-Chlorite-Smectite (3S) R0 Ca")))
    # component count = number of coded parts (fixed clays + smectite states)
    for name, g in [("Di-Smectite (2S) R0 Ca", 2), ("Di-Smectite (3S) R0 Ca", 3),
                    ("Illite-Smectite (2S) R0 Ca", 3),
                    ("Illite-Chlorite-Smectite R0 Ca", 3),
                    ("Kaolinite-Chlorite-Smectite (3S) R0 Ca", 5)]:
        ps = build_catalog_entry_by_name(name)
        ok = (len(ps) == 3 and all(len(p.components) == g for p in ps)
              and all(_computes(p) for p in ps))
        # every treated component is linked (to the AD directly, or up the
        # AD/EG/350 chain for a state shared across treatments) and reads its
        # layer atoms through that link.
        linked = all(c.linked_with is not None and c.is_inherited("layer_atoms")
                     for p in ps[1:] for c in p.components)
        check("7 %s -> G%d, all linked + compute" % (name, g), ok and linked)

    # 8. Full sweep: EVERY catalog entry builds and every phase computes.
    bad = []
    for name in entries:
        ps = build_catalog_entry_by_name(name)
        if not ps or not all(_computes(p) and p.is_valid for p in ps):
            bad.append(name)
    check("8 every catalog entry builds valid, computable phases", not bad)
    if bad:
        print("    failed to build/compute:", bad[:6])

    # 9. Peak positions: the calc puts each clay's basal (001) reflection at the
    #    2theta its d001 predicts, and the smectite Ca-AD -> Ca-EG -> Ca-350
    #    series shows the diagnostic glycol expansion / heat collapse. This
    #    guards CORRECTNESS (right peaks), not just non-blankness.
    unplaced = []
    for name, d_a in [("Kaolinite", 7.16), ("Illite", 9.98), ("Chlorite", 14.2),
                      ("Talc", 9.40), ("Serpentine", 7.26)]:
        phase = build_catalog_entry_by_name(name)[0]
        if _basal_peak(phase, _bragg_2theta(d_a)) is None:
            unplaced.append(name)
    check("9 each single-layer clay's 001 basal reflection is at the known 2theta",
          not unplaced)
    if unplaced:
        print("    001 not found for:", unplaced)

    ad, eg, ht = build_catalog_entry_by_name("Di-Smectite R0 Ca")
    t_ad = _basal_peak(ad, _bragg_2theta(15.0), tol=0.6)     # 2 water, ~15 A
    t_eg = _basal_peak(eg, _bragg_2theta(16.86), tol=0.6)    # 2 glycol, ~16.9 A
    t_ht = _basal_peak(ht, _bragg_2theta(9.6), tol=0.6)      # heated, ~9.6 A
    check("9 the smectite 001 is found in each of AD / EG / 350",
          None not in (t_ad, t_eg, t_ht))
    check("9 glycol expands + heat collapses (EG 2theta < AD < 350)",
          None not in (t_ad, t_eg, t_ht) and t_eg < t_ad < t_ht)
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
