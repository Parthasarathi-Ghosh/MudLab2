"""Component (clay layer) editor. Design: ui/edit_component.ui.

Ported from the GTK EditComponentView (phases/glade/component.glade). A
phase has G components (clay layers); a selector picks one, and this
sub-batch makes the c-axis scalars editable - the name, basal spacing
(d001 / cell length c), default c length and the delta-c defect spread -
with the derived cell a/b, volume and charge balance shown read-only.
Layer/interlayer atom lists come with the next sub-batch (they fill the
group-box placeholders here).

Plugged into the Edit Phases > Components tab and bound to the phase's
Component models; editing a scalar recomputes the structure factor and,
via the phase editor's callback, the calculated pattern.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QWidget

from mudlab.ui.ui_edit_component import Ui_EditComponentWidget


class EditComponentWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditComponentWidget()
        self.ui.setupUi(self)

        self._components: list = []
        self._component = None
        self._on_changed: Callable[[], None] | None = None
        self._updating = False

        self.ui.cmb_component.currentIndexChanged.connect(self._on_component_selected)
        self.ui.component_name.editingFinished.connect(self._on_name_edited)
        self.ui.component_d001.valueChanged.connect(
            lambda v: self._on_scalar_changed("d001", v)
        )
        self.ui.component_default_c.valueChanged.connect(
            lambda v: self._on_scalar_changed("default_c", v)
        )
        self.ui.component_delta_c.valueChanged.connect(
            lambda v: self._on_scalar_changed("delta_c", v)
        )

        self.setEnabled(False)

    # ------------------------------------------------------------------
    def bind_components(self, components, on_changed: Callable[[], None] | None = None) -> None:
        """Show and edit a phase's Component list. `on_changed` runs after an
        accepted scalar edit (used to recompute + redraw the pattern)."""
        self._components = list(components or [])
        self._on_changed = on_changed
        self.setEnabled(bool(self._components))

        self._updating = True
        try:
            self.ui.cmb_component.clear()
            for i, comp in enumerate(self._components):
                self.ui.cmb_component.addItem(
                    getattr(comp, "name", "") or "Component %d" % (i + 1)
                )
        finally:
            self._updating = False

        if self._components:
            self._bind_one(0)
        else:
            self._component = None

    def _bind_one(self, index: int) -> None:
        if not (0 <= index < len(self._components)):
            return
        self._component = self._components[index]
        comp = self._component
        self._updating = True
        try:
            self.ui.component_name.setText(comp.name)
            self.ui.component_d001.setValue(float(comp.d001))
            self.ui.component_default_c.setValue(float(comp.default_c))
            self.ui.component_delta_c.setValue(float(comp.delta_c))
        finally:
            self._updating = False
        self._refresh_derived()

    # ------------------------------------------------------------------
    def _on_component_selected(self, index: int) -> None:
        if not self._updating:
            self._bind_one(index)

    def _on_name_edited(self) -> None:
        if self._component is not None and not self._updating:
            self._component.name = self.ui.component_name.text()
            # Keep the selector label in step with the edited name.
            self._updating = True
            try:
                self.ui.cmb_component.setItemText(
                    self.ui.cmb_component.currentIndex(), self._component.name
                )
            finally:
                self._updating = False
            self._notify()

    def _on_scalar_changed(self, prop: str, value: float) -> None:
        if self._component is not None and not self._updating:
            setattr(self._component, prop, value)
            self._refresh_derived()
            self._notify()

    def _refresh_derived(self) -> None:
        comp = self._component
        if comp is None:
            return
        self.ui.component_cell_a.setText("%.4f" % comp.cell_a)
        self.ui.component_cell_b.setText("%.4f" % comp.cell_b)
        self.ui.component_volume.setText("%.5f" % comp.volume)
        layer, interlayer, net = comp.compute_charge_balance()
        self.ui.component_charge.setText(
            "layer %+.2f / interlayer %+.2f / net %+.2f" % (layer, interlayer, net)
        )

    def _notify(self) -> None:
        if self._on_changed is not None:
            self._on_changed()
