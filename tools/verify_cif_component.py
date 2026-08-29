#!/usr/bin/env python
"""Importing a clay Component from a CIF.

Two kinds of check. The first need nothing but the repository and always run:
the projection geometry, the fold semantics, and that a built component uses
only keys the old GTK MudLab can deserialise.

The second measure the projector against a corpus of published structures -
73 RRUFF/AMCSD clay CIFs the user keeps OUTSIDE this repository. When that
corpus is absent the harness SKIPS (exit 2) rather than failing, exactly as
the ones needing `.mud` fixtures do.

The oracle that matters
-----------------------
Textbook mineral formulas are NOT a valid oracle and cost a whole measurement
pass to learn: published cells differ in setting, Z and occupancy convention,
and the corpus contains a fluor-hectorite whose "missing" hydroxyls are really
fluorine. What can be checked honestly is **faithfulness** - does the projected
profile still hold the anion content the CIF itself states - plus agreement
with MudLab's own shipped components, which are real ground truth.

That oracle found a genuine defect. Folding a cell that stacks two layers used
to keep the larger of two coincident sites and discard the rest, while still
dividing amounts by the divisor, so shared content was counted once and then
halved again: 0 of 12 folded cells kept their anion totals. Merging coincident
levels by SUMMING fixed all of them, and the corpus now passes 73/73.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_cif_component.py

Exit codes: 0 = all pass, 1 = a regression, 2 = corpus unavailable.
"""

from __future__ import annotations

import math
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.calculations.goniometer import get_machine_correction_range  # noqa: E402
from mudlab.calculations.specimen import calculate_phase_intensities  # noqa: E402
from mudlab.file_parsers import cif_component as cc  # noqa: E402
from mudlab.file_parsers.atom_type_library import atom_type_library_map  # noqa: E402
from mudlab.file_parsers.default_catalog import (  # noqa: E402
    build_catalog_entry_by_name,
)
from mudlab.models.goniometer import Goniometer  # noqa: E402

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []

#: The published-structure corpus, kept OUTSIDE the repository (it is not
#: ours to redistribute). Override with MUDLAB_CIF_CORPUS to point at another
#: copy; absent, the corpus checks skip rather than fail.
CORPUS = os.environ.get(
    "MUDLAB_CIF_CORPUS",
    r"C:\GitHub\CIF builder\Clay structures\RRUFF AMCSD",
)

#: Keys a Component may serialise. The old GTK app deserialises with
#: ``cls(**properties)`` and raises TypeError on anything else, so an imported
#: component must be indistinguishable from a hand-built one.
COMPONENT_KEYS = {
    "uuid", "name", "d001", "default_c", "delta_c", "ucp_a", "ucp_b",
    "layer_atoms", "interlayer_atoms", "atom_relations", "linked_with_uuid",
    "inherit_ucp_a", "inherit_ucp_b", "inherit_d001", "inherit_default_c",
    "inherit_delta_c", "inherit_layer_atoms", "inherit_interlayer_atoms",
    "inherit_atom_relations",
}


def check(label, ok):
    results.append((label, bool(ok)))


def corpus_files():
    if not os.path.isdir(CORPUS):
        return []
    return sorted(os.path.join(CORPUS, n) for n in os.listdir(CORPUS)
                  if n.lower().endswith(".cif"))


def synthetic_cif():
    """A minimal two-layer cell, so the fold is exercised without the corpus.

    One 'layer' of four atoms, repeated at z + 1/2. Folding must return one
    layer holding the SAME total amount, not half of it.
    """
    rows = []
    for index, (element, z) in enumerate(
            (("Si", 0.05), ("O", 0.12), ("Al", 0.20), ("O", 0.28))):
        rows.append("%s%d %s %.4f %.4f %.4f 1.0" % (element, index, element,
                                                    0.1 * index, 0.2 * index, z))
        rows.append("%s%da %s %.4f %.4f %.4f 1.0" % (element, index, element,
                                                     0.1 * index, 0.2 * index,
                                                     z + 0.5))
    return "\n".join([
        "data_test",
        "_cell_length_a 5.2",
        "_cell_length_b 9.0",
        "_cell_length_c 20.0",
        "_cell_angle_alpha 90.0",
        "_cell_angle_beta 100.0",
        "_cell_angle_gamma 90.0",
        "loop_",
        "_atom_site_label",
        "_atom_site_type_symbol",
        "_atom_site_fract_x",
        "_atom_site_fract_y",
        "_atom_site_fract_z",
        "_atom_site_occupancy",
    ] + rows) + "\n"


