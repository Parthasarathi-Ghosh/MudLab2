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
from matplotlib.offsetbox import (
    AnchoredOffsetbox,
    AuxTransformBox,
    HPacker,
    TextArea,
    VPacker,
)
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import MultipleLocator
from matplotlib.transforms import Bbox, IdentityTransform
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QSizePolicy

from mudlab.chart_style import (
    GRIDLINE,
    INK_MUTED,
    INK_PRIMARY,
    INK_SECONDARY,
    SURFACE,
    style_axes,
)
from mudlab.models import Project, Specimen

PLOT_MIN_HEIGHT = 340

ZOOM_FACTOR = 1.15  # old on_scroll factor
PAN_FRACTION = 0.1  # old _pan_x step: 10% of the visible span

CROSSHAIR_COLOR = "#555555"
HIGHLIGHT_COLOR = "#FF6600"
RESIDUAL_COLOR = "#7048a8"  # difference-curve violet (Rietveld convention)
PREVIEW_COLOR = "#E8590C"  # live data-op preview (warm orange, over the original)
MINERAL_PREVIEW_COLOR = "#D6336C"  # Match Minerals reference-peak sticks (magenta)
SHIFT_REFERENCE_COLOR = "#1098AD"  # Shift dialog's fixed reference-position line (teal)


def _max_display_y(specimen: Specimen) -> float:
    """Old Specimen.max_display_y: max intensity over both patterns."""
    peak = 0.0
    if specimen.has_experimental_data:
        peak = max(peak, float(np.max(specimen.experimental_pattern[1])))
    if specimen.has_calculated_data:
        peak = max(peak, float(np.max(specimen.calculated_pattern[1])))
    return peak


def save_figure(figure, canvas, filename: str, dpi: float,
                i_width: float, i_height: float) -> None:
    """Export `figure` to `filename` (.png / .pdf / .svg / other bitmaps) at the
    given inch size and dpi, restoring the on-screen size and dpi afterwards.

    Port of the old plot_controller.save_figure. Module-level rather than a
    PatternPlot method because the Composition dialog's chart is a plain Figure
    and needs the identical behaviour - in particular the `finally` that puts
    the interactive size back even when saving fails, which is easy to omit in a
    second copy.

    dpi is ignored for the vector formats, where it means nothing.
    """
    is_vector = filename.lower().endswith((".svg", ".pdf"))
    original_dpi = figure.get_dpi()
    original_size = figure.get_size_inches()
    figure.set_size_inches((i_width, i_height))
    if not is_vector:
        figure.set_dpi(dpi)
    canvas.draw()
    bbox = Bbox.from_bounds(0, 0, i_width, i_height)
    save_kwargs = {"bbox_inches": bbox}
    if not is_vector:
        save_kwargs["dpi"] = dpi
    if filename.lower().endswith((".tif", ".tiff")):
        # Matplotlib writes TIFF UNCOMPRESSED. At the size dialog's default
        # 8000x4800 that is 153 MB for a chart a compressed PNG stores in
        # ~340 KB. LZW is lossless and universally readable, so nothing is
        # given up for the ~10x saving. (Journals often ask for TIFF, which is
        # why the format is offered at all.)
        save_kwargs["pil_kwargs"] = {"compression": "tiff_lzw"}
    try:
        figure.savefig(filename, **save_kwargs)
    finally:
        # Always restore the interactive size/dpi, even if saving failed.
        figure.set_dpi(original_dpi)
        figure.set_size_inches(original_size)
        canvas.draw()


