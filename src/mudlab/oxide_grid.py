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
from PySide6.QtWidgets import QDoubleSpinBox, QHeaderView, QTableWidget, QTableWidgetItem

from mudlab.calculations.composition import reporting_oxides


class OxideGrid:
    def __init__(self, table: QTableWidget, on_changed=None) -> None:
        self._table = table
        self._on_changed = on_changed
        self._spins: dict[str, QDoubleSpinBox] = {}
        self._build()

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
