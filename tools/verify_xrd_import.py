#!/usr/bin/env python
"""Durable harness for the measured-pattern import parsers (raw-pattern phase
batch 3), run head-less.

Covers the SUPPORTED formats with deterministic synthetic fixtures:
  - ASCII XY (.xy/.txt): whitespace/comma columns, a UTF-8 BOM, header lines
    and an extra background column pair are all tolerated (first two columns);
  - PANalytical .xrdml: start/end + linspace 2theta, intensities normalised to
    counts-per-second by <commonCountingTime>;
  - Rigaku .rasx: the ZIP's Data0/Profile0.txt profile;
  - Bruker .uxd ASCII: paired / single-column layouts + CPS normalisation;
  - Bruker binary .raw v1 (RAW1) and v4 (RAW4, ported from xylib);
  - Rigaku binary .raw ('FI' magic, reverse-engineered against the .rasx);
  - the extension dispatcher (xrd_import.parse_pattern);
  - an unknown `.raw` magic fails with a clear error;
  - EXPORT: save_pattern writes ASCII XY / Bruker UXD (non-proprietary only)
    and the files round-trip back through the importer.

Where the real test files are present (~/Downloads/Phraser tests), it also
cross-checks the real .xrdml / .rasx / .txt and confirms the .rasx and .txt of
the same sample share an identical 2theta grid. That section skips if the files
are absent (they are the user's private data, never committed).

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_xrd_import.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import struct
import sys
import tempfile
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402

from mudlab.file_parsers.raw_parser import parse_raw  # noqa: E402
from mudlab.file_parsers.rasx_parser import parse_rasx  # noqa: E402
from mudlab.file_parsers.uxd_parser import parse_uxd  # noqa: E402
from mudlab.file_parsers.xrd_export import EXPORT_FILTERS, save_pattern  # noqa: E402
from mudlab.file_parsers.xrd_import import parse_pattern  # noqa: E402
from mudlab.file_parsers.xrdml_parser import parse_xrdml  # noqa: E402
from mudlab.file_parsers.xy_parser import parse_xy  # noqa: E402


def _write(dirpath, name, text, encoding="utf-8"):
    p = os.path.join(dirpath, name)
    with open(p, "w", encoding=encoding, newline="") as fh:
        fh.write(text)
    return p


def _raw1_bytes(tmin, step, counts):
    """A synthetic Bruker RAW1 file matching the reader's byte offsets."""
    n = len(counts)
    return (b"RAW "
            + struct.pack("I", n)
            + struct.pack("fff", 1.0, step, 0.0)   # time_step, step, scan_mode
            + b"\0" * 4
            + struct.pack("f", tmin)
            + b"\0" * 12
            + b"synthetic".ljust(32, b"\0")
            + struct.pack("ff", 1.5406, 1.5444)
            + b"\0" * 72
            + struct.pack("I", 0)                  # isfollowed = 0
            + np.asarray(counts, dtype="<f4").tobytes())


def _raw4_bytes(start, step, ys):
    """A synthetic Bruker RAW4 file: 61-byte header, an immediate range marker
    (type 160), one Locked-Coupled range primary header, then float32 data.
    Offsets match xylib's load_version4."""
    steps = len(ys)
    buf = bytearray(61 + 160 + steps * 4)
    buf[0:7] = b"RAW4.00"
    rs = 61
    struct.pack_into("<I", buf, rs, 160)                 # range marker (+0)
    buf[rs + 32:rs + 32 + 14] = b"Locked Coupled"        # SCAN_TYPE (+32)
    struct.pack_into("<d", buf, rs + 72, start)          # start_angle (+72)
    struct.pack_into("<d", buf, rs + 80, step)           # step_size (+80)
    struct.pack_into("<I", buf, rs + 88, steps)          # steps (+88)
    struct.pack_into("<I", buf, rs + 136, 4)             # datum_size (+136)
    struct.pack_into("<I", buf, rs + 140, 0)             # hdr_size (+140)
    struct.pack_into("<%df" % steps, buf, rs + 160, *ys)  # data (+160)
    return bytes(buf)


def _rigaku_fi_bytes(start, end, step, ys):
    """A synthetic Rigaku 'FI' .raw: magic, the (start, end, step) float32 axis
    at offset 0x0B92, and float32 data filling the file to EOF."""
    count = len(ys)
    header = 2976  # >= 0x0B92 + 12
    buf = bytearray(header + count * 4)
    buf[0:4] = b"FI\x00\x00"
    struct.pack_into("<fff", buf, 0x0B92, start, end, step)
    struct.pack_into("<%df" % count, buf, header, *ys)
    return bytes(buf)


