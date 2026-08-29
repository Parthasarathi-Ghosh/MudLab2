#!/usr/bin/env python
"""The goniometer's 2theta range: seeded from an imported scan, and no shipped
setup that describes an impossible one.

Two related fixes:

  1. Importing a specimen left the goniometer at the 3-45 deg / 2500-step model
     default however wide the scan actually was, so an untouched goniometer
     described a measurement nobody took. The old app seeded this on every
     import (`create_gon_file` -> `reset_from_file`) but only from a range a
     vendor parser DECLARED, so a plain `.xy` still fell back to the default.
     We seed from the parsed axis, which every format we can open provides.

  2. `D8 ECO Lynxeye XE.gon` stored `max_2theta` equal to `min_2theta` (both
     3.0) - a zero-width range that calculates an empty pattern. The file is
     byte-identical to upstream PyXRD's, so this is inherited, not a porting
     slip, and upstream carries no better value: it is now 2-90 deg. The sweep
     below is the part that matters long-term - it fails for ANY shipped setup
     with a degenerate range, so this cannot come back unnoticed.

Seeding is a DEFAULT, not a decision. `Goniometer.apply_setup` resets every
modelled parameter, so a setup applied afterwards overwrites all three fields -
checked here, because that precedence is the whole reason seeding is safe.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_goniometer_seeding.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from mudlab.file_parsers.gon_file import (  # noqa: E402
    DEFAULT_GONIO_DIR, list_setups_in, load_gon,
)
from mudlab.models.goniometer import Goniometer  # noqa: E402

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def counting(gonio):
    """A list that grows by one per data_changed emission."""
    seen = []
    gonio.data_changed.connect(lambda: seen.append(1))
    return seen


def main():  # noqa: C901 - a checklist, not a branchy algorithm
    # ------------------------------------------------- 1. the seeding itself
    gonio = Goniometer()
    check("defaults are the model's before seeding (3-45 deg, 2500)",
          (gonio.min_2theta, gonio.max_2theta, gonio.steps) == (3.0, 45.0, 2500))

    x = np.linspace(4.0, 70.0, 3301)
    emitted = counting(gonio)
    check("seeding a 4-70 deg / 3301-point scan reports success",
          gonio.seed_range_from_data(x) is True)
    check("...min_2theta comes from the scan (%.4f)" % gonio.min_2theta,
          abs(gonio.min_2theta - 4.0) < 1e-9)
    check("...max_2theta comes from the scan (%.4f)" % gonio.max_2theta,
          abs(gonio.max_2theta - 70.0) < 1e-9)
    check("...steps is the point count (%d)" % gonio.steps, gonio.steps == 3301)
    check("...steps is an int, not a float (%s)" % type(gonio.steps).__name__,
          isinstance(gonio.steps, int))
    # Three Prop writes would be three recalculations of every pattern that
    # listens; the setter blocks them and emits once, as apply_setup does.
    check("...and data_changed fires ONCE, not once per field (%d)"
          % len(emitted), len(emitted) == 1)

    # ------------------------------------------------- 2. what it must refuse
    for label, bad in (
        ("an empty axis", np.array([])),
        ("a single point", np.array([12.0])),
        ("a constant axis (would be zero-width)", np.full(500, 7.0)),
        ("an all-NaN axis", np.full(10, np.nan)),
    ):
        fresh = Goniometer()
        seen = counting(fresh)
        refused = fresh.seed_range_from_data(bad) is False
        untouched = (fresh.min_2theta, fresh.max_2theta, fresh.steps) == (
            3.0, 45.0, 2500)
        check("refuses %s, leaving the defaults alone" % label,
              refused and untouched and not seen)

    # A descending axis must not come out inverted: min/max, not first/last.
    fresh = Goniometer()
    fresh.seed_range_from_data(np.linspace(60.0, 5.0, 100))
    check("a DESCENDING axis still gives min < max (%.1f-%.1f)"
          % (fresh.min_2theta, fresh.max_2theta),
          fresh.min_2theta == 5.0 and fresh.max_2theta == 60.0)

    # Non-finite samples are dropped, and `steps` counts what survived - the
    # count must match the range it describes.
    fresh = Goniometer()
    dirty = np.array([3.0, np.nan, 4.0, np.inf, 5.0, -np.inf, 6.0])
    fresh.seed_range_from_data(dirty)
    check("NaN/inf are dropped and steps counts the survivors (%d of %d)"
          % (fresh.steps, dirty.size),
          fresh.steps == 4 and fresh.min_2theta == 3.0 and fresh.max_2theta == 6.0)

    # ------------------------------------- 3. a setup still wins over seeding
    seeded = Goniometer()
    seeded.seed_range_from_data(np.linspace(4.0, 70.0, 3301))
    seeded.apply_setup(load_gon(os.path.join(DEFAULT_GONIO_DIR, "D8 ECO.gon")))
    check("apply_setup OVERWRITES a seeded range (%.1f-%.1f, %d steps)"
          % (seeded.min_2theta, seeded.max_2theta, seeded.steps),
          (seeded.min_2theta, seeded.max_2theta, seeded.steps) == (3.0, 45.0, 2500))

    # ------------------------------------ 4. every shipped setup is scannable
    setups = list_setups_in(DEFAULT_GONIO_DIR)
    check("the shipped setups still load (%d found)" % len(setups),
          len(setups) >= 12)
    degenerate, too_few, unreadable = [], [], []
    for name, path in setups:
        try:
            props = load_gon(path)
        except (OSError, ValueError):
            unreadable.append(name)
            continue
        applied = Goniometer()
        applied.apply_setup(props)
        if not applied.max_2theta > applied.min_2theta:
            degenerate.append("%s (%.4g-%.4g)"
                              % (name, applied.min_2theta, applied.max_2theta))
        if int(applied.steps) < 2:
            too_few.append("%s (%d)" % (name, applied.steps))
    check("every shipped setup parses%s"
          % ("" if not unreadable else " -> %s" % unreadable), not unreadable)
    check("no shipped setup has a zero-width 2theta range%s"
          % ("" if not degenerate else " -> %s" % degenerate), not degenerate)
    check("every shipped setup steps at least twice%s"
          % ("" if not too_few else " -> %s" % too_few), not too_few)

    lynxeye = Goniometer()
    lynxeye.apply_setup(load_gon(os.path.join(
        DEFAULT_GONIO_DIR, "D8 ECO Lynxeye XE.gon")))
    check("D8 ECO Lynxeye XE is 2-90 deg (%.1f-%.1f)"
          % (lynxeye.min_2theta, lynxeye.max_2theta),
          (lynxeye.min_2theta, lynxeye.max_2theta) == (2.0, 90.0))
    check("...and its other fields are untouched (radius %.1f, %s, %d steps)"
          % (lynxeye.radius, lynxeye.divergence_mode, lynxeye.steps),
          lynxeye.radius == 25.0 and lynxeye.divergence_mode == "AUTOMATIC"
          and lynxeye.steps == 6895 and len(lynxeye.wavelength_distribution) == 4)

    # The point of the fix: a specimen on this setup can produce a pattern.
    blank = Goniometer()
    blank.apply_setup(load_gon(os.path.join(
        DEFAULT_GONIO_DIR, "D8 ECO Lynxeye XE.gon")))
    grid = np.linspace(blank.min_2theta, blank.max_2theta, int(blank.steps))
    check("a data-less specimen on that setup spans a real range (%.1f-%.1f)"
          % (grid.min(), grid.max()), grid.max() - grid.min() > 80.0)

    # ------------------------------- 4b. the pane must be able to SHOW a scan
    # Seeding is what made this reachable. `steps` used to be 2500 after every
    # import, comfortably inside the spin box's old maximum of 10000; a real
    # PSD scan (2-90 deg at 0.005) is 17601 points. The box clamped the display
    # to 10000 - and one click on its down arrow then wrote 9999 back over the
    # model, silently discarding the scan length.
    from mudlab.goniometer_widget import GoniometerWidget

    wide = Goniometer()
    wide.seed_range_from_data(np.arange(2.0, 90.0 + 1e-9, 0.005))
    widget = GoniometerWidget()
    widget.bind_goniometer(wide)
    shown = widget.ui.steps_spn_btn1.value()
    check("the steps box SHOWS a 17601-point scan rather than clamping (%d)"
          % shown, shown == wide.steps == 17601)
    widget.ui.steps_spn_btn1.stepDown()
    check("...and a down-arrow click edits it instead of truncating it (%d)"
          % wide.steps, wide.steps == 17600)
    check("the min/max 2theta boxes reach 90 deg",
          widget.ui.gonio_min_2theta_spb.maximum() >= 90.0
          and widget.ui.gonio_max_2theta_spb.maximum() >= 90.0)
    widget.deleteLater()

    # ------------------------------------------------- 5. end to end, on disk
    scratch = tempfile.mkdtemp(prefix="gonio-seed-")
    xy_path = os.path.join(scratch, "synthetic scan.xy")
    data_x = np.arange(2.5, 75.0 + 1e-9, 0.02)
    data_y = 100.0 + 20.0 * np.exp(-((data_x - 26.6) ** 2) / 0.02)
    with open(xy_path, "w", encoding="utf-8") as handle:
        for xi, yi in zip(data_x, data_y):
            handle.write("%.4f\t%.4f\n" % (xi, yi))

    real_question = QMessageBox.question
    real_warning = QMessageBox.warning
    QMessageBox.question = staticmethod(
        lambda *a, **k: QMessageBox.StandardButton.No)
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    try:
        from mudlab.calculations.specimen import calculate_specimen_pattern
        from mudlab.file_parsers.default_catalog import (
            build_catalog_entry_by_name,
        )
        from mudlab.file_parsers.mud_project import load_mud, save_mud
        from mudlab.main_window import MainWindow

        window = MainWindow()
        app.processEvents()
        imported = window.import_specimen_files([xy_path])
        app.processEvents()
        check("importing a .xy makes one specimen", len(imported) == 1)
        specimen = imported[0]
        gon = specimen.goniometer
        check("the imported specimen's goniometer matches its scan "
              "(%.2f-%.2f, %d)" % (gon.min_2theta, gon.max_2theta, gon.steps),
              abs(gon.min_2theta - float(data_x.min())) < 1e-6
              and abs(gon.max_2theta - float(data_x.max())) < 1e-6
              and gon.steps == data_x.size)
        # A .xy carries no metadata, so the wavelength must stay the Cu Ka1
        # default - the seeding must not have disturbed that branch.
        check("...and a metadata-less file keeps Cu Ka1 (%.6f nm)"
              % gon.wavelength, abs(gon.wavelength - 0.154056) < 1e-9)

        # The seeded range must survive a save/load round-trip.
        mud_path = os.path.join(scratch, "seeded.mud")
        save_mud(window.project, mud_path)
        reloaded = load_mud(mud_path)
        back = reloaded.specimens[0].goniometer
        check("the seeded range survives a .mud round-trip (%.2f-%.2f, %d)"
              % (back.min_2theta, back.max_2theta, back.steps),
              (round(back.min_2theta, 6), round(back.max_2theta, 6), back.steps)
              == (round(float(data_x.min()), 6), round(float(data_x.max()), 6),
                  int(data_x.size)))

        # Seeding must not have moved the numerics for a specimen that HAS
        # data: calculate_specimen grids on the experimental axis regardless.
        phase = build_catalog_entry_by_name("Illite")[0]
        target = reloaded.specimens[0]
        before = calculate_specimen_pattern(target, [phase], 1.0, [1.0], 0.0)
        target.goniometer.min_2theta = 11.0
        target.goniometer.max_2theta = 12.0
        target.goniometer.steps = 5
        after = calculate_specimen_pattern(target, [phase], 1.0, [1.0], 0.0)
        same = (len(before[0]) == len(after[0])
                and np.allclose(before[0], after[0])
                and np.allclose(before[1], after[1]))
        check("a specimen WITH data is unaffected by the range "
              "(calc still grids on the scan, %d points)" % len(after[0]), same)

        window._dirty = False
        window.close()
    finally:
        QMessageBox.question = real_question
        QMessageBox.warning = real_warning

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Goniometer range: seeding on import + shipped-setup sanity")
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