def geometry_checks():
    """The projection identity, on a deliberately triclinic cell."""
    text = synthetic_cif().replace("_cell_angle_alpha 90.0",
                                   "_cell_angle_alpha 91.7") \
                          .replace("_cell_angle_gamma 90.0",
                                   "_cell_angle_gamma 89.8")
    structure = cc.parse_cif(text)
    basis = structure.cartesian_basis()
    check("projection: a and b have no component along c* (%.1e, %.1e)"
          % (basis[0][2], basis[1][2]),
          basis[0][2] == 0.0 and basis[1][2] == 0.0)
    check("projection: the c vector's height IS d001 (%.6f)" % basis[2][2],
          abs(basis[2][2] - structure.d001) < 1e-9)
    # Two atoms sharing z but nothing else must land at the same height. This
    # is why detecting a boundary in 3-D cannot beat detecting it after
    # projecting: the projection preserves height exactly.
    height = lambda x, y, z: (x * basis[0][2] + y * basis[1][2] + z * basis[2][2])
    check("projection: height depends on z ALONE, not on x or y",
          abs(height(0.0, 0.5, 0.37) - height(0.5, 0.0, 0.37)) < 1e-12)
    check("projection: d001 is V/|a x b|, not c sin(beta), for a triclinic cell",
          abs(structure.d001
              - structure.c * math.sin(math.radians(structure.beta))) > 1e-4)


def fold_checks():
    """The defect that cost 12 of 12 folded cells."""
    structure = cc.parse_cif(synthetic_cif())
    profile = cc.build_profile(structure)
    before = sum(e.pn for e in profile)
    divisor = cc.detect_repeat(profile)
    check("fold: a cell stacking two identical layers is detected (%d)" % divisor,
          divisor == 2)
    folded = cc.fold_profile(profile, divisor)
    after = sum(e.pn for e in folded)
    check("fold: one repeat holds HALF the cell's amount (%.2f of %.2f)"
          % (after, before), abs(after - before / 2.0) < 1e-6)
    check("fold: ...and half as many levels (%d of %d)" % (len(folded), len(profile)),
          len(folded) * 2 == len(profile))
    # The regression itself: coincident levels must MERGE, not overwrite.
    doubled = [cc.Entry("O", "layer", 0.10, 2.0), cc.Entry("O", "layer", 0.60, 2.0)]
    merged = cc.fold_profile(doubled, 2)
    check("fold: coincident levels merge by SUMMING, not by keeping the larger "
          "(%.2f)" % sum(e.pn for e in merged),
          abs(sum(e.pn for e in merged) - 2.0) < 1e-9)

    rows, report = cc.project(structure)
    check("fold: the projected repeat is half the cell (%.4f nm)" % report.d001_nm,
          abs(report.d001_nm - structure.d001 / 20.0) < 1e-6)
    check("fold: no row sits outside the repeat",
          all(-1e-9 <= r.z_nm <= report.d001_nm + 1e-9 for r in rows))


def component_checks():
    library = atom_type_library_map()
    structure = cc.parse_cif(synthetic_cif())
    rows, report = cc.project(structure)
    data = cc.component_dict(rows, report, name="Test")
    keys = set(data["properties"])
    check("component: serialises with the old app's keys only%s"
          % ("" if keys <= COMPONENT_KEYS else " -> %s" % sorted(keys - COMPONENT_KEYS)),
          keys <= COMPONENT_KEYS)
    check("component: it is a Component record", data.get("type") == "Component")
    check("component: every atom names a type the shipped library has",
          all(a["properties"]["atom_type_name"] in library
              for group in ("layer_atoms", "interlayer_atoms")
              for a in data["properties"][group]))
    check("component: hydrogen never becomes a row",
          all(a["properties"]["name"] != "H"
              for group in ("layer_atoms", "interlayer_atoms")
              for a in data["properties"][group]))
    # Every element the projector can emit must map to a real scattering factor,
    # or that atom contributes nothing and says nothing.
    unknown = [v for v in cc.ATOM_TYPE_BY_ELEMENT.values() if v not in library]
    check("component: every mapped atom type exists%s"
          % ("" if not unknown else " -> %s" % unknown), not unknown)


