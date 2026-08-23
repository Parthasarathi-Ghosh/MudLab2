#!/usr/bin/env python
"""Main pattern plot: no grid, a tick per degree, and the specimen text moved
into the upper-right index.

Three changes requested 2026-08-23:

  a) the background grid is gone - but ONLY here. `chart_style.style_axes`
     switches a grid on for every chart in the app and seven other dialogs
     share it, so the pattern plot turns its own off after styling rather than
     changing the shared helper;
  b) a tick every degree. Every degree gets a MINOR tick; the LABELLED (major)
     step adapts (1, 2, 5, 10, 20) so a 70-degree scan does not print 70
     overlapping numbers, and resolves to 1 when zoomed in;
  c) the specimen name and its Rp / Rwp / GoF, which used to be drawn in the
     left margin at `display_label_pos`, are now the first entries of the
     upper-right index, ahead of the mixture blocks - and the plot takes back
     the 18% of figure width that margin reserved.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_plot_axes_index.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no usable sample project.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from matplotlib.offsetbox import AnchoredOffsetbox, TextArea  # noqa: E402
from matplotlib.ticker import MultipleLocator  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.chart_style import SURFACE  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.plot_controller import PatternPlot  # noqa: E402

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in sorted(glob.glob(os.path.join(
            _REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        if any(s is not None and s.has_experimental_data
               for s in project.specimens):
            return path
    return None


PATH = _fixture()
if PATH is None:
    print("No sample project with pattern data; skipping (exit 2).")
    raise SystemExit(2)

PROJECT = load_mud(PATH)
SPECIMENS = [s for s in PROJECT.specimens
             if s is not None and s.has_experimental_data]


def _index_of(plot):
    for artist in plot.axes.get_children():
        if isinstance(artist, AnchoredOffsetbox):
            return artist
    return None


def _texts(box):
    """Every TextArea string, IN DRAWN ORDER.

    Order matters here - two checks below are about it - so this is an ordered
    depth-first walk. A stack-based walk pops last-in-first-out and returns the
    children reversed, which silently made the ordering checks meaningless.
    """
    found = []

    def walk(node):
        if isinstance(node, TextArea):
            found.append(node.get_text())
            return
        kids = getattr(node, "get_children", None)
        if callable(kids):
            for kid in kids():
                walk(kid)
            return
        child = getattr(node, "get_child", None)
        if callable(child):
            kid = child()
            if kid is not None:
                walk(kid)

    walk(box)
    return found


def main():
    plot = PatternPlot(SPECIMENS, PROJECT)
    axes = plot.axes

    # ------------------------------------------------------------ (a) grid
    check("grid: no x gridlines", not axes.xaxis._major_tick_kw.get("gridOn"))
    check("grid: no y gridlines", not axes.yaxis._major_tick_kw.get("gridOn"))
    check("grid: no gridline is actually drawn",
          not any(line.get_visible() for line in
                  axes.get_xgridlines() + axes.get_ygridlines()))
    # The shared helper must be untouched - other charts still want a grid.
    import matplotlib.pyplot as plt

    from mudlab.chart_style import style_axes
    other = plt.figure().add_subplot(111)
    style_axes(other)
    check("grid: style_axes STILL grids other charts (helper untouched)",
          other.xaxis._major_tick_kw.get("gridOn"))
    plt.close(other.figure)

    # ------------------------------------------------------------ (b) ticks
    minor = axes.xaxis.get_minor_locator()
    major = axes.xaxis.get_major_locator()
    check("ticks: minor locator is a fixed step", isinstance(minor, MultipleLocator))
    check("ticks: major locator is a fixed step", isinstance(major, MultipleLocator))
    minor_positions = minor()
    steps = {round(b - a, 6) for a, b in zip(minor_positions, minor_positions[1:])}
    check("ticks: a MINOR tick every 1 degree", steps == {1.0})
    lo, hi = axes.get_xlim()
    span = hi - lo
    check("ticks: minor ticks span the axis (%d over %.0f deg)"
          % (len(minor_positions), span), len(minor_positions) >= int(span) - 1)
    major_positions = major()
    major_steps = {round(b - a, 6)
                   for a, b in zip(major_positions, major_positions[1:])}
    check("ticks: labelled step is one of 1/2/5/10/20",
          major_steps and major_steps.pop() in (1.0, 2.0, 5.0, 10.0, 20.0))
    check("ticks: labels are thinned, not one per degree on a wide scan",
          len(major_positions) < len(minor_positions))
    check("ticks: minor ticks are shorter than major",
          axes.xaxis.get_minor_ticks()[0].tick1line.get_markersize()
          < axes.xaxis.get_major_ticks()[0].tick1line.get_markersize())

    # A zoomed-in span must resolve to a labelled tick PER DEGREE.
    plot.axes.set_xlim(20.0, 28.0)
    plot._set_degree_ticks(plot.axes, (20.0, 28.0))
    zoom_major = plot.axes.xaxis.get_major_locator()()
    zsteps = {round(b - a, 6) for a, b in zip(zoom_major, zoom_major[1:])}
    check("ticks: an 8-degree span labels every degree", zsteps == {1.0})

    # -------------------------------------------------- (c) text in the index
    plot2 = PatternPlot(SPECIMENS, PROJECT)
    index = _index_of(plot2)
    check("index: an index is drawn", index is not None)
    texts = _texts(index) if index is not None else []
    for specimen in SPECIMENS:
        check("index: names %r" % (specimen.name,), specimen.name in texts)

    # ...and nothing is left in the left margin.
    margin_texts = [
        artist.get_text() for artist in plot2.axes.texts
        if artist.get_position()[0] < 0
    ]
    check("index: the left margin holds no specimen text any more",
          not margin_texts)

    # Specimen entries come BEFORE the mixture blocks.
    mixture_names = [m.name for m in PROJECT.mixtures
                     if any(s in m.specimens for s in SPECIMENS)]
    if mixture_names and texts:
        first_mixture = min(texts.index(n) for n in mixture_names if n in texts)
        last_specimen = max(texts.index(s.name) for s in SPECIMENS
                            if s.name in texts)
        check("index: specimen entries precede the mixture blocks",
              last_specimen < first_mixture)
    else:
        check("index: (no mixture on show; ordering check skipped)", True)

    # Top-of-plot first: the stack draws specimens[0] at the BOTTOM, so the
    # index must list them reversed or the list reads against the picture.
    if len(SPECIMENS) > 1:
        positions = [texts.index(s.name) for s in SPECIMENS if s.name in texts]
        check("index: listed top-of-plot first (reverse of stacking order)",
              positions == sorted(positions, reverse=True))
    else:
        check("index: (single specimen; ordering check skipped)", True)

    # Statistics ride along only when the specimen asks for them.
    with_stats = next((s for s in SPECIMENS if s.statistics.has_data), None)
    if with_stats is not None:
        # The flag is persisted, so the fixture may already have it on for some
        # specimens - clear them all for the "off" case.
        was = {id(s): s.display_stats_in_lbl for s in SPECIMENS}
        for s in SPECIMENS:
            s.display_stats_in_lbl = False
        plot3 = PatternPlot(SPECIMENS, PROJECT)
        off = _texts(_index_of(plot3))
        check("index: no Rp/Rwp/GoF while display_stats_in_lbl is off",
              not any(t.startswith("Rp =") for t in off))
        with_stats.display_stats_in_lbl = True
        plot4 = PatternPlot(SPECIMENS, PROJECT)
        on = _texts(_index_of(plot4))
        check("index: Rp / Rwp / GoF appear when it is on",
              any(t.startswith("Rp =") for t in on)
              and any(t.startswith("Rwp =") for t in on)
              and any(t.startswith("GoF =") for t in on))
        for s in SPECIMENS:
            s.display_stats_in_lbl = was[id(s)]
    else:
        check("index: (no specimen with statistics; skipped)", True)

    # The index must be READABLE over the curves it now overlaps.
    from matplotlib.colors import to_rgb
    face = index.patch.get_facecolor()
    check("index: backed by an opaque-ish panel, not bare text",
          index.patch.get_visible()
          and all(abs(a - b) < 1e-6 for a, b in zip(face[:3], to_rgb(SURFACE)))
          and index.patch.get_alpha() >= 0.85)

    # ------------------------------------------------- (c) reclaimed margin
    check("margin: the 18% left reservation is gone",
          plot2.figure.subplotpars.left < 0.12)
    PROJECT.axes_yvisible = True
    plot5 = PatternPlot(SPECIMENS, PROJECT)
    check("margin: a visible y axis still gets room for its labels",
          plot5.figure.subplotpars.left > plot2.figure.subplotpars.left)
    PROJECT.axes_yvisible = False

    # It all has to actually render.
    try:
        plot2.canvas.draw()
        drew = True
    except Exception as exc:  # pragma: no cover
        print("  draw() raised:", exc)
        drew = False
    check("the figure renders", drew)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Pattern-plot axes + index:", os.path.basename(PATH))
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
