"""Wavelength-distribution (emission spectrum) editor. Design:
ui/wavelength_distribution.ui.

Ported from the GTK WavelengthDistributionView + WavelengthDistributionController
(goniometer/glade/wavelength_distribution.glade, goniometer/controllers.py).
An editable (wavelength_nm, fraction) table with Add / Remove and .wld
import / export. Edits are live: every change writes the whole distribution
back to the bound Goniometer (Goniometer.set_wavelength_distribution), which
updates the derived dominant `wavelength`.
"""

from __future__ import annotations

import os

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget

from mudlab.file_parsers.wld_file import load_wld, save_wld
from mudlab.ui.ui_wavelength_distribution import Ui_WavelengthDistributionDialog

_WLD_FILTER = "Wavelength distribution (*.wld);;All files (*)"
_DEFAULT_WLD_DIR = os.path.join(
    os.path.dirname(__file__), "data", "default wavelength distributions"
)


class WavelengthDistributionDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, goniometer=None) -> None:
        super().__init__(parent)
        self.ui = Ui_WavelengthDistributionDialog()
        self.ui.setupUi(self)
        self.goniometer = goniometer
        self._updating = False
        # Working copy (list of [wavelength, fraction]); pushed to the model on
        # every edit. Mutable rows so a single cell can be updated in place.
        self._pairs: list[list[float]] = [
            [float(w), float(f)]
            for w, f in (goniometer.wavelength_distribution if goniometer else [])
        ]

        self.model = QStandardItemModel(self)
        self.model.setHorizontalHeaderLabels(["Wavelength (nm)", "Fraction"])
        self.ui.tv_wld.setModel(self.model)
        self.ui.tv_wld.horizontalHeader().setStretchLastSection(True)
        self._populate()
        self.model.itemChanged.connect(self._on_item_changed)

        self.ui.btn_add.clicked.connect(self._on_add)
        self.ui.btn_del.clicked.connect(self._on_del)
        self.ui.btn_import.clicked.connect(self._on_import)
        self.ui.btn_export.clicked.connect(self._on_export)
        self.ui.buttonBox.rejected.connect(self.accept)  # Close (edits are live)

        self.setEnabled(goniometer is not None)

    # ------------------------------------------------------------------
    # Table <-> working copy
    # ------------------------------------------------------------------
    def _populate(self) -> None:
        self._updating = True
        self.model.removeRows(0, self.model.rowCount())
        for wavelength, fraction in self._pairs:
            self.model.appendRow(
                [self._cell(wavelength), self._cell(fraction)]
            )
        self._updating = False

    @staticmethod
    def _cell(value: float) -> QStandardItem:
        item = QStandardItem("%g" % value)
        return item

    def _on_item_changed(self, item: QStandardItem) -> None:
        if self._updating:
            return
        row, col = item.row(), item.column()
        try:
            value = float(item.text().strip())
        except ValueError:
            self._revert(item, row, col)
            return
        problem = self._out_of_range(col, value)
        if problem is not None:
            # A VALID NUMBER can still be impossible. The classic typo is a
            # missing leading zero - 1.544 for 0.1544 nm - and nothing
            # downstream complains: `get_2t_from_nm` clamps arcsin's argument
            # to [-1, 1], so reflections do not error, they just silently stop
            # appearing. A pattern quietly missing most of its peaks is far
            # worse than a rejected cell.
            self._revert(item, row, col)
            QMessageBox.warning(self, "Emission spectrum", problem)
            return
        self._pairs[row][col] = value
        self._push()

    #: Plausible X-ray wavelengths, in nm. Deliberately wide - Mo Ka is about
    #: 0.071 and Cr Ka about 0.229 - so it rejects typos, not unusual sources.
    _MIN_NM, _MAX_NM = 0.01, 1.0

    def _out_of_range(self, col, value):
        """Why `value` cannot go in column `col`, or None if it can."""
        if col == 0:
            if not (self._MIN_NM <= value <= self._MAX_NM):
                return (
                    "%g is not a usable wavelength.\n\n"
                    "Wavelengths are in NANOMETRES and must be between %g and "
                    "%g nm - copper Ka1 is 0.154056, molybdenum 0.0709.\n\n"
                    "A value near 1.5 is the usual sign of a missing leading "
                    "zero." % (value, self._MIN_NM, self._MAX_NM))
        elif value < 0.0:
            return ("A fraction cannot be negative.\n\n"
                    "Fractions are relative weights; they are normalised, so "
                    "they need not add to 1.")
        return None

    def _revert(self, item, row, col) -> None:
        """Put the cell back to the last value that was accepted."""
        self._updating = True
        item.setText("%g" % self._pairs[row][col])
        self._updating = False

    def _push(self) -> None:
        if self.goniometer is not None:
            self.goniometer.set_wavelength_distribution(self._pairs)

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def _on_add(self) -> None:
        self._pairs.append([0.0, 0.0])
        self._updating = True
        self.model.appendRow([self._cell(0.0), self._cell(0.0)])
        self._updating = False
        self.ui.tv_wld.setCurrentIndex(self.model.index(len(self._pairs) - 1, 0))
        self._push()

    def _on_del(self) -> None:
        rows = sorted(
            (i.row() for i in self.ui.tv_wld.selectionModel().selectedRows()),
            reverse=True,
        )
        if not rows:
            return
        for row in rows:
            if 0 <= row < len(self._pairs):
                del self._pairs[row]
        self._populate()
        self._push()

    def _on_import(self) -> None:
        if QMessageBox.question(
            self, "Import wavelength distribution",
            "Importing will replace the current emission spectrum. Continue?",
        ) != QMessageBox.StandardButton.Yes:
            return
        start_dir = _DEFAULT_WLD_DIR if os.path.isdir(_DEFAULT_WLD_DIR) else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import wavelength distribution", start_dir, _WLD_FILTER
        )
        if not path:
            return
        try:
            pairs = load_wld(path)
        except Exception as exc:  # noqa: BLE001 - surface any parse/IO error
            QMessageBox.critical(
                self, "Import wavelength distribution",
                "Could not import:\n%s\n\n%s" % (path, exc),
            )
            return
        self._pairs = [[float(w), float(f)] for w, f in pairs]
        self._populate()
        self._push()

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export wavelength distribution", "", _WLD_FILTER
        )
        if not path:
            return
        if not path.lower().endswith(".wld"):
            path += ".wld"
        try:
            save_wld(path, self._pairs)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Export wavelength distribution",
                "Could not export:\n%s\n\n%s" % (path, exc),
            )