def check_ascii(tmp, results):
    # BOM + a title line + a units line + 4 columns (sample pair + BG pair).
    txt = ("﻿Sample\t\tBG\t\n"
           "2θ, °\tIntensity, cps\t2θ, °\tIntensity, cps\n"
           "2\t1000\t2\t50\n"
           "2.02\t1100\t2.02\t60\n"
           "2.04\t1200\t2.04\t70\n")
    p = _write(tmp, "sample.txt", txt, encoding="utf-8-sig")
    x, y = parse_xy(p)
    results.append(("ascii: BOM + headers + BG column ignored -> first two cols",
                    np.allclose(x, [2.0, 2.02, 2.04])
                    and np.allclose(y, [1000, 1100, 1200])))


def check_xrdml(tmp, results):
    xml = (
        '<?xml version="1.0"?>\n'
        '<xrdMeasurements xmlns="http://www.xrdml.com/XRDMeasurement/1.5">'
        '<xrdMeasurement><scan><dataPoints>'
        '<positions axis="2Theta">'
        '<startPosition>10</startPosition><endPosition>10.4</endPosition>'
        '</positions>'
        '<commonCountingTime>2</commonCountingTime>'
        '<intensities unit="counts">100 200 300 400 500</intensities>'
        '</dataPoints></scan></xrdMeasurement></xrdMeasurements>'
    )
    p = _write(tmp, "scan.xrdml", xml)
    x, y = parse_xrdml(p)
    results.append(("xrdml: start/end -> linspace 2theta",
                    np.allclose(x, [10.0, 10.1, 10.2, 10.3, 10.4])))
    results.append(("xrdml: counts normalised to CPS by commonCountingTime",
                    np.allclose(y, [50, 100, 150, 200, 250])))
    # An aborted scan is skipped in favour of the completed one.
    xml2 = xml.replace('<scan>', '<scan status="Aborted"><dataPoints>'
                       '<positions axis="2Theta"><startPosition>0</startPosition>'
                       '<endPosition>1</endPosition></positions>'
                       '<intensities>9 9</intensities></dataPoints></scan><scan>')
    p2 = _write(tmp, "aborted.xrdml", xml2)
    x2, _ = parse_xrdml(p2)
    results.append(("xrdml: aborted scan skipped", np.allclose(x2[0], 10.0)))


def check_rasx(tmp, results):
    profile = ("﻿2.0000\t1000.0\t1\n"
               "2.0200\t1100.0\t1\n"
               "2.0400\t1200.0\t1\n")
    p = os.path.join(tmp, "scan.rasx")
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("root.xml", "<root/>")
        z.writestr("Data0/Profile0.txt", profile.encode("utf-8-sig"))
    x, y = parse_rasx(p)
    results.append(("rasx: reads Data0/Profile0.txt first two columns",
                    np.allclose(x, [2.0, 2.02, 2.04])
                    and np.allclose(y, [1000, 1100, 1200])))


def check_raw(tmp, results):
    p = os.path.join(tmp, "scan.raw")
    with open(p, "wb") as fh:
        fh.write(_raw1_bytes(5.0, 0.02, [10, 20, 40, 30, 15, 5]))
    x, y = parse_raw(p)
    results.append(("raw: Bruker RAW1 x = min + step*n, y = counts",
                    np.allclose(x, 5.0 + 0.02 * np.arange(6))
                    and np.allclose(y, [10, 20, 40, 30, 15, 5])))


def check_raw4(tmp, results):
    p = os.path.join(tmp, "scan4.raw")
    with open(p, "wb") as fh:
        fh.write(_raw4_bytes(10.0, 0.02, [100, 250, 900, 250, 100]))
    x, y = parse_raw(p)
    results.append(("raw: Bruker RAW4 (Locked Coupled) x = start + step*n, y",
                    np.allclose(x, 10.0 + 0.02 * np.arange(5))
                    and np.allclose(y, [100, 250, 900, 250, 100])))


