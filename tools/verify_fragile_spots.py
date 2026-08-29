#!/usr/bin/env python
"""The "faithful but fragile" spots, once they stopped being faithful.

These were ported from the old app exactly as they were and left alone on
purpose - a deliberate bug-for-bug port is worth more than a hasty improvement
when the numerics are being validated against goldens. Each is now fixed, and
this pins the fix so nobody restores the old behaviour by accident.

  1. `find_closest(value, [])` raised IndexError out of `zip(*array)`. Every
     caller guarded it, so it never surfaced - but a helper that is only safe
     because of what its callers remember is a trap for the next one.
  2. `get_best_threshold` divided by a zero slope on a FLAT region: 32
     "invalid value encountered in scalar divide" warnings on stderr for one
     Detect Peaks run. The numerical answer is unchanged - nan fails the
     |R| >= 0.98 test exactly as it did - only the noise is gone.
  3. The mineral loader let a header too short to carry an abbreviation keep
     the PREVIOUS mineral's, so an entry silently wore a label belonging to
     something else. One shipped entry was short (Augite) and inherited "Aug"
     from the Augite above it - right by luck. The parser now clears, and the
     data line carries its own.
  4. `Muscovite.cmp` was bundled but never offered, faithful to the old app,
     which shipped the component and left it out of its own list.
  5. The emission-spectrum editor took any number. A missing leading zero -
     1.544 for 0.1544 nm - is a valid float and an impossible wavelength, and
     nothing downstream complains: `get_2t_from_nm` clamps arcsin's argument,
     so reflections do not error, they silently stop appearing.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_fragile_spots.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys
import warnings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from mudlab.calculations.peak_detection import (  # noqa: E402
    find_closest, get_best_threshold, load_mineral_references, score_minerals,
)

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def main():
    # ------------------------------------------------------- 1. find_closest
    check("find_closest: an empty array answers None instead of raising",
          find_closest(1.0, []) is None)
    check("find_closest: still finds the nearest when there IS one",
          find_closest(2.9, [(1.0, 5), (3.0, 7)]) == (3.0, 7))
    # VACUOUS BEFORE: this passed an empty MINERALS list too, so the loop that
    # reaches find_closest never ran. Scoring an empty pattern against the real
    # library is the case that used to crash - first with IndexError, then,
    # after find_closest answered None, with TypeError one line further down.
    check("scoring: an empty peak list against REAL minerals returns nothing",
          score_minerals([], load_mineral_references()) == [])
    # d-spacings here are ANGSTROM, matching the reference library - quartz's
    # 3.343 / 4.255 lines. (My first attempt used nm and matched nothing,
    # which is a unit mistake in the test, not a defect in the code.)
    check("scoring: ...and real quartz peaks still score",
          any(name.startswith("Quartz") for name, _a, _p, _m, _s
              in score_minerals([(3.34347, 100.0), (4.25499, 16.0)],
                                load_mineral_references())))

    # --------------------------------------------------- 2. the flat divide
    x = np.linspace(5.0, 45.0, 400)
    flat = np.ones_like(x) * 3.0
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = get_best_threshold(x, flat)
        noisy = [w for w in caught if issubclass(w.category, RuntimeWarning)]
    check("threshold: a flat region emits no divide warnings (%d)" % len(noisy),
          not noisy)
    check("threshold: ...and still returns a result", out is not None)

    # A real pattern must be unaffected - this is a noise fix, not a numerics
    # change, and that distinction is the whole reason it was left alone before.
    import glob

    from mudlab.file_parsers.mud_project import load_mud
    fixtures = sorted(glob.glob(os.path.join(
        _REPO, "tools", "sample_projects", "*.mud")))
    real = None
    for path in fixtures:
        project = load_mud(path)
        for specimen in project.specimens:
            if specimen is not None and specimen.has_experimental_data:
                real = specimen.experimental_pattern
                break
        if real is not None:
            break
    if real is not None:
        _curve, threshold, _mx = get_best_threshold(real[0], real[1])
        check("threshold: a real pattern still yields a sane threshold (%.4f)"
              % threshold, 0.0 < threshold < 10.0)
    else:
        check("threshold: (no real pattern available; skipped)", True)

    # ----------------------------------------------- 3. the mineral loader
    minerals = load_mineral_references()
    check("minerals: the library still loads (%d entries)" % len(minerals),
          len(minerals) > 200)
    missing = [n for n, abbr, _ in minerals if not abbr]
    check("minerals: every entry carries its own abbreviation%s"
          % ("" if not missing else " -> %s" % missing[:4]), not missing)
    augite = [(n, a) for n, a, _ in minerals if n.startswith("Augite")]
    check("minerals: Augite is labelled Aug, by data and not by inheritance",
          bool(augite) and all(a == "Aug" for _n, a in augite))

    # The parser must CLEAR rather than inherit: a synthetic short header must
    # not pick up the abbreviation above it.
    import tempfile

    tmp = os.path.join(tempfile.mkdtemp(), "minerals.csv")
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write("Alpha                   00-0001                  Alp\n")
        handle.write("1.0\n100.0\n")
        handle.write("Beta                    00-0002\n")     # too short
        handle.write("2.0\n50.0\n")
    parsed = {n: a for n, a, _ in load_mineral_references(tmp)}
    check("minerals: a short header does NOT inherit the previous label",
          parsed.get("Beta") == "" and parsed.get("Alpha") == "Alp")

    # ------------------------------------------------------- 4. Muscovite
    from mudlab.file_parsers.default_catalog import (
        build_catalog_entry_by_name, default_phase_names,
    )
    names = default_phase_names()
    check("catalog: Muscovite is offered", "Muscovite" in names)
    built = build_catalog_entry_by_name("Muscovite")
    check("catalog: ...and it builds a valid phase",
          len(built) == 1 and built[0].is_valid)
    check("catalog: ...with its atoms",
          bool(built[0].components[0].layer_atoms))

    # ------------------------------------------- 5. wavelength range check
    from mudlab.models.goniometer import Goniometer
    from mudlab.wavelength_distribution_dialog import (
        WavelengthDistributionDialog,
    )

    warned = []
    real_warning = QMessageBox.warning
    QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(a[2]))
    try:
        gonio = Goniometer()
        dialog = WavelengthDistributionDialog(None, goniometer=gonio)
        before = list(gonio.wavelength_distribution)
        item = dialog.model.item(0, 0)
        dialog._updating = False

        item.setText("1.544")            # the missing-leading-zero typo
        check("wavelength: a 1.544 nm typo is refused", bool(warned))
        check("wavelength: ...the message explains nanometres",
              warned and "NANOMETRES" in warned[-1])
        check("wavelength: ...the cell reverts", item.text() == "0.154056")
        check("wavelength: ...and the spectrum is untouched",
              list(gonio.wavelength_distribution) == before)

        warned.clear()
        item.setText("0.154056")         # a legitimate value still goes in
        check("wavelength: a valid wavelength is accepted", not warned)

        warned.clear()
        fraction = dialog.model.item(0, 1)
        fraction.setText("-1")
        check("wavelength: a negative fraction is refused", bool(warned))
        dialog.close()
    finally:
        QMessageBox.warning = real_warning

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Fragile spots")
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
