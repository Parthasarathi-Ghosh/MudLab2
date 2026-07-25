#!/usr/bin/env python
"""Durable harness for the Detect Peaks wiring, run head-less.

The Detect Peaks dialog shipped as a placeholder: it opened, plotted nothing,
and added no markers. This harness drives the wired dialog + the
Specimen.auto_add_peaks it calls, and asserts markers are actually created at
the detected peak positions (not merely that the dialog opens/accepts).

Coverage:
  - Specimen.clear_markers / auto_add_peaks (both algorithms, both patterns),
    cross-checked against calculations.peak_detection directly so the marker
    set must equal the detector's output;
  - the dialog's threshold histogram + the coupled Selected-threshold / # of
    peaks fields + the draggable line;
  - accept -> the specimen gains exactly the peaks at the selected cut-off.

The detector numerics themselves are guarded by verify_peak_detection.py.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_detect_peaks.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication, QMessageBox

from mudlab.calculations import peak_detection as pd
from mudlab.detect_peaks_dialog import DetectPeaksDialog
from mudlab.edit_markers_dialog import EditMarkersDialog
from mudlab.file_parsers.mud_project import load_mud
from mudlab.models.marker import Marker
from mudlab.models.specimen import Specimen, _peak_label

_FIXTURE_NAME = "308 r1.mud"
FIXTURE = os.path.join(_REPO, "tools", "sample_projects", _FIXTURE_NAME)
if not os.path.isfile(FIXTURE):
    FIXTURE = os.path.join(os.path.expanduser("~"), "Downloads", _FIXTURE_NAME)
if not os.path.isfile(FIXTURE):
    print("No sample project found; skipping (exit 2).")
    raise SystemExit(2)

app = QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def fresh_specimen():
    project = load_mud(FIXTURE)
    for spec in project.specimens:
        if spec.has_experimental_data:
            return spec
    raise SystemExit(2)


def synthetic_specimen():
    """A deterministic specimen with 6 well-separated Gaussian peaks on the
    CALCULATED curve (so base=2 / pattern='calc' can be exercised)."""
    x = np.linspace(5.0, 65.0, 3000)
    y = np.full_like(x, 2.0)
    for pos, amp, wid in [
        (10.0, 90, 0.15), (18.0, 60, 0.15), (26.0, 100, 0.15),
        (34.0, 45, 0.15), (48.0, 70, 0.15), (58.0, 30, 0.15),
    ]:
        y = y + amp * np.exp(-0.5 * ((x - pos) / wid) ** 2)
    spec = Specimen(name="synthetic")
    spec.set_calculated_pattern(x, y)
    return spec


# ----------------------------------------------------------------------
# Model: clear_markers / auto_add_peaks
# ----------------------------------------------------------------------
def check_clear_markers():
    spec = fresh_specimen()
    spec.add_marker(Marker(label="a", position=10.0))
    spec.add_marker(Marker(label="b", position=20.0))
    fired = []
    spec.visuals_changed.connect(lambda: fired.append(1))
    spec.clear_markers()
    check("clear_markers empties the list", len(spec.markers) == 0)
    check("clear_markers emits once", len(fired) == 1)
    # No-op on an empty list must not emit.
    fired.clear()
    spec.clear_markers()
    check("clear_markers no-op is silent", len(fired) == 0)


def check_auto_add_threshold():
    spec = fresh_specimen()
    spec.clear_markers()
    x, y = spec.experimental_pattern
    threshold = 0.05
    added = spec.auto_add_peaks(threshold, pattern="exp", algorithm="threshold")
    maxtab, _ = pd.peakdetect(np.asarray(y, float), np.asarray(x, float), 5, threshold)
    expected_pos = [p for p, _ in maxtab]
    got_pos = [m.position for m in added]
    check("auto_add(threshold): positions == peakdetect", got_pos == expected_pos)
    check("auto_add(threshold): >0 peaks found", len(added) > 0)
    check("auto_add(threshold): base=1 (experimental)",
          all(m.base == 1 for m in added))
    check("auto_add(threshold): markers registered on specimen",
          all(m in spec.markers for m in added))
    # Labels are the d-spacing at each position.
    labels_ok = all(
        m.label == _peak_label(m.position, spec.wavelength) for m in added)
    check("auto_add(threshold): labels are d-spacings", labels_ok)


def check_auto_add_skips_existing():
    spec = fresh_specimen()
    spec.clear_markers()
    x, y = spec.experimental_pattern
    threshold = 0.05
    maxtab, _ = pd.peakdetect(np.asarray(y, float), np.asarray(x, float), 5, threshold)
    # Seed a marker exactly on the first detected peak.
    seed_pos = maxtab[0][0]
    spec.add_marker(Marker(label="seed", position=seed_pos))
    added = spec.auto_add_peaks(threshold, pattern="exp", algorithm="threshold")
    check("auto_add skips an existing peak position",
          all(m.position != seed_pos for m in added)
          and len(added) == len(maxtab) - 1)


def check_auto_add_prominence_and_calc():
    spec = synthetic_specimen()
    x, y = spec.calculated_pattern
    added = spec.auto_add_peaks(
        0.05, pattern="calc", algorithm="prominence", min_distance=0.1)
    span = x[-1] - x[0]
    resolution = (len(x) - 1) / span
    min_dist_samples = max(1, int(0.1 * resolution))
    maxtab = pd.scipy_peakdetect(
        np.asarray(y, float), np.asarray(x, float),
        min_prominence=0.05, min_distance_samples=min_dist_samples)
    expected = [p for p, _ in maxtab]
    got = [m.position for m in added]
    check("auto_add(prominence,calc): positions == scipy_peakdetect", got == expected)
    check("auto_add(prominence,calc): base=2 (calculated)",
          all(m.base == 2 for m in added))
    # The 6 synthetic peaks must all be recovered.
    recovered = sum(
        any(abs(m.position - pos) < 0.2 for m in added)
        for pos in (10.0, 18.0, 26.0, 34.0, 48.0, 58.0))
    check("auto_add(prominence,calc): all 6 synthetic peaks recovered",
          recovered == 6)


def check_auto_add_empty_pattern():
    spec = Specimen(name="empty")
    check("auto_add on empty pattern returns []",
          spec.auto_add_peaks(0.1) == [])


# ----------------------------------------------------------------------
# Dialog: histogram + coupled fields + accept
# ----------------------------------------------------------------------
def check_dialog_histogram_and_coupling():
    spec = fresh_specimen()
    spec.clear_markers()
    dlg = DetectPeaksDialog(specimen=spec)
    check("dialog: histogram computed",
          dlg._threshold_data is not None and len(dlg._threshold_data[0]) > 1)
    deltas = dlg._threshold_data[0]
    thr = dlg.ui.sel_threshold.value()
    check("dialog: sel_threshold within grid",
          deltas[0] <= thr <= deltas[-1])
    # # of peaks field consistent with the interpolated histogram value.
    expect_n = int(round(dlg._num_peaks_at(thr)))
    check("dialog: # peaks field == histogram value at threshold",
          dlg.ui.spin_sel_num_peaks.value() == expect_n)

    # Editing the threshold field updates the # of peaks field. Compare against
    # the value the spinbox actually stored (it rounds to its decimals), so the
    # check tracks the displayed threshold, not the pre-rounding input.
    mid = float((deltas[0] + deltas[-1]) / 2)
    dlg.ui.sel_threshold.setValue(mid)
    shown = dlg.ui.sel_threshold.value()
    check("dialog: editing threshold updates # peaks",
          dlg.ui.spin_sel_num_peaks.value() == int(round(dlg._num_peaks_at(shown))))

    # Editing the # of peaks field drives the threshold (reverse lookup), to
    # within the spinbox's own rounding resolution.
    _, numpeaks = dlg._threshold_data
    target_n = int(numpeaks[len(numpeaks) // 2])
    dlg.ui.spin_sel_num_peaks.setValue(target_n)
    back = dlg.ui.sel_threshold.value()
    check("dialog: editing # peaks drives threshold",
          abs(dlg._threshold_at(target_n) - back) < 1e-4)

    # Dragging the plot line sets the threshold (to spinbox resolution).
    dlg._on_plot_press(type("E", (), {"inaxes": dlg.axes, "button": 1, "xdata": mid})())
    check("dialog: plot click sets threshold near click x",
          abs(dlg.ui.sel_threshold.value() - mid) < 1e-4)
    dlg._on_plot_release(None)
    dlg.deleteLater()


def check_dialog_accept_adds_markers():
    spec = fresh_specimen()
    spec.clear_markers()
    dlg = DetectPeaksDialog(specimen=spec)
    thr = dlg.ui.sel_threshold.value()
    x, y = spec.experimental_pattern
    maxtab, _ = pd.peakdetect(np.asarray(y, float), np.asarray(x, float), 5, thr)
    dlg._on_accept()
    check("dialog accept: added markers == detector count at threshold",
          len(dlg.added_markers) == len(maxtab) and len(spec.markers) == len(maxtab))
    dlg.deleteLater()


def check_dialog_calc_only_pattern():
    spec = synthetic_specimen()  # calc only, no experimental data
    dlg = DetectPeaksDialog(specimen=spec)
    model = dlg.ui.pattern.model()
    check("dialog: exp disabled when only calc data",
          not model.item(0).isEnabled() and model.item(1).isEnabled())
    check("dialog: defaults to calc pattern", dlg._current_pattern() == "calc")
    dlg.deleteLater()


def check_edit_markers_clear_then_cancel():
    """Bug A regression: answering "Yes, clear" then cancelling the dialog (or
    detecting nothing) must reload the marker list, not leave it showing the
    markers that were just cleared."""
    spec = fresh_specimen()
    spec.clear_markers()
    spec.add_marker(Marker(label="m1", position=10.0))
    spec.add_marker(Marker(label="m2", position=20.0))
    ed = EditMarkersDialog(specimen=spec)
    pre_rows = ed.objects_model.rowCount()

    orig_question = QMessageBox.question
    orig_exec = DetectPeaksDialog.exec
    # Confirm "Yes" (clear), then the user cancels the dialog -> 0 added markers.
    QMessageBox.question = staticmethod(
        lambda *a, **k: QMessageBox.StandardButton.Yes)
    DetectPeaksDialog.exec = lambda self: 0
    try:
        ed._on_find_peaks()
    finally:
        QMessageBox.question = orig_question
        DetectPeaksDialog.exec = orig_exec

    check("Bug A: clear+cancel actually empties the specimen markers",
          len(spec.markers) == 0)
    check("Bug A: marker list reloads (no stale rows) after clear+cancel",
          pre_rows == 2 and ed.objects_model.rowCount() == 0)
    ed.deleteLater()


def main():
    check_clear_markers()
    check_edit_markers_clear_then_cancel()
    check_auto_add_threshold()
    check_auto_add_skips_existing()
    check_auto_add_prominence_and_calc()
    check_auto_add_empty_pattern()
    check_dialog_histogram_and_coupling()
    check_dialog_accept_adds_markers()
    check_dialog_calc_only_pattern()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- Detect Peaks verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
