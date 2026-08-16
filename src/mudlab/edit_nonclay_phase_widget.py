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
from PySide6.QtWidgets import QWidget

from mudlab.chart_style import INK_SECONDARY, SERIES_BLUE, SURFACE, style_axes
from mudlab.oxide_grid import OxideGrid
from mudlab.qt_utils import ColorButton
from mudlab.ui.ui_edit_nonclay_phase import Ui_EditNonClayPhaseWidget


class EditNonClayPhaseWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditNonClayPhaseWidget()
        self.ui.setupUi(self)

        self._phase = None
        self._on_changed: Callable[[], None] | None = None
        self._updating = False

        self.color = ColorButton(self.ui.button_color, on_change=self._on_color_changed)
        self.grid = OxideGrid(self.ui.oxide_grid, on_changed=self._on_grid_changed)

        self.figure = Figure(facecolor=SURFACE, layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(160)
        self.ui.previewLayout.addWidget(self.canvas)
        self.axes = self.figure.add_subplot(111)

        self.ui.nonclay_name.editingFinished.connect(self._on_name_edited)
        self.ui.button_normalize.clicked.connect(self.grid.normalize)

        self.setEnabled(False)
        self._refresh()

    # ------------------------------------------------------------------
    def bind_nonclay_phase(
        self, phase, on_changed: Callable[[], None] | None = None
    ) -> None:
        self._phase = phase
        self._on_changed = on_changed
        self.setEnabled(phase is not None)
        self._updating = True
        try:
            self.ui.nonclay_name.setText(phase.name if phase is not None else "")
            self.color.set_color(
                phase.display_color if phase is not None else "#000000"
            )
            self.grid.set_values(phase.oxides if phase is not None else {})
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
