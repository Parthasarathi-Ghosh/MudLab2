"""Refinement window. Design: ui/refinement.ui.

Ported from the GTK RefinementView/RefinerView (refinement/views/glade/
refinement.glade + refine_results.glade). Opened from the Edit Mixtures
Refine button for the current mixture: a foldable tree of the mixture's
refinable structural parameters (editable value/min/max + a Refine toggle), a
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
import time
from typing import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFontDatabase
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDoubleSpinBox, QGridLayout, QHeaderView,
    QLabel, QMenu, QMessageBox, QSpinBox, QStyledItemDelegate,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QWidget,
)

from mudlab.calculations.refinement import (
    BASINHOPPING_LOCAL_MAXFUN, REFINE_METHODS, refine_mixture,
)
from mudlab.calculations.mixture import per_specimen_residuals_from_patterns
from mudlab.calculations.validation import validation_report_lines
from mudlab.ui.ui_refinement import Ui_RefinementDialog


class _RefineWorker(QObject):
    """Runs one refinement on a background thread. Only touches the plain calc
    models (thread-safe) and never emits a Qt signal from the calc path itself;
    the recompute + redraw happen on the main thread in the finished handler.
    `refine_mixture` restores the model on error before re-raising, so `failed`
    leaves the mixture clean."""

    # (n_evaluations, best_residual, per-specimen [(name, Rp), ...] of the best)
    progress = Signal(int, float, object)
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
                on_progress=lambda n, best, parts: self.progress.emit(
                    n, best, list(parts or [])),
            )
        except Exception as exc:  # noqa: BLE001 - reported via `failed`
            self.failed.emit(str(exc))
        else:
            self.finished.emit(refiner)

_COL_NAME, _COL_VALUE, _COL_MIN, _COL_MAX, _COL_REFINE = range(5)
# The four numeric columns, not the names, set the floor on how narrow the
# parameters frame can be. "Refine" spelled out costs ~50 px over "Ref.", and
# that is a deliberate trade: the column heading has to be readable.
_HEADERS = ["Parameter", "Value", "Min", "Max", "Refine"]
_NUM_COL_WIDTH = 72   # Value / Min / Max: enough for "%.4f" of a 3-digit value

# Per-method OUTER-search options (name, label, default, min, max, kind). The
# inner fraction/scale/bg optimiser keeps its own fixed limits. Old sources:
# scipy_runs.py (L-BFGS-B / Basin Hopping); indices match REFINE_METHODS.
# Labels are kept SHORT so two (label, spinbox) pairs fit side by side in the
# middle frame; _OPTION_TOOLTIPS carries the full meaning.
_METHOD_OPTIONS = {
    0: [
        ("maxfun", "Function calls", 500, 1, 1_000_000, int),
        ("maxiter", "Iterations", 150, 1, 1_000_000, int),
    ],
    1: [
        ("niter", "Iterations", 100, 1, 100_000, int),
        ("local_maxfun", "Calls per run", BASINHOPPING_LOCAL_MAXFUN,
         1, 1_000_000, int),
        ("T", "Temperature", 1.0, 0.0, 10_000.0, float),
        ("stepsize", "Step size", 0.5, 0.0, 1_000.0, float),
    ],
}

# Cell tints for the warning line's culprits. A soft wash rather than a strong
# colour: the tree already uses alternating row colours, and these have to read
# as "look here", not as an error state.
_WARN_BRUSH = QBrush(QColor("#FFE8CC"))   # cannot be refined as set up
_HAND_BRUSH = QBrush(QColor("#E7F5FF"))   # value typed in by hand
_NO_BRUSH = QBrush()                      # default: clears the tint
_WARNING_STYLE = "color: #C2410C;"
_MAX_NAMED = 2   # names listed in a warning before "and N more"

# Per-specimen progress curves: a qualitative palette that stays distinguishable
# against the mean's blue, and the point past which a legend costs more plot
# than it explains (the report names every specimen regardless).
_SPECIMEN_COLORS = ["#E8590C", "#2F9E44", "#9C36B5", "#0B7285",
                    "#C2255C", "#5C940D"]
_MAX_LEGEND_SERIES = 5
_MAX_LEGEND_NAME = 14


def _short_name(name: str) -> str:
    return name if len(name) <= _MAX_LEGEND_NAME else name[:_MAX_LEGEND_NAME - 1] + "…"


_WARNING_TOOLTIP = (
    "Problems with the current set-up, and nothing when there are none.\n\n"
    "• Min not below Max: the refiner silently drops such a parameter, so "
    "it stays ticked but never moves.\n"
    "• Outside Min/Max: the search clips the start value into the range, "
    "so the run does not begin at the value shown.\n"
    "• Set by hand: a typed Value is written straight into the model. "
    "Phases are shared between mixtures, so it can move another mixture too, "
    "and there is no undo - refine, or keep a solution, to overwrite it.\n\n"
    "The affected cells are tinted in the tree; hover one for its own detail."
)


def _plural(count: int, noun: str, singular: str = "", plural: str = "") -> str:
    """"1 value was" / "3 values were" - the warning line reads as a sentence."""
    word = noun if count == 1 else noun + "s"
    verb = (singular if count == 1 else plural) if singular else ""
    return "%d %s%s" % (count, word, " " + verb if verb else "")


def _value_tooltip(ref, outside: bool, hand: bool) -> str:
    parts = []
    if outside:
        parts.append("Outside Min/Max (%.4f to %.4f): a refinement starts from "
                     "the nearest bound, not this value."
                     % (ref.minimum, ref.maximum))
    if hand:
        parts.append("Set by hand - written straight into the model.")
    return "\n".join(parts)


_OPTION_TOOLTIPS = {
    "maxfun": "Maximum number of objective-function evaluations.",
    "maxiter": "Maximum number of solver iterations.",
    "niter": "Number of basin-hopping iterations (random restarts).",
    "local_maxfun": ("Evaluations allowed per local minimisation. Uncapped, "
                     "scipy allows 15000 per run - so 100 iterations could mean "
                     "over a million evaluations. Raise it if a local minimum "
                     "genuinely needs more work."),
    "T": "Basin-hopping temperature: how readily a worse solution is accepted.",
    "stepsize": "Size of the random displacement between basin-hopping steps.",
}


class _EditableCellDelegate(QStyledItemDelegate):
    """Only the Value, Min and Max cells may be edited - never Parameter.

    A QTreeWidgetItem's ItemIsEditable flag applies to EVERY column, so without
    this the Parameter cell opens an editor too, and a typed name would stay on
    screen while the model kept its own. A cell that lies about the model is
    worse than one that is read-only. (The flat table this replaced set
    editability per CELL, which is why it never had the problem.)

    Value was read-only for the same reason until `_on_item_changed` learned to
    write it back; the old GTK app always allowed editing it, and setting a
    parameter by hand before refining is a real workflow."""

    def createEditor(self, parent, option, index):
        if index.column() not in (_COL_VALUE, _COL_MIN, _COL_MAX):
            return None
        return super().createEditor(parent, option, index)


class RefinementDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, mixture=None,
                 on_applied: Callable[[], None] | None = None) -> None:
        super().__init__(parent)
        # Free the dialog when it closes instead of leaving it parented to the
        # mixture editor: it is opened with exec() from a local variable, so
        # every Refine click otherwise left one hidden dialog (with its
        # refinables table and progress plot) alive for the editor's lifetime.
        # Safe here because (a) the caller does not touch the dialog after
        # exec() returns, and (b) `done()` cancels and WAITS for the worker
        # thread, so the QThread parented to this dialog is always torn down
        # before the deletion. That teardown MUST stay in done() - disabling
        # buttonBox does not stop Esc, and deleting the dialog with a live
        # QThread aborts the process.
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.ui = Ui_RefinementDialog()
        self.ui.setupUi(self)

        self._mixture = mixture
        self._on_applied = on_applied
        self._refinables: list = []
        self._refiner = None
        self._updating = False
        self._option_spins: dict = {}
        # The per-method options sit in a GRID of (label, spinbox) pairs, two
        # pairs per row: the common case (max function calls + max iterations)
        # then reads as one side-by-side row in the narrow middle frame, and a
        # method with more options (Basin Hopping has three) wraps instead of
        # squeezing everything into one line.
        self._options_form = QGridLayout()
        self._options_form.setContentsMargins(0, 0, 0, 0)
        self.ui.optionsLayout.addLayout(self._options_form)
        # Background-refinement state (Phase C).
        self._thread: QThread | None = None
        self._worker: _RefineWorker | None = None
        self._stop_event: threading.Event | None = None
        self._cancelled = False
        self._refine_started: float | None = None
        self._elapsed: float | None = None
        self._applied: str | None = None      # "initial" / "best" / "last"
        self._applied_by_user = False         # False = left there by the run
        # ids of the Refinables whose Value the user typed in by hand since the
        # model last came from a refinement. Cleared whenever the model's values
        # are written wholesale again (a new run, or keeping a solution), since
        # the hand-set numbers are gone at that point.
        self._hand_edited: set = set()
        self._setup_progress_plot()
        # The report is fixed-pitch: it is a column-aligned text table.
        self.ui.txt_report.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.ui.lbl_param_warning.setStyleSheet(_WARNING_STYLE)
        self.ui.lbl_param_warning.setToolTip(_WARNING_TOOLTIP)
        self.ui.lbl_param_warning.setVisible(False)

        # {id(QTreeWidgetItem): Refinable} for the parameter LEAVES; a group row
        # is absent from it, which is how edits on a group are ignored.
        self._items: dict = {}
        tree = self.ui.tree_refinables
        tree.setColumnCount(len(_HEADERS))
        tree.setHeaderLabels(_HEADERS)
        tree.setRootIsDecorated(True)          # the fold arrows
        # Tighter than Qt's ~20 px default: the tree is three levels deep
        # (phase / component / parameter), so the default indent ate width the
        # name column needs.
        tree.setIndentation(12)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._on_tree_menu)
        tree.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        tree.setItemDelegate(_EditableCellDelegate(tree))
        header = tree.header()
        # The name column is the stretching one; without this Qt ALSO stretches
        # the last section, and the two together push the header past the
        # viewport - which shows up as a permanent horizontal scrollbar.
        header.setStretchLastSection(False)
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        # Fixed-but-draggable numeric columns rather than ResizeToContents: the
        # latter sized them to their widest value (a 200.0000 CSDS mean pushed
        # Max to ~102 px) and left the name column whatever was over.
        for col in (_COL_VALUE, _COL_MIN, _COL_MAX):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(col, _NUM_COL_WIDTH)
        header.setSectionResizeMode(_COL_REFINE, QHeaderView.ResizeMode.ResizeToContents)

        # Method combo: only the two convergent SciPy methods.
        for index, (name, _fn) in sorted(REFINE_METHODS.items()):
            self.ui.cmb_method.addItem(name, index)
        self._select_stored_method()
        self._build_options_form(int(self.ui.cmb_method.currentData()))

        tree.itemChanged.connect(self._on_item_changed)
        self.ui.cmb_method.currentIndexChanged.connect(self._on_method_changed)
        self.ui.btn_refine.clicked.connect(self._on_refine)
        self.ui.btn_cancel.clicked.connect(self._on_cancel)
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
        """Build the refinables TREE: a foldable group per phase (and per
        component below it), with one leaf per parameter showing only its own
        title. Ported from the old app's refinables GtkTreeView, which did the
        same - it is what keeps the name column narrow, since the full path
        ("Illite | Illite | d001") is carried by the group rows instead of being
        repeated on every row. Group rows carry no value/min/max/refine cells,
        exactly as the old view hid them on non-refinable nodes."""
        tree = self.ui.tree_refinables
        self._updating = True
        try:
            tree.clear()
            self._items = {}
            self._hand_edited = set()
            self._refinables = (
                self._mixture.refinables() if self._mixture is not None else []
            )
            # Keyed by `group_key` (stable ids), NOT by the displayed names:
            # two phases - or two components of one phase - may share a name,
            # and keying by name merged their parameters into a single branch
            # with no way to tell which owned which.
            groups: dict = {}
            for ref in self._refinables:
                parent = None
                path: tuple = ()
                for level, name in enumerate(ref.group):
                    path += (ref.group_key[level]
                             if level < len(ref.group_key) else name,)
                    node = groups.get(path)
                    if node is None:
                        node = (QTreeWidgetItem(tree, [name]) if parent is None
                                else QTreeWidgetItem(parent, [name]))
                        node.setFlags(Qt.ItemFlag.ItemIsEnabled)
                        node.setFirstColumnSpanned(False)
                        groups[path] = node
                    parent = node
                item = (QTreeWidgetItem(parent, [ref.title]) if parent is not None
                        else QTreeWidgetItem(tree, [ref.title]))
                item.setToolTip(_COL_NAME, ref.label)
                # ItemIsUserCheckable is what actually DRAWS (and enables) the
                # Refine box; editable covers the Min/Max cells.
                item.setFlags(Qt.ItemFlag.ItemIsEnabled
                              | Qt.ItemFlag.ItemIsEditable
                              | Qt.ItemFlag.ItemIsUserCheckable)
                self._items[id(item)] = ref
                self._fill_item(item, ref)
            # Opens FOLDED: a real project has dozens of parameters across
            # several phases, and the phase names alone are the useful overview.
            # Expand all / Fold all live on the tree's right-click menu.
            tree.collapseAll()
        finally:
            self._updating = False
        self._update_selected_count()

    def _effective_parameters(self) -> int:
        """How many parameters the refiner will ACTUALLY vary: flagged, with a
        non-degenerate range. `Refiner.__init__` applies exactly this filter, so
        a ticked parameter whose Min >= Max is counted out here too - which is
        what makes that otherwise-silent skip visible."""
        return sum(1 for ref in self._refinables
                   if ref.refine and ref.minimum < ref.maximum)

    def _update_budget(self) -> None:
        """Describe the work this run may do - WITHOUT inventing a total.

        An earlier version showed "Up to N evaluations" from
        min(maxfun, maxiter x (n+1)). Measuring proved that wrong: scipy's
        maxfun / maxiter count its OWN solver steps, not model evaluations, and
        a step costs a gradient (about n+1 evaluations) plus an unbounded line
        search - maxiter=3 produced 28 model evaluations against a predicted 9.
        Basin Hopping is looser still: its per-run cap barely binds (cap 200
        gave 89 evaluations where UNCAPPED gave 71), because a local run usually
        converges long before the cap. So this states only what is true - the
        parameter count, which is exact, and each method's own limits verbatim."""
        method = int(self.ui.cmb_method.currentData() or 0)
        options = self._options()
        n = self._effective_parameters()
        if n == 0:
            self.ui.lbl_budget.setText(
                "No parameters selected - Refine only re-fits "
                "fractions / scales / background.")
            return
        params = "%d parameter%s" % (n, "" if n == 1 else "s")
        if method == 0:
            self.ui.lbl_budget.setText(
                "%s; stops at %d solver steps / %d iterations, each costing "
                "about %d model evaluations."
                % (params, int(options.get("maxfun", 500)),
                   int(options.get("maxiter", 150)), n + 1))
        else:
            self.ui.lbl_budget.setText(
                "%s; %d local runs, each stopping at %d solver steps. Much "
                "slower than L-BFGS-B."
                % (params, int(options.get("niter", 100)) + 1,
                   int(options.get("local_maxfun", BASINHOPPING_LOCAL_MAXFUN))))

    def _update_selected_count(self) -> None:
        """"N of M selected" beside the instruction above the tree. With the
        tree folded by default, the flagged count is otherwise invisible - and
        it is exactly what decides how long a refinement will take."""
        total = len(self._refinables)
        selected = sum(1 for ref in self._refinables if ref.refine)
        self.ui.lbl_selected.setText("%d of %d selected" % (selected, total))
        self._update_budget()
        self._update_warning()

    # ------------------------------------------------------------------
    # Warning line (below the tree)
    # ------------------------------------------------------------------
    def _warning_state(self) -> tuple:
        """(degenerate, outside): ids of FLAGGED refinables the refiner will
        silently drop because Min is not below Max, and of those whose current
        value sits outside its own bounds (the search clips the start value into
        the range, so the typed number is not where the run begins).

        `Refiner.__init__` is the authority for both - it skips a degenerate
        range and clips the start value - and this mirrors it exactly."""
        degenerate, outside = set(), set()
        for ref in self._refinables:
            if not ref.refine:
                continue
            low, high = ref.minimum, ref.maximum
            if not (low < high):
                degenerate.add(id(ref))
            elif not (low <= ref.value <= high):
                outside.add(id(ref))
        return degenerate, outside

    def _name_list(self, ids: set) -> str:
        """Up to `_MAX_NAMED` parameter names, then "and N more"; a bare count
        would leave the user hunting through folded branches for the culprit."""
        titles = [ref.label for ref in self._refinables if id(ref) in ids]
        shown = titles[:_MAX_NAMED]
        if len(titles) > _MAX_NAMED:
            shown.append("and %d more" % (len(titles) - _MAX_NAMED))
        return ", ".join(shown)

    def _update_warning(self) -> None:
        """Show what is wrong with the current selection, and nothing when
        nothing is - the label hides itself, so an untroubled dialog does not
        carry a permanent empty warning strip."""
        degenerate, outside = self._warning_state()
        self._mark_problem_rows(degenerate, outside)
        # Kept SHORT deliberately. Spelled out ("...the run will start from the
        # nearest bound, not the shown value"), three messages wrapped to ten
        # lines and took 152 px off a 415 px tree. The reasoning lives in the
        # label's tooltip and in each tinted cell's own tooltip; the line itself
        # only has to say what is wrong and which parameter it is.
        messages = []
        if degenerate:
            messages.append("Min not below Max, so not refined: %s."
                            % self._name_list(degenerate))
        if outside:
            messages.append("Outside Min/Max, so refining starts at the "
                            "bound: %s." % self._name_list(outside))
        if self._hand_edited:
            messages.append("%s set by hand (direct model edit, no undo)."
                            % _plural(len(self._hand_edited), "value"))
        label = self.ui.lbl_param_warning
        # One message per line: they are independent problems, and running them
        # together made a wrapped paragraph nobody would read.
        label.setText("\n".join(messages))
        label.setVisible(bool(messages))

    def _mark_problem_rows(self, degenerate: set, outside: set) -> None:
        """Tint the offending cells so the warning's names can be found in the
        tree. Cleared on every pass, so a fixed row loses its tint - the marks
        describe the CURRENT state, never a stale one."""
        self._updating = True
        try:
            for item, ref in self._leaf_items():
                bad_bounds = id(ref) in degenerate
                bad_value = id(ref) in outside
                hand = id(ref) in self._hand_edited
                for col, flagged in ((_COL_MIN, bad_bounds),
                                     (_COL_MAX, bad_bounds),
                                     (_COL_VALUE, bad_value)):
                    item.setBackground(col, _WARN_BRUSH if flagged else _NO_BRUSH)
                if not bad_value:
                    item.setBackground(_COL_VALUE,
                                       _HAND_BRUSH if hand else _NO_BRUSH)
                item.setToolTip(_COL_VALUE, _value_tooltip(ref, bad_value, hand))
        finally:
            self._updating = False

    def _on_tree_menu(self, pos) -> None:
        tree = self.ui.tree_refinables
        self._tree_menu().exec(tree.viewport().mapToGlobal(pos))

    def _tree_menu(self) -> QMenu:
        """Build the parameters tree's right-click menu. Kept separate from
        showing it so it can be inspected without entering a modal loop.

        Folding is always available; the four model-touching entries are greyed
        while a refinement runs, the way the Auto-restrict / Randomize buttons
        they replaced used to be."""
        tree = self.ui.tree_refinables
        idle = self._thread is None
        menu = QMenu(self)
        menu.addAction("Expand all", tree.expandAll)
        menu.addAction("Fold all", tree.collapseAll)
        menu.addSeparator()
        select = menu.addAction("Select all", lambda: self._set_all_refine(True))
        unselect = menu.addAction("Unselect all", lambda: self._set_all_refine(False))
        menu.addSeparator()
        restrict = menu.addAction("Auto restrict", self._on_auto_restrict)
        restrict.setToolTip(
            "Set Min/Max to +/-20% of each flagged parameter's current value.")
        randomise = menu.addAction("Randomise", self._on_randomize)
        randomise.setToolTip("Randomize each flagged parameter within its Min/Max.")
        for action in (select, unselect, restrict, randomise):
            action.setEnabled(idle)
        return menu

    def _set_all_refine(self, refine: bool) -> None:
        """Tick / untick the Refine box on every parameter, and UNFOLD so the
        result is visible - selecting everything behind collapsed branches would
        otherwise look like nothing happened."""
        self._updating = True
        try:
            for item, ref in self._leaf_items():
                ref.set_ref_info(refine=refine)
                item.setCheckState(
                    _COL_REFINE,
                    Qt.CheckState.Checked if refine else Qt.CheckState.Unchecked)
        finally:
            self._updating = False
        self.ui.tree_refinables.expandAll()
        self._update_selected_count()

    def _fill_item(self, item, ref) -> None:
        item.setText(_COL_VALUE, "%.4f" % ref.value)
        item.setText(_COL_MIN, "%.4f" % ref.minimum)
        item.setText(_COL_MAX, "%.4f" % ref.maximum)
        item.setCheckState(_COL_REFINE,
                           Qt.CheckState.Checked if ref.refine
                           else Qt.CheckState.Unchecked)

    def _leaf_items(self):
        """(item, refinable) for every parameter leaf, groups excluded."""
        walker = QTreeWidgetItemIterator(self.ui.tree_refinables)
        while walker.value():
            item = walker.value()
            ref = self._items.get(id(item))
            if ref is not None:
                yield item, ref
            walker += 1

    def _refresh_values(self) -> None:
        """After a refine/apply the model values changed; refresh Value (and
        Min/Max/refine, which auto-restrict/randomize may have touched)."""
        self._updating = True
        try:
            for item, ref in self._leaf_items():
                self._fill_item(item, ref)
        finally:
            self._updating = False
        self._update_selected_count()

    # ------------------------------------------------------------------
    # Editing the tree
    # ------------------------------------------------------------------
    def _on_item_changed(self, item, col: int) -> None:
        if self._updating:
            return
        ref = self._items.get(id(item))
        if ref is None:
            return  # a group row: nothing to edit
        if col == _COL_REFINE:
            ref.set_ref_info(refine=item.checkState(_COL_REFINE) == Qt.CheckState.Checked)
            self._update_selected_count()
        elif col == _COL_VALUE:
            self._on_value_edited(item, ref)
        elif col in (_COL_MIN, _COL_MAX):
            try:
                value = float(item.text(col))
            except ValueError:
                self._revert_cell(item, col, ref)
                return
            if col == _COL_MIN:
                ref.set_ref_info(minimum=value)
            else:
                ref.set_ref_info(maximum=value)
            # A bound decides whether the parameter can be refined at all, so
            # the count, the budget and the Min >= Max warning all move with it.
            self._update_selected_count()

    def _revert_cell(self, item, col: int, ref) -> None:
        """Put the model's own number back in a cell after unparseable input."""
        current = {_COL_VALUE: ref.value, _COL_MIN: ref.minimum,
                   _COL_MAX: ref.maximum}[col]
        self._updating = True
        try:
            item.setText(col, "%.4f" % current)
        finally:
            self._updating = False

    def _on_value_edited(self, item, ref) -> None:
        """Write a hand-typed Value straight into the live model.

        The old GTK app allowed this and MudLab2 did not; setting a parameter by
        hand (then refining from there, or just seeing its effect on the pattern)
        is a real workflow. It is a DIRECT model write with no undo, and phases
        are shared objects, so it can move another mixture too - hence the
        warning line, which names the count and survives until the values are
        written wholesale again. The value is deliberately NOT clamped to
        Min/Max: those are search bounds, not validity limits, and refusing the
        number would be worse than reporting that a run will start from the
        clipped bound (which `_warnings` does)."""
        try:
            value = float(item.text(_COL_VALUE))
        except ValueError:
            self._revert_cell(item, _COL_VALUE, ref)
            return
        if value == ref.value:
            self._revert_cell(item, _COL_VALUE, ref)   # reformat only
            return
        ref.value = value
        self._hand_edited.add(id(ref))
        if self._mixture is not None:
            self._mixture.calculate()
        # The setter may not store the number verbatim (an atom relation
        # re-applies itself), so redisplay what the model actually holds.
        self._refresh_values()
        if self._refiner is not None:
            # The results now describe a model the user has changed by hand:
            # refresh the GoF from the new patterns and rewrite the report,
            # rather than leaving either describing the pre-edit state.
            self._show_results(self._refiner)
            self._write_report()
        if self._on_applied is not None:
            self._on_applied()

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
            # QGridLayout has no removeRow: drop every item and its widget.
            while self._options_form.count():
                item = self._options_form.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
            self._option_spins = {}
            stored = self._stored_options(method_index)
            pairs_per_row = 2
            for position, (name, label, default, lo, hi, kind) in enumerate(
                _METHOD_OPTIONS.get(method_index, [])
            ):
                spin = QSpinBox() if kind is int else QDoubleSpinBox()
                if kind is float:
                    spin.setDecimals(3)
                spin.setRange(lo, hi)
                spin.setValue(kind(stored.get(name, default)))
                spin.valueChanged.connect(self._save_options)
                tip = _OPTION_TOOLTIPS.get(name, "")
                spin.setToolTip(tip)
                caption = QLabel(label)
                caption.setToolTip(tip)
                row, pair = divmod(position, pairs_per_row)
                self._options_form.addWidget(caption, row, pair * 2)
                self._options_form.addWidget(spin, row, pair * 2 + 1)
                self._option_spins[name] = (spin, kind)
            # Let the spin columns take the slack, not the labels.
            for pair in range(pairs_per_row):
                self._options_form.setColumnStretch(pair * 2, 0)
                self._options_form.setColumnStretch(pair * 2 + 1, 1)
        finally:
            self._updating = False
        self._update_budget()

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
        self._update_budget()

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
                self._hand_edited.discard(id(ref))   # overwritten
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
        # Keep figsize modest: a FigureCanvas reports figsize x dpi as its
        # sizeHint, and at 4.0in that was ~560 px, which let the middle frame
        # hog the three-frame row and squeezed the parameter table into a
        # horizontal scrollbar. The canvas expands to fill whatever it gets.
        self._prog_fig = Figure(figsize=(2.2, 1.7))
        self._prog_fig.set_layout_engine("tight")
        self._prog_canvas = FigureCanvasQTAgg(self._prog_fig)
        self._prog_canvas.setMinimumHeight(140)
        self.ui.progressLayout.addWidget(self._prog_canvas)
        self._prog_ax = self._prog_fig.add_subplot(111)
        self._prog_evals: list[int] = []
        self._prog_best: list[float] = []
        # {specimen name: (evaluations, Rp)} - the per-specimen curves behind
        # the mean. Appended to per progress point (never rebuilt from a stored
        # history), so the throttled redraw stays O(points) rather than
        # regrouping thousands of breakdowns on every tick.
        self._prog_series: dict = {}
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
        # The per-specimen curves go UNDER the mean, thin and lighter: the mean
        # is the number every other readout quotes, so it has to stay the one
        # the eye follows. The point of the thin lines is the SPREAD - a run
        # that improves the mean by pulling one specimen down while pushing
        # another up is invisible in a single curve.
        for position, (name, (evals, values)) in enumerate(
            sorted(self._prog_series.items())
        ):
            if not evals:
                continue
            ax.plot(evals, values, linewidth=0.8, alpha=0.75,
                    color=_SPECIMEN_COLORS[position % len(_SPECIMEN_COLORS)],
                    label=_short_name(name))
        if self._prog_evals:
            ax.plot(self._prog_evals, self._prog_best,
                    color="#1971C2", linewidth=1.6, label="mean", zorder=3)
        # A legend only where it fits: past a handful of specimens it would
        # cover the curves it is meant to explain, and the report's per-specimen
        # table names them all anyway. It sits ABOVE the axes - inside, it landed
        # on the worst-fitting specimen's curve (the curves fill the plot by
        # construction, since the axes autoscale to them), and "best" placement
        # would re-solve an overlap search on every throttled redraw.
        if 0 < len(self._prog_series) <= _MAX_LEGEND_SERIES:
            ax.legend(fontsize=6, frameon=False, labelspacing=0.2,
                      loc="lower center", bbox_to_anchor=(0.5, 1.0),
                      borderaxespad=0.0, ncol=len(self._prog_series) + 1,
                      handlelength=1.2, columnspacing=1.0, handletextpad=0.4)
        self._prog_canvas.draw_idle()

    def _redraw_progress(self, force: bool = False) -> None:
        if self._prog_dirty or force:
            self._prog_dirty = False
            self._draw_progress()

    def _start_progress(self) -> None:
        self._prog_evals.clear()
        self._prog_best.clear()
        self._prog_series.clear()
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
        self._applied = None
        self._applied_by_user = False
        # The run starts FROM any hand-set values and then writes its own, so
        # they stop being hand-set the moment it begins.
        self._hand_edited = set()
        self._elapsed = None
        self._refine_started = time.monotonic()
        self.ui.txt_report.clear()   # the previous run's report is now stale
        self._start_progress()
        self._thread.start()

    def _on_cancel(self) -> None:
        if self._stop_event is not None:
            self._cancelled = True
            self._stop_event.set()  # the engine aborts at the next trial
            self.ui.btn_cancel.setEnabled(False)
            self.ui.lbl_status.setText("Cancelling - keeping the best so far...")

    def _on_progress(self, n_evals: int, best_residual: float,
                     parts=None) -> None:
        self.ui.lbl_status.setText(
            "Refining... %d evaluations, best Rp = %.3f %%" % (n_evals, best_residual)
        )
        # Append only - the throttle timer does the (expensive) redraw.
        self._prog_evals.append(n_evals)
        self._prog_best.append(best_residual)
        for name, value in parts or []:
            evals, values = self._prog_series.setdefault(name, ([], []))
            evals.append(n_evals)
            values.append(value)
        self._prog_dirty = True

    def _on_finished(self, refiner) -> None:
        self._teardown_thread()
        self._finish_progress()
        if self._refine_started is not None:
            self._elapsed = time.monotonic() - self._refine_started
        # Back on the GUI thread: recompute (this emits data_changed -> the plot
        # redraws) and show the outcome.
        self._mixture.calculate()
        self._refiner = refiner
        # `refine_mixture` leaves the model AT THE BEST solution (normally and
        # on cancel), so the report must say "best" - not "nothing applied" -
        # and the validation section applies to that state, which is also when
        # the old app ran it (it called apply_best_solution() on finish).
        self._applied = "best"
        self._applied_by_user = False
        self._show_results(refiner)
        self._refresh_values()
        self._set_apply_enabled(True)
        self._set_running(False)
        self.ui.lbl_status.setText(
            "Cancelled - kept best (Rp = %.3f %%)." % refiner.best_residual
            if self._cancelled else "Done - best Rp = %.3f %%." % refiner.best_residual
        )
        self._write_report()
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
        active. Cancel is disabled otherwise. (Auto-restrict / Randomise moved to
        the tree's right-click menu, which greys them itself while running - and
        disabling the tree blocks the menu anyway.)"""
        for control in (
            self.ui.tree_refinables, self.ui.cmb_method, self.ui.btn_refine,
            self.ui.buttonBox,
            self.ui.btn_apply_initial, self.ui.btn_apply_best, self.ui.btn_apply_last,
        ):
            control.setEnabled(not running)
        for spin, _kind in self._option_spins.values():
            spin.setEnabled(not running)
        self.ui.btn_cancel.setEnabled(running)
        if not running:
            self._set_apply_enabled(self._refiner is not None)

    def _abort_refinement(self) -> None:
        """Cancel a running refinement and WAIT for the worker, so it never
        outlives the dialog / keeps mutating the model. Idempotent."""
        if self._thread is not None:
            if self._stop_event is not None:
                self._stop_event.set()
            self._thread.quit()
            self._thread.wait()
            self._teardown_thread()
        self._prog_timer.stop()

    def done(self, result: int) -> None:
        # done() is the single funnel for OK / Cancel / Esc / close(), and with
        # WA_DeleteOnClose it takes the dialog - and the QThread parented to it -
        # with it. **Esc is NOT stopped by disabling buttonBox**, so a run really
        # can be dismissed mid-flight; without this teardown the QThread is
        # destroyed while still running and the process ABORTS. Tearing down here
        # (not only in closeEvent) covers every dismissal path.
        self._abort_refinement()
        super().done(result)

    def closeEvent(self, event) -> None:
        # The window-X path. QDialog::closeEvent routes through reject() -> done()
        # above, so this is belt-and-braces; _abort_refinement is idempotent.
        self._abort_refinement()
        super().closeEvent(event)

    def _on_apply(self, which: str) -> None:
        if self._refiner is None or self._mixture is None or self._thread is not None:
            return
        getattr(self._refiner, "apply_" + which)()
        self._hand_edited = set()   # the solution overwrote every hand-set value
        self._mixture.calculate()
        self._refresh_values()
        # Rewrite the report for the solution now in the model: its GoF is
        # recomputed from the freshly calculated patterns, so the report always
        # describes what is actually applied.
        self._applied = which
        self._applied_by_user = True
        self._write_report()
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

    def _per_specimen_residuals(self) -> list:
        """The per-specimen Rp behind the reported mean, or [] if unavailable."""
        if self._mixture is None:
            return []
        try:
            # The report is written straight after a recompute, so read the
            # patterns the specimens already hold rather than rebuilding every
            # phase's intensities - identical numbers, ~1300x cheaper (the full
            # version cost ~0.15 s on every report write).
            return per_specimen_residuals_from_patterns(self._mixture)
        except Exception:  # noqa: BLE001 - a report must never fail to render
            return []

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

    # ------------------------------------------------------------------
    # Detailed report (old RefinerController.populate_log -> txt_refine_log)
    # ------------------------------------------------------------------
    _REPORT_WIDTH = 64
    _MAX_PROGRESS_ROWS = 20

    def _write_report(self) -> None:
        """Fill the report box for the finished run.

        Written when the run ends and again whenever a solution is kept, so it
        always describes the solution currently in the model. Ported from the
        old app's `populate_log`, with two deliberate differences: the old
        per-ITERATION log becomes the per-EVALUATION progress series (MudLab2
        keeps `record_history` off so a long run cannot grow unbounded, and the
        series is thinned to `_MAX_PROGRESS_ROWS` rows), and an "Applied" line
        distinguishes the best solution the engine LEAVES in the model from one
        the user then keeps."""
        refiner = self._refiner
        if refiner is None:
            self.ui.txt_report.clear()
            return
        self.ui.txt_report.setPlainText("\n".join(self._report_lines(refiner)))

    def _report_lines(self, refiner) -> list:
        sep = "=" * self._REPORT_WIDTH
        lines = [sep, "  Refinement Summary", sep, ""]

        applied = {
            "initial": "Initial solution", "best": "Best solution",
            "last": "Last solution",
        }.get(self._applied, "-")
        if self._applied is not None:
            applied += ("  (kept)" if self._applied_by_user
                        else "  (left by the refinement)")
        # ...but a hand-edited Value moved the model away from that solution
        # afterwards, so saying only "Best solution" would describe a model that
        # is no longer there. The parameter table below still lists the
        # solution's own numbers; the tree shows what the model actually holds.
        if self._hand_edited:
            applied += "  + %s changed by hand since" % _plural(
                len(self._hand_edited), "value")
        lines.append("  Method:       %s" % self.ui.cmb_method.currentText())
        lines.append("  Parameters:   %d" % len(refiner.refinables))
        if self._elapsed is not None:
            mins, secs = divmod(int(self._elapsed), 60)
            lines.append("  Time elapsed: %d:%02d" % (mins, secs))
        if self._cancelled:
            lines.append("  Note:         cancelled by the user; best-so-far kept")
        lines.append("  Applied:      %s" % applied)
        lines.append("")

        lines.append("  Parameters:")
        lines.append("  %-28s %10s %10s %10s"
                     % ("Name", "Initial", "Best", "Last"))
        lines.append("  " + "-" * (self._REPORT_WIDTH - 2))
        initial, best, last = (refiner.initial_solution, refiner.best_solution,
                               refiner.last_solution)
        for i, ref in enumerate(refiner.refinables):
            name = ref.label
            if len(name) > 28:
                name = name[:27] + "…"
            lines.append("  %-28s %10.4f %10.4f %10.4f"
                         % (name, initial[i], best[i], last[i]))
        lines.append("")

        def rp(value):
            return "-" if value is None else "%.6f" % value

        gof = self._compute_gof()
        lines.append("  Residuals (Rp %):")
        lines.append("    Initial : %s" % rp(refiner.initial_residual))
        lines.append("    Best    : %s" % rp(refiner.best_residual))
        lines.append("    Last    : %s" % rp(refiner.last_residual))
        lines.append("    GoF     : %s  (as applied, P=%d)"
                     % ("-" if gof is None else "%.4f" % gof,
                        len(refiner.refinables)))
        lines.append("")

        # Every Rp above is the MEAN over the mixture's specimens, so a single
        # number hides one specimen fitting badly while the others carry the
        # average. These are the same values that mean was taken over.
        per_specimen = self._per_specimen_residuals()
        if per_specimen:
            lines.append("  Rp per specimen (as applied - the values above are")
            lines.append("  their mean):")
            width = min(34, max(len(name) for name, _rp in per_specimen))
            for name, value in per_specimen:
                shown = name if len(name) <= width else name[:width - 1] + "…"
                lines.append("    %-*s %8.3f" % (width, shown, value))
            lines.append("")

        rows = self._thinned_progress()
        if rows:
            lines.append("  Progress log (%d evaluations):" % self._prog_evals[-1])
            lines.append("  %12s  %14s" % ("Evaluations", "Best Rp"))
            lines.append("  " + "-" * 28)
            for n_evals, best_rp in rows:
                lines.append("  %12d  %14.6f" % (n_evals, best_rp))
            if len(self._prog_evals) > len(rows):
                lines.append("  (thinned from %d points)" % len(self._prog_evals))
            lines.append("")

        lines.append(sep)

        # Post-refinement validation of the state the applied solution left
        # behind - read-only, and only meaningful once a solution IS applied.
        if self._applied is not None and self._mixture is not None:
            lines.append("")
            lines.extend(validation_report_lines(self._mixture,
                                                 self._REPORT_WIDTH))
        return lines

    def _thinned_progress(self) -> list:
        """The progress series reduced to at most `_MAX_PROGRESS_ROWS` evenly
        spaced points (always keeping the first and last): a refinement can run
        to thousands of evaluations and the report is meant to be read."""
        points = list(zip(self._prog_evals, self._prog_best))
        if len(points) <= self._MAX_PROGRESS_ROWS:
            return points
        step = (len(points) - 1) / (self._MAX_PROGRESS_ROWS - 1)
        picked = [points[int(round(i * step))]
                  for i in range(self._MAX_PROGRESS_ROWS)]
        picked[-1] = points[-1]
        return picked

    def _set_apply_enabled(self, enabled: bool) -> None:
        for button in (self.ui.btn_apply_initial, self.ui.btn_apply_best,
                       self.ui.btn_apply_last):
            button.setEnabled(enabled)

