"""Auto detect peaks dialog. Design: ui/find_peaks_dialog.ui.

Ported from the GTK DetectPeaksView + ThresholdController
(specimen/glade/find_peaks_dialog.glade, marker_controllers.py). Modal. The
graph plots the "# of peaks vs threshold/prominence" histogram with a draggable
vertical line marking the selected cut-off; the Selected threshold and # of
peaks fields stay coupled to it. On OK the peaks at the selected cut-off are
added to the specimen as markers (Specimen.auto_add_peaks).
"""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QDialog, QWidget

from mudlab.calculations import peak_detection as pd
from mudlab.chart_style import INK_SECONDARY, SERIES_BLUE, SURFACE, style_axes
from mudlab.ui.ui_find_peaks_dialog import Ui_DetectPeaksDialog

# Combo index -> old model value.
FIND_PEAKS_PATTERNS = ("exp", "calc")
FIND_PEAKS_ALGORITHMS = ("threshold", "prominence")


class DetectPeaksDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, specimen=None) -> None:
        super().__init__(parent)
        self.ui = Ui_DetectPeaksDialog()
        self.ui.setupUi(self)
        self.specimen = specimen
        self.added_markers: list = []  # populated on accept
        self._updating = False  # guards the threshold <-> #peaks feedback loop
        self._threshold_data: tuple[list, list] | None = None
        self._vline = None
        self._dragging = False

        # --- histogram canvas ---
        self.figure = Figure(facecolor=SURFACE, layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(180)
        self.ui.graphLayout.addWidget(self.canvas)
        self.axes = self.figure.add_subplot(111)
        style_axes(self.axes)
        self.axes.set_ylabel("# of peaks", color=INK_SECONDARY)
        self.canvas.mpl_connect("button_press_event", self._on_plot_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_plot_motion)
        self.canvas.mpl_connect("button_release_event", self._on_plot_release)

        # --- default field values (old ThresholdSelector defaults) ---
        self._block_field_signals(True)
        # The cut-off is a small fraction of the max intensity (grid spacing can
        # be ~0.01), so 2 decimals from the .ui is too coarse - the coupled
        # fields would disagree after rounding. Give them float-entry precision.
        for spin in (self.ui.sel_threshold, self.ui.max_threshold):
            spin.setDecimals(5)
            spin.setSingleStep(0.001)
        self.ui.spin_steps.setMinimum(3)
        self.ui.spin_steps.setValue(20)
        self.ui.max_threshold.setValue(0.32)
        self.ui.sel_threshold.setValue(0.1)
        self.ui.min_distance.setValue(0.1)
        self._select_available_pattern()
        self._block_field_signals(False)

        self._update_algorithm_ui()

        # --- wiring ---
        self.ui.pattern.currentIndexChanged.connect(self._recompute_histogram)
        self.ui.algorithm.currentIndexChanged.connect(self._on_algorithm_changed)
        self.ui.max_threshold.valueChanged.connect(self._on_input_changed)
        self.ui.spin_steps.valueChanged.connect(self._on_input_changed)
        self.ui.min_distance.valueChanged.connect(self._on_input_changed)
        self.ui.sel_threshold.valueChanged.connect(self._on_sel_threshold_changed)
        self.ui.spin_sel_num_peaks.valueChanged.connect(self._on_sel_num_peaks_changed)
        self.ui.buttonBox.accepted.connect(self._on_accept)
        self.ui.buttonBox.rejected.connect(self.reject)

        self._recompute_histogram()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------
    def _block_field_signals(self, block: bool) -> None:
        for widget in (
            self.ui.pattern, self.ui.algorithm, self.ui.max_threshold,
            self.ui.spin_steps, self.ui.min_distance, self.ui.sel_threshold,
            self.ui.spin_sel_num_peaks,
        ):
            widget.blockSignals(block)

    def _select_available_pattern(self) -> None:
        """Default to the experimental pattern, else the calculated one, and
        grey out an unavailable choice so an empty pattern can't be picked."""
        has_exp = self.specimen is not None and self.specimen.has_experimental_data
        has_calc = self.specimen is not None and self.specimen.has_calculated_data
        model = self.ui.pattern.model()
        model.item(0).setEnabled(has_exp)
        model.item(1).setEnabled(has_calc)
        self.ui.pattern.setCurrentIndex(0 if has_exp or not has_calc else 1)

    def _current_pattern(self):
        idx = self.ui.pattern.currentIndex()
        return FIND_PEAKS_PATTERNS[idx] if 0 <= idx < len(FIND_PEAKS_PATTERNS) else "exp"

    def _current_algorithm(self):
        idx = self.ui.algorithm.currentIndex()
        return FIND_PEAKS_ALGORITHMS[idx] if 0 <= idx < len(FIND_PEAKS_ALGORITHMS) else "threshold"

    def _pattern_xy(self):
        if self.specimen is None:
            return np.empty(0), np.empty(0)
        if self._current_pattern() == "calc":
            return self.specimen.calculated_pattern
        return self.specimen.experimental_pattern

    # ------------------------------------------------------------------
    # Algorithm switch (threshold vs prominence)
    # ------------------------------------------------------------------
    def _update_algorithm_ui(self) -> None:
        is_prominence = self._current_algorithm() == "prominence"
        self.ui.lbl_min_distance.setVisible(is_prominence)
        self.ui.min_distance.setVisible(is_prominence)
        self.ui.lbl_thold.setText(
            "Min. prominence:" if is_prominence else "Selected threshold:")
        self.axes.set_xlabel(
            "Min. prominence" if is_prominence else "Threshold", color=INK_SECONDARY)

    def _on_algorithm_changed(self) -> None:
        self._update_algorithm_ui()
        self._recompute_histogram()

    # ------------------------------------------------------------------
    # Histogram (# of peaks vs cut-off)
    # ------------------------------------------------------------------
    def _on_input_changed(self) -> None:
        if not self._updating:
            self._recompute_histogram()

    def _recompute_histogram(self) -> None:
        data_x, data_y = self._pattern_xy()
        data_x = np.asarray(data_x, dtype=float)
        data_y = np.asarray(data_y, dtype=float)
        max_threshold = self.ui.max_threshold.value()
        steps = self.ui.spin_steps.value()

        if data_y.size < 3:
            self._threshold_data = ([], [])
        elif self._current_algorithm() == "prominence":
            (self._threshold_data, sel, mx) = pd.get_best_prominence(
                data_x, data_y, max_threshold, steps, self.ui.min_distance.value())
            self._apply_estimate(sel, mx)
        else:
            (self._threshold_data, sel, mx) = pd.get_best_threshold(
                data_x, data_y, max_threshold, steps)
            self._apply_estimate(sel, mx)

        self._redraw()

    def _apply_estimate(self, sel_threshold: float, max_threshold: float) -> None:
        """Adopt the estimator's suggested cut-off + grid maximum (old
        update_threshold_plot_data set both back onto the model)."""
        self._updating = True
        self.ui.max_threshold.setValue(max_threshold)
        self._updating = False
        self._set_sel_threshold(sel_threshold)

    # ------------------------------------------------------------------
    # Coupled Selected-threshold <-> # of peaks fields + draggable line
    # ------------------------------------------------------------------
    def _has_histogram(self) -> bool:
        return bool(self._threshold_data and len(self._threshold_data[0]) >= 1)

    def _num_peaks_at(self, threshold: float) -> float:
        deltas, numpeaks = self._threshold_data
        return float(np.interp(threshold, deltas, numpeaks))

    def _threshold_at(self, num_peaks: float) -> float:
        deltas, numpeaks = self._threshold_data
        d = np.asarray(deltas, dtype=float)
        n = np.asarray(numpeaks, dtype=float)
        # numpeaks decreases as threshold rises; reverse so xp is increasing.
        return float(np.interp(num_peaks, n[::-1], d[::-1]))

    def _set_sel_threshold(self, value: float) -> None:
        """Authoritative setter: clamp to the grid, sync the # of peaks field
        and the plot line, all without re-entering the signal handlers."""
        if self._has_histogram():
            deltas = self._threshold_data[0]
            value = float(min(max(value, deltas[0]), deltas[-1]))
        self._updating = True
        self.ui.sel_threshold.setValue(value)
        # Read the value back after the spinbox rounds it, so the # of peaks
        # field and the plot line stay consistent with what is displayed.
        actual = self.ui.sel_threshold.value()
        if self._has_histogram():
            self.ui.spin_sel_num_peaks.setValue(int(round(self._num_peaks_at(actual))))
        self._updating = False
        self._move_vline(actual)

    def _on_sel_threshold_changed(self, value: float) -> None:
        if not self._updating:
            self._set_sel_threshold(value)

    def _on_sel_num_peaks_changed(self, value: int) -> None:
        if self._updating or not self._has_histogram():
            return
        self._set_sel_threshold(self._threshold_at(value))

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------
    def _redraw(self) -> None:
        self.axes.clear()
        style_axes(self.axes)
        is_prominence = self._current_algorithm() == "prominence"
        self.axes.set_xlabel(
            "Min. prominence" if is_prominence else "Threshold", color=INK_SECONDARY)
        self.axes.set_ylabel("# of peaks", color=INK_SECONDARY)
        self._vline = None
        if self._has_histogram():
            deltas, numpeaks = self._threshold_data
            self.axes.plot(deltas, numpeaks, color=INK_SECONDARY, linewidth=1.2)
            self._vline = self.axes.axvline(
                x=self.ui.sel_threshold.value(), color=SERIES_BLUE, linewidth=1.5)
            self.axes.autoscale_view()
        self.canvas.draw_idle()

    def _move_vline(self, value: float) -> None:
        if self._vline is not None:
            self._vline.set_xdata([value, value])
            self.canvas.draw_idle()

    def _on_plot_press(self, event) -> None:
        if event.inaxes is self.axes and event.button == 1 and event.xdata is not None:
            self._dragging = True
            self._set_sel_threshold(event.xdata)

    def _on_plot_motion(self, event) -> None:
        if self._dragging and event.inaxes is self.axes and event.xdata is not None:
            self._set_sel_threshold(event.xdata)

    def _on_plot_release(self, event) -> None:
        self._dragging = False

    # ------------------------------------------------------------------
    # Accept -> create the markers
    # ------------------------------------------------------------------
    def _on_accept(self) -> None:
        if self.specimen is not None:
            self.added_markers = self.specimen.auto_add_peaks(
                self.ui.sel_threshold.value(),
                pattern=self._current_pattern(),
                algorithm=self._current_algorithm(),
                min_distance=self.ui.min_distance.value(),
            )
        self.accept()
