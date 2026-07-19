"""Rigaku *.RASX pattern parser (2θ, intensity).

RASX is the format written by newer Rigaku instruments (SmartLab / Miniflex
via the SmartLab Studio II software). It is a ZIP archive; the scan profile
lives in a ``Data<i>/Profile<j>.txt`` member as tab-separated text -
``2theta<TAB>intensity<TAB>flag`` per row, with a UTF-8 BOM. MudLab2 reads the
first profile's first two columns (the flag column is ignored).

Not part of PyXRD / old mudlab (which predate RASX); this is a new parser.
"""

from __future__ import annotations

import re
import zipfile

import numpy as np

from mudlab.file_parsers.xy_parser import parse_xy_lines

# Members like "Data0/Profile0.txt" (allow any Data<i>/Profile<j>).
_PROFILE = re.compile(r"(^|/)Data\d+/Profile\d+\.txt$", re.IGNORECASE)


def parse_rasx(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse a Rigaku *.RASX file; returns (two_theta, intensity) from its
    first scan profile."""
    with zipfile.ZipFile(path) as archive:
        members = [n for n in archive.namelist() if _PROFILE.search(n)]
        if not members:
            raise ValueError("No scan profile (Data*/Profile*.txt) in %r." % path)
        member = sorted(members)[0]
        text = archive.read(member).decode("utf-8-sig", "replace")
    return parse_xy_lines(text.splitlines(), source="%s::%s" % (path, member))