def check_rigaku(tmp, results):
    p = os.path.join(tmp, "rigaku.raw")
    with open(p, "wb") as fh:
        fh.write(_rigaku_fi_bytes(10.0, 12.0, 0.5, [100, 200, 900, 200, 100]))
    x, y = parse_raw(p)
    results.append(("raw: Rigaku 'FI' axis from (start,end,step) + float32 data",
                    np.allclose(x, [10.0, 10.5, 11.0, 11.5, 12.0])
                    and np.allclose(y, [100, 200, 900, 200, 100])))


def check_uxd(tmp, results):
    # Paired "2theta counts", normalised to CPS by _STEPTIME.
    paired = ("; a comment\n_SAMPLE='x'\n_STEPTIME=2.0\n_START=5\n_STEPSIZE=0.02\n"
              "_2THETACOUNTS\n10 320\n10.02 640\n10.04 160\n")
    p = _write(tmp, "paired.uxd", paired)
    x, y = parse_uxd(p)
    results.append(("uxd: _2THETACOUNTS paired, counts/steptime -> CPS",
                    np.allclose(x, [10, 10.02, 10.04])
                    and np.allclose(y, [160, 320, 80])))
    # Single-column counts: 2theta rebuilt from _START / _STEPSIZE.
    single = "_STEPTIME=1.0\n_START=5.0\n_STEPSIZE=0.1\n_COUNTS\n100\n200\n300\n"
    x2, y2 = parse_uxd(_write(tmp, "single.uxd", single))
    results.append(("uxd: _COUNTS single column, 2theta from _START/_STEPSIZE",
                    np.allclose(x2, [5.0, 5.1, 5.2])
                    and np.allclose(y2, [100, 200, 300])))
    # A *CPS marker means values are already CPS (no steptime division).
    cps = "_STEPTIME=8.0\n_2THETACPS\n20 50\n20.02 75\n"
    _, y3 = parse_uxd(_write(tmp, "cps.uxd", cps))
    results.append(("uxd: _2THETACPS already CPS (no steptime division)",
                    np.allclose(y3, [50, 75])))
    # The dispatcher routes .uxd to parse_uxd (CPS), not the generic xy_parser.
    _, yd = parse_pattern(p)
    results.append(("uxd: dispatcher routes .uxd -> parse_uxd",
                    np.allclose(yd, [160, 320, 80])))


def check_export(tmp, results):
    x = np.round(2.0 + 0.02 * np.arange(50), 4)
    y = np.round(100.0 + np.arange(50) * 3.0, 3)
    for ext in (".xy", ".uxd", ".dat"):
        p = os.path.join(tmp, "export" + ext)
        save_pattern(p, x, y)
        rx, ry = parse_pattern(p)
        results.append(("export: %s round-trips (save_pattern -> parse_pattern)" % ext,
                        rx.size == x.size
                        and np.allclose(rx, x, atol=1e-4)
                        and np.allclose(ry, y, atol=1e-2)))
    # The exported .uxd is a real Bruker UXD (paired _2THETACOUNTS layout).
    ux, uy = parse_uxd(os.path.join(tmp, "export.uxd"))
    results.append(("export: .uxd is a valid Bruker UXD",
                    ux.size == x.size and np.allclose(uy, y, atol=1e-2)))
    # Only non-proprietary text formats are offered for export.
    results.append(("export: filters offer ASCII XY + UXD only (no binary/vendor)",
                    "*.uxd" in EXPORT_FILTERS and "*.xy" in EXPORT_FILTERS
                    and "*.raw" not in EXPORT_FILTERS
                    and "*.rasx" not in EXPORT_FILTERS
                    and "*.xrdml" not in EXPORT_FILTERS))


def check_unknown_magic(tmp, results):
    # Bruker (RAW*) and Rigaku (FI) are read; any other .raw magic is rejected
    # with a clear error rather than mis-parsed.
    p = os.path.join(tmp, "unknown.raw")
    with open(p, "wb") as fh:
        fh.write(b"XYZ?" + b"\0" * 64)
    try:
        parse_raw(p)
        ok = False
    except ValueError as e:
        ok = "unrecognised" in str(e).lower()
    results.append(("raw: an unknown .raw magic is rejected clearly", ok))


def check_dispatch(tmp, results):
    # parse_pattern routes by extension; an unknown extension falls back to XY.
    xy = _write(tmp, "plain.abc", "3 111\n3.1 222\n")
    x, y = parse_pattern(xy)
    results.append(("dispatch: unknown extension -> ASCII XY fallback",
                    np.allclose(x, [3.0, 3.1]) and np.allclose(y, [111, 222])))
    p = os.path.join(tmp, "scan.raw")
    with open(p, "wb") as fh:
        fh.write(_raw1_bytes(1.0, 0.1, [1, 2, 3]))
    xr, _ = parse_pattern(p)
    results.append(("dispatch: .raw -> Bruker parser",
                    np.allclose(xr, [1.0, 1.1, 1.2])))


