"""Marker editor form. Design: ui/edit_marker.ui.

Ported from the GTK EditMarkerView (specimen/glade/edit_marker.glade).
Plugged into the Properties pane of the Edit Markers window and bound live
to a Marker model: edits write straight to the marker (Qt signals then
refresh the plot). The 'default' checkboxes are the inherit_* flags; each
disables its paired editor.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from mudlab.models import Marker
from mudlab.qt_utils import ColorButton
from mudlab.ui.ui_edit_marker import Ui_EditMarkerWidget

# Combo index -> old model value (settings.py order).
MARKER_STYLES = ("none", "solid", "dashed", "dotted", "dashdot", "offset")
MARKER_ALIGNS = ("left", "center", "right")
MARKER_BASES = (0, 1, 2, 3, 4)
MARKER_TOPS = (0, 1)


class EditMarkerWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditMarkerWidget()
        self.ui.setupUi(self)

        self._marker: Marker | None = None
        self._updating = False

        self.color = ColorButton(
            self.ui.marker_color,
            on_change=lambda c: self._write("color", c.name()),
        )

        # inherit ("default") checkbox -> flag, plus disables its editor.
        self._inherit_pairs = (
            (self.ui.marker_inherit_color, self.ui.marker_color, "inherit_color"),
            (self.ui.marker_inherit_style, self.ui.marker_style, "inherit_style"),
            (self.ui.marker_inherit_angle, self.ui.spb_angle, "inherit_angle"),
            (self.ui.marker_inherit_align, self.ui.marker_align, "inherit_align"),
            (self.ui.marker_inherit_base, self.ui.marker_base, "inherit_base"),
            (self.ui.marker_inherit_top, self.ui.marker_top, "inherit_top"),
            (self.ui.marker_inherit_top_offset, self.ui.spb_top_offset,
             "inherit_top_offset"),
        )
        for checkbox, editor, flag in self._inherit_pairs:
            checkbox.toggled.connect(
                lambda checked, e=editor, f=flag: (
                    e.setEnabled(not checked), self._write(f, checked)
                )
            )

        self.ui.marker_label.textChanged.connect(lambda t: self._write("label", t))
        self.ui.marker_visible.toggled.connect(lambda v: self._write("visible", v))
        self.ui.spb_position.valueChanged.connect(lambda v: self._write("position", v))
        self.ui.spb_angle.valueChanged.connect(lambda v: self._write("angle", v))
        self.ui.spb_top_offset.valueChanged.connect(
            lambda v: self._write("top_offset", v)
        )
        self.ui.spb_x_offset.valueChanged.connect(lambda v: self._write("x_offset", v))
        self.ui.spb_y_offset.valueChanged.connect(lambda v: self._write("y_offset", v))
        self.ui.marker_style.currentIndexChanged.connect(
            lambda i: self._write("style", MARKER_STYLES[i])
        )
        self.ui.marker_align.currentIndexChanged.connect(
            lambda i: self._write("align", MARKER_ALIGNS[i])
        )
        self.ui.marker_base.currentIndexChanged.connect(
            lambda i: self._write("base", MARKER_BASES[i])
        )
        self.ui.marker_top.currentIndexChanged.connect(
            lambda i: self._write("top", MARKER_TOPS[i])
        )

    def bind_marker(self, marker: Marker | None) -> None:
        self._marker = marker
        self.setEnabled(marker is not None)
        if marker is None:
            return
        self._updating = True
        try:
            u = self.ui
            u.marker_label.setText(marker.label)
            u.marker_visible.setChecked(marker.visible)
            u.spb_position.setValue(marker.position)
            u.spb_nanometer.setValue(marker.get_nm_position())
            u.spb_angle.setValue(marker.angle)
            u.spb_top_offset.setValue(marker.top_offset)
            u.spb_x_offset.setValue(marker.x_offset)
            u.spb_y_offset.setValue(marker.y_offset)
            u.marker_style.setCurrentIndex(_index(MARKER_STYLES, marker.style))
            u.marker_align.setCurrentIndex(_index(MARKER_ALIGNS, marker.align))
            u.marker_base.setCurrentIndex(_index(MARKER_BASES, marker.base))
            u.marker_top.setCurrentIndex(_index(MARKER_TOPS, marker.top))
            self.color.set_color(marker.color)
            for checkbox, editor, flag in self._inherit_pairs:
                checked = getattr(marker, flag)
                checkbox.setChecked(checked)
                editor.setEnabled(not checked)
        finally:
            self._updating = False

    def _write(self, prop: str, value) -> None:
        if self._marker is not None and not self._updating:
            setattr(self._marker, prop, value)
            if prop == "position":
                self._updating = True
                self.ui.spb_nanometer.setValue(self._marker.get_nm_position())
                self._updating = False


def _index(values: tuple, value) -> int:
    return values.index(value) if value in values else 0
