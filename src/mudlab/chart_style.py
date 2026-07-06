"""Shared Matplotlib chart styling (validated light-mode palette)."""

from __future__ import annotations

from matplotlib.axes import Axes

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
