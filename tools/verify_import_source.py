#!/usr/bin/env python
"""Import specimen -> the General tab's 'Source' box. It was empty; the old app
filled it with the file name, 2theta range/step, and instrument metadata. This
covers the restore + the .xrdml metadata:

  - build_source_string always reports File + 2theta range/step/points (any
    format, from the data);
  - parse_xrdml_metadata reads wavelength / count time / sample / date / radius
    from a PANalytical .xrdml, which the source string then lists;
  - importing a .xrdml populates specimen.source AND applies its Kα1 wavelength
    to the specimen's goniometer;
  - a plain text file (no metadata reader) still gets the File + 2theta source.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_import_source.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication

import zipfile

from mudlab.file_parsers.rasx_parser import parse_rasx_metadata
from mudlab.file_parsers.uxd_parser import parse_uxd_metadata
from mudlab.file_parsers.xrd_import import (
    build_source_string, parse_pattern_metadata,
)
from mudlab.file_parsers.xrdml_parser import parse_xrdml_metadata
from mudlab.main_window import MainWindow
from mudlab.models import Project

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []
_TMP = tempfile.mkdtemp()

_XRDML = (
    '<?xml version="1.0"?>\n'
    '<xrdMeasurements xmlns="http://www.xrdml.com/XRDMeasurement/1.5">'
    '<sample type="To be analyzed"><id>S42</id><name>Test Clay</name></sample>'
    '<xrdMeasurement measurementType="Scan" status="Completed">'
    '<usedWavelength intended="K-Alpha 1">'
    '<kAlpha1 unit="Angstrom">1.5405980</kAlpha1>'
    '<kAlpha2 unit="Angstrom">1.5444260</kAlpha2>'
    '<ratioKAlpha2KAlpha1>0.5</ratioKAlpha2KAlpha1>'
    '</usedWavelength>'
    '<incidentBeamPath><radius unit="mm">240.00</radius></incidentBeamPath>'
    '<scan status="Completed"><header>'
    '<startTimeStamp>2024-01-15T10:30:00+01:00</startTimeStamp></header>'
    '<dataPoints>'
    '<positions axis="2Theta"><startPosition>10</startPosition>'
    '<endPosition>10.4</endPosition></positions>'
    '<commonCountingTime>2</commonCountingTime>'
    '<intensities unit="counts">100 200 300 400 500</intensities>'
    '</dataPoints></scan></xrdMeasurement></xrdMeasurements>'
)


def check(label, ok):
    results.append((label, bool(ok)))


def _write(name, text):
    p = os.path.join(_TMP, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def main():
    # --- build_source_string: base info from the data (any format) -----------
    txt = _write("sample.txt", "\n".join("%.2f %d" % (5 + i * 0.1, 10 + i)
                                         for i in range(651)))
    x = np.linspace(5.0, 70.0, 651)
    base = build_source_string(txt, x, {})
    check("base source names the file", "File: sample.txt" in base)
    check("base source reports the 2theta step", "step:" in base)
    check("base source reports the point count", "(651 points)" in base)

    # --- parse_xrdml_metadata: the instrument fields -------------------------
    xrdml = _write("scan.xrdml", _XRDML)
    md = parse_xrdml_metadata(xrdml)
    check("xrdml wavelength Ka1 read (Angstrom -> nm)",
          abs(md.get("wavelength_ka1", 0) - 0.15405980) < 1e-8)
    check("xrdml wavelength Ka2 read", abs(md.get("wavelength_ka2", 0) - 0.15444260) < 1e-8)
    check("xrdml count time read", md.get("count_time") == 2.0)
    check("xrdml sample name + id read",
          md.get("sample_name") == "Test Clay" and md.get("sample_id") == "S42")
    check("xrdml scan date read", md.get("scan_date", "").startswith("2024-01-15"))
    check("xrdml radius read (mm)", md.get("radius_mm") == 240.0)
    check("parse_pattern_metadata dispatches by extension",
          parse_pattern_metadata(xrdml).get("count_time") == 2.0
          and parse_pattern_metadata(txt) == {})

    # --- source string lists the xrdml metadata ------------------------------
    src = build_source_string(xrdml, np.array([10.0, 10.1, 10.2, 10.3, 10.4]), md)
    for needle in ("File: scan.xrdml", "Count time: 2.00 s",
                   "Sample: Test Clay (id: S42)", "Scanned: 2024-01-15",
                   "0.15406", "Goniometer radius: 240.0 mm"):
        check("source lists %r" % needle, needle in src)

    # --- end-to-end import: source set + Ka1 applied to the goniometer --------
    win = MainWindow()
    win._set_project(Project(name="p"))
    imported = win.import_specimen_files([xrdml])
    check("one specimen imported", len(imported) == 1)
    spec = imported[0]
    check("imported specimen has a non-empty source",
          bool(spec.source) and "File: scan.xrdml" in spec.source)
    check("import applied the file's Ka1 wavelength to the goniometer",
          spec.goniometer is not None
          and abs(spec.goniometer.wavelength - 0.15405980) < 1e-6)

    # The Edit Specimen dialog's Source box shows it (the reported scenario).
    from mudlab.edit_specimen_dialog import EditSpecimenDialog
    dlg = EditSpecimenDialog()
    dlg.bind_specimen(spec)
    box_text = dlg.ui.specimen_source.toPlainText()
    check("Edit Specimen Source box is no longer empty",
          bool(box_text) and "File: scan.xrdml" in box_text)

    # --- .rasx metadata (Rigaku MesurementConditions XML) --------------------
    rasx = os.path.join(_TMP, "scan.rasx")
    profile = "﻿" + "\n".join("%.2f\t%d\t1" % (2.0 + i * 0.02, 100 + i)
                                   for i in range(6))
    conditions = (
        '<?xml version="1.0"?><MeasurementConditions>'
        '<WavelengthKalpha1>1.540593</WavelengthKalpha1>'
        '<WavelengthKalpha2>1.544414</WavelengthKalpha2>'
        '<TargetName>Cu</TargetName>'
        '<Voltage>40</Voltage><Current>75</Current>'
        '<StartTime>2026-07-15T07:33:34Z</StartTime>'
        '<Speed>6.0000</Speed></MeasurementConditions>'
    )
    with zipfile.ZipFile(rasx, "w") as z:
        z.writestr("Data0/Profile0.txt", profile)
        z.writestr("Data0/MesurementConditions0.xml", conditions)  # Rigaku spelling

    rmd = parse_rasx_metadata(rasx)
    check("rasx wavelength Ka1 read (from the conditions XML)",
          abs(rmd.get("wavelength_ka1", 0) - 0.1540593) < 1e-8)
    check("rasx anode + kV + mA read",
          rmd.get("anode") == "Cu" and rmd.get("voltage_kv") == 40.0
          and rmd.get("current_ma") == 75.0)
    check("rasx scan date + speed read",
          rmd.get("scan_date", "").startswith("2026-07-15")
          and rmd.get("scan_speed_deg_min") == 6.0)
    rsrc = build_source_string(rasx, np.array([2.0, 2.02, 2.04, 2.06, 2.08]), rmd)
    for needle in ("X-ray tube: Cu, 40 kV, 75 mA", "Scan speed: 6", "0.15406"):
        check("rasx source lists %r" % needle, needle in rsrc)
    rimported = win.import_specimen_files([rasx])
    check("rasx import applies its Ka1 to the goniometer",
          rimported and abs(rimported[0].goniometer.wavelength - 0.1540593) < 1e-6)

    # --- .uxd metadata (Bruker DIFFRAC header, _KEY=VALUE) -------------------
    uxd = _write("scan.uxd", "\n".join([
        "; converted by XCH",
        "_FILEVERSION=2",
        "_GONIOMETER_RADIUS=217.500000",
        "_DATEMEASURED='20-Jul-2022 15:27:56'",
        "_WL_UNIT='A'",
        "_WL1=1.540600", "_WL2=1.544390", "_WLRATIO=0.500000",
        "_ANODE='Cu'", "_KV=40", "_MA=40",
        "_STEPTIME=32.000000", "_STEPSIZE=0.020000", "_START=5.000000",
        "_2THETACOUNTS",
        "5.00 100", "5.02 200", "5.04 300", "5.06 400", "5.08 500",
    ]))
    umd = parse_uxd_metadata(uxd)
    check("uxd _WL1 read as Ka1 (A->nm via _WL_UNIT)",
          abs(umd.get("wavelength_ka1", 0) - 0.15406) < 1e-8)
    check("uxd _WL2 read as Ka2", abs(umd.get("wavelength_ka2", 0) - 0.154439) < 1e-8)
    check("uxd anode + kV + mA read",
          umd.get("anode") == "Cu" and umd.get("voltage_kv") == 40.0
          and umd.get("current_ma") == 40.0)
    check("uxd _STEPTIME -> count time + date + radius",
          umd.get("count_time") == 32.0
          and umd.get("scan_date", "").startswith("20-Jul-2022")
          and umd.get("radius_mm") == 217.5)
    usrc = build_source_string(uxd, np.array([5.0, 5.02, 5.04, 5.06, 5.08]), umd)
    for needle in ("X-ray tube: Cu, 40 kV, 40 mA", "Count time: 32.00 s per step",
                   "Goniometer radius: 217.5 mm", "0.15406"):
        check("uxd source lists %r" % needle, needle in usrc)
    uimported = win.import_specimen_files([uxd])
    check("uxd import applies its Ka1 to the goniometer",
          uimported and abs(uimported[0].goniometer.wavelength - 0.15406) < 1e-6)

    # A plain-text import still gets a (base) source.
    imported2 = win.import_specimen_files([txt])
    check("text import still gets a base source",
          imported2 and "File: sample.txt" in imported2[0].source)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("--- import source / metadata verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
