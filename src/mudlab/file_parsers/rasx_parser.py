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
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

from mudlab.file_parsers.xy_parser import parse_xy_lines

# Members like "Data0/Profile0.txt" (allow any Data<i>/Profile<j>).
_PROFILE = re.compile(r"(^|/)Data\d+/Profile\d+\.txt$", re.IGNORECASE)
# Rigaku (mis)spells it "MesurementConditions"; match that or "Measurement".
_CONDITIONS = re.compile(r"(^|/)Data\d+/Mea?surementConditions\d+\.xml$",
                         re.IGNORECASE)


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


def parse_rasx_metadata(path: str) -> dict:
    """Best-effort instrument metadata from a Rigaku *.RASX, read from its
    ``Data*/MesurementConditions*.xml`` member (for the specimen 'source'
    description). All fields optional; returns any of: wavelength_ka1 /
    wavelength_ka2 (nm), anode, voltage_kv, current_ma, scan_date,
    scan_speed_deg_min. Never raises."""
    md: dict = {}
    try:
        with zipfile.ZipFile(path) as archive:
            member = next((n for n in archive.namelist()
                           if _CONDITIONS.search(n)), None)
            if member is None:
                return md
            root = ET.fromstring(archive.read(member))
    except (OSError, zipfile.BadZipFile, ET.ParseError):
        return md

    # First non-empty text value per local (namespace-stripped) tag name.
    vals: dict = {}
    for el in root.iter():
        name = el.tag.rsplit("}", 1)[-1]
        if el.text and el.text.strip() and name not in vals:
            vals[name] = el.text.strip()

    def _f(key):
        try:
            return float(vals[key])
        except (KeyError, ValueError):
            return None

    ka1 = _f("WavelengthKalpha1")  # stored in Angstrom
    ka2 = _f("WavelengthKalpha2")
    if ka1 and ka1 > 0:
        md["wavelength_ka1"] = ka1 / 10.0  # -> nm
    if ka2 and ka2 > 0:
        md["wavelength_ka2"] = ka2 / 10.0
    if vals.get("TargetName"):
        md["anode"] = vals["TargetName"]
    kv = _f("Voltage")
    if kv:
        md["voltage_kv"] = kv
    ma = _f("Current")
    if ma:
        md["current_ma"] = ma
    if vals.get("StartTime"):
        md["scan_date"] = vals["StartTime"]
    speed = _f("Speed")
    if speed:
        md["scan_speed_deg_min"] = speed
    return md
