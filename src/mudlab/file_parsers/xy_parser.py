"""Plain-text XY pattern parser (2θ, intensity).

Accepts the common interchange layouts: two numeric columns separated by
whitespace, commas, or semicolons; header/comment lines (#, //, ;, or
non-numeric text) are skipped. Numbers are ASCII, so files are read as
UTF-8 with replacement for stray bytes from instrument software.
"""

from __future__ import annotations

import re

import numpy as np

_SPLIT = re.compile(r"[,;\s]+")


def parse_xy(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse a text pattern file; returns (two_theta, intensity) arrays."""
    x_values: list[float] = []
    y_values: list[float] = []
    with open(path, "r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            line = line.strip()
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
        raise ValueError(f"No XY data found in {path!r}")
    return np.asarray(x_values), np.asarray(y_values)
