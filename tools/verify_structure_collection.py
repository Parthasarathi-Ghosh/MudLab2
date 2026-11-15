#!/usr/bin/env python
"""Guard the shipped collection of published crystal structures (`structures/`).

65 published CIFs ship as a visible `Structures` folder beside MudLab.exe
(docs/structure-collection-plan.md, phase 1). This harness keeps four promises:

1. **The files are the published files.** Every CIF's sha256 matches the
   manifest. The manifest records the published bytes, so a citation provably
   describes its file. Git must not convert their line endings
   (`.gitattributes`); the published files mix CRLF and LF, so a conversion
   shows up here as a checksum mismatch.
2. **Everything is cited.** Every row has authors, year, journal and a COD or
   AMCSD id, and CREDITS.md names every file.
3. **MudLab can read them.** Every file parses in the clay reader with no site
   skipped, every clay projects, and every file gives reflections in the
   non-clay reader.
4. **They are the minerals they claim to be.** Reading a file proves nothing
   about its cell: the first talc shipped (Drits et al. 2012, AMCSD 0020723)
   read perfectly and carried a pyrophyllite-size cell, b 8.92 A and d001
   9.19 A instead of 9.17 A and 9.35 A. So every clay that MudLab has its own
   component for (11 of the 18) is imported the way a user would, with the
   layer count its manifest hint gives, and must match that component: the
   same basal spacing within 0.01 nm and a 00l pattern correlating at r >= 0.85.
   Measured 2026-11-15, the shipped files give r 0.907-0.999 and spacings within
   0.0065 nm; the 2012 talc gave r 0.51 and 0.0212 nm.
5. **Users can find them.** The folder resolves in a source checkout and in a
   (simulated) frozen build; the four CIF file dialogs open in the right
   subfolder and then remember the user's folder; Help -> Structure
   Collection... reaches the folder (through the Structure Library's Open
   folder since phase 2); package.cmd copies it before the self-test.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_structure_collection.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import os
import shutil
import sys
import tempfile
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

app = QApplication.instance() or QApplication([])

from mudlab import structure_collection as sc  # noqa: E402
from mudlab.calculations.goniometer import get_machine_correction_range  # noqa: E402
from mudlab.calculations.specimen import calculate_phase_intensities  # noqa: E402
from mudlab.file_parsers import cif_component as cc  # noqa: E402
from mudlab.file_parsers.atom_type_library import atom_type_library_map  # noqa: E402
from mudlab.file_parsers.default_catalog import (  # noqa: E402
    build_catalog_entry_by_name,
)
from mudlab.models.goniometer import Goniometer  # noqa: E402
from mudlab.nonclay.structure import reflections_from_cif  # noqa: E402

ROOT = os.path.join(_REPO, "structures")
CU_KA = SimpleNamespace(wavelength=0.154056)  # nm

results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def rows():
    with open(os.path.join(ROOT, "manifest.csv"), encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def full(row):
    return os.path.join(ROOT, *row["file"].split("/"))


# ---------------------------------------------------------------------------
def check_layout():
    check("structures/ exists in the repository", os.path.isdir(ROOT))
    top = sorted(os.listdir(ROOT))
    check("top level holds exactly Clays, Non-clays, README, CREDITS, manifest (%s)"
          % ", ".join(top),
          top == ["CREDITS.md", "Clays", "Non-clays", "README.md", "manifest.csv"])
    data = rows()
    check("manifest lists 65 structures (%d)" % len(data), len(data) == 65)
    listed = {os.path.normcase(full(r)) for r in data}
    on_disk = {os.path.normcase(p) for p in glob.glob(os.path.join(ROOT, "*", "*"))}
    check("every listed file exists and nothing unlisted is in Clays / Non-clays",
          listed == on_disk)
    kinds = {r["kind"] for r in data}
    check("kinds are clay / non-clay only", kinds == {"clay", "non-clay"})
    check("each file sits in its kind's folder",
          all(r["file"].startswith("Clays/" if r["kind"] == "clay" else "Non-clays/")
              for r in data))
    check("18 clays and 47 non-clays",
          sum(r["kind"] == "clay" for r in data) == 18
          and sum(r["kind"] == "non-clay" for r in data) == 47)
    check("one structure per mineral", len({r["mineral"] for r in data}) == len(data))


def check_integrity():
    data = rows()
    bad = [r["file"] for r in data
           if hashlib.sha256(open(full(r), "rb").read()).hexdigest() != r["sha256"]]
    check("every CIF matches its manifest sha256 (the published bytes)%s"
          % (": " + ", ".join(bad) if bad else ""), not bad)
    crlf = sum(b"\r\n" in open(full(r), "rb").read() for r in data)
    check("line endings left as published (%d of 65 CRLF, the rest LF)" % crlf,
          0 < crlf < len(data))
    attrs = open(os.path.join(_REPO, ".gitattributes"), encoding="utf-8").read()
    check(".gitattributes stores the CIFs without line-ending conversion",
          "structures/**/*.cif -text" in attrs.splitlines())


def check_citations():
    data = rows()
    missing = [r["mineral"] for r in data
               if not (r["authors"] and r["year"] and r["journal"])]
    check("every row has authors, year and journal%s"
          % (": " + ", ".join(missing) if missing else ""), not missing)
    check("every row has a COD or AMCSD id",
          all(r["cod"] or r["amcsd"] for r in data))
    check("every row has a formula", all(r["formula"] for r in data))
    credits = open(os.path.join(ROOT, "CREDITS.md"), encoding="utf-8").read()
    check("CREDITS.md names every file", all("`%s`" % r["file"] in credits for r in data))
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    check("README.md states the terms and asks for citation",
          "public" in readme and "attribution" in readme and "Cite" in readme)
    hinted = {r["mineral"] for r in data if r["hint"]}
    check("the two-layer polytypes carry an import hint (%s)" % ", ".join(sorted(hinted)),
          hinted == {"Nacrite", "Muscovite-2M1", "Paragonite-2M1"})
    check("README.md names the hinted polytypes",
          all(m.lower() in readme.lower() for m in hinted))


def check_readers():
    data = rows()
    skipped, unread, no_refl, unprojected = [], [], [], []
    for r in data:
        text = open(full(r), encoding="utf-8", errors="replace").read()
        try:
            st = cc.parse_cif(text)
            if st.skipped:
                skipped.append(r["mineral"])
            if r["kind"] == "clay":
                cc.project(st)
        except Exception:  # noqa: BLE001 - name the file, keep going
            (unprojected if r["kind"] == "clay" else unread).append(r["mineral"])
        try:
            refl, _ox = reflections_from_cif(full(r), CU_KA)
            if not refl:
                no_refl.append(r["mineral"])
        except Exception:  # noqa: BLE001
            no_refl.append(r["mineral"])
    check("clay reader parses all 65 with no site skipped%s"
          % (": " + ", ".join(skipped + unread) if skipped or unread else ""),
          not skipped and not unread)
    check("every clay projects onto c*%s"
          % (": " + ", ".join(unprojected) if unprojected else ""), not unprojected)
    check("non-clay reader gives reflections for all 65 at Cu Ka%s"
          % (": " + ", ".join(no_refl) if no_refl else ""), not no_refl)


#: Shipped clay (manifest `mineral`) -> MudLab's own component of that mineral.
#: The other seven clays have no counterpart: pyrophyllite, phlogopite and
#: annite have no component, and the smectites' and vermiculite's basal
#: spacing depends on hydration, so there is nothing fixed to compare with.
COUNTERPARTS = {
    "Kaolinite": "Kaolinite",
    "Dickite": "Kaolinite",
    "Nacrite": "Kaolinite",
    "Lizardite-1T": "Serpentine",
    "Illite-1M": "Illite",
    "Illite-2M1": "Illite",
    "Muscovite-2M1": "Muscovite",
    "Paragonite-2M1": "Paragonite",
    "Talc": "Talc",
    "Clinochlore": "Chlorite",
    "Chamosite": "Chlorite",
}
#: How close an imported clay must come to its counterpart.
D001_TOLERANCE_NM = 0.01
MIN_CORRELATION = 0.85


def check_agreement():
    """Each clay with a counterpart matches MudLab's own component of it."""
    data = {r["mineral"]: r for r in rows() if r["kind"] == "clay"}
    absent = sorted(set(COUNTERPARTS) - set(data))
    check("every clay with a MudLab counterpart is in the manifest%s"
          % (": missing " + ", ".join(absent) if absent else ""), not absent)

    library = atom_type_library_map()
    gonio = Goniometer()
    gonio.min_2theta, gonio.max_2theta, gonio.steps = 2.0, 45.0, 4301
    theta = np.radians(np.linspace(2.0, 45.0, 4301) * 0.5)
    correction = get_machine_correction_range(gonio, theta)

    def pattern(phase):
        return calculate_phase_intensities(
            theta, gonio.wavelength, gonio.wavelength_distribution,
            gonio.soller1, gonio.soller2, gonio.mcr_2theta, correction, [phase])[0]

    for mineral, reference_name in COUNTERPARTS.items():
        row = data.get(mineral)
        if row is None:
            continue
        # The manifest hints exactly the two-layer cells the importer does not
        # fold; the hint tells the user to set 2, so the import does too.
        divisor = 2 if row["hint"] else None
        reference = build_catalog_entry_by_name(reference_name)[0]
        want_d001 = reference.components[0].d001
        expected = pattern(reference)
        component, _report, missing = cc.component_from_cif(full(row), library,
                                                            divisor=divisor)
        phase = build_catalog_entry_by_name(reference_name)[0]
        phase.components[0] = component
        imported = pattern(phase)
        if expected.max() > 0 and imported.max() > 0:
            r = float(np.corrcoef(expected / expected.max(),
                                  imported / imported.max())[0, 1])
        else:
            r = 0.0
        ok = (not missing
              and abs(component.d001 - want_d001) <= D001_TOLERANCE_NM
              and r >= MIN_CORRELATION)
        check("%s matches MudLab's %s component: d001 %.4f vs %.4f nm, r = %.3f%s"
              % (mineral, reference_name, component.d001, want_d001, r,
                 "" if not missing else ", unresolved atom types %s" % missing),
              ok)