def check_real_files(results):
    """Opportunistic: real vendor files if the user's test folder is present."""
    root = os.path.join(os.path.expanduser("~"), "Downloads", "Phraser tests")
    if not os.path.isdir(root):
        print("(real test files absent; skipping the real-file cross-check)")
        return
    xrdml = os.path.join(root, "1.xrdml")
    if os.path.isfile(xrdml):
        x, y = parse_pattern(xrdml)
        results.append(("real: 1.xrdml parses (>1000 pts, ascending 2theta)",
                        x.size > 1000 and np.all(np.diff(x) > 0)))
    rasx = os.path.join(root, "15_07_26", "AT_509_1.rasx")
    txt = os.path.join(root, "15_07_26", "AT_509_1.txt")
    if os.path.isfile(rasx) and os.path.isfile(txt):
        xr, _ = parse_pattern(rasx)
        xt, _ = parse_pattern(txt)
        m = min(xr.size, xt.size)
        results.append(("real: .rasx and .txt of one sample share the 2theta grid",
                        xr.size == xt.size
                        and np.allclose(xr[:m], xt[:m], atol=1e-9)))
    # Real Rigaku 'FI' .raw vs the same sample's .rasx: intensities are the same
    # float32 values; the 2theta axis matches to the float32-step rounding.
    rigaku_raw = os.path.join(root, "15_07_26_RawFile", "AT_509_1.raw")
    if os.path.isfile(rigaku_raw) and os.path.isfile(rasx):
        xg, yg = parse_pattern(rigaku_raw)
        xr, yr = parse_pattern(rasx)
        results.append(("real: Rigaku .raw matches its .rasx (intensity exact)",
                        xg.size == xr.size
                        and np.allclose(yg, yr, atol=1e-3)
                        and np.allclose(xg, xr, atol=1e-3)))
    # Real Bruker RAW4 (Dh232): the xylib-based decode is a Locked-Coupled
    # 5..80 deg scan, 3649 pts, quartz 101 peak at ~26.5 deg.
    raw4 = os.path.join(root, "Dh232.raw")
    if os.path.isfile(raw4):
        x, y = parse_pattern(raw4)
        results.append(("real: Dh232 RAW4 decodes (3649 pts, 5..80, quartz peak ~26.5)",
                        x.size == 3649
                        and abs(x[0] - 5.0) < 1e-6 and abs(x[-1] - 80.004) < 1e-2
                        and abs(float(x[int(np.argmax(y))]) - 26.53) < 0.1))
        # Cross-check against the Bruker UXD ASCII export (a processed +
        # truncated 5..60 derivative, so not byte-exact): the 2theta axis must
        # match exactly and the quartz peak must land within ~1 step.
        uxd = os.path.join(root, "dh232.UXD")
        if os.path.isfile(uxd):
            xu, yu = parse_pattern(uxd)
            step = x[1] - x[0]
            # The UXD prints 2theta rounded to 4 decimals, so its step differs
            # from the exact RAW4 step by ~4e-5; allow the rounding.
            results.append(("real: RAW4 axis matches the UXD (start + step)",
                            abs(x[0] - xu[0]) < 1e-4
                            and abs(step - (xu[1] - xu[0])) < 1e-3))
            results.append(("real: RAW4 & UXD quartz peak agree within 1 step",
                            abs(float(x[int(np.argmax(y))])
                                - float(xu[int(np.argmax(yu))])) <= 1.5 * step))


def main():
    results = []
    print("=" * 72)
    print("XRD import parsers - xrdml / rasx / ascii / Bruker RAW1-4 / Rigaku")
    print("=" * 72)
    with tempfile.TemporaryDirectory(prefix="mudlab_xrd_") as tmp:
        check_ascii(tmp, results)
        check_xrdml(tmp, results)
        check_rasx(tmp, results)
        check_uxd(tmp, results)
        check_raw(tmp, results)
        check_raw4(tmp, results)
        check_rigaku(tmp, results)
        check_unknown_magic(tmp, results)
        check_dispatch(tmp, results)
        check_export(tmp, results)
    check_real_files(results)

    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("XRD-import harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
