"""Structure Library: browse the shipped crystal structures and add one as a
phase. Design: ui/structure_library.ui. Plan: docs/structure-collection-plan.md,
phase 2.

The collection (`structure_collection`) is 65 published CIFs with a manifest:
mineral, family, formula, citation, notes and an import hint. This dialog is
that manifest as a searchable table, with the full citation of the selected
structure beside it and two ways to use it:

- **New clay phase...** (layer silicates only): the existing CIF review
  (`CifImportDialog`) projects the structure onto c* and lets every guess be
  corrected; on OK a one-component R0 phase named after the mineral holds the
  component, and the project adopts its atom types. Until now a CIF could only
  REPLACE a component of a phase that already existed.
- **Add as non-clay phase...** (any structure): Import Non-Clay opens with the
  file loaded and the mineral's name filled in, so the user still checks the
  name, the peak width and the oxides.

Opened from Edit Phases it is given the project and offers both; it hands each
new phase back through `phase_created`, and Edit Phases adds it exactly as its
own Add and Import Non-Clay do. Opened from Help -> Structure Collection... it
has no project: it is for browsing, citing and opening the folder.

Lifetime: always run modally with `exec()` and released by the caller with
`deleteLater()` afterwards. Not WA_DeleteOnClose - the caller reads nothing
back, but the add actions open their own modal dialogs from this one, and a
close-time delete would take this dialog away under them.
"""

from __future__ import annotations

import html

from PySide6.QtCore import QSortFilterProxyModel, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QDialog, QHeaderView, QMessageBox, QWidget

from mudlab import structure_collection as sc
from mudlab.qt_utils import clear_auto_default
from mudlab.ui.ui_structure_library import Ui_StructureLibraryDialog

COLUMNS = ("Mineral", "Group", "Kind", "Formula", "Year", "Source")
COL_MINERAL, COL_GROUP, COL_KIND, COL_FORMULA, COL_YEAR, COL_SOURCE = range(6)
#: The manifest row, kept on the Mineral item of each table row.
ROW_ROLE = Qt.ItemDataRole.UserRole + 1
ALL_GROUPS = "All groups"
KIND_TEXT = {sc.KIND_CLAY: "Clay", sc.KIND_NONCLAY: "Non-clay"}
#: What a search word is matched against.
SEARCH_FIELDS = ("mineral", "group", "kind", "formula", "authors", "year",
                 "title", "journal", "cod", "amcsd", "file", "note")


def _haystack(row: dict) -> str:
    return " ".join(str(row.get(field, "")) for field in SEARCH_FIELDS).lower()


