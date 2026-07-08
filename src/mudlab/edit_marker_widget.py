"""Marker editor form. Design: ui/edit_marker.ui.

Ported from the GTK EditMarkerView (specimen/glade/edit_marker.glade).
Plugged into the Properties pane of the Edit Markers window. The 'default'
checkboxes are the old inherit_* flags (value comes from the project
marker display settings); each disables its paired editor.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from mudlab.qt_utils import ColorButton
from mudlab.ui.ui_edit_marker import Ui_EditMarkerWidget

# Combo index -> old model value (settings.py order), shared with the
# project marker display settings.
MARKER_STYLES = ("none", "solid", "dashed", "dotted", "dashdot", "offset")
MARKER_ALIGNS = ("left", "center", "right")
MARKER_BASES = (0, 1, 2, 3, 4)
MARKER_TOPS = (0, 1)


class EditMarkerWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditMarkerWidget()
        self.ui.setupUi(self)

        self.color = ColorButton(self.ui.marker_color)

        # 'default' (inherit) checkboxes disable their paired editors.
        for checkbox, editor in (
            (self.ui.marker_inherit_color, self.ui.marker_color),
            (self.ui.marker_inherit_style, self.ui.marker_style),
            (self.ui.marker_inherit_angle, self.ui.spb_angle),
            (self.ui.marker_inherit_align, self.ui.marker_align),
            (self.ui.marker_inherit_base, self.ui.marker_base),
            (self.ui.marker_inherit_top, self.ui.marker_top),
            (self.ui.marker_inherit_top_offset, self.ui.spb_top_offset),
        ):
            checkbox.toggled.connect(
                lambda checked, e=editor: e.setEnabled(not checked)
            )
            editor.setEnabled(not checkbox.isChecked())

    def set_marker_placeholder(self, label: str, position: float) -> None:
        """Show placeholder values until the marker model (Qt signals) exists."""
        self.ui.marker_label.setText(label)
        self.ui.spb_position.setValue(position)
