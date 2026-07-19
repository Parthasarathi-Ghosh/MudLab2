"""Bruker/Siemens binary *.RAW pattern parser (2θ, intensity).

Ported from old mudlab's BrkRAWParser (file_parsers/xrd_parsers/brk_raw_parser.
py), which fixed several bugs in PyXRD's version - so this follows OLD MUDLAB,
not PyXRD:
  - RAW3 (`RAW1.01`) is detected by decoding the version bytes (PyXRD compared
    `str(f.read(3))` == ".01", which never matched, so v3 files misparsed);
  - RAW3's per-step counting time is a 4-byte float at header+192 (PyXRD read
    an 8-byte double there -> garbage -> broke normalisation);
  - intensities are normalised to counts-per-second (y / count_time), matching
    the CPI / XRDML parsers (PyXRD returned raw counts);
  - x[n] = twotheta_min + twotheta_step * n (PyXRD used n + 0.5).

MudLab2 uses a single measured curve per raw-pattern phase, so this returns the
FIRST sample/range only (all the real files here hold one). Supports V1/V2/V3.
"""

from __future__ import annotations

import struct
from io import SEEK_CUR, SEEK_SET

import numpy as np


def _read_version(f) -> str:
    f.seek(0, SEEK_SET)
    version = f.read(4).decode("utf-8", "replace")
    if version == "RAW ":
        return "RAW1"
    if version == "RAW2":
        return "RAW2"
    if version == "RAW1" and f.read(3).decode("utf-8", "replace") == ".01":
        return "RAW3"
    raise ValueError(
        "Unsupported .raw file (magic %r). Only Bruker RAW versions 1-3 are "
        "read so far; Bruker RAW4 and non-Bruker vendor .raw files are not "
        "supported yet." % version
    )


def _header_v1(f) -> tuple[float, float, int, int, float]:
    # Cursor is just past the 4-byte "RAW " marker.
    twotheta_count = int(struct.unpack("I", f.read(4))[0])
    # time_step, twotheta_step, scan_mode:
    _time_step, twotheta_step, _scan_mode = struct.unpack("fff", f.read(12))
    f.seek(4, SEEK_CUR)                      # skip 4
    twotheta_min, = struct.unpack("f", f.read(4))
    f.seek(12, SEEK_CUR)                     # theta/khi/phi start (eulerian)
    f.read(32)                              # sample name
    struct.unpack("ff", f.read(8))          # alpha1, alpha2
    f.seek(72, SEEK_CUR)
    struct.unpack("I", f.read(4))            # isfollowed
    data_start = f.tell()
    return twotheta_min, twotheta_step, twotheta_count, data_start, 1.0


def _header_v2(f) -> tuple[float, float, int, int, float]:
    # RAW2: number of ranges then a fixed header; first range header at 256.
    header_start = 256
    f.seek(header_start, SEEK_SET)
    _header_length, twotheta_count = struct.unpack("HH", f.read(4))
    data_start = header_start + _header_length
    f.seek(header_start + 12, SEEK_SET)
    twotheta_step, twotheta_min = struct.unpack("ff", f.read(8))
    return twotheta_min, twotheta_step, int(twotheta_count), data_start, 1.0


def _header_v3(f) -> tuple[float, float, int, int, float]:
    # RAW3 (DIFFRAC plus): per-range headers begin at 712, each 304 bytes.
    header_start = 712
    f.seek(header_start + 0, SEEK_SET)
    header_length, = struct.unpack("I", f.read(4))
    if header_length != 304:
        raise ValueError("Invalid Bruker RAW3 header length %d." % header_length)
    f.seek(header_start + 4, SEEK_SET)
    twotheta_count, = struct.unpack("I", f.read(4))
    f.seek(header_start + 8, SEEK_SET)
    _theta_min, twotheta_min = struct.unpack("dd", f.read(16))
    f.seek(header_start + 176, SEEK_SET)
    twotheta_step, = struct.unpack("d", f.read(8))
    # Per-step counting time is a 4-byte float here (old mudlab's fix).
    f.seek(header_start + 192, SEEK_SET)
    count_time, = struct.unpack("f", f.read(4))
    f.seek(header_start + 256, SEEK_SET)
    supp_headers_size, = struct.unpack("I", f.read(4))
    data_start = header_start + header_length + supp_headers_size
    return (float(twotheta_min), float(twotheta_step), int(twotheta_count),
            data_start, float(count_time) or 1.0)


_HEADERS = {"RAW1": _header_v1, "RAW2": _header_v2, "RAW3": _header_v3}


def parse_raw(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse a Bruker/Siemens binary *.RAW file; returns (two_theta, intensity)
    for its first range. Intensity is counts-per-second."""
    with open(path, "rb") as f:
        version = _read_version(f)
        twotheta_min, twotheta_step, count, data_start, count_time = (
            _HEADERS[version](f)
        )
        if count < 2:
            raise ValueError("No usable data in %r." % path)
        f.seek(data_start, SEEK_SET)
        counts = np.frombuffer(f.read(count * 4), dtype="<f4", count=count)

    x = twotheta_min + twotheta_step * np.arange(count, dtype=float)
    y = counts.astype(float) / (count_time or 1.0)
    return x, y
