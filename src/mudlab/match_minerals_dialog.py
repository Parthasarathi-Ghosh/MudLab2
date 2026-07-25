"""Match minerals dialog. Design: ui/match_minerals.ui.

Ported from the GTK MatchMineralsView + MatchMineralController
(specimen/glade/match_minerals.glade, marker_controllers.py). Non-modal (the
old view stayed above the main window so the plot stayed interactive). The
reference minerals are scored against the target markers' peaks
(calculations.peak_detection.score_minerals); the best matches list on the
left, all references on the right, with transfer buttons between them.
"Append labels" writes the chosen minerals' abbreviations onto the target
markers.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QDialog, QWidget

from mudlab.calculations import peak_detection as pd
from mudlab.ui.ui_match_minerals import Ui_MatchMineralsDialog

_SCORE_ROLE = Qt.ItemDataRole.UserRole + 1
# Source row in self._minerals, stamped on both list items. The reference set
# has a handful of duplicate names (e.g. two "Albite, ordered"), so a mineral
# must be identified by its row, never by its (non-unique) name.
_INDEX_ROLE = Qt.ItemDataRole.UserRole + 2


class MatchMineralsDialog(QDialog):
    # Emitted after Append labels rewrites marker labels, so the host list can
    # refresh (labels are not otherwise observed by the markers treeview).
    applied = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        specimen=None,
        targets=None,
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_MatchMineralsDialog()
        self.ui.setupUi(self)
        self.specimen = specimen
        # Targets: the markers whose peaks we score against. Default to the
        # specimen's full marker set (old on_match_minerals fallback).
        if targets:
            self.targets = list(targets)
        elif specimen is not None:
            self.targets = list(specimen.markers)
        else:
            self.targets = []

        self._minerals = pd.load_mineral_references()  # [(name, abbr, peaks)]

        # --- all-minerals list (Name, Abbr) ---
        self.minerals_model = QStandardItemModel(self)
        self.minerals_model.setHorizontalHeaderLabels(["Mineral", "Abbr."])
        for idx, (name, abbr, _peaks) in enumerate(self._minerals):
            name_item = _readonly_item(name)
            name_item.setData(idx, _INDEX_ROLE)  # remember which reference row
            self.minerals_model.appendRow([name_item, _readonly_item(abbr)])
        self.ui.tv_minerals.setModel(self.minerals_model)

        # --- matched-minerals list (Name, Abbr, Score) ---
        self.matches_model = QStandardItemModel(self)
        self.matches_model.setHorizontalHeaderLabels(["Mineral", "Abbr.", "Score"])
        self.ui.tv_matches.setModel(self.matches_model)

        # The specimen-range checkbox drove the (deferred) mineral-preview
        # overlay in the old app; there is no such overlay in MudLab2 yet, so it
        # has nothing to act on.
        self.ui.chk_use_specimen_range.setEnabled(False)
        self.ui.chk_use_specimen_range.setToolTip(
            "Reserved for the mineral-preview overlay (not yet ported)."
        )

        # Old glade: btn_rtl = add (minerals -> matches), btn_ltr = remove.
        self.ui.btn_rtl.clicked.connect(self._add_selected_match)
        self.ui.btn_ltr.clicked.connect(self._remove_selected_match)
        self.ui.btn_auto_match.clicked.connect(self._on_auto_match)
        self.ui.btn_apply.clicked.connect(self._on_apply)
        self.ui.buttonBox.rejected.connect(self.reject)

        self._marker_peaks = self._compute_marker_peaks()
        self.ui.btn_auto_match.setEnabled(bool(self._marker_peaks))
        self.ui.btn_apply.setEnabled(bool(self.targets))
        # Score straight away so the dialog opens with results (old app left it
        # empty until Auto match, but the button is right there and the peaks
        # are known - running it once is strictly more useful).
        if self._marker_peaks:
            self._on_auto_match()

    # ------------------------------------------------------------------
    # Target marker peaks (position in angstrom, intensity)
    # ------------------------------------------------------------------
    def _compute_marker_peaks(self):
        """(d-spacing in angstrom, experimental intensity) for each target
        marker - the observed peak list score_minerals expects."""
        if self.specimen is None or not self.targets:
            return []
        x, y = self.specimen.experimental_pattern
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        peaks = []
        for marker in self.targets:
            angstrom = marker.get_nm_position() * 10.0
            if x.size:
                intensity = float(np.interp(marker.position, x, y))
            else:
                intensity = 0.0
            if angstrom > 0:
                peaks.append((angstrom, intensity))
        return peaks

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------
    def _on_auto_match(self) -> None:
        self._marker_peaks = self._compute_marker_peaks()
        self.matches_model.removeRows(0, self.matches_model.rowCount())
        if not self._marker_peaks:
            return
        for name, abbr, _mpeaks, _p_matches, score in pd.score_minerals(
            self._marker_peaks, self._minerals
        ):
            self._append_match_row(name, abbr, score)
        # Select the best (top) match, as the old reload_matches did.
        if self.matches_model.rowCount():
            self.ui.tv_matches.setCurrentIndex(self.matches_model.index(0, 0))

    def _add_selected_match(self) -> None:
        """Add the mineral(s) selected in the all-minerals list to the matches,
        scored individually (old add_match). The reference is identified by its
        row index, not its name, so the correct peaks are used even for the few
        duplicate-named entries (and both duplicates can be added)."""
        for index in self.ui.tv_minerals.selectionModel().selectedRows():
            idx = self.minerals_model.itemFromIndex(index).data(_INDEX_ROLE)
            if idx is None or self._match_row_for_index(idx) is not None:
                continue  # nothing resolvable, or this exact row is already listed
            name, abbr, peaks = self._minerals[idx]
            score = 0.0
            if self._marker_peaks:
                scored = pd.score_minerals(self._marker_peaks, [(name, abbr, peaks)])
                if scored:
                    score = scored[0][4]
            self._append_match_row(name, abbr, score, idx)

    def _remove_selected_match(self) -> None:
        rows = sorted(
            (i.row() for i in self.ui.tv_matches.selectionModel().selectedRows()),
            reverse=True,
        )
        for row in rows:
            self.matches_model.removeRow(row)

    # ------------------------------------------------------------------
    # Append labels
    # ------------------------------------------------------------------
    def _on_apply(self) -> None:
        """Append each chosen match's abbreviation to every target marker's
        label (skipping duplicates), clearing the plot annotation so it falls
        back to the label (old apply_cb)."""
        chosen = self._selected_or_all_matches()
        changed = False
        for _name, abbr in chosen:
            if not abbr:
                continue
            for marker in self.targets:
                existing = [part.strip() for part in marker.label.split(",")]
                if abbr not in existing:
                    marker.label = f"{marker.label}, {abbr}"
                    marker.anno_label = ""
                    changed = True
        if changed:
            self.applied.emit()

    def _selected_or_all_matches(self):
        """(name, abbr) for the selected match rows, or all matches if none are
        selected (old apply used the selection, falling back to all matches)."""
        selected = self.ui.tv_matches.selectionModel().selectedRows()
        rows = [i.row() for i in selected]
        if not rows:
            rows = range(self.matches_model.rowCount())
        out = []
        for row in rows:
            name_item = self.matches_model.item(row, 0)
            abbr_item = self.matches_model.item(row, 1)
            if name_item is not None:
                out.append((name_item.text(), abbr_item.text() if abbr_item else ""))
        return out

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _append_match_row(self, name: str, abbr: str, score: float, idx=None) -> None:
        name_item = _readonly_item(name)
        if idx is not None:
            name_item.setData(idx, _INDEX_ROLE)  # remember the source row
        score_item = _readonly_item(f"{score:.5f}")
        score_item.setData(float(score), _SCORE_ROLE)
        self.matches_model.appendRow([name_item, _readonly_item(abbr), score_item])

    def _match_row_for_index(self, idx: int):
        """The matches row holding reference row `idx`, or None. Auto-match rows
        carry no index (score_minerals loses it) and never dedup a manual add."""
        for row in range(self.matches_model.rowCount()):
            if self.matches_model.item(row, 0).data(_INDEX_ROLE) == idx:
                return row
        return None


def _readonly_item(text: str) -> QStandardItem:
    item = QStandardItem(text)
    item.setEditable(False)
    return item
