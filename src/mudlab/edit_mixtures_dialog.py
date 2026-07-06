"""Edit Mixtures window: the object-store shell hosting the mixture editor.

Old: AppView child view "mixtures" = NoMinMaxObjectListStoreView +
MixturesController; opened by the edit_mixtures action.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QWidget

from mudlab.edit_mixture_widget import EditMixtureWidget
from mudlab.object_store_dialog import ObjectStoreDialog

# Placeholder mixtures until the mixture model (Qt signals) exists.
_DEMO_MIXTURES = (
    (
        "Mixture 1",
        ("Specimen A", "Specimen B"),
        (("Kaolinite", 0.40), ("Illite", 0.35), ("Illite/Smectite R1", 0.25)),
        (1.00, 0.85),
        (0.0, 12.0),
    ),
    (
        "Mixture 2",
        ("Specimen C",),
        (("Kaolinite", 0.55), ("Illite", 0.45)),
        (1.00,),
        (0.0,),
    ),
)


class EditMixturesDialog(ObjectStoreDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, title="Edit Mixtures", columns=("Mixture",))

        self.mixture_widget = EditMixtureWidget(self)
        self.set_properties_widget(self.mixture_widget)

        self._mixtures = list(_DEMO_MIXTURES)
        for mixture in self._mixtures:
            self.add_object_row(mixture[0])

        self.object_selected.connect(self._on_mixture_selected)

        first = self.objects_model.index(0, 0)
        self.ui.edit_objects_treeview.setCurrentIndex(first)

    def _on_mixture_selected(self, index: QModelIndex) -> None:
        self.mixture_widget.set_mixture_placeholder(*self._mixtures[index.row()])
