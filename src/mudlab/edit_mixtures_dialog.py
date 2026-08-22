"""Edit Mixtures window: the object-store shell hosting the mixture editor,
bound to the project's real Mixture models.

Old: AppView child view "mixtures" = NoMinMaxObjectListStoreView +
MixturesController; opened by the edit_mixtures action.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QMessageBox, QWidget

from mudlab.edit_mixture_widget import EditMixtureWidget
from mudlab.models import Project
from mudlab.models.mixture import Mixture
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
        # Add / Remove (old MixturesController create/delete). The old app's
        # Add Mixture type-chooser dialog was abandoned dead code (in-situ
        # mixtures were never finished): create_new_object_proxy just returns a
        # blank Mixture. So Add makes a blank regular mixture directly - no
        # dialog - which the user then builds with the editor's Add phase /
        # Add specimen buttons.
        self.ui.button_add_object.clicked.connect(self._on_add_mixture)
        self.ui.button_del_object.clicked.connect(self._on_remove_mixture)

        if self._mixtures:
            self.ui.edit_objects_treeview.setCurrentIndex(
                self.objects_model.index(0, 0)
            )
        else:
            self.mixture_widget.bind_mixture(None)

    # ------------------------------------------------------------------
    # Add / Remove
    # ------------------------------------------------------------------
    def _on_add_mixture(self) -> None:
        if self.project is None:
            return
        mixture = Mixture(name="New Mixture")
        self.project.add_mixture(mixture)
        self._mixtures.append(mixture)
        self.add_object_row(mixture.name)
        # Select the new mixture so its (empty) editor opens, ready to build.
        self.ui.edit_objects_treeview.setCurrentIndex(
            self.objects_model.index(len(self._mixtures) - 1, 0)
        )

    def _on_remove_mixture(self) -> None:
        rows = self.ui.edit_objects_treeview.selectionModel().selectedRows(0)
        if not rows or self.project is None:
            return
        index = rows[0].row()
        if not (0 <= index < len(self._mixtures)):
            return
        mixture = self._mixtures[index]
        if QMessageBox.question(
            self, "Remove mixture",
            "Delete the mixture '%s'?\nThis cannot be undone."
            % (mixture.name or "mixture"),
        ) != QMessageBox.StandardButton.Yes:
            return
        self.project.remove_mixture(mixture)
        del self._mixtures[index]
        self.objects_model.removeRow(index)
        # Reselect a neighbour so the editor keeps showing a valid mixture.
        if self._mixtures:
            new_row = min(index, len(self._mixtures) - 1)
            self.ui.edit_objects_treeview.setCurrentIndex(
                self.objects_model.index(new_row, 0)
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
                on_changed=lambda m=mixture: self._recalculate(m),
                project=self.project,
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
