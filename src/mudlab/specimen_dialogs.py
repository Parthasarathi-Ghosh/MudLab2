"""Specimen utility dialogs: trim, statistics, save-graph size.

Ported from specimen/glade/trim_dialog.glade, statistics.glade and
save_graph_size.glade.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QWidget

from mudlab.ui.ui_save_graph_size import Ui_SaveGraphSizeDialog
from mudlab.ui.ui_statistics import Ui_StatisticsDialog
from mudlab.ui.ui_trim_dialog import Ui_TrimDataDialog

# Combo index -> scope (old cmb_scope items order).
TRIM_SCOPES = ("specimen", "all")

# Export presets: (label, width px, height px, dpi) - old settings.OUTPUT_PRESETS.
SAVE_GRAPH_PRESETS = (
    ("Landscape Large print", 8000, 4800, 300),
    ("Landscape Medium print", 6000, 3800, 300),
    ("Landscape Small print", 4000, 2800, 300),
    ("Portrait Large print", 4800, 8000, 300),
    ("Portrait Medium print", 3800, 6000, 300),
    ("Portrait Small print", 2800, 4000, 300),
)


class TrimDataDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_TrimDataDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

    @property
    def scope(self) -> str:
        return TRIM_SCOPES[self.ui.cmb_scope.currentIndex()]


class StatisticsDialog(QDialog):
    """Old StatisticsView; opened from the specimens context menu."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_StatisticsDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.rejected.connect(self.reject)

    def set_statistics(
        self, points: int, chi2: float, R2: float, Rp: float, Rwp: float, Re: float
    ) -> None:
        self.ui.lbl_points.setText(str(points))
        self.ui.lbl_chi2.setText(f"{chi2:.4f}")
        self.ui.lbl_R2.setText(f"{R2:.4f}")
        self.ui.lbl_Rp.setText(f"{Rp:.2f}")
        self.ui.lbl_Rwp.setText(f"{Rwp:.2f}")
        self.ui.lbl_Re.setText(f"{Re:.2f}")


class SaveGraphSizeDialog(QDialog):
    """Size/DPI options shown when saving the graph (old: an expander
    embedded in the GTK save dialog; Qt native dialogs cannot embed custom
    widgets, so this runs as a small dialog before the file picker)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_SaveGraphSizeDialog()
        self.ui.setupUi(self)
        for label, *_ in SAVE_GRAPH_PRESETS:
            self.ui.cmb_presets.addItem(label)
        self.ui.cmb_presets.currentIndexChanged.connect(self._apply_preset)
        self._apply_preset(0)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

    def _apply_preset(self, index: int) -> None:
        _label, width, height, dpi = SAVE_GRAPH_PRESETS[index]
        self.ui.entry_width.setValue(width)
        self.ui.entry_height.setValue(height)
        self.ui.entry_dpi.setValue(dpi)
