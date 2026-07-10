"""Layer-stacking probabilities component. Design: ui/probabilities.ui.

Ported from the GTK EditProbabilitiesView (probabilities/glade/
probabilities.glade + matrix.glade + R0_independents.glade). Only R0
(independent) stacking is modeled: the (G-1) independent variables
Fi = Wi / sum(Wi..Wg) are editable spinboxes, and the derived weight
fractions W and junction-probability matrix P are shown read-only. The
G-1 inputs and the GxG matrices are built dynamically per phase.

Plugged into the Edit Phases > Probabilities tab (only shown for G>=2, as
the old app removed the tab for single-component R0/G1 phases) and bound to
an R0Probability model; editing an F recomputes W/P and, via the phase
editor's callback, the calculated pattern.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QWidget,
)

from mudlab.ui.ui_probabilities import Ui_ProbabilitiesWidget


class ProbabilitiesWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_ProbabilitiesWidget()
        self.ui.setupUi(self)

        self._prob = None
        self._labels: list[str] = []
        self._on_changed: Callable[[], None] | None = None
        self._updating = False
        self._f_spins: list[QDoubleSpinBox] = []
        self._w_table: QTableWidget | None = None
        self._p_table: QTableWidget | None = None

        self.setEnabled(False)

    # ------------------------------------------------------------------
    def bind_probabilities(
        self, prob, labels=None, on_changed: Callable[[], None] | None = None
    ) -> None:
        """Show and edit an R0Probability. `labels` names the G layers (falls
        back to "Layer i"); `on_changed` runs after an accepted F edit."""
        self._prob = prob
        self._on_changed = on_changed
        self.setEnabled(prob is not None)
        if prob is None:
            self._rebuild(0)
            return
        G = prob.G
        self._labels = self._resolve_labels(labels, G)
        self._rebuild(G)
        self._refresh_matrices()

    def _resolve_labels(self, labels, G: int) -> list[str]:
        names = list(labels or [])
        return [
            names[i] if i < len(names) and names[i] else "Layer %d" % (i + 1)
            for i in range(G)
        ]

    # ------------------------------------------------------------------
    def _rebuild(self, G: int) -> None:
        """(Re)build the F spinboxes and the W/P tables for a G-component
        phase; called whenever a different phase is bound."""
        self._updating = True
        try:
            self._clear_layout(self.ui.independentsForm)
            self._clear_layout(self.ui.weightsLayout)
            self._clear_layout(self.ui.transitionsLayout)
            self._f_spins = []
            self._w_table = None
            self._p_table = None
            if G < 1 or self._prob is None:
                return

            # (G-1) independent F variables.
            for i in range(self._prob.n_independents):
                spin = QDoubleSpinBox(self)
                spin.setDecimals(4)
                spin.setRange(0.0, 1.0)
                spin.setSingleStep(0.05)
                spin.setValue(float(self._prob.f_value(i)))
                spin.setToolTip("W%d / sum(W%d..W%d)" % (i + 1, i + 1, G))
                spin.valueChanged.connect(
                    lambda value, index=i: self._on_f_changed(index, value)
                )
                self._f_spins.append(spin)
                self.ui.independentsForm.addRow("F%d" % (i + 1), spin)

            # W (1 x G weight fractions) and P (G x G) read-only tables.
            self._w_table = self._make_table(1, G, row_labels=["W"])
            self.ui.weightsLayout.addWidget(self._w_table)
            self._p_table = self._make_table(G, G, row_labels=self._labels)
            self.ui.transitionsLayout.addWidget(self._p_table)
        finally:
            self._updating = False

    def _make_table(self, rows: int, cols: int, row_labels) -> QTableWidget:
        table = QTableWidget(rows, cols, self)
        table.setHorizontalHeaderLabels(self._labels)
        table.setVerticalHeaderLabels(list(row_labels))
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        header = table.horizontalHeader()
        for col in range(cols):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setDefaultSectionSize(24)
        # Keep the table compact: height for the rows + header.
        table.setMaximumHeight(28 * rows + 28)
        return table

    # ------------------------------------------------------------------
    def _on_f_changed(self, index: int, value: float) -> None:
        if self._prob is None or self._updating:
            return
        self._prob.set_f(index, value)
        self._refresh_matrices()
        if self._on_changed is not None:
            self._on_changed()

    def _refresh_matrices(self) -> None:
        if self._prob is None:
            return
        weights = np.asarray(self._prob.get_distribution_array(), dtype=float)
        transitions = np.asarray(self._prob.get_probability_matrix(), dtype=float)
        if self._w_table is not None:
            for col in range(self._w_table.columnCount()):
                self._set_cell(self._w_table, 0, col, weights[col])
        if self._p_table is not None:
            for r in range(self._p_table.rowCount()):
                for c in range(self._p_table.columnCount()):
                    self._set_cell(self._p_table, r, c, transitions[r, c])

    @staticmethod
    def _set_cell(table: QTableWidget, row: int, col: int, value: float) -> None:
        item = QTableWidgetItem("%.4f" % float(value))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        table.setItem(row, col, item)

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
