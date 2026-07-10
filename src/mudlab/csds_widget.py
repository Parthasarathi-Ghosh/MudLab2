"""CSDS distribution component. Design: ui/csds.ui.

Ported from the GTK EditCSDSDistributionView (phases/glade/csds.glade):
the mean coherent-scattering-domain size (average number of stacked
layers) plus a live histogram of the Drits log-normal size distribution.
Plugged into the Edit Phases > CSDS Distribution tab and bound to a
DritsCSDSDistribution model; editing the mean recomputes the distribution
(and, via the phase editor's callback, the calculated pattern).
"""

from __future__ import annotations

from typing import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget

from mudlab.chart_style import INK_SECONDARY, SERIES_BLUE, SURFACE, style_axes
from mudlab.ui.ui_csds import Ui_CSDSWidget


class CSDSWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_CSDSWidget()
        self.ui.setupUi(self)

        self._csds = None
        self._on_changed: Callable[[], None] | None = None
        self._updating = False

        self.figure = Figure(facecolor=SURFACE, layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(180)
        self.ui.csdsHistLayout.addWidget(self.canvas)
        self.axes = self.figure.add_subplot(111)

        self.ui.csds_average.valueChanged.connect(self._on_average_changed)

        self.setEnabled(False)
        self._update_figure()

    def bind_csds(self, csds, on_changed: Callable[[], None] | None = None) -> None:
        """Show and edit a DritsCSDSDistribution. `on_changed` runs after an
        accepted mean edit (used to recompute + redraw the pattern)."""
        self._csds = csds
        self._on_changed = on_changed
        self.setEnabled(csds is not None)
        if csds is None:
            self._update_figure()
            return
        self._updating = True
        try:
            self.ui.csds_average.setValue(float(csds.average))
        finally:
            self._updating = False
        self._update_figure()

    def _on_average_changed(self, value: float) -> None:
        if self._csds is None or self._updating:
            return
        self._csds.average = value
        self._update_figure()
        if self._on_changed is not None:
            self._on_changed()

    def _update_figure(self) -> None:
        self.axes.clear()
        csds = self._csds
        if csds is not None:
            self.ui.csds_range.setText(f"{csds.minimum} - {csds.maximum}")
            distribution, mean = csds.distribution()
            counts = range(len(distribution))
            self.axes.bar(counts, distribution, color=SERIES_BLUE, width=0.9)
            self.axes.axvline(mean, color=INK_SECONDARY, linewidth=1.0, linestyle="--")
            self.axes.set_xlim(0, max(len(distribution) - 1, 1))
            self.axes.set_xlabel("Number of layers", color=INK_SECONDARY)
            self.axes.set_ylabel("Frequency", color=INK_SECONDARY)
        style_axes(self.axes)
        self.canvas.draw_idle()
