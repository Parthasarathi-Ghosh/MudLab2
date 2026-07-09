"""Edit Atom Types window: the object-store shell hosting the atom editor,
bound to the project's real AtomType models.

Old: AppView child view "atom_types" = ObjectListStoreView +
AtomTypesController; opened by the edit_atom_types action.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QWidget

from mudlab.edit_atom_type_widget import EditAtomTypeWidget
from mudlab.models import Project
from mudlab.object_store_dialog import ObjectStoreDialog


class EditAtomTypesDialog(ObjectStoreDialog):
    def __init__(self, parent: QWidget | None = None, project: Project | None = None) -> None:
        super().__init__(parent, title="Edit Atom Types", columns=("Atom type", "Nr"))
        self.project = project

        self.atom_widget = EditAtomTypeWidget(self)
        self.set_properties_widget(self.atom_widget)

        self._atom_types = list(project.atom_types) if project is not None else []
        for atom in self._atom_types:
            self.add_object_row(atom.name, str(int(atom.atom_nr)))

        self.object_selected.connect(self._on_atom_selected)

        if self._atom_types:
            self.ui.edit_objects_treeview.setCurrentIndex(
                self.objects_model.index(0, 0)
            )
        else:
            self.atom_widget.bind_atom_type(None)

    def _on_atom_selected(self, index: QModelIndex) -> None:
        if 0 <= index.row() < len(self._atom_types):
            self.atom_widget.bind_atom_type(self._atom_types[index.row()])