def corpus_checks(paths):
    library = atom_type_library_map()
    failed_parse, lost = [], []
    divisors = {}
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                structure = cc.parse_cif(handle.read())
            expanded = cc.expand(structure)
            rows, report = cc.project(structure)
        except Exception as exc:  # noqa: BLE001
            failed_parse.append("%s (%s)" % (os.path.basename(path), exc))
            continue
        divisors[report.repeat_divisor] = divisors.get(report.repeat_divisor, 0) + 1
        stated = sum(s.occupancy for s in expanded if s.element in ("O", "F"))
        want = stated / report.repeat_divisor
        got = sum(r.pn for r in rows if r.name in ("O", "OH", "H2O", "F"))
        if abs(want - got) > max(0.15, 0.03 * want):
            lost.append("%s (want %.1f got %.1f)"
                        % (os.path.basename(path), want, got))

    check("corpus: every published CIF parses and projects (%d)%s"
          % (len(paths), "" if not failed_parse else " -> %s" % failed_parse[:3]),
          not failed_parse)
    check("corpus: anion content is preserved in all of them%s"
          % ("" if not lost else " -> %s" % lost[:3]), not lost)
    check("corpus: folded cells are actually present to test (%s)"
          % ", ".join("%d x div %d" % (n, d) for d, n in sorted(divisors.items())),
          divisors.get(2, 0) >= 5)


def shipped_comparison():
    """Against real ground truth: MudLab's own components."""
    library = atom_type_library_map()
    gonio = Goniometer()
    gonio.min_2theta, gonio.max_2theta, gonio.steps = 2.0, 45.0, 4301
    two_theta = np.linspace(gonio.min_2theta, gonio.max_2theta, int(gonio.steps))
    theta = np.radians(two_theta * 0.5)
    correction = get_machine_correction_range(gonio, theta)

    def pattern(phase):
        return calculate_phase_intensities(
            theta, gonio.wavelength, gonio.wavelength_distribution,
            gonio.soller1, gonio.soller2, gonio.mcr_2theta, correction, [phase])[0]

    for cif_name, shipped, floor in (("Kaolinite__0012232.cif", "Kaolinite", 0.99),
                                     ("Illite__0005015.cif", "Illite", 0.90),
                                     ("Talc__0010839.cif", "Talc", 0.90),
                                     ("Chlorite__0004284.cif", "Chlorite", 0.90)):
        path = os.path.join(CORPUS, cif_name)
        if not os.path.isfile(path):
            check("shipped: %s absent from the corpus; skipped" % cif_name, True)
            continue
        phase = build_catalog_entry_by_name(shipped)[0]
        reference = pattern(phase)
        component, report, missing = cc.component_from_cif(path, library)
        check("shipped: %s imports with every atom type resolved%s"
              % (shipped, "" if not missing else " -> %s" % missing), not missing)
        check("shipped: %s basal spacing matches (%.4f vs %.4f nm)"
              % (shipped, phase.components[0].d001, component.d001),
              abs(phase.components[0].d001 - component.d001) < 0.02)
        phase.components[0] = component
        imported = pattern(phase)
        if reference.max() <= 0 or imported.max() <= 0:
            check("shipped: %s produces a pattern" % shipped, False)
            continue
        correlation = float(np.corrcoef(reference / reference.max(),
                                        imported / imported.max())[0, 1])
        check("shipped: %s matches MudLab's own component (r = %.4f, need %.2f)"
              % (shipped, correlation, floor), correlation >= floor)


def main():
    print("=" * 72)
    print("CIF -> Component projection")
    print("=" * 72)
    geometry_checks()
    fold_checks()
    component_checks()

    paths = corpus_files()
    if not paths:
        for label, ok in results:
            print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
        print()
        print("Published-CIF corpus not found at:")
        print("  %s" % CORPUS)
        print("Repository-only checks ran; skipping the rest (exit 2).")
        return 2 if all(ok for _, ok in results) else 1

    corpus_checks(paths)
    shipped_comparison()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
