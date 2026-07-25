"""Plain-text XY pattern parser (2θ, intensity) - backwards-compatible facade.

The implementation now lives in :mod:`mudlab.file_parsers.csv_io`, the common
CSV import/export used across the app. This module keeps the historical
``parse_xy`` / ``parse_xy_lines`` / ``save_xy`` names so existing callers (and
the Rigaku .rasx parser) are undisturbed.
"""

from __future__ import annotations

from mudlab.file_parsers.csv_io import parse_xy_lines, read_xy, write_xy

__all__ = ["parse_xy_lines", "parse_xy", "save_xy"]


def parse_xy(path: str):
    """Parse a text pattern file; returns (two_theta, intensity) arrays
    (tolerant auto-detect - the common CSV reader with default options)."""
    return read_xy(path)


def save_xy(path: str, x, y) -> None:
    """Write a pattern as two tab-separated ASCII columns (2θ, intensity) - the
    plain interchange format, readable by every XRD tool and by parse_xy."""
    write_xy(path, x, y, delimiter="\t", fmt="%.6f")
