"""Layer / interlayer atom list. Design: ui/atom_list.ui.

Ported from the GTK EditLayerView (phases/glade/layer.glade): a table of
the atoms in one clay layer - name, default z, calculated z (read-only),
occupancy (#) and the element (an atom-type combo drawn from the project's
atom types) - with Add / Remove. Two instances live in the component
editor (layer atoms and interlayer atoms). Editing an atom recomputes the
structure factor and, via the component/phase callbacks, the pattern.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QComboBox, QHeaderView, QTableWidget, QTableWidgetItem, QWidget,
)

from mudlab.models.component import Atom
from mudlab.ui.ui_atom_list import Ui_AtomListWidget

_COL_NAME, _COL_DEFZ, _COL_CALCZ, _COL_PN, _COL_ELEMENT = range(5)
_HEADERS = ["Atom name", "Def. Z (nm)", "Calc. Z (nm)", "#", "Element"]


class AtomListWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_AtomListWidget()
        self.ui.setupUi(self)

        self._atoms: list = []
        self._atom_types: list = []
        self._on_changed: Callable[[], None] | None = None
        self._updating = False

        table = self.ui.tbl_atoms
        table.setColumnCount(len(_HEADERS))
        table.setHorizontalHeaderLabels(_HEADERS)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        header = table.horizontalHeader()
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(_COL_ELEMENT, QHeaderView.ResizeMode.Stretch)
        for col in (_COL_DEFZ, _COL_CALCZ, _COL_PN):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        table.itemChanged.connect(self._on_item_changed)
        self.ui.btn_add_atom.clicked.connect(self._on_add)
        self.ui.btn_del_atom.clicked.connect(self._on_del)

        self.setEnabled(False)

    # ------------------------------------------------------------------
    def bind_atoms(
        self, atoms, atom_types, on_changed: Callable[[], None] | None = None
    ) -> None:
        """Edit the given atom list in place. `atom_types` fills the element
        combo; `on_changed` runs after every accepted change."""
        self._atoms = atoms if atoms is not None else []
        self._atom_types = list(atom_types or [])
        self._on_changed = on_changed
        self.setEnabled(atoms is not None)
        self._populate()

    def _populate(self) -> None:
        table = self.ui.tbl_atoms
        self._updating = True
        try:
            table.setRowCount(0)
            table.setRowCount(len(self._atoms))
            for row, atom in enumerate(self._atoms):
                self._set_text(row, _COL_NAME, atom.name, editable=True)
                self._set_text(row, _COL_DEFZ, "%.4f" % atom.default_z, editable=True)
                self._set_text(row, _COL_CALCZ, "%.4f" % atom.z, editable=False)
                self._set_text(row, _COL_PN, "%.4f" % atom.pn, editable=True)
                table.setCellWidget(row, _COL_ELEMENT, self._make_combo(atom))
        finally:
            self._updating = False

    def _make_combo(self, atom) -> QComboBox:
        combo = QComboBox()
        combo.addItem("(none)", None)
        current = 0
        for i, atom_type in enumerate(self._atom_types):
            combo.addItem(atom_type.name, atom_type)
            if atom_type is atom.atom_type:
                current = i + 1
        combo.setCurrentIndex(current)  # set before connecting: no spurious fire
        combo.currentIndexChanged.connect(
            lambda _index, a=atom, c=combo: self._on_element_changed(a, c)
        )
        return combo

    # ------------------------------------------------------------------
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return
        row, col = item.row(), item.column()
        if not (0 <= row < len(self._atoms)):
            return
        atom = self._atoms[row]
        if col == _COL_NAME:
            atom.name = item.text()
            self._notify()
        elif col == _COL_DEFZ:
            self._edit_float(item, atom, "default_z")
        elif col == _COL_PN:
            self._edit_float(item, atom, "pn")

    def _edit_float(self, item: QTableWidgetItem, atom, prop: str) -> None:
        try:
            value = float(item.text())
        except ValueError:
            self._updating = True
            try:
                item.setText("%.4f" % getattr(atom, prop))
            finally:
                self._updating = False
            return
        setattr(atom, prop, value)
        self._notify()

    def _on_element_changed(self, atom, combo: QComboBox) -> None:
        if self._updating:
            return
        atom.atom_type = combo.currentData()
        self._notify()

    def _on_add(self) -> None:
        # stretch_z stays False (the stored default for both lists); the calc
        # rescales interlayer z by list position, not this flag.
        self._atoms.append(Atom(name="New atom"))
        self._populate()
        self._notify()

    def _on_del(self) -> None:
        table = self.ui.tbl_atoms
        rows = {index.row() for index in table.selectionModel().selectedRows()}
        if not rows and table.currentRow() >= 0:
            rows = {table.currentRow()}
        for row in sorted(rows, reverse=True):
            if 0 <= row < len(self._atoms):
                del self._atoms[row]
        self._populate()
        self._notify()

    # ------------------------------------------------------------------
    def _notify(self) -> None:
        if self._on_changed is not None:
            self._on_changed()
        self._refresh_calc_z()

    def _refresh_calc_z(self) -> None:
        """The calculated z is derived (interlayer atoms rescale with the
        d-spacing); refresh it from the model after a recompute."""
        table = self.ui.tbl_atoms
        self._updating = True
        try:
            for row, atom in enumerate(self._atoms):
                item = table.item(row, _COL_CALCZ)
                if item is not None:
                    item.setText("%.4f" % atom.z)
        finally:
            self._updating = False

    def _set_text(self, row: int, col: int, text: str, editable: bool) -> None:
        from PySide6.QtCore import Qt

        item = QTableWidgetItem(text)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if editable:
            flags |= Qt.ItemFlag.ItemIsEditable
        item.setFlags(flags)
        self.ui.tbl_atoms.setItem(row, col, item)