# ---------------------------------------------------------------------------
def check_resolver():
    check("collection_dir() finds the repository folder in a source run",
          os.path.normcase(sc.collection_dir() or "") == os.path.normcase(ROOT))
    check("clays_dir() / nonclays_dir() resolve",
          sc.clays_dir() == os.path.join(ROOT, "Clays")
          and sc.nonclays_dir() == os.path.join(ROOT, "Non-clays"))

    saved = (getattr(sys, "frozen", None), sys.executable)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            sys.frozen = True
            sys.executable = os.path.join(tmp, "MudLab.exe")
            os.makedirs(os.path.join(tmp, "Structures", "Clays"))
            check("a frozen build uses Structures beside the exe",
                  sc.collection_dir() == os.path.join(tmp, "Structures"))
        finally:
            if saved[0] is None:
                del sys.frozen
            else:
                sys.frozen = saved[0]
            sys.executable = saved[1]

    real = sc._candidates
    sc._candidates = lambda: [os.path.join(_REPO, "no-such-folder")]
    try:
        sc.forget_all()
        check("no collection -> no folder, and dialogs get no start folder",
              sc.collection_dir() is None and sc.start_dir(sc.IMPORT_CIF) == "")
    finally:
        sc._candidates = real


def check_dialog_start_folders():
    """Each CIF dialog passes the right start folder, then the user's folder."""
    seen = []
    pick = {"path": ""}

    def fake_open(*args, **kwargs):
        seen.append(args[2] if len(args) > 2 else kwargs.get("dir", ""))
        return (pick["path"], "")

    real_open = QFileDialog.getOpenFileName
    real_warning = QMessageBox.warning
    QFileDialog.getOpenFileName = staticmethod(fake_open)
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    clays, nonclays = os.path.join(ROOT, "Clays"), os.path.join(ROOT, "Non-clays")
    quartz = os.path.join(nonclays, "Quartz__COD-5000035.cif")
    try:
        # Import CIF... in the component editor.
        from mudlab import cif_import_dialog
        from mudlab.component_widget import EditComponentWidget
        from mudlab.file_parsers.default_catalog import (
            build_catalog_entry_by_name, default_catalog_entries)

        phase = build_catalog_entry_by_name(default_catalog_entries()[0][0])[0]
        widget = EditComponentWidget()
        widget.bind_components(phase.components)
        widget.ui.cmb_component.setCurrentIndex(0)
        sc.forget_all()
        seen.clear()
        widget._on_import_cif()
        check("Import CIF... opens in Clays", seen == [clays])

        class _NoReview:  # the review dialog is modal; stand in for a refusal
            component = None
            _structure = None
            added_atom_types = ()

            def __init__(self, *a, **k):
                pass

        real_review = cif_import_dialog.CifImportDialog
        cif_import_dialog.CifImportDialog = _NoReview
        try:
            with tempfile.TemporaryDirectory() as own:
                pick["path"] = os.path.join(own, "mine.cif")
                widget._on_import_cif()
                pick["path"] = ""
                seen.clear()
                widget._on_import_cif()
                check("...and afterwards opens where the user last picked from",
                      seen == [own])
        finally:
            cif_import_dialog.CifImportDialog = real_review
        widget.deleteLater()

        # Import Non-Clay.
        from mudlab.import_nonclay_dialog import ImportNonClayDialog

        sc.forget_all()
        dialog = ImportNonClayDialog()
        seen.clear()
        dialog._on_open_file()
        check("Import Non-Clay opens in Non-clays", seen == [nonclays])
        pick["path"] = quartz
        dialog._on_open_file()
        check("...builds a phase from the collection's quartz",
              bool(getattr(dialog, "_reflections", None))
              and "Quartz" in dialog.ui.lbl_source.text())
        # A folder other than the default, or remembering cannot be told apart
        # from falling back to Non-clays.
        with tempfile.TemporaryDirectory() as own:
            pick["path"] = shutil.copy(quartz, own)
            dialog._on_open_file()
            pick["path"] = ""
            seen.clear()
            dialog._on_open_file()
            check("...and afterwards opens where the user last picked from",
                  seen == [own])
        dialog.deleteLater()

        # Calibrate FWHM.
        from mudlab.calibrate_fwhm_dialog import CalibrateFwhmDialog

        sc.forget_all()
        dialog = CalibrateFwhmDialog()
        seen.clear()
        dialog._on_load_standard()
        check("Calibrate FWHM opens in Non-clays", seen == [nonclays])
        pick["path"] = quartz
        dialog._on_load_standard()
        pick["path"] = ""
        check("...reads the collection's quartz as a standard",
              bool(getattr(dialog, "_reflections", None)))
        with tempfile.TemporaryDirectory() as own:
            pick["path"] = shutil.copy(quartz, own)
            dialog._on_load_standard()
            pick["path"] = ""
            seen.clear()
            dialog._on_load_standard()
            check("...and afterwards opens where the user last picked from",
                  seen == [own])
        dialog.deleteLater()

        # The experimental non-clay dialog's CIF reference.
        from mudlab.nonclay.dialog import NonclayDialog

        sc.forget_all()
        dialog = NonclayDialog(SimpleNamespace(name="m", specimens=[]))
        seen.clear()
        dialog._on_add_cif()
        check("the non-clay dialog's structure reference opens in Non-clays",
              seen == [nonclays])
        dialog.deleteLater()

        # The four dialogs remember separately.
        sc.forget_all()
        with tempfile.TemporaryDirectory() as own:
            sc.remember(sc.IMPORT_CIF, os.path.join(own, "x.cif"))
            check("each dialog has its own memory",
                  sc.start_dir(sc.IMPORT_CIF) == own
                  and sc.start_dir(sc.IMPORT_NONCLAY) == nonclays)
        check("a remembered folder that is gone falls back to the collection",
              sc.start_dir(sc.IMPORT_CIF) == clays)
    finally:
        QFileDialog.getOpenFileName = real_open
        QMessageBox.warning = real_warning
        pick["path"] = ""
        sc.forget_all()


