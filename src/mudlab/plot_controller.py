"""The main pattern plot: mudlab-style single-axes plotting for one or
more specimens, plus the old MainPlotController's interactions.

Drawing is ported from the old plot_specimens (generic/plot/plotters.py):
all selected specimens share ONE axes, stacked vertically by the project
display settings (display_plot_offset per display_group_by group), with
Y-scale normalization (axes_ynormalize: multi / single / raw counts),
per-specimen vshift/vscale, and specimen-name labels in the left margin
at display_label_pos. A single selection is simply the N=1 case.

Interactions (old generic/plot/controllers.py):
- scroll: zoom 2θ around the cursor (x >= 0, never wider than home view)
- Ctrl+scroll: zoom intensity around the cursor (y >= 0, clamped to home)
- Shift+scroll: pan 2θ by 10% of the visible span (clamped to home)
- left / right arrow keys: pan (canvas takes focus on click)
- right-click: reset to the home (full) view
- crosshair cursor (toggle) + left-drag measurement highlight
- motion/click callbacks for the status readout and point sampling
"""

from __future__ import annotations

import time
from typing import Callable

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QSizePolicy

from mudlab.chart_style import INK_MUTED, INK_PRIMARY, INK_SECONDARY, SURFACE, style_axes
from mudlab.models import Project, Specimen

PLOT_MIN_HEIGHT = 340

ZOOM_FACTOR = 1.15  # old on_scroll factor
PAN_FRACTION = 0.1  # old _pan_x step: 10% of the visible span

CROSSHAIR_COLOR = "#555555"
HIGHLIGHT_COLOR = "#FF6600"


def _max_display_y(specimen: Specimen) -> float:
    """Old Specimen.max_display_y: max intensity over both patterns."""
    peak = 0.0
    if specimen.has_experimental_data:
        peak = max(peak, float(np.max(specimen.experimental_pattern[1])))
    if specimen.has_calculated_data:
        peak = max(peak, float(np.max(specimen.calculated_pattern[1])))
    return peak


