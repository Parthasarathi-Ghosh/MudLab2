"""Goniometer setup component. Design: ui/goniometer.ui.

Ported from the GTK InlineGoniometerView (goniometer/glade/
goniometer.glade). Plugged into the Edit Specimen Goniometer tab and bound
live to a Goniometer model: edits write straight to the model (used by the
intensity-correction calculations).
"""

from __future__ import annotations

import os

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from mudlab.file_parsers.gon_file import (
    DEFAULT_GONIO_DIR, list_setups_in, load_gon, save_gon,
)
from mudlab.models import Goniometer
from mudlab.ui.ui_goniometer import Ui_GoniometerWidget
from mudlab.wavelength_distribution_dialog import WavelengthDistributionDialog

# Combo index -> old model value (goniometer.ui item order).
DIVERGENCE_MODES = ("AUTOMATIC", "FIXED")
_GON_FILTER = "Goniometer setup (*.gon);;All files (*)"


def _user_gonio_dir(create: bool = False) -> str:
    """Writable directory for user-stored goniometer setups (the bundled
    presets are read-only). Created on demand when `create` is set."""
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    path = os.path.join(base or os.path.expanduser("~"), "goniometer setups")
    if create:
        os.makedirs(path, exist_ok=True)
    return path


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

        # Stored goniometer setups: bundled presets + the user's saved ones.
        # "Load setup" applies one; "Store setup" saves the current goniometer.
        self._populate_setups()
        self.ui.cmb_import_gonio.activated.connect(self._on_load_setup)
        self.ui.btn_export_gonio.clicked.connect(self._on_store_setup)

        # Edit emission spectrum (wavelength distribution) editor.
        self.ui.btn_edit_wld.clicked.connect(self._on_edit_wld)

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
        self.ui.cmb_import_gonio.setCurrentIndex(0)
        self._set_applied_label("")  # the source setup of a bound gonio is unknown
        if goniometer is None:
            return
        self._refresh_fields()

    def _refresh_fields(self) -> None:
        """Reflect the bound goniometer's values into every widget (used on bind
        and after a stored setup is loaded)."""
        goniometer = self._goniometer
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
        self._refresh_wavelength_label()

    def _refresh_wavelength_label(self) -> None:
        """Show the current dominant (highest-fraction) wavelength on the label."""
        if self._goniometer is not None:
            self.ui.gonio_lambda_lbl.setText(
                "Wavelength (λ): %.5f nm" % self._goniometer.wavelength
            )
        else:
            self.ui.gonio_lambda_lbl.setText("Wavelength (λ)")

    def _on_edit_wld(self) -> None:
        if self._goniometer is None:
            return
        WavelengthDistributionDialog(self, goniometer=self._goniometer).exec()
        # The dominant wavelength may have changed.
        self._refresh_wavelength_label()

    # ------------------------------------------------------------------
    # Stored goniometer setups (.gon)
    # ------------------------------------------------------------------
    def _populate_setups(self) -> None:
        """Fill the Load-setup combo: a placeholder first, then the bundled
        presets and any user-saved setups (data = the .gon path)."""
        combo = self.ui.cmb_import_gonio
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("(select a stored setup)", None)
        for name, path in list_setups_in(DEFAULT_GONIO_DIR):
            combo.addItem(name, path)
        for name, path in list_setups_in(_user_gonio_dir()):
            combo.addItem(name + " (custom)", path)
        combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _on_load_setup(self, index: int) -> None:
        """Apply the selected stored setup to the bound goniometer (after
        confirmation). Bound to `activated`, so it only fires on a user pick."""
        path = self.ui.cmb_import_gonio.itemData(index)
        if self._goniometer is None or not path:
            return
        name = self.ui.cmb_import_gonio.itemText(index)
        reply = QMessageBox.question(
            self, "Load goniometer setup",
            "Replace the current goniometer settings with “%s”?" % name,
        )
        # Reset to the placeholder so re-picking the same setup fires again.
        self.ui.cmb_import_gonio.setCurrentIndex(0)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            props = load_gon(path)
        except Exception as exc:  # noqa: BLE001 - surface any parse/IO error
            QMessageBox.warning(
                self, "Load goniometer setup",
                "Could not read the setup:\n%s\n\n%s" % (path, exc),
            )
            return
        self._goniometer.apply_setup(props)
        self._refresh_fields()
        self._set_applied_label(name)

    def _on_store_setup(self) -> None:
        """Save the current goniometer as a `.gon` file (defaults to the user
        setups folder), then refresh the combo so it appears."""
        if self._goniometer is None:
            return
        start_dir = _user_gonio_dir(create=True)
        path, _ = QFileDialog.getSaveFileName(
            self, "Store goniometer setup", start_dir, _GON_FILTER
        )
        if not path:
            return
        if not path.lower().endswith(".gon"):
            path += ".gon"
        try:
            save_gon(path, self._goniometer.to_dict())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self, "Store goniometer setup",
                "Could not save the setup:\n%s\n\n%s" % (path, exc),
            )
            return
        self._populate_setups()
        self._set_applied_label(os.path.splitext(os.path.basename(path))[0])

    def _set_applied_label(self, name: str) -> None:
        self.ui.lbl_applied_gonio.setText(("Goniometer: %s" % name) if name else "")

    def _write(self, prop: str, value) -> None:
        if self._goniometer is not None and not self._updating:
            setattr(self._goniometer, prop, value)

    def _on_divergence_mode_changed(self, index: int) -> None:
        if DIVERGENCE_MODES[index] == "AUTOMATIC":
            self.ui.gonio_div_value_spb.setSuffix(" cm")
        else:
            self.ui.gonio_div_value_spb.setSuffix(" °")
