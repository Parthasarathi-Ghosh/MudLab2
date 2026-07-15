"""Atom-contents editor (scale a set of atoms by one value). Design: ui/contents.ui.

Ported from the GTK ContentsController + contents.glade. An AtomContents sets
``atom.pn = amount * value`` for each of its atom rows (e.g. an interlayer K /
Ca / H2O content). Embedded in the component editor's Atom relations group and
bound to an AtomContents model; an edit writes to the model and calls
``on_changed``, which re-applies the relation and recomputes.

Only the atom rows (``prop == "pn"``) are shown/edited; any chaining rows
(targeting another relation) are preserved on the model but not listed here.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHeaderView, QTableWidget, QWidget,
)

from mudlab.models.atom_relations import AtomContent
from mudlab.ui.ui_contents import Ui_AtomContentsWidget


class AtomContentsWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_AtomContentsWidget()
        self.ui.setupUi(self)

        self._contents = None
        self._atoms: list = []
        self._on_changed: Callable[[], None] | None = None
        self._updating = False

        self._table = QTableWidget(0, 2, self)
        self._table.setHorizontalHeaderLabels(["Atom", "Amount"])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        self.ui.contentsTableLayout.addWidget(self._table)

        self.ui.contents_name.editingFinished.connect(self._on_name)
        self.ui.contents_enabled.toggled.connect(self._on_enabled)
        self.ui.contents_value.valueChanged.connect(self._on_value)
        self.ui.btn_add_content_row.clicked.connect(self._on_add_row)
        self.ui.btn_del_content_row.clicked.connect(self._on_del_row)

        self.setEnabled(False)

    # ------------------------------------------------------------------
    def bind_contents(self, contents, atoms, on_changed: Callable[[], None] | None = None) -> None:
        self._contents = contents
        self._atoms = list(atoms or [])
        self._on_changed = on_changed
        self.setEnabled(contents is not None)
        if contents is None:
            self._table.setRowCount(0)
            return
        self._updating = True
        try:
            self.ui.contents_name.setText(contents.name)
            self.ui.contents_enabled.setChecked(bool(contents.enabled))
            self.ui.contents_value.setValue(float(contents.value))
        finally:
            self._updating = False
        self._rebuild_table()

    def _rebuild_table(self) -> None:
        rows = self._contents.atom_rows if self._contents is not None else []
        self._updating = True
        try:
            self._table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                combo = QComboBox(self)
                combo.addItem("(none)", None)
                for atom in self._atoms:
                    combo.addItem(getattr(atom, "name", "") or "atom", atom)
                    if atom is row.atom:
                        combo.setCurrentIndex(combo.count() - 1)
                combo.currentIndexChanged.connect(
                    lambda _i, r=row, c=combo: self._on_row_atom(r, c)
                )
                self._table.setCellWidget(i, 0, combo)

                spin = QDoubleSpinBox(self)
                spin.setDecimals(4)
                spin.setMaximum(100.0)
                spin.setSingleStep(0.1)
                spin.setValue(float(row.amount))
                spin.valueChanged.connect(
                    lambda v, r=row: self._on_row_amount(r, v)
                )
                self._table.setCellWidget(i, 1, spin)
        finally:
            self._updating = False

    # ------------------------------------------------------------------
    def _on_name(self) -> None:
        if self._contents is not None and not self._updating:
            self._contents.name = self.ui.contents_name.text()
            self._notify()

    def _on_enabled(self, checked: bool) -> None:
        if self._contents is not None and not self._updating:
            self._contents.enabled = checked
            self._notify()

    def _on_value(self, value: float) -> None:
        if self._contents is not None and not self._updating:
            self._contents.value = float(value)
            self._notify()

    def _on_row_atom(self, row, combo) -> None:
        if self._updating:
            return
        atom = combo.currentData()
        row.atom = atom
        row._ref = atom.uuid if atom is not None else None
        self._notify()

    def _on_row_amount(self, row, value: float) -> None:
        if not self._updating:
            row.amount = float(value)
            self._notify()

    def _on_add_row(self) -> None:
        if self._contents is None:
            return
        self._contents.atom_contents.append(AtomContent(None, "pn", 1.0))
        self._rebuild_table()
        self._notify()

    def _on_del_row(self) -> None:
        if self._contents is None:
            return
        i = self._table.currentRow()
        rows = self._contents.atom_rows
        if 0 <= i < len(rows):
            self._contents.atom_contents.remove(rows[i])
            self._rebuild_table()
            self._notify()

    def _notify(self) -> None:
        if self._on_changed is not None:
            self._on_changed()
