"""Edit Markers window: the object-store shell hosting the marker editor,
with a Find peaks / Match minerals extra-widget row in the list panel.

Old: EditMarkersView (specimen/views/markers.py) = ObjectListStoreView +
the find_peaks.glade extra widget; MarkersController; opened by the
edit_markers action for the current specimen. Bound live to the
specimen's real Marker models (add/remove/edit update the plot).
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QPushButton, QWidget

from mudlab.detect_peaks_dialog import DetectPeaksDialog
from mudlab.edit_marker_widget import EditMarkerWidget
from mudlab.match_minerals_dialog import MatchMineralsDialog
from mudlab.models import Marker, Specimen
from mudlab.object_store_dialog import ObjectStoreDialog


class EditMarkersDialog(ObjectStoreDialog):
    def __init__(self, parent: QWidget | None = None, specimen: Specimen | None = None) -> None:
        self.specimen = specimen
        title = "Edit Markers"
        if specimen is not None:
            title += f" - {specimen.name}"
        super().__init__(parent, title=title, columns=("Marker", "Position"))

        self.marker_widget = EditMarkerWidget(self)
        self.set_properties_widget(self.marker_widget)
        self.marker_widget.bind_marker(None)

        # Extra-widget row under the list (old find_peaks.glade vbox).
        self.btn_find_peaks = QPushButton("Find peaks")
        self.btn_match_minerals = QPushButton("Match minerals")
        self.ui.extraLayout.addWidget(self.btn_find_peaks)
        self.ui.extraLayout.addWidget(self.btn_match_minerals)
        self.btn_find_peaks.clicked.connect(self._on_find_peaks)
        self.btn_match_minerals.clicked.connect(self._on_match_minerals)
        self.btn_match_minerals.setEnabled(False)

        self.object_selected.connect(self._on_marker_selected)
        self.ui.button_add_object.clicked.connect(self._on_add_marker)
        self.ui.button_del_object.clicked.connect(self._on_del_marker)

        self._reload_markers()

    def _markers(self) -> tuple:
        return self.specimen.markers if self.specimen is not None else ()

    def _reload_markers(self, select_row: int = 0) -> None:
        self.objects_model.removeRows(0, self.objects_model.rowCount())
        for marker in self._markers():
            self.add_object_row(marker.label, f"{marker.position:.4f}")
        if self.objects_model.rowCount():
            row = min(select_row, self.objects_model.rowCount() - 1)
            self.ui.edit_objects_treeview.setCurrentIndex(
                self.objects_model.index(row, 0)
            )
        else:
            self.marker_widget.bind_marker(None)
            self.btn_match_minerals.setEnabled(False)

    def _on_marker_selected(self, index: QModelIndex) -> None:
        markers = self._markers()
        if 0 <= index.row() < len(markers):
            self.marker_widget.bind_marker(markers[index.row()])
            self.btn_match_minerals.setEnabled(True)

    def _on_add_marker(self) -> None:
        if self.specimen is None:
            return
        marker = self.specimen.add_marker(Marker(label="New Marker"))
        marker.visuals_changed.connect(self._sync_selected_row)
        self._reload_markers(select_row=len(self._markers()) - 1)

    def _on_del_marker(self) -> None:
        markers = self._markers()
        rows = sorted(
            (i.row() for i in self.ui.edit_objects_treeview.selectionModel().selectedRows()),
            reverse=True,
        )
        for row in rows:
            if 0 <= row < len(markers):
                self.specimen.remove_marker(markers[row])
        self._reload_markers(select_row=rows[-1] if rows else 0)

    def _sync_selected_row(self) -> None:
        # Reflect label/position edits back into the list without a full
        # rebuild (which would drop the selection mid-edit).
        index = self.ui.edit_objects_treeview.currentIndex()
        marker = self.marker_widget._marker
        if index.isValid() and marker is not None:
            self.objects_model.item(index.row(), 0).setText(marker.label)
            self.objects_model.item(index.row(), 1).setText(f"{marker.position:.4f}")

    def _on_find_peaks(self) -> None:
        DetectPeaksDialog(self).exec()

    def _on_match_minerals(self) -> None:
        MatchMineralsDialog(self).show()