class PatternPlot:
    """One canvas, one axes, one or more specimens (mudlab style)."""

    def __init__(
        self,
        specimens: list[Specimen],
        project: Project,
        on_motion: Callable | None = None,
        on_click: Callable | None = None,
        on_marker_pick: Callable | None = None,
        on_range_select: Callable | None = None,
    ) -> None:
        if not specimens:
            raise ValueError("PatternPlot needs at least one specimen")
        self.specimens = list(specimens)
        self.project = project
        self._on_motion = on_motion
        self._on_click = on_click
        self._on_marker_pick = on_marker_pick
        self._on_range_select = on_range_select

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
        # Range-select mode (Strip Peak / Peak Properties): reuses the crosshair
        # drag-highlight to sweep a [start, end] range, reported on release.
        self._range_select_enabled = False
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
        # Live data-op preview overlay (see set_preview): the result a data-op
        # dialog would apply, drawn over the original while the dialog is open.
        self._preview: dict | None = None
        # Shift dialog's fixed reference line (a 2theta position, degrees), drawn
        # as a dotted vertical line while that dialog is open (see draw_pattern).
        self._shift_reference: float | None = None

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

    # ------------------------------------------------------------------
    # Live data-op preview overlay
    # ------------------------------------------------------------------
    def set_preview(self, specimen, x, y, show_original: bool = True) -> None:
        """Overlay a data-op preview curve ``(x, y)`` (intensity units) for
        `specimen`, drawn in that specimen's plot coordinates. `show_original`
        keeps the specimen's original experimental line visible under it;
        otherwise only the preview shows. Redraws, preserving any user zoom."""
        if specimen not in self.specimens or x is None or len(x) < 2:
            return
        self._preview = {
            "specimen": specimen,
            "x": np.asarray(x, dtype=float),
            "y": np.asarray(y, dtype=float),
            "show_original": show_original,
        }
        self._redraw_keep_view()

    def clear_preview(self) -> None:
        if self._preview is not None:
            self._preview = None
            self._redraw_keep_view()

    def set_shift_reference(self, position: float) -> None:
        """Show a fixed dotted vertical line at `position` (2theta, degrees) -
        the Shift dialog's reference reflection, which the user aligns the
        shifted peak onto. Redraws, preserving any user zoom."""
        self._shift_reference = float(position)
        self._redraw_keep_view()

    def clear_shift_reference(self) -> None:
        if self._shift_reference is not None:
            self._shift_reference = None
            self._redraw_keep_view()

    def refresh(self) -> None:
        """Redraw the current content in place (no rebuild), preserving zoom.
        Reads specimen.mineral_preview + plot._preview, so an overlay update
        never discards the other overlay or the user's zoom."""
        self._redraw_keep_view()

    def save_figure(self, filename: str, dpi: float,
                    i_width: float, i_height: float) -> None:
        """Export the plot to `filename` (.png / .pdf / .svg) at the given inch
        size and dpi. See the module-level `save_figure`, which the Composition
        dialog's plot shares."""
        save_figure(self.figure, self.canvas, filename, dpi, i_width, i_height)

    def _redraw_keep_view(self) -> None:
        view = self.user_view()  # the user's zoom, if any (None = home view)
        self.draw_pattern()
        if view is not None:
            self.axes.set_xlim(view[0])
            self.axes.set_ylim(view[1])
        self.canvas.draw_idle()

    def _preview_for(self, specimen) -> dict | None:
        if self._preview is not None and self._preview["specimen"] is specimen:
            return self._preview
        return None

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
        # The left margin used to reserve 18% of the figure for the specimen
        # name / Rp / Rwp / GoF text. That text now lives in the upper-right
        # index, so the plot takes the space back: just enough for the y tick
        # labels when the y axis is shown, and a hair otherwise.
        left = 0.10 if project.axes_yvisible else 0.045
        self.figure.subplots_adjust(left=left, right=0.97, top=0.96, bottom=0.10)

        # Old Project.get_scale_factor():
        max_all = max((_max_display_y(s) for s in self.specimens), default=0.0)
        ynormalize = project.axes_ynormalize
        if ynormalize == 2:  # Unchanged raw counts
            scale, scale_unit = 1.0, (max_all or 1.0)
        else:  # 0 = Multi normalised (1 = Single normalised: per specimen)
            scale, scale_unit = 1.0 / (max_all or 1.0), 1.0

        base_offset = project.display_plot_offset
        group_by = max(1, int(project.display_group_by))

        current_y_pos = 0.0
        group_counter = 0
        ylim_top = scale_unit
        lines = 0
        marker_specs: list[tuple] = []
        # (name, [stat lines]) per specimen, in stacking order (index 0 is the
        # BOTTOM of the plot); the index renders them top-first.
        specimen_entries: list[tuple] = []

        for specimen in self.specimens:
            spec_max = _max_display_y(specimen)
            spec_scale = (
                (1.0 / spec_max) if (ynormalize == 1 and spec_max != 0.0) else scale
            ) * specimen.display_vscale
            spec_y_pos = (current_y_pos + specimen.display_vshift) * scale_unit

            # Statistics band (old plot_specimens): when a calculated pattern
            # exists and residuals/derivatives are shown, the bottom 35% of
            # the specimen's slot holds the difference curve and the patterns
            # take the top 65%.
            spec_reqst_height = scale_unit * specimen.display_vscale
            show_stats_band = (
                specimen.display_calculated
                and specimen.has_calculated_data
                and (specimen.display_residuals or specimen.display_derivatives)
            )
            if show_stats_band:
                stats_height = 0.35 * spec_reqst_height
                self._draw_stats_band(
                    specimen, spec_scale * 0.65, spec_y_pos, stats_height
                )
                spec_y_pos = spec_y_pos + stats_height
                spec_scale = spec_scale * 0.65

            preview = self._preview_for(specimen)
            # The original experimental line is hidden only when a preview is
            # active AND its dialog asked to hide the original (Smooth's
            # "show original" off); otherwise it stays as the base reference.
            hide_original = preview is not None and not preview["show_original"]
            if (specimen.display_experimental and specimen.has_experimental_data
                    and not hide_original):
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
            if preview is not None:
                axes.plot(
                    preview["x"], preview["y"] * spec_scale + spec_y_pos,
                    color=PREVIEW_COLOR, linewidth=1.3, zorder=6,
                )
                lines += 1
            # Per-phase contributions (display_phases): each phase's calculated
            # curve in its own display_color, drawn under the total. Only when
            # the calculated pattern is shown (they are part of it).
            phase_patterns = getattr(specimen, "phase_patterns", None)
            if (specimen.display_phases and specimen.display_calculated
                    and specimen.has_calculated_data and phase_patterns):
                cx, _cy = specimen.calculated_pattern
                for phase, phase_y in phase_patterns:
                    phase_y = np.asarray(phase_y, dtype=float)
                    if phase_y.shape != cx.shape:
                        continue  # stale (grid changed); a recompute rebuilds it
                    # getattr guard: a phase-like without a colour must never
                    # blank the whole plot with an AttributeError (a raw phase
                    # used to lack display_color).
                    color = (getattr(phase, "display_color", None)
                             or project.display_calc_color)
                    axes.plot(
                        cx, phase_y * spec_scale + spec_y_pos,
                        color=color, linewidth=0.9, zorder=2,
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

            # Match Minerals reference-peak overlay: magenta sticks at each
            # reference reflection's 2theta, height = relative intensity scaled
            # to the specimen's strongest displayed reflection (old mineral
            # preview sticks).
            mineral_preview = getattr(specimen, "mineral_preview", None)
            peak_max = spec_max * spec_scale
            if mineral_preview and peak_max > 0:
                for position, rel_intensity in mineral_preview:
                    top = spec_y_pos + (rel_intensity / 100.0) * peak_max
                    axes.plot(
                        [position, position], [spec_y_pos, top],
                        color=MINERAL_PREVIEW_COLOR, linewidth=1.0, zorder=5,
                    )

            # The specimen name (and, with display_stats_in_lbl, its Rp / Rwp /
            # GoF) used to be drawn in the left margin at display_label_pos.
            # It is collected here and rendered in the upper-right index
            # instead - see _draw_plot_index.
            stats_lines = []
            if specimen.display_stats_in_lbl and specimen.statistics.has_data:
                st = specimen.statistics
                stats_lines = ["Rp = %.1f%%" % st.Rp,
                               "Rwp = %.1f%%" % st.Rwp,
                               "GoF = %.3f" % st.GoF]
            specimen_entries.append((specimen.name, stats_lines))

            for marker in specimen.markers:
                marker_specs.append(
                    (marker, specimen, spec_scale, spec_y_pos, scale_unit)
                )

            ylim_top = current_y_pos * scale_unit + scale_unit
            group_counter += 1
            if group_counter >= group_by:
                group_counter = 0
                current_y_pos += base_offset

        # Shade the excluded 2theta regions (light band behind the curves).
        # Full-height for simplicity - per-specimen vertical slots are not
        # distinguished, which is exact for a single specimen or shared ranges.
        shaded = set()
        for specimen in self.specimens:
            for x0, x1 in specimen.exclusion_ranges:
                lo, hi = round(min(x0, x1), 6), round(max(x0, x1), 6)
                if lo == hi or (lo, hi) in shaded:
                    continue
                shaded.add((lo, hi))
                axes.axvspan(lo, hi, color=INK_MUTED, alpha=0.15, linewidth=0, zorder=0)

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
        # No grid on the pattern plot. style_axes turns one on for every chart
        # in the app, so it is switched off HERE rather than there - the other
        # seven charts that share that helper still want theirs.
        axes.grid(False)
        axes.set_xlim(xlim)
        axes.set_ylim(0.0, ylim_top)
        axes.set_xlabel("2θ (°)", color=INK_SECONDARY)
        self._set_degree_ticks(axes, xlim)
        axes.yaxis.set_visible(bool(project.axes_yvisible))
        if not project.axes_yvisible:
            axes.spines["left"].set_visible(False)

        # Markers, once the y-range is fixed (top-of-plot markers need it).
        for spec in marker_specs:
            self._draw_marker(*spec, xlim=xlim, y_top=ylim_top)

        # Upper-right index: the specimen names + fit statistics that used to
        # sit in the left margin, then the mixtures on show.
        self._draw_plot_index(specimen_entries)

        # Shift dialog's reference line: a fixed dotted vertical at the target
        # 2theta, so the user can line the shifted peak up against it.
        if self._shift_reference is not None:
            axes.axvline(
                self._shift_reference, color=SHIFT_REFERENCE_COLOR,
                linestyle=":", linewidth=1.3, zorder=9,
            )

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

    # Label steps tried in order; the first whose labels fit is used.
    _LABEL_STEPS = (1, 2, 5, 10, 20)

    def _set_degree_ticks(self, axes, xlim) -> None:
        """A tick every degree on the 2-theta axis.

        Every degree gets a MINOR tick, which is the visible "tick per degree".
        Labelling every degree as well is not readable - a routine 4-70 deg scan
        would print 67 numbers into a few hundred pixels and they would overlap
        into a smear - so the LABELLED (major) step is the smallest of 1, 2, 5,
        10, 20 that leaves room for its labels at the current figure width. On a
        zoomed-in span that resolves to 1, and the labels really are per degree.
        """
        span = abs(float(xlim[1]) - float(xlim[0])) or 1.0
        # Width available to the axes, in points; ~28 pt per "70.0"-ish label
        # plus a gap is comfortable.
        width_px = max(self.figure.get_size_inches()[0], 1.0) * self.figure.dpi
        width_pt = width_px * 72.0 / self.figure.dpi
        axes_pt = width_pt * max(
            0.1, 1.0 - self.figure.subplotpars.left
            - (1.0 - self.figure.subplotpars.right))
        room_for = max(2.0, axes_pt / 28.0)

        step = self._LABEL_STEPS[-1]
        for candidate in self._LABEL_STEPS:
            if span / candidate <= room_for:
                step = candidate
                break
        axes.xaxis.set_major_locator(MultipleLocator(step))
        axes.xaxis.set_minor_locator(MultipleLocator(1))
        # Minor ticks are the per-degree marks: shorter, so the labelled ones
        # still read as the primary scale.
        axes.tick_params(axis="x", which="major", length=5)
        axes.tick_params(axis="x", which="minor", length=2.5, color=INK_MUTED)

    def _draw_plot_index(self, specimen_entries=()) -> None:
        """The upper-right index: the specimen names and fit statistics first,
        then a block per mixture on show.

        `specimen_entries` are (name, [stat lines]) in STACKING order - index 0
        is the bottom of the plot - and are rendered TOP-FIRST so the list reads
        down the screen in the same order as the curves. That ordering is the
        only cue left tying a name to its curve: every specimen draws in the
        same experimental/calculated colour (they are distinguished by vertical
        position, not hue), so a colour swatch here would say nothing. This is
        the one thing the move costs, and reversing the list is what pays most
        of it back.

        The mixture half is the old plot_mixtures: each block is the mixture
        name, then one row per phase slot - "<label>: <fraction %>" and a colour
        swatch per specimen-cell filling that slot, in the phase's display_color
        (the same colour its per-phase curve uses). `axes.clear()` at the top of
        draw_pattern drops the previous index, so no remove-old bookkeeping is
        needed.

        SHOWN-ONLY swatches: a slot's swatches come from the mixture's DISPLAYED
        specimens only, so the swatch columns match the curves on screen. (The
        old app drew a column for every specimen of the mixture, displayed or
        not, which on a multi-specimen mixture put up swatches for patterns the
        user could not see.) The mixture, its slot labels and its fractions are
        still listed in full - they are properties of the mixture, not of the
        selection."""
        project = self.project
        # Identity, not equality: Specimen defines no __eq__, and two distinct
        # specimens must never collapse into one column.
        shown = {id(s) for s in self.specimens if s is not None}
        mixtures = [
            m for m in getattr(project, "mixtures", [])
            if any(id(s) in shown for s in m.specimens)
        ]
        if not mixtures and not specimen_entries:
            return

        default_color = getattr(project, "display_calc_color", INK_PRIMARY)

        def swatch(ec="#000000", fc=None):
            # A fixed-size square (figure-fraction units), or an invisible spacer
            # when both colours are None (old create_rect_patch).
            box = AuxTransformBox(IdentityTransform())
            box.add_artist(FancyBboxPatch(
                (0, 0), width=0.02, height=0.02, boxstyle="square",
                ec=ec, fc=fc, mutation_scale=14,
                transform=self.figure.transFigure,
                alpha=1.0 if (ec is not None or fc is not None) else 0.0,
            ))
            return box

        def text(s, weight="normal"):
            return TextArea(s, textprops=dict(
                color=INK_PRIMARY, size="small", weight=weight))

        blocks = []
        # Specimen names + fit statistics, top of plot first.
        for name, stats_lines in reversed(list(specimen_entries)):
            rows = [HPacker(children=[text(name or "(unnamed)", weight="bold")],
                            align="right", pad=0, sep=3)]
            for line in stats_lines:
                rows.append(HPacker(children=[text(line)],
                                    align="right", pad=0, sep=3))
            blocks.append(VPacker(children=rows, align="right", pad=0, sep=2))

        for mixture in mixtures:
            labels = mixture.phase_labels
            fractions = mixture.fractions
            # The grid rows of this mixture that are actually on the plot; the
            # rows of phase_matrix line up with `specimens` by index.
            shown_rows = [
                i for i, spec in enumerate(mixture.specimens) if id(spec) in shown
            ]
            # Title, padded with an invisible swatch per shown specimen so the
            # name sits above the label column, not the swatches (old title_box).
            title_row = [text(mixture.name, weight="bold")]
            title_row += [swatch(ec=None) for _ in shown_rows]
            rows = [HPacker(children=title_row, align="center", pad=0, sep=3)]
            for i, label in enumerate(labels):
                frac = float(fractions[i]) if i < len(fractions) else 0.0
                children = [text("{}: {:>5.1f}".format(label, frac * 100.0))]
                for r in shown_rows:
                    row = mixture.phase_matrix[r] if r < len(mixture.phase_matrix) else []
                    phase = row[i] if i < len(row) else None
                    if phase is not None:
                        children.append(swatch(
                            fc=getattr(phase, "display_color", None) or default_color))
                rows.append(HPacker(children=children, align="center", pad=0, sep=3))
            blocks.append(VPacker(children=rows, align="right", pad=0, sep=3))

        legend = AnchoredOffsetbox(
            loc="upper right", pad=0.3, borderpad=0.3, frameon=True,
            child=VPacker(children=blocks, align="right", pad=0, sep=6),
        )
        # The index used to be frameless, which was fine when it held only
        # mixture rows. Now it also carries the specimen names and fit
        # statistics that moved out of the left margin, so it is tall enough to
        # sit over the curves - and unbacked text over a pattern is unreadable.
        # A near-opaque surface-coloured panel keeps it legible without hiding
        # much: it is nudged toward opaque rather than fully so, so a curve
        # running behind it is still perceptible.
        legend.patch.set_facecolor(SURFACE)
        legend.patch.set_edgecolor(GRIDLINE)
        legend.patch.set_alpha(0.92)
        legend.patch.set_linewidth(0.8)
        legend.set_zorder(10)
        self.axes.add_artist(legend)

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

    def _draw_stats_band(self, specimen, spec_scale, stats_y_pos, stats_height) -> None:
        """Difference curve(s) centered in the stats band (old plot_statistics).

        Residual/derivative patterns plot with the pattern zero-line at the
        band's middle, scaled by half the (reduced) specimen scale times the
        residual scale factor.
        """
        stats = specimen.statistics
        band_scale = spec_scale * 0.5 * specimen.display_residual_scale
        band_offset = stats_y_pos + 0.5 * stats_height

        # Faint zero line so the difference curve reads as its own panel.
        self.axes.axhline(
            band_offset, color=GRIDLINE, linewidth=0.6, zorder=1,
            xmin=0, xmax=1,
        )
        if specimen.display_residuals:
            rx, ry = stats.residual_pattern
            if rx.size > 1:
                self.axes.plot(
                    rx, ry * band_scale + band_offset,
                    color=RESIDUAL_COLOR, linewidth=0.6, alpha=0.75, zorder=7,
                )
        if specimen.display_derivatives:
            dx, dy = stats.derivative_residual()
            if dx.size > 1:
                self.axes.plot(
                    dx, dy * band_scale + band_offset,
                    color=RESIDUAL_COLOR, linewidth=0.6, alpha=0.65, zorder=7,
                )

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
            if self.drag_start_x is not None and not self._range_select_enabled:
                self._end_drag_highlight()
            if self._crosshair_line is not None:
                self._crosshair_line.remove()
                self._crosshair_line = None
                self.canvas.draw_idle()

    def set_range_select_enabled(self, enabled: bool) -> None:
        """Arm/disarm drag-to-select-a-range. While armed a left-drag reuses the
        crosshair drag-highlight to mark the swept span, and on release reports
        ``(x0, x1)`` (ascending, degrees 2theta) via ``on_range_select`` - the
        Strip Peak / Peak Properties dialogs use this instead of two eye-dropper
        picks. Independent of the crosshair toggle."""
        self._range_select_enabled = enabled
        if not enabled and self.drag_start_x is not None and not self._crosshair_enabled:
            self._end_drag_highlight()

    def _drag_highlight_armed(self) -> bool:
        return self._crosshair_enabled or self._range_select_enabled

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
        if x_pos is None or not self._drag_highlight_armed():
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
            x0 = self.drag_start_x
            x1 = self._event_x(event)
            self._end_drag_highlight()
            if self._on_motion is not None:
                # Deferred, like the old GLib.idle_add refresh.
                QTimer.singleShot(0, lambda: self._on_motion(self, x1))
            # A genuine drag in range-select mode reports the swept [x0, x1]
            # range (a plain click leaves x1 == x0 and reports nothing).
            if (self._range_select_enabled and self._on_range_select is not None
                    and x1 >= 0 and x1 != x0):
                lo, hi = (x0, x1) if x0 <= x1 else (x1, x0)
                self._on_range_select(self, lo, hi)

    def _on_key_press(self, event) -> None:
        if event.key == "left":
            self.pan_x(-1)
        elif event.key == "right":
            self.pan_x(+1)
