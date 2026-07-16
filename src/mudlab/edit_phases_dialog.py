"""Edit Phases window: the object-store shell hosting the phase editor,
bound to the project's real Phase models.

Old: AppView child view "phases" = NoMinMaxObjectListStoreView +
PhasesController; opened by the edit_phases action.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QMessageBox, QWidget

from mudlab.add_phase_dialog import AddPhaseDialog
from mudlab.edit_phase_widget import EditPhaseWidget
from mudlab.models import Project
from mudlab.models.phase import Phase
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

        # Add / Remove are wired (Batch P2). Import / Export (.phs) come with
        # the phase-file parser and the import uuid-collision policy.
        self.ui.button_add_object.clicked.connect(self._on_add_phase)
        self.ui.button_del_object.clicked.connect(self._on_remove_phase)
        for button, why in (
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

    # ------------------------------------------------------------------
    # Add / Remove (old PhasesController create/delete)
    # ------------------------------------------------------------------
    def _on_add_phase(self) -> None:
        if self.project is None:
            return
        dialog = AddPhaseDialog(self)
        if dialog.exec() != AddPhaseDialog.DialogCode.Accepted:
            return
        # Only the empty-phase path is offered by the dialog for now; the model
        # factory builds the G blank components and the R0 probabilities.
        phase = Phase.create_empty(G=dialog.G, name="New Phase")
        self.project.add_phase(phase)
        self._phases.append(phase)
        self.add_object_row(
            phase.name, str(getattr(phase.probabilities, "R", 0)), str(phase.G)
        )
        # Select the new phase so its editor opens (and the candidate combos,
        # rebuilt on selection, pick it up).
        self.ui.edit_objects_treeview.setCurrentIndex(
            self.objects_model.index(len(self._phases) - 1, 0)
        )

    def _on_remove_phase(self) -> None:
        rows = self.ui.edit_objects_treeview.selectionModel().selectedRows(0)
        if not rows or self.project is None:
            return
        index = rows[0].row()
        if not (0 <= index < len(self._phases)):
            return
        phase = self._phases[index]
        # The old app confirms - deleting a phase is irreversible and also
        # clears every based_on / linked_with / mixture reference to it.
        if QMessageBox.question(
            self, "Remove phase",
            "Deleting a phase is irreversible!\nAre you sure you want to "
            "continue?",
        ) != QMessageBox.StandardButton.Yes:
            return
        self.project.remove_phase(phase)  # cascades every reference to it
        # Recompute: a mixture that used the phase now has an empty cell, so
        # its stored calculated pattern still carries the removed phase's
        # contribution until this runs.
        self.project.calculate()
        del self._phases[index]
        self.objects_model.removeRow(index)
        # Reselect a neighbour so the editor keeps showing a valid phase.
        if self._phases:
            new_row = min(index, len(self._phases) - 1)
            self.ui.edit_objects_treeview.setCurrentIndex(
                self.objects_model.index(new_row, 0)
            )
        else:
            self.phase_widget.bind_phase(None)

    def _on_phase_selected(self, index: QModelIndex) -> None:
        if 0 <= index.row() < len(self._phases):
            phase = self._phases[index.row()]
            atom_types = self.project.atom_types if self.project is not None else []
            self.phase_widget.bind_phase(
                phase,
                on_changed=lambda p=phase: self._recalculate(p),
                atom_types=atom_types,
                link_candidates=self._link_candidates(),
                phase_candidates=self._phase_candidates(),
            )

    def _phase_candidates(self):
        """(label, phase) for every phase - the reference phases offered in the
        editor's "based on" combo (it filters to matching G)."""
        if self.project is None:
            return []
        return [(ph.name or "phase", ph) for ph in self.project.phases]

    def _link_candidates(self):
        """(label, component) for every component in the project - the linking
        templates offered in the component editor's "Linked with" combo."""
        if self.project is None:
            return []
        return [
            ("%s / %s" % (ph.name, getattr(comp, "name", "") or "component"), comp)
            for ph in self.project.phases
            for comp in ph.components
        ]

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
