"""Mixture editor form. Design: ui/edit_mixture.ui.

Ported from the GTK EditMixtureView (mixture/views/glade/
edit_mixture.glade). Plugged into the Properties pane of the Edit
Mixtures window. The matrix is phase slots (rows) x specimens (columns):
each specimen carries an absolute scale and a background shift, each phase
slot a weight fraction, and every cell names the phase that fills that
slot for that specimen.

The numeric parameters (fractions / scales / background shifts) are editable
with a live recalculation, and the fraction/scale/bg Optimize + Refine controls
are wired. Each phase cell is a combo that assigns WHICH phase fills that slot
for that specimen (or "(none)" to empty it); only VALID phases are selectable -
a phase with an empty component slot (no atoms) is shown greyed, so an
incomplete New Phase cannot be assigned.

Structural editing is wired too: the Add phase / Add specimen / Add both buttons
append a slot or specimen, and right-clicking a phase-slot row header (rename /
remove) or a specimen column header (assign a project specimen / remove) does
the structural edits - kept on the headers so the grid stays a clean value
matrix. The Composition button opens the read-only oxide-composition summary.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHeaderView, QInputDialog, QMenu, QMessageBox,
    QTableWidgetItem, QWidget,
)

from mudlab.ui.ui_edit_mixture import Ui_EditMixtureWidget

# Row layout of tbl_matrix: two fixed header rows, then one row per phase slot.
_ROW_SCALE = 0
_ROW_BG = 1
_FIRST_PHASE_ROW = 2
_COL_FRACTION = 0
_FIRST_SPEC_COL = 1


class EditMixtureWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditMixtureWidget()
        self.ui.setupUi(self)

        self._mixture = None
        self._phases: list = []
        self._specimens: list = []
        self._on_changed: Callable[[], None] | None = None

        self.ui.mixture_name.editingFinished.connect(self._on_name_edited)
        self.ui.tbl_matrix.itemChanged.connect(self._on_item_changed)
        self.ui.btn_optimize.clicked.connect(self._on_optimize)
        self.ui.btn_refine.clicked.connect(self._on_refine)
        self.ui.btn_add_phase.clicked.connect(self._on_add_phase)
        self.ui.btn_add_specimen.clicked.connect(self._on_add_specimen)
        self.ui.btn_add_both.clicked.connect(self._on_add_both)
        self.ui.btn_composition.clicked.connect(self._on_composition)
        self._install_header_menus()
        self.ui.mixture_auto_run.toggled.connect(
            lambda checked: self._on_auto_toggled("auto_run", checked)
        )
        self.ui.mixture_auto_scales.toggled.connect(
            lambda checked: self._on_auto_toggled("auto_scales", checked)
        )
        self.ui.mixture_auto_bg.toggled.connect(
            lambda checked: self._on_auto_toggled("auto_bg", checked)
        )

    # ------------------------------------------------------------------
    def bind_mixture(self, mixture, phases=None, specimens=None,
                     on_changed: Callable[[], None] | None = None) -> None:
        """Show and edit a real Mixture model. `phases` are the project's phases
        offered in each cell's phase combo (invalid ones greyed); `specimens`
        are the project's specimens offered when assigning a specimen column
        (right-click its header). `on_changed` is called after every accepted
        edit (used to recompute + redraw)."""
        self._mixture = mixture
        self._phases = list(phases or [])
        self._specimens = list(specimens or [])
        self._on_changed = on_changed
        self._populate()
        self._update_residual_label()

    def _populate(self) -> None:
        mixture = self._mixture
        table = self.ui.tbl_matrix
        # Block change signals while we build, or every setItem / setChecked
        # would fire its handler.
        checkboxes = (
            self.ui.mixture_auto_run,
            self.ui.mixture_auto_scales,
            self.ui.mixture_auto_bg,
        )
        table.blockSignals(True)
        self.ui.mixture_name.blockSignals(True)
        for box in checkboxes:
            box.blockSignals(True)
        try:
            if mixture is None:
                self.ui.mixture_name.setText("")
                table.clear()
                table.setRowCount(0)
                table.setColumnCount(0)
                return

            self.ui.mixture_name.setText(mixture.name)
            # Reflect the stored optimizer preferences (auto_scales/bg default
            # on in the old model; they select which variables Optimize frees).
            raw = mixture.raw_properties
            self.ui.mixture_auto_run.setChecked(bool(raw.get("auto_run", False)))
            self.ui.mixture_auto_scales.setChecked(bool(raw.get("auto_scales", True)))
            self.ui.mixture_auto_bg.setChecked(bool(raw.get("auto_bg", True)))

            specimens = mixture.specimens
            labels = mixture.phase_labels
            n_spec = len(specimens)
            m_slot = len(labels)

            table.clear()
            table.setRowCount(0)  # also drops phase-combo cell widgets from a prior bind
            table.setColumnCount(_FIRST_SPEC_COL + n_spec)
            table.setRowCount(_FIRST_PHASE_ROW + m_slot)
            table.setHorizontalHeaderLabels(
                ["Fraction", *(self._specimen_name(s, i) for i, s in enumerate(specimens))]
            )
            table.setVerticalHeaderLabels(["Abs. scale", "Bg. shift", *labels])

            # Corner cells (Fraction x scale/bg) are meaningless: blank + locked.
            for row in (_ROW_SCALE, _ROW_BG):
                self._set_cell(row, _COL_FRACTION, "", editable=False)

            # Per-specimen scale + background rows.
            for i in range(n_spec):
                col = _FIRST_SPEC_COL + i
                self._set_cell(_ROW_SCALE, col, self._fmt(mixture.scales, i, 4), editable=True)
                self._set_cell(_ROW_BG, col, self._fmt(mixture.bgshifts, i, 3), editable=True)

            # Per-phase-slot fraction + a combo assigning the phase in each cell.
            for j in range(m_slot):
                row = _FIRST_PHASE_ROW + j
                self._set_cell(row, _COL_FRACTION, self._fmt(mixture.fractions, j, 4),
                               editable=True, check=mixture.fraction_refine(j))
                for i in range(n_spec):
                    self._set_phase_combo(row, _FIRST_SPEC_COL + i, i, j)

            header = table.horizontalHeader()
            for col in range(table.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        finally:
            table.blockSignals(False)
            self.ui.mixture_name.blockSignals(False)
            for box in checkboxes:
                box.blockSignals(False)

    # ------------------------------------------------------------------
    # Optimizer + auto-* flags
    # ------------------------------------------------------------------
    def _on_auto_toggled(self, key: str, checked: bool) -> None:
        """auto_run / auto_scales / auto_bg select which variables Optimize
        frees; store the flag (it round-trips) and mark the project changed."""
        if self._mixture is None:
            return
        self._mixture.raw_properties[key] = bool(checked)
        self._notify()

    def _on_optimize(self) -> None:
        """Run the L-BFGS-B refinement for this mixture. The optimizer core
        fails loud; this is the UI-boundary safety net (busy cursor + an error
        dialog) so a bad refine never takes the app down or corrupts state -
        optimize() only writes the model on success."""
        if self._mixture is None:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            residual = self._mixture.optimize()
        except Exception as exc:  # noqa: BLE001 - surface, don't crash
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self, "Refinement failed",
                "The refinement could not complete:\n\n%s" % exc,
            )
            return
        finally:
            QApplication.restoreOverrideCursor()
        # optimize() already recomputed + stored the patterns (which redraws
        # the plot via the specimens' data_changed); just refresh this editor.
        self._populate()
        self._show_residual(residual)

    def _on_refine(self) -> None:
        """Open the Refinement window for this mixture (structural-parameter
        refinement). It edits the same model, so refresh this editor's matrix +
        residual after it closes."""
        if self._mixture is None:
            return
        from mudlab.refinement_dialog import RefinementDialog

        dialog = RefinementDialog(self, mixture=self._mixture)
        dialog.exec()
        self._populate()
        self._update_residual_label()

    def _on_composition(self) -> None:
        """Show the mixture's oxide composition (a read-only per-specimen table
        with CSV copy/export). Old app: on_composition_clicked."""
        if self._mixture is None:
            return
        from mudlab.composition_dialog import CompositionDialog

        CompositionDialog(self._mixture, self).exec()

    def _update_residual_label(self) -> None:
        if self._mixture is None:
            self.ui.lbl_residual.setText("Residual (Rp): -")
            return
        try:
            self._show_residual(self._mixture.current_residual())
        except Exception:  # noqa: BLE001 - a display convenience, never fatal
            self.ui.lbl_residual.setText("Residual (Rp): -")

    def _show_residual(self, residual: float) -> None:
        self.ui.lbl_residual.setText("Residual (Rp): %.3f %%" % residual)

    # ------------------------------------------------------------------
    # Editing
    # ------------------------------------------------------------------
    def _on_name_edited(self) -> None:
        if self._mixture is None:
            return
        self._mixture.name = self.ui.mixture_name.text()
        self._notify()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._mixture is None:
            return
        row, col = item.row(), item.column()
        # The fraction cell carries a "refine this fraction" checkbox; sync its
        # state to the model. A toggle never changes the cell text, so the
        # fraction fall-through below always parses and fires the single _notify
        # that persists this mask change.
        if row >= _FIRST_PHASE_ROW and col == _COL_FRACTION:
            slot = row - _FIRST_PHASE_ROW
            refine = item.checkState() == Qt.CheckState.Checked
            if self._mixture.fraction_refine(slot) != refine:
                self._mixture.set_fraction_refine(slot, refine)
        target = self._field_for(row, col)
        if target is None:
            return  # phase cell / corner - not editable
        array, index = target
        try:
            value = float(item.text())
        except ValueError:
            # Reject: restore the model value without re-triggering.
            self._revert(item, array, index)
            return
        if 0 <= index < len(array):
            array[index] = value
            self._notify()
            self._update_residual_label()

    def _field_for(self, row: int, col: int):
        """Map a table cell to (model array, index) or None if not editable."""
        mixture = self._mixture
        if row == _ROW_SCALE and col >= _FIRST_SPEC_COL:
            return mixture.scales, col - _FIRST_SPEC_COL
        if row == _ROW_BG and col >= _FIRST_SPEC_COL:
            return mixture.bgshifts, col - _FIRST_SPEC_COL
        if row >= _FIRST_PHASE_ROW and col == _COL_FRACTION:
            return mixture.fractions, row - _FIRST_PHASE_ROW
        return None

    def _notify(self) -> None:
        if self._on_changed is not None:
            self._on_changed()

    def _revert(self, item: QTableWidgetItem, array, index: int) -> None:
        table = self.ui.tbl_matrix
        table.blockSignals(True)
        try:
            decimals = 4 if array is not self._mixture.bgshifts else 3
            item.setText(self._fmt(array, index, decimals))
        finally:
            table.blockSignals(False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _phase_at(self, specimen_index: int, slot_index: int):
        grid = self._mixture.phase_matrix
        if specimen_index < len(grid) and slot_index < len(grid[specimen_index]):
            return grid[specimen_index][slot_index]
        return None

    @staticmethod
    def _specimen_name(specimen, index: int) -> str:
        if specimen is not None and getattr(specimen, "name", ""):
            return specimen.name
        return "Specimen %d" % (index + 1)

    @staticmethod
    def _fmt(array, index: int, decimals: int) -> str:
        if 0 <= index < len(array):
            return f"{float(array[index]):.{decimals}f}"
        return ""

    def _set_cell(self, row: int, col: int, text: str, editable: bool,
                  check: bool | None = None) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        flags = Qt.ItemFlag.ItemIsEnabled
        if editable:
            flags |= Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
        if check is not None:
            # A per-phase "refine this fraction" checkbox lives on the fraction
            # cell (old app: fractions_mask). Unchecked = the fraction is held
            # fixed by Optimize.
            flags |= Qt.ItemFlag.ItemIsUserCheckable
            item.setCheckState(
                Qt.CheckState.Checked if check else Qt.CheckState.Unchecked)
            item.setToolTip("Refine this phase's fraction during Optimize "
                            "(uncheck to hold it fixed).")
        item.setFlags(flags)
        self.ui.tbl_matrix.setItem(row, col, item)

    def _set_phase_combo(self, row: int, col: int,
                         specimen_index: int, slot_index: int) -> None:
        """A combo naming the phase in this cell. Offers "(none)" + every
        project phase; an INVALID phase (empty component slot -> blank pattern)
        is listed but greyed, so it cannot be assigned. The signal is connected
        AFTER the current value is set, so populating does not fire it."""
        combo = QComboBox()
        combo.addItem("(none)", None)
        current = self._phase_at(specimen_index, slot_index)
        selected = 0
        for phase in self._phases:
            combo.addItem(phase.name or "phase", phase)
            idx = combo.count() - 1
            if not getattr(phase, "is_valid", True):
                combo.model().item(idx).setEnabled(False)
                combo.setItemData(
                    idx, self._invalid_reason(phase),
                    Qt.ItemDataRole.ToolTipRole)
            if phase is current:
                selected = idx
        combo.setCurrentIndex(selected)
        combo.currentIndexChanged.connect(
            lambda _i, c=combo, si=specimen_index, sj=slot_index:
            self._on_phase_reassigned(si, sj, c))
        self.ui.tbl_matrix.setCellWidget(row, col, combo)

    @staticmethod
    def _invalid_reason(phase) -> str:
        """Why `phase` is greyed in the slot combo, worded for its type: a raw
        phase is invalid for want of a measured pattern, a structural phase for
        an empty component slot (a New Phase whose components have no atoms)."""
        if getattr(phase, "type", "") == "RawPatternPhase":
            return ("This raw-pattern phase has no measured pattern yet - "
                    "import one before assigning.")
        return ("This phase has an empty component slot (no atoms) - "
                "fill it before assigning.")

    def _on_phase_reassigned(self, specimen_index: int, slot_index: int,
                             combo: QComboBox) -> None:
        if self._mixture is None:
            return
        self._mixture.set_phase_at(specimen_index, slot_index, combo.currentData())
        self._notify()
        self._update_residual_label()

    # ------------------------------------------------------------------
    # Structural add / remove (slots + specimens)
    # ------------------------------------------------------------------
    def _on_add_phase(self) -> None:
        """Add a phase slot (a "New Phase" row, fraction 1, empty cells). Old
        app: add_phase_slot("New Phase", 1.0). Rename/fill it afterwards."""
        if self._mixture is None:
            return
        self._mixture.add_phase_slot("New Phase", 1.0)
        self._after_structural_change()

    def _on_add_specimen(self) -> None:
        """Add a specimen slot (an unassigned column, scale 1, bg 0). Old app:
        add_specimen_slot(None, 1.0, 0.0). Right-click its header to assign a
        specimen."""
        if self._mixture is None:
            return
        self._mixture.add_specimen_slot(None, 1.0, 0.0)
        self._after_structural_change()

    def _on_add_both(self) -> None:
        """Add a specimen column and a phase row in one step (old on_add_both)."""
        if self._mixture is None:
            return
        self._mixture.add_specimen_slot(None, 1.0, 0.0)
        self._mixture.add_phase_slot("New Phase", 1.0)
        self._after_structural_change()

    def _after_structural_change(self) -> None:
        """Rebuild the grid, recompute and refresh the residual after a slot /
        specimen was added or removed."""
        self._populate()
        self._notify()
        self._update_residual_label()

    # -- right-click header menus (rename / remove a slot; assign / remove a
    #    specimen). The delete + assign affordances live on the headers so the
    #    grid itself stays a clean value matrix.
    def _install_header_menus(self) -> None:
        table = self.ui.tbl_matrix
        for header, handler in (
            (table.verticalHeader(), self._on_slot_header_menu),
            (table.horizontalHeader(), self._on_specimen_header_menu),
        ):
            header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            header.customContextMenuRequested.connect(handler)

    def _on_slot_header_menu(self, pos) -> None:
        """Right-click a phase-slot row header: rename or remove that slot. The
        two fixed header rows (Abs. scale / Bg. shift) carry no slot."""
        if self._mixture is None:
            return
        header = self.ui.tbl_matrix.verticalHeader()
        row = header.logicalIndexAt(pos)
        if row < _FIRST_PHASE_ROW:
            return
        slot = row - _FIRST_PHASE_ROW
        menu = QMenu(self)
        act_rename = menu.addAction("Rename phase slot…")
        act_remove = menu.addAction("Remove phase slot")
        chosen = menu.exec(header.mapToGlobal(pos))
        if chosen is act_rename:
            self._rename_slot(slot)
        elif chosen is act_remove:
            self._mixture.del_phase_slot(slot)
            self._after_structural_change()

    def _rename_slot(self, slot_index: int) -> None:
        labels = self._mixture.phase_labels
        current = labels[slot_index] if 0 <= slot_index < len(labels) else ""
        text, ok = QInputDialog.getText(
            self, "Rename phase slot", "Slot name:", text=current)
        if ok:
            self._mixture.set_phase_label(slot_index, text)
            self._after_structural_change()

    def _on_specimen_header_menu(self, pos) -> None:
        """Right-click a specimen column header: assign which project specimen
        fills it (or (none)), or remove the column. The Fraction column carries
        no specimen."""
        if self._mixture is None:
            return
        header = self.ui.tbl_matrix.horizontalHeader()
        col = header.logicalIndexAt(pos)
        if col < _FIRST_SPEC_COL:
            return
        spec_index = col - _FIRST_SPEC_COL
        current = (self._mixture.specimens[spec_index]
                   if spec_index < len(self._mixture.specimens) else None)
        menu = QMenu(self)
        assign = menu.addMenu("Assign specimen")
        by_action = {}
        act_none = assign.addAction("(none)")
        act_none.setCheckable(True)
        act_none.setChecked(current is None)
        by_action[act_none] = None
        for spec in self._specimens:
            act = assign.addAction(getattr(spec, "name", "") or "specimen")
            act.setCheckable(True)
            act.setChecked(spec is current)
            by_action[act] = spec
        act_remove = menu.addAction("Remove specimen")
        chosen = menu.exec(header.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen is act_remove:
            self._mixture.del_specimen_slot(spec_index)
            self._after_structural_change()
        elif chosen in by_action:
            self._mixture.set_specimen_at(spec_index, by_action[chosen])
            self._after_structural_change()
