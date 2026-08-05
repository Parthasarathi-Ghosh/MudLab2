"""Bruker/Siemens DIFFRAC *.UXD ASCII pattern parser (2θ, intensity).

Ported from old mudlab's UXDParser (file_parsers/xrd_parsers/uxd_parser.py) -
the direct lineage; xylib has a UXD reader too but old mudlab's already matches
this app's conventions. A UXD file is a header of `;` comment lines and
`_KEYWORD=value` lines, ended by a data marker that also states the layout:

  * ``_2THETACOUNTS`` / ``_2THETACPS`` - rows of "2theta  value";
  * ``_COUNTS`` / ``_CPS``            - single-column values; 2theta is
                                        rebuilt from ``_START`` / ``_STEPSIZE``.

Counts are normalised to counts-per-second using ``_STEPTIME`` (a `*CPS` marker
means the values are already CPS), matching the XRDML / RASX / RAW parsers. Only
the FIRST data range is read (MudLab2 stores one measured curve per raw phase).
"""

from __future__ import annotations

import numpy as np

_MARKERS_PAIRED = ("_2THETACOUNTS", "_2THETACPS")
_MARKERS_SINGLE = ("_COUNTS", "_CPS")


def parse_uxd(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse a Bruker *.UXD file; returns (two_theta, intensity) for its first
    range. Intensity is counts-per-second."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as stream:
        lines = stream.readlines()

    meta: dict[str, str] = {}
    paired = None
    already_cps = False
    data_start = None
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s or s.startswith(";"):
            continue
        up = s.upper()
        if up.startswith(_MARKERS_PAIRED):
            paired, already_cps, data_start = True, up.endswith("CPS"), i + 1
            break
        if up.startswith(_MARKERS_SINGLE):
            paired, already_cps, data_start = False, up.endswith("CPS"), i + 1
            break
        if s.startswith("_") and "=" in s:
            key, _, val = s[1:].partition("=")
            meta[key.strip().upper()] = val.strip().strip("'").strip('"')

    # No marker: fall back to the first row that has >= 2 numeric columns
    # (paired), so an atypical export still loads.
    if data_start is None:
        for i, raw in enumerate(lines):
            parts = raw.strip().replace(",", ".").split()
            if len(parts) >= 2:
                try:
                    float(parts[0]); float(parts[1])
                except ValueError:
                    continue
                paired, data_start = True, i
                break
        if data_start is None:
            raise ValueError("No UXD data found in %r." % path)

    def fnum(key, default=None):
        try:
            return float(meta[key])
        except (KeyError, ValueError, TypeError):
            return default

    steptime = fnum("STEPTIME", 1.0)
    # A non-positive / NaN step time must not divide the counts (0 -> inf,
    # negative -> sign flip); fall back to 1.0 (leave as counts).
    steptime = steptime if (steptime and steptime > 0) else 1.0
    count_time = 1.0 if already_cps else steptime
    start = fnum("START", 0.0)
    step = fnum("STEPSIZE", 1.0)

    xs: list[float] = []
    ys: list[float] = []
    n = 0
    for raw in lines[data_start:]:
        s = raw.strip().replace(",", ".")
        if not s:
            continue
        if s.startswith("_") or s.startswith(";"):
            break  # next range / keyword block - first range only
        parts = s.split()
        try:
            if paired:
                x = float(parts[0])
                y = float(parts[1])
            else:
                x = start + step * n
                y = float(parts[0])
        except (IndexError, ValueError):
            continue
        xs.append(x)
        ys.append(y / count_time)
        n += 1

    if len(xs) < 2:
        raise ValueError("No UXD data rows in %r." % path)
    return np.asarray(xs), np.asarray(ys)


def parse_uxd_metadata(path: str) -> dict:
    """Best-effort instrument metadata from a Bruker *.UXD header (for the
    specimen 'source' description). The header is `_KEY=VALUE` lines before the
    first data block; wavelengths are in the unit named by `_WL_UNIT` ('A' =
    Angstrom, the norm). Returns any of: wavelength_ka1 / wavelength_ka2 (nm),
    anode, voltage_kv, current_ma, count_time (s), scan_date, radius_mm. Never
    raises."""
    meta: dict = {}
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as stream:
            for raw in stream:
                s = raw.strip()
                if not s or s.startswith(";"):
                    continue
                up = s.upper()
                if up.startswith(_MARKERS_PAIRED) or up.startswith(_MARKERS_SINGLE):
                    break  # header ends at the first data block
                if s.startswith("_") and "=" in s:
                    key, _, val = s[1:].partition("=")
                    meta[key.strip().upper()] = val.strip().strip("'").strip('"')
    except OSError:
        return {}  # unreadable file -> no metadata

    def _f(key):
        try:
            return float(meta[key])
        except (KeyError, ValueError, TypeError):
            return None

    # Wavelengths are in _WL_UNIT ('A' = Angstrom -> nm; 'NM' kept as-is).
    unit = meta.get("WL_UNIT", "A").upper()
    to_nm = 1.0 if unit in ("NM", "NANOMETER", "NANOMETRE") else 0.1
    md: dict = {}
    wl1, wl2 = _f("WL1"), _f("WL2")
    if wl1 and wl1 > 0:
        md["wavelength_ka1"] = wl1 * to_nm
    if wl2 and wl2 > 0:
        md["wavelength_ka2"] = wl2 * to_nm
    if meta.get("ANODE"):
        md["anode"] = meta["ANODE"]
    kv, ma = _f("KV"), _f("MA")
    if kv:
        md["voltage_kv"] = kv
    if ma:
        md["current_ma"] = ma
    steptime = _f("STEPTIME")
    if steptime:
        md["count_time"] = steptime
    if meta.get("DATEMEASURED"):
        md["scan_date"] = meta["DATEMEASURED"]
    radius = _f("GONIOMETER_RADIUS")
    if radius and radius > 0:
        md["radius_mm"] = radius
    return md


def _wavelength_lines(goniometer) -> list[str]:
    """UXD wavelength fields from the goniometer's wavelength distribution.
    MudLab stores nm; UXD uses Angstrom (x10). WLRATIO is the second line's
    intensity fraction over the dominant one (the old parser reads it as
    Kalpha2/Kalpha1)."""
    wls = sorted(
        list(getattr(goniometer, "wavelength_distribution", None) or []),
        key=lambda wf: wf[1], reverse=True,
    )
    if not wls:
        return ["_WL_UNIT='A'", "_WL1=%.6f" % (1.54056)]
    lines = ["_WL_UNIT='A'", "_WL1=%.6f" % (wls[0][0] * 10.0)]
    if len(wls) > 1 and wls[0][1]:
        lines.append("_WL2=%.6f" % (wls[1][0] * 10.0))
        lines.append("_WLRATIO=%.6f" % (wls[1][1] / wls[0][1]))
    return lines


def save_uxd(path: str, x, y, sample: str = "", goniometer=None,
             anode: str = "Cu") -> None:
    """Write a pattern as a Bruker/Siemens *.UXD ASCII file (a documented,
    non-proprietary text format). Uses the paired `_2THETACOUNTS` layout with
    `_STEPTIME=1`, so the values are written verbatim (counts == CPS) and
    round-trip through parse_uxd unchanged. When a `goniometer` is given, its
    setup is written too (wavelengths, radius, divergence, soller slits, sample
    length) so the export carries the diffractometer parameters, not just the
    curve."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    start = float(x[0]) if x.size else 0.0
    step = float(x[1] - x[0]) if x.size > 1 else 0.0
    header = ["; Exported by MudLab2", "_FILEVERSION=2", "_SAMPLE='%s'" % sample]
    if goniometer is not None:
        header += _wavelength_lines(goniometer)
        header.append("_ANODE='%s'" % anode)
        header.append("_GONIOMETER_RADIUS=%.6f"
                      % float(getattr(goniometer, "radius", 0.0)))
        header.append("_DIVERGENCE=%.6f"
                      % float(getattr(goniometer, "divergence", 0.0)))
        header.append("_DIVERGENCE_MODE='%s'"
                      % getattr(goniometer, "divergence_mode", "FIXED"))
        header.append("_SOLLER1=%.6f"
                      % float(getattr(goniometer, "effective_soller1", 0.0)))
        header.append("_SOLLER2=%.6f"
                      % float(getattr(goniometer, "effective_soller2", 0.0)))
        header.append("_SAMPLE_LENGTH=%.6f"
                      % float(getattr(goniometer, "sample_length", 0.0)))
    else:
        header += ["_WL_UNIT='A'", "_WL1=%.6f" % 1.54056, "_ANODE='%s'" % anode]
    header += [
        "_DRIVE='COUPLED'",
        "_STEPTIME=1.000000",
        "_STEPSIZE=%.6f" % step,
        "_STEPMODE='C'",
        "_START=%.6f" % start,
        "_2THETA=%.6f" % start,
        "_2THETACOUNTS",
    ]
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(header) + "\n")
        for xi, yi in zip(x, y):
            stream.write("%.6f %.6g\n" % (xi, yi))
