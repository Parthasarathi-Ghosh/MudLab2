#!/usr/bin/env python
"""Durable harness for the measured-pattern import parsers (raw-pattern phase
batch 3), run head-less.

Covers the SUPPORTED formats with deterministic synthetic fixtures:
  - ASCII XY (.xy/.txt): whitespace/comma columns, a UTF-8 BOM, header lines
    and an extra background column pair are all tolerated (first two columns);
  - PANalytical .xrdml: start/end + linspace 2theta, intensities normalised to
    counts-per-second by <commonCountingTime>;
  - Rigaku .rasx: the ZIP's Data0/Profile0.txt profile;
  - Bruker binary .raw v1 (RAW1);
  - the extension dispatcher (xrd_import.parse_pattern);
  - the DEFERRED formats fail with a clear error (Bruker RAW4, non-Bruker `FI`).

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


def check_deferred(tmp, results):
    for magic, tag in ((b"RAW4.00\0", "Bruker RAW4"), (b"FI\0\0" + b"\0" * 8, "FI")):
        p = os.path.join(tmp, tag.replace(" ", "_") + ".raw")
        with open(p, "wb") as fh:
            fh.write(magic + b"\0" * 64)
        try:
            parse_raw(p)
            ok = False
        except ValueError as e:
            ok = "not supported" in str(e).lower()
        results.append(("deferred: %s .raw rejected with a clear error" % tag, ok))


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


def main():
    results = []
    print("=" * 72)
    print("XRD import parsers - xrdml / rasx / ascii(+BOM) / Bruker RAW1-3")
    print("=" * 72)
    with tempfile.TemporaryDirectory(prefix="mudlab_xrd_") as tmp:
        check_ascii(tmp, results)
        check_xrdml(tmp, results)
        check_rasx(tmp, results)
        check_raw(tmp, results)
        check_deferred(tmp, results)
        check_dispatch(tmp, results)
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