class _Filter(QSortFilterProxyModel):
    """Every typed word must appear somewhere in the row (any order, any case),
    and the row must be in the chosen family."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._words: list[str] = []
        self._group = ""

    def set_text(self, text: str) -> None:
        self.beginFilterChange()
        self._words = text.lower().split()
        self.endFilterChange()

    def set_group(self, group: str) -> None:
        self.beginFilterChange()
        self._group = group
        self.endFilterChange()

    def filterAcceptsRow(self, source_row, source_parent) -> bool:  # noqa: N802 - Qt
        item = self.sourceModel().item(source_row, COL_MINERAL)
        row = item.data(ROW_ROLE) if item is not None else None
        if not row:
            return False
        if self._group and row["group"] != self._group:
            return False
        haystack = row["_haystack"]
        return all(word in haystack for word in self._words)


class StructureLibraryDialog(QDialog):
    #: A phase built from a structure, for the caller to add to the project.
    phase_created = Signal(object)

    def __init__(self, parent: QWidget | None = None, project=None,
                 goniometer=None, rows: list | None = None) -> None:
        """`project` enables the two add actions (Edit Phases); without it the
        dialog is for browsing (Help). `goniometer` sets the wavelength a
        non-clay pattern is computed at. `rows` overrides the manifest (tests)."""
        super().__init__(parent)
        self.ui = Ui_StructureLibraryDialog()
        self.ui.setupUi(self)
        # Layer 2 of the autoDefault rule (the .ui is layer 1, the app-wide
        # Enter policy layer 3): Return in the search box must not fire an add.
        clear_auto_default(self)

        self.project = project
        self.goniometer = goniometer
        self.folder = sc.collection_dir()
        self.rows = list(rows) if rows is not None else sc.load_manifest()
        for row in self.rows:
            row["_haystack"] = _haystack(row)

        self.model = QStandardItemModel(0, len(COLUMNS), self)
        self.model.setHorizontalHeaderLabels(COLUMNS)
        self.proxy = _Filter(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.ui.tbl_structures.setModel(self.proxy)
        self._fill()

        self._new_clay_tip = self.ui.btn_new_clay.toolTip()
        # Browsing only (Help): no project to add a phase to.
        browsing = project is None
        self.ui.btn_new_clay.setVisible(not browsing)
        self.ui.btn_add_nonclay.setVisible(not browsing)

        self.ui.edit_search.textChanged.connect(self._on_search)
        self.ui.cmb_group.currentIndexChanged.connect(self._on_group)
        self.ui.tbl_structures.selectionModel().currentRowChanged.connect(
            lambda *_: self._show_current())
        self.ui.btn_new_clay.clicked.connect(self._on_new_clay)
        self.ui.btn_add_nonclay.clicked.connect(self._on_add_nonclay)
        self.ui.btn_copy_citation.clicked.connect(self._on_copy_citation)
        self.ui.btn_open_folder.clicked.connect(self._on_open_folder)
        self.ui.buttonBox.rejected.connect(self.reject)

        self.ui.splitter.setSizes([420, 200])
        if not self.rows:
            self._disable_for_missing_collection()
        else:
            self.ui.lbl_intro.setText(
                "%d published crystal structures that ship with MudLab. Cite the "
                "article for any structure you use.%s"
                % (len(self.rows), "" if not browsing else
                   " To add one as a phase, open the library from Edit Phases."))
            self._select_first()
        self._update_count()
        self._show_current()

    # ------------------------------------------------------------------
    # The table
    # ------------------------------------------------------------------
    def _fill(self) -> None:
        groups = []
        for row in self.rows:
            values = (row["mineral"], row["group"],
                      KIND_TEXT.get(row["kind"], row["kind"]), row["formula"],
                      row["year"], sc.source_ids(row))
            items = [QStandardItem(text) for text in values]
            items[COL_MINERAL].setData(row, ROW_ROLE)
            items[COL_MINERAL].setToolTip(row["file"])
            self.model.appendRow(items)
            if row["group"] not in groups:
                groups.append(row["group"])
        self.ui.cmb_group.addItem(ALL_GROUPS, "")
        for group in groups:                 # manifest order: by mineral family
            self.ui.cmb_group.addItem(group, group)

        header = self.ui.tbl_structures.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft
                                   | Qt.AlignmentFlag.AlignVCenter)
        for column in (COL_MINERAL, COL_GROUP, COL_KIND, COL_YEAR, COL_SOURCE):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_FORMULA, QHeaderView.ResizeMode.Stretch)
        # The manifest's own order (grouped by family) until a header is clicked.
        self.proxy.sort(-1)
        header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

    def _on_search(self, text: str) -> None:
        self.proxy.set_text(text)
        self._after_filter()

    def _on_group(self, _index: int) -> None:
        self.proxy.set_group(self.ui.cmb_group.currentData() or "")
        self._after_filter()

    def _after_filter(self) -> None:
        if not self.ui.tbl_structures.selectionModel().currentIndex().isValid():
            self._select_first()
        self._update_count()
        self._show_current()

    def _select_first(self) -> None:
        if self.proxy.rowCount() > 0:
            self.ui.tbl_structures.setCurrentIndex(self.proxy.index(0, COL_MINERAL))

    def _update_count(self) -> None:
        shown, total = self.proxy.rowCount(), len(self.rows)
        self.ui.lbl_count.setText(
            "%d structures" % total if shown == total
            else "%d of %d structures" % (shown, total))

    def current_row(self) -> dict | None:
        """The manifest row of the selected structure, or None."""
        index = self.ui.tbl_structures.selectionModel().currentIndex()
        if not index.isValid():
            return None
        source = self.proxy.mapToSource(index.siblingAtColumn(COL_MINERAL))
        item = self.model.item(source.row(), COL_MINERAL)
        return item.data(ROW_ROLE) if item is not None else None

    # ------------------------------------------------------------------
    # Details pane
    # ------------------------------------------------------------------
    def _show_current(self) -> None:
        row = self.current_row()
        has_row = row is not None
        self.ui.btn_copy_citation.setEnabled(has_row)
        self.ui.btn_add_nonclay.setEnabled(has_row and self.project is not None)
        self.ui.btn_new_clay.setEnabled(
            has_row and self.project is not None and row["kind"] == sc.KIND_CLAY)
        self.ui.btn_new_clay.setToolTip(
            self._new_clay_tip if not has_row or row["kind"] == sc.KIND_CLAY
            else "Only a layer silicate (the Clays folder) projects into a clay "
                 "component. Add this one as a non-clay phase instead.")
        self.ui.txt_details.setHtml(details_html(row) if has_row else "")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_new_clay(self) -> None:
        row = self.current_row()
        if row is None or self.project is None or row["kind"] != sc.KIND_CLAY:
            return
        if row.get("hint"):
            # The review is where the fix is made, so say it on the way in.
            QMessageBox.information(
                self, "New clay phase",
                "%s\n\n%s\n\nThe import review opens next."
                % (row["mineral"], row["hint"]))

        from mudlab.cif_import_dialog import CifImportDialog, new_clay_phase

        dialog = CifImportDialog(self, path=row["path"],
                                 atom_type_map=self.project.atom_type_uuid_map())
        try:
            if dialog.component is None and dialog._structure is None:
                return                       # unreadable or unsupported; it said so
            if not dialog.exec() or dialog.component is None:
                return
            phase = new_clay_phase(self.project, dialog.component, row["mineral"])
        finally:
            dialog.deleteLater()
        self.phase_created.emit(phase)
        self._status('Added the clay phase "%s" to the project.' % phase.name)

    def _on_add_nonclay(self) -> None:
        row = self.current_row()
        if row is None or self.project is None:
            return
        from mudlab.import_nonclay_dialog import ImportNonClayDialog

        dialog = ImportNonClayDialog(self, goniometer=self.goniometer,
                                     path=row["path"], name=row["mineral"])
        try:
            if dialog.exec() != QDialog.DialogCode.Accepted or dialog.phase is None:
                return
            phase = dialog.phase
        finally:
            dialog.deleteLater()
        self.phase_created.emit(phase)
        self._status('Added the non-clay phase "%s" to the project.' % phase.name)

    def _on_copy_citation(self) -> None:
        row = self.current_row()
        if row is None:
            return
        QGuiApplication.clipboard().setText(sc.citation(row))
        self._status("Copied the citation for %s." % row["mineral"])

    def _on_open_folder(self) -> None:
        if self.folder is None:
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(self.folder)):
            QMessageBox.information(
                self, "Structure Library",
                "Could not open the folder. It is here:\n\n%s" % self.folder)

    # ------------------------------------------------------------------
    def _status(self, text: str) -> None:
        self.ui.lbl_status.setText(text)

    def _disable_for_missing_collection(self) -> None:
        """No folder, or no manifest in it: say so, and offer nothing."""
        self.ui.lbl_intro.setText(
            "This installation has no structure collection. It ships as a "
            "Structures folder beside MudLab.exe.")
        for widget in (self.ui.edit_search, self.ui.cmb_group,
                       self.ui.tbl_structures, self.ui.btn_new_clay,
                       self.ui.btn_add_nonclay, self.ui.btn_copy_citation,
                       self.ui.btn_open_folder):
            widget.setEnabled(False)


def details_html(row: dict) -> str:
    """The selected structure, for the details pane."""
    esc = html.escape
    kind = KIND_TEXT.get(row["kind"], row["kind"])
    parts = ["<h3>%s</h3>" % esc(row["mineral"]),
             "<p>%s &middot; %s &middot; %s</p>"
             % (esc(row["group"]), esc(kind), esc(row["formula"]))]
    cite = esc(sc.citation(row))
    if row.get("doi"):
        url = "https://doi.org/%s" % row["doi"]
        cite = cite.replace(esc(url), '<a href="%s">%s</a>' % (esc(url), esc(url)))
    parts.append("<p><b>Cite:</b> %s</p>" % cite)
    if row.get("note"):
        parts.append("<p><b>Note:</b> %s</p>" % esc(row["note"]))
    if row.get("hint"):
        parts.append("<p><b>Before you accept the import review:</b> %s</p>"
                     % esc(row["hint"]))
    parts.append("<p>File: %s<br>Obtained via %s</p>"
                 % (esc(row["file"]), esc(row.get("obtained_via", ""))))
    return "".join(parts)
