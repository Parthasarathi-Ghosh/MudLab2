"""Edit Atom Types window: the object-store shell hosting the atom editor.

Old: AppView child view "atom_types" = ObjectListStoreView +
AtomTypesController; opened by the edit_atom_types action.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QWidget

from mudlab.edit_atom_type_widget import EditAtomTypeWidget
from mudlab.object_store_dialog import ObjectStoreDialog

# Placeholder atom types until the model (Qt signals) exists. Atom numbers
# and weights are real; the scattering coefficients are synthetic demo
# values (real ones come from the atomic scattering factors data files).
_DEMO_ATOM_TYPES = (
    ("O1-", 8, 15.9994, 1.4, -1.0,
     (2.0, 1.6, 1.2, 0.8, 0.4), (14.0, 6.0, 2.0, 0.6, 0.2), 0.2),
    ("Si4+", 14, 28.0855, 0.8, 4.0,
     (2.6, 2.0, 1.4, 1.0, 0.6), (12.0, 5.0, 1.8, 0.5, 0.15), 0.3),
    ("Al3+", 13, 26.9815, 0.9, 3.0,
     (2.4, 1.8, 1.3, 0.9, 0.5), (12.5, 5.2, 1.9, 0.55, 0.18), 0.25),
)


class EditAtomTypesDialog(ObjectStoreDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, title="Edit Atom Types", columns=("Atom type",))

        self.atom_widget = EditAtomTypeWidget(self)
        self.set_properties_widget(self.atom_widget)

        self._atom_types = list(_DEMO_ATOM_TYPES)
        for atom in self._atom_types:
            self.add_object_row(atom[0])

        self.object_selected.connect(self._on_atom_selected)

        first = self.objects_model.index(0, 0)
        self.ui.edit_objects_treeview.setCurrentIndex(first)

    def _on_atom_selected(self, index: QModelIndex) -> None:
        self.atom_widget.set_atom_placeholder(*self._atom_types[index.row()])
