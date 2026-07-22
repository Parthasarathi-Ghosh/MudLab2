"""Atom-contents editor (scale a set of atoms by one value). Design: ui/contents.ui.

Ported from the GTK ContentsController + contents.glade. An AtomContents sets
``atom.pn = amount * value`` for each of its atom rows (e.g. an interlayer K /
Ca / H2O content). Embedded in the component editor's Atom relations group and
bound to an AtomContents model; an edit writes to the model and calls
``on_changed``, which re-applies the relation and recomputes.

Every row is shown/edited: an atom row (``prop == "pn"``) scales an atom's pn,
a chaining row targets a sibling relation (an AtomRatio's RATIO value or SUM, or
an AtomContents value). The Target combo offers the component's atoms plus its
other relations; a choice that would form a cycle is refused.
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
        self._relations: list = []
        self._on_changed: Callable[[], None] | None = None
        self._updating = False

        self._table = QTableWidget(0, 2, self)
        self._table.setHorizontalHeaderLabels(["Target", "Amount"])
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
    def bind_contents(self, contents, atoms, relations=None,
                      on_changed: Callable[[], None] | None = None) -> None:
        """Bind an AtomContents. `atoms` are the component's atoms (pn targets);
        `relations` are its OTHER relations, offered as chaining targets."""
        self._contents = contents
        self._atoms = list(atoms or [])
        self._relations = list(relations or [])
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
        rows = self._contents.atom_contents if self._contents is not None else []
        self._updating = True
        try:
            self._table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self._table.setCellWidget(i, 0, self._build_target_combo(row))

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

    def _build_target_combo(self, row) -> QComboBox:
        """A combo of every possible target for a content row: the component's
        atoms (as pn targets) and its other relations (a ratio contributes its
        RATIO value + SUM, a contents its value). Each item's data is
        ``(object, prop)``; the current target is pre-selected."""
        combo = QComboBox(self)
        combo.addItem("(none)", (None, None))
        selected = 0
        current = (row.target, row.prop)
        for atom in self._atoms:
            combo.addItem(getattr(atom, "name", "") or "atom", (atom, "pn"))
            if current == (atom, "pn"):
                selected = combo.count() - 1
        for rel in self._relations:
            name = getattr(rel, "name", "") or "relation"
            entries = ([("%s: RATIO" % name, "value"), ("%s: SUM" % name, "__internal_sum__")]
                       if getattr(rel, "type", "") == "AtomRatio"
                       else [(name, "value")])
            for label, prop in entries:
                combo.addItem(label, (rel, prop))
                if current == (rel, prop):
                    selected = combo.count() - 1
        combo.setCurrentIndex(selected)
        combo.currentIndexChanged.connect(
            lambda _i, r=row, c=combo: self._on_row_target(r, c)
        )
        return combo

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

    def _on_row_target(self, row, combo) -> None:
        if self._updating:
            return
        obj, prop = combo.currentData()
        # Refuse a target that would make this contents drive itself (directly
        # or through a chain) - the apply guard would break the loop, but the
        # link is meaningless. Revert the combo to the row's current target.
        if obj is not None and prop != "pn" and self._would_cycle(obj):
            self._rebuild_table()
            return
        row.prop = prop or "pn"
        row.atom = obj if prop == "pn" else None
        row.relation = obj if (obj is not None and prop != "pn") else None
        row._ref = obj.uuid if obj is not None else None
        self._notify()

    def _would_cycle(self, target) -> bool:
        """True if driving `target` would loop back to the contents being edited
        (target reaches self._contents through its own chain rows, or IS it)."""
        seen, stack = set(), [target]
        while stack:
            rel = stack.pop()
            if rel is self._contents:
                return True
            if id(rel) in seen:
                continue
            seen.add(id(rel))
            for r in getattr(rel, "chain_rows", []) or []:
                if r.relation is not None:
                    stack.append(r.relation)
        return False

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
        rows = self._contents.atom_contents
        i = self._table.currentRow()
        if 0 <= i < len(rows):
            del rows[i]
            self._rebuild_table()
            self._notify()

    def _notify(self) -> None:
        if self._on_changed is not None:
            self._on_changed()
