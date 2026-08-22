"""Default phases dialog. Design: ui/default_phases.ui.

Records which shipped default phase each of the project's phases started as -
the mapping the composition comparison needs and cannot derive (see
`mudlab.default_state` for why: fresh uuids on every catalog build, no stored
origin, and freely renamed phases).

One row per structural phase, with a drop-down of every default phase the
catalog can build. "(not stated)" is always available and is the default, so a
partial mapping is a first-class outcome: the comparison then simply leaves
those phases at their current state rather than guessing.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHeaderView, QTableWidgetItem, QWidget,
)

from mudlab.default_state import structural_phases, suggest_default_phase_map
from mudlab.file_parsers.default_catalog import default_phase_names
from mudlab.ui.ui_default_phases import Ui_DefaultPhasesDialog

_NOT_STATED = "(not stated)"
_COL_PHASE, _COL_DEFAULT = 0, 1


class DefaultPhasesDialog(QDialog):
    def __init__(self, project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_DefaultPhasesDialog()
        self.ui.setupUi(self)
        self._project = project
        self._phases = structural_phases(project)
        self.mapping: dict | None = None       # set on accept

        # Built once - enumerating the catalog costs ~1.2 s the first time and
        # is cached from then on, but every combo shares this one list anyway.
        self._names = default_phase_names()
        self._combos: list[QComboBox] = []
        self._build_table()
        self._load(project.default_phase_map)

        self.ui.button_match.clicked.connect(self._on_match)
        self.ui.button_clear.clicked.connect(self._on_clear)
        self.ui.buttonBox.accepted.connect(self._on_accept)
        self.ui.buttonBox.rejected.connect(self.reject)
        self._update_status()

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
            combo = QComboBox()
            combo.addItem(_NOT_STATED)
            combo.addItems(self._names)
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
        for combo in self._combos:
            combo.setCurrentIndex(0)
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
        self.ui.lbl_status.setText(text)

    def _on_accept(self) -> None:
        self.mapping = self._current()
        self.accept()
