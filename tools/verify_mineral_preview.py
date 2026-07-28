#!/usr/bin/env python
"""Durable harness for the Match Minerals reference-peak overlay, run head-less.

Batch 1 (foundation) covers:
  - Specimen.mineral_preview + set_mineral_preview: transient, emits
    visuals_changed, and is NOT persisted to the .mud;
  - PatternPlot.draw_pattern: draws one magenta stick per reference peak, height
    proportional to relative intensity, and none when the overlay is cleared.

Batch 2 (dialog wiring) is covered by additional checks appended below.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_mineral_preview.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project.
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication, QWidget

from mudlab.calculations import get_2t_from_nm
from mudlab.edit_markers_dialog import EditMarkersDialog
from mudlab.file_parsers.mud_project import load_mud, save_mud
from mudlab.match_minerals_dialog import MatchMineralsDialog, _PEAKS_ROLE
from mudlab.models.marker import Marker
from mudlab.plot_controller import MINERAL_PREVIEW_COLOR, PREVIEW_COLOR, PatternPlot

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


def fresh_project():
    return load_mud(FIXTURE)


def _mineral_lines(plot):
    return [ln for ln in plot.axes.get_lines()
            if ln.get_color() == MINERAL_PREVIEW_COLOR]


# ----------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------
def check_model():
    project = fresh_project()
    spec = next(s for s in project.specimens if s.has_experimental_data)
    check("mineral_preview defaults to None", spec.mineral_preview is None)

    fired = []
    spec.visuals_changed.connect(lambda: fired.append(1))
    spec.set_mineral_preview([(20.0, 100.0), (26.0, 50.0)])
    check("set_mineral_preview stores the peaks",
          spec.mineral_preview == [(20.0, 100.0), (26.0, 50.0)])
    check("set_mineral_preview emits visuals_changed", len(fired) == 1)
    spec.set_mineral_preview(None)
    check("set_mineral_preview(None) clears", spec.mineral_preview is None)
    spec.set_mineral_preview([])
    check("set_mineral_preview([]) clears", spec.mineral_preview is None)


def check_not_persisted():
    project = fresh_project()
    spec = next(s for s in project.specimens if s.has_experimental_data)
    spec.set_mineral_preview([(20.0, 100.0), (26.0, 50.0)])
    tmp = os.path.join(tempfile.mkdtemp(), "mp.mud")
    save_mud(project, tmp)
    reloaded = load_mud(tmp)
    rspec = next(s for s in reloaded.specimens if s.has_experimental_data)
    check("mineral_preview is NOT persisted to the .mud",
          rspec.mineral_preview is None)


# ----------------------------------------------------------------------
# Plot drawing
# ----------------------------------------------------------------------
def check_plot_sticks():
    project = fresh_project()
    spec = next(s for s in project.specimens if s.has_experimental_data)
    x, _ = spec.experimental_pattern
    mid = float(x[len(x) // 2])
    lo = float(x[len(x) // 4])
    spec.mineral_preview = [(mid, 100.0), (lo, 40.0)]

    plot = PatternPlot([spec], project)
    sticks = _mineral_lines(plot)
    check("plot draws one magenta stick per reference peak", len(sticks) == 2)

    # A stick is a vertical 2-point segment at its 2theta.
    xs = {round(float(ln.get_xdata()[0]), 6) for ln in sticks}
    check("sticks sit at the reference 2theta positions",
          round(mid, 6) in xs and round(lo, 6) in xs)

    # Height scales with relative intensity: the 100% stick is taller than 40%.
    def height(ln):
        yd = ln.get_ydata()
        return abs(yd[1] - yd[0])
    tall = max(sticks, key=lambda ln: round(float(ln.get_xdata()[0]), 6) == round(mid, 6))
    short = min(sticks, key=lambda ln: round(float(ln.get_xdata()[0]), 6) == round(mid, 6))
    check("stick height scales with relative intensity",
          height(tall) > height(short) > 0)

    # Clearing removes the sticks on the next draw.
    spec.mineral_preview = None
    plot.draw_pattern()
    check("clearing mineral_preview removes the sticks", len(_mineral_lines(plot)) == 0)


def _expected_preview(peaks, wavelength, x=None):
    """Reference conversion for the dialog's _preview_peaks (range off when
    x is None)."""
    out = []
    rng = (float(np.min(x)), float(np.max(x))) if x is not None and len(x) else None
    for d_angstrom, rel in peaks:
        nm = d_angstrom / 10.0
        if nm <= wavelength / 2.0:
            continue
        tt = get_2t_from_nm(nm, wavelength)
        if not np.isfinite(tt):
            continue
        if rng is not None and not (rng[0] <= tt <= rng[1]):
            continue
        out.append((tt, float(rel)))
    return out


def _same(a, b):
    return len(a) == len(b) and all(
        abs(p[0] - q[0]) < 1e-9 and abs(p[1] - q[1]) < 1e-9 for p, q in zip(a, b))


# ----------------------------------------------------------------------
# Dialog wiring (Batch 2)
# ----------------------------------------------------------------------
def check_dialog():
    project = fresh_project()
    spec = next(s for s in project.specimens if s.has_experimental_data)
    x, _ = spec.experimental_pattern
    spec.add_marker(Marker(label="a", position=float(x[len(x) // 3])))
    spec.add_marker(Marker(label="b", position=float(x[len(x) // 2])))

    dlg = MatchMineralsDialog(specimen=spec, targets=list(spec.markers))
    check("dialog: opens with a mineral preview (top auto-match)",
          spec.mineral_preview is not None and len(spec.mineral_preview) > 0)

    # Selecting a specific reference row previews its converted reflections.
    dlg.ui.chk_use_specimen_range.setChecked(False)
    dlg.ui.tv_minerals.setCurrentIndex(dlg.minerals_model.index(0, 0))
    peaks = dlg.minerals_model.item(0, 0).data(_PEAKS_ROLE)
    expected = _expected_preview(peaks, spec.wavelength)
    check("dialog: selecting a mineral previews its converted reflections",
          _same(spec.mineral_preview, expected))
    check("dialog: all previewed 2theta are finite Bragg reflections",
          all(np.isfinite(t) for t, _ in spec.mineral_preview))

    # Specimen range keeps only in-range peaks (a subset).
    dlg.ui.chk_use_specimen_range.setChecked(True)
    expected_ranged = _expected_preview(peaks, spec.wavelength, x)
    x_min, x_max = float(np.min(x)), float(np.max(x))
    check("dialog: Specimen range filters to the scanned range",
          _same(spec.mineral_preview, expected_ranged)
          and all(x_min <= t <= x_max for t, _ in spec.mineral_preview)
          and len(spec.mineral_preview) <= len(expected))

    # Selecting a match row also updates the preview. Use a row other than the
    # one auto-match already selected, so selectionChanged actually fires.
    if dlg.matches_model.rowCount() > 1:
        dlg.ui.chk_use_specimen_range.setChecked(False)
        dlg.ui.tv_matches.setCurrentIndex(dlg.matches_model.index(1, 0))
        mpeaks = dlg.matches_model.item(1, 0).data(_PEAKS_ROLE)
        check("dialog: selecting a match row previews it",
              _same(spec.mineral_preview, _expected_preview(mpeaks, spec.wavelength)))

    # Close clears the preview.
    dlg.reject()
    check("dialog: close (reject) clears the preview", spec.mineral_preview is None)
    dlg.deleteLater()


def _specimen_with_markers():
    project = fresh_project()
    spec = next(s for s in project.specimens if s.has_experimental_data)
    x, _ = spec.experimental_pattern
    for i in (3, 2, 4):
        spec.add_marker(Marker(label="m%d" % i, position=float(x[len(x) // i])))
    return spec


# ----------------------------------------------------------------------
# Cleanup / no-orphan (follow-up #1)
# ----------------------------------------------------------------------
def check_cleanup():
    spec = _specimen_with_markers()
    ed = EditMarkersDialog(specimen=spec)

    ed._on_match_minerals()
    dlg1 = ed._match_dialog
    check("Match Minerals opens from Edit Markers",
          isinstance(dlg1, MatchMineralsDialog))

    # Reopening closes the previous dialog and creates a new one (no orphan).
    ed._on_match_minerals()
    check("reopen replaces the match dialog (no accumulation)",
          ed._match_dialog is not None and ed._match_dialog is not dlg1)

    # Closing a match dialog clears the preview.
    ed._match_dialog.close()
    check("closing the match dialog clears the preview", spec.mineral_preview is None)

    # And closing Edit Markers with a match dialog open also clears it.
    ed._on_match_minerals()
    check("(precondition) preview set again", spec.mineral_preview is not None)
    ed.close()
    check("closing Edit Markers clears the preview + drops the dialog",
          spec.mineral_preview is None and ed._match_dialog is None)


class StubHost(QWidget):
    """Stand-in for the main window's lightweight mineral-preview plumbing."""

    def __init__(self):
        super().__init__()
        self.calls = []
        self.clears = 0

    def set_mineral_preview(self, specimen, peaks):
        self.calls.append(list(peaks) if peaks else None)
        specimen.mineral_preview = list(peaks) if peaks else None

    def clear_mineral_preview(self, specimen):
        self.clears += 1
        specimen.mineral_preview = None


