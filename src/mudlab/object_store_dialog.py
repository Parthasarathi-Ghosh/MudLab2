"""Generic list-plus-properties editor window. Design: ui/object_store.ui.

Ported from the GTK ObjectListStoreView (generic/views/glade/
object_store.glade): a modeless window with the object list on the left
(Add/Remove/Import/Export) and the selected object's editor on the right.
Reused by Edit Phases, Edit Atom Types, and Edit Mixtures.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QDialog, QHeaderView, QWidget

from mudlab.ui.ui_object_store import Ui_ObjectStoreDialog


class ObjectStoreDialog(QDialog):
    """The reusable shell; subclasses set a title, columns and the editor."""

    object_selected = Signal(QModelIndex)

    def __init__(
        self,
        parent: QWidget | None = None,
        title: str = "Edit Objects",
        columns: tuple[str, ...] = ("Name",),
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_ObjectStoreDialog()
        self.ui.setupUi(self)
        self.setWindowTitle(title)

        self.objects_model = QStandardItemModel(0, len(columns), self)
        self.objects_model.setHorizontalHeaderLabels(list(columns))
        self.ui.edit_objects_treeview.setModel(self.objects_model)

        header = self.ui.edit_objects_treeview.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(columns)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.ui.edit_objects_treeview.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

        self.ui.edit_object_store.setSizes([240, 680])
        self.ui.buttonBox.rejected.connect(self.reject)

    def set_properties_widget(self, widget: QWidget) -> None:
        """Put the object editor into the Properties pane."""
        self.ui.propertiesLayout.addWidget(widget)

    def add_object_row(self, *values: str) -> None:
        row = []
        for value in values:
            item = QStandardItem(value)
            item.setEditable(False)
            row.append(item)
        self.objects_model.appendRow(row)

    def _on_selection_changed(self, *_args) -> None:
        rows = self.ui.edit_objects_treeview.selectionModel().selectedRows(0)
        if rows:
            self.object_selected.emit(rows[0])
