"""Auto detect peaks dialog. Design: ui/find_peaks_dialog.ui.

Ported from the GTK DetectPeaksView (specimen/glade/find_peaks_dialog.glade).
Modal; the threshold histogram (# of peaks vs threshold) plots into the
graph placeholder. The actual peak detection connects with the
calculation-engine port.
"""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QDialog, QWidget

from mudlab.chart_style import INK_SECONDARY, SURFACE, style_axes
from mudlab.ui.ui_find_peaks_dialog import Ui_DetectPeaksDialog

# Combo index -> old model value.
FIND_PEAKS_PATTERNS = ("experimental", "calculated")
FIND_PEAKS_ALGORITHMS = ("threshold",)


class DetectPeaksDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_DetectPeaksDialog()
        self.ui.setupUi(self)

        self.figure = Figure(facecolor=SURFACE, layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(180)
        self.ui.graphLayout.addWidget(self.canvas)
        self.axes = self.figure.add_subplot(111)
        style_axes(self.axes)
        self.axes.set_xlabel("Threshold", color=INK_SECONDARY)
        self.axes.set_ylabel("# of peaks", color=INK_SECONDARY)

        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)
