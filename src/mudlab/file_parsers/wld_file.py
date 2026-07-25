"""Wavelength-distribution (`.wld`) reader/writer.

A `.wld` is a two-column CSV (``Wavelength, Factor`` header + ``wavelength_nm,
fraction`` rows). Reading and writing go through the common
:mod:`mudlab.file_parsers.csv_io` so `.wld` files behave like every other CSV
in the app - the only specifics here are the header line and that a
single-line distribution is valid.
"""

from __future__ import annotations

from mudlab.file_parsers.csv_io import read_xy, write_xy

_HEADER = "Wavelength, Factor"


def load_wld(path: str) -> list[tuple[float, float]]:
    """Parse a `.wld` file into ``[(wavelength_nm, fraction), ...]`` (a single
    line is valid). Raises ValueError if no numeric row is found."""
    x, y = read_xy(path, min_rows=1)
    return [(float(w), float(f)) for w, f in zip(x, y)]


def save_wld(path: str, pairs) -> None:
    """Write ``[(wavelength_nm, fraction), ...]`` to a `.wld` file with the old
    app's ``Wavelength, Factor`` header + comma-separated rows."""
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    write_xy(path, xs, ys, delimiter=",", header=_HEADER, fmt="%.10g")
