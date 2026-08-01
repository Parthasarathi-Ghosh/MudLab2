"""Refinement window. Design: ui/refinement.ui.

Ported from the GTK RefinementView/RefinerView (refinement/views/glade/
refinement.glade + refine_results.glade). Opened from the Edit Mixtures
Refine button for the current mixture: a table of the mixture's refinable
structural parameters (value + editable min/max + a Refine toggle), a
method combo (0 = L-BFGS-B, 1 = Basin Hopping), a Refine button, and the
Initial / Best / Last residuals + a GoF (best solution) readout with buttons
to keep one of those solutions.

Refine runs on a background thread (_RefineWorker + QThread): the window
stays responsive, a live status label shows the evaluation count + best Rp,
and Cancel sets the engine's stop event (keeping the best result so far).
The worker only mutates the plain calc models and emits no signals from the
calc path; the recompute + plot redraw happen on the GUI thread in the
finished handler.

A live convergence plot (best Rp vs evaluations) fills the Progress group,
fed by the same per-evaluation progress signal but redrawn on a throttle timer
(so thousands of evaluations never flood the GUI). The parameter-landscape /
brute-force view is intentionally NOT ported (see calculations/refinement.py).
"""

from __future__ import annotations

import random
import threading
from typing import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QDoubleSpinBox, QFormLayout, QHeaderView, QMessageBox,
    QSpinBox, QTableWidgetItem, QWidget,
)

from mudlab.calculations.refinement import REFINE_METHODS, refine_mixture
from mudlab.ui.ui_refinement import Ui_RefinementDialog


