"""Pattern line-operation dialogs (background, smooth, shift, noise,
strip peak, peak properties).

Ported from the GTK dialogs in generic/views/glade/lines/. All are modal;
OK applies the operation to the active specimen once the specimen model
(Qt signals) is ported - accessor properties expose the chosen values.
"""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QFileDialog, QWidget

from mudlab.ui.ui_add_noise import Ui_AddNoiseDialog
from mudlab.ui.ui_background import Ui_RemoveBackgroundDialog
from mudlab.ui.ui_peak_properties import Ui_PeakPropertiesDialog
from mudlab.ui.ui_shifting import Ui_ShiftPatternDialog
from mudlab.ui.ui_smoothing import Ui_SmoothDataDialog
from mudlab.ui.ui_strip_peak import Ui_StripPeakDialog

# Combo index -> old model value maps (settings.py order).
BG_TYPES = (0, 1)  # Linear, Pattern
SMOOTH_TYPES = (0, 1, 2, 3, 4, 5)
SHIFT_POSITIONS = (0.42574, 0.3134, 0.2476, 0.2085, 0.4183, 0.48486, 0.0)
SHIFT_MANUAL_INDEX = len(SHIFT_POSITIONS) - 1  # "Manual"


class RemoveBackgroundDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_RemoveBackgroundDialog()
        self.ui.setupUi(self)
        self.ui.bg_type.currentIndexChanged.connect(
            self.ui.bg_view_stack.setCurrentIndex
        )
        self.ui.btn_browse_bg.clicked.connect(self._browse_pattern)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

    def _browse_pattern(self) -> None:
        # Old: a file chooser button; filters come with the parser port.
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select background pattern file"
        )
        if filename:
            self.ui.bg_pattern_file.setText(filename)


class SmoothDataDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_SmoothDataDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)


class ShiftPatternDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_ShiftPatternDialog()
        self.ui.setupUi(self)
        self.ui.shift_position.currentIndexChanged.connect(self._on_position_changed)
        self._on_position_changed(self.ui.shift_position.currentIndex())
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

    def _on_position_changed(self, index: int) -> None:
        manual = index == SHIFT_MANUAL_INDEX
        if not manual:
            self.ui.spin_shift_value.setValue(SHIFT_POSITIONS[index])
        self.ui.spin_shift_value.setEnabled(manual)


class AddNoiseDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_AddNoiseDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)


class StripPeakDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_StripPeakDialog()
        self.ui.setupUi(self)
        # cmd_sample_start / cmd_sample_end pick positions on the pattern
        # via the eye-dropper; connected with the plot controller port.
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)


class PeakPropertiesDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_PeakPropertiesDialog()
        self.ui.setupUi(self)
        self.ui.btn_copy_results.clicked.connect(self._copy_results)
        self.ui.buttonBox.rejected.connect(self.reject)

    def set_results(self, area: float, fwhm: float) -> None:
        self.ui.peak_area_result.setText(f"{area:.4f}")
        self.ui.peak_fwhm_result.setText(f"{fwhm:.4f}")

    def _copy_results(self) -> None:
        QGuiApplication.clipboard().setText(
            f"Peak area:\t{self.ui.peak_area_result.text()}\n"
            f"FWHM [°2θ]:\t{self.ui.peak_fwhm_result.text()}"
        )
