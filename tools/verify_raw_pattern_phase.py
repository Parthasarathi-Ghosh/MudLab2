#!/usr/bin/env python
"""Durable harness for the RawPatternPhase port (batch 1: model + calc +
round-trip), run head-less.

A RawPatternPhase is not computed from a structure - it carries a fixed
measured pattern (2theta -> intensity) and contributes it directly, scaled by
its fraction. This covers:

  1. model - type / apply flags / pattern arrays / validity;
  2. calc - get_diffracted_intensity resamples the stored curve onto the 2theta
     grid, zero outside range, and the LP factor is NOT applied (apply_lpf is
     False), i.e. get_intensity == get_diffracted_intensity;
  3. in-memory round-trip - to_dict -> from_dict preserves the pattern and is
     idempotent (byte-identical dict on a second pass);
  4. through-the-file round-trip - a raw phase added to a real project survives
     save_mud -> load_mud alongside the modeled phases, which are untouched.

There is no golden fixture (no sample project has a RawPatternPhase, same as
R1G4). The calc is a plain interpolation, so a synthetic pattern fully
exercises it; a real .pyxrd with a raw phase would only add a byte-golden.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_raw_pattern_phase.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project (for point 4).
"""

from __future__ import annotations

import copy
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.calculations.phases import (  # noqa: E402
    get_diffracted_intensity, get_intensity,
)
from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.models import RawPatternPhase  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")
_app = QApplication.instance() or QApplication([])


def _fixture():
    for name in ("Dh537A.mud", "308 r1.mud", "Dh2040A 14Jul26 r1.mud"):
        for base in (_FIXTURES, os.path.join(os.path.expanduser("~"), "Downloads")):
            path = os.path.join(base, name)
            if os.path.isfile(path):
                return path
    return None


def _triangle_phase(name="Quartz (raw)"):
    """A raw phase with a triangular peak: 0 at 10 and 30 deg, 100 at 20 deg."""
    phase = RawPatternPhase(name=name)
    phase.set_raw_pattern([10.0, 20.0, 30.0], [0.0, 100.0, 0.0])
    return phase


def check_model(results):
    p = _triangle_phase()
    results.append(("1 type is RawPatternPhase", p.type == "RawPatternPhase"))
    results.append(("1 apply_lpf and apply_correction are False",
                    p.apply_lpf is False and p.apply_correction is False))
    results.append(("1 no structure (G=0, no components, no based_on)",
                    p.G == 0 and p.components == [] and p.based_on is None))
    results.append(("1 pattern arrays stored",
                    np.array_equal(p.raw_pattern_x, [10.0, 20.0, 30.0])
                    and np.array_equal(p.raw_pattern_y, [0.0, 100.0, 0.0])))
    results.append(("1 valid_probs True with >=2 points", p.valid_probs is True))
    empty = RawPatternPhase(name="empty")
    results.append(("1 valid_probs False with no pattern",
                    empty.valid_probs is False))
    # phase-graph no-ops must not raise / must report no change
    results.append(("1 set_based_on is a no-op", empty.set_based_on(p) is False))
    empty.resolve_based_on({})  # must not raise


def check_calc(results):
    p = _triangle_phase()
    # 2theta grid straddling the stored range (5 and 40 are outside).
    two_theta_deg = np.array([5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0])
    range_theta = np.deg2rad(two_theta_deg) / 2.0   # so rad2deg(2*theta)==2theta
    range_stl = np.zeros_like(range_theta)          # unused by the raw branch
    got = get_diffracted_intensity(range_theta, range_stl, p)
    want = np.array([0.0, 0.0, 50.0, 100.0, 50.0, 0.0, 0.0])  # interp + zero-fill
    results.append(("2 resamples the stored curve onto the 2theta grid",
                    np.allclose(got, want, atol=1e-9)))
    results.append(("2 zero outside the stored range",
                    got[0] == 0.0 and got[-1] == 0.0))
    # LP factor is not applied for a raw phase -> get_intensity == diffracted.
    full = get_intensity(range_theta, range_stl, 0.5, 0.5, 0.0, p)
    results.append(("2 LP factor not applied (get_intensity == diffracted)",
                    np.allclose(full, got, atol=1e-12)))
    # A degenerate (empty) pattern yields zeros, not a crash.
    empty = RawPatternPhase(name="empty")
    z = get_diffracted_intensity(range_theta, range_stl, empty)
    results.append(("2 empty pattern -> zeros", np.allclose(z, 0.0)
                    and z.shape == range_stl.shape))


