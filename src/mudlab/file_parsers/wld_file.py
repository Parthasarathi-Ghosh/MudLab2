"""Wavelength-distribution (`.wld`) reader/writer.

The old app's ASCII `.wld` is a two-column CSV: a ``Wavelength, Factor``
header line followed by ``wavelength_nm,fraction`` rows (old GenericXYCSVParser
with a header). Whitespace around the comma is tolerated; blank lines and any
non-numeric header rows are skipped.
"""

from __future__ import annotations

import csv

_HEADER = "Wavelength, Factor"


def load_wld(path: str) -> list[tuple[float, float]]:
    """Parse a `.wld` file into ``[(wavelength_nm, fraction), ...]``.

    Skips the header and any blank / non-numeric lines. Raises ValueError if no
    valid ``(wavelength, fraction)`` row is found.
    """
    pairs: list[tuple[float, float]] = []
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 2:
                continue
            try:
                pairs.append((float(row[0]), float(row[1])))
            except ValueError:
                continue  # header row or stray text
    if not pairs:
        raise ValueError("No valid 'wavelength, fraction' rows in %s" % path)
    return pairs


def save_wld(path: str, pairs) -> None:
    """Write ``[(wavelength_nm, fraction), ...]`` to a `.wld` file, matching the
    old app's ``Wavelength, Factor`` header + comma-separated rows."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(_HEADER + "\n")
        for wavelength, fraction in pairs:
            handle.write("%.10g,%.10g\n" % (float(wavelength), float(fraction)))
