"""Plain-text XY pattern parser (2θ, intensity).

Accepts the common interchange layouts: two numeric columns separated by
whitespace, commas, or semicolons; header/comment lines (#, //, ;, or
non-numeric text) are skipped, and extra columns (e.g. a background pair) are
ignored. Read as UTF-8 with a BOM tolerated (instrument software often writes a
UTF-8 BOM) and replacement for stray bytes.
"""

from __future__ import annotations

import re

import numpy as np

_SPLIT = re.compile(r"[,;\s]+")


def parse_xy_lines(lines, source: str = "<lines>") -> tuple[np.ndarray, np.ndarray]:
    """Parse XY data from an iterable of text lines: the first two numeric
    columns of each data row (extra columns ignored), header/comment lines
    skipped. Shared by parse_xy and the Rigaku .rasx parser (whose embedded
    profile is the same layout)."""
    x_values: list[float] = []
    y_values: list[float] = []
    for line in lines:
        line = line.strip().lstrip("﻿")  # tolerate a stray BOM
        if not line or line.startswith(("#", "//", ";", "'")):
            continue
        parts = [p for p in _SPLIT.split(line) if p]
        if len(parts) < 2:
            continue
        try:
            x = float(parts[0])
            y = float(parts[1])
        except ValueError:
            continue  # header or text line
        x_values.append(x)
        y_values.append(y)

    if len(x_values) < 2:
        raise ValueError(f"No XY data found in {source!r}")
    return np.asarray(x_values), np.asarray(y_values)


def parse_xy(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse a text pattern file; returns (two_theta, intensity) arrays."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as stream:
        return parse_xy_lines(stream, source=path)


def save_xy(path: str, x, y) -> None:
    """Write a pattern as two tab-separated ASCII columns (2theta, intensity) -
    the plain interchange format, readable by every XRD tool and by parse_xy."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        for xi, yi in zip(x, y):
            stream.write("%.6f\t%.6f\n" % (xi, yi))
