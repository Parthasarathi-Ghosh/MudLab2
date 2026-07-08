"""Match minerals dialog. Design: ui/match_minerals.ui.

Ported from the GTK MatchMineralsView (specimen/glade/match_minerals.glade).
Non-modal (old view kept it above the main window so the plot stays
interactive). Two lists - all minerals on the right, matched on the left -
with transfer buttons; auto-match and append-labels connect with the
mineral-reference data port.
"""

from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QDialog, QWidget

from mudlab.ui.ui_match_minerals import Ui_MatchMineralsDialog

# Placeholder mineral references until the reference data is ported (old:
# mudlab/data/mineral_references.csv).
_DEMO_MINERALS = (
    "Kaolinite", "Illite", "Smectite", "Chlorite", "Quartz",
    "Calcite", "Dolomite", "Feldspar", "Goethite", "Gibbsite",
)


class MatchMineralsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_MatchMineralsDialog()
        self.ui.setupUi(self)

        self.minerals_model = QStandardItemModel(self)
        self.minerals_model.setHorizontalHeaderLabels(["Mineral"])
        for name in _DEMO_MINERALS:
            self.minerals_model.appendRow(_readonly_item(name))
        self.ui.tv_minerals.setModel(self.minerals_model)

        self.matches_model = QStandardItemModel(self)
        self.matches_model.setHorizontalHeaderLabels(["Mineral"])
        self.ui.tv_matches.setModel(self.matches_model)

        # Old glade: btn_rtl = add (minerals -> matches), btn_ltr = remove.
        self.ui.btn_rtl.clicked.connect(self._add_selected_match)
        self.ui.btn_ltr.clicked.connect(self._remove_selected_match)
        self.ui.buttonBox.rejected.connect(self.reject)

    def _add_selected_match(self) -> None:
        for index in self.ui.tv_minerals.selectionModel().selectedRows():
            self.matches_model.appendRow(_readonly_item(index.data()))

    def _remove_selected_match(self) -> None:
        rows = sorted(
            (i.row() for i in self.ui.tv_matches.selectionModel().selectedRows()),
            reverse=True,
        )
        for row in rows:
            self.matches_model.removeRow(row)


def _readonly_item(text: str) -> QStandardItem:
    item = QStandardItem(text)
    item.setEditable(False)
    return item
