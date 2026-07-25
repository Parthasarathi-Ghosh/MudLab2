#!/usr/bin/env python
"""Durable harness for the wavelength-distribution (emission spectrum) editor,
run head-less.

The editor was previously unported: the goniometer's "Edit emission spectrum"
button did nothing and the distribution could not be changed (Goniometer.to_dict
even kept the raw string verbatim, assuming no UI would edit it). This harness
drives the new editor + its model/parser support and asserts:

  - the .wld reader/writer round-trips and matches the bundled presets;
  - Goniometer.set_wavelength_distribution updates the list, the derived
    dominant `wavelength`, and (critically) invalidates the verbatim raw string
    so an EDIT is actually persisted, while an UNTOUCHED goniometer still
    round-trips byte-identically;
  - the dialog binds, edits/validates cells, adds/removes rows, and
    imports/exports .wld files, writing every change straight to the model;
  - the GoniometerWidget wires the button and shows the dominant wavelength.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_wavelength_distribution.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project.
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from mudlab.file_parsers.mud_project import load_mud, save_mud
from mudlab.file_parsers.wld_file import load_wld, save_wld
from mudlab.goniometer_widget import GoniometerWidget
from mudlab.models import Goniometer
from mudlab.wavelength_distribution_dialog import (
    WavelengthDistributionDialog, _DEFAULT_WLD_DIR,
)

_FIXTURE_NAME = "308 r1.mud"
FIXTURE = os.path.join(_REPO, "tools", "sample_projects", _FIXTURE_NAME)
if not os.path.isfile(FIXTURE):
    FIXTURE = os.path.join(os.path.expanduser("~"), "Downloads", _FIXTURE_NAME)
if not os.path.isfile(FIXTURE):
    print("No sample project found; skipping (exit 2).")
    raise SystemExit(2)

app = QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _pairs_equal(a, b, tol=1e-12):
    return len(a) == len(b) and all(
        abs(x0 - y0) < tol and abs(x1 - y1) < tol
        for (x0, x1), (y0, y1) in zip(a, b)
    )


# ----------------------------------------------------------------------
# Parser
# ----------------------------------------------------------------------
def check_parser():
    cu = load_wld(os.path.join(_DEFAULT_WLD_DIR, "Cu.wld"))
    check("wld: Cu.wld = single CuKalpha line",
          _pairs_equal(cu, [(0.15418, 1.0)]))
    xe = load_wld(os.path.join(_DEFAULT_WLD_DIR, "Cu LynxEye XE.wld"))
    check("wld: Cu LynxEye XE.wld has 4 lines summing ~1.0",
          len(xe) == 4 and abs(sum(f for _, f in xe) - 1.0) < 0.02)

    # Save -> load round-trip preserves values.
    tmp = os.path.join(tempfile.mkdtemp(), "rt.wld")
    save_wld(tmp, xe)
    check("wld: save/load round-trip is loss-free", _pairs_equal(load_wld(tmp), xe))
    # A written file carries the old app's header.
    with open(tmp, encoding="utf-8") as handle:
        first = handle.readline().strip()
    check("wld: writes 'Wavelength, Factor' header", first == "Wavelength, Factor")

    # Blank lines / stray header text are skipped; empty content raises.
    messy = os.path.join(tempfile.mkdtemp(), "messy.wld")
    with open(messy, "w", encoding="utf-8") as handle:
        handle.write("Wavelength, Factor\n\n0.154, 1.0\n   \nfoo, bar\n")
    check("wld: skips blanks and non-numeric rows",
          _pairs_equal(load_wld(messy), [(0.154, 1.0)]))
    empty = os.path.join(tempfile.mkdtemp(), "empty.wld")
    with open(empty, "w", encoding="utf-8") as handle:
        handle.write("Wavelength, Factor\n")
    try:
        load_wld(empty)
        check("wld: empty file raises ValueError", False)
    except ValueError:
        check("wld: empty file raises ValueError", True)


# ----------------------------------------------------------------------
# Model: set_wavelength_distribution + persistence
# ----------------------------------------------------------------------
def check_model_setter():
    g = Goniometer()
    fired = []
    g.data_changed.connect(lambda: fired.append(1))
    g.set_wavelength_distribution([(0.1544, 0.5), (0.1540, 1.0)])
    check("setter: stores float tuples",
          _pairs_equal(g.wavelength_distribution, [(0.1544, 0.5), (0.154, 1.0)]))
    check("setter: dominant wavelength = highest-fraction line",
          abs(g.wavelength - 0.154) < 1e-12)
    check("setter: emits data_changed", len(fired) == 1)
    check("setter: invalidates verbatim raw string",
          "wavelength_distribution" not in g.raw_properties)


def check_mud_persistence():
    # Unedited goniometer: the raw wavelength_distribution survives verbatim.
    project = load_mud(FIXTURE)
    gonio = next((s.goniometer for s in project.specimens
                  if s.goniometer is not None), None)
    if gonio is None:
        check("persistence: fixture has a goniometer", False)
        return
    check("persistence: fixture has a goniometer", True)
    orig_raw = gonio.raw_properties.get("wavelength_distribution")

    tmp = os.path.join(tempfile.mkdtemp(), "unedited.mud")
    save_mud(project, tmp)
    reloaded = load_mud(tmp)
    rg = next(s.goniometer for s in reloaded.specimens if s.goniometer is not None)
    check("persistence: untouched distribution round-trips byte-identically",
          rg.raw_properties.get("wavelength_distribution") == orig_raw)

    # Edited goniometer: the change is re-encoded and reloads intact.
    project2 = load_mud(FIXTURE)
    g2 = next(s.goniometer for s in project2.specimens if s.goniometer is not None)
    edited = [(0.1544, 0.5), (0.1540, 1.0), (0.1392, 0.1)]
    g2.set_wavelength_distribution(edited)
    tmp2 = os.path.join(tempfile.mkdtemp(), "edited.mud")
    save_mud(project2, tmp2)
    rg2 = next(s.goniometer for s in load_mud(tmp2).specimens
               if s.goniometer is not None)
    check("persistence: edited distribution is saved and reloads intact",
          _pairs_equal(rg2.wavelength_distribution, edited))


# ----------------------------------------------------------------------
# Dialog
# ----------------------------------------------------------------------
def check_dialog_bind_and_edit():
    g = Goniometer()
    g.set_wavelength_distribution([(0.1544, 0.5), (0.1540, 1.0)])
    dlg = WavelengthDistributionDialog(goniometer=g)
    check("dialog: binds one row per distribution line", dlg.model.rowCount() == 2)

    # Valid cell edit writes through to the model.
    dlg.model.item(0, 1).setText("0.8")
    check("dialog: valid cell edit pushes to goniometer",
          abs(g.wavelength_distribution[0][1] - 0.8) < 1e-12)

    # Invalid cell edit reverts and leaves the model untouched.
    before = list(g.wavelength_distribution)
    dlg.model.item(0, 0).setText("not-a-number")
    check("dialog: invalid edit reverts the cell",
          dlg.model.item(0, 0).text() == "%g" % before[0][0])
    check("dialog: invalid edit leaves the goniometer unchanged",
          _pairs_equal(g.wavelength_distribution, before))
    dlg.deleteLater()


def check_dialog_add_remove():
    g = Goniometer()
    g.set_wavelength_distribution([(0.154, 1.0)])
    dlg = WavelengthDistributionDialog(goniometer=g)
    dlg._on_add()
    check("dialog: add appends a row (model + goniometer)",
          dlg.model.rowCount() == 2 and len(g.wavelength_distribution) == 2)
    # Remove the first row.
    dlg.ui.tv_wld.setCurrentIndex(dlg.model.index(0, 0))
    dlg._on_del()
    check("dialog: remove drops the selected row",
          dlg.model.rowCount() == 1 and len(g.wavelength_distribution) == 1)
    dlg.deleteLater()


def check_dialog_import_export():
    g = Goniometer()
    dlg = WavelengthDistributionDialog(goniometer=g)

    preset = os.path.join(_DEFAULT_WLD_DIR, "Cu LynxEye XE.wld")
    orig_q = QMessageBox.question
    orig_open = QFileDialog.getOpenFileName
    QMessageBox.question = staticmethod(
        lambda *a, **k: QMessageBox.StandardButton.Yes)
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (preset, ""))
    try:
        dlg._on_import()
    finally:
        QMessageBox.question = orig_q
        QFileDialog.getOpenFileName = orig_open
    check("dialog: import replaces distribution from .wld",
          _pairs_equal(g.wavelength_distribution, load_wld(preset)))
    check("dialog: import repopulates the table",
          dlg.model.rowCount() == len(load_wld(preset)))

    out = os.path.join(tempfile.mkdtemp(), "exported")  # no extension on purpose
    orig_save = QFileDialog.getSaveFileName
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (out, ""))
    try:
        dlg._on_export()
    finally:
        QFileDialog.getSaveFileName = orig_save
    check("dialog: export appends .wld and writes the file",
          os.path.isfile(out + ".wld"))
    check("dialog: exported file reloads to the same distribution",
          _pairs_equal(load_wld(out + ".wld"), g.wavelength_distribution))
    dlg.deleteLater()


# ----------------------------------------------------------------------
# GoniometerWidget wiring
# ----------------------------------------------------------------------
def check_widget_wiring():
    g = Goniometer()
    g.set_wavelength_distribution([(0.1544, 0.4), (0.1540, 1.0)])
    w = GoniometerWidget()
    w.bind_goniometer(g)
    check("widget: label shows dominant wavelength after bind",
          "0.15400" in w.ui.gonio_lambda_lbl.text())

    # The edit button is wired; opening the editor refreshes the label. Stub
    # exec so it does not block, then change the distribution and refresh.
    orig_exec = WavelengthDistributionDialog.exec
    WavelengthDistributionDialog.exec = lambda self: 0
    try:
        g.set_wavelength_distribution([(0.1544, 1.0), (0.1540, 0.4)])
        w._on_edit_wld()
    finally:
        WavelengthDistributionDialog.exec = orig_exec
    check("widget: label refreshes to the new dominant wavelength",
          "0.15440" in w.ui.gonio_lambda_lbl.text())
    w.deleteLater()


def main():
    check_parser()
    check_model_setter()
    check_mud_persistence()
    check_dialog_bind_and_edit()
    check_dialog_add_remove()
    check_dialog_import_export()
    check_widget_wiring()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- wavelength-distribution editor verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
