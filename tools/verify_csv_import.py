#!/usr/bin/env python
"""Durable harness for the common CSV import/export + the CSV-import options
dialog, run head-less.

Covers:
  - file_parsers/csv_io: read_xy (auto + explicit delimiter/decimal/header),
    write_xy, sniff, preview, and the min_rows knob;
  - backward compat of the xy_parser facade (parse_xy/save_xy) and wld_file;
  - xrd_import.parse_pattern(options) + uses_csv_options;
  - the CsvImportDialog (sniff pre-fill, live options) and the import_pattern
    helper (vendor vs text routing, cancel, error handling).

The tolerant auto path on real instrument files is already guarded by
verify_xrd_import; this harness focuses on the new options behaviour.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_csv_import.py

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
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

# The error path pops a modal QMessageBox, which blocks forever head-less.
# Record the calls instead of showing them (as verify_data_op_dialogs does).
_boxes = []
for _name in ("warning", "critical", "information"):
    setattr(QMessageBox, _name, staticmethod(
        lambda parent, title, text, *a, _n=_name, **k: _boxes.append((_n, title, text))
    ))

from mudlab.csv_import_dialog import CsvImportDialog, import_pattern
from mudlab.file_parsers.csv_io import (
    CsvOptions, preview, read_xy, sniff, write_xy,
)
from mudlab.file_parsers.wld_file import load_wld
from mudlab.file_parsers.xy_parser import parse_xy, save_xy
from mudlab.file_parsers.xrd_import import parse_pattern, uses_csv_options

app = QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _tmp(name: str, content: str) -> str:
    path = os.path.join(tempfile.mkdtemp(), name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


# Common dialects.
_COMMA = _tmp("comma.csv", "2th,intensity\n10.0,100\n10.1,110\n10.2,95\n")
_EURO = _tmp("euro.csv", "2th;intensity\n10,0;100,5\n10,1;110,25\n10,2;95,0\n")
_TAB = _tmp("tab.txt", "10.0\t100\n10.1\t110\n10.2\t95\n")
_WS = _tmp("ws.xy", "# comment\n10.0 100\n10.1 110\n10.2 95\n")


# ----------------------------------------------------------------------
# csv_io: reading
# ----------------------------------------------------------------------
def check_read_auto():
    x, y = read_xy(_WS)  # auto, no options
    check("read_xy auto: whitespace + comment skipped",
          list(x) == [10.0, 10.1, 10.2] and list(y) == [100, 110, 95])
    x, y = read_xy(_COMMA)  # auto handles comma + text header
    check("read_xy auto: comma + text header skipped",
          list(x) == [10.0, 10.1, 10.2] and list(y) == [100, 110, 95])


def check_read_explicit():
    # European: semicolon delimiter, comma decimal, header row.
    opt = CsvOptions(delimiter=";", decimal=",", has_header=True)
    x, y = read_xy(_EURO, opt)
    check("read_xy explicit: European ;/, with header",
          np.allclose(x, [10.0, 10.1, 10.2]) and np.allclose(y, [100.5, 110.25, 95.0]))
    # Explicit comma with header skipped.
    opt = CsvOptions(delimiter=",", decimal=".", has_header=True)
    x, y = read_xy(_COMMA, opt)
    check("read_xy explicit: comma + has_header drops first row",
          list(x) == [10.0, 10.1, 10.2])
    # Wrong decimal makes the European file unreadable (proves decimal matters).
    try:
        read_xy(_EURO, CsvOptions(delimiter=";", decimal=".", has_header=True))
        check("read_xy explicit: wrong decimal fails to parse", False)
    except ValueError:
        check("read_xy explicit: wrong decimal fails to parse", True)


def check_explicit_desync_regression():
    """Bug A regression: a row whose second column fails to parse must be
    dropped whole, leaving x and y the same length (it used to append x before
    validating y, returning mismatched arrays)."""
    mixed = _tmp("mixed.csv", "10.0;100\n10.1;bad\n10.2;95\n")
    x, y = read_xy(mixed, CsvOptions(delimiter=";"))
    check("Bug A: malformed y-row skipped whole, x/y stay aligned",
          len(x) == len(y) == 2 and list(x) == [10.0, 10.2] and list(y) == [100.0, 95.0])
    # Space-aligned columns under an explicit Space separator: every second
    # field is empty, so all rows drop -> a clean ValueError, never a
    # mismatched (x longer than y) return.
    aligned = _tmp("aligned.xy", "10.0    100\n10.1    110\n10.2    95\n")
    try:
        rx, ry = read_xy(aligned, CsvOptions(delimiter=" "))
        ok = len(rx) == len(ry)  # if it returns at all, it must be aligned
    except ValueError:
        ok = True
    check("Bug A: space-aligned explicit never returns mismatched arrays", ok)


def check_footgun_b():
    """Footgun B: explicit 'Space' now collapses whitespace runs (so aligned
    columns parse), and the dialog forbids decimal == separator."""
    aligned = _tmp("aligned2.xy", "10.0    100\n10.1    110\n10.2    95\n")
    x, y = read_xy(aligned, CsvOptions(delimiter=" "))
    check("Footgun B: explicit Space collapses aligned columns",
          list(x) == [10.0, 10.1, 10.2] and list(y) == [100.0, 110.0, 95.0])

    # Comma file: the comma-decimal item is disabled from the start.
    dlg = CsvImportDialog(path=_COMMA)
    dec_model = dlg.ui.cmb_decimal.model()
    comma_row = next(i for i in range(dlg.ui.cmb_decimal.count())
                     if dlg.ui.cmb_decimal.itemData(i) == ",")
    check("Footgun B: comma-decimal disabled when separator is comma",
          not dec_model.item(comma_row).isEnabled()
          and dlg.options().decimal != dlg.options().delimiter)
    dlg.deleteLater()

    # European file starts with a comma decimal; switching the separator TO
    # comma must force the decimal off comma (never delimiter == decimal).
    dlg2 = CsvImportDialog(path=_EURO)
    check("Footgun B: European file starts with comma decimal",
          dlg2.options().decimal == ",")
    dlg2.ui.cmb_separator.setCurrentIndex(dlg2.ui.cmb_separator.findData(","))
    check("Footgun B: switching separator to comma forces decimal off comma",
          dlg2.options().delimiter == "," and dlg2.options().decimal == ".")
    dlg2.deleteLater()


def check_decimal_never_delimiter():
    """The decimal sign must NEVER be used to split columns, in any mode."""
    euro = _tmp("dnd.csv", "10,5;100,0\n10,6;110,25\n10,7;95,5\n")
    ex, ey = [10.5, 10.6, 10.7], [100.0, 110.25, 95.5]
    # Auto delimiter + comma decimal: the comma is a decimal, not a separator.
    x, y = read_xy(euro, CsvOptions(delimiter=None, decimal=","))
    check("decimal-not-delim: auto delimiter keeps comma as decimal",
          list(x) == ex and list(y) == ey)
    # Explicit semicolon + comma decimal.
    x, y = read_xy(euro, CsvOptions(delimiter=";", decimal=","))
    check("decimal-not-delim: explicit ';' + comma decimal",
          list(x) == ex and list(y) == ey)
    # Contradictory delimiter == decimal (both comma): the decimal wins, so it
    # still parses (comma is never treated as the separator).
    x, y = read_xy(euro, CsvOptions(delimiter=",", decimal=","))
    check("decimal-not-delim: delimiter==decimal falls back (decimal wins)",
          list(x) == ex and list(y) == ey)
    # A period decimal must STILL let comma separate (no over-correction).
    us = _tmp("us.csv", "10.0,100\n10.1,110\n")
    x, y = read_xy(us, CsvOptions(delimiter=None, decimal="."))
    check("decimal-not-delim: period decimal keeps comma as separator",
          list(x) == [10.0, 10.1] and list(y) == [100.0, 110.0])
    # sniff never suggests a delimiter equal to the decimal.
    ok = True
    for content in ("10,5;100,0\n10,6;110,0\n", "10.0,100\n10.1,110\n",
                    "10.0\t100\n10.1\t110\n", "10.0 100\n10.1 110\n"):
        o = sniff(_tmp("sn.csv", content))
        ok = ok and o.delimiter != o.decimal
    check("decimal-not-delim: sniff never returns delimiter == decimal", ok)


def check_text_formats_and_export():
    """The .xy/.txt/.dat/.tab formats share read_xy, so the decimal is never a
    delimiter for them either; .uxd treats comma as a decimal; and export never
    writes a file where the decimal equals the delimiter."""
    euro = "10,5;100,0\n10,6;110,25\n10,7;95,5\n"
    ex, ey = [10.5, 10.6, 10.7], [100.0, 110.25, 95.5]
    for ext in (".xy", ".txt", ".dat", ".tab"):
        p = _tmp("data" + ext, euro)
        x, y = parse_pattern(p, CsvOptions(delimiter=None, decimal=","))
        check("text %s: parse_pattern keeps comma as decimal, not delimiter" % ext,
              list(x) == ex and list(y) == ey)

    # .uxd is whitespace-delimited and converts comma -> decimal (never splits
    # on a comma). A marker-less numeric file loads via the fallback path.
    from mudlab.file_parsers.uxd_parser import parse_uxd
    up = _tmp("euro.uxd", "10,0   100\n10,1   110\n10,2   95\n")
    ux, uy = parse_uxd(up)
    check("uxd: comma is a decimal, whitespace the separator",
          list(ux) == [10.0, 10.1, 10.2])

    # Export: a comma decimal with a non-comma delimiter round-trips cleanly.
    out = os.path.join(tempfile.mkdtemp(), "eu.txt")
    write_xy(out, ex, ey, delimiter="\t", decimal=",", fmt="%.4f")
    rx, ry = read_xy(out, CsvOptions(delimiter="\t", decimal=","))
    check("export: comma-decimal + tab delimiter round-trips",
          np.allclose(rx, ex) and np.allclose(ry, ey))

    # Export refuses an ambiguous decimal == delimiter file.
    try:
        write_xy(out, ex, ey, delimiter=",", decimal=",")
        check("export: refuses decimal == delimiter", False)
    except ValueError:
        check("export: refuses decimal == delimiter", True)


def check_min_rows():
    one = _tmp("one.wld", "Wavelength, Factor\n0.15418,1.0\n")
    try:
        read_xy(one, min_rows=2)
        check("read_xy min_rows=2 rejects a single row", False)
    except ValueError:
        check("read_xy min_rows=2 rejects a single row", True)
    x, y = read_xy(one, min_rows=1)
    check("read_xy min_rows=1 accepts a single row",
          list(x) == [0.15418] and list(y) == [1.0])


# ----------------------------------------------------------------------
# csv_io: writing + round-trip
# ----------------------------------------------------------------------
def check_write_roundtrip():
    x = [10.0, 10.1, 10.2]
    y = [100.5, 110.25, 95.0]
    # European write, then read back with matching options.
    out = os.path.join(tempfile.mkdtemp(), "euro_out.csv")
    write_xy(out, x, y, delimiter=";", decimal=",", header="w;i", fmt="%.4f")
    with open(out, encoding="utf-8") as handle:
        first = handle.readline().strip()
        sample = handle.readline().strip()
    check("write_xy: header + ';' delimiter + ',' decimal",
          first == "w;i" and sample == "10,0000;100,5000")
    rx, ry = read_xy(out, CsvOptions(delimiter=";", decimal=",", has_header=True))
    check("write_xy/read_xy European round-trip", np.allclose(rx, x) and np.allclose(ry, y))


# ----------------------------------------------------------------------
# csv_io: sniff + preview
# ----------------------------------------------------------------------
def check_sniff():
    s_comma = sniff(_COMMA)
    check("sniff: comma file -> ','", s_comma.delimiter == "," and s_comma.decimal == ".")
    s_euro = sniff(_EURO)
    check("sniff: European -> ';' delimiter + ',' decimal",
          s_euro.delimiter == ";" and s_euro.decimal == ",")
    s_tab = sniff(_TAB)
    check("sniff: tab file -> tab, no header",
          s_tab.delimiter == "\t" and not s_tab.has_header)
    check("sniff: comma file detects the text header", sniff(_COMMA).has_header)


def check_preview():
    rows = preview(_EURO, CsvOptions(delimiter=";", decimal=",", has_header=True))
    # First row is the header (flagged not-ok), the rest parse.
    check("preview: header row flagged, data rows ok",
          rows[0][2] is False and rows[0][0] == "2th"
          and rows[1][2] is True and rows[1][0] == "10,0")


# ----------------------------------------------------------------------
# Backward compatibility
# ----------------------------------------------------------------------
def check_backcompat():
    # parse_xy facade == read_xy auto.
    a = parse_xy(_WS)
    b = read_xy(_WS)
    check("parse_xy facade == read_xy auto",
          np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1]))
    # save_xy still writes tab + %.6f.
    out = os.path.join(tempfile.mkdtemp(), "x.xy")
    save_xy(out, [10.0], [100.0])
    with open(out, encoding="utf-8") as handle:
        line = handle.readline().rstrip("\n")
    check("save_xy: unchanged tab + %.6f format", line == "10.000000\t100.000000")
    # wld single-line still loads (min_rows=1 path).
    one = _tmp("cu.wld", "Wavelength, Factor\n0.15418,1.0\n")
    check("wld single-line still loads", load_wld(one) == [(0.15418, 1.0)])


# ----------------------------------------------------------------------
# parse_pattern(options) + uses_csv_options
# ----------------------------------------------------------------------
def check_parse_pattern():
    # No options -> auto, unchanged.
    x, y = parse_pattern(_WS)
    check("parse_pattern auto unchanged", list(x) == [10.0, 10.1, 10.2])
    # Options honoured on the text path.
    x, y = parse_pattern(_EURO, CsvOptions(delimiter=";", decimal=",", has_header=True))
    check("parse_pattern honours options on text", np.allclose(y, [100.5, 110.25, 95.0]))
    # uses_csv_options: text yes, vendor no.
    check("uses_csv_options: .csv yes, .rasx/.raw/.uxd/.xrdml no",
          uses_csv_options("a.csv") and uses_csv_options("a.xy")
          and not uses_csv_options("a.rasx") and not uses_csv_options("a.raw")
          and not uses_csv_options("a.uxd") and not uses_csv_options("a.xrdml"))


# ----------------------------------------------------------------------
# Dialog
# ----------------------------------------------------------------------
def check_dialog():
    dlg = CsvImportDialog(path=_EURO)
    o = dlg.options()
    check("dialog: pre-fills from sniff (European)",
          o.delimiter == ";" and o.decimal == "," and o.has_header)
    check("dialog: preview populated", dlg.preview_model.rowCount() > 0)
    # Change the separator; options() reflects it and preview refreshes.
    idx = dlg.ui.cmb_separator.findData(",")
    dlg.ui.cmb_separator.setCurrentIndex(idx)
    check("dialog: changing separator updates options", dlg.options().delimiter == ",")
    dlg.deleteLater()


def check_get_options_cancel():
    orig = CsvImportDialog.exec
    CsvImportDialog.exec = lambda self: 0  # user cancels
    try:
        check("dialog get_options: None on cancel",
              CsvImportDialog.get_options(None, _COMMA) is None)
    finally:
        CsvImportDialog.exec = orig


# ----------------------------------------------------------------------
# import_pattern helper
# ----------------------------------------------------------------------
def check_import_helper():
    # Text file -> options dialog is consulted.
    orig_get = CsvImportDialog.get_options
    CsvImportDialog.get_options = staticmethod(
        lambda parent, path: CsvOptions(delimiter=";", decimal=",", has_header=True))
    try:
        res = import_pattern(None, path=_EURO)
    finally:
        CsvImportDialog.get_options = orig_get
    check("import_pattern: text path uses returned options",
          res is not None and np.allclose(res[1], [100.5, 110.25, 95.0]))

    # Cancel at options -> None.
    CsvImportDialog.get_options = staticmethod(lambda parent, path: None)
    try:
        check("import_pattern: None when options cancelled",
              import_pattern(None, path=_COMMA) is None)
    finally:
        CsvImportDialog.get_options = orig_get

    # File picker cancelled -> None (no path).
    orig_open = QFileDialog.getOpenFileName
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
    try:
        check("import_pattern: None when file picker cancelled",
              import_pattern(None) is None)
    finally:
        QFileDialog.getOpenFileName = orig_open

    # Unreadable file -> None (error shown via QMessageBox, not raised).
    bad = _tmp("bad.csv", "no numbers here\njust text\n")
    CsvImportDialog.get_options = staticmethod(lambda parent, path: CsvOptions())
    _boxes.clear()
    try:
        got = import_pattern(None, path=bad)
    finally:
        CsvImportDialog.get_options = orig_get
    check("import_pattern: None (no raise) on unreadable file", got is None)
    check("import_pattern: shows an error box on unreadable file", len(_boxes) == 1)


def main():
    check_read_auto()
    check_read_explicit()
    check_explicit_desync_regression()
    check_footgun_b()
    check_decimal_never_delimiter()
    check_text_formats_and_export()
    check_min_rows()
    check_write_roundtrip()
    check_sniff()
    check_preview()
    check_backcompat()
    check_parse_pattern()
    check_dialog()
    check_get_options_cancel()
    check_import_helper()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- CSV import/export verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