# ----------------------------------------------------------------------
# Lightweight redraw path (follow-up #2a, and #2b for free)
# ----------------------------------------------------------------------
def check_lightweight_redraw():
    # (a) A data-op preview survives a mineral refresh on the SAME plot: no
    # rebuild, both overlays coexist.
    project = fresh_project()
    spec = next(s for s in project.specimens if s.has_experimental_data)
    plot = PatternPlot([spec], project)
    x, y = spec.experimental_pattern
    plot.set_preview(spec, x, y * 0.5, show_original=True)  # data-op curve
    spec.mineral_preview = [(float(x[len(x) // 2]), 100.0)]
    plot.refresh()
    colors = [ln.get_color() for ln in plot.axes.get_lines()]
    check("refresh keeps BOTH the data-op preview and the mineral sticks",
          PREVIEW_COLOR in colors and MINERAL_PREVIEW_COLOR in colors)

    # (b) The dialog routes the preview through the host (main window) rather
    # than the model-driven emit, so no full plot rebuild is triggered.
    spec2 = _specimen_with_markers()
    host = StubHost()
    mid = QWidget(host)  # stands in for the Edit Markers window
    fired = []
    spec2.visuals_changed.connect(lambda: fired.append(1))
    dlg = MatchMineralsDialog(mid, specimen=spec2, targets=list(spec2.markers))
    check("dialog routes the preview through the host",
          len(host.calls) > 0 and spec2.mineral_preview is not None)
    check("host path does NOT emit visuals_changed (no full rebuild)",
          len(fired) == 0)
    dlg.reject()
    check("dialog clears via the host on close",
          host.clears >= 1 and spec2.mineral_preview is None)
    dlg.deleteLater()


def main():
    check_model()
    check_not_persisted()
    check_plot_sticks()
    check_dialog()
    check_cleanup()
    check_lightweight_redraw()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- mineral-preview overlay verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
