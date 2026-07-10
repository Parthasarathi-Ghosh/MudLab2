"""Mixture editor form. Design: ui/edit_mixture.ui.

Ported from the GTK EditMixtureView (mixture/views/glade/
edit_mixture.glade). Plugged into the Properties pane of the Edit
Mixtures window. The matrix is phase slots (rows) x specimens (columns):
each specimen carries an absolute scale and a background shift, each phase
slot a weight fraction, and every cell names the phase that fills that
slot for that specimen.

Batch 1 of the editor-wiring port binds the real Mixture model and makes
the numeric parameters (fractions / scales / background shifts) editable
with a live recalculation of the calculated pattern. Phase-cell
reassignment, structural add/remove and the fraction/scale/bg optimizer
(the Refine/Optimize/auto-* controls) come with later batches and are
disabled for now.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QHeaderView, QMessageBox, QTableWidgetItem, QWidget,
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
        self._on_changed: Callable[[], None] | None = None

        # Still a later port: the full Refinement window (btn_refine), the
        # composition summary, and structural add/remove. Disabled so the UI
        # reads honestly. The one-shot Optimize + the auto-* flags are live.
        for control, why in (
            (self.ui.btn_refine, "The Refinement window is not ported yet."),
            (self.ui.btn_composition, "Composition summary is not ported yet."),
            (self.ui.btn_add_phase, "Adding phase slots is not ported yet."),
            (self.ui.btn_add_specimen, "Adding specimens is not ported yet."),
            (self.ui.btn_add_both, "Adding rows/columns is not ported yet."),
        ):
            control.setEnabled(False)
            control.setToolTip(why)

        self.ui.mixture_name.editingFinished.connect(self._on_name_edited)
        self.ui.tbl_matrix.itemChanged.connect(self._on_item_changed)
        self.ui.btn_optimize.clicked.connect(self._on_optimize)
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
    def bind_mixture(self, mixture, on_changed: Callable[[], None] | None = None) -> None:
        """Show and edit a real Mixture model. `on_changed` is called after
        every accepted edit (used to recompute + redraw the pattern)."""
        self._mixture = mixture
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

            # Per-phase-slot fraction + the phase filling each cell.
            for j in range(m_slot):
                row = _FIRST_PHASE_ROW + j
                self._set_cell(row, _COL_FRACTION, self._fmt(mixture.fractions, j, 4), editable=True)
                for i in range(n_spec):
                    phase = self._phase_at(i, j)
                    name = phase.name if phase is not None else "-"
                    self._set_cell(row, _FIRST_SPEC_COL + i, name, editable=False)

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

    def _set_cell(self, row: int, col: int, text: str, editable: bool) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        flags = Qt.ItemFlag.ItemIsEnabled
        if editable:
            flags |= Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
        item.setFlags(flags)
        self.ui.tbl_matrix.setItem(row, col, item)
