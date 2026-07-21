"""Export a measured/calculated pattern to a data file, dispatching on extension.

The write-side counterpart of `xrd_import`: one entry point (`save_pattern`)
over the individual writers, plus the matching Qt save-dialog filter.

Only NON-proprietary text formats are offered - ASCII XY (`.xy/.txt/.csv/.dat/
.tab`) and Bruker DIFFRAC `.uxd`. The binary/vendor formats we can READ (Bruker
/ Rigaku `.raw`, Rigaku `.rasx`, PANalytical `.xrdml`) are proprietary container
formats and are intentionally not offered for export; a `.uxd` (Bruker ASCII) or
`.xy` file carries the same pattern in an open, widely-read form.
"""

from __future__ import annotations

import os

import numpy as np

from mudlab.file_parsers.uxd_parser import save_uxd
from mudlab.file_parsers.xy_parser import save_xy

# Extension -> writer. ASCII XY is the fallback for an unknown/blank extension.
_WRITERS = {
    ".uxd": save_uxd,
    ".xy": save_xy,
    ".txt": save_xy,
    ".csv": save_xy,
    ".dat": save_xy,
    ".tab": save_xy,
}

#: Qt getSaveFileName filter (ASCII XY default, then Bruker UXD).
EXPORT_FILTERS = (
    "ASCII XY (*.xy *.txt *.csv *.dat *.tab);;"
    "Bruker UXD (*.uxd);;"
    "All files (*.*)"
)


def save_pattern(path: str, x, y) -> None:
    """Write a pattern (two_theta, intensity), choosing the writer from the file
    extension; an unrecognised/blank extension is written as ASCII XY."""
    ext = os.path.splitext(path)[1].lower()
    writer = _WRITERS.get(ext, save_xy)
    writer(path, np.asarray(x, dtype=float), np.asarray(y, dtype=float))
