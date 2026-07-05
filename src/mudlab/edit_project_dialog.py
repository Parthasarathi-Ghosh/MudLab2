"""Edit Project dialog logic. The design lives in ui/edit_project.ui.

Ported from the GTK ProjectView (project/glade/project.glade, notebook
nbk_edit_project). Like the old app, the dialog is modeless and changes are
meant to apply to the project live; see ui/WIRING.md for the field mapping.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QPushButton, QWidget

from mudlab.qt_utils import ColorButton
from mudlab.ui.ui_edit_project import Ui_EditProjectDialog

# Combo index -> old model value (order matches the .ui item order).
LAYOUT_MODES = ("FULL", "VIEWER")  # temporary: only FULL will be used
AXES_YNORMALIZERS = (0, 1, 2)
AXES_LIMITS = (0, 1)  # Automatic, Manual (x and y alike)
PATTERN_LINE_STYLES = ("", "-", "--", "-.", ":")
PATTERN_MARKERS = (
    "", ".", ",", "+", "x", "D", "o", "v", "^", "<", ">", "8", "s", "p", "*", "h",
)
MARKER_STYLES = ("none", "solid", "dashed", "dotted", "dashdot", "offset")
MARKER_BASES = (0, 1, 2, 3, 4)
MARKER_TOPS = (0, 1)
MARKER_ALIGNS = ("left", "center", "right")


class EditProjectDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditProjectDialog()
        self.ui.setupUi(self)

        # Initial colors come from the button texts set in the .ui file.
        self._color_buttons: dict[QPushButton, ColorButton] = {
            button: ColorButton(button)
            for button in (
                self.ui.project_display_exp_color,
                self.ui.project_display_calc_color,
                self.ui.project_display_marker_color,
            )
        }

        # Old app toggled the manual-range boxes' sensitivity with the combos.
        self.ui.project_axes_xlimit.currentIndexChanged.connect(self._update_range_enables)
        self.ui.project_axes_ylimit.currentIndexChanged.connect(self._update_range_enables)
        self._update_range_enables()

        self.ui.buttonBox.rejected.connect(self.reject)

    # ------------------------------------------------------------------
    # Color buttons (old GtkColorButtons; native Windows color dialog)
    # ------------------------------------------------------------------
    def button_color(self, button: QPushButton) -> str:
        """Hex color currently held by one of the color buttons."""
        return self._color_buttons[button].hex()

    # ------------------------------------------------------------------
    # Enable/disable the manual axis ranges
    # ------------------------------------------------------------------
    def _update_range_enables(self) -> None:
        manual_x = self.ui.project_axes_xlimit.currentIndex() == 1
        self.ui.spin_project_axes_xmin.setEnabled(manual_x)
        self.ui.spin_project_axes_xmax.setEnabled(manual_x)
        self.ui.lblXMin.setEnabled(manual_x)
        self.ui.lblXMax.setEnabled(manual_x)

        manual_y = self.ui.project_axes_ylimit.currentIndex() == 1
        self.ui.spin_project_axes_ymin.setEnabled(manual_y)
        self.ui.spin_project_axes_ymax.setEnabled(manual_y)
        self.ui.lblYMin.setEnabled(manual_y)
        self.ui.lblYMax.setEnabled(manual_y)
