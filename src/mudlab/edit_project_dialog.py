"""Edit Project dialog logic. The design lives in ui/edit_project.ui.

Ported from the GTK ProjectView (project/glade/project.glade, notebook
nbk_edit_project). Modeless and live-applying like the old app:
`bind_project()` fills the widgets from the Project model and edits write
straight back (Qt signals update the title bar and plots).
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QPushButton, QWidget

from mudlab.models import Project
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

        self._project: Project | None = None
        self._updating = False

        # Initial colors come from the button texts set in the .ui file.
        self._color_buttons: dict[QPushButton, ColorButton] = {
            self.ui.project_display_exp_color: ColorButton(
                self.ui.project_display_exp_color,
                on_change=lambda c: self._write("display_exp_color", c.name()),
            ),
            self.ui.project_display_calc_color: ColorButton(
                self.ui.project_display_calc_color,
                on_change=lambda c: self._write("display_calc_color", c.name()),
            ),
            self.ui.project_display_marker_color: ColorButton(
                self.ui.project_display_marker_color,
                on_change=lambda c: self._write("display_marker_color", c.name()),
            ),
        }

        # Widget <-> model property binding tables.
        u = self.ui
        self._text_bindings = (
            (u.project_name, "name"),
            (u.project_author, "author"),
            (u.project_date, "date"),
        )
        self._combo_bindings = (
            (u.project_layout_mode, "layout_mode", LAYOUT_MODES),
            (u.project_axes_ynormalize, "axes_ynormalize", AXES_YNORMALIZERS),
            (u.project_display_exp_ls, "display_exp_ls", PATTERN_LINE_STYLES),
            (u.project_display_calc_ls, "display_calc_ls", PATTERN_LINE_STYLES),
            (u.project_display_exp_marker, "display_exp_marker", PATTERN_MARKERS),
            (u.project_display_calc_marker, "display_calc_marker", PATTERN_MARKERS),
            (u.project_axes_xlimit, "axes_xlimit", AXES_LIMITS),
            (u.project_axes_ylimit, "axes_ylimit", AXES_LIMITS),
            (u.project_display_marker_style, "display_marker_style", MARKER_STYLES),
            (u.project_display_marker_base, "display_marker_base", MARKER_BASES),
            (u.project_display_marker_top, "display_marker_top", MARKER_TOPS),
            (u.project_display_marker_align, "display_marker_align", MARKER_ALIGNS),
        )
        self._spin_bindings = (
            (u.project_display_plot_offset, "display_plot_offset"),
            (u.spin_display_group_by, "display_group_by"),
            (u.project_display_label_pos, "display_label_pos"),
            (u.spin_display_exp_lw, "display_exp_lw"),
            (u.spin_display_calc_lw, "display_calc_lw"),
            (u.spin_project_axes_xmin, "axes_xmin"),
            (u.spin_project_axes_xmax, "axes_xmax"),
            (u.spin_project_axes_ymin, "axes_ymin"),
            (u.spin_project_axes_ymax, "axes_ymax"),
            (u.project_display_marker_angle, "display_marker_angle"),
            (u.project_display_marker_top_offset, "display_marker_top_offset"),
        )
        self._check_bindings = (
            (u.project_axes_xstretch, "axes_xstretch"),
            (u.project_axes_yvisible, "axes_yvisible"),
            (u.project_axes_dspacing, "axes_dspacing"),
        )

        for widget, prop in self._text_bindings:
            widget.textChanged.connect(lambda text, p=prop: self._write(p, text))
        u.project_description.textChanged.connect(
            lambda: self._write("description", u.project_description.toPlainText())
        )
        for widget, prop, values in self._combo_bindings:
            widget.currentIndexChanged.connect(
                lambda index, p=prop, v=values: self._write(p, v[index])
            )
        for widget, prop in self._spin_bindings:
            widget.valueChanged.connect(lambda value, p=prop: self._write(p, value))
        for widget, prop in self._check_bindings:
            widget.toggled.connect(lambda checked, p=prop: self._write(p, checked))

        # Old app toggled the manual-range boxes' sensitivity with the combos.
        self.ui.project_axes_xlimit.currentIndexChanged.connect(self._update_range_enables)
        self.ui.project_axes_ylimit.currentIndexChanged.connect(self._update_range_enables)
        self._update_range_enables()

        self.ui.buttonBox.rejected.connect(self.reject)

    # ------------------------------------------------------------------
    # Model binding (live apply, old adapter behavior)
    # ------------------------------------------------------------------
    def bind_project(self, project: Project) -> None:
        self._project = project
        self._updating = True
        try:
            for widget, prop in self._text_bindings:
                widget.setText(getattr(project, prop))
            self.ui.project_description.setPlainText(project.description)
            for widget, prop, values in self._combo_bindings:
                # Unknown values from old files fall back to the first
                # entry visually; the model keeps the original value.
                value = getattr(project, prop)
                widget.setCurrentIndex(values.index(value) if value in values else 0)
            for widget, prop in self._spin_bindings:
                widget.setValue(getattr(project, prop))
            for widget, prop in self._check_bindings:
                widget.setChecked(getattr(project, prop))
            self._color_buttons[self.ui.project_display_exp_color].set_color(
                project.display_exp_color
            )
            self._color_buttons[self.ui.project_display_calc_color].set_color(
                project.display_calc_color
            )
            self._color_buttons[self.ui.project_display_marker_color].set_color(
                project.display_marker_color
            )
        finally:
            self._updating = False
        self._update_range_enables()

    def _write(self, prop: str, value) -> None:
        if self._project is not None and not self._updating:
            setattr(self._project, prop, value)

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
