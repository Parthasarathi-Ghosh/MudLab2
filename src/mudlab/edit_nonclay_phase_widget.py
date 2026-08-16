"""Non-clay phase editor. Design: ui/edit_nonclay_phase.ui.

Shown in the Edit Phases Properties pane when a NonClayPhase is selected: name,
display colour, an EDITABLE oxide grid, and a read-only pattern preview. The
pattern itself is set at import time (Import Non-Clay); here the user tunes the
name, colour and oxide composition.

Oxide edits are stored on the phase but do NOT recompute the project - the
composition is not yet wired into the pattern (deferred), so an oxide change has
no visual effect. Name / colour changes do notify (the list label and the
plot-curve colour follow them).
"""

from __future__ import annotations

from typing import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from mudlab.calibrate_fwhm_dialog import CalibrateFwhmDialog
from mudlab.chart_style import INK_SECONDARY, SERIES_BLUE, SURFACE, style_axes
from mudlab.oxide_grid import OxideGrid
from mudlab.qt_utils import ColorButton
from mudlab.ui.ui_edit_nonclay_phase import Ui_EditNonClayPhaseWidget


class EditNonClayPhaseWidget(QWidget):
    # Emitted (with the fitted FWHM) when a calibration asks to apply it to every
    # computed non-clay phase; EditPhasesDialog does the project-wide update.
    apply_fwhm_to_all = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditNonClayPhaseWidget()
        self.ui.setupUi(self)

        self._phase = None
        self._on_changed: Callable[[], None] | None = None
        self._updating = False
        self._wavelength_nm = 0.154056  # for rendering a computed phase's pattern

        self.color = ColorButton(self.ui.button_color, on_change=self._on_color_changed)
        self.grid = OxideGrid(
            self.ui.oxide_grid, on_changed=self._on_grid_changed,
            formula_edit=self.ui.edit_formula,
            formula_button=self.ui.button_formula,
        )

        self.figure = Figure(facecolor=SURFACE, layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(160)
        self.ui.previewLayout.addWidget(self.canvas)
        self.axes = self.figure.add_subplot(111)

        self.ui.nonclay_name.editingFinished.connect(self._on_name_edited)
        self.ui.button_normalize.clicked.connect(self.grid.normalize)
        self.ui.spin_fwhm.valueChanged.connect(self._on_fwhm_changed)
        self.ui.button_calibrate.clicked.connect(self._on_calibrate)

        self.setEnabled(False)
        self._refresh()

    # ------------------------------------------------------------------
    def bind_nonclay_phase(
        self, phase, on_changed: Callable[[], None] | None = None,
        wavelength_nm: float | None = None,
    ) -> None:
        self._phase = phase
        self._on_changed = on_changed
        if wavelength_nm:
            self._wavelength_nm = float(wavelength_nm)
        self.setEnabled(phase is not None)
        self._updating = True
        try:
            self.ui.nonclay_name.setText(phase.name if phase is not None else "")
            self.color.set_color(
                phase.display_color if phase is not None else "#000000"
            )
            self.grid.set_values(phase.oxides if phase is not None else {})
            # FWHM applies only to a CIF-derived (computed) phase; a measured
            # phase has a fixed curve, so hide the row for it.
            computed = phase is not None and phase.is_computed
            if computed:
                self.ui.spin_fwhm.setValue(phase.fwhm)
            # The field cell is a layout (spinbox + Calibrate button), so gate the
            # row via its label widget.
            self.ui.topForm.setRowVisible(self.ui.lbl_fwhm, computed)
        finally:
            self._updating = False
        self._refresh()

    # ------------------------------------------------------------------
    def _on_name_edited(self) -> None:
        if self._phase is None or self._updating:
            return
        self._phase.name = self.ui.nonclay_name.text()
        self._notify()

    def _on_color_changed(self, _qcolor) -> None:
        if self._phase is None or self._updating:
            return
        self._phase.display_color = self.color.hex()
        self._notify()  # the plot-curve colour follows

    def _on_grid_changed(self) -> None:
        # Always keep the sum label current; write oxides only for a real edit.
        self._update_sum()
        if self._phase is None or self._updating:
            return
        self._phase.set_oxides(self.grid.values())
        # No _notify(): composition does not affect the pattern (deferred).

    def _on_fwhm_changed(self, value) -> None:
        if self._phase is None or self._updating or not self._phase.is_computed:
            return
        # Width DOES change the pattern: re-render from the reflection list and
        # recompute (unlike an oxide edit).
        self._phase.set_fwhm(value)
        self._phase.rebuild_stored_pattern(self._wavelength_nm)
        self._update_info()
        self._update_figure()
        self._notify()

    def _on_calibrate(self) -> None:
        """Fit the FWHM from a measured standard and apply it to the spinbox
        (which re-renders + recomputes via _on_fwhm_changed)."""
        if self._phase is None or not self._phase.is_computed:
            return
        dialog = CalibrateFwhmDialog(self, wavelength_nm=self._wavelength_nm)
        if dialog.exec() == CalibrateFwhmDialog.DialogCode.Accepted and dialog.fwhm:
            self.ui.spin_fwhm.setValue(dialog.fwhm)  # this phase (re-renders)
            if dialog.apply_to_all:
                self.apply_fwhm_to_all.emit(dialog.fwhm)

    def _notify(self) -> None:
        if self._on_changed is not None:
            self._on_changed()

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        self._update_sum()
        self._update_info()
        self._update_figure()

    def _update_sum(self) -> None:
        self.ui.lbl_sum.setText("Sum: %.2f %%" % self.grid.total())

    def _update_info(self) -> None:
        phase = self._phase
        if phase is None or phase.raw_pattern_x.size < 2:
            self.ui.nonclay_pattern_info.setText("No pattern loaded.")
            return
        x, y = phase.raw_pattern_x, phase.raw_pattern_y
        self.ui.nonclay_pattern_info.setText(
            "%d points   %.3f-%.3f deg 2θ   max %.4g"
            % (x.size, float(x.min()), float(x.max()), float(y.max()))
        )

    def _update_figure(self) -> None:
        self.axes.clear()
        phase = self._phase
        if phase is not None and phase.raw_pattern_x.size >= 2:
            self.axes.plot(
                phase.raw_pattern_x, phase.raw_pattern_y,
                color=SERIES_BLUE, linewidth=1.0,
            )
            self.axes.set_xlabel("2θ [deg]", color=INK_SECONDARY)
            self.axes.set_ylabel("Intensity", color=INK_SECONDARY)
        style_axes(self.axes)
        self.canvas.draw_idle()
