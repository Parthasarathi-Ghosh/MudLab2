"""Shared Matplotlib chart styling (validated light-mode palette + typeface)."""

from __future__ import annotations

import matplotlib
from matplotlib.axes import Axes

#: The interface font, so a chart and the window around it are set in the same
#: typeface. Without this matplotlib draws in its own bundled DejaVu Sans while
#: every widget is in Segoe UI - two faces in one window, which reads as a
#: mistake even to someone who cannot name it.
#:
#: DejaVu Sans is KEPT as the fallback, and deliberately last: it ships inside
#: matplotlib, so a machine that somehow lacks the Windows UI fonts still draws
#: charts rather than failing. Matplotlib walks this list itself.
UI_FONT = "Segoe UI"
_FONT_STACK = [UI_FONT, "Segoe UI Variable", "Calibri", "Arial",
               "DejaVu Sans"]

def apply_chart_font() -> None:
    """Point matplotlib at the interface font.

    Called from `create_app`, so it does not matter which chart module happens
    to be imported first. It ALSO runs at import of this module, because the
    verification harnesses build charts without ever creating the application -
    but an import side effect is not something to rely on: `refinement_dialog`
    draws the convergence plot and does not import this module, and its text
    would have stayed in DejaVu Sans while every other chart moved.
    """
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = list(_FONT_STACK)


apply_chart_font()

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES_BLUE = "#2a78d6"


def style_axes(axes: Axes) -> None:
    """Apply the standard MudLab chart styling to a Matplotlib axes."""
    axes.set_facecolor(SURFACE)
    axes.tick_params(colors=INK_MUTED)
    axes.grid(True, color=GRIDLINE, linewidth=0.8)
    axes.set_axisbelow(True)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(BASELINE)
