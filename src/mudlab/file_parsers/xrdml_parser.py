"""PANalytical *.XRDML pattern parser (2θ, intensity).

Ported from old mudlab's XRDMLParser (file_parsers/xrd_parsers/xrdml_parser.py).
XRDML is the XML format written by Malvern PANalytical instruments. The scan
stores its 2θ axis either as an explicit `<listPositions>` or as a
`<startPosition>`/`<endPosition>` pair (fixed step, reconstructed with
linspace), and its `<intensities>`/`<counts>` as whitespace-separated numbers.
Intensities are normalised to counts-per-second (÷ `<commonCountingTime>`)
unless already CPS - matching the old app and the RAW / CPI parsers.

MudLab2 uses one measured curve per raw-pattern phase, so this returns the
FIRST non-aborted scan's data points.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import numpy as np


def _ns(root) -> str:
    """The default namespace URI from the root tag ('{uri}tag'), or ''."""
    tag = root.tag
    if tag.startswith("{"):
        return tag[1:tag.index("}")]
    return ""


def _q(tag: str, ns: str) -> str:
    return "{%s}%s" % (ns, tag) if ns else tag


def _common_counting_time(dp, ns: str) -> float:
    el = dp.find(_q("commonCountingTime", ns))
    if el is not None and el.text:
        try:
            return float(el.text)
        except ValueError:
            pass
    return 1.0


def _two_theta(dp, ns: str, n: int):
    """The 2θ axis for a <dataPoints>: explicit list, or start/end + linspace
    over n intensities. Returns an array or None."""
    for pos in dp.iter(_q("positions", ns)):
        if pos.get("axis") != "2Theta":
            continue
        lp = pos.find(_q("listPositions", ns))
        if lp is not None and lp.text:
            return np.fromstring(lp.text, dtype=float, sep=" ")
        s = pos.find(_q("startPosition", ns))
        e = pos.find(_q("endPosition", ns))
        if s is not None and e is not None and s.text and e.text:
            return np.linspace(float(s.text), float(e.text), n)
    return None


def _datapoints(dp, ns: str):
    """Parse one <dataPoints> to (two_theta, intensity_cps) or None."""
    int_el = dp.find(_q("intensities", ns))
    if int_el is None:
        int_el = dp.find(_q("counts", ns))
    if int_el is None or not int_el.text:
        return None
    intensity = np.fromstring(int_el.text, dtype=float, sep=" ")
    if intensity.size == 0:
        return None

    two_theta = _two_theta(dp, ns, intensity.size)
    if two_theta is None or two_theta.size == 0:
        return None

    unit = (int_el.get("unit", "counts") or "counts").lower()
    if unit in ("counts", "counts per step", ""):
        intensity = intensity / _common_counting_time(dp, ns)

    if two_theta.size != intensity.size:
        m = min(two_theta.size, intensity.size)
        two_theta, intensity = two_theta[:m], intensity[:m]
    return two_theta, intensity


def parse_xrdml(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse a PANalytical *.XRDML file; returns (two_theta, intensity) for its
    first non-aborted scan. Intensity is counts-per-second."""
    root = ET.parse(path).getroot()
    ns = _ns(root)
    for meas in root.iter(_q("xrdMeasurement", ns)):
        for scan in meas.iter(_q("scan", ns)):
            if scan.get("status", "") == "Aborted":
                continue
            for dp in scan.iter(_q("dataPoints", ns)):
                result = _datapoints(dp, ns)
                if result is not None:
                    return result
    raise ValueError("No usable scan data in %r." % path)


def _first_float(root, tag: str, ns: str):
    for el in root.iter(_q(tag, ns)):
        if el.text and el.text.strip():
            try:
                return float(el.text)
            except ValueError:
                pass
    return None


def parse_xrdml_metadata(path: str) -> dict:
    """Best-effort instrument / scan metadata from a PANalytical *.XRDML, for the
    specimen 'source' description. Every field is optional; returns a dict with
    any of: wavelength_ka1 / wavelength_ka2 (nm), count_time (s), sample_name,
    sample_id, scan_date, radius_mm. Never raises - a missing/odd file just
    yields fewer keys."""
    md: dict = {}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return md
    ns = _ns(root)

    ka1 = _first_float(root, "kAlpha1", ns)  # stored in Angstrom
    ka2 = _first_float(root, "kAlpha2", ns)
    if ka1 and ka1 > 0:
        md["wavelength_ka1"] = ka1 / 10.0    # -> nm (MudLab's unit)
    if ka2 and ka2 > 0:
        md["wavelength_ka2"] = ka2 / 10.0

    ct = _first_float(root, "commonCountingTime", ns)
    if ct:
        md["count_time"] = ct

    # Sample name / id come from <sample> (not the author's <name>).
    for sample in root.iter(_q("sample", ns)):
        sname = sample.find(_q("name", ns))
        sid = sample.find(_q("id", ns))
        if sname is not None and sname.text and sname.text.strip():
            md["sample_name"] = sname.text.strip()
        if sid is not None and sid.text and sid.text.strip():
            md["sample_id"] = sid.text.strip()
        break

    for el in root.iter(_q("startTimeStamp", ns)):
        if el.text and el.text.strip():
            md["scan_date"] = el.text.strip()
            break

    radius = _first_float(root, "radius", ns)  # incident-beam radius, mm
    if radius and radius > 0:
        md["radius_mm"] = radius
    return md
