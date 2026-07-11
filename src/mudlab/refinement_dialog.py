"""Refinement window. Design: ui/refinement.ui.

Ported from the GTK RefinementView/RefinerView (refinement/views/glade/
refinement.glade + refine_results.glade). Opened from the Edit Mixtures
Refine button for the current mixture: a table of the mixture's refinable
structural parameters (value + editable min/max + a Refine toggle), a
method combo (0 = L-BFGS-B, 1 = Basin Hopping), a Refine button, and the
Initial / Best / Last residuals with buttons to keep one of those solutions.

Phase B is synchronous - Refine runs under a busy cursor and blocks; the
Cancel button + live status (the engine's stop hook) and the progress plot
come with the threaded Phase C. The per-method options and the
auto-restrict / randomize helpers are wired in B2 (disabled here).
"""

from __future__ import annotations

import random
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QDoubleSpinBox, QFormLayout, QHeaderView, QMessageBox,
    QSpinBox, QTableWidgetItem, QWidget,
)

from mudlab.calculations.refinement import REFINE_METHODS, refine_mixture
from mudlab.ui.ui_refinement import Ui_RefinementDialog

_COL_NAME, _COL_VALUE, _COL_MIN, _COL_MAX, _COL_REFINE = range(5)
_HEADERS = ["Parameter", "Value", "Min", "Max", "Refine"]

# Per-method OUTER-search options (name, label, default, min, max, kind). The
# inner fraction/scale/bg optimiser keeps its own fixed limits. Old sources:
# scipy_runs.py (L-BFGS-B / Basin Hopping); indices match REFINE_METHODS.
_METHOD_OPTIONS = {
    0: [
        ("maxfun", "Max # function calls", 500, 1, 1_000_000, int),
        ("maxiter", "Max # iterations", 150, 1, 1_000_000, int),
    ],
    1: [
        ("niter", "Number of iterations", 100, 1, 100_000, int),
        ("T", "Temperature", 1.0, 0.0, 10_000.0, float),
        ("stepsize", "Step size", 0.5, 0.0, 1_000.0, float),
    ],
}


class RefinementDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, mixture=None,
                 on_applied: Callable[[], None] | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_RefinementDialog()
        self.ui.setupUi(self)

        self._mixture = mixture
        self._on_applied = on_applied
        self._refinables: list = []
        self._refiner = None
        self._updating = False
        self._option_spins: dict = {}
        self._options_form = QFormLayout()
        self.ui.optionsLayout.addLayout(self._options_form)

        table = self.ui.tbl_refinables
        table.setColumnCount(len(_HEADERS))
        table.setHorizontalHeaderLabels(_HEADERS)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        for col in (_COL_VALUE, _COL_MIN, _COL_MAX, _COL_REFINE):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        # Method combo: only the two convergent SciPy methods.
        for index, (name, _fn) in sorted(REFINE_METHODS.items()):
            self.ui.cmb_method.addItem(name, index)
        self._select_stored_method()
        self._build_options_form(int(self.ui.cmb_method.currentData()))

        table.itemChanged.connect(self._on_item_changed)
        self.ui.cmb_method.currentIndexChanged.connect(self._on_method_changed)
        self.ui.btn_refine.clicked.connect(self._on_refine)
        self.ui.btn_auto_restrict.clicked.connect(self._on_auto_restrict)
        self.ui.btn_randomize.clicked.connect(self._on_randomize)
        self.ui.btn_apply_initial.clicked.connect(lambda: self._on_apply("initial"))
        self.ui.btn_apply_best.clicked.connect(lambda: self._on_apply("best"))
        self.ui.btn_apply_last.clicked.connect(lambda: self._on_apply("last"))
        self.ui.buttonBox.rejected.connect(self.reject)

        self._set_apply_enabled(False)
        self._populate()

    # ------------------------------------------------------------------
    def _select_stored_method(self) -> None:
        stored = 0
        if self._mixture is not None:
            stored = int(self._mixture.raw_properties.get("refine_method_index", 0) or 0)
        if stored not in REFINE_METHODS:
            stored = 0
        self.ui.cmb_method.setCurrentIndex(self.ui.cmb_method.findData(stored))

    def _populate(self) -> None:
        table = self.ui.tbl_refinables
        self._updating = True
        try:
            self._refinables = (
                self._mixture.refinables() if self._mixture is not None else []
            )
            table.setRowCount(len(self._refinables))
            for row, ref in enumerate(self._refinables):
                self._set_text(row, _COL_NAME, ref.label, editable=False)
                self._set_text(row, _COL_VALUE, "%.4f" % ref.value, editable=False)
                self._set_text(row, _COL_MIN, "%.4f" % ref.minimum, editable=True)
                self._set_text(row, _COL_MAX, "%.4f" % ref.maximum, editable=True)
                self._set_check(row, _COL_REFINE, ref.refine)
        finally:
            self._updating = False

    def _refresh_values(self) -> None:
        """After a refine/apply the model values changed; refresh Value column
        (and Min/Max/refine, which auto-restrict/randomize may have touched)."""
        table = self.ui.tbl_refinables
        self._updating = True
        try:
            for row, ref in enumerate(self._refinables):
                table.item(row, _COL_VALUE).setText("%.4f" % ref.value)
                table.item(row, _COL_MIN).setText("%.4f" % ref.minimum)
                table.item(row, _COL_MAX).setText("%.4f" % ref.maximum)
                self._set_check(row, _COL_REFINE, ref.refine)
        finally:
            self._updating = False

    # ------------------------------------------------------------------
    # Editing the tree
    # ------------------------------------------------------------------
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return
        row, col = item.row(), item.column()
        if not (0 <= row < len(self._refinables)):
            return
        ref = self._refinables[row]
        if col == _COL_REFINE:
            ref.set_ref_info(refine=item.checkState() == Qt.CheckState.Checked)
        elif col in (_COL_MIN, _COL_MAX):
            try:
                value = float(item.text())
            except ValueError:
                self._updating = True
                try:
                    item.setText("%.4f" % (ref.minimum if col == _COL_MIN else ref.maximum))
                finally:
                    self._updating = False
                return
            if col == _COL_MIN:
                ref.set_ref_info(minimum=value)
            else:
                ref.set_ref_info(maximum=value)

    def _on_method_changed(self, _index: int) -> None:
        if self._updating:
            return
        method_index = int(self.ui.cmb_method.currentData())
        if self._mixture is not None:
            self._mixture.raw_properties["refine_method_index"] = method_index
        self._build_options_form(method_index)

    # ------------------------------------------------------------------
    # Per-method options + auto-restrict / randomize (B2)
    # ------------------------------------------------------------------
    def _build_options_form(self, method_index: int) -> None:
        """(Re)build the outer-method options form, seeded from the mixture's
        stored refine_options[method] or the method defaults."""
        self._updating = True
        try:
            while self._options_form.rowCount():
                self._options_form.removeRow(0)
            self._option_spins = {}
            stored = self._stored_options(method_index)
            for name, label, default, lo, hi, kind in _METHOD_OPTIONS.get(method_index, []):
                spin = QSpinBox() if kind is int else QDoubleSpinBox()
                if kind is float:
                    spin.setDecimals(3)
                spin.setRange(lo, hi)
                spin.setValue(kind(stored.get(name, default)))
                spin.valueChanged.connect(self._save_options)
                self._options_form.addRow(label, spin)
                self._option_spins[name] = (spin, kind)
        finally:
            self._updating = False

    def _stored_options(self, method_index: int) -> dict:
        if self._mixture is None:
            return {}
        opts = self._mixture.raw_properties.get("refine_options") or {}
        value = opts.get(str(method_index))
        return dict(value) if isinstance(value, dict) else {}

    def _save_options(self, *_args) -> None:
        if self._updating or self._mixture is None:
            return
        method_index = int(self.ui.cmb_method.currentData())
        opts = dict(self._mixture.raw_properties.get("refine_options") or {})
        opts[str(method_index)] = self._options()
        self._mixture.raw_properties["refine_options"] = opts

    def _on_auto_restrict(self) -> None:
        """Set Min/Max to +/-20% of each flagged parameter's current value
        (old RefinementModel.auto_restrict)."""
        for ref in self._refinables:
            if ref.refine:
                ref.set_ref_info(minimum=ref.value * 0.8, maximum=ref.value * 1.2)
        self._refresh_values()

    def _on_randomize(self) -> None:
        """Randomize each flagged parameter within its Min/Max (old
        RefinementModel.randomize) and recompute so the plot shows the new
        starting point; the user then Refines from here."""
        for ref in self._refinables:
            if ref.refine and ref.minimum < ref.maximum:
                ref.value = random.uniform(ref.minimum, ref.maximum)
        if self._mixture is not None:
            self._mixture.calculate()
        self._refresh_values()
        if self._on_applied is not None:
            self._on_applied()

    # ------------------------------------------------------------------
    # Running the refinement (synchronous - Phase B)
    # ------------------------------------------------------------------
    def _on_refine(self) -> None:
        if self._mixture is None:
            return
        method_index = int(self.ui.cmb_method.currentData())
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.setEnabled(False)
        QApplication.processEvents()  # paint the disabled/busy state before blocking
        try:
            refiner = refine_mixture(self._mixture, method_index, self._options())
            self._mixture.calculate()  # recompute patterns + redraw via signals
        except Exception as exc:  # noqa: BLE001 - surface, don't crash
            self.setEnabled(True)
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self, "Refinement failed",
                "The refinement could not complete:\n\n%s" % exc,
            )
            return
        finally:
            self.setEnabled(True)
            QApplication.restoreOverrideCursor()

        self._refiner = refiner
        self._show_results(refiner)
        self._refresh_values()
        self._set_apply_enabled(True)
        if self._on_applied is not None:
            self._on_applied()

    def _on_apply(self, which: str) -> None:
        if self._refiner is None or self._mixture is None:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            getattr(self._refiner, "apply_" + which)()
            self._mixture.calculate()
        finally:
            QApplication.restoreOverrideCursor()
        self._refresh_values()
        if self._on_applied is not None:
            self._on_applied()

    def _options(self) -> dict:
        """The current method's options read from the options form."""
        return {name: kind(spin.value()) for name, (spin, kind) in self._option_spins.items()}

    def _show_results(self, refiner) -> None:
        def fmt(value):
            return "-" if value is None else "%.4f %%" % value
        self.ui.lbl_initial_residual.setText(fmt(refiner.initial_residual))
        self.ui.lbl_best_residual.setText(fmt(refiner.best_residual))
        self.ui.lbl_last_residual.setText(fmt(refiner.last_residual))

    def _set_apply_enabled(self, enabled: bool) -> None:
        for button in (self.ui.btn_apply_initial, self.ui.btn_apply_best,
                       self.ui.btn_apply_last):
            button.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Cell helpers
    # ------------------------------------------------------------------
    def _set_text(self, row: int, col: int, text: str, editable: bool) -> None:
        item = QTableWidgetItem(text)
        flags = Qt.ItemFlag.ItemIsEnabled
        if editable:
            flags |= Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
        item.setFlags(flags)
        self.ui.tbl_refinables.setItem(row, col, item)

    def _set_check(self, row: int, col: int, checked: bool) -> None:
        item = self.ui.tbl_refinables.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.tbl_refinables.setItem(row, col, item)
        item.setCheckState(
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        )
