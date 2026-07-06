"""Goniometer setup component. Design: ui/goniometer.ui.

Ported from the GTK InlineGoniometerView (goniometer/glade/
goniometer.glade). Plugged into the Edit Specimen Goniometer tab; later
also used wherever a goniometer setup is edited.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from mudlab.ui.ui_goniometer import Ui_GoniometerWidget

# Combo index -> old model value (settings.DIVERGENCE_MODES order).
DIVERGENCE_MODES = ("AUTOMATIC", "FIXED")


class GoniometerWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_GoniometerWidget()
        self.ui.setupUi(self)

        self.ui.gonio_has_soller1.toggled.connect(self.ui.gonio_soller1_spb.setEnabled)
        self.ui.gonio_has_soller2.toggled.connect(self.ui.gonio_soller2_spb.setEnabled)
        self.ui.gonio_has_absorption_correction.toggled.connect(
            self.ui.absorption_spb.setEnabled
        )

        # Old controller swapped the divergence value unit with the mode:
        # FIXED = slit opening angle [°], AUTOMATIC = irradiated length [cm].
        self.ui.gonio_divergence_mode.currentIndexChanged.connect(
            self._on_divergence_mode_changed
        )
        self._on_divergence_mode_changed(self.ui.gonio_divergence_mode.currentIndex())

        # Placeholder until stored goniometer setups are ported (old:
        # cmb_import_gonio listed the default .gon setup files).
        self.ui.cmb_import_gonio.addItem("(select a stored setup)")

    def _on_divergence_mode_changed(self, index: int) -> None:
        if DIVERGENCE_MODES[index] == "AUTOMATIC":
            self.ui.gonio_div_value_spb.setSuffix(" cm")
        else:
            self.ui.gonio_div_value_spb.setSuffix(" °")