def check_help_action():
    from PySide6.QtGui import QDesktopServices

    from mudlab.main_window import MainWindow
    from mudlab.structure_library_dialog import StructureLibraryDialog

    opened, told = [], []
    real_open = QDesktopServices.openUrl
    real_info = QMessageBox.information
    real_exec = StructureLibraryDialog.exec
    QDesktopServices.openUrl = staticmethod(lambda url: opened.append(url) or True)
    QMessageBox.information = staticmethod(lambda *a, **k: told.append(a[2:3]))
    # Since phase 2 the action opens the Structure Library (modal), and the
    # folder is one click further, on its Open folder button. exec() would
    # block head-less, so it presses that button and returns.
    StructureLibraryDialog.exec = lambda self: (self.ui.btn_open_folder.click(), 0)[1]
    try:
        window = MainWindow()
        action = window.ui.actionStructureCollection
        menu = [a.objectName() for a in window.ui.menuHelp.actions()]
        check("Help menu: Manual, How MudLab Works, Structure Collection, About (%s)"
              % ", ".join(menu),
              menu == ["actionManual", "actionHowItWorks",
                       "actionStructureCollection", "actionAbout"])
        check("the action names CREDITS.md in its tooltip",
              "CREDITS.md" in action.toolTip())
        action.trigger()
        check("Help -> Structure Collection... reaches the collection folder "
              "(the library's Open folder)",
              len(opened) == 1
              and os.path.normcase(opened[0].toLocalFile()) == os.path.normcase(ROOT)
              and not told)

        real = sc.collection_dir
        sc.collection_dir = lambda: None
        try:
            opened.clear()
            action.trigger()
            check("...and says so instead when there is no collection",
                  not opened and len(told) == 1)
        finally:
            sc.collection_dir = real
        window.setWindowModified(False)
        window.deleteLater()
    finally:
        QDesktopServices.openUrl = real_open
        QMessageBox.information = real_info
        StructureLibraryDialog.exec = real_exec


def check_packaging():
    package = open(os.path.join(_REPO, "package.cmd"), encoding="utf-8").read()
    copy_at = package.find('xcopy "structures" "dist\\MudLab\\Structures\\"')
    test_at = package.find("--selftest")
    check("package.cmd copies structures to dist\\MudLab\\Structures",
          copy_at >= 0)
    check("...before the frozen self-test runs", 0 <= copy_at < test_at)
    spec = open(os.path.join(_REPO, "MudLab.spec"), encoding="utf-8").read()
    check("...and not through the spec's datas (that would hide it in _internal)",
          '"structures"' not in spec)


def main() -> int:
    print("=" * 72)
    print("Shipped structure collection (structures/)")
    print("=" * 72)
    check_layout()
    check_integrity()
    check_citations()
    check_readers()
    check_agreement()
    check_resolver()
    check_dialog_start_folders()
    check_help_action()
    check_packaging()
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    passed = sum(ok for _, ok in results)
    print("%d/%d checks passed" % (passed, len(results)))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
