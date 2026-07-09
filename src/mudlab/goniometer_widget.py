"""Goniometer setup component. Design: ui/goniometer.ui.

Ported from the GTK InlineGoniometerView (goniometer/glade/
goniometer.glade). Plugged into the Edit Specimen Goniometer tab and bound
live to a Goniometer model: edits write straight to the model (used by the
intensity-correction calculations).
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from mudlab.models import Goniometer
from mudlab.ui.ui_goniometer import Ui_GoniometerWidget

# Combo index -> old model value (goniometer.ui item order).
DIVERGENCE_MODES = ("AUTOMATIC", "FIXED")


class GoniometerWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_GoniometerWidget()
        self.ui.setupUi(self)

        self._goniometer: Goniometer | None = None
        self._updating = False

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

        # Widget <-> model bindings.
        self._spin_bindings = (
            (self.ui.gonio_radius_spb, "radius"),
            (self.ui.gonio_min_2theta_spb, "min_2theta"),
            (self.ui.gonio_max_2theta_spb, "max_2theta"),
            (self.ui.gonio_div_value_spb, "divergence"),
            (self.ui.gonio_soller1_spb, "soller1"),
            (self.ui.gonio_soller2_spb, "soller2"),
            (self.ui.gonio_mcr2t_spb, "mcr_2theta"),
            (self.ui.sample_length_spb, "sample_length"),
            (self.ui.sample_surf_density_spb, "sample_surf_density"),
            (self.ui.absorption_spb, "absorption"),
        )
        self._check_bindings = (
            (self.ui.gonio_has_soller1, "has_soller1"),
            (self.ui.gonio_has_soller2, "has_soller2"),
            (self.ui.gonio_has_absorption_correction, "has_absorption_correction"),
        )
        for spin, prop in self._spin_bindings:
            spin.valueChanged.connect(lambda v, p=prop: self._write(p, v))
        for check, prop in self._check_bindings:
            check.toggled.connect(lambda v, p=prop: self._write(p, v))
        self.ui.steps_spn_btn1.valueChanged.connect(lambda v: self._write("steps", v))
        self.ui.gonio_divergence_mode.currentIndexChanged.connect(
            lambda i: self._write("divergence_mode", DIVERGENCE_MODES[i])
        )

        self.setEnabled(False)

    def bind_goniometer(self, goniometer: Goniometer | None) -> None:
        self._goniometer = goniometer
        self.setEnabled(goniometer is not None)
        if goniometer is None:
            return
        self._updating = True
        try:
            for spin, prop in self._spin_bindings:
                spin.setValue(getattr(goniometer, prop))
            for check, prop in self._check_bindings:
                check.setChecked(getattr(goniometer, prop))
            self.ui.steps_spn_btn1.setValue(int(goniometer.steps))
            mode = goniometer.divergence_mode
            self.ui.gonio_divergence_mode.setCurrentIndex(
                DIVERGENCE_MODES.index(mode) if mode in DIVERGENCE_MODES else 1
            )
        finally:
            self._updating = False

    def _write(self, prop: str, value) -> None:
        if self._goniometer is not None and not self._updating:
            setattr(self._goniometer, prop, value)

    def _on_divergence_mode_changed(self, index: int) -> None:
        if DIVERGENCE_MODES[index] == "AUTOMATIC":
            self.ui.gonio_div_value_spb.setSuffix(" cm")
        else:
            self.ui.gonio_div_value_spb.setSuffix(" °")
