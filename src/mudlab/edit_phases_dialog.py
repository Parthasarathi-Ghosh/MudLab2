"""Edit Phases window: the object-store shell hosting the phase editor,
bound to the project's real Phase models.

Old: AppView child view "phases" = NoMinMaxObjectListStoreView +
PhasesController; opened by the edit_phases action.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QWidget

from mudlab.edit_phase_widget import EditPhaseWidget
from mudlab.models import Project
from mudlab.object_store_dialog import ObjectStoreDialog


class EditPhasesDialog(ObjectStoreDialog):
    def __init__(self, parent: QWidget | None = None, project: Project | None = None) -> None:
        super().__init__(parent, title="Edit Phases", columns=("Phase", "R", "G"))
        self.project = project

        self.phase_widget = EditPhaseWidget(self)
        self.set_properties_widget(self.phase_widget)

        self._phases = list(project.phases) if project is not None else []
        for phase in self._phases:
            self.add_object_row(
                phase.name,
                str(getattr(phase.probabilities, "R", 0)),
                str(phase.G),
            )

        self.object_selected.connect(self._on_phase_selected)

        # Adding / removing / import / export of phases is structural and
        # comes with the phase-creation batch (needs the component editor and
        # the default-phase catalog); disable them for now.
        for button, why in (
            (self.ui.button_add_object, "Creating phases is not ported yet."),
            (self.ui.button_del_object, "Removing phases is not ported yet."),
            (self.ui.button_load_object, "Importing phases is not ported yet."),
            (self.ui.button_save_object, "Exporting phases is not ported yet."),
        ):
            button.setEnabled(False)
            button.setToolTip(why)

        if self._phases:
            self.ui.edit_objects_treeview.setCurrentIndex(
                self.objects_model.index(0, 0)
            )
        else:
            self.phase_widget.bind_phase(None)

    def _on_phase_selected(self, index: QModelIndex) -> None:
        if 0 <= index.row() < len(self._phases):
            phase = self._phases[index.row()]
            self.phase_widget.bind_phase(
                phase, on_changed=lambda p=phase: self._recalculate(p)
            )

    def _recalculate(self, phase) -> None:
        """Recompute every mixture after a phase edit (any mixture may use
        this phase); the specimens' data_changed then refreshes the plot.
        Keep the list label in sync with an edited phase name."""
        if self.project is not None:
            self.project.calculate()
        rows = self.ui.edit_objects_treeview.selectionModel().selectedRows(0)
        if rows:
            item = self.objects_model.itemFromIndex(rows[0])
            if item is not None:
                item.setText(phase.name)
