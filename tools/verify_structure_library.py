#!/usr/bin/env python
"""Structure Library (phase 2 of the shipped structure collection), head-less.

The dialog shows the collection's manifest as a searchable table, with the
selected structure's full citation, and adds a structure as a phase: **New clay
phase...** (the CIF review, then a one-component R0 phase) or **Add as non-clay
phase...** (Import Non-Clay with the file loaded). Edit Phases opens it with
the project; Help -> Structure Collection... opens it for browsing.

Checked here, through the real Edit Phases dialog and the real project:

1. **The table.** All 65 rows in the manifest's order, the columns, the family
   filter's choices, sorting.
2. **Search and filter.** Every typed word must match, in any order and case;
   the family filter narrows further; no match leaves nothing selected and
   every action disabled.
3. **Details and citation.** For all 65, Copy citation puts exactly the
   CREDITS.md citation on the clipboard; the DOI is a link; the three two-layer
   polytypes show their import hint.
4. **Buttons.** New clay phase only for a clay; the add actions only with a
   project; after a real show no button is the default, and Return/Enter in
   the search box fires nothing.
5. **Adding.** New clay phase builds a one-component R0 phase named after the
   mineral, holding the citation-named component, and the PROJECT adopts its
   atom types - they survive a save and reload. Cancel in the review adds
   nothing. A hinted polytype says so before the review. Add as non-clay phase
   builds a NonClayPhase from the structure; Cancel adds nothing. One library
   session can add several phases.
6. **The component editor's Import CIF...** now puts new atom types into the
   project too. Until 1.1.0 they went into the editor's private copy of the
   list, so an imported illite's potassium scattered nothing after a reload.
7. **No collection:** the dialog opens, says so, and offers nothing.
8. **Help -> Structure Collection...** opens the library for browsing, and its
   Open folder button opens the collection.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_structure_library.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import contextlib
import os
import re
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QDesktopServices, QGuiApplication, QKeyEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QPushButton  # noqa: E402

app = QApplication.instance() or QApplication([])

from mudlab import structure_collection as sc  # noqa: E402
from mudlab.cif_import_dialog import CifImportDialog  # noqa: E402
from mudlab.edit_phases_dialog import EditPhasesDialog  # noqa: E402
from mudlab.file_parsers.default_catalog import add_catalog_entry_to_project  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.import_nonclay_dialog import ImportNonClayDialog  # noqa: E402
from mudlab.models import Project  # noqa: E402
from mudlab.qt_utils import install_enter_policy  # noqa: E402
from mudlab.structure_library_dialog import (  # noqa: E402
    ALL_GROUPS, COL_SOURCE, COLUMNS, StructureLibraryDialog, details_html,
)

install_enter_policy(app)

#: Every message box a flow raises is RECORDED here instead of shown. A modal
#: box blocks forever head-less, so a regression that ends in a warning (Import
#: Non-Clay with nothing loaded refuses OK with one) would hang the whole suite
#: instead of failing a check - found by a deliberate break. Checks that expect
#: a box patch it locally; any other box is a failure (see check_adding).
DIALOGS: list[str] = []


def _record_dialog(*args, **_kwargs):
    DIALOGS.append(str(args[2]) if len(args) > 2 else "")
    return QMessageBox.StandardButton.Ok


for _name in ("warning", "critical", "information", "question"):
    setattr(QMessageBox, _name, staticmethod(_record_dialog))

ROOT = os.path.join(_REPO, "structures")
ROWS = sc.load_manifest()
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


@contextlib.contextmanager
def patched(owner, name, value):
    saved = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        setattr(owner, name, saved)


def shown(dialog) -> list[str]:
    return [dialog.proxy.index(i, 0).data() for i in range(dialog.proxy.rowCount())]


def select(dialog, mineral) -> dict:
    for i in range(dialog.proxy.rowCount()):
        if dialog.proxy.index(i, 0).data() == mineral:
            dialog.ui.tbl_structures.setCurrentIndex(dialog.proxy.index(i, 0))
            return dialog.current_row()
    raise LookupError(mineral)


def expected(words="", group=""):
    words = words.lower().split()
    return [r["mineral"] for r in ROWS
            if (not group or r["group"] == group)
            and all(w in r["_haystack"] for w in words)]


def credits_citation(row) -> str:
    lines = open(os.path.join(ROOT, "CREDITS.md"), encoding="utf-8").read().splitlines()
    i = next(i for i, line in enumerate(lines) if "`%s`" % row["file"] in line)
    return re.sub(r"\*([^*]+)\*", r"\1", lines[i + 1].strip())


def atoms_of(phase):
    out = []
    for component in phase.components:
        out += list(component.layer_atoms) + list(component.interlayer_atoms)
    return out


# ---------------------------------------------------------------------------
def check_table():
    dialog = StructureLibraryDialog(None, project=Project())
    global ROWS
    ROWS = dialog.rows                      # the rows carry their search text
    check("all 65 structures load (%d)" % dialog.proxy.rowCount(),
          dialog.proxy.rowCount() == len(ROWS) == 65)
    check("the count says so: %r" % dialog.ui.lbl_count.text(),
          dialog.ui.lbl_count.text() == "65 structures")
    headers = tuple(dialog.model.headerData(i, Qt.Orientation.Horizontal)
                    for i in range(dialog.model.columnCount()))
    check("columns: %s" % ", ".join(headers), headers == COLUMNS)
    check("rows in the manifest's order (grouped by family) until sorted",
          shown(dialog) == [r["mineral"] for r in ROWS])
    families = list(dict.fromkeys(r["group"] for r in ROWS))
    combo = [dialog.ui.cmb_group.itemText(i) for i in range(dialog.ui.cmb_group.count())]
    check("family filter offers All groups + the %d families in order" % len(families),
          combo == [ALL_GROUPS] + families)
    row = select(dialog, "Chamosite")
    source_index = dialog.ui.tbl_structures.currentIndex().siblingAtColumn(COL_SOURCE)
    check("Source column gives both database numbers (%s)" % source_index.data(),
          source_index.data() == "COD 9009233, AMCSD 0012235" == sc.source_ids(row))
    dialog.ui.tbl_structures.sortByColumn(0, Qt.SortOrder.AscendingOrder)
    names = shown(dialog)
    check("clicking a header sorts (Mineral, A-Z)",
          names == sorted(names, key=str.lower) and len(names) == 65)
    dialog.deleteLater()

    fresh = StructureLibraryDialog(None, project=Project())
    check("the first structure is selected on open, with its details",
          fresh.current_row() is not None
          and fresh.current_row()["mineral"] == ROWS[0]["mineral"]
          and ROWS[0]["mineral"] in fresh.ui.txt_details.toPlainText())
    fresh.deleteLater()


def check_filter():
    dialog = StructureLibraryDialog(None, project=Project())
    dialog.ui.edit_search.setText("quartz")
    check("search 'quartz' -> Quartz alone; count %r" % dialog.ui.lbl_count.text(),
          shown(dialog) == ["Quartz"] and dialog.ui.lbl_count.text() == "1 of 65 structures")
    dialog.ui.edit_search.setText("1981 TALC")
    check("every word must match, any order and case ('1981 TALC' -> %s)" % shown(dialog),
          shown(dialog) == ["Talc"])
    dialog.ui.edit_search.setText("kaolin")
    check("a word matches the family too ('kaolin' -> %d)" % len(shown(dialog)),
          shown(dialog) == expected("kaolin") and len(shown(dialog)) >= 4)
    dialog.ui.edit_search.setText("")
    dialog.ui.cmb_group.setCurrentIndex(dialog.ui.cmb_group.findText("Carbonates"))
    check("family filter: Carbonates -> %d" % len(shown(dialog)),
          shown(dialog) == expected(group="Carbonates") and len(shown(dialog)) == 7)
    dialog.ui.edit_search.setText("mg")
    check("family AND search narrow together (%s)" % ", ".join(shown(dialog)),
          shown(dialog) == expected("mg", "Carbonates") and 0 < len(shown(dialog)) < 7)
    dialog.ui.edit_search.setText("no such mineral zzz")
    buttons = (dialog.ui.btn_new_clay, dialog.ui.btn_add_nonclay, dialog.ui.btn_copy_citation)
    check("no match: nothing shown, nothing selected, every action disabled",
          shown(dialog) == [] and dialog.current_row() is None
          and not any(b.isEnabled() for b in buttons)
          and dialog.ui.txt_details.toPlainText().strip() == "")
    dialog.ui.edit_search.setText("")
    dialog.ui.cmb_group.setCurrentIndex(0)
    check("clearing both shows all 65 again, with a selection",
          len(shown(dialog)) == 65 and dialog.current_row() is not None)
    dialog.deleteLater()


def check_details_and_citation():
    dialog = StructureLibraryDialog(None, project=Project())
    clipboard = QGuiApplication.clipboard()
    wrong = []
    for row in ROWS:
        select(dialog, row["mineral"])
        dialog.ui.btn_copy_citation.click()
        if clipboard.text() != sc.citation(row) or clipboard.text() != credits_citation(row):
            wrong.append(row["mineral"])
    check("Copy citation gives exactly the CREDITS.md citation, all 65%s"
          % ("" if not wrong else " -> wrong: %s" % wrong), not wrong)
    check("...and the status line says what was copied",
          "Copied the citation" in dialog.ui.lbl_status.text())
    chamosite = next(r for r in ROWS if r["mineral"] == "Chamosite")
    check("the DOI is a link in the details",
          '<a href="https://doi.org/10.1346/CCMN.1992.0400311">' in details_html(chamosite))
    hinted = [r for r in ROWS if r["hint"]]
    check("the hinted polytypes show their hint in the details (%s)"
          % ", ".join(r["mineral"] for r in hinted),
          len(hinted) == 3 and all("Layers stacked in the published cell"
                                   in details_html(r) for r in hinted))
    check("...and no other structure does",
          not any("Before you accept" in details_html(r) for r in ROWS if not r["hint"]))
    dialog.deleteLater()


def check_buttons():
    dialog = StructureLibraryDialog(None, project=Project())
    original_tip = dialog.ui.btn_new_clay.toolTip()
    select(dialog, "Kaolinite")
    check("a clay: New clay phase and Add as non-clay phase enabled",
          dialog.ui.btn_new_clay.isEnabled() and dialog.ui.btn_add_nonclay.isEnabled())
    select(dialog, "Quartz")
    check("a non-clay: New clay phase disabled, with the reason as its tooltip",
          not dialog.ui.btn_new_clay.isEnabled() and dialog.ui.btn_add_nonclay.isEnabled()
          and "Only a layer silicate" in dialog.ui.btn_new_clay.toolTip())
    select(dialog, "Kaolinite")
    check("...and back on a clay the button's own tooltip returns",
          dialog.ui.btn_new_clay.toolTip() == original_tip)
    dialog.deleteLater()

    browse = StructureLibraryDialog(None)
    check("browsing (no project): the add actions are hidden",
          not browse.ui.btn_new_clay.isVisibleTo(browse)
          and not browse.ui.btn_add_nonclay.isVisibleTo(browse))
    check("...Copy citation and Open folder remain, and it says where adding is",
          browse.ui.btn_copy_citation.isEnabled() and browse.ui.btn_open_folder.isEnabled()
          and "Edit Phases" in browse.ui.lbl_intro.text())
    browse.deleteLater()

    # AUTODEFAULT: assert after a real show (the promotion happens then), and
    # press the keys - nothing beats pressing them.
    fired = []
    with patched(StructureLibraryDialog, "_on_new_clay", lambda self: fired.append("clay")), \
            patched(StructureLibraryDialog, "_on_add_nonclay", lambda self: fired.append("nonclay")), \
            patched(StructureLibraryDialog, "_on_copy_citation", lambda self: fired.append("copy")), \
            patched(StructureLibraryDialog, "_on_open_folder", lambda self: fired.append("folder")):
        dialog = StructureLibraryDialog(None, project=Project())
        dialog.show()
        app.processEvents()
        buttons = dialog.findChildren(QPushButton)
        check("after a real show no button is the default or autoDefault",
              not any(b.isDefault() or b.autoDefault() for b in buttons))
        dialog.ui.edit_search.setFocus()
        app.processEvents()
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            app.sendEvent(dialog.ui.edit_search,
                          QKeyEvent(QKeyEvent.Type.KeyPress, key,
                                    Qt.KeyboardModifier.NoModifier))
            app.processEvents()
        check("Return/Enter in the search box fires nothing and closes nothing",
              not fired and dialog.isVisible())
        dialog.close()
        dialog.deleteLater()


# ---------------------------------------------------------------------------
def _accept_review(self):
    self._on_accept()
    return 1 if self.component is not None else 0


def _accept_nonclay(self):
    self._on_accept()
    return self.result()


def check_adding():
    boxes_before = len(DIALOGS)
    project = Project()
    add_catalog_entry_to_project(project, "Kaolinite")   # no potassium in it
    editor = EditPhasesDialog(None, project=project)
    button = editor.button_structure_library
    check("Edit Phases has a Structure Library... button beside Import Non-Clay",
          button.text() == "Structure Library…"
          and editor.ui.extraLayout.indexOf(button) > editor.ui.extraLayout.indexOf(
              editor.button_import_nonclay) >= 0)
    check("...which is not autoDefault", not button.autoDefault() and not button.isDefault())

    def run(script):
        """Open the library from Edit Phases and run `script` inside it."""
        with patched(StructureLibraryDialog, "exec", lambda self: script(self) or 0):
            button.click()

    phases_before = len(project.phases)
    types_before = {a.name for a in project.atom_types}
    rows_before = editor.objects_model.rowCount()
    library = {}

    def new_illite(dialog):
        library["dialog"] = dialog
        select(dialog, "Illite-1M")
        dialog.ui.btn_new_clay.click()

    with patched(CifImportDialog, "exec", _accept_review):
        run(new_illite)
    added = project.phases[phases_before:] if len(project.phases) > phases_before else []
    phase = added[0] if added else None
    check("New clay phase adds one phase, named after the mineral (%s)"
          % [p.name for p in added], len(added) == 1 and phase.name == "Illite-1M")
    check("...a one-component R0 clay phase",
          phase is not None and getattr(phase, "type", "") == "Phase" and phase.G == 1
          and getattr(phase.probabilities, "R", None) == 0 and len(phase.components) == 1)
    check("...holding the citation-named component (%s)"
          % (phase.components[0].name if phase else ""),
          phase is not None and "AMCSD-0005015" in phase.components[0].name)
    check("...listed and selected in Edit Phases",
          editor.objects_model.rowCount() == rows_before + 1
          and editor.ui.edit_objects_treeview.currentIndex().row() == rows_before)
    check("...and the library says what it added",
          "Illite-1M" in library["dialog"].ui.lbl_status.text())
    gained = {a.name for a in project.atom_types} - types_before
    check("the PROJECT adopts the atom types it lacked (%s)" % sorted(gained),
          "K1+" in gained)
    check("every atom of the new phase uses one of the project's own atom types",
          phase is not None and all(a.atom_type is not None
                                    and any(a.atom_type is t for t in project.atom_types)
                                    for a in atoms_of(phase)))
    path = os.path.join(tempfile.mkdtemp(), "library.mud")
    save_mud(project, path)
    reloaded = load_mud(path)
    again = next((p for p in reloaded.phases if p.name == "Illite-1M"), None)
    check("...so they survive a save and reload (no atom left without a type)",
          again is not None and atoms_of(again)
          and all(a.atom_type is not None for a in atoms_of(again)))

    # Cancel in the review adds nothing.
    count, types = len(project.phases), {a.name for a in project.atom_types}
    with patched(CifImportDialog, "exec", lambda self: 0):
        run(lambda d: (select(d, "Vermiculite"), d.ui.btn_new_clay.click()))
    check("Cancel in the review adds no phase and no atom type",
          len(project.phases) == count and {a.name for a in project.atom_types} == types)

    # A two-layer polytype says so before the review opens.
    told = []
    with patched(CifImportDialog, "exec", lambda self: 0), \
            patched(QMessageBox, "information",
                    staticmethod(lambda *a, **k: told.append(str(a[2]) if len(a) > 2 else ""))):
        run(lambda d: (select(d, "Nacrite"), d.ui.btn_new_clay.click()))
    check("a hinted polytype gives its hint before the review",
          len(told) == 1 and "Layers stacked in the published cell" in told[0])

    # Add as non-clay phase.
    count = len(project.phases)
    with patched(ImportNonClayDialog, "exec", _accept_nonclay):
        run(lambda d: (select(d, "Quartz"), d.ui.btn_add_nonclay.click()))
    new = project.phases[count:]
    nonclay = new[0] if new else None
    check("Add as non-clay phase adds a NonClayPhase named after the mineral (%s)"
          % [p.name for p in new],
          len(new) == 1 and getattr(nonclay, "type", "") == "NonClayPhase"
          and nonclay.name == "Quartz")
    check("...computed from the structure: reflections and SiO2 (%.1f wt%%)"
          % (nonclay.oxides.get("SiO2", 0.0) if nonclay else 0.0),
          nonclay is not None and len(nonclay.reflections) > 10
          and nonclay.oxides.get("SiO2", 0.0) > 99.0)
    count = len(project.phases)
    with patched(ImportNonClayDialog, "exec", lambda self: 0):
        run(lambda d: (select(d, "Calcite"), d.ui.btn_add_nonclay.click()))
    check("Cancel in Import Non-Clay adds nothing", len(project.phases) == count)

    # Several phases from one visit.
    count = len(project.phases)
    with patched(CifImportDialog, "exec", _accept_review), \
            patched(ImportNonClayDialog, "exec", _accept_nonclay):
        run(lambda d: (select(d, "Talc"), d.ui.btn_new_clay.click(),
                       select(d, "Calcite"), d.ui.btn_add_nonclay.click()))
    check("one visit to the library can add several phases (%s)"
          % [p.name for p in project.phases[count:]],
          [p.name for p in project.phases[count:]] == ["Talc", "Calcite"])
    unexpected = DIALOGS[boxes_before:]
    check("no warning or message came up while adding%s"
          % ("" if not unexpected else " -> %s" % [u[:60] for u in unexpected]),
          not unexpected)
    editor.deleteLater()


def check_import_nonclay_path():
    quartz = next(r for r in ROWS if r["mineral"] == "Quartz")["path"]
    dialog = ImportNonClayDialog(None, path=quartz, name="Quartz")
    check("Import Non-Clay(path=, name=) opens with the CIF loaded and the name set",
          dialog.ui.edit_name.text() == "Quartz" and len(dialog._reflections) > 10
          and os.path.basename(quartz) in dialog.ui.lbl_source.text())
    dialog.deleteLater()


def check_component_editor_atom_types():
    """Regression: Import CIF... in the component editor lost new atom types."""
    project = Project()
    add_catalog_entry_to_project(project, "Kaolinite")
    illite = next(r for r in ROWS if r["mineral"] == "Illite-1M")["path"]
    editor = EditPhasesDialog(None, project=project)
    editor.ui.edit_objects_treeview.setCurrentIndex(editor.objects_model.index(0, 0))
    with patched(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (illite, ""))), \
            patched(QMessageBox, "information", staticmethod(lambda *a, **k: None)), \
            patched(CifImportDialog, "exec", _accept_review):
        # (information: "Imported. These atom types were added..." - expected)
        editor.phase_widget.component_widget._on_import_cif()
    phase = project.phases[0]
    check("component editor's Import CIF... puts K1+ into the PROJECT",
          "K1+" in {a.name for a in project.atom_types}
          and "AMCSD-0005015" in phase.components[0].name)
    path = os.path.join(tempfile.mkdtemp(), "component.mud")
    save_mud(project, path)
    again = load_mud(path).phases[0]
    check("...so after a save and reload every atom still has its type "
          "(until 1.1.0 the potassium had none and scattered nothing)",
          all(a.atom_type is not None for a in atoms_of(again)))
    editor.deleteLater()


def check_missing_collection():
    with patched(sc, "collection_dir", lambda: None):
        dialog = StructureLibraryDialog(None, project=Project())
    controls = (dialog.ui.edit_search, dialog.ui.cmb_group, dialog.ui.tbl_structures,
                dialog.ui.btn_new_clay, dialog.ui.btn_add_nonclay,
                dialog.ui.btn_copy_citation, dialog.ui.btn_open_folder)
    check("no collection: the dialog opens and says so",
          dialog.proxy.rowCount() == 0
          and "no structure collection" in dialog.ui.lbl_intro.text())
    check("...and offers nothing", not any(w.isEnabled() for w in controls))
    dialog.deleteLater()


def check_help_and_folder():
    from mudlab.main_window import MainWindow

    opened, told, libraries = [], [], []
    with patched(QDesktopServices, "openUrl",
                 staticmethod(lambda url: opened.append(url) or True)), \
            patched(QMessageBox, "information",
                    staticmethod(lambda *a, **k: told.append(a[2:3]))), \
            patched(StructureLibraryDialog, "exec",
                    lambda self: (libraries.append(self), self.ui.btn_open_folder.click(), 0)[2]):
        window = MainWindow()
        window.ui.actionStructureCollection.trigger()
        check("Help -> Structure Collection... opens the library for browsing",
              len(libraries) == 1 and libraries[0].project is None
              and not libraries[0].ui.btn_new_clay.isVisibleTo(libraries[0]))
        check("...whose Open folder opens the collection",
              len(opened) == 1
              and os.path.normcase(opened[0].toLocalFile()) == os.path.normcase(ROOT)
              and not told)
        with patched(sc, "collection_dir", lambda: None):
            libraries.clear()
            window.ui.actionStructureCollection.trigger()
        check("...and with no collection it says so and opens nothing",
              not libraries and len(told) == 1)
        window.setWindowModified(False)
        window.deleteLater()


def main() -> int:
    print("=" * 72)
    print("Structure Library")
    print("=" * 72)
    check_table()
    check_filter()
    check_details_and_citation()
    check_buttons()
    check_adding()
    check_import_nonclay_path()
    check_component_editor_atom_types()
    check_missing_collection()
    check_help_and_folder()
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    passed = sum(ok for _, ok in results)
    print("%d/%d checks passed" % (passed, len(results)))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
