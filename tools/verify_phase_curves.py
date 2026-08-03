#!/usr/bin/env python
"""Durable harness for the per-phase plot curves, run head-less.

A mixture recompute now retains each phase's calculated contribution on the
specimen (Specimen.phase_patterns), and the plot draws them in each phase's
display_color when display_phases is on. This checks:

  - the capture: after Mixture.calculate, phase_patterns holds one
    (phase, curve) per FILLED slot, the phase objects are the assigned ones,
    and each curve is on the calculated x-grid;
  - it is transient (a set_calculated_pattern without them clears them; trim
    clears them; it is never saved to the .mud);
  - the drawing: display_phases on adds exactly one line per phase in the
    phase's display_color, off removes them, and they follow display_calculated.

The per-phase intensity numerics are guarded by verify_calc_engine.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_phase_curves.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication

import mudlab.calculations.specimen as calc_specimen
from mudlab.calculations.specimen import calculate_specimen_pattern
from mudlab.file_parsers.mud_project import load_mud, save_mud
from mudlab.plot_controller import PatternPlot

app = QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _load_project_with_phase_patterns():
    """A project whose first mixture, once recomputed, gives a specimen with
    per-phase curves - plus that specimen and its filled phase list."""
    fixtures = [os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")]
    fixtures += sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud")))
    seen = set()
    for path in fixtures:
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        project = load_mud(path)
        if not project.mixtures:
            continue
        mixture = project.mixtures[0]
        mixture.calculate()
        for i, spec in enumerate(mixture.specimens):
            if spec is not None and spec.phase_patterns:
                filled = [p for p in mixture.phase_matrix[i] if p is not None]
                return path, project, mixture, spec, filled
    return None, None, None, None, None


PATH, PROJECT, MIXTURE, SPEC, FILLED = _load_project_with_phase_patterns()
if SPEC is None:
    print("No fixture with a mixture + assigned phases; skipping (exit 2).")
    raise SystemExit(2)


def _phase_line_count(plot, colors):
    return sum(1 for ln in plot.axes.get_lines() if ln.get_color() in colors)


# ----------------------------------------------------------------------
# Capture
# ----------------------------------------------------------------------
def check_capture():
    check("capture: one (phase, curve) per filled slot",
          len(SPEC.phase_patterns) == len(FILLED))
    check("capture: the entries are the assigned phase objects",
          [p for p, _ in SPEC.phase_patterns] == FILLED)
    cx, _ = SPEC.calculated_pattern
    check("capture: each curve is on the calculated x-grid",
          all(np.asarray(y).shape == cx.shape for _, y in SPEC.phase_patterns))
    check("capture: each phase carries a display_color",
          all(isinstance(p.display_color, str) for p, _ in SPEC.phase_patterns))


# ----------------------------------------------------------------------
# Transient / not persisted
# ----------------------------------------------------------------------
def check_transient():
    # A plain calculated-pattern set (no per-phase) clears them.
    x, y = SPEC.calculated_pattern
    saved = SPEC.phase_patterns
    SPEC.set_calculated_pattern(x, y)
    cleared = SPEC.phase_patterns is None
    SPEC.phase_patterns = saved  # restore for later checks
    check("transient: set_calculated_pattern without per-phase clears them", cleared)

    # trim clears them.
    project = load_mud(PATH)
    mixture = project.mixtures[0]
    mixture.calculate()
    spec = next(s for s in mixture.specimens if s is not None and s.phase_patterns)
    ex, _ = spec.experimental_pattern
    if ex.size > 4:
        spec.trim(float(ex[1]), float(ex[-2]))
        check("transient: trim clears the per-phase curves", spec.phase_patterns is None)

    # Not saved to the .mud.
    project2 = load_mud(PATH)
    m2 = project2.mixtures[0]
    m2.calculate()
    s2 = next(s for s in m2.specimens if s is not None and s.phase_patterns)
    tmp = os.path.join(tempfile.mkdtemp(), "pp.mud")
    save_mud(project2, tmp)
    r = load_mud(tmp)
    rs = r.specimens[project2.specimens.index(s2)] if s2 in project2.specimens else None
    check("transient: phase_patterns not persisted to the .mud",
          rs is not None and rs.phase_patterns is None)


# ----------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------
def check_drawing():
    colors = {p.display_color for p, _ in SPEC.phase_patterns}
    SPEC.display_calculated = True

    SPEC.display_phases = False
    plot = PatternPlot([SPEC], PROJECT)
    off = len(plot.axes.get_lines())

    SPEC.display_phases = True
    plot.draw_pattern()
    on = len(plot.axes.get_lines())
    check("draw: display_phases adds one line per phase",
          on - off == len(SPEC.phase_patterns))
    check("draw: the added lines use each phase's display_color",
          colors <= {ln.get_color() for ln in plot.axes.get_lines()})

    # Hiding the calculated pattern hides the per-phase too (they are part of it).
    SPEC.display_calculated = False
    plot.draw_pattern()
    check("draw: per-phase follow display_calculated (off -> none)",
          _phase_line_count(plot, colors) == 0)
    SPEC.display_calculated = True
    SPEC.display_phases = False


# ----------------------------------------------------------------------
# Pairing robustness (per-phase audit #5): each phase must be paired with ITS
# OWN contribution, and a row-count mismatch must fail loudly, not mis-colour.
# ----------------------------------------------------------------------
def check_pairing():
    i = MIXTURE.specimens.index(SPEC)
    full = MIXTURE.phase_matrix[i]
    scale = float(MIXTURE.scales[i])
    bgshift = float(MIXTURE.bgshifts[i])
    filled_slots = [j for j, p in enumerate(full) if p is not None]

    ok = True
    for m, j in enumerate(filled_slots):
        # Recompute slot j's contribution IN ISOLATION (only phase j filled) and
        # compare to the m-th captured pair - independent of any positional
        # assumption, so a reordering would be caught.
        isolated = [p if k == j else None for k, p in enumerate(full)]
        _, _, iso = calculate_specimen_pattern(
            SPEC, isolated, scale, MIXTURE.fractions, bgshift,
            return_phase_patterns=True)
        pair_phase, pair_row = SPEC.phase_patterns[m]
        if not (pair_phase is full[j] and len(iso) == 1
                and np.allclose(np.asarray(pair_row), np.asarray(iso[0][1]))):
            ok = False
    check("pairing: each phase is paired with its own isolated contribution", ok)

    # The loud row-count guard: if the scaled-intensity row count stops matching
    # the slot count, calculate_specimen_pattern must raise, not mis-pair.
    orig = calc_specimen.calculate_scaled_intensities

    def drop_a_row(*a, **k):
        total, scaled, bg = orig(*a, **k)
        return total, scaled[:-1], bg

    calc_specimen.calculate_scaled_intensities = drop_a_row
    try:
        raised = False
        try:
            calculate_specimen_pattern(SPEC, full, scale, MIXTURE.fractions,
                                       bgshift, return_phase_patterns=True)
        except ValueError:
            raised = True
    finally:
        calc_specimen.calculate_scaled_intensities = orig
    check("pairing: a row-count mismatch raises instead of mis-pairing", raised)


# ----------------------------------------------------------------------
# Regression: a RawPatternPhase in a mixture must draw in the per-phase overlay.
# It used to lack `display_color`, so drawing the overlay raised AttributeError,
# which blanked the whole plot after an Optimize with a raw phase assigned.
# ----------------------------------------------------------------------
def check_raw_phase_overlay():
    from mudlab.models.raw_pattern_phase import RawPatternPhase

    raw = RawPatternPhase(name="Raw")
    check("RawPatternPhase has a display_color", hasattr(raw, "display_color"))
    raw.display_color = "#123456"
    back = RawPatternPhase.from_dict(raw.to_dict())
    check("RawPatternPhase display_color round-trips", back.display_color == "#123456")

    project = load_mud(PATH)
    mix = project.mixtures[0]
    spec = next(s for s in mix.specimens if s is not None)
    ex, ey = spec.experimental_pattern
    raw = RawPatternPhase(name="Raw")
    raw.set_raw_pattern(np.asarray(ex, float), np.asarray(ey, float))
    raw.display_color = "#123456"
    project.add_phase(raw)
    j = mix.add_phase_slot("Raw")
    for i, s in enumerate(mix.specimens):
        if s is not None:
            mix.set_phase_at(i, j, raw)
    mix.calculate()
    shown = [s for s in mix.specimens if s is not None][:1]
    shown[0].display_phases = True
    shown[0].display_calculated = True
    crashed = False
    colors: set = set()
    try:
        plot = PatternPlot(shown, project)
        colors = {ln.get_color() for ln in plot.axes.get_lines()}
    except Exception:
        crashed = True
    check("raw phase in a mixture draws the per-phase overlay without crashing",
          not crashed)
    check("the raw phase is drawn in its display_color", "#123456" in colors)


def main():
    print("fixture: %s (%d phases)" % (os.path.basename(PATH), len(FILLED)))
    check_capture()
    check_transient()
    check_drawing()
    check_pairing()
    check_raw_phase_overlay()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- per-phase curves verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
