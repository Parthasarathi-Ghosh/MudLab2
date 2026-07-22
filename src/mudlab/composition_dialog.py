"""Compositions dialog. Design: ui/composition.ui.

Ported from the old edit_mixture_controller.on_composition_clicked, which popped
a modal window showing the mixture's oxide composition (one column per specimen,
one row per oxide) with a CSV export. Here the same table is shown in a Qt
QTableWidget and can be copied to the clipboard or exported to a .csv file.

Opened modally from the Edit Mixtures editor's Composition button for the bound
mixture. Read-only - it reports what calculations.composition computes, it does
not edit the mixture.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QMessageBox, QTableWidgetItem, QWidget,
)

from mudlab.calculations.composition import composition_to_csv, mixture_composition
from mudlab.ui.ui_composition import Ui_CompositionDialog


class CompositionDialog(QDialog):
    def __init__(self, mixture, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Free the dialog when it closes instead of leaving it parented to the
        # mixture editor - otherwise each Composition click leaks one hidden
        # dialog for the editor's lifetime. Safe because exec() does not touch
        # the dialog after it returns.
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.ui = Ui_CompositionDialog()
        self.ui.setupUi(self)
        self._mixture = mixture

        self._specimen_names, self._oxide_rows = mixture_composition(mixture)
        name = getattr(mixture, "name", "") or "mixture"
        self.setWindowTitle("Composition - %s" % name)
        self._populate()

        self.ui.btn_copy.clicked.connect(self._on_copy)
        self.ui.btn_export.clicked.connect(self._on_export)
        self.ui.btn_close.clicked.connect(self.accept)

    def _populate(self) -> None:
        table = self.ui.tbl_composition
        table.setColumnCount(len(self._specimen_names))
        table.setRowCount(len(self._oxide_rows))
        table.setHorizontalHeaderLabels(self._specimen_names)
        table.setVerticalHeaderLabels([oxide for oxide, _ in self._oxide_rows])
        align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        for i, (_oxide, pcts) in enumerate(self._oxide_rows):
            for j, pct in enumerate(pcts):
                item = QTableWidgetItem("%.1f" % pct)
                item.setTextAlignment(align)
                table.setItem(i, j, item)
        table.resizeColumnsToContents()

    # ------------------------------------------------------------------
    def _csv_text(self) -> str:
        return composition_to_csv(self._specimen_names, self._oxide_rows)

    def _on_copy(self) -> None:
        QApplication.clipboard().setText(self._csv_text())

    def _on_export(self) -> None:
        name = (getattr(self._mixture, "name", "") or "composition").strip()
        path, _filter = QFileDialog.getSaveFileName(
            self, "Export composition", "%s composition.csv" % name,
            "CSV files (*.csv);;All files (*)",
        )
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".csv"
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(self._csv_text())
        except OSError as exc:  # surface, don't crash the editor
            QMessageBox.warning(
                self, "Export failed", "Could not write the file:\n\n%s" % exc)