class PatternPlot:
    """One canvas, one axes, one or more specimens (mudlab style)."""

    def __init__(
        self,
        specimens: list[Specimen],
        project: Project,
        on_motion: Callable | None = None,
        on_click: Callable | None = None,
        on_marker_pick: Callable | None = None,
    ) -> None:
        if not specimens:
            raise ValueError("PatternPlot needs at least one specimen")
        self.specimens = list(specimens)
        self.project = project
        self._on_motion = on_motion
        self._on_click = on_click
        self._on_marker_pick = on_marker_pick

        self.figure = Figure(facecolor=SURFACE)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(PLOT_MIN_HEIGHT)
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        # Old canvas had set_can_focus(True): needed for arrow-key panning.
        self.canvas.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.axes = self.figure.add_subplot(111)

        self._crosshair_enabled = False
        self._crosshair_line = None
        self.drag_start_x: float | None = None
        self._drag_source_lines: list[tuple[np.ndarray, np.ndarray]] = []
        self._drag_highlight_lines: list = []
        self._home_xlim: tuple[float, float] | None = None
        self._home_ylim: tuple[float, float] | None = None
        # Marker artist -> Marker, for double-click picking (old ClickCatcher).
        self._marker_artists: dict = {}
        self._last_pick_artist = None
        self._last_pick_time = 0.0

        self.draw_pattern()

        self.canvas.mpl_connect("motion_notify_event", self._on_motion_event)
        self.canvas.mpl_connect("figure_leave_event", self._on_leave_event)
        self.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.canvas.mpl_connect("button_press_event", self._on_button_press)
        self.canvas.mpl_connect("button_release_event", self._on_button_release)
        self.canvas.mpl_connect("key_press_event", self._on_key_press)
        self.canvas.mpl_connect("pick_event", self._on_pick)

    def set_pick_cursor(self, enabled: bool) -> None:
        """Show a crosshair cursor while an eye-dropper pick is armed."""
        if enabled:
            self.canvas.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.canvas.unsetCursor()

    @property
    def specimen(self) -> Specimen:
        """The first specimen: the old multi readout used its goniometer."""
        return self.specimens[0]

    @property
    def multi(self) -> bool:
        return len(self.specimens) > 1

    @property
    def view_key(self):
        """Key identifying what this plot shows (for zoom preservation)."""
        return tuple(self.specimens)

    # ------------------------------------------------------------------
    # Drawing (old plot_specimens)
    # ------------------------------------------------------------------
    def draw_pattern(self) -> None:
        project = self.project
        axes = self.axes
        axes.clear()
        self._crosshair_line = None
        self._drag_highlight_lines = []
        self._marker_artists = {}
        self.figure.subplots_adjust(left=0.18, right=0.97, top=0.96, bottom=0.10)

        # Old Project.get_scale_factor():
        max_all = max((_max_display_y(s) for s in self.specimens), default=0.0)
        ynormalize = project.axes_ynormalize
        if ynormalize == 2:  # Unchanged raw counts
            scale, scale_unit = 1.0, (max_all or 1.0)
        else:  # 0 = Multi normalised (1 = Single normalised: per specimen)
            scale, scale_unit = 1.0 / (max_all or 1.0), 1.0

        base_offset = project.display_plot_offset
        label_offset = project.display_label_pos
        group_by = max(1, int(project.display_group_by))

        current_y_pos = 0.0
        group_counter = 0
        ylim_top = scale_unit
        lines = 0
        marker_specs: list[tuple] = []

        for specimen in self.specimens:
            spec_max = _max_display_y(specimen)
            spec_scale = (
                (1.0 / spec_max) if (ynormalize == 1 and spec_max != 0.0) else scale
            ) * specimen.display_vscale
            spec_y_pos = (current_y_pos + specimen.display_vshift) * scale_unit

            if specimen.display_experimental and specimen.has_experimental_data:
                x, y = specimen.experimental_pattern
                axes.plot(
                    x, y * spec_scale + spec_y_pos,
                    color=project.display_exp_color,
                    linewidth=project.display_exp_lw,
                    linestyle=project.display_exp_ls or "None",
                    marker=project.display_exp_marker or "",
                    markersize=3,
                )
                lines += 1
            if specimen.display_calculated and specimen.has_calculated_data:
                x, y = specimen.calculated_pattern
                axes.plot(
                    x, y * spec_scale + spec_y_pos,
                    color=project.display_calc_color,
                    linewidth=project.display_calc_lw,
                    linestyle=project.display_calc_ls or "None",
                    marker=project.display_calc_marker or "",
                    markersize=3,
                )
                lines += 1

            # Old plot_label: specimen name in the left margin, right
            # aligned, y in data coordinates at the label position.
            axes.text(
                -0.02,
                (current_y_pos + label_offset + specimen.display_vshift) * scale_unit,
                specimen.name,
                transform=axes.get_yaxis_transform(),
                ha="right", va="center", clip_on=False,
                color=INK_PRIMARY, fontsize="medium",
            )

            for marker in specimen.markers:
                marker_specs.append(
                    (marker, specimen, spec_scale, spec_y_pos, scale_unit)
                )

            ylim_top = current_y_pos * scale_unit + scale_unit
            group_counter += 1
            if group_counter >= group_by:
                group_counter = 0
                current_y_pos += base_offset

        # Old update_axes: manual or automatic x-limits; tight y from stack.
        if project.axes_xlimit == 1:
            xlim = (project.axes_xmin, project.axes_xmax)
        else:
            x_bounds = [
                (float(np.min(x)), float(np.max(x)))
                for s in self.specimens
                for x, _y in (s.experimental_pattern, s.calculated_pattern)
                if x.size > 1
            ]
            if x_bounds:
                xlim = (min(b[0] for b in x_bounds), max(b[1] for b in x_bounds))
            else:
                xlim = (0.0, 70.0)

        style_axes(axes)
        axes.set_xlim(xlim)
        axes.set_ylim(0.0, ylim_top)
        axes.set_xlabel("2θ (°)", color=INK_SECONDARY)
        axes.yaxis.set_visible(bool(project.axes_yvisible))
        if not project.axes_yvisible:
            axes.spines["left"].set_visible(False)
            axes.grid(False, axis="y")

        # Markers, once the y-range is fixed (top-of-plot markers need it).
        for spec in marker_specs:
            self._draw_marker(*spec, xlim=xlim, y_top=ylim_top)

        if lines == 0:
            axes.text(
                0.5, 0.5, "No pattern data",
                transform=axes.transAxes, ha="center", va="center",
                color=INK_MUTED,
            )

        self._home_xlim = axes.get_xlim()
        self._home_ylim = axes.get_ylim()
        # Old controller (controllers.py:108): the axes never autoscale, so
        # crosshair/highlight artists can never alter the view ranges.
        axes.set_autoscale_on(False)

    # matplotlib line styles by marker style value (none/offset draw no line).
    _MARKER_LINE_STYLES = {
        "solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-.",
    }

    def _plotted_y(self, specimen, position, scale, y_pos, pattern) -> float:
        x, y = pattern
        if x.size < 2:
            return y_pos
        return float(np.interp(position, x, y)) * scale + y_pos

    def _draw_marker(self, marker, specimen, scale, y_pos, unit, xlim, y_top) -> None:
        """Port of the old plot_marker_line + plot_marker_text."""
        if not marker.visible:
            return
        position = marker.position
        # Old within_range: honor manual x-limits.
        if self.project.axes_xlimit == 1 and not (xlim[0] <= position <= xlim[1]):
            return

        # base_y: where the connector starts (old plot_markers).
        base = marker.effective_base
        if base == 1:
            base_y = self._plotted_y(specimen, position, scale, y_pos,
                                     specimen.experimental_pattern)
        elif base == 2:
            base_y = self._plotted_y(specimen, position, scale, y_pos,
                                     specimen.calculated_pattern)
        elif base in (3, 4):
            exp = self._plotted_y(specimen, position, scale, y_pos,
                                  specimen.experimental_pattern)
            calc = self._plotted_y(specimen, position, scale, y_pos,
                                   specimen.calculated_pattern)
            base_y = min(exp, calc) if base == 3 else max(exp, calc)
        else:  # 0 = X-axis (specimen baseline)
            base_y = y_pos

        color = marker.effective_color
        style = marker.effective_style
        top = marker.effective_top
        top_offset = marker.effective_top_offset

        # Connector line (skipped for 'none'/'offset').
        line_style = self._MARKER_LINE_STYLES.get(style)
        if line_style is not None:
            y1 = y_top if top == 1 else base_y + top_offset * unit
            line, = self.axes.plot(
                [position, position], [base_y, y1],
                color=color, linestyle=line_style, linewidth=1.0, zorder=8,
            )
            self._register_marker_artist(line, marker)

        # Label text (skipped for 'offset'); rotated like the old app.
        if style != "offset":
            text = marker.anno_label or marker.label
            if top == 1:
                y_text = y_top * 0.98 + marker.y_offset * unit
            else:
                y_text = base_y + (top_offset + marker.y_offset) * unit
            label_artist = self.axes.text(
                position + marker.x_offset, y_text, text,
                rotation=90 - marker.effective_angle, rotation_mode="anchor",
                ha=marker.effective_align, va="center",
                color=color, clip_on=True, zorder=9, fontsize="small",
            )
            self._register_marker_artist(label_artist, marker)

    def _register_marker_artist(self, artist, marker) -> None:
        # Only pickable when a selection handler is wired (old ClickCatcher).
        if self._on_marker_pick is not None:
            artist.set_picker(True)
            self._marker_artists[artist] = marker

    def _on_pick(self, event) -> None:
        """Double-click a marker line/label to select it (old ClickCatcher)."""
        marker = self._marker_artists.get(event.artist)
        if marker is None:
            return
        now = time.monotonic()
        is_double = getattr(event.mouseevent, "dblclick", False) or (
            event.artist is self._last_pick_artist
            and (now - self._last_pick_time) <= 0.5
        )
        if is_double:
            self._last_pick_artist = None
            self._last_pick_time = 0.0
            if self._on_marker_pick is not None:
                self._on_marker_pick(marker)
        else:
            self._last_pick_artist = event.artist
            self._last_pick_time = now

    # ------------------------------------------------------------------
    # View state (zoom preservation across redraws, old update() logic)
    # ------------------------------------------------------------------
    def user_view(self) -> tuple | None:
        """Current (xlim, ylim) if the user zoomed/panned, else None."""
        if self._home_xlim is None:
            return None
        xlim, ylim = self.axes.get_xlim(), self.axes.get_ylim()
        if xlim != self._home_xlim or ylim != self._home_ylim:
            return (xlim, ylim)
        return None

    def restore_view(self, view: tuple) -> None:
        xlim, ylim = view
        self.axes.set_xlim(xlim)
        self.axes.set_ylim(ylim)
        self.canvas.draw_idle()

    def reset_view(self) -> None:
        if self._home_xlim is not None:
            self.axes.set_xlim(self._home_xlim)
            self.axes.set_ylim(self._home_ylim)
            self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Zoom & pan (old on_scroll / _pan_x semantics)
    # ------------------------------------------------------------------
    def zoom_x(self, factor: float, center: float | None = None) -> None:
        xmin, xmax = self.axes.get_xlim()
        cx = center if center is not None else (xmin + xmax) / 2.0
        new_xmin = max(0.0, cx - (cx - xmin) * factor)
        new_xmax = cx + (xmax - cx) * factor
        if self._home_xlim is not None:
            home_min, home_max = self._home_xlim
            if new_xmax - new_xmin >= home_max - home_min:
                new_xmin, new_xmax = home_min, home_max
        self.axes.set_xlim(new_xmin, new_xmax)
        self.canvas.draw_idle()

    def zoom_y(self, factor: float, center: float | None = None) -> None:
        ymin, ymax = self.axes.get_ylim()
        cy = center if center is not None else (ymin + ymax) / 2.0
        new_ymin = max(0.0, cy - (cy - ymin) * factor)
        new_ymax = cy + (ymax - cy) * factor
        if self._home_ylim is not None:
            home_min, home_max = self._home_ylim
            if new_ymax - new_ymin >= home_max - home_min:
                new_ymin, new_ymax = home_min, home_max
        self.axes.set_ylim(new_ymin, new_ymax)
        self.canvas.draw_idle()

    def pan_x(self, direction: int) -> None:
        """Pan by 10% of the visible span; +1 = right, -1 = left."""
        xmin, xmax = self.axes.get_xlim()
        span = xmax - xmin
        new_xmin = xmin + span * PAN_FRACTION * direction
        if self._home_xlim is not None:
            home_min, home_max = self._home_xlim
            new_xmin = max(home_min, min(new_xmin, home_max - span))
        self.axes.set_xlim(new_xmin, new_xmin + span)
        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Crosshair cursor
    # ------------------------------------------------------------------
    def set_crosshair_enabled(self, enabled: bool) -> None:
        self._crosshair_enabled = enabled
        if not enabled:
            if self.drag_start_x is not None:
                self._end_drag_highlight()
            if self._crosshair_line is not None:
                self._crosshair_line.remove()
                self._crosshair_line = None
                self.canvas.draw_idle()

    def _update_crosshair(self, x_pos: float) -> None:
        if not self._crosshair_enabled:
            return
        if x_pos < 0:
            if self._crosshair_line is not None:
                self._crosshair_line.set_visible(False)
                self.canvas.draw_idle()
            return
        if self._crosshair_line is None:
            self._crosshair_line = self.axes.axvline(
                x=x_pos, color=CROSSHAIR_COLOR, linewidth=0.8,
                linestyle="--", zorder=1000,
            )
        else:
            self._crosshair_line.set_xdata([x_pos, x_pos])
            self._crosshair_line.set_visible(True)
        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Drag-measurement highlight
    # ------------------------------------------------------------------
    def _start_drag_highlight(self, x_pos: float | None) -> None:
        if not self._crosshair_enabled or x_pos is None:
            return
        self.drag_start_x = x_pos
        self._drag_source_lines = []
        skip = set(self._drag_highlight_lines)
        if self._crosshair_line is not None:
            skip.add(self._crosshair_line)
        for line in self.axes.get_lines():
            if line in skip:
                continue
            xd = np.asarray(line.get_xdata())
            yd = np.asarray(line.get_ydata())
            if len(xd) > 1:
                self._drag_source_lines.append((xd, yd))

    def _update_drag_highlight(self, x_pos: float) -> None:
        if self.drag_start_x is None:
            return
        x0 = min(self.drag_start_x, x_pos)
        x1 = max(self.drag_start_x, x_pos)
        for i, (xd, yd) in enumerate(self._drag_source_lines):
            mask = (xd >= x0) & (xd <= x1)
            seg_x, seg_y = xd[mask], yd[mask]
            if i < len(self._drag_highlight_lines):
                self._drag_highlight_lines[i].set_data(seg_x, seg_y)
                self._drag_highlight_lines[i].set_visible(len(seg_x) > 0)
            else:
                highlight, = self.axes.plot(
                    seg_x, seg_y,
                    color=HIGHLIGHT_COLOR, linewidth=3.0, alpha=0.45, zorder=999,
                )
                self._drag_highlight_lines.append(highlight)
        for j in range(len(self._drag_source_lines), len(self._drag_highlight_lines)):
            self._drag_highlight_lines[j].set_visible(False)
        self.canvas.draw_idle()

    def _end_drag_highlight(self) -> None:
        for highlight in self._drag_highlight_lines:
            highlight.remove()
        self._drag_highlight_lines = []
        self.drag_start_x = None
        self._drag_source_lines = []
        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Matplotlib event handlers
    # ------------------------------------------------------------------
    def _event_x(self, event) -> float:
        if event.inaxes is self.axes and event.xdata is not None:
            return float(event.xdata)
        return -1.0

    def _on_motion_event(self, event) -> None:
        x_pos = self._event_x(event)
        self._update_crosshair(x_pos)
        if self.drag_start_x is not None and x_pos >= 0:
            self._update_drag_highlight(x_pos)
        if self._on_motion is not None:
            self._on_motion(self, x_pos)

    def _on_leave_event(self, _event) -> None:
        self._update_crosshair(-1.0)
        if self._on_motion is not None:
            self._on_motion(self, -1.0)

    def _on_scroll(self, event) -> None:
        if event.inaxes is not self.axes:
            return
        # Like the old controller (which read GDK state directly because
        # event.key was unreliable), read the modifiers from Qt.
        modifiers = QGuiApplication.keyboardModifiers()
        ctrl_held = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        shift_held = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

        factor = ZOOM_FACTOR if event.button == "down" else 1.0 / ZOOM_FACTOR
        if ctrl_held:
            self.zoom_y(factor, center=event.ydata)
        elif shift_held:
            self.pan_x(1 if event.button == "down" else -1)
        else:
            self.zoom_x(factor, center=event.xdata)

    def _on_button_press(self, event) -> None:
        if event.button == 1 and event.inaxes is self.axes and not event.dblclick:
            if self._on_click is not None:
                self._on_click(self, self._event_x(event))
            self._start_drag_highlight(event.xdata)
        elif event.button == 3 and event.inaxes is self.axes:
            self.reset_view()

    def _on_button_release(self, event) -> None:
        if event.button == 1 and self.drag_start_x is not None:
            self._end_drag_highlight()
            if self._on_motion is not None:
                x_pos = self._event_x(event)
                # Deferred, like the old GLib.idle_add refresh.
                QTimer.singleShot(0, lambda: self._on_motion(self, x_pos))

    def _on_key_press(self, event) -> None:
        if event.key == "left":
            self.pan_x(-1)
        elif event.key == "right":
            self.pan_x(+1)
