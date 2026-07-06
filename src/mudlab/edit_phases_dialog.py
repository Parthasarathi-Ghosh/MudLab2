"""Edit Phases window: the object-store shell hosting the phase editor.

Old: AppView child view "phases" = NoMinMaxObjectListStoreView +
PhasesController; opened by the edit_phases action.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QDialog, QWidget

from mudlab.add_phase_dialog import AddPhaseDialog
from mudlab.edit_phase_widget import EditPhaseWidget
from mudlab.object_store_dialog import ObjectStoreDialog

# Placeholder phases until the project model (Qt signals) exists.
_DEMO_PHASES = (
    ("Kaolinite", 0, 1),
    ("Illite", 0, 1),
    ("Illite/Smectite R1", 1, 2),
)


class EditPhasesDialog(ObjectStoreDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, title="Edit Phases", columns=("Phase", "R", "G"))

        self.phase_widget = EditPhaseWidget(self)
        self.set_properties_widget(self.phase_widget)

        self._phases = list(_DEMO_PHASES)
        for name, R, G in self._phases:
            self.add_object_row(name, str(R), str(G))

        self.object_selected.connect(self._on_phase_selected)
        self.ui.button_add_object.clicked.connect(self._on_add_phase)

        # The based-on combo offers the other phases (placeholder).
        for name, _R, _G in self._phases:
            self.phase_widget.ui.phase_based_on.addItem(name)

        # Select the first phase so the editor shows something.
        first = self.objects_model.index(0, 0)
        self.ui.edit_objects_treeview.setCurrentIndex(first)

    def _on_phase_selected(self, index: QModelIndex) -> None:
        name, R, G = self._phases[index.row()]
        self.phase_widget.set_phase_placeholder(name, R, G)

    def _on_add_phase(self) -> None:
        dialog = AddPhaseDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        # Placeholder: append a row; the real phase creation (empty /
        # default catalog / raw pattern) comes with the phase model port.
        if dialog.phase_type == "empty":
            name, R, G = "New phase", dialog.R, dialog.G
        elif dialog.phase_type == "default":
            name, R, G = dialog.default_phase, 0, 1
        else:
            name, R, G = "Raw pattern phase", 0, 1
        self._phases.append((name, R, G))
        self.add_object_row(name, str(R), str(G))
        self.phase_widget.ui.phase_based_on.addItem(name)
        self.ui.edit_objects_treeview.setCurrentIndex(
            self.objects_model.index(self.objects_model.rowCount() - 1, 0)
        )
