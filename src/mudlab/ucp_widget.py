"""Unit-cell property editor (cell length a or b). Design: ui/ucp.ui.

Ported from the GTK EditUnitCellPropertyController + unit_cell_prop.glade. A
component's cell length is either fixed (a typed value) or derived
(``value = factor * property + constant``, where the property is an atom's pn
or the other cell length). One reusable widget is embedded twice in the
component editor - once for a, once for b.

Bound to a UnitCellProperty model (models/unit_cell_prop.py): editing a field
writes to the model and calls ``on_changed``, which (in the component editor)
recomputes the derived values, refreshes the displays and redraws the pattern.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QWidget

from mudlab.ui.ui_ucp import Ui_UnitCellPropWidget


class UnitCellPropWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_UnitCellPropWidget()
        self.ui.setupUi(self)

        self._ucp = None
        self._component = None
        self._other_attr = ""     # "cell_a" / "cell_b" - the extra prop option
        self._other_label = ""
        self._on_changed: Callable[[], None] | None = None
        self._updating = False

        self.ui.ucp_enabled.toggled.connect(self._on_enabled_toggled)
        self.ui.ucp_value.valueChanged.connect(self._on_value_changed)
        self.ui.ucp_factor.valueChanged.connect(self._on_factor_constant_changed)
        self.ui.ucp_constant.valueChanged.connect(self._on_factor_constant_changed)
        self.ui.ucp_prop.currentIndexChanged.connect(self._on_prop_changed)

        self.setEnabled(False)

    # ------------------------------------------------------------------
    def bind_ucp(
        self,
        ucp,
        component,
        other_attr: str,
        other_label: str,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        """Bind a UnitCellProperty. `component` supplies the derivation-source
        options (its atoms' pn + the other cell length, named by `other_attr` /
        `other_label`). `on_changed` runs after an accepted edit."""
        self._ucp = ucp
        self._component = component
        self._other_attr = other_attr
        self._other_label = other_label
        self._on_changed = on_changed
        self.setEnabled(ucp is not None)
        if ucp is None:
            return
        self._updating = True
        try:
            self._populate_prop_combo()
            self.ui.ucp_enabled.setChecked(bool(ucp.enabled))
            self.ui.ucp_value.setValue(float(ucp.value))
            self.ui.ucp_factor.setValue(float(ucp.factor))
            self.ui.ucp_constant.setValue(float(ucp.constant))
            self._select_current_prop()
        finally:
            self._updating = False
        self._apply_sensitivity()

    def refresh_value(self) -> None:
        """Re-read the (possibly recomputed) value into the spinbox."""
        if self._ucp is None:
            return
        self._updating = True
        try:
            self.ui.ucp_value.setValue(float(self._ucp.value))
        finally:
            self._updating = False

    # ------------------------------------------------------------------
    def _populate_prop_combo(self) -> None:
        combo = self.ui.ucp_prop
        combo.clear()
        combo.addItem("(none)", None)
        comp = self._component
        for atom in list(comp.layer_atoms) + list(comp.interlayer_atoms):
            combo.addItem(getattr(atom, "name", "") or "atom", (atom, "pn"))
        combo.addItem(self._other_label, (comp, self._other_attr))

    def _select_current_prop(self) -> None:
        combo = self.ui.ucp_prop
        target = self._ucp.prop  # (obj, attr) or None
        idx = 0
        if target is not None:
            for i in range(combo.count()):
                data = combo.itemData(i)
                if data is not None and data[0] is target[0] and data[1] == target[1]:
                    idx = i
                    break
        combo.setCurrentIndex(idx)

    def _apply_sensitivity(self) -> None:
        """Fixed -> the value spin is editable; derived -> the factor/prop/
        constant box is editable (old update_sensitivities)."""
        enabled = bool(self._ucp.enabled) if self._ucp is not None else False
        self.ui.ucp_value.setEnabled(not enabled)
        self.ui.box_enabled.setEnabled(enabled)

    # ------------------------------------------------------------------
    def _on_enabled_toggled(self, checked: bool) -> None:
        if self._ucp is None or self._updating:
            return
        self._ucp.enabled = checked
        self._apply_sensitivity()
        self._notify()

    def _on_value_changed(self, value: float) -> None:
        if self._ucp is None or self._updating:
            return
        self._ucp.value = float(value)  # fixed-value edit
        self._notify()

    def _on_factor_constant_changed(self, _value: float) -> None:
        if self._ucp is None or self._updating:
            return
        self._ucp.factor = float(self.ui.ucp_factor.value())
        self._ucp.constant = float(self.ui.ucp_constant.value())
        self._notify()

    def _on_prop_changed(self, _index: int) -> None:
        if self._ucp is None or self._updating:
            return
        data = self.ui.ucp_prop.currentData()
        if data is None:
            self._ucp.set_prop(None, None)
        else:
            self._ucp.set_prop(data[0], data[1])
        self._notify()

    def _notify(self) -> None:
        if self._on_changed is not None:
            self._on_changed()
