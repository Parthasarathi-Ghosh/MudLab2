"""Edit Markers window: the object-store shell hosting the marker editor,
with a Find peaks / Match minerals extra-widget row in the list panel.

Old: EditMarkersView (specimen/views/markers.py) = ObjectListStoreView +
the find_peaks.glade extra widget; MarkersController; opened by the
edit_markers action for the current specimen.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QPushButton, QWidget

from mudlab.detect_peaks_dialog import DetectPeaksDialog
from mudlab.edit_marker_widget import EditMarkerWidget
from mudlab.match_minerals_dialog import MatchMineralsDialog
from mudlab.object_store_dialog import ObjectStoreDialog

# Placeholder markers until the marker model (Qt signals) exists.
_DEMO_MARKERS = (
    ("d(001) 10Å", 8.84),
    ("d(002)", 17.74),
    ("Quartz", 26.64),
)


class EditMarkersDialog(ObjectStoreDialog):
    def __init__(self, parent: QWidget | None = None, specimen_name: str = "") -> None:
        title = "Edit Markers"
        if specimen_name:
            title += f" - {specimen_name}"
        super().__init__(parent, title=title, columns=("Marker", "Position"))

        self.marker_widget = EditMarkerWidget(self)
        self.set_properties_widget(self.marker_widget)

        # Extra-widget row under the list (old find_peaks.glade vbox).
        self.btn_find_peaks = QPushButton("Find peaks")
        self.btn_match_minerals = QPushButton("Match minerals")
        self.ui.extraLayout.addWidget(self.btn_find_peaks)
        self.ui.extraLayout.addWidget(self.btn_match_minerals)
        self.btn_find_peaks.clicked.connect(self._on_find_peaks)
        self.btn_match_minerals.clicked.connect(self._on_match_minerals)
        # Old set_selection_state: match-minerals needs a selected marker.
        self.btn_match_minerals.setEnabled(False)

        self._markers = list(_DEMO_MARKERS)
        for name, position in self._markers:
            self.add_object_row(name, f"{position:.4f}")

        self.object_selected.connect(self._on_marker_selected)

        first = self.objects_model.index(0, 0)
        self.ui.edit_objects_treeview.setCurrentIndex(first)

    def _on_marker_selected(self, index: QModelIndex) -> None:
        name, position = self._markers[index.row()]
        self.marker_widget.set_marker_placeholder(name, position)
        self.btn_match_minerals.setEnabled(True)

    def _on_find_peaks(self) -> None:
        DetectPeaksDialog(self).exec()

    def _on_match_minerals(self) -> None:
        # Old MatchMineralsView is non-modal (keep-above) so the plot stays
        # interactive while matching.
        dialog = MatchMineralsDialog(self)
        dialog.show()
