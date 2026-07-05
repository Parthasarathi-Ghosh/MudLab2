"""Small Qt helpers shared by the dialogs."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QPushButton


class ColorButton:
    """Make a plain QPushButton behave like a color swatch button.

    The button shows the current color and its hex code; clicking opens the
    native color dialog. (Replaces the old GtkColorButton.) The initial
    color is read from the button text set in the .ui file.
    """

    def __init__(self, button: QPushButton) -> None:
        self._button = button
        color = QColor(button.text())
        self._color = color if color.isValid() else QColor("#000000")
        self._apply()
        button.clicked.connect(self._pick)

    @property
    def color(self) -> QColor:
        return QColor(self._color)

    def hex(self) -> str:
        return self._color.name()

    def set_color(self, color: QColor | str) -> None:
        color = QColor(color)
        if color.isValid():
            self._color = color
            self._apply()

    def _pick(self) -> None:
        color = QColorDialog.getColor(
            self._color, self._button.window(), "Select color"
        )
        if color.isValid():
            self._color = color
            self._apply()

    def _apply(self) -> None:
        luminance = (
            0.299 * self._color.red()
            + 0.587 * self._color.green()
            + 0.114 * self._color.blue()
        )
        text_color = "#000000" if luminance > 128 else "#ffffff"
        self._button.setText(self._color.name())
        self._button.setStyleSheet(
            f"background-color: {self._color.name()}; color: {text_color};"
        )
