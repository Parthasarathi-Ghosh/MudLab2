"""The component's structure diagram, in a window. Design: ui/structure_diagram.ui.

Port of the old app's Show Structure dialog (`component_controllers.
on_btn_show_structure_clicked`), which built a 740x540 modal with a scrolled
text view. Same size, same read-only text, plus Copy and Save - the old one
could only be read on screen, and a cross-section is the kind of thing that ends
up in a notebook.

MODELESS, unlike the old one. The diagram is a reference you read WHILE editing
the component it describes; a modal would force you to close it before changing
the d001 it shows. `refresh()` re-renders it in place.
"""

from __future__ import annotations

import os

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QMessageBox, QWidget,
)

from mudlab.qt_utils import fixed_font
from mudlab.component_diagram import build_structure_diagram
from mudlab.ui.ui_structure_diagram import Ui_StructureDiagramDialog


class StructureDiagramDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, component=None,
                 phase_name: str = "") -> None:
        super().__init__(parent)
        self.ui = Ui_StructureDiagramDialog()
        self.ui.setupUi(self)
        self._component = component
        self._phase_name = phase_name

        # The diagram aligns its columns with spaces, so it is only a diagram
        # in a fixed-pitch font.
        self.ui.txt_diagram.setFont(fixed_font())

        self.ui.buttonBox.rejected.connect(self.reject)
        self.ui.button_copy.clicked.connect(self._on_copy)
        self.ui.button_save.clicked.connect(self._on_save)
        # Enter must not fire Copy or Save. The app-wide policy
        # (qt_utils.install_enter_policy) clears autoDefault on every dialog it
        # shows, which covers these two - but that runs on Show, and this
        # dialog is also constructed by harnesses that never show it, so the
        # flags are cleared here as well. Close is RejectRole: its key is Esc.
        for button in (self.ui.button_copy, self.ui.button_save):
            button.setAutoDefault(False)
            button.setDefault(False)

        self.refresh()

    # ------------------------------------------------------------------
    def set_component(self, component, phase_name: str | None = None) -> None:
        self._component = component
        if phase_name is not None:
            self._phase_name = phase_name
        self.refresh()

    def refresh(self) -> None:
        """Re-render from the live model."""
        if self._component is None:
            self.ui.txt_diagram.setPlainText("No component selected.")
            self.setWindowTitle("Structure")
            return
        self.setWindowTitle("Structure - %s"
                            % (self._component.name or "(unnamed)"))
        self.ui.txt_diagram.setPlainText(
            build_structure_diagram(self._component, self._phase_name))

    # ------------------------------------------------------------------
    def _on_copy(self) -> None:
        QApplication.clipboard().setText(self.ui.txt_diagram.toPlainText())

    def _on_save(self) -> None:
        name = (getattr(self._component, "name", "") or "component").strip()
        path, _filter = QFileDialog.getSaveFileName(
            self, "Save structure diagram", "%s structure.txt" % name,
            "Text files (*.txt);;All files (*)",
        )
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".txt"
        try:
            # UTF-8: the diagram is drawn with box-drawing characters.
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(self.ui.txt_diagram.toPlainText())
        except OSError as exc:
            QMessageBox.warning(
                self, "Save failed", "Could not write the file:\n\n%s" % exc)
