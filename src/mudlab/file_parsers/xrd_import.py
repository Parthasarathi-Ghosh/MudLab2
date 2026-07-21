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

from mudlab.file_parsers.rasx_parser import parse_rasx
from mudlab.file_parsers.raw_parser import parse_raw
from mudlab.file_parsers.uxd_parser import parse_uxd
from mudlab.file_parsers.xrdml_parser import parse_xrdml
from mudlab.file_parsers.xy_parser import parse_xy

# Extension -> parser. ASCII XY family is the fallback for unknown extensions.
_PARSERS = {
    ".xrdml": parse_xrdml,
    ".rasx": parse_rasx,
    ".raw": parse_raw,
    ".uxd": parse_uxd,   # Bruker DIFFRAC ASCII (markers, CPS normalisation)
    ".xy": parse_xy,
    ".txt": parse_xy,
    ".csv": parse_xy,
    ".dat": parse_xy,
    ".tab": parse_xy,
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


def parse_pattern(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Read a measured pattern, choosing the parser from the file extension;
    an unrecognised extension is tried as ASCII XY. Returns (two_theta,
    intensity)."""
    ext = os.path.splitext(path)[1].lower()
    parser = _PARSERS.get(ext, parse_xy)
    return parser(path)
