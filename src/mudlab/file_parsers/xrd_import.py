"""Import a measured XRD pattern from a data file, dispatching on extension.

One entry point (`parse_pattern`) over the individual format parsers, plus the
matching Qt file-dialog filter. Used by the raw-pattern phase editor; the
specimen data import can adopt it too.

Formats: plain ASCII XY (`.xy/.txt/.csv/.dat/.tab`, via xy_parser, BOM-
tolerant), Bruker DIFFRAC `.uxd` (ASCII with markers + CPS normalisation),
PANalytical `.xrdml`, Rigaku `.rasx`, and binary `.raw` - both Bruker (versions
1-4; v4 ported from xylib) and Rigaku (`FI` magic, reverse-engineered against
the `.rasx`). Not yet ported: the other PyXRD/old-mudlab formats (`.cpi`, `.rd`,
`.brml`).
"""

from __future__ import annotations

import os

import numpy as np

from mudlab.file_parsers.csv_io import CsvOptions, read_xy
from mudlab.file_parsers.rasx_parser import parse_rasx, parse_rasx_metadata
from mudlab.file_parsers.raw_parser import parse_raw
from mudlab.file_parsers.uxd_parser import parse_uxd, parse_uxd_metadata
from mudlab.file_parsers.xrdml_parser import parse_xrdml, parse_xrdml_metadata

# Vendor/binary formats with a fixed layout. Everything else (ASCII XY family
# and unknown extensions) is read as delimited text via the common CSV reader,
# so the CSV-import options apply to it.
_VENDOR_PARSERS = {
    ".xrdml": parse_xrdml,
    ".rasx": parse_rasx,
    ".raw": parse_raw,
    ".uxd": parse_uxd,   # Bruker DIFFRAC ASCII (markers, CPS normalisation)
}

#: Qt getOpenFileName filter offering every supported format.
PATTERN_FILTERS = (
    "XRD patterns (*.xy *.txt *.csv *.dat *.tab *.uxd *.xrdml *.rasx *.raw);;"
    "ASCII XY (*.xy *.txt *.csv *.dat *.tab *.uxd);;"
    "PANalytical XRDML (*.xrdml);;"
    "Rigaku RASX (*.rasx);;"
    "Bruker / Rigaku RAW (*.raw);;"
    "All files (*.*)"
)


def uses_csv_options(path: str) -> bool:
    """True when `path` is read as delimited text (so the CSV-import options
    apply); False for the vendor/binary formats, which have a fixed layout."""
    return os.path.splitext(path)[1].lower() not in _VENDOR_PARSERS


def parse_pattern(
    path: str, options: "CsvOptions | None" = None
) -> tuple[np.ndarray, np.ndarray]:
    """Read a measured pattern, choosing the parser from the file extension; an
    unrecognised extension is read as delimited text. `options` (a
    :class:`CsvOptions`) applies only to the text path; vendor formats ignore
    it. Returns (two_theta, intensity)."""
    parser = _VENDOR_PARSERS.get(os.path.splitext(path)[1].lower())
    if parser is not None:
        return parser(path)
    return read_xy(path, options)


# Per-format metadata readers for the specimen "source" description (best-effort;
# formats without one contribute just the file name + 2theta range built from the
# data). .xrdml / .rasx / .uxd are read; .raw metadata is a follow-up.
_VENDOR_METADATA = {
    ".xrdml": parse_xrdml_metadata,
    ".rasx": parse_rasx_metadata,
    ".uxd": parse_uxd_metadata,
}


def parse_pattern_metadata(path: str) -> dict:
    """Best-effort file metadata (wavelength, count time, sample, ...) for the
    source description. Returns {} for formats without a metadata reader, and
    never raises - the import must not fail over descriptive metadata."""
    reader = _VENDOR_METADATA.get(os.path.splitext(path)[1].lower())
    if reader is None:
        return {}
    try:
        return reader(path) or {}
    except Exception:  # noqa: BLE001 - metadata is purely descriptive
        return {}


def build_source_string(path: str, x, metadata: "dict | None" = None) -> str:
    """The specimen 'source' text for an imported pattern (old app's
    _build_source_string): the file name and the 2theta range/step/points read
    from the data, plus any wavelength / count-time / sample metadata the file
    provided. `x` is the 2theta axis; `metadata` comes from
    `parse_pattern_metadata`."""
    metadata = metadata or {}
    parts = ["File: %s" % os.path.basename(path)]

    x = np.asarray(x, dtype=float)
    if x.size >= 2:
        step = float(np.median(np.abs(np.diff(x))))
        parts.append("2θ: %.4f° – %.4f°   step: %.4f°   (%d points)"
                     % (float(np.min(x)), float(np.max(x)), step, x.size))
    elif x.size == 1:
        parts.append("2θ: %.4f°   (1 point)" % float(x[0]))

    ct = metadata.get("count_time")
    if ct is not None and ct != 1.0:
        parts.append("Count time: %.2f s per step" % ct)

    speed = metadata.get("scan_speed_deg_min")
    if speed:
        parts.append("Scan speed: %g °/min" % speed)

    name, sid = metadata.get("sample_name"), metadata.get("sample_id")
    if name or sid:
        line = "Sample: %s" % (name or "")
        if sid:
            line += " (id: %s)" % sid
        parts.append(line.strip())

    date = metadata.get("scan_date")
    if date:
        parts.append("Scanned: %s" % date)

    ka1, ka2 = metadata.get("wavelength_ka1"), metadata.get("wavelength_ka2")
    if ka1:
        parts.append("Wavelength Kα1: %.5f nm (%.4f Å)  (applied to goniometer)"
                     % (ka1, ka1 * 10.0))
        if ka2:
            parts.append("Wavelength Kα2: %.5f nm (%.4f Å)" % (ka2, ka2 * 10.0))

    tube = []
    if metadata.get("anode"):
        tube.append(str(metadata["anode"]))
    if metadata.get("voltage_kv"):
        tube.append("%g kV" % metadata["voltage_kv"])
    if metadata.get("current_ma"):
        tube.append("%g mA" % metadata["current_ma"])
    if tube:
        parts.append("X-ray tube: %s" % ", ".join(tube))

    radius = metadata.get("radius_mm")
    if radius:
        parts.append("Goniometer radius: %.1f mm (from file)" % radius)

    return "\n".join(parts)
