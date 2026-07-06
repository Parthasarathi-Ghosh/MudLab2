"""Mixture editor form. Design: ui/edit_mixture.ui.

Ported from the GTK EditMixtureView (mixture/views/glade/
edit_mixture.glade). Plugged into the Properties pane of the Edit
Mixtures window. The old app built the phases-x-specimens matrix
dynamically (phase rows with name + fraction; one column per specimen
with a phase-selection combo per cell, plus scale and background shift
per specimen); here a placeholder QTableWidget shows that arrangement
until the mixture model (Qt signals) exists.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidgetItem, QWidget

from mudlab.ui.ui_edit_mixture import Ui_EditMixtureWidget


class EditMixtureWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditMixtureWidget()
        self.ui.setupUi(self)

    def set_mixture_placeholder(
        self,
        name: str,
        specimens: tuple[str, ...],
        phases: tuple[tuple[str, float], ...],
        scales: tuple[float, ...],
        bg_shifts: tuple[float, ...],
    ) -> None:
        self.ui.mixture_name.setText(name)

        table = self.ui.tbl_matrix
        table.clear()
        table.setColumnCount(1 + len(specimens))
        table.setHorizontalHeaderLabels(["Fraction", *specimens])
        table.setRowCount(2 + len(phases))
        table.setVerticalHeaderLabels(
            ["Abs. scale", "Bg. shift", *(phase for phase, _ in phases)]
        )

        def put(row: int, col: int, text: str) -> None:
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, col, item)

        for col, (scale, bg) in enumerate(zip(scales, bg_shifts), start=1):
            put(0, col, f"{scale:.2f}")
            put(1, col, f"{bg:.1f}")
        for row, (phase, fraction) in enumerate(phases, start=2):
            put(row, 0, f"{fraction:.2f}")
            # Old: a combo per cell picking which phase object applies to
            # that specimen; placeholder shows the linked phase name.
            for col in range(1, 1 + len(specimens)):
                put(row, col, phase)

        header = table.horizontalHeader()
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
