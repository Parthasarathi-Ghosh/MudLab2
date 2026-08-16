"""Shared oxide-composition grid controller.

Drives a ``QTableWidget`` as an oxide -> wt% grid: column 0 is the oxide name
(read-only), column 1 a 0-100 ``QDoubleSpinBox`` (so a value can never go below
0, and only numbers are accepted). Values are relative wt% - composition
normalises them later. Used by the Import Non-Clay dialog and the non-clay phase
editor, so both share one implementation and one oxide set
(``composition.reporting_oxides``).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox, QHeaderView, QMessageBox, QTableWidget, QTableWidgetItem,
)

from mudlab.calculations.composition import (
    formula_dot_is_ambiguous, parse_formula, reporting_oxides,
)


class OxideGrid:
    def __init__(self, table: QTableWidget, on_changed=None,
                 formula_edit=None, formula_button=None) -> None:
        self._table = table
        self._on_changed = on_changed
        self._spins: dict[str, QDoubleSpinBox] = {}
        self._build()
        # Optional "fill from chemical formula" input (shared by the import
        # dialog and the editor).
        self._formula_edit = formula_edit
        if formula_button is not None:
            formula_button.clicked.connect(self._on_formula)
        if formula_edit is not None:
            formula_edit.returnPressed.connect(self._on_formula)

    def _build(self) -> None:
        table = self._table
        oxides = reporting_oxides()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Oxide", "wt %"])
        table.setRowCount(len(oxides))
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        for row, name in enumerate(oxides):
            label = QTableWidgetItem(name)
            label.setFlags(Qt.ItemFlag.ItemIsEnabled)  # read-only
            table.setItem(row, 0, label)
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setRange(0.0, 100.0)   # minimum 0 -> negatives impossible
            spin.setSingleStep(1.0)
            spin.valueChanged.connect(self._emit)
            table.setCellWidget(row, 1, spin)
            self._spins[name] = spin

    def _emit(self, *_args) -> None:
        if self._on_changed is not None:
            self._on_changed()

    # -- values ------------------------------------------------------------
    def set_values(self, oxides) -> None:
        data = {str(k): float(v) for k, v in dict(oxides or {}).items()}
        for name, spin in self._spins.items():
            blocked = spin.blockSignals(True)
            spin.setValue(data.get(name, 0.0))
            spin.blockSignals(blocked)
        self._emit()

    def values(self) -> dict[str, float]:
        """Only the oxides with a positive wt%."""
        return {n: s.value() for n, s in self._spins.items() if s.value() > 0}

    def total(self) -> float:
        return float(sum(s.value() for s in self._spins.values()))

    def normalize(self) -> None:
        total = self.total()
        if total <= 0:
            return
        for spin in self._spins.values():
            blocked = spin.blockSignals(True)
            spin.setValue(spin.value() * 100.0 / total)
            spin.blockSignals(blocked)
        self._emit()

    def set_enabled(self, enabled: bool) -> None:
        for spin in self._spins.values():
            spin.setEnabled(enabled)

    # -- fill from a chemical formula --------------------------------------
    def fill_from_formula(self, formula, dot_as_separator: bool = False) -> bool:
        """Parse a chemical formula (e.g. ``NaAlSi3O8``) into oxide wt% and fill
        the grid. Returns False (grid unchanged) when nothing convertible was
        found. ``dot_as_separator`` reads a ``.`` as a segment separator
        (``K2O.Al2O3.6SiO2``) instead of a decimal point."""
        oxides = parse_formula(formula, dot_as_separator=dot_as_separator)
        if not oxides:
            return False
        self.set_values(oxides)
        return True

    def _ask_dot_meaning(self, text: str) -> bool:
        """A '.' between digits reads either way ("Si2.5" vs "Al2O3.2SiO2") and
        the text cannot say which - ask, but only when the two readings would
        actually give different oxides. Returns True for the separator reading."""
        box = QMessageBox(self._table.window())
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Formula")
        box.setText("How should the '.' in '%s' be read?" % text)
        box.setInformativeText(
            "A dot between digits can be a decimal subscript (Fe0.5Mg0.5SiO3) "
            "or a segment / hydrate separator (K2O.Al2O3.6SiO2), and these give "
            "different oxides here.\n\nTip: '·' and '*' are always read as "
            "separators."
        )
        decimal = box.addButton("Decimal point", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Separator", QMessageBox.ButtonRole.AcceptRole)
        box.setDefaultButton(decimal)
        box.exec()
        return box.clickedButton() is not decimal

    def _on_formula(self) -> None:
        text = self._formula_edit.text().strip() if self._formula_edit else ""
        if not text:
            return
        separator = formula_dot_is_ambiguous(text) and self._ask_dot_meaning(text)
        if not self.fill_from_formula(text, dot_as_separator=separator):
            QMessageBox.information(
                self._table.window(), "Formula",
                "Couldn't read any reportable oxide from '%s'.\n\nOnly Si, Al, "
                "Fe, Ca, Mg, Na and K map to the reported oxides; other elements "
                "(and H, C, O) are ignored." % text,
            )