def check_inmemory_roundtrip(results):
    p = _triangle_phase()
    d1 = p.to_dict()
    results.append(("3 to_dict emits a RawPatternPhase entry",
                    d1.get("type") == "RawPatternPhase"))
    back = RawPatternPhase.from_dict(d1)
    results.append(("3 from_dict restores the pattern",
                    np.array_equal(back.raw_pattern_x, p.raw_pattern_x)
                    and np.array_equal(back.raw_pattern_y, p.raw_pattern_y)
                    and back.uuid == p.uuid and back.name == p.name))
    results.append(("3 to_dict is idempotent (byte-identical second pass)",
                    back.to_dict() == d1))
    # The embedded line's non-modeled keys survive.
    p2 = RawPatternPhase.from_dict({
        "type": "RawPatternPhase",
        "properties": {
            "name": "Q", "uuid": "abc",
            "raw_pattern": {"type": "PyXRDLine", "properties": {
                "label": "Raw pattern", "uuid": "line-1",
                "color": "#ff0000", "data": "[[10.0,0.0],[20.0,5.0]]"}},
        },
    })
    line_props = p2.to_dict()["properties"]["raw_pattern"]["properties"]
    results.append(("3 unmodeled line keys preserved (color, uuid)",
                    line_props.get("color") == "#ff0000"
                    and line_props.get("uuid") == "line-1"))


def check_file_roundtrip(path, results):
    """4. A raw phase added to a real project survives save/load, and the
    modeled phases are untouched."""
    project = load_mud(path)
    before_uuids = [ph.uuid for ph in project.phases]
    before_types = [ph.type for ph in project.phases]

    raw = _triangle_phase("Corundum (raw internal std)")
    project.add_phase(raw)
    raw_dict_before = copy.deepcopy(raw.to_dict())

    tmpdir = tempfile.mkdtemp(prefix="mudlab_rawphase_")
    out = os.path.join(tmpdir, "with_raw.mud")
    try:
        save_mud(project, out)
        reloaded = load_mud(out)
    finally:
        for f in (out, out + "~", out + ".tmp"):
            if os.path.exists(f):
                os.remove(f)
        os.rmdir(tmpdir)

    raws = [ph for ph in reloaded.phases if ph.type == "RawPatternPhase"]
    results.append(("4 raw phase survives save/load", len(raws) == 1))
    if raws:
        r = raws[0]
        results.append(("4 reloaded pattern matches",
                        np.allclose(r.raw_pattern_x, raw.raw_pattern_x)
                        and np.allclose(r.raw_pattern_y, raw.raw_pattern_y)))
        results.append(("4 reloaded raw phase to_dict is byte-identical",
                        r.to_dict() == raw_dict_before))
    # The original modeled phases are all still there, same uuids/types.
    kept = [ph for ph in reloaded.phases if ph.uuid in before_uuids]
    results.append(("4 modeled phases untouched (count + uuids)",
                    len(kept) == len(before_uuids)
                    and [ph.type for ph in kept] == before_types))


def main(argv):
    results = []
    print("=" * 72)
    print("RawPatternPhase - model + calc + round-trip")
    print("=" * 72)
    check_model(results)
    check_calc(results)
    check_inmemory_roundtrip(results)

    path = argv[1] if len(argv) > 1 else _fixture()
    if path and os.path.isfile(path):
        print("through-the-file round-trip on:", os.path.basename(path))
        check_file_roundtrip(path, results)
    else:
        print("(no sample project; skipping the through-the-file check)")

    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("RawPatternPhase harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    if passed != len(results):
        return 1
    return 0 if (path and os.path.isfile(path)) else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
