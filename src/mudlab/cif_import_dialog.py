"""Review a CIF projection before it becomes a component.

The projection has to guess four things, and measurement over 73 published
structures says each of them can be wrong: how many layers the published cell
stacks, which oxygens are hydroxyls, where the layer stops and the interlayer
starts, and the basal spacing that follows from the first. This dialog shows
every one of them as a *proposal* and lets it be corrected.

Nothing reaches the phase until OK. That is the whole point: an importer that
silently produced a plausible-looking component would be worse than none,
because a wrong `pn` corrupts the reported oxide composition with no visible
symptom, and a row put in the wrong sheet changes what the model means.

Two disagreements it exists to surface, both found by measurement:

* **Chlorite.** Its brucite sheet is framework-bonded, so the bonding rule puts
  it in the layer, while MudLab's own shipped Chlorite carries those atoms as
  interlayer. Neither is a bug; the user has to say which they want.
* **Sepiolite.** A channel mineral. MudLab has no channel bucket, so its
  guests would land in the interlayer and look like a clay that it is not.
  Refused outright rather than approximated.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHeaderView, QMessageBox, QStyledItemDelegate,
)

from mudlab.file_parsers import cif_component as cc
from mudlab.qt_utils import clear_auto_default
from mudlab.ui.ui_cif_import import Ui_CifImportDialog

#: Column layout of the review table.
COL_NAME, COL_KIND, COL_Z, COL_PN, COL_SHEET = range(5)
HEADERS = ("Atom", "Kind", "z (nm)", "pn", "Sheet")

#: What an oxygen row may be changed to. Hydroxyl and water are the two the
#: projection can confuse: neither bonds to silicon, so only the 3-D
#: neighbourhood separates them and a marginal case can land either way.
OXYGEN_KINDS = ("O", "OH", "H2O")
SHEETS = ("Layer", "Interlayer")

#: Minerals whose structure MudLab cannot represent at all.
UNSUPPORTED = {
    "sepiolite": (
        "Sepiolite is a channel (fibrous) mineral, not a basal-repeat clay.\n\n"
        "MudLab models a layer and an interlayer; it has nowhere to put "
        "channel guests, so importing this would produce something that looks "
        "like a clay but is not one."
    ),
    "palygorskite": (
        "Palygorskite is a channel (fibrous) mineral, not a basal-repeat "
        "clay, and MudLab has nowhere to put its channel guests."
    ),
}


class _KindDelegate(QStyledItemDelegate):
    """Drop-down editor for the Kind and Sheet columns."""

    def __init__(self, choices, parent=None):
        super().__init__(parent)
        self._choices = tuple(choices)

    def createEditor(self, parent, option, index):  # noqa: N802 - Qt override
        editor = QComboBox(parent)
        editor.addItems(self._choices)
        return editor

    def setEditorData(self, editor, index):  # noqa: N802 - Qt override
        position = editor.findText(index.data() or "")
        editor.setCurrentIndex(max(0, position))

    def setModelData(self, editor, model, index):  # noqa: N802 - Qt override
        model.setData(index, editor.currentText())


def unsupported_reason(name: str) -> str:
    """Why this mineral cannot be imported at all, or "" when it can."""
    lowered = (name or "").strip().lower()
    for key, reason in UNSUPPORTED.items():
        if key in lowered:
            return reason
    return ""


class CifImportDialog(QDialog):
    """Show a CIF projection, let it be corrected, and build the component."""

    def __init__(self, parent=None, path: str = "", atom_type_map: dict | None = None):
        super().__init__(parent)
        self.ui = Ui_CifImportDialog()
        self.ui.setupUi(self)
        # Qt re-grants autoDefault on reparenting, so the .ui flags alone are
        # not enough: Return while editing a pn must not accept the dialog.
        clear_auto_default(self)

        self.path = path
        self._atom_type_map = dict(atom_type_map or {})
        self._structure = None
        self._rows = []
        self._report = None
        self._updating = False
        self.component = None
        self.added_atom_types = []

        self.model = QStandardItemModel(0, len(HEADERS), self)
        self.model.setHorizontalHeaderLabels(HEADERS)
        self.ui.tbl_rows.setModel(self.model)
        # The table is the working surface, so let it use the width: size the
        # first columns to their content and give the remainder to Sheet.
        header = self.ui.tbl_rows.horizontalHeader()
        header.setStretchLastSection(True)
        # The last column is stretched, so a centred header would float away
        # from the values beneath it.
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft
                                   | Qt.AlignmentFlag.AlignVCenter)
        for column in (COL_NAME, COL_KIND, COL_Z, COL_PN):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        # Numeric fields do not need half the dialog.
        for spin in (self.ui.spin_divisor, self.ui.spin_d001):
            spin.setMaximumWidth(140)
        self.ui.tbl_rows.setItemDelegateForColumn(
            COL_KIND, _KindDelegate(OXYGEN_KINDS, self))
        self.ui.tbl_rows.setItemDelegateForColumn(
            COL_SHEET, _KindDelegate(SHEETS, self))
        self.model.itemChanged.connect(self._on_item_changed)

        self.ui.spin_divisor.valueChanged.connect(self._on_divisor_changed)
        self.ui.btn_reset.clicked.connect(self._reproject)
        self.ui.buttonBox.accepted.connect(self._on_accept)
        self.ui.buttonBox.rejected.connect(self.reject)

        if path:
            self.load(path)

    # ------------------------------------------------------------------
    # Loading and projecting
    # ------------------------------------------------------------------
    def load(self, path: str) -> bool:
        """Read `path`. Answers whether it can be imported at all."""
        self.path = path
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                self._structure = cc.parse_cif(handle.read())
        except (OSError, ValueError) as error:
            QMessageBox.warning(
                self, "Import CIF",
                "This file could not be read as a CIF:\n\n%s\n\n%s"
                % (os.path.basename(path), error))
            return False

        reason = unsupported_reason(self._structure.name or os.path.basename(path))
        if reason:
            QMessageBox.warning(self, "Import CIF", reason)
            return False

        self.ui.lbl_source.setText(
            "<b>%s</b> — %s, cell a %.4f b %.4f c %.4f nm, "
            "α %.2f β %.2f γ %.2f°%s"
            % (self._structure.name or os.path.basename(path),
               os.path.basename(path),
               self._structure.a / 10.0, self._structure.b / 10.0,
               self._structure.c / 10.0, self._structure.alpha,
               self._structure.beta, self._structure.gamma,
               ", %s" % self._structure.space_group
               if self._structure.space_group else ""))
        # The mineral name alone does not say WHICH published structure this
        # is - nine files in the reference corpus are called "Chlorite". The
        # file identifies it, and since the name is the only field that
        # travels with a component, it is the only place the source can live.
        self.ui.edit_name.setText(cc.suggest_name(self._structure, path))
        self._reproject()
        return True

    def _reproject(self) -> None:
        """Run the projection afresh and replace whatever is on screen."""
        if self._structure is None:
            return
        divisor = self.ui.spin_divisor.value() or None
        if self._report is None:
            divisor = None                    # first pass: let it detect
        self._rows, self._report = cc.project(self._structure, divisor=divisor)
        self._updating = True
        try:
            self.ui.spin_divisor.setValue(self._report.repeat_divisor)
            self.ui.spin_d001.setValue(self._report.d001_nm)
            self.ui.lbl_cell.setText(
                "a %.4f nm   b %.4f nm" % (self._report.cell_a_nm,
                                           self._report.cell_b_nm))
            self.ui.lbl_divisor_note.setText(
                "one layer per cell" if self._report.repeat_divisor == 1
                else "cell folded to one of %d layers" % self._report.repeat_divisor)
            self.ui.lbl_layer_type.setText(_layer_type_text(self._report))
            self._fill_table()
        finally:
            self._updating = False
        self._refresh_totals()

    def _fill_table(self) -> None:
        self.model.removeRows(0, self.model.rowCount())
        for row in self._rows:
            name = QStandardItem(row.name)
            name.setEditable(False)
            kind = QStandardItem(row.name if row.name in OXYGEN_KINDS else "—")
            kind.setEditable(row.name in OXYGEN_KINDS)
            z = QStandardItem("%.4f" % row.z_nm)
            pn = QStandardItem("%.4f" % row.pn)
            sheet = QStandardItem(SHEETS[1] if row.interlayer else SHEETS[0])
            for item in (z, pn, sheet):
                item.setEditable(True)
            self.model.appendRow([name, kind, z, pn, sheet])

    # ------------------------------------------------------------------
    # Edits
    # ------------------------------------------------------------------
    def _on_divisor_changed(self, _value) -> None:
        if not self._updating:
            self._reproject()

    def _on_item_changed(self, item) -> None:
        if self._updating or not (0 <= item.row() < len(self._rows)):
            return
        row = self._rows[item.row()]
        column = item.column()
        self._updating = True
        try:
            if column == COL_KIND and item.text() in OXYGEN_KINDS:
                row.name = item.text()
                row.atom_type_name = cc.ATOM_TYPE_BY_ELEMENT.get(row.name, row.name)
                self.model.item(item.row(), COL_NAME).setText(row.name)
            elif column == COL_Z:
                value = _as_float(item.text())
                if value is None or value < 0.0:
                    item.setText("%.4f" % row.z_nm)
                else:
                    row.z_nm = value
            elif column == COL_PN:
                value = _as_float(item.text())
                if value is None or value < 0.0:
                    item.setText("%.4f" % row.pn)
                else:
                    row.pn = value
            elif column == COL_SHEET:
                row.interlayer = (item.text() == SHEETS[1])
        finally:
            self._updating = False
        self._refresh_totals()

    def _refresh_totals(self) -> None:
        layer = sum(r.pn for r in self._rows if not r.interlayer)
        inter = sum(r.pn for r in self._rows if r.interlayer)
        hydroxyl = sum(r.pn for r in self._rows if r.name == "OH")
        water = sum(r.pn for r in self._rows if r.name == "H2O")
        self.ui.lbl_totals.setText(
            "%d rows — layer %.2f atoms, interlayer %.2f; OH %.2f, H₂O %.2f"
            % (len(self._rows), layer, inter, hydroxyl, water))

        problems = list(self._report.warnings) if self._report else []
        if not any(not r.interlayer for r in self._rows):
            problems.append("Nothing is assigned to the layer.")
        highest = max((r.z_nm for r in self._rows), default=0.0)
        if highest > self.ui.spin_d001.value() + 1e-6:
            problems.append(
                "An atom sits above the basal spacing (%.4f nm vs %.4f nm)."
                % (highest, self.ui.spin_d001.value()))
        missing = sorted({r.atom_type_name for r in self._rows
                          if r.atom_type_name not in self._atom_type_map})
        if missing:
            problems.append(
                "Not in this project yet, and will be added: %s."
                % ", ".join(missing))
        self.ui.lbl_warning.setText("  ".join(problems))

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------
    def _on_accept(self) -> None:
        if not self._rows:
            QMessageBox.warning(self, "Import CIF",
                                "There is nothing to import.")
            return
        if not any(not r.interlayer for r in self._rows):
            QMessageBox.warning(
                self, "Import CIF",
                "Every row is in the interlayer. A component needs a layer - "
                "set the Sheet column for the rows that belong to it.")
            return

        report = self._report
        report.d001_nm = self.ui.spin_d001.value()
        chosen = self.ui.edit_name.text().strip()
        data = cc.component_dict(self._rows, report,
                                 name=chosen or report.name
                                 or "Imported component")

        missing = sorted({r.atom_type_name for r in self._rows
                          if r.atom_type_name not in self._atom_type_map})
        if missing:
            self.added_atom_types = self._add_atom_types(missing)

        from mudlab.models.component import Component
        self.component = Component.from_dict(data, self._atom_type_map)
        self.component.set_linked_with(None)
        self.accept()

    def _add_atom_types(self, names: list) -> list:
        """Bring the scattering factors this component needs into the project.

        Without them the atoms resolve to nothing and contribute nothing to the
        calculated pattern - silently, which is the worst way for a structural
        import to be wrong. Every name the projector emits exists in the
        shipped library, so this always succeeds for a real CIF.
        """
        from mudlab.file_parsers.atom_type_library import atom_type_library_map

        library = atom_type_library_map()
        added = []
        for name in names:
            source = library.get(name)
            if source is None:
                continue
            self._atom_type_map[name] = source
            self._atom_type_map[source.uuid] = source
            added.append(source)
        return added


def _layer_type_text(report) -> str:
    """How to describe the layer the projection found."""
    if report.layer_type == "1:1":
        return ("1:1 — one tetrahedral sheet. A 1:1 clay has no interlayer "
                "to fill and does not swell.")
    if report.layer_type == "2:1":
        return ("2:1 — two tetrahedral sheets, so an interlayer is expected.")
    return ("not a phyllosilicate profile — %d tetrahedral sheets found. "
            "Check the fold and the Sheet column before accepting."
            % report.tetrahedral_sheets)


def _as_float(text):
    try:
        return float(str(text).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
