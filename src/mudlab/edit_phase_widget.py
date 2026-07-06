"""Phase editor form. Design: ui/edit_phase.ui.

Ported from the GTK EditPhaseView (phases/glade/phase.glade). Plugged into
the Properties pane of the Edit Phases window; the CSDS distribution,
probabilities, and component editor components plug into its tab
placeholders later (old: set_csds_view / set_probabilities_view /
set_components_view).
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from mudlab.qt_utils import ColorButton
from mudlab.ui.ui_edit_phase import Ui_EditPhaseWidget


class EditPhaseWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditPhaseWidget()
        self.ui.setupUi(self)

        self.color = ColorButton(self.ui.phase_display_color)

        # Inherit checkboxes disable their paired editors; they are only
        # meaningful (enabled) when a "based on" phase is selected.
        self.ui.phase_inherit_display_color.toggled.connect(
            lambda checked: self.ui.phase_display_color.setEnabled(not checked)
        )
        self.ui.phase_inherit_sigma_star.toggled.connect(
            lambda checked: self.ui.phase_sigma_star.setEnabled(not checked)
        )
        self.ui.phase_inherit_CSDS_distribution.toggled.connect(
            self._on_inherit_csds_toggled
        )
        self.ui.phase_based_on.currentIndexChanged.connect(self._on_based_on_changed)
        self._on_based_on_changed(self.ui.phase_based_on.currentIndex())

    def set_phase_placeholder(self, name: str, R: int, G: int) -> None:
        """Show placeholder values until the phase model (Qt signals) exists."""
        self.ui.phase_name.setText(name)
        self.ui.phase_R.setText(str(R))
        self.ui.phase_G.setText(str(G))

    def _on_inherit_csds_toggled(self, checked: bool) -> None:
        # Old set_csds_sensitive: the CSDS editor grays out when inherited.
        # Applies to the CSDS component once inserted into csdsLayout.
        for i in range(self.ui.csdsLayout.count()):
            widget = self.ui.csdsLayout.itemAt(i).widget()
            if widget is not None:
                widget.setEnabled(not checked)

    def _on_based_on_changed(self, index: int) -> None:
        # Old app: inherit flags only make sense with a based-on phase.
        has_base = index > 0
        for checkbox in (
            self.ui.phase_inherit_display_color,
            self.ui.phase_inherit_sigma_star,
            self.ui.phase_inherit_CSDS_distribution,
        ):
            if not has_base:
                checkbox.setChecked(False)
            checkbox.setEnabled(has_base)
