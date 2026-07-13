"""Phase editor form. Design: ui/edit_phase.ui.

Ported from the GTK EditPhaseView (phases/glade/phase.glade). Plugged into
the Properties pane of the Edit Phases window and bound to a real Phase
model.

Editor-wiring batch 2 makes the phase name, sigma* orientation factor and
the CSDS mean editable (the CSDS component, csds.ui, lives in the CSDS
Distribution tab) with a live recalculation of the pattern. The
probabilities and component tabs, plus phase inheritance (based-on chains),
the display colour and the inherit flags, come with later batches and are
disabled for now.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QWidget

from mudlab.component_widget import EditComponentWidget
from mudlab.csds_widget import CSDSWidget
from mudlab.probabilities_widget import ProbabilitiesWidget
from mudlab.qt_utils import ColorButton
from mudlab.ui.ui_edit_phase import Ui_EditPhaseWidget


class EditPhaseWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditPhaseWidget()
        self.ui.setupUi(self)

        self._phase = None
        self._atom_types: list = []
        self._on_changed: Callable[[], None] | None = None
        self._updating = False

        self.color = ColorButton(self.ui.phase_display_color)

        # The CSDS distribution component fills the CSDS tab; hide the
        # "insert here" placeholder label now that the real widget is present.
        self.csds_widget = CSDSWidget(self)
        self.ui.csdsLayout.addWidget(self.csds_widget)
        self.ui.lblCsdsPlaceholder.hide()

        # The probabilities component fills the Probabilities tab (R0 only).
        # The old app removed the tab for single-component (G=1) phases, so we
        # remove/re-insert it per phase; remember its title/position for that.
        self.probabilities_widget = ProbabilitiesWidget(self)
        self.ui.probabilitiesLayout.addWidget(self.probabilities_widget)
        self.ui.lblProbabilitiesPlaceholder.hide()
        self._prob_tab_index = self.ui.book_wrapper.indexOf(self.ui.tabProbabilities)
        self._prob_tab_title = self.ui.book_wrapper.tabText(self._prob_tab_index)

        # The component editor fills the Components tab (always present - every
        # phase has at least one component).
        self.component_widget = EditComponentWidget(self)
        self.ui.componentsLayout.addWidget(self.component_widget)
        self.ui.lblComponentsPlaceholder.hide()

        # The display colour is a visuals-only property that is not modeled yet.
        for control, why in (
            (self.ui.phase_display_color, "Phase display colour is not modeled yet."),
            (self.ui.phase_inherit_display_color,
             "Phase display colour is not modeled yet."),
        ):
            control.setEnabled(False)
            control.setToolTip(why)

        self.ui.phase_name.editingFinished.connect(self._on_name_edited)
        self.ui.phase_sigma_star.valueChanged.connect(self._on_sigma_changed)

        # Phase-level inheritance (old based_on): pick a reference phase, then
        # tick which properties to take from it.
        self.ui.phase_based_on.currentIndexChanged.connect(self._on_based_on_changed)
        self.ui.phase_inherit_sigma_star.toggled.connect(
            lambda checked: self._on_phase_inherit_toggled("sigma_star", checked)
        )
        self.ui.phase_inherit_CSDS_distribution.toggled.connect(
            lambda checked: self._on_phase_inherit_toggled("CSDS_distribution", checked)
        )

        self.setEnabled(False)

    # ------------------------------------------------------------------
    def bind_phase(
        self,
        phase,
        on_changed: Callable[[], None] | None = None,
        atom_types=None,
        link_candidates=None,
        phase_candidates=None,
    ) -> None:
        """Show and edit a real Phase model. `atom_types` feeds the component
        atom-element combos; `link_candidates` are (label, component) pairs
        offered as component-linking templates. `on_changed` runs after every
        accepted edit (used to recompute + redraw the pattern)."""
        self._phase = phase
        self._atom_types = list(atom_types or [])
        self._link_candidates = list(link_candidates or [])
        self._phase_candidates = list(phase_candidates or [])
        self._on_changed = on_changed
        self.setEnabled(phase is not None)
        if phase is None:
            self.csds_widget.bind_csds(None)
            self.probabilities_widget.bind_probabilities(None)
            self._set_probabilities_tab_visible(False)
            self.component_widget.bind_components([])
            return
        self._updating = True
        try:
            self.ui.phase_name.setText(phase.name)
            self.ui.phase_G.setText(str(phase.G))
            self.ui.phase_R.setText(str(getattr(phase.probabilities, "R", 0)))
            self.ui.phase_sigma_star.setValue(float(phase.sigma_star))
        finally:
            self._updating = False
        self.csds_widget.bind_csds(phase.CSDS, on_changed=self._notify)

        # Probabilities tab: R0/G1 single-component phases have no independent
        # variables, so (like the old app) the tab is only shown for G>=2.
        has_probabilities = phase.G >= 2
        self._set_probabilities_tab_visible(has_probabilities)
        if has_probabilities:
            labels = [getattr(c, "name", "") for c in phase.components]
            self.probabilities_widget.bind_probabilities(
                phase.probabilities, labels=labels, on_changed=self._notify,
                can_inherit=phase.based_on is not None,
            )
        else:
            self.probabilities_widget.bind_probabilities(None)

        self._bind_based_on(phase)

        self.component_widget.bind_components(
            phase.components, atom_types=self._atom_types, on_changed=self._notify,
            link_candidates=self._link_candidates,
        )

    # ------------------------------------------------------------------
    # Phase-level inheritance (based_on)
    # ------------------------------------------------------------------
    def _bind_based_on(self, phase) -> None:
        """Fill the "based on" combo (phases with the SAME G - the F params pair
        up one-to-one, as in the old app), the inherit check-boxes, and grey the
        fields that read through to the reference phase."""
        self._updating = True
        try:
            combo = self.ui.phase_based_on
            combo.clear()
            combo.addItem("(not based on)", None)
            current = 0
            for label, cand in self._phase_candidates:
                if cand is phase or cand.G != phase.G:
                    continue
                combo.addItem(label, cand)
                if cand is phase.based_on:
                    current = combo.count() - 1
            combo.setCurrentIndex(current)

            based = phase.based_on is not None
            self.ui.phase_inherit_sigma_star.setChecked(phase.inherit_sigma_star)
            self.ui.phase_inherit_sigma_star.setEnabled(based)
            self.ui.phase_inherit_CSDS_distribution.setChecked(
                phase.inherit_CSDS_distribution
            )
            self.ui.phase_inherit_CSDS_distribution.setEnabled(based)
        finally:
            self._updating = False
        self._apply_phase_inheritance(phase)

    def _apply_phase_inheritance(self, phase) -> None:
        """Grey each field that currently reads through to the based_on phase."""
        self.ui.phase_sigma_star.setDisabled(phase.is_inherited("sigma_star"))
        self.csds_widget.setDisabled(phase.is_inherited("CSDS"))

    def _on_based_on_changed(self, _index: int) -> None:
        if self._phase is None or self._updating:
            return
        target = self.ui.phase_based_on.currentData()
        if target is self._phase.based_on:
            return
        if not self._phase.set_based_on(target):
            self._bind_based_on(self._phase)  # rejected (self / cycle) - revert
            return
        # Rebind so the inherit boxes, the greying and any newly inherited
        # values (sigma*, CSDS, the F params) refresh, then recompute.
        self.bind_phase(
            self._phase, on_changed=self._on_changed, atom_types=self._atom_types,
            link_candidates=self._link_candidates,
            phase_candidates=self._phase_candidates,
        )
        self._notify()

    def _on_phase_inherit_toggled(self, name: str, checked: bool) -> None:
        if self._phase is None or self._updating:
            return
        setattr(self._phase, "inherit_%s" % name, checked)
        self._updating = True
        try:
            # An inherited field shows the reference phase's value.
            self.ui.phase_sigma_star.setValue(float(self._phase.sigma_star))
        finally:
            self._updating = False
        self.csds_widget.bind_csds(self._phase.CSDS, on_changed=self._notify)
        self._apply_phase_inheritance(self._phase)
        self._notify()

    def _set_probabilities_tab_visible(self, visible: bool) -> None:
        tabs = self.ui.book_wrapper
        index = tabs.indexOf(self.ui.tabProbabilities)
        if visible and index == -1:
            tabs.insertTab(
                self._prob_tab_index, self.ui.tabProbabilities, self._prob_tab_title
            )
        elif not visible and index != -1:
            tabs.removeTab(index)

    # ------------------------------------------------------------------
    def _on_name_edited(self) -> None:
        if self._phase is not None and not self._updating:
            self._phase.name = self.ui.phase_name.text()
            self._notify()

    def _on_sigma_changed(self, value: float) -> None:
        if self._phase is not None and not self._updating:
            self._phase.sigma_star = value
            self._notify()

    def _notify(self) -> None:
        if self._on_changed is not None:
            self._on_changed()
