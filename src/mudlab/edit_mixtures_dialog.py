"""Edit Mixtures window: the object-store shell hosting the mixture editor,
bound to the project's real Mixture models.

Old: AppView child view "mixtures" = NoMinMaxObjectListStoreView +
MixturesController; opened by the edit_mixtures action.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QWidget

from mudlab.edit_mixture_widget import EditMixtureWidget
from mudlab.models import Project
from mudlab.object_store_dialog import ObjectStoreDialog


class EditMixturesDialog(ObjectStoreDialog):
    def __init__(self, parent: QWidget | None = None, project: Project | None = None) -> None:
        super().__init__(parent, title="Edit Mixtures", columns=("Mixture",))
        self.project = project

        self.mixture_widget = EditMixtureWidget(self)
        self.set_properties_widget(self.mixture_widget)

        self._mixtures = list(project.mixtures) if project is not None else []
        for mixture in self._mixtures:
            self.add_object_row(mixture.name)

        self.object_selected.connect(self._on_mixture_selected)

        if self._mixtures:
            self.ui.edit_objects_treeview.setCurrentIndex(
                self.objects_model.index(0, 0)
            )
        else:
            self.mixture_widget.bind_mixture(None)

    def _on_mixture_selected(self, index: QModelIndex) -> None:
        if 0 <= index.row() < len(self._mixtures):
            mixture = self._mixtures[index.row()]
            phases = self.project.phases if self.project is not None else []
            specimens = self.project.specimens if self.project is not None else []
            self.mixture_widget.bind_mixture(
                mixture, phases=phases, specimens=specimens,
                on_changed=lambda m=mixture: self._recalculate(m)
            )

    def _recalculate(self, mixture) -> None:
        """Recompute the mixture's calculated pattern after an edit; the
        specimens' data_changed then refreshes the plot. Also keep the list
        label in sync with an edited mixture name."""
        mixture.calculate()
        rows = self.ui.edit_objects_treeview.selectionModel().selectedRows(0)
        if rows:
            item = self.objects_model.itemFromIndex(rows[0])
            if item is not None:
                item.setText(mixture.name)
