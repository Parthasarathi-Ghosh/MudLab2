"""Reusable per-pattern line style editor. Design: ui/line_properties.ui.

Ported from the old inline ExperimentalLinePropertiesView /
CalculatedLinePropertiesView (generic/views/glade/lines/
experimental_props.glade and calculated_props.glade). Each 'Use default X'
checkbox inherits the value from the project settings and disables its
paired editor; the cut-off row exists only on the experimental variant.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from mudlab.qt_utils import ColorButton
from mudlab.ui.ui_line_properties import Ui_LinePropertiesWidget


class LinePropertiesWidget(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        with_cap: bool = True,
        default_color: str = "#000000",
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_LinePropertiesWidget()
        self.ui.setupUi(self)

        self.color = ColorButton(self.ui.color_button)
        self.color.set_color(default_color)

        pairs = (
            (self.ui.inherit_color, self.ui.color_button),
            (self.ui.inherit_lw, self.ui.linewidth),
            (self.ui.inherit_ls, self.ui.linestyle),
            (self.ui.inherit_marker, self.ui.marker),
        )
        for checkbox, editor in pairs:
            checkbox.toggled.connect(
                lambda checked, e=editor: e.setEnabled(not checked)
            )
            editor.setEnabled(not checkbox.isChecked())

        if not with_cap:
            # Old CalculatedLinePropertiesView had no cut-off value row.
            self.ui.lblCap.hide()
            self.ui.cap_value.hide()
