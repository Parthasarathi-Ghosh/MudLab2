"""Import Non-Clay phase dialog (experimental "path 2"). Design: ui/import_nonclay.ui.

Creates a :class:`~mudlab.models.nonclay_phase.NonClayPhase` from either:
  - a **measured pattern** file (.xy/.xrdml/.uxd/.raw/.rasx/...) - the oxide
    composition is entered by hand (mandatory); or
  - a **CIF with atoms** - ``nonclay.structure.reference_from_cif`` computes both
    the pattern and the oxide composition (editable afterwards).

A non-clay phase always needs a pattern (it contributes to the fit and its
fraction is optimised), so OK is refused until a pattern is loaded and at least
one oxide is > 0. Composition wiring and a formula parser are deferred.
"""

from __future__ import annotations

import os

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget

from mudlab.chart_style import INK_SECONDARY, SERIES_BLUE, SURFACE, style_axes
from mudlab.csv_import_dialog import import_pattern
from mudlab.file_parsers.xrd_import import PATTERN_FILTERS
from mudlab.models import Goniometer
from mudlab.models.nonclay_phase import NonClayPhase
from mudlab.nonclay.structure import reference_from_cif
from mudlab.oxide_grid import OxideGrid
from mudlab.qt_utils import ColorButton
from mudlab.ui.ui_import_nonclay import Ui_ImportNonClayDialog

_SOURCE_FILTERS = (
    "Pattern or CIF (*.xy *.txt *.csv *.dat *.tab *.xrdml *.uxd *.raw *.rasx "
    "*.rd *.cif);;CIF with atoms (*.cif);;" + PATTERN_FILTERS
)


class ImportNonClayDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, goniometer=None) -> None:
        super().__init__(parent)
        self.ui = Ui_ImportNonClayDialog()
        self.ui.setupUi(self)
        # A CIF pattern is computed at this wavelength; default to CuKα when the
        # project has no specimen goniometer to borrow.
        self._goniometer = goniometer if goniometer is not None else Goniometer()
        self.phase: NonClayPhase | None = None  # set on accept
        self._x = np.empty(0)
        self._y = np.empty(0)

        self.color = ColorButton(self.ui.button_color)
        self.grid = OxideGrid(self.ui.oxide_grid, on_changed=self._update_sum)

        self.figure = Figure(facecolor=SURFACE, layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(180)
        self.ui.previewLayout.addWidget(self.canvas)
        self.axes = self.figure.add_subplot(111)

        self.ui.button_open_file.clicked.connect(self._on_open_file)
        self.ui.button_normalize.clicked.connect(self.grid.normalize)
        self.ui.buttonBox.accepted.connect(self._on_accept)
        self.ui.buttonBox.rejected.connect(self.reject)

        self._update_sum()
        self._update_preview()

    # ------------------------------------------------------------------
    def _on_open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open pattern or CIF", "", _SOURCE_FILTERS
        )
        if not path:
            return
        if path.lower().endswith(".cif"):
            self._load_cif(path)
        else:
            self._load_pattern(path)

    def _load_cif(self, path: str) -> None:
        try:
            reference, oxides = reference_from_cif(
                path, self._goniometer, fwhm=self.ui.spin_fwhm.value()
            )
        except Exception as exc:  # noqa: BLE001 - reference_from_cif raises ValueError
            QMessageBox.warning(
                self, "Import non-clay phase",
                "Could not build a phase from this CIF:\n\n%s" % exc,
            )
            return
        self._x = np.asarray(reference.raw_pattern_x, dtype=float)
        self._y = np.asarray(reference.raw_pattern_y, dtype=float)
        self.grid.set_values(oxides)
        self._default_name(path)
        self.ui.lbl_source.setText(
            "Computed from CIF: %s  (%d oxides, %d points)"
            % (os.path.basename(path), len(oxides), self._x.size)
        )
        self._update_preview()

    def _load_pattern(self, path: str) -> None:
        result = import_pattern(self, path=path, title="Import measured pattern")
        if result is None:
            return
        self._x = np.asarray(result[0], dtype=float)
        self._y = np.asarray(result[1], dtype=float)
        self._default_name(path)
        self.ui.lbl_source.setText(
            "Measured pattern: %s  (%d points) - enter the oxides below."
            % (os.path.basename(path), self._x.size)
        )
        self._update_preview()

    def _default_name(self, path: str) -> None:
        if not self.ui.edit_name.text().strip():
            self.ui.edit_name.setText(os.path.splitext(os.path.basename(path))[0])

    # ------------------------------------------------------------------
    def _update_sum(self) -> None:
        self.ui.lbl_sum.setText("Sum: %.2f %%" % self.grid.total())

    def _update_preview(self) -> None:
        self.axes.clear()
        if self._x.size >= 2:
            self.axes.plot(self._x, self._y, color=SERIES_BLUE, linewidth=1.0)
            self.axes.set_xlabel("2θ [deg]", color=INK_SECONDARY)
            self.axes.set_ylabel("Intensity", color=INK_SECONDARY)
        style_axes(self.axes)
        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    def _on_accept(self) -> None:
        name = self.ui.edit_name.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Import non-clay phase", "Enter a phase name."
            )
            return
        if self._x.size < 2:
            QMessageBox.warning(
                self, "Import non-clay phase",
                "Load a pattern file or a CIF first - a non-clay phase needs a "
                "pattern to contribute to the fit.",
            )
            return
        if self.grid.total() <= 0:
            QMessageBox.warning(
                self, "Import non-clay phase",
                "Enter the oxide composition (at least one oxide must be > 0).",
            )
            return
        phase = NonClayPhase(name=name)
        phase.display_color = self.color.hex()
        phase.set_raw_pattern(self._x, self._y)
        phase.set_oxides(self.grid.values())
        self.phase = phase
        self.accept()
