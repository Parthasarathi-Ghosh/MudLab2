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

        # Not modeled yet: phase inheritance (based-on chains), the display
        # colour and every inherit flag. Disable them so the UI reads
        # honestly; they come with the phase-visuals / inheritance batch.
        for control, why in (
            (self.ui.phase_display_color, "Phase display colour is not modeled yet."),
            (self.ui.phase_inherit_display_color, "Phase inheritance is not ported yet."),
            (self.ui.phase_based_on, "Phase inheritance (based-on) is not ported yet."),
            (self.ui.phase_inherit_sigma_star, "Phase inheritance is not ported yet."),
            (self.ui.phase_inherit_CSDS_distribution, "Phase inheritance is not ported yet."),
        ):
            control.setEnabled(False)
            control.setToolTip(why)

        self.ui.phase_name.editingFinished.connect(self._on_name_edited)
        self.ui.phase_sigma_star.valueChanged.connect(self._on_sigma_changed)

        self.setEnabled(False)

    # ------------------------------------------------------------------
    def bind_phase(self, phase, on_changed: Callable[[], None] | None = None) -> None:
        """Show and edit a real Phase model. `on_changed` runs after every
        accepted edit (used to recompute + redraw the pattern)."""
        self._phase = phase
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
                phase.probabilities, labels=labels, on_changed=self._notify
            )
        else:
            self.probabilities_widget.bind_probabilities(None)

        self.component_widget.bind_components(phase.components, on_changed=self._notify)

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
