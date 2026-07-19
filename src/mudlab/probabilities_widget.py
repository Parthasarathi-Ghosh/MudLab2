"""Layer-stacking probabilities component. Design: ui/probabilities.ui.

Ported from the GTK EditProbabilitiesView (probabilities/glade/
probabilities.glade + matrix.glade + R0_independents.glade). The editable
independent parameters differ per model - R0 has (G-1) F params
Fi = Wi / sum(Wi..Wg); R1G2 has W1 and the free junction probability
P11/P22 - so the widget does not hard-code them: it iterates the model's
`editable_params()` descriptors, one spinbox + Inherit checkbox each, and
shows the derived weight fractions W and junction matrix P read-only below.
W and P are rank x rank (rank = g**R): just G for R0/R1, but the layer
PAIRS/TRIPLETS for R2/R3 (4x4, 8x8, 9x9), so the tables are sized and
state-labelled from the model per phase, not hard-coded to G.

Plugged into the Edit Phases > Probabilities tab (only shown for G>=2, as
the old app removed the tab for single-component R0/G1 phases) and bound to
the phase's probability model; editing a parameter recomputes W/P and, via
the phase editor's callback, the calculated pattern.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QHBoxLayout, QHeaderView, QLabel, QTableWidget,
    QTableWidgetItem, QWidget,
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
        self._specs: list[dict] = []
        self._param_spins: list[QDoubleSpinBox] = []
        self._param_inherits: list[QCheckBox] = []
        self._can_inherit = False
        self._w_table: QTableWidget | None = None
        self._p_table: QTableWidget | None = None

        self.setEnabled(False)

    # ------------------------------------------------------------------
    def bind_probabilities(
        self,
        prob,
        labels=None,
        on_changed: Callable[[], None] | None = None,
        can_inherit: bool = False,
    ) -> None:
        """Show and edit a probability model (R0, or R1-R3). `labels` names the G
        layers (falls back to "Layer i"); `on_changed` runs after an accepted
        edit. `can_inherit` is True when the phase is based on another - only
        then can a parameter be inherited (the per-parameter "Inherit" boxes
        are enabled)."""
        self._prob = prob
        self._on_changed = on_changed
        self._can_inherit = bool(can_inherit)
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
        """(Re)build the parameter spinboxes and the W/P tables for the bound
        phase; called whenever a different phase is bound. The parameters come
        from the model's editable_params(), so R0 (F1..Fn) and R1G2 (W1, P11/
        P22) are handled by the same code."""
        self._updating = True
        try:
            self._clear_layout(self.ui.independentsForm)
            self._clear_layout(self.ui.weightsLayout)
            self._clear_layout(self.ui.transitionsLayout)
            self._specs = []
            self._param_spins = []
            self._param_inherits = []
            self._w_table = None
            self._p_table = None
            if G < 1 or self._prob is None:
                return

            # One spin + "Inherit" toggle per independent parameter. The
            # inherit box reads through to the based_on phase (old inherit_*
            # flags); it is only enabled when the phase is based on another.
            self._specs = list(self._prob.editable_params())
            for index, spec in enumerate(self._specs):
                spin = QDoubleSpinBox(self)
                spin.setDecimals(4)
                lo, hi = spec.get("bounds", (0.0, 1.0))
                spin.setRange(float(lo), float(hi))
                spin.setSingleStep(0.05)
                spin.setValue(float(spec["get"]()))
                spin.setToolTip(spec.get("tooltip", ""))
                spin.valueChanged.connect(
                    lambda value, i=index: self._on_param_changed(i, value)
                )
                inherit = QCheckBox("Inherit", self)
                inherit.setToolTip(spec.get("inherit_tooltip", ""))
                inherit.setChecked(bool(spec["inherited"]))
                inherit.setEnabled(self._can_inherit)
                inherit.toggled.connect(
                    lambda checked, i=index: self._on_param_inherit_toggled(i, checked)
                )
                spin.setDisabled(bool(spec["inherited"]))

                row = QWidget(self)
                box = QHBoxLayout(row)
                box.setContentsMargins(0, 0, 0, 0)
                box.addWidget(spin)
                box.addWidget(inherit)
                self._param_spins.append(spin)
                self._param_inherits.append(inherit)
                self.ui.independentsForm.addRow(spec["label"], row)

            # W and P are rank x rank, where rank = G**max(R,1): just G for R0
            # and R1 (a state is one layer), but g**R for R>=2 (a state is a
            # layer PAIR/TRIPLET - 4x4 for R2G2, 8x8 for R3G2, 9x9 for R2G3).
            # Size the tables to the real matrices and label the g**R axes with
            # their state tuples, not layer names.
            state_labels = self._state_labels()
            rank = len(state_labels)
            self._w_table = self._make_table(
                1, rank, col_labels=state_labels, row_labels=["W"])
            self.ui.weightsLayout.addWidget(self._w_table)
            self._p_table = self._make_table(
                rank, rank, col_labels=state_labels, row_labels=state_labels)
            self.ui.transitionsLayout.addWidget(self._p_table)
        finally:
            self._updating = False

    def _state_labels(self) -> list[str]:
        """Header labels for the W/P axes. For R0/R1 a state is a single layer,
        so use the layer names. For R>=2 a state is an R-tuple of layers
        (state index x = sum_k i_k * G**(R-1-k)); label it with the 1-based
        layer numbers, e.g. R2G2 -> '1,1' '1,2' '2,1' '2,2'."""
        if self._prob is None:
            return []
        G = self._prob.G
        R = max(int(getattr(self._prob, "R", 0)), 1)
        if R <= 1:
            return list(self._labels)
        labels = []
        for x in range(G ** R):
            digits = [str((x // (G ** (R - 1 - k))) % G + 1) for k in range(R)]
            labels.append(",".join(digits))
        return labels

    def _make_table(self, rows: int, cols: int, col_labels, row_labels
                    ) -> QTableWidget:
        table = QTableWidget(rows, cols, self)
        table.setHorizontalHeaderLabels(list(col_labels))
        table.setVerticalHeaderLabels(list(row_labels))
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        header = table.horizontalHeader()
        # Few columns (R0/R1): stretch to fill the tab. Many (pair/triplet
        # states, up to 9): size to content and let the table scroll so the
        # cells stay legible instead of being squeezed.
        if cols <= 4:
            for col in range(cols):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        else:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setDefaultSectionSize(24)
        # Cap the height: show up to ~6 rows then scroll, so an 8x8/9x9 P
        # matrix does not blow out the tab.
        visible_rows = min(rows, 6)
        table.setMaximumHeight(28 * visible_rows + 28)
        return table

    # ------------------------------------------------------------------
    def _on_param_changed(self, index: int, value: float) -> None:
        if self._prob is None or self._updating:
            return
        self._specs[index]["set"](value)
        self._refresh_matrices()
        if self._on_changed is not None:
            self._on_changed()

    def _on_param_inherit_toggled(self, index: int, checked: bool) -> None:
        """Tick -> the parameter reads through to the based_on phase (spin greys
        out and shows the parent's value); untick -> it falls back to this
        phase's own stored value. Either way W/P re-derive and the pattern
        recomputes."""
        if self._prob is None or self._updating:
            return
        self._specs[index]["set_inherited"](checked)
        # Re-query the model for the authoritative state (a flag only reads
        # through when a based_on parent is actually resolved), and refresh
        # this row's spec so its getter reflects the new source.
        fresh = self._prob.editable_params()[index]
        self._specs[index] = fresh
        self._updating = True
        try:
            self._param_spins[index].setDisabled(bool(fresh["inherited"]))
            self._param_spins[index].setValue(float(fresh["get"]()))
        finally:
            self._updating = False
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
