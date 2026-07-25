"""CSV import options dialog + the shared pattern-import helper. Design:
ui/csv_import.ui.

Ported from the GTK CSV File Import chooser (generic/views/glade/csv_import.glade,
the "Advanced" expander: separator sign, decimal sign, first-row-headers). The
options drive the common reader in file_parsers.csv_io, so every pattern import
that goes through :func:`import_pattern` honours the same choices, with a live
preview of how the file parses.
"""

from __future__ import annotations

import os

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QWidget,
)

from mudlab.file_parsers.csv_io import (
    DECIMALS, DELIMITERS, CsvOptions, preview, sniff,
)
from mudlab.file_parsers.xrd_import import (
    PATTERN_FILTERS, parse_pattern, uses_csv_options,
)
from mudlab.ui.ui_csv_import import Ui_CsvImportDialog


class CsvImportDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, path: str = "") -> None:
        super().__init__(parent)
        self.ui = Ui_CsvImportDialog()
        self.ui.setupUi(self)
        self.path = path
        self.ui.lbl_file.setText(os.path.basename(path) if path else "")

        for label, value in DELIMITERS:
            self.ui.cmb_separator.addItem(label, value)
        for label, value in DECIMALS:
            self.ui.cmb_decimal.addItem(label, value)

        self.preview_model = QStandardItemModel(self)
        self.preview_model.setHorizontalHeaderLabels(["Column 1", "Column 2"])
        self.ui.tv_preview.setModel(self.preview_model)
        self.ui.tv_preview.horizontalHeader().setStretchLastSection(True)

        # Pre-fill from a best-guess sniff of the file.
        if path:
            self._apply_options(sniff(path))

        self.ui.cmb_separator.currentIndexChanged.connect(self._on_separator_changed)
        self.ui.cmb_decimal.currentIndexChanged.connect(self._refresh_preview)
        self.ui.chk_has_header.toggled.connect(self._refresh_preview)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

        self._sync_decimal_options()  # set the initial enabled state
        self._refresh_preview()

    # ------------------------------------------------------------------
    def _apply_options(self, options: CsvOptions) -> None:
        sep_idx = self.ui.cmb_separator.findData(options.delimiter)
        self.ui.cmb_separator.setCurrentIndex(sep_idx if sep_idx >= 0 else 0)
        dec_idx = self.ui.cmb_decimal.findData(options.decimal)
        self.ui.cmb_decimal.setCurrentIndex(dec_idx if dec_idx >= 0 else 0)
        self.ui.chk_has_header.setChecked(options.has_header)

    def options(self) -> CsvOptions:
        return CsvOptions(
            delimiter=self.ui.cmb_separator.currentData(),
            decimal=self.ui.cmb_decimal.currentData(),
            has_header=self.ui.chk_has_header.isChecked(),
        )

    def _on_separator_changed(self) -> None:
        self._sync_decimal_options()
        self._refresh_preview()

    def _sync_decimal_options(self) -> None:
        """The decimal sign cannot be the same character as the separator (it
        would split a number in two). Disable the matching decimal item and,
        if it was selected, fall back to the first non-conflicting one."""
        delimiter = self.ui.cmb_separator.currentData()
        model = self.ui.cmb_decimal.model()
        for i in range(self.ui.cmb_decimal.count()):
            conflict = self.ui.cmb_decimal.itemData(i) == delimiter
            model.item(i).setEnabled(not conflict)
            if conflict and self.ui.cmb_decimal.currentIndex() == i:
                fallback = next(
                    (j for j in range(self.ui.cmb_decimal.count())
                     if self.ui.cmb_decimal.itemData(j) != delimiter), 0)
                self.ui.cmb_decimal.setCurrentIndex(fallback)

    def _refresh_preview(self) -> None:
        self.preview_model.removeRows(0, self.preview_model.rowCount())
        if not self.path:
            return
        try:
            rows = preview(self.path, self.options())
        except Exception:  # noqa: BLE001 - preview must never break the dialog
            rows = []
        for col0, col1, ok in rows:
            items = [_cell(col0, ok), _cell(col1, ok)]
            self.preview_model.appendRow(items)

    @staticmethod
    def get_options(parent, path: str) -> CsvOptions | None:
        """Show the dialog for `path`; return the chosen options, or None if
        the user cancelled."""
        dialog = CsvImportDialog(parent, path)
        if dialog.exec():
            return dialog.options()
        return None


def _cell(text: str, ok: bool) -> QStandardItem:
    item = QStandardItem(text)
    item.setEditable(False)
    if not ok:
        # Header / non-numeric rows read as headings, not data.
        font = item.font()
        font.setItalic(True)
        item.setFont(font)
    return item


def import_pattern(
    parent,
    path: str | None = None,
    filters: str = PATTERN_FILTERS,
    title: str = "Import pattern",
):
    """Pick a pattern file (unless `path` is given), offer the CSV-import
    options for delimited-text formats, then parse. Returns ``(x, y)`` numpy
    arrays, or None if the user cancelled or the file could not be read (an
    error is shown). The single place pattern imports flow through so every
    caller shares the parser and the options."""
    if path is None:
        path, _ = QFileDialog.getOpenFileName(parent, title, "", filters)
        if not path:
            return None
    options = None
    if uses_csv_options(path):
        options = CsvImportDialog.get_options(parent, path)
        if options is None:
            return None  # cancelled at the options step
    try:
        return parse_pattern(path, options)
    except Exception as exc:  # noqa: BLE001 - surface any parse/IO error
        QMessageBox.warning(
            parent, title, "Could not read:\n%s\n\n%s" % (path, exc)
        )
        return None
