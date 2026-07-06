"""Adapter between Project.specimens and the specimens dock tree.

Columns mirror the old project view treeview: name plus the Exp/Cal/Sep
toggles bound to display_experimental / display_calculated /
display_phases. Sync is two-way: checkbox edits write to the specimen,
model signals refresh the rows.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel

from mudlab.models import Project, Specimen

SPECIMEN_COLUMNS = ("Specimen", "Exp", "Cal", "Sep")
SPECIMEN_COLUMN_TOOLTIPS = (
    "Specimen name",
    "Show experimental pattern",
    "Show calculated pattern",
    "Show phase patterns separately",
)
_TOGGLE_PROPS = ("display_experimental", "display_calculated", "display_phases")


class SpecimensModel(QStandardItemModel):
    def __init__(self, project: Project, parent=None) -> None:
        super().__init__(0, len(SPECIMEN_COLUMNS), parent)
        self._project = project
        self._updating = False

        self.itemChanged.connect(self._on_item_changed)
        project.specimens_changed.connect(self.reload)
        project.visuals_changed.connect(self.refresh)
        self.reload()

    def specimen_at(self, row: int) -> Specimen:
        return self._project.specimens[row]

    def reload(self) -> None:
        self._updating = True
        try:
            self.clear()
            self.setHorizontalHeaderLabels(list(SPECIMEN_COLUMNS))
            for col, tooltip in enumerate(SPECIMEN_COLUMN_TOOLTIPS):
                self.setHeaderData(
                    col, Qt.Orientation.Horizontal, tooltip,
                    Qt.ItemDataRole.ToolTipRole,
                )
            for specimen in self._project.specimens:
                name_item = QStandardItem(specimen.name)
                name_item.setEditable(False)
                row = [name_item]
                for prop in _TOGGLE_PROPS:
                    item = QStandardItem()
                    item.setEditable(False)
                    item.setCheckable(True)
                    item.setCheckState(
                        Qt.CheckState.Checked
                        if getattr(specimen, prop)
                        else Qt.CheckState.Unchecked
                    )
                    row.append(item)
                self.appendRow(row)
        finally:
            self._updating = False

    def refresh(self) -> None:
        """Resync row texts/checks after model-side changes (e.g. dialogs)."""
        if self._updating:
            return
        self._updating = True
        try:
            for row, specimen in enumerate(self._project.specimens):
                if row >= self.rowCount():
                    break
                self.item(row, 0).setText(specimen.name)
                for col, prop in enumerate(_TOGGLE_PROPS, start=1):
                    self.item(row, col).setCheckState(
                        Qt.CheckState.Checked
                        if getattr(specimen, prop)
                        else Qt.CheckState.Unchecked
                    )
        finally:
            self._updating = False

    def _on_item_changed(self, item: QStandardItem) -> None:
        if self._updating or item.column() == 0:
            return
        specimen = self.specimen_at(item.row())
        prop = _TOGGLE_PROPS[item.column() - 1]
        setattr(specimen, prop, item.checkState() == Qt.CheckState.Checked)
