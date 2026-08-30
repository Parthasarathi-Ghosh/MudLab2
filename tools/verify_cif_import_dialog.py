#!/usr/bin/env python
"""Import component from CIF: the review step, and the path a user takes.

Stage 1 built the projector; this pins the part that makes it a feature. The
projector has to guess four things and measurement says each can be wrong, so
nothing may reach a phase without being shown first:

  * how many layers the published cell stacks,
  * which oxygens are hydroxyls (or interlayer water),
  * which rows belong to the layer and which to the interlayer,
  * the basal spacing that follows from the first.

Deliberately corpus-free: every case is built from a synthetic CIF written to a
temporary file, so this runs anywhere, CI included. The projector's agreement
with published structures is `verify_cif_component.py`'s job.

Two behaviours here are worth more than they look. **Atom types the CIF needs
and the project lacks are added**, because an unresolved type contributes
nothing to the calculated pattern and says nothing while doing it. And
**sepiolite is refused**: MudLab has no channel bucket, so its guests would
land in the interlayer and produce something that looks like a clay and is not.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_cif_import_dialog.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from mudlab.cif_import_dialog import (  # noqa: E402
    COL_KIND, COL_PN, COL_SHEET, COL_Z, CifImportDialog, unsupported_reason,
)
from mudlab.file_parsers.default_catalog import (  # noqa: E402
    build_catalog_entry_by_name,
)

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []
SCRATCH = tempfile.mkdtemp(prefix="cifdlg-")


def check(label, ok):
    results.append((label, bool(ok)))


def write_cif(name: str, mineral: str = "Synthetic", layers: int = 1,
              interlayer: bool = True, sheets: int = 2,
              space_group: str = "", operators: tuple = ()) -> str:
    """A minimal clay cell. `sheets` picks 2:1 (two tetrahedral sheets) or 1:1
    (one); `layers` stacks the whole thing; `operators` adds a symmetry loop."""
    if sheets == 1:
        sites = [
            ("O1", "O", 0.00), ("Si1", "Si", 0.06), ("O2", "O", 0.23),
            ("Oh1", "O", 0.24), ("Al1", "Al", 0.34), ("Oh2", "O", 0.44),
        ]
    else:
        sites = [
            ("O1", "O", 0.00), ("Si1", "Si", 0.06), ("O2", "O", 0.23),
            ("Oh1", "O", 0.24), ("Al1", "Al", 0.34), ("Oh2", "O", 0.44),
            ("O3", "O", 0.45), ("Si2", "Si", 0.61), ("O4", "O", 0.67),
        ]
    if interlayer and sheets != 1:
        sites.append(("K1", "K", 0.84))
    elif interlayer and sheets == 1:
        # a trace guest of the kind that exposed a real misclassification
        sites.append(("Ca1", "Ca", 0.88))
    rows = []
    for copy in range(layers):
        offset = copy / float(layers)
        for index, (label, element, z) in enumerate(sites):
            rows.append("%s_%d %s %.4f %.4f %.4f 1.0"
                        % (label, copy, element,
                           0.05 * index, 0.11 * index, z / layers + offset))
    head = ["data_synthetic", "_chemical_name_mineral '%s'" % mineral]
    if space_group:
        head.append("_symmetry_space_group_name_H-M '%s'" % space_group)
    symmetry = []
    if operators:
        symmetry = ["loop_", "_space_group_symop_operation_xyz"]
        symmetry += ["'%s'" % op for op in operators]
    text = "\n".join(head + [
        "_cell_length_a 5.2000",
        "_cell_length_b 9.0000",
        "_cell_length_c %.4f" % (10.0 * layers),
        "_cell_angle_alpha 90.0",
        "_cell_angle_beta 100.0",
        "_cell_angle_gamma 90.0",
        "loop_",
        "_atom_site_label",
        "_atom_site_type_symbol",
        "_atom_site_fract_x",
        "_atom_site_fract_y",
        "_atom_site_fract_z",
        "_atom_site_occupancy",
    ] + rows + symmetry) + "\n"
    path = os.path.join(SCRATCH, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def illite_atom_types() -> dict:
    """The atom types a project built from the shipped Illite would hold."""
    phase = build_catalog_entry_by_name("Illite")[0]
    table = {}
    for component in phase.components:
        for atom in list(component.layer_atoms) + list(component.interlayer_atoms):
            if atom.atom_type is not None:
                table[atom.atom_type.name] = atom.atom_type
                table[atom.atom_type.uuid] = atom.atom_type
    return table


def main():  # noqa: C901 - a checklist
    warned, informed = [], []
    real_warning, real_information = QMessageBox.warning, QMessageBox.information
    QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(a[2]))
    QMessageBox.information = staticmethod(lambda *a, **k: informed.append(a[2]))
    try:
        types = illite_atom_types()

        # -------------------------------------------------- the user's path
        from mudlab.component_widget import CIF_FILTERS

        check("the component pane offers a CIF filter (%s)" % CIF_FILTERS.split(";;")[0],
              ".cif" in CIF_FILTERS)

        from mudlab.ui.ui_edit_component import Ui_EditComponentWidget
        from PySide6.QtWidgets import QWidget

        holder = QWidget()
        pane = Ui_EditComponentWidget()
        pane.setupUi(holder)
        check("...and an Import CIF button beside Import",
              hasattr(pane, "btn_import_cif")
              and "CIF" in pane.btn_import_cif.text())
        check("...which does not claim autoDefault",
              not pane.btn_import_cif.autoDefault())

        import mudlab.component_widget as cw
        source = open(cw.__file__, encoding="utf-8").read()
        check("...wired to a handler", "_on_import_cif" in source
              and "btn_import_cif.clicked.connect" in source)

        # ------------------------------------------------ loading a CIF
        path = write_cif("clay.cif")
        dialog = CifImportDialog(None, path=path, atom_type_map=types)
        check("a CIF loads and populates the table (%d rows)"
              % dialog.model.rowCount(), dialog.model.rowCount() >= 8)
        check("...with nothing built yet", dialog.component is None)
        # The header states the cell in NANOMETRES, the unit the rest of the
        # dialog uses, not the angstrom the CIF was written in.
        check("...the source line names the mineral and the cell in nm",
              "Synthetic" in dialog.ui.lbl_source.text()
              and "0.5200" in dialog.ui.lbl_source.text())
        check("...an interlayer cation is recognised as interlayer",
              any(r.interlayer and r.name == "K" for r in dialog._rows))
        check("...hydroxyls are found (OH pn %.1f)"
              % sum(r.pn for r in dialog._rows if r.name == "OH"),
              any(r.name == "OH" for r in dialog._rows))

        # ------------------------------------------- the four overrides
        stacked = write_cif("stacked.cif", layers=2)
        two = CifImportDialog(None, path=stacked, atom_type_map=types)
        detected = two.ui.spin_divisor.value()
        check("a two-layer cell is detected and folded (divisor %d)" % detected,
              detected == 2)
        folded_d001 = two.ui.spin_d001.value()
        two.ui.spin_divisor.setValue(1)
        check("...and the divisor can be overridden, re-projecting "
              "(%.4f -> %.4f nm)" % (folded_d001, two.ui.spin_d001.value()),
              two.ui.spin_d001.value() > folded_d001 * 1.8)

        oxygen = next(i for i, r in enumerate(dialog._rows) if r.name == "O")
        before = sum(r.pn for r in dialog._rows if r.name == "OH")
        dialog.model.item(oxygen, COL_KIND).setText("OH")
        check("an oxygen can be corrected to a hydroxyl (OH %.1f -> %.1f)"
              % (before, sum(r.pn for r in dialog._rows if r.name == "OH")),
              dialog._rows[oxygen].name == "OH"
              and sum(r.pn for r in dialog._rows if r.name == "OH") > before)
        check("...and its atom type follows",
              dialog._rows[oxygen].atom_type_name == "OH1-")

        moved = next(i for i, r in enumerate(dialog._rows) if not r.interlayer)
        dialog.model.item(moved, COL_SHEET).setText("Interlayer")
        check("a row can be moved to the interlayer",
              dialog._rows[moved].interlayer)
        dialog.model.item(moved, COL_SHEET).setText("Layer")

        row_z = dialog._rows[0].z_nm
        dialog.model.item(0, COL_Z).setText("not a number")
        check("a nonsense z is refused and the cell reverts (%.4f)"
              % dialog._rows[0].z_nm, abs(dialog._rows[0].z_nm - row_z) < 1e-9)
        dialog.model.item(0, COL_PN).setText("-3")
        check("a negative pn is refused", dialog._rows[0].pn >= 0.0)
        dialog.model.item(0, COL_PN).setText("5.5")
        check("...but a real edit is kept (%.2f)" % dialog._rows[0].pn,
              abs(dialog._rows[0].pn - 5.5) < 1e-9)

        check("the totals line reports what is on screen",
              "rows" in dialog.ui.lbl_totals.text()
              and "OH" in dialog.ui.lbl_totals.text())

        # ---------------------------------------- layer type, naming, symmetry
        from mudlab.file_parsers import cif_component as cc

        one_to_one = write_cif("kaol.cif", mineral="Kaolinite", sheets=1)
        thin = CifImportDialog(None, path=one_to_one, atom_type_map=types)
        check("a one-sheet profile is called 1:1 (%s)" % thin._report.layer_type,
              thin._report.layer_type == "1:1")
        check("...and the dialog says a 1:1 clay has no interlayer",
              "no interlayer" in thin.ui.lbl_layer_type.text())
        check("a two-sheet profile is called 2:1 (%s)" % dialog._report.layer_type,
              dialog._report.layer_type == "2:1")

        # A 1:1 clay with something in its interlayer is a misclassification, and
        # the projector caught a real one this way (trace Ca inside a kaolinite
        # layer, put in the interlayer at 1.2% occupancy).
        guested = write_cif("kaol_guest.cif", mineral="Kaolinite", sheets=1,
                            interlayer=True)
        flagged = CifImportDialog(None, path=guested, atom_type_map=types)
        check("...and a 1:1 clay with interlayer rows is flagged",
              any("1:1" in w and "interlayer" in w
                  for w in flagged._report.warnings))

        check("the proposed name distinguishes the structure, not just the mineral "
              "(%r)" % thin.ui.edit_name.text(),
              thin.ui.edit_name.text().startswith("Kaolinite")
              and thin.ui.edit_name.text() != "Kaolinite")
        renamed = CifImportDialog(None, path=one_to_one, atom_type_map=dict(types))
        renamed.ui.edit_name.setText("My illite")
        renamed._on_accept()
        check("...and the name the user types is what the component gets (%r)"
              % (renamed.component and renamed.component.name),
              renamed.component is not None and renamed.component.name == "My illite")

        # Water is its own scatterer; hydroxyl is not a substitute for it.
        check("water maps to the H2O type, not to hydroxyl (%s)"
              % cc.ATOM_TYPE_BY_ELEMENT["H2O"],
              cc.ATOM_TYPE_BY_ELEMENT["H2O"] == "H2O")
        from mudlab.file_parsers.atom_type_library import atom_type_library_map
        library = atom_type_library_map()
        check("...and H2O and OH1- really are different scatterers",
              abs(library["H2O"].weight - library["OH1-"].weight) > 0.5)

        # Without symmetry operators a cell cannot be expanded; say so rather than
        # inventing operators from a space-group name.
        plain = write_cif("nosym.cif", mineral="Talc", sheets=2)
        check("a CIF with no operator loop is read as P1 and SAYS so",
              any("P1" in w for w in
                  CifImportDialog(None, path=plain,
                                  atom_type_map=types)._report.warnings))
        named = write_cif("nosym_named.cif", mineral="Talc", sheets=2,
                          space_group="C 1 2/m 1")
        warnings = CifImportDialog(None, path=named,
                                   atom_type_map=types)._report.warnings
        check("...naming the space group it could not use",
              any("C 1 2/m 1" in w for w in warnings))
        withops = write_cif("withsym.cif", mineral="Talc", sheets=2,
                            operators=("x,y,z", "-x,-y,-z"))
        check("...and a CIF that HAS operators is not warned about",
              not any("P1" in w for w in
                      CifImportDialog(None, path=withops,
                                      atom_type_map=types)._report.warnings))
        # ------------------------------------------------ refusals
        warned.clear()
        sepiolite = write_cif("sep.cif", mineral="Sepiolite")
        blocked = CifImportDialog(None, path=sepiolite, atom_type_map=types)
        check("sepiolite is refused, with a reason", bool(warned)
              and "channel" in warned[-1].lower())
        check("...and nothing is projected from it", not blocked._rows)
        check("unsupported_reason names palygorskite too",
              bool(unsupported_reason("Palygorskite")))

        warned.clear()
        junk = os.path.join(SCRATCH, "junk.cif")
        with open(junk, "w", encoding="utf-8") as handle:
            handle.write("this is not a CIF at all\n")
        CifImportDialog(None, path=junk, atom_type_map=types)
        check("an unreadable file warns instead of raising", bool(warned))

        # ------------------------------------------------ the result
        warned.clear()
        thin = CifImportDialog(None, path=path, atom_type_map=types)
        for index in range(len(thin._rows)):
            thin.model.item(index, COL_SHEET).setText("Interlayer")
        thin._on_accept()
        check("accepting with an empty layer is refused",
              thin.component is None and bool(warned))

        final = CifImportDialog(None, path=path, atom_type_map=dict(types))
        final._on_accept()
        component = final.component
        check("accepting builds a component (%r)" % (component and component.name),
              component is not None)
        check("...with the basal spacing shown (%.4f nm)" % component.d001,
              abs(component.d001 - final.ui.spin_d001.value()) < 1e-6)
        check("...with layer and interlayer atoms (%d + %d)"
              % (len(component.layer_atoms), len(component.interlayer_atoms)),
              component.layer_atoms and component.interlayer_atoms)
        unresolved = [a.name for a in component.layer_atoms + component.interlayer_atoms
                      if a.atom_type is None]
        check("...and EVERY atom resolves to a scattering factor%s"
              % ("" if not unresolved else " -> %s" % unresolved), not unresolved)
        check("...it is not linked to anything", component.linked_with is None)

        # A project lacking a needed type must gain it, not silently drop it.
        bare = {k: v for k, v in types.items() if "K1+" not in str(k)}
        needy = CifImportDialog(None, path=path, atom_type_map=bare)
        check("a missing atom type is announced before accepting",
              "K1+" in needy.ui.lbl_warning.text())
        needy._on_accept()
        check("...and added on accept (%s)"
              % [a.name for a in needy.added_atom_types],
              any(a.name == "K1+" for a in needy.added_atom_types))
        still = [a.name for a in needy.component.layer_atoms
                 + needy.component.interlayer_atoms if a.atom_type is None]
        check("...so no row is left contributing nothing%s"
              % ("" if not still else " -> %s" % still), not still)

        passed = sum(1 for _, ok in results if ok)
        total = len(results)
        print("=" * 72)
        print("Import component from CIF (review dialog)")
        print("=" * 72)
        for label, ok in results:
            print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
        print("%d/%d checks passed" % (passed, total))
        return 0 if passed == total else 1
    finally:
        QMessageBox.warning = real_warning
        QMessageBox.information = real_information


if __name__ == "__main__":
    sys.exit(main())
