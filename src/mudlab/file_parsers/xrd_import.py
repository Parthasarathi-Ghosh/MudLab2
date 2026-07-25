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
from mudlab.file_parsers.rasx_parser import parse_rasx
from mudlab.file_parsers.raw_parser import parse_raw
from mudlab.file_parsers.uxd_parser import parse_uxd
from mudlab.file_parsers.xrdml_parser import parse_xrdml

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
