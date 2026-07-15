"""Atom-ratio editor (a substitution between two atoms). Design: ui/ratio.ui.

Ported from the GTK EditAtomRatioController + ratio.glade. An AtomRatio sets
``atom1.pn = value*sum`` and ``atom2.pn = (1-value)*sum`` - the substituting and
original atoms of a substitution (e.g. octahedral Fe-for-Mg). Embedded in the
component editor's Atom relations group and bound to an AtomRatio model; an edit
writes to the model and calls ``on_changed``, which re-applies the relation
(updating the atoms' pn), recomputes and redraws.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QWidget

from mudlab.ui.ui_ratio import Ui_AtomRatioWidget


class AtomRatioWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_AtomRatioWidget()
        self.ui.setupUi(self)

        self._ratio = None
        self._atoms: list = []
        self._on_changed: Callable[[], None] | None = None
        self._updating = False

        self.ui.ratio_name.editingFinished.connect(self._on_name_edited)
        self.ui.ratio_enabled.toggled.connect(self._on_enabled_toggled)
        self.ui.ratio_value.valueChanged.connect(self._on_value_sum_changed)
        self.ui.ratio_sum.valueChanged.connect(self._on_value_sum_changed)
        self.ui.ratio_atom1.currentIndexChanged.connect(
            lambda _i: self._on_atom_changed("atom1")
        )
        self.ui.ratio_atom2.currentIndexChanged.connect(
            lambda _i: self._on_atom_changed("atom2")
        )

        self.setEnabled(False)

    # ------------------------------------------------------------------
    def bind_ratio(self, ratio, atoms, on_changed: Callable[[], None] | None = None) -> None:
        """Bind an AtomRatio. `atoms` are the component's atoms (the substituting
        / original candidates). `on_changed` runs after an accepted edit."""
        self._ratio = ratio
        self._atoms = list(atoms or [])
        self._on_changed = on_changed
        self.setEnabled(ratio is not None)
        if ratio is None:
            return
        self._updating = True
        try:
            self.ui.ratio_name.setText(ratio.name)
            self.ui.ratio_enabled.setChecked(bool(ratio.enabled))
            self.ui.ratio_value.setValue(float(ratio.value))
            self.ui.ratio_sum.setValue(float(ratio.sum))
            self._fill_atom_combo(self.ui.ratio_atom1, ratio.atom1)
            self._fill_atom_combo(self.ui.ratio_atom2, ratio.atom2)
        finally:
            self._updating = False

    def _fill_atom_combo(self, combo, current) -> None:
        combo.clear()
        combo.addItem("(none)", None)
        target_atom = current[0] if current else None
        selected = 0
        for atom in self._atoms:
            combo.addItem(getattr(atom, "name", "") or "atom", atom)
            if atom is target_atom:
                selected = combo.count() - 1
        combo.setCurrentIndex(selected)

    # ------------------------------------------------------------------
    def _on_name_edited(self) -> None:
        if self._ratio is not None and not self._updating:
            self._ratio.name = self.ui.ratio_name.text()
            self._notify()

    def _on_enabled_toggled(self, checked: bool) -> None:
        if self._ratio is not None and not self._updating:
            self._ratio.enabled = checked
            self._notify()

    def _on_value_sum_changed(self, _v: float) -> None:
        if self._ratio is not None and not self._updating:
            self._ratio.value = float(self.ui.ratio_value.value())
            self._ratio.sum = float(self.ui.ratio_sum.value())
            self._notify()

    def _on_atom_changed(self, which: str) -> None:
        if self._ratio is None or self._updating:
            return
        combo = self.ui.ratio_atom1 if which == "atom1" else self.ui.ratio_atom2
        atom = combo.currentData()
        setattr(self._ratio, which, (atom, "pn") if atom is not None else None)
        self._notify()

    def _notify(self) -> None:
        if self._on_changed is not None:
            self._on_changed()
