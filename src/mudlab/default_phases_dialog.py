"""Default phases dialog. Design: ui/default_phases.ui.

Records which shipped default phase each of the project's phases started as -
the mapping the composition comparison needs and cannot derive (see
`mudlab.default_state` for why: fresh uuids on every catalog build, no stored
origin, and freely renamed phases).

One row per structural phase that a mixture actually uses - a phase in no
mixture cannot affect any composition, so listing it is busywork (7 of 15 on a
real project); "Show unused phases" brings the rest back. Each row has a
drop-down of every available default:
the project's own imported reference phases first, then everything the shipped
catalog can build. "(not stated)" is always available and is the default, so a
partial mapping is a first-class outcome: the comparison then simply leaves
those phases at their current state rather than guessing.

**Import .phs...** adds a reference phase the shipped catalog does not have -
a clay the user built themselves. It is stored WITH THE PROJECT and never enters
`project.phases`, so it can be compared against without becoming part of the
model or turning up in mixture cells.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHeaderView, QMessageBox, QTableWidgetItem,
    QWidget,
)

from mudlab.default_state import (
    available_default_names, custom_default_names, import_custom_defaults,
    phases_used_in_mixtures, structural_phases, suggest_default_phase_map,
)
from mudlab.ui.ui_default_phases import Ui_DefaultPhasesDialog

_NOT_STATED = "(not stated)"
_COL_PHASE, _COL_DEFAULT = 0, 1


class _NoScrollComboBox(QComboBox):
    """A combo that ignores the mouse wheel.

    In a table row a normal combo swallows the wheel and CHANGES ITS SELECTION,
    so scrolling the list silently re-states the defaults it passes over -
    destructive, and easy not to notice. Ignoring the event lets it through to
    the table, which scrolls, which is what the gesture means here.
    """

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt naming
        event.ignore()


class DefaultPhasesDialog(QDialog):
    def __init__(self, project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_DefaultPhasesDialog()
        self.ui.setupUi(self)
        self._project = project
        # Mappings for rows NOT shown, carried through accept untouched - hiding
        # a row must never silently discard what it already said.
        self._hidden: dict = {}
        self._phases: list = []
        self.mapping: dict | None = None       # set on accept

        # Built once - enumerating the catalog costs ~1.2 s the first time and
        # is cached from then on, but every combo shares this one list anyway.
        self._custom = set(custom_default_names(project))
        self._names = available_default_names(project)
        self._combos: list[QComboBox] = []
        self._refresh_rows()

        self.ui.chk_show_unused.toggled.connect(self._on_show_unused)
        self.ui.button_import.clicked.connect(self._on_import)
        self.ui.button_match.clicked.connect(self._on_match)
        self.ui.button_clear.clicked.connect(self._on_clear)
        self.ui.buttonBox.accepted.connect(self._on_accept)
        self.ui.buttonBox.rejected.connect(self.reject)
        self._update_status()

    # ------------------------------------------------------------------
    def _visible_phases(self) -> list:
        """The phases to list: those a mixture uses, plus - always - any other
        phase that already has a default stated, so hiding a row can never make
        an existing statement invisible and then drop it."""
        stated = set(self._project.default_phase_map or {})
        if self.ui.chk_show_unused.isChecked():
            return structural_phases(self._project)
        used = phases_used_in_mixtures(self._project)
        return [phase for phase in structural_phases(self._project)
                if phase.uuid in used or phase.uuid in stated]

    def _refresh_rows(self, keep: dict | None = None) -> None:
        """(Re)build the rows for the current filter, preserving what is stated.

        Seeded from THREE places, in increasing recency: what the project has
        saved, what this dialog is holding for currently-hidden rows, and what
        the visible rows say now. `self._hidden` is the one that is easy to
        forget - a statement made while a row was visible, and then hidden,
        exists ONLY there until accept. Rebuilding from the project alone
        dropped it on the very next rebuild (a second filter toggle, or an
        Import), silently.
        """
        stated = dict(self._project.default_phase_map or {})
        stated.update(self._hidden)
        if keep is not None:
            stated.update(keep)
        self._phases = self._visible_phases()
        shown = {phase.uuid for phase in self._phases}
        # Everything stated for a row we are not showing rides along untouched.
        self._hidden = {uuid_: name for uuid_, name in stated.items()
                        if uuid_ not in shown}
        self.ui.tbl_phases.setRowCount(0)
        self._combos = []
        self._build_table()
        self._load(stated)
        self._update_status()

    def _on_show_unused(self, _checked: bool) -> None:
        self._refresh_rows(keep=self._current())

    # ------------------------------------------------------------------
    def _build_table(self) -> None:
        table = self.ui.tbl_phases
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Phase", "Started as (default phase)"])
        table.setRowCount(len(self._phases))
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(_COL_PHASE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_DEFAULT, QHeaderView.ResizeMode.Stretch)
        for row, phase in enumerate(self._phases):
            label = QTableWidgetItem(phase.name)
            label.setFlags(Qt.ItemFlag.ItemIsEnabled)      # read-only
            table.setItem(row, _COL_PHASE, label)
            combo = _NoScrollComboBox()
            combo.addItem(_NOT_STATED)
            for name in self._names:
                # The item TEXT stays the bare name - it is what gets stored -
                # and "custom" is shown as a tooltip instead, so the stored
                # mapping never carries a decoration it would have to strip.
                combo.addItem(name)
                if name in self._custom:
                    combo.setItemData(
                        combo.count() - 1,
                        "Imported reference phase (yours, not built in)",
                        Qt.ItemDataRole.ToolTipRole)
            # Typing jumps to a match: 224 entries is too many to scroll.
            combo.setEditable(False)
            combo.currentIndexChanged.connect(self._update_status)
            table.setCellWidget(row, _COL_DEFAULT, combo)
            self._combos.append(combo)

    def _load(self, mapping: dict) -> None:
        for phase, combo in zip(self._phases, self._combos):
            name = (mapping or {}).get(phase.uuid)
            index = combo.findText(name) if name else -1
            combo.setCurrentIndex(index if index >= 0 else 0)

    # ------------------------------------------------------------------
    def _on_import(self) -> None:
        """Import a .phs as one or more custom default phases, then re-offer the
        combos with the new names - keeping every choice already made."""
        path, _filter = QFileDialog.getOpenFileName(
            self, "Import reference phase", "",
            "Phase files (*.phs);;All files (*)")
        if not path:
            return
        try:
            added, shadowed = import_custom_defaults(self._project, path)
        except Exception as exc:  # noqa: BLE001 - a bad file must not kill the dialog
            QMessageBox.warning(
                self, "Import failed",
                "Could not read that phase file:\n\n%s" % exc)
            return
        if not added:
            QMessageBox.information(
                self, "Nothing imported",
                "That file contains no structural phase to use as a default.")
            return

        # Rebuild the choices, preserving what is already stated.
        current = self._current()
        self._custom = set(custom_default_names(self._project))
        self._names = available_default_names(self._project)
        self._refresh_rows(keep=current)
        # A newly imported name that matches a phase exactly is almost certainly
        # the answer, so offer it rather than making the user hunt for it.
        self._on_match()

        message = "Imported: %s." % ", ".join(added)
        if shadowed:
            message += ("  %s also exists as a built-in default; yours is used."
                        % ", ".join(shadowed))
        self.ui.lbl_status.setText(message)

    def _on_match(self) -> None:
        """Fill in the phases whose names still match the catalog exactly.

        Deliberately only EXACT matches: a fuzzy guess that silently pairs the
        wrong clay would corrupt the comparison in a way the user could not see.
        Anything renamed stays "(not stated)" for them to set."""
        suggested = suggest_default_phase_map(self._project)
        for phase, combo in zip(self._phases, self._combos):
            name = suggested.get(phase.uuid)
            if name:
                index = combo.findText(name)
                if index >= 0:
                    combo.setCurrentIndex(index)
        self._update_status()

    def _on_clear(self) -> None:
        """Clear every statement - including the rows the filter is hiding.

        The button says "all", so it has to mean all: leaving hidden rows stated
        would send the user away believing they had cleared something they had
        not. The status line says how many rows are hidden, so this is never a
        surprise about invisible data."""
        for combo in self._combos:
            combo.setCurrentIndex(0)
        self._hidden = {}
        self._update_status()

    def _current(self) -> dict:
        out = {}
        for phase, combo in zip(self._phases, self._combos):
            if combo.currentIndex() > 0:
                out[phase.uuid] = combo.currentText()
        return out

    def _update_status(self, *_args) -> None:
        stated = len(self._current())
        total = len(self._phases)
        hidden = (len(structural_phases(self._project)) - total
                  if not self.ui.chk_show_unused.isChecked() else 0)
        if total == 0:
            text = "This project has no structural phases to map."
        elif stated == total:
            text = "All %d phases stated." % total
        else:
            missing = [phase.name for phase, combo
                       in zip(self._phases, self._combos)
                       if combo.currentIndex() == 0]
            shown = ", ".join(missing[:3])
            if len(missing) > 3:
                shown += " and %d more" % (len(missing) - 3)
            text = ("%d of %d stated - the comparison will leave %s at their "
                    "current state." % (stated, total, shown))
        if hidden:
            text += ("  (%d phase(s) in no mixture are hidden.)" % hidden)
        self.ui.lbl_status.setText(text)

    def _on_accept(self) -> None:
        # The hidden rows' statements are merged back in, so filtering the list
        # is a VIEW change and never a way to lose a mapping.
        self.mapping = {**self._hidden, **self._current()}
        self.accept()
