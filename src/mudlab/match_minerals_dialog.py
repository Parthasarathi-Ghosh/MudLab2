"""Match minerals dialog. Design: ui/match_minerals.ui.

Ported from the GTK MatchMineralsView + MatchMineralController
(specimen/glade/match_minerals.glade, marker_controllers.py), including the old
app's multi-target workflow (old MudLab 71807ac8, 2026-06-05). Non-modal: the
plot stays visible so the user can judge candidates against the pattern.

The workflow: the dialog opens with the peak the user selected as its only
target and scores straight away. The **Targets** dropdown lists every peak of
the specimen with a tick box; ticking or unticking a peak changes the targets
and rescores at once (at least one target is always kept). The target peaks are
highlighted on the plot, the selected mineral's reference lines are drawn as
magenta sticks, and the plot is view-only meanwhile (zoom and pan only), so the
only way to change the targets is here. "Append labels" writes the chosen
mineral's abbreviation onto every CURRENT target.

The reference minerals are scored against the target peaks with
calculations.peak_detection.score_minerals, one mineral at a time so each row
keeps its reference index. **Pairing** chooses how each mineral's lines are
paired with the peaks: Greedy (the original, default) or One-to-one (the best
pairing); changing it rescores. The best matches list on the left, all
references on the right, with transfer buttons between them.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QEvent, QModelIndex, QObject, Qt, Signal
from PySide6.QtGui import QCursor, QPalette, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog, QHeaderView, QPushButton, QStyledItemDelegate, QToolTip, QWidget,
)

from mudlab.calculations import get_2t_from_nm, peak_detection as pd
from mudlab.ui.ui_match_minerals import Ui_MatchMineralsDialog

_SCORE_ROLE = Qt.ItemDataRole.UserRole + 1
# Source row in self._minerals, stamped on both list items. The reference set
# has a handful of duplicate names (e.g. two "Albite, ordered"), so a mineral
# must be identified by its row, never by its (non-unique) name.
_INDEX_ROLE = Qt.ItemDataRole.UserRole + 2
# The reference peaks [(d_angstrom, rel_intensity), ...] for the row, so
# selecting it can draw the mineral-preview overlay without a name/index lookup.
_PEAKS_ROLE = Qt.ItemDataRole.UserRole + 3
# True on a matches row the user added by hand: kept (and rescored) when the
# targets change, whereas the scored rows are recomputed from scratch.
_MANUAL_ROLE = Qt.ItemDataRole.UserRole + 4
# The Marker behind a row of the Targets dropdown.
_MARKER_ROLE = Qt.ItemDataRole.UserRole + 5

_KEEP_ONE_TARGET = "At least one target is needed."


class _TickOnClick(QObject):
    """Event filter for the Targets dropdown's popup list.

    A click on a row toggles its tick and the popup STAYS OPEN, so several
    peaks can be ticked in one go (a plain QComboBox would choose the row and
    close). Space toggles the current row the same way."""

    def __init__(self, view, on_toggle) -> None:
        super().__init__(view)
        self._view = view
        self._on_toggle = on_toggle

    def eventFilter(self, obj, event) -> bool:
        etype = event.type()
        if (etype == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
                and obj is self._view.viewport()):
            index = self._view.indexAt(event.position().toPoint())
            if index.isValid():
                self._on_toggle(index.row())
            return True  # never let the combo choose the row and close
        if (etype == QEvent.Type.KeyPress and obj is self._view
                and event.key() == Qt.Key.Key_Space):
            index = self._view.currentIndex()
            if index.isValid():
                self._on_toggle(index.row())
            return True
        return False


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
        # Targets: the markers whose peaks we score against. Normally the one
        # peak selected in the Peaks window; with none, every peak (old
        # on_match_minerals fallback). Order as given, new targets appended
        # (as the old app did), so the scorer sees exactly the old peak list.
        if targets:
            self.targets = list(targets)
        elif specimen is not None:
            self.targets = list(specimen.markers)
        else:
            self.targets = []
        if specimen is not None and specimen.name:
            self.setWindowTitle(f"Match minerals - {specimen.name}")

        self._session_ended = False
        self._plot_locked = False
        self._minerals = pd.load_mineral_references()  # [(name, abbr, peaks)]

        # --- all-minerals list (Name, Abbr) ---
        self.minerals_model = QStandardItemModel(self)
        self.minerals_model.setHorizontalHeaderLabels(["Mineral", "Abbr."])
        for idx, (name, abbr, peaks) in enumerate(self._minerals):
            name_item = _readonly_item(name)
            name_item.setData(idx, _INDEX_ROLE)  # remember which reference row
            name_item.setData(peaks, _PEAKS_ROLE)  # for the preview overlay
            self.minerals_model.appendRow([name_item, _readonly_item(abbr)])
        self.ui.tv_minerals.setModel(self.minerals_model)

        # --- matched-minerals list (Name, Abbr, Score) ---
        self.matches_model = QStandardItemModel(self)
        self.matches_model.setHorizontalHeaderLabels(["Mineral", "Abbr.", "Score"])
        self.ui.tv_matches.setModel(self.matches_model)
        # Compact dialog: the name takes the slack, Abbr. and Score are sized
        # to their contents, so the score is never clipped.
        for view, fitted in ((self.ui.tv_matches, (1, 2)), (self.ui.tv_minerals, (1,))):
            header = view.header()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for column in fitted:
                header.setSectionResizeMode(
                    column, QHeaderView.ResizeMode.ResizeToContents)

        # --- Targets dropdown: every peak, ticked = a target ---
        self.targets_model = QStandardItemModel(self)
        combo = self.ui.cmb_targets
        combo.setModel(self.targets_model)
        # A styled delegate draws real tick boxes in the popup (the default
        # combo delegate draws menu-like rows that hide the check state).
        combo.setItemDelegate(QStyledItemDelegate(combo))
        self._tick_filter = _TickOnClick(combo.view(), self._toggle_target_row)
        combo.view().viewport().installEventFilter(self._tick_filter)
        combo.view().installEventFilter(self._tick_filter)
        combo.activated.connect(self._on_target_activated)
        # The closed box shows a summary ("3 of 12 peaks") as its placeholder;
        # draw it in the normal text colour, not the greyed placeholder one.
        palette = combo.palette()
        palette.setColor(QPalette.ColorRole.PlaceholderText,
                         palette.color(QPalette.ColorRole.ButtonText))
        combo.setPalette(palette)
        self._targets_tooltip = combo.toolTip()

        # --- Pairing: how each mineral's lines are paired with the peaks ---
        # The scorer's key rides on each item, so the order of the items in
        # the .ui is free. Greedy (the original) is the default.
        pairing = self.ui.cmb_pairing
        for row, (key, tip) in enumerate((
            (pd.PAIRING_GREEDY,
             "Greedy (the original): from the largest d-spacing down, each "
             "reference line takes its nearest peak, if no earlier line took it. "
             "A line whose nearest peak is taken gives up."),
            (pd.PAIRING_ONE_TO_ONE,
             "One-to-one: the pairing that matches the most reference lines to "
             "different peaks, and of those the closest overall. Does not depend "
             "on the order of the lines."),
        )):
            pairing.setItemData(row, key)
            pairing.setItemData(row, tip, Qt.ItemDataRole.ToolTipRole)
        pairing.setCurrentIndex(0)
        pairing.currentIndexChanged.connect(lambda _i: self._rescore())

        # Selecting a mineral in either list draws its reflections on the main
        # plot as magenta sticks (the old mineral-preview overlay). "Specimen
        # range" limits them to the scanned 2theta range.
        self._last_peaks: list = []
        self.ui.chk_use_specimen_range.setToolTip(
            "Show only reference peaks that fall within the specimen's 2θ range."
        )
        self.ui.chk_use_specimen_range.toggled.connect(self._refresh_preview)
        self.ui.tv_minerals.selectionModel().selectionChanged.connect(
            lambda *_a: self._on_row_selected(self.ui.tv_minerals)
        )
        self.ui.tv_matches.selectionModel().selectionChanged.connect(
            lambda *_a: self._on_row_selected(self.ui.tv_matches)
        )

        # Old glade: btn_rtl = add (minerals -> matches), btn_ltr = remove.
        self.ui.btn_rtl.clicked.connect(self._add_selected_match)
        self.ui.btn_ltr.clicked.connect(self._remove_selected_match)
        self.ui.btn_apply.clicked.connect(self._on_apply)
        self.ui.buttonBox.rejected.connect(self.reject)
        # Search box: filter the all-minerals list by name/abbreviation as the
        # user types (the old app's Ctrl+F tree search, always visible here).
        self.ui.edit_search.textChanged.connect(self._filter_minerals)
        # Enter must never fire Append labels from the search box. The .ui
        # clears autoDefault and install_enter_policy re-clears on show; this
        # covers a dialog used without being shown (harnesses).
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)

        # Peaks added, removed or relabelled elsewhere (Append labels included)
        # must show up in the dropdown, and a deleted target must stop counting.
        if specimen is not None:
            specimen.visuals_changed.connect(self._on_specimen_visuals_changed)

        self._sync_targets_combo()
        self.ui.btn_apply.setEnabled(bool(self.targets))
        self._marker_peaks: list = []
        # Score straight away so the dialog opens with results (old app left it
        # empty until Auto match; every change of targets rescores the same way).
        self._rescore()
        self._show_target_highlight()

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
    # Targets dropdown
    # ------------------------------------------------------------------
    def _specimen_markers(self) -> list:
        if self.specimen is None:
            return []
        return sorted(self.specimen.markers, key=lambda m: m.position)

    def _is_target(self, marker) -> bool:
        return any(marker is t for t in self.targets)

    def _sync_targets_combo(self) -> None:
        """Show every peak in the dropdown, ticked when it is a target, with
        "<n> of <total> peaks" in the closed box. Updated in place when the set
        of peaks is unchanged, so an open popup is not disturbed."""
        markers = self._specimen_markers()
        model = self.targets_model
        listed = [model.item(r).data(_MARKER_ROLE) for r in range(model.rowCount())]
        same = len(listed) == len(markers) and all(
            a is b for a, b in zip(listed, markers))
        if not same:
            model.clear()
            for marker in markers:
                item = QStandardItem()
                # Selectable only for the popup's hover highlight; a click is
                # turned into a tick by _TickOnClick, never a choice.
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                              | Qt.ItemFlag.ItemIsUserCheckable)
                item.setData(marker, _MARKER_ROLE)
                model.appendRow(item)
        for row, marker in enumerate(markers):
            item = model.item(row)
            item.setText(_marker_text(marker))
            item.setCheckState(Qt.CheckState.Checked if self._is_target(marker)
                               else Qt.CheckState.Unchecked)
        combo = self.ui.cmb_targets
        total = len(markers)
        combo.setPlaceholderText(
            f"{len(self.targets)} of {total} peak{'' if total == 1 else 's'}")
        combo.setCurrentIndex(-1)  # the summary, never one row's text
        names = "\n".join(_marker_text(m) for m in self.targets)
        combo.setToolTip(self._targets_tooltip
                         + ("\n\nCurrent targets:\n" + names if names else ""))

    def _toggle_target_row(self, row: int) -> None:
        item = self.targets_model.item(row)
        marker = item.data(_MARKER_ROLE) if item is not None else None
        if marker is not None:
            self.toggle_target(marker)

    def _on_target_activated(self, row: int) -> None:
        # Enter on a row of the open popup: same as clicking it.
        self._toggle_target_row(row)
        self.ui.cmb_targets.setCurrentIndex(-1)

    def toggle_target(self, marker) -> bool:
        """Add `marker` to the targets, or remove it if it is one, and rescore.
        The last target cannot be removed. Returns True if the targets changed."""
        if self._is_target(marker):
            if len(self.targets) <= 1:
                QToolTip.showText(QCursor.pos(), _KEEP_ONE_TARGET, self.ui.cmb_targets)
                self._sync_targets_combo()  # undo the tick the click implied
                return False
            self.targets = [t for t in self.targets if t is not marker]
        else:
            self.targets = self.targets + [marker]
        self._targets_changed()
        return True

    def _targets_changed(self) -> None:
        self._sync_targets_combo()
        self.ui.btn_apply.setEnabled(bool(self.targets))
        self._rescore()
        self._show_target_highlight()

    def _on_specimen_visuals_changed(self) -> None:
        if self._session_ended:
            return
        # A target deleted elsewhere no longer exists: stop scoring against it.
        alive = self.specimen.markers if self.specimen is not None else ()
        kept = [t for t in self.targets if any(t is m for m in alive)]
        if len(kept) != len(self.targets):
            self.targets = kept
            self._targets_changed()
        else:
            self._sync_targets_combo()  # a label or the set of peaks changed

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------
    def _score_all(self, peaks) -> list:
        """[(reference index, score)] best first - exactly score_minerals'
        result over the whole library (its sort is stable, and so is this one,
        so even ties come out in the same order), but with each row's index
        kept, which the one-call form loses."""
        scored = []
        pairing = self.pairing()
        for idx, mineral in enumerate(self._minerals):
            result = pd.score_minerals(peaks, [mineral], pairing=pairing)
            if result:
                scored.append((idx, result[0][4]))
        scored.sort(key=lambda s: s[1], reverse=True)
        return scored

    def _score_one(self, idx: int) -> float:
        if not self._marker_peaks:
            return 0.0
        result = pd.score_minerals(self._marker_peaks, [self._minerals[idx]],
                                   pairing=self.pairing())
        return result[0][4] if result else 0.0

    def pairing(self) -> str:
        """The scorer's pairing mode chosen in the Pairing box."""
        return self.ui.cmb_pairing.currentData() or pd.PAIRING_GREEDY

    def set_pairing(self, pairing: str) -> None:
        """Choose a pairing mode (rescores, like picking it in the box)."""
        index = self.ui.cmb_pairing.findData(pairing)
        if index < 0:
            raise ValueError("Unknown pairing %r" % (pairing,))
        self.ui.cmb_pairing.setCurrentIndex(index)

    def _rescore(self) -> None:
        """Score the library against the current targets. Rows added by hand
        stay (rescored), and the mineral the user had selected stays selected,
        so its reference lines remain on the plot while targets are added."""
        selected = self._selected_match_index()
        manual = [self.matches_model.item(r, 0).data(_INDEX_ROLE)
                  for r in range(self.matches_model.rowCount())
                  if self.matches_model.item(r, 0).data(_MANUAL_ROLE)]
        self._marker_peaks = self._compute_marker_peaks()
        self.matches_model.removeRows(0, self.matches_model.rowCount())
        if self._marker_peaks:
            for idx, score in self._score_all(self._marker_peaks):
                self._append_match_row(idx, score, manual=idx in manual)
        for idx in manual:
            if self._match_row_for_index(idx) is None:
                self._append_match_row(idx, self._score_one(idx), manual=True)
        if self.matches_model.rowCount():
            row = self._match_row_for_index(selected) if selected is not None else None
            # The best (top) match otherwise, as the old reload_matches did.
            self.ui.tv_matches.setCurrentIndex(
                self.matches_model.index(row if row is not None else 0, 0))

    def _selected_match_index(self):
        rows = self.ui.tv_matches.selectionModel().selectedRows()
        if not rows:
            return None
        return self.matches_model.item(rows[0].row(), 0).data(_INDEX_ROLE)

    def _add_selected_match(self) -> None:
        """Add the mineral(s) selected in the all-minerals list to the matches,
        scored individually (old add_match). The reference is identified by its
        row index, not its name, so the correct peaks are used even for the few
        duplicate-named entries (and both duplicates can be added)."""
        for index in self.ui.tv_minerals.selectionModel().selectedRows():
            idx = self.minerals_model.itemFromIndex(index).data(_INDEX_ROLE)
            if idx is None or self._match_row_for_index(idx) is not None:
                continue  # nothing resolvable, or this exact row is already listed
            self._append_match_row(idx, self._score_one(idx), manual=True)

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
        back to the label (old apply_cb, which also used the CURRENT targets)."""
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
            self._sync_targets_combo()  # the dropdown shows the new labels
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
    def _append_match_row(self, idx: int, score: float, manual: bool = False) -> None:
        """One matches row for reference `idx`. It carries the FULL reference
        peak list, so a mineral previews the same lines from either list."""
        name, abbr, peaks = self._minerals[idx]
        name_item = _readonly_item(name)
        name_item.setData(idx, _INDEX_ROLE)  # remember the source row
        name_item.setData(peaks, _PEAKS_ROLE)  # for the preview overlay
        if manual:
            name_item.setData(True, _MANUAL_ROLE)
        score_item = _readonly_item(f"{score:.5f}")
        score_item.setData(float(score), _SCORE_ROLE)
        self.matches_model.appendRow([name_item, _readonly_item(abbr), score_item])

    def _match_row_for_index(self, idx):
        """The matches row holding reference row `idx`, or None."""
        if idx is None:
            return None
        for row in range(self.matches_model.rowCount()):
            if self.matches_model.item(row, 0).data(_INDEX_ROLE) == idx:
                return row
        return None

    def _filter_minerals(self, text: str) -> None:
        """Filter the all-minerals list to rows whose name OR abbreviation
        contains the search text (case-insensitive); an empty box shows all.
        Rows are hidden in the view, so the model, indices and selection/data
        logic are untouched (228 references, so a linear pass is fine)."""
        needle = text.strip().lower()
        root = QModelIndex()
        tv = self.ui.tv_minerals
        for row in range(self.minerals_model.rowCount()):
            name = self.minerals_model.item(row, 0).text().lower()
            abbr_item = self.minerals_model.item(row, 1)
            abbr = abbr_item.text().lower() if abbr_item is not None else ""
            hidden = bool(needle) and needle not in name and needle not in abbr
            tv.setRowHidden(row, root, hidden)

    # ------------------------------------------------------------------
    # Reference-peak preview overlay (magenta sticks on the main plot)
    # ------------------------------------------------------------------
    def _on_row_selected(self, tree_view) -> None:
        rows = tree_view.selectionModel().selectedRows()
        if not rows:
            return  # transient deselection during (re)population: keep the last
        item = tree_view.model().itemFromIndex(rows[0])
        self._last_peaks = item.data(_PEAKS_ROLE) or []
        self._refresh_preview()

    def _preview_host(self):
        """Walk up to the main window (has set_mineral_preview) so a selection
        redraws the plot in place rather than triggering a full rebuild via
        visuals_changed. None when there is no such host (fall back to the
        model-driven path)."""
        widget = self.parent()
        while widget is not None:
            if hasattr(widget, "set_mineral_preview"):
                return widget
            widget = widget.parent()
        return None

    def _refresh_preview(self) -> None:
        if self.specimen is None or self._session_ended:
            return
        peaks = self._preview_peaks()
        host = self._preview_host()
        if host is not None:
            host.set_mineral_preview(self.specimen, peaks)  # lightweight redraw
        else:
            self.specimen.set_mineral_preview(peaks)  # model-driven fallback

    def _preview_peaks(self):
        """The selected mineral's reflections as ``[(2theta, rel_intensity)]``,
        dropping any without a Bragg solution and (when "Specimen range" is on)
        any outside the experimental 2theta range."""
        if self.specimen is None or not self._last_peaks:
            return []
        wavelength = self.specimen.wavelength
        x, _ = self.specimen.experimental_pattern
        use_range = self.ui.chk_use_specimen_range.isChecked() and x.size > 0
        if use_range:
            x_min, x_max = float(np.min(x)), float(np.max(x))
        out = []
        for d_angstrom, rel_intensity in self._last_peaks:
            nm = d_angstrom / 10.0
            if nm <= wavelength / 2.0:
                continue  # d < lambda/2 -> no Bragg reflection
            two_theta = get_2t_from_nm(nm, wavelength)
            if not np.isfinite(two_theta):
                continue
            if use_range and not (x_min <= two_theta <= x_max):
                continue
            out.append((two_theta, float(rel_intensity)))
        return out

    # ------------------------------------------------------------------
    # Target highlight + view-only plot, for as long as the dialog is open
    # ------------------------------------------------------------------
    def _show_target_highlight(self, clear: bool = False) -> None:
        if self.specimen is None:
            return
        markers = None if clear else self.targets
        host = self._preview_host()
        if host is not None and hasattr(host, "set_match_targets"):
            host.set_match_targets(self.specimen, markers)  # lightweight redraw
        elif host is None:
            self.specimen.set_match_targets(markers)  # model-driven fallback
        else:  # a host without the highlight: keep the model honest, no emit
            self.specimen.match_targets = list(markers) if markers else None

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # View-only plot while open: zoom and pan, no clicks. A double-click on
        # a peak would otherwise rebuild the Peaks window and destroy this one.
        if not self._plot_locked and not self._session_ended:
            host = self._preview_host()
            if host is not None and hasattr(host, "set_plot_interaction_locked"):
                host.set_plot_interaction_locked(True, owner=self)
                self._plot_locked = True

    def _end_session(self) -> None:
        """Drop everything the dialog put on the plot and unlock it. Idempotent:
        reached from done() (Close, Esc, window X) and from closeEvent."""
        if self._session_ended:
            return
        self._session_ended = True
        if self.specimen is not None:
            try:
                self.specimen.visuals_changed.disconnect(
                    self._on_specimen_visuals_changed)
            except (RuntimeError, TypeError):
                pass
            host = self._preview_host()
            if host is not None:
                host.clear_mineral_preview(self.specimen)
            else:
                self.specimen.set_mineral_preview(None)
            self._show_target_highlight(clear=True)
            if self._plot_locked and host is not None:
                host.set_plot_interaction_locked(False, owner=self)
        self._plot_locked = False

    def done(self, result: int) -> None:
        # Every way out (Close button, Esc, window X, close()) passes here.
        self._end_session()
        super().done(result)

    def closeEvent(self, event) -> None:
        # close() on a dialog that is not visible skips done(); end it anyway.
        super().closeEvent(event)
        self._end_session()


def _marker_text(marker) -> str:
    """How a peak reads in the Targets dropdown: its label and 2theta."""
    label = (marker.label or "").strip() or "(no label)"
    hidden = "" if marker.visible else "  (hidden)"
    return f"{label}   {marker.position:.2f}°{hidden}"


def _readonly_item(text: str) -> QStandardItem:
    item = QStandardItem(text)
    item.setEditable(False)
    return item