class _RefineWorker(QObject):
    """Runs one refinement on a background thread. Only touches the plain calc
    models (thread-safe) and never emits a Qt signal from the calc path itself;
    the recompute + redraw happen on the main thread in the finished handler.
    `refine_mixture` restores the model on error before re-raising, so `failed`
    leaves the mixture clean."""

    progress = Signal(int, float)   # (n_evaluations, best_residual)
    finished = Signal(object)       # the Refiner
    failed = Signal(str)

    def __init__(self, mixture, method_index, options, stop_event):
        super().__init__()
        self._mixture = mixture
        self._method_index = method_index
        self._options = options
        self._stop_event = stop_event

    def run(self) -> None:
        try:
            refiner = refine_mixture(
                self._mixture, self._method_index, self._options,
                stop=self._stop_event.is_set,
                on_progress=lambda n, best: self.progress.emit(n, best),
            )
        except Exception as exc:  # noqa: BLE001 - reported via `failed`
            self.failed.emit(str(exc))
        else:
            self.finished.emit(refiner)

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
        # Background-refinement state (Phase C).
        self._thread: QThread | None = None
        self._worker: _RefineWorker | None = None
        self._stop_event: threading.Event | None = None
        self._cancelled = False
        self._setup_progress_plot()

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
        self.ui.btn_cancel.clicked.connect(self._on_cancel)
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
    # Live convergence plot (best Rp vs evaluations)
    # ------------------------------------------------------------------
    def _setup_progress_plot(self) -> None:
        """Embed the convergence plot in the Progress group. Redraws are throttled
        by a timer so a run of thousands of evaluations never floods the GUI - the
        per-eval progress signal only appends a point; the timer redraws at most a
        few times a second, with a final redraw when the run ends."""
        self._prog_fig = Figure(figsize=(4.0, 1.8))
        self._prog_fig.set_layout_engine("tight")
        self._prog_canvas = FigureCanvasQTAgg(self._prog_fig)
        self._prog_canvas.setMinimumHeight(140)
        self.ui.progressLayout.addWidget(self._prog_canvas)
        self._prog_ax = self._prog_fig.add_subplot(111)
        self._prog_evals: list[int] = []
        self._prog_best: list[float] = []
        self._prog_dirty = False
        self._prog_timer = QTimer(self)
        self._prog_timer.setInterval(150)  # ms - the redraw throttle
        self._prog_timer.timeout.connect(self._redraw_progress)
        self._draw_progress()

    def _draw_progress(self) -> None:
        ax = self._prog_ax
        ax.clear()
        ax.set_xlabel("evaluations", fontsize=8)
        ax.set_ylabel("best Rp (%)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)
        if self._prog_evals:
            ax.plot(self._prog_evals, self._prog_best,
                    color="#1971C2", linewidth=1.3)
        self._prog_canvas.draw_idle()

    def _redraw_progress(self, force: bool = False) -> None:
        if self._prog_dirty or force:
            self._prog_dirty = False
            self._draw_progress()

    def _start_progress(self) -> None:
        self._prog_evals.clear()
        self._prog_best.clear()
        self._prog_dirty = False
        self._draw_progress()
        self._prog_timer.start()

    def _finish_progress(self) -> None:
        self._prog_timer.stop()
        self._redraw_progress(force=True)

    # ------------------------------------------------------------------
    # Running the refinement on a background thread (Phase C)
    # ------------------------------------------------------------------
    def _on_refine(self) -> None:
        if self._mixture is None or self._thread is not None:
            return  # already running
        method_index = int(self.ui.cmb_method.currentData())
        options = self._options()  # read the form on the main thread

        self._cancelled = False
        self._stop_event = threading.Event()
        self._worker = _RefineWorker(self._mixture, method_index, options, self._stop_event)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)

        self._set_running(True)
        self.ui.lbl_status.setText("Refining...")
        self._start_progress()
        self._thread.start()

    def _on_cancel(self) -> None:
        if self._stop_event is not None:
            self._cancelled = True
            self._stop_event.set()  # the engine aborts at the next trial
            self.ui.btn_cancel.setEnabled(False)
            self.ui.lbl_status.setText("Cancelling - keeping the best so far...")

    def _on_progress(self, n_evals: int, best_residual: float) -> None:
        self.ui.lbl_status.setText(
            "Refining... %d evaluations, best Rp = %.3f %%" % (n_evals, best_residual)
        )
        # Append only - the throttle timer does the (expensive) redraw.
        self._prog_evals.append(n_evals)
        self._prog_best.append(best_residual)
        self._prog_dirty = True

    def _on_finished(self, refiner) -> None:
        self._teardown_thread()
        self._finish_progress()
        # Back on the GUI thread: recompute (this emits data_changed -> the plot
        # redraws) and show the outcome.
        self._mixture.calculate()
        self._refiner = refiner
        self._show_results(refiner)
        self._refresh_values()
        self._set_apply_enabled(True)
        self._set_running(False)
        self.ui.lbl_status.setText(
            "Cancelled - kept best (Rp = %.3f %%)." % refiner.best_residual
            if self._cancelled else "Done - best Rp = %.3f %%." % refiner.best_residual
        )
        if self._on_applied is not None:
            self._on_applied()

    def _on_failed(self, message: str) -> None:
        self._teardown_thread()
        self._finish_progress()
        self._set_running(False)
        self.ui.lbl_status.setText("Refinement failed.")
        QMessageBox.warning(
            self, "Refinement failed",
            "The refinement could not complete:\n\n%s" % message,
        )

    def _teardown_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._worker.deleteLater()
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self._stop_event = None

    def _set_running(self, running: bool) -> None:
        """Lock the editing controls while a refinement runs; only Cancel stays
        active. Cancel is disabled otherwise."""
        for control in (
            self.ui.tbl_refinables, self.ui.cmb_method, self.ui.btn_refine,
            self.ui.btn_auto_restrict, self.ui.btn_randomize, self.ui.buttonBox,
            self.ui.btn_apply_initial, self.ui.btn_apply_best, self.ui.btn_apply_last,
        ):
            control.setEnabled(not running)
        for spin, _kind in self._option_spins.values():
            spin.setEnabled(not running)
        self.ui.btn_cancel.setEnabled(running)
        if not running:
            self._set_apply_enabled(self._refiner is not None)

    def closeEvent(self, event) -> None:
        # If a refinement is running, cancel and wait for it before closing so
        # the worker never outlives the dialog / keeps mutating the model.
        if self._thread is not None:
            if self._stop_event is not None:
                self._stop_event.set()
            self._thread.quit()
            self._thread.wait()
            self._teardown_thread()
        self._prog_timer.stop()
        super().closeEvent(event)

    def _on_apply(self, which: str) -> None:
        if self._refiner is None or self._mixture is None or self._thread is not None:
            return
        getattr(self._refiner, "apply_" + which)()
        self._mixture.calculate()
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
        # GoF of the best solution: this runs in the finished handler, after
        # the model was left at best + recomputed, so the specimens' calculated
        # patterns reflect it. Mean over the mixture's specimens (num_params=0,
        # matching SpecimenStatistics), like the mean-Rp residual.
        gof = self._compute_gof()
        self.ui.lbl_gof.setText("-" if gof is None else "%.4f" % gof)

    def _compute_gof(self) -> float | None:
        from mudlab.calculations import GoF

        if self._mixture is None:
            return None
        values = []
        for specimen in self._mixture.specimens:
            if specimen is None or not (
                specimen.has_experimental_data and specimen.has_calculated_data
            ):
                continue
            exp = specimen.experimental_pattern[1]
            calc = specimen.calculated_pattern[1]
            if exp.size == calc.size and exp.size > 0:
                values.append(float(GoF(exp, calc)))
        return sum(values) / len(values) if values else None

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
