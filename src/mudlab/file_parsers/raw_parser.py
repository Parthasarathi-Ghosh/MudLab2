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

Version 4 (`RAW4.00`, the DIFFRAC.SUITE format) is a different, segment-based
container; its reader (_parse_v4) is ported from xylib's bruker_raw.cpp (the
authoritative open-source RAW4 parser, github.com/wojdyr/xylib). Validated on a
real v4 file: a Locked-Coupled scan decodes to 2theta 5-80 deg with the quartz
101 peak at ~26.5 deg.

Rigaku also writes a *.raw (a different binary, `FI` magic) - `_parse_rigaku_fi`
reads it (reverse-engineered against the same samples' .rasx / .txt exports:
its float32 intensities match the .rasx exactly). So both Bruker (V1-V4) and
Rigaku *.raw are supported.

MudLab2 uses a single measured curve per raw-pattern phase, so this returns the
FIRST sample/range only.
"""

from __future__ import annotations

import struct
from io import SEEK_CUR, SEEK_SET, BytesIO

import numpy as np


def _read_version(f) -> str:
    f.seek(0, SEEK_SET)
    version = f.read(4).decode("utf-8", "replace")
    if version == "RAW ":
        return "RAW1"
    if version == "RAW2":
        return "RAW2"
    if version == "RAW4" and f.read(3).decode("utf-8", "replace") == ".00":
        return "RAW4"
    f.seek(4, SEEK_SET)
    if version == "RAW1" and f.read(3).decode("utf-8", "replace") == ".01":
        return "RAW3"
    raise ValueError(
        "Unrecognised .raw file (magic %r). Supported: Bruker RAW v1-4 and "
        "Rigaku (FI) .raw." % version
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


def _parse_v4(data: bytes) -> tuple[np.ndarray, np.ndarray]:
    """Bruker RAW4 (RAW4.00) reader, ported from xylib's bruker_raw.cpp
    load_version4. Layout: a 61-byte header, then global metadata segments
    (uint32 type, uint32 len; type 0/160 marks the start of the ranges), then
    range blocks. Each range's 160-byte primary header holds start_angle
    (double @+72), step_size (@+80), steps (uint32 @+88) and hdr_size
    (uint32 @+140); `hdr_size` bytes of sub-segments follow, then `steps`
    float32 intensities. Returns the first Locked/Unlocked-Coupled range's
    (2theta, intensity); x = start_angle + step_size * n."""
    n = len(data)
    pos = 61
    while True:
        if pos + 4 > n:
            raise ValueError("Truncated RAW4 file (no measurement ranges).")
        stype = struct.unpack_from("<I", data, pos)[0]; pos += 4
        if stype in (0, 160):
            break
        seg_len = struct.unpack_from("<I", data, pos)[0]; pos += 4
        if seg_len < 8:
            raise ValueError("Corrupt RAW4 metadata segment.")
        pos += seg_len - 8

    while stype in (0, 160):
        rs = pos - 4  # range start (the 4-byte marker we just read)
        if rs + 160 > n:
            break
        scan_type = data[rs + 32:rs + 56].split(b"\0")[0].decode("latin-1", "replace")
        start_angle = struct.unpack_from("<d", data, rs + 72)[0]
        step_size = struct.unpack_from("<d", data, rs + 80)[0]
        steps = struct.unpack_from("<I", data, rs + 88)[0]
        datum_size = struct.unpack_from("<I", data, rs + 136)[0]
        hdr_size = struct.unpack_from("<I", data, rs + 140)[0]
        data_off = rs + 160 + hdr_size
        if scan_type in ("Locked Coupled", "Unlocked Coupled"):
            if datum_size != 4:
                raise ValueError("Unsupported RAW4 datum size %d." % datum_size)
            if steps < 2 or data_off + steps * 4 > n:
                raise ValueError("Truncated RAW4 data block.")
            y = np.frombuffer(data, dtype="<f4", count=steps, offset=data_off)
            x = start_angle + step_size * np.arange(steps, dtype=float)
            return x, y.astype(float)
        # Skip a range type we do not read, and try the next.
        pos = data_off + datum_size * steps
        if pos + 4 > n:
            break
        stype = struct.unpack_from("<I", data, pos)[0]; pos += 4
    raise ValueError("No Locked/Unlocked-Coupled range in RAW4 file.")


# Rigaku 'FI' *.raw: the 2theta axis is three float32 (start, end, step) at this
# offset; the intensities are `count` float32 filling the file to EOF, where
# count = (end - start)/step + 1. Reverse-engineered against the same samples'
# .rasx export (the float32 values match it exactly).
_RIGAKU_MAGIC = b"FI\x00\x00"
_RIGAKU_AXIS_OFFSET = 0x0B92


def _parse_rigaku_fi(data: bytes) -> tuple[np.ndarray, np.ndarray]:
    n = len(data)
    if n < _RIGAKU_AXIS_OFFSET + 12:
        raise ValueError("Truncated Rigaku .raw file.")
    start, end, step = struct.unpack_from("<fff", data, _RIGAKU_AXIS_OFFSET)
    if not (0.0 <= start < end <= 180.0 and 0.0 < step < 10.0):
        raise ValueError(
            "Unrecognised Rigaku .raw header (start=%.4g end=%.4g step=%.4g)."
            % (start, end, step)
        )
    count = int(round((end - start) / step)) + 1
    data_start = n - count * 4  # the data fills the file to EOF
    if count < 2 or data_start < _RIGAKU_AXIS_OFFSET + 12:
        raise ValueError("Rigaku .raw data block does not line up.")
    y = np.frombuffer(data, dtype="<f4", count=count, offset=data_start)
    x = start + step * np.arange(count, dtype=float)
    return x, y.astype(float)


def parse_raw(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse a binary *.raw pattern; returns (two_theta, intensity) for its
    first range. Bruker RAW v1-3 intensity is counts-per-second, v4 and Rigaku
    are as stored (the raw-pattern phase scale is fit anyway)."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] == _RIGAKU_MAGIC:
        return _parse_rigaku_fi(data)

    f = BytesIO(data)
    version = _read_version(f)
    if version == "RAW4":
        return _parse_v4(data)
    twotheta_min, twotheta_step, count, data_start, count_time = _HEADERS[version](f)
    if count < 2:
        raise ValueError("No usable data in %r." % path)
    f.seek(data_start, SEEK_SET)
    counts = np.frombuffer(f.read(count * 4), dtype="<f4", count=count)
    x = twotheta_min + twotheta_step * np.arange(count, dtype=float)
    y = counts.astype(float) / (count_time or 1.0)
    return x, y


def _angstrom_to_nm(value):
    """Convert an Angstrom wavelength to nm, or None if it is not a plausible
    XRD wavelength (guards against a zero/garbage header field)."""
    if not value or value <= 0:
        return None
    nm = float(value) / 10.0
    return nm if 0.03 < nm < 0.4 else None  # ~0.3-4 Angstrom


def parse_raw_metadata(path: str) -> dict:
    """Best-effort metadata from a binary *.raw (for the specimen 'source'
    description). Bruker RAW1 exposes the per-step count time and the Kα1/Kα2
    wavelengths (Angstrom→nm); Bruker RAW3 exposes the per-step count time
    (header+192). RAW2 / RAW4 and Rigaku 'FI' .raw have no mapped metadata here.
    Returns any of: count_time (s), wavelength_ka1 / wavelength_ka2 (nm). Never
    raises."""
    md: dict = {}
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return md
    if data[:4] == _RIGAKU_MAGIC:
        return md  # Rigaku FI: axis-only, header not reverse-engineered

    f = BytesIO(data)
    try:
        version = _read_version(f)
        if version == "RAW1":
            f.seek(4, SEEK_SET)             # past the "RAW " magic
            f.read(4)                       # twotheta_count
            time_step, = struct.unpack("f", f.read(4))
            if time_step and time_step > 0:
                md["count_time"] = float(time_step)
            f.seek(60, SEEK_CUR)            # -> alpha1/alpha2 (as in _header_v1)
            a1, a2 = struct.unpack("ff", f.read(8))
            nm1, nm2 = _angstrom_to_nm(a1), _angstrom_to_nm(a2)
            if nm1:
                md["wavelength_ka1"] = nm1
            if nm2:
                md["wavelength_ka2"] = nm2
        elif version == "RAW3":
            f.seek(712 + 192, SEEK_SET)     # per-step count time (header+192)
            count_time, = struct.unpack("f", f.read(4))
            if count_time and 0 < count_time < 1e6:
                md["count_time"] = float(count_time)
        # RAW2 / RAW4: metadata offsets not mapped -> nothing.
    except (struct.error, ValueError):
        return md
    return md
