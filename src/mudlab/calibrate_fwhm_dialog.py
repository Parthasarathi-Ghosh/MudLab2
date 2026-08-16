"""Calibrate peak FWHM dialog (path-2 phase B, batch 2). Design: ui/calibrate_fwhm.ui.

Fit the instrumental peak width by matching a standard's computed pattern to a
measured scan of that standard (default standard: built-in Silicon; any CIF
works). A 2theta zero-shift is fitted alongside the width so displacement does
not inflate it. On OK, ``dialog.fwhm`` holds the fitted width for the caller to
apply. Read-only: nothing here mutates a model.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QMessageBox, QWidget,
)

from mudlab.chart_style import INK_SECONDARY, SERIES_BLUE, SURFACE, style_axes
from mudlab.csv_import_dialog import import_pattern
from mudlab.nonclay_calibration import calibrate_fwhm, silicon_reflections
from mudlab.nonclay.structure import reflections_from_cif
from mudlab.ui.ui_calibrate_fwhm import Ui_CalibrateFwhmDialog

_FIT_COLOR = "#e8720c"  # orange, to contrast the blue measured curve


class CalibrateFwhmDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, wavelength_nm: float = 0.154056) -> None:
        super().__init__(parent)
        self.ui = Ui_CalibrateFwhmDialog()
        self.ui.setupUi(self)

        self._wavelength_nm = float(wavelength_nm)
        self._reflections = silicon_reflections()
        self._mx = None
        self._my = None
        self._result = None
        self.fwhm: float | None = None  # set on a successful fit; read on OK

        self.figure = Figure(facecolor=SURFACE, layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(180)
        self.ui.previewLayout.addWidget(self.canvas)
        self.axes = self.figure.add_subplot(111)

        self.ui.lbl_wavelength.setText("%.5f nm" % self._wavelength_nm)
        self.ui.button_standard.clicked.connect(self._on_load_standard)
        self.ui.button_measured.clicked.connect(self._on_load_measured)
        self.ui.button_fit.clicked.connect(self._on_fit)
        self.ui.buttonBox.accepted.connect(self._on_accept)
        self.ui.buttonBox.rejected.connect(self.reject)

        self._ok_enabled(False)
        self._draw_preview()

    # ------------------------------------------------------------------
    def _ok_enabled(self, enabled: bool) -> None:
        button = self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        if button is not None:
            button.setEnabled(enabled)

    def _on_load_standard(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Standard CIF", "", "CIF with atoms (*.cif)"
        )
        if not path:
            return
        try:
            reflections, _ox = reflections_from_cif(
                path, SimpleNamespace(wavelength=self._wavelength_nm)
            )
        except Exception as exc:  # noqa: BLE001 - reflections_from_cif raises ValueError
            QMessageBox.warning(
                self, "Calibrate FWHM", "Could not read this CIF:\n\n%s" % exc
            )
            return
        self._reflections = reflections
        self.ui.lbl_standard.setText(os.path.basename(path))
        self._invalidate()

    def _on_load_measured(self) -> None:
        result = import_pattern(self, title="Open measured standard pattern")
        if result is None:
            return
        self._mx = np.asarray(result[0], dtype=float)
        self._my = np.asarray(result[1], dtype=float)
        self.ui.lbl_measured.setText("%d points" % self._mx.size)
        self._invalidate()

    def _invalidate(self) -> None:
        """A source changed: drop the previous fit until the user re-fits."""
        self._result = None
        self.fwhm = None
        self._ok_enabled(False)
        self.ui.lbl_result.setText("Open a measured pattern, then Fit.")
        self._draw_preview()

    def _on_fit(self) -> None:
        if self._mx is None or self._mx.size < 5:
            QMessageBox.information(
                self, "Calibrate FWHM", "Open a measured standard pattern first."
            )
            return
        self._result = calibrate_fwhm(
            self._reflections, self._wavelength_nm, self._mx, self._my
        )
        self.fwhm = self._result.fwhm
        self.ui.lbl_result.setText(
            "FWHM = %.3f °2θ    (shift %+.3f°, residual %.3f)"
            % (self._result.fwhm, self._result.shift, self._result.residual)
        )
        self._ok_enabled(True)
        self._draw_preview()

    def _draw_preview(self) -> None:
        self.axes.clear()
        result = self._result
        if result is not None:
            self.axes.plot(result.two_theta, result.measured, color=SERIES_BLUE,
                           linewidth=1.0, label="measured")
            self.axes.plot(result.two_theta, result.fitted, color=_FIT_COLOR,
                           linewidth=1.2, label="fitted standard")
            self.axes.legend(loc="upper right", fontsize=8)
            self.axes.set_xlabel("2θ [deg]", color=INK_SECONDARY)
            self.axes.set_ylabel("Intensity", color=INK_SECONDARY)
        style_axes(self.axes)
        self.canvas.draw_idle()

    @property
    def apply_to_all(self) -> bool:
        """Whether to set the fitted width on every computed non-clay phase."""
        return self.ui.chk_apply_all.isChecked()

    def _on_accept(self) -> None:
        if self.fwhm is None:
            return  # nothing fitted yet: OK is disabled, but guard anyway
        self.accept()
