#!/usr/bin/env python
"""Durable harness for the live data-op preview overlay foundation (Batch 1),
run head-less.

Covers:
  - Specimen.preview_* : non-destructive and equal to what the matching
    mutating operation applies (same pattern_ops), so the preview matches OK;
  - PatternPlot.set_preview / clear_preview : draws the preview curve in the
    preview colour over the original, hides the original when asked, restores
    on clear, and preserves the user's zoom across the redraw.

The pattern_ops numerics themselves are guarded by verify_pattern_ops.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_pattern_preview.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication

from mudlab.calculations import pattern_ops
from mudlab.file_parsers.mud_project import load_mud
from mudlab.plot_controller import PREVIEW_COLOR, PatternPlot

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


def fresh_specimen():
    project = load_mud(FIXTURE)
    return next(s for s in project.specimens if s.has_experimental_data)


# ----------------------------------------------------------------------
# Specimen.preview_* : non-destructive + equal to apply
# ----------------------------------------------------------------------
def _check_preview_matches_apply(name, preview_fn, apply_fn):
    spec = fresh_specimen()
    x0, y0 = (a.copy() for a in spec.experimental_pattern)
    px, py = preview_fn(spec)
    # Non-destructive: the stored pattern is unchanged by the preview.
    unchanged = (np.array_equal(spec.experimental_pattern[0], x0)
                 and np.array_equal(spec.experimental_pattern[1], y0))
    check("%s: preview is non-destructive" % name, unchanged)
    apply_fn(spec)
    ax, ay = spec.experimental_pattern
    check("%s: preview == applied result" % name,
          np.allclose(px, ax) and np.allclose(py, ay))


def check_preview_methods():
    _check_preview_matches_apply(
        "smooth",
        lambda s: s.preview_smooth(pattern_ops.SMOOTH_BLACKMAN, 5),
        lambda s: s.smooth_data(pattern_ops.SMOOTH_BLACKMAN, 5),
    )
    _check_preview_matches_apply(
        "remove_background",
        lambda s: s.preview_remove_background(pattern_ops.BG_LINEAR, 12.0),
        lambda s: s.remove_background(pattern_ops.BG_LINEAR, 12.0),
    )
    _check_preview_matches_apply(
        "shift",
        lambda s: s.preview_shift(0.05, 0.42574),
        lambda s: s.apply_shift(0.05, 0.42574),
    )

    # Strip uses a shared strip object, so preview and apply take the same one.
    spec = fresh_specimen()
    x, _ = spec.experimental_pattern
    startx, endx = float(x[len(x) // 3]), float(x[len(x) // 3 + 20])
    strip = spec.compute_strip_pattern(startx, endx)
    y0 = spec.experimental_pattern[1].copy()
    px, py = spec.preview_strip(strip)
    check("strip: preview is non-destructive",
          np.array_equal(spec.experimental_pattern[1], y0))
    spec.apply_strip(strip)
    check("strip: preview == applied result",
          np.allclose(py, spec.experimental_pattern[1]))

    # Noise is random: only assert non-destructive + that noise was added.
    spec = fresh_specimen()
    y0 = spec.experimental_pattern[1].copy()
    _, py = spec.preview_add_noise(0.1)
    check("add_noise: preview is non-destructive",
          np.array_equal(spec.experimental_pattern[1], y0))
    check("add_noise: preview changed the data", py.shape == y0.shape
          and not np.array_equal(py, y0))


# ----------------------------------------------------------------------
# PatternPlot preview overlay
# ----------------------------------------------------------------------
def check_plot_overlay():
    project = fresh_project()
    spec = next(s for s in project.specimens if s.has_experimental_data)
    plot = PatternPlot([spec], project)
    base = len(plot.axes.get_lines())
    x, y = spec.experimental_pattern

    plot.set_preview(spec, x, y * 0.5, show_original=True)
    lines = plot.axes.get_lines()
    check("plot: preview adds one line (original kept)", len(lines) == base + 1)
    check("plot: preview drawn in PREVIEW_COLOR",
          any(ln.get_color() == PREVIEW_COLOR for ln in lines))

    plot.set_preview(spec, x, y * 0.5, show_original=False)
    check("plot: show_original=False hides the base line",
          len(plot.axes.get_lines()) == base)
    check("plot: preview still present when original hidden",
          any(ln.get_color() == PREVIEW_COLOR for ln in plot.axes.get_lines()))

    plot.clear_preview()
    check("plot: clear_preview restores the original view",
          len(plot.axes.get_lines()) == base
          and not any(ln.get_color() == PREVIEW_COLOR for ln in plot.axes.get_lines()))

    # A preview for a specimen this plot does not show is ignored.
    other = object()
    plot.set_preview(other, x, y, True)
    check("plot: preview ignored for an unshown specimen", plot._preview is None)


def check_plot_preserves_zoom():
    project = fresh_project()
    spec = next(s for s in project.specimens if s.has_experimental_data)
    plot = PatternPlot([spec], project)
    plot.axes.set_xlim(10.0, 20.0)
    plot.axes.set_ylim(0.0, 5.0)
    x, y = spec.experimental_pattern
    plot.set_preview(spec, x, y, True)
    check("plot: preview preserves the user's zoom",
          plot.axes.get_xlim() == (10.0, 20.0) and plot.axes.get_ylim() == (0.0, 5.0))
    plot.clear_preview()
    check("plot: clear preserves the user's zoom",
          plot.axes.get_xlim() == (10.0, 20.0))


def main():
    check_preview_methods()
    check_plot_overlay()
    check_plot_preserves_zoom()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- data-op preview overlay verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
