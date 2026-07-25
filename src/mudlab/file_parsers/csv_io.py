"""Common CSV / plain-text XY import & export.

One place every feature reads and writes two-column ``(x, y)`` text data, so
delimiter / decimal-sign / header handling behaves the same everywhere
(experimental-pattern import & export, wavelength distributions, background
patterns, ...).

Two modes:

* **Auto** (``options is None`` or an all-default :class:`CsvOptions`): the
  tolerant reader used for XRD patterns - any of comma / semicolon / whitespace
  as the separator, ``.`` decimal, comment/header lines (``#``, ``//``, ``;``,
  ``'`` or any non-numeric row) skipped. This is the historical behaviour and
  the default for drag-in imports.
* **Explicit** (a :class:`CsvOptions` with a chosen ``delimiter`` / ``decimal``
  / ``has_header``): honours exactly what the CSV-import options dialog asked
  for, for files auto-detection gets wrong (e.g. European ``;``-separated,
  ``,``-decimal exports).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass

import numpy as np

# Tolerant auto-mode split: runs of comma / semicolon / whitespace.
_AUTO_SPLIT = re.compile(r"[,;\s]+")
_COMMENT_PREFIXES = ("#", "//", ";", "'")

#: Human label -> delimiter char (None = auto-detect). Shared with the dialog.
DELIMITERS = (
    ("Auto-detect", None),
    ("Comma  ,", ","),
    ("Semicolon  ;", ";"),
    ("Tab", "\t"),
    ("Space", " "),
)
DECIMALS = (("Period  .", "."), ("Comma  ,", ","))


@dataclass(frozen=True)
class CsvOptions:
    """How to read a delimited text file. ``delimiter=None`` means auto-detect;
    ``decimal`` is the character used for the decimal point; ``has_header``
    skips the first content line."""
    delimiter: str | None = None
    decimal: str = "."
    has_header: bool = False

    @property
    def is_auto(self) -> bool:
        return self.delimiter is None and self.decimal == "." and not self.has_header


# ----------------------------------------------------------------------
# Reading
# ----------------------------------------------------------------------
def parse_xy_lines(lines, source: str = "<lines>", min_rows: int = 2):
    """Tolerant auto-mode parse of an iterable of text lines: the first two
    numeric columns of each data row (comma / semicolon / whitespace
    separated), header/comment lines skipped. Shared with the Rigaku .rasx
    parser (same embedded layout). Raises ValueError with fewer than
    ``min_rows`` data rows."""
    x_values: list[float] = []
    y_values: list[float] = []
    for line in lines:
        line = line.strip().lstrip("﻿")  # tolerate a stray BOM
        if not line or line.startswith(_COMMENT_PREFIXES):
            continue
        parts = [p for p in _AUTO_SPLIT.split(line) if p]
        if len(parts) < 2:
            continue
        try:
            x = float(parts[0])
            y = float(parts[1])
        except ValueError:
            continue  # header or text line
        x_values.append(x)
        y_values.append(y)

    if len(x_values) < min_rows:
        raise ValueError(f"No XY data found in {source!r}")
    return np.asarray(x_values), np.asarray(y_values)


def _make_splitter(delimiter: str | None, decimal: str):
    """Return a ``line -> [fields]`` splitter that NEVER splits on the decimal
    sign, so a comma decimal (European data) is not mistaken for a separator.

    - Auto (``delimiter is None``) - or a delimiter equal to the decimal, which
      is contradictory - splits on comma / semicolon / whitespace with the
      decimal character removed from that set.
    - "Space" (`" "`) splits on any whitespace run (aligned columns).
    - Any other explicit delimiter is used verbatim (it is guaranteed different
      from the decimal by the cases above).
    """
    if delimiter is None or delimiter == decimal:
        seps = "".join(c for c in ",;" if c != decimal)
        rx = re.compile("[" + seps + r"\s]+")
        return lambda line: [p for p in rx.split(line) if p]
    if delimiter == " ":
        return lambda line: line.split()
    return lambda line: [p.strip() for p in line.split(delimiter)]


def _parse_explicit(lines, options: CsvOptions, source: str, min_rows: int):
    x_values: list[float] = []
    y_values: list[float] = []
    header_pending = options.has_header
    split = _make_splitter(options.delimiter, options.decimal)
    for line in lines:
        line = line.strip().lstrip("﻿")
        if not line or line.startswith(_COMMENT_PREFIXES):
            continue
        if header_pending:
            header_pending = False  # drop the first content line
            continue
        parts = split(line)
        if len(parts) < 2:
            continue
        a, b = parts[0], parts[1]
        if options.decimal != ".":
            a = a.replace(options.decimal, ".")
            b = b.replace(options.decimal, ".")
        try:
            # Parse both BEFORE appending either, so a row whose second column
            # fails is skipped whole and x/y stay the same length.
            xv, yv = float(a), float(b)
        except ValueError:
            continue
        x_values.append(xv)
        y_values.append(yv)
    if len(x_values) < min_rows:
        raise ValueError(f"No XY data found in {source!r}")
    return np.asarray(x_values), np.asarray(y_values)


def _read_lines(path: str):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as stream:
        return stream.readlines()


def read_xy(path: str, options: CsvOptions | None = None, min_rows: int = 2):
    """Read a two-column text file into ``(x, y)`` numpy arrays.

    ``options`` None or all-default -> tolerant auto parse; otherwise the
    explicit delimiter / decimal / header are honoured. ``min_rows`` is the
    minimum number of data rows required (2 for a pattern, 1 for a single-line
    distribution)."""
    lines = _read_lines(path)
    if options is None or options.is_auto:
        return parse_xy_lines(lines, source=path, min_rows=min_rows)
    return _parse_explicit(lines, options, path, min_rows)


# ----------------------------------------------------------------------
# Writing
# ----------------------------------------------------------------------
def write_xy(path, x, y, delimiter: str = "\t", decimal: str = ".",
             header: str | None = None, fmt: str = "%.6f") -> None:
    """Write ``(x, y)`` as two delimited columns. ``header`` (when given) is
    written as a first line verbatim; ``fmt`` formats each number; ``decimal``
    swaps the decimal point in the formatted numbers (e.g. European ``,``).

    Refuses ``decimal == delimiter``: that would put the decimal sign between the
    two numbers, producing a file no reader could split unambiguously."""
    if decimal == delimiter:
        raise ValueError(
            "decimal sign and delimiter cannot be the same character (%r)" % decimal
        )
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        if header is not None:
            stream.write(header + "\n")
        for xi, yi in zip(x, y):
            a = fmt % xi
            b = fmt % yi
            if decimal != ".":
                a = a.replace(".", decimal)
                b = b.replace(".", decimal)
            stream.write(a + delimiter + b + "\n")


# ----------------------------------------------------------------------
# Sniffing / preview (for the import-options dialog)
# ----------------------------------------------------------------------
def _content_lines(path: str, limit: int = 40):
    out = []
    for line in _read_lines(path):
        s = line.strip().lstrip("﻿")
        if s and not s.startswith(_COMMENT_PREFIXES):
            out.append(s)
        if len(out) >= limit:
            break
    return out


def sniff(path: str) -> CsvOptions:
    """Best-guess :class:`CsvOptions` for `path`, to pre-fill the dialog.

    Uses csv.Sniffer for the delimiter and header, with a decimal heuristic:
    a comma that is not the delimiter but appears inside numeric fields is
    read as the decimal sign (European exports). Falls back to auto on any
    uncertainty."""
    lines = _content_lines(path)
    if not lines:
        return CsvOptions()
    sample = "\n".join(lines[:20])
    delimiter: str | None = None
    has_header = False
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t ")
        if dialect.delimiter in (",", ";", "\t", " "):
            delimiter = dialect.delimiter
    except csv.Error:
        delimiter = None
    try:
        has_header = csv.Sniffer().has_header(sample)
    except csv.Error:
        has_header = False

    decimal = "."
    # If the delimiter is not a comma but fields still contain commas, those
    # commas are decimal points (e.g. "12,5;0,03").
    if delimiter not in (None, ",") and any("," in ln for ln in lines):
        decimal = ","

    return CsvOptions(delimiter=delimiter, decimal=decimal, has_header=has_header)


def preview(path: str, options: CsvOptions, limit: int = 12):
    """First `limit` content rows as ``(col0, col1, parses_ok)`` under
    `options`, for the dialog's live preview. A header row (when
    ``has_header``) is returned with ``parses_ok=False`` so it reads as a
    heading, not data."""
    rows = []
    header_pending = options.has_header
    split = _make_splitter(options.delimiter, options.decimal)
    for line in _content_lines(path, limit + (1 if options.has_header else 0)):
        parts = split(line)
        col0 = parts[0] if len(parts) > 0 else ""
        col1 = parts[1] if len(parts) > 1 else ""
        if header_pending:
            header_pending = False
            rows.append((col0, col1, False))
            continue
        a, b = col0, col1
        if options.decimal != ".":
            a = a.replace(options.decimal, ".")
            b = b.replace(options.decimal, ".")
        try:
            float(a)
            float(b)
            ok = len(parts) >= 2
        except ValueError:
            ok = False
        rows.append((col0, col1, ok))
        if len(rows) >= limit + (1 if options.has_header else 0):
            break
    return rows
