"""Edit Atom Types window: the object-store shell hosting the atom editor,
bound to the project's real AtomType models.

Old: AppView child view "atom_types" = ObjectListStoreView +
AtomTypesController; opened by the edit_atom_types action.

The window is modeless, so the project's atom-type list can grow while it is
open (adding a default phase or importing a `.phs` adopts atom types). It
listens to ``Project.atom_types_changed`` and rebuilds its list, keeping the
selected atom type selected where it still exists.
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

        self._atom_types = []
        self.object_selected.connect(self._on_atom_selected)
        if project is not None:
            project.atom_types_changed.connect(self._reload)
        self._reload()

    def _reload(self) -> None:
        """(Re)build the list from the project, preserving the selection."""
        selected = None
        row = self._current_row()
        if 0 <= row < len(self._atom_types):
            selected = self._atom_types[row]

        self._atom_types = list(self.project.atom_types) if self.project is not None else []
        self.objects_model.removeRows(0, self.objects_model.rowCount())
        for atom in self._atom_types:
            self.add_object_row(atom.name, str(int(atom.atom_nr)))

        if not self._atom_types:
            self.atom_widget.bind_atom_type(None)
            return
        # Same object where it survived, else fall back to the first row.
        keep = next((i for i, a in enumerate(self._atom_types) if a is selected), 0)
        self.ui.edit_objects_treeview.setCurrentIndex(
            self.objects_model.index(keep, 0)
        )

    def _current_row(self) -> int:
        index = self.ui.edit_objects_treeview.currentIndex()
        return index.row() if index.isValid() else -1

    def _on_atom_selected(self, index: QModelIndex) -> None:
        if 0 <= index.row() < len(self._atom_types):
            self.atom_widget.bind_atom_type(self._atom_types[index.row()])
