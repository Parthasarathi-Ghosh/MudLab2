"""Peaks window: the object-store shell hosting the peak (marker) editor,
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
        # "Peaks" is what the user calls these; MARKER remains the model name
        # (and the .mud key), so the code keeps saying marker and only the
        # visible strings say peak.
        title = "Peaks"
        if specimen is not None:
            title += f" - {specimen.name}"
        super().__init__(parent, title=title, columns=("Peak", "Position"))

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

        # A position is only COMMITTED on editingFinished; valueChanged fires
        # per keystroke and re-sorting there would move the row mid-type.
        self.marker_widget.ui.spb_position.editingFinished.connect(
            self._resort_to_position)

        self._match_dialog: MatchMineralsDialog | None = None
        self._hidden_for_plot = False
        self._closing = False
        self._reload_markers()

    def _close_match_dialog(self) -> None:
        """Close any open Match Minerals child (which clears its reference-peak
        overlay via reject) and drop it, so reopening / closing never leaves an
        orphaned window or a lingering preview on the plot."""
        # NOTE deliberately NOT WA_DeleteOnClose on the match dialog: this owner
        # keeps a reference and closes it later, so letting Qt delete it on the
        # window-X would make the next close() hit an already-deleted C++ object
        # (RuntimeError). The explicit deleteLater below is the accumulation fix.
        if self._match_dialog is not None:
            self._match_dialog.close()  # -> reject clears the mineral preview
            self._match_dialog.deleteLater()
            self._match_dialog = None

    def closeEvent(self, event) -> None:
        # A pick armed by THIS dialog must die with it. Reopening Peaks from the
        # toolbar while it was hidden for a Sample pick used to close this one
        # and leave its pick armed: the next plot click then ran our callback
        # and `_step_back` SHOWED THE CLOSED WINDOW again, so the user ended up
        # with two Peaks dialogs and the position written into the dead one.
        self._closing = True
        main_window = self.parent()
        if main_window is not None and hasattr(main_window, "cancel_position_pick"):
            main_window.cancel_position_pick()
        self._close_match_dialog()
        super().closeEvent(event)

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

    # ------------------------------------------------------------------
    # Getting out of the way of the plot
    # ------------------------------------------------------------------
    def _step_aside(self) -> None:
        """Hide, remembering that WE hid - so a dialog the user closed while it
        was out of the way is not resurrected behind their back."""
        if self.isVisible():
            self._hidden_for_plot = True
            self.hide()

    def _step_back(self) -> None:
        """Come back, but only if `_step_aside` is what put us away - and never
        once this dialog is closing, or the close would put it back on screen."""
        if self._hidden_for_plot and not self._closing:
            self._hidden_for_plot = False
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_sample_position(self) -> None:
        """Pick the peak position on the plot.

        The dialog steps aside for the duration: it is a tall window that
        routinely covers the pattern the user is being asked to click.

        Hiding is only safe because the pick is CANCELLABLE - `on_cancel`
        brings the window back when the user presses Esc instead of clicking.
        Before that existed, an armed pick could only ever end in a click, and
        a hidden dialog would have been stranded.
        """
        if self.marker_widget._marker is None:
            return
        main_window = self.parent()
        if main_window is None or not hasattr(main_window, "arm_position_pick"):
            return

        def picked(_plot, x):
            self.marker_widget.ui.spb_position.setValue(x)
            self._step_back()
            # Sampling COMMITS a position, so this is one of the two moments
            # the list is re-sorted (see _resort_to_position).
            self._resort_to_position()

        self._step_aside()
        main_window.arm_position_pick(
            picked,
            "Click the peak position on the pattern...",
            on_cancel=self._step_back,
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
        marker = self.specimen.add_marker(Marker(label="New Peak"))
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

    def _resort_to_position(self) -> None:
        """Put the list back in position order and keep the edited peak selected.

        WHY ONLY ON COMMIT: the position spin box writes on every `valueChanged`,
        so sorting there would move the row under the user's cursor on each
        keystroke - typing "25" would jump the selection twice, once at "2".
        This runs at the two moments a position is FINISHED: the spin box's
        editingFinished, and a completed Sample pick.
        """
        marker = self.marker_widget._marker
        if self.specimen is None or marker is None:
            return
        if not self.specimen.sort_markers():
            return          # already in order - do not disturb the selection
        markers = self._markers()
        row = markers.index(marker) if marker in markers else 0
        self._reload_markers(select_row=row)

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
        # Detected peaks are appended, so a set added on top of existing
        # markers interleaves them - sort so the list reads by position again.
        if dialog.added_markers:
            self.specimen.sort_markers()
        # Reload whenever the marker set changed: peaks were added, OR we
        # cleared (even if the dialog was cancelled or found nothing) - otherwise
        # the list would keep showing markers that no longer exist.
        if cleared or dialog.added_markers:
            # Select the first NEW peak rather than the last row: the sort above
            # means the last row is simply the highest-position peak, which has
            # nothing to do with what was just detected.
            markers = self._markers()
            row = 0
            if dialog.added_markers:
                rows = [markers.index(m) for m in dialog.added_markers
                        if m in markers]
                row = min(rows) if rows else 0
            self._reload_markers(select_row=row)

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
        # Close any prior match dialog first (clears its overlay + no orphaned
        # windows), then open a fresh one bound to the current selection.
        self._close_match_dialog()
        targets = self._selected_markers() or list(self.specimen.markers)
        # Non-modal: keep a reference so it is not garbage-collected, and
        # refresh the marker list when it appends labels.
        self._match_dialog = MatchMineralsDialog(
            self, specimen=self.specimen, targets=targets)
        self._match_dialog.applied.connect(self._on_labels_applied)
        # Step aside for it too: Match Minerals draws reference peaks ON the
        # pattern, which is the whole point of it, and this window sits over
        # them. `finished` covers every way it can end - its own buttons, the
        # window X, or _close_match_dialog from here.
        self._match_dialog.finished.connect(self._step_back)
        self._step_aside()
        self._match_dialog.show()

    def _on_labels_applied(self) -> None:
        row = self.ui.edit_objects_treeview.currentIndex().row()
        self._reload_markers(select_row=row if row >= 0 else 0)
