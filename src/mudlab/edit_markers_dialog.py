"""Edit Markers window: the object-store shell hosting the marker editor,
with a Find peaks / Match minerals extra-widget row in the list panel.

Old: EditMarkersView (specimen/views/markers.py) = ObjectListStoreView +
the find_peaks.glade extra widget; MarkersController; opened by the
edit_markers action for the current specimen. Bound live to the
specimen's real Marker models (add/remove/edit update the plot).
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QMessageBox, QPushButton, QWidget

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
        # Sample button: pick the marker position directly on the plot.
        self.marker_widget.ui.cmd_sample.clicked.connect(self._on_sample_position)

        self._reload_markers()

    def _markers(self) -> tuple:
        return self.specimen.markers if self.specimen is not None else ()

    def select_marker(self, marker) -> None:
        """Select the row for the given marker (old show_marker)."""
        markers = self._markers()
        if marker in markers:
            self.ui.edit_objects_treeview.setCurrentIndex(
                self.objects_model.index(markers.index(marker), 0)
            )
        self.raise_()
        self.activateWindow()

    def _on_sample_position(self) -> None:
        # Arm the main window's eye-dropper; the next plot click fills the
        # position field (which writes to the bound marker).
        if self.marker_widget._marker is None:
            return
        main_window = self.parent()
        if main_window is not None and hasattr(main_window, "arm_position_pick"):
            main_window.arm_position_pick(
                lambda plot, x: self.marker_widget.ui.spb_position.setValue(x),
                "Click the marker position on the pattern...",
            )

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
        if self.specimen is None or not (
            self.specimen.has_experimental_data or self.specimen.has_calculated_data
        ):
            QMessageBox.information(
                self, "Detect peaks",
                "This specimen has no pattern data to detect peaks in.")
            return
        # Old app: when markers already exist, offer to clear them first so the
        # detected set replaces (Yes) or appends to (No) the current markers.
        cleared = False
        if self.specimen.markers:
            reply = QMessageBox.question(
                self, "Detect peaks",
                "Clear the current markers for this pattern first?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Yes:
                self.specimen.clear_markers()
                cleared = True
        dialog = DetectPeaksDialog(self, specimen=self.specimen)
        dialog.exec()
        # Reload whenever the marker set changed: peaks were added, OR we
        # cleared (even if the dialog was cancelled or found nothing) - otherwise
        # the list would keep showing markers that no longer exist.
        if cleared or dialog.added_markers:
            self._reload_markers(select_row=len(self._markers()) - 1)

    def _selected_markers(self) -> list:
        markers = self._markers()
        rows = [
            i.row()
            for i in self.ui.edit_objects_treeview.selectionModel().selectedRows()
        ]
        return [markers[r] for r in rows if 0 <= r < len(markers)]

    def _on_match_minerals(self) -> None:
        if self.specimen is None:
            return
        targets = self._selected_markers() or list(self.specimen.markers)
        # Non-modal: keep a reference so it is not garbage-collected, and
        # refresh the marker list when it appends labels.
        self._match_dialog = MatchMineralsDialog(
            self, specimen=self.specimen, targets=targets)
        self._match_dialog.applied.connect(self._on_labels_applied)
        self._match_dialog.show()

    def _on_labels_applied(self) -> None:
        row = self.ui.edit_objects_treeview.currentIndex().row()
        self._reload_markers(select_row=row if row >= 0 else 0)
