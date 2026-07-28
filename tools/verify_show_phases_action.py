#!/usr/bin/env python
"""Head-less harness for the View > 'Show phase patterns' toggle.

Batch 1 draws each phase's calculated curve when a specimen's display_phases
is on; this checks the MainWindow wiring around it:

  - the menu toggle bulk-flips display_phases on the shown specimens and the
    per-phase curves appear / disappear on the live plot;
  - flipped on before any refresh, it recomputes once so the curves have data
    (phase_patterns is transient and starts empty on a freshly loaded .mud);
  - the checkmark is a read-only mirror: a per-specimen edit (as the specimen
    dialog / tree toggles make) rebuilds the plot and updates the checkmark
    without re-entering the toggle handler.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_show_phases_action.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication

from mudlab.file_parsers.mud_project import load_mud
from mudlab.main_window import MainWindow

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _find_fixture():
    """A fixture path plus, once its first mixture is recomputed, the index of
    a specimen that carries assigned phases."""
    fixtures = [os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")]
    fixtures += sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud")))
    seen = set()
    for path in fixtures:
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        probe = load_mud(path)
        if not probe.mixtures:
            continue
        mix = probe.mixtures[0]
        mix.calculate()
        for i, spec in enumerate(mix.specimens):
            if spec is not None and spec.phase_patterns:
                phase_colors = {p.display_color for p, _ in spec.phase_patterns}
                return path, i, len(spec.phase_patterns), phase_colors
    return None, None, None, None


PATH, SPEC_I, NPHASES, PHASE_COLORS = _find_fixture()
if PATH is None:
    print("No fixture with a mixture + assigned phases; skipping (exit 2).")
    raise SystemExit(2)


def _phase_lines(win):
    plot = win.pattern_plots[0]
    return sum(1 for ln in plot.axes.get_lines() if ln.get_color() in PHASE_COLORS)


def main():
    print("fixture: %s (specimen #%d, %d phases)"
          % (os.path.basename(PATH), SPEC_I, NPHASES))

    project = load_mud(PATH)
    win = MainWindow()
    win._set_project(project)
    spec = project.mixtures[0].specimens[SPEC_I]
    win.show_specimen_plots([spec])

    # Load path: a project saved with display_phases on gets its transient
    # per-phase curves recomputed at load, so they show without a manual F5.
    if spec.display_phases:
        check("load w/ phases on: curves recomputed at load",
              bool(getattr(spec, "phase_patterns", None)))
        check("load w/ phases on: action reflects the stored state (checked)",
              win.ui.actionShowPhases.isChecked())
        check("load w/ phases on: one phase-coloured line per phase drawn",
              _phase_lines(win) == NPHASES)

    # Force a clean 'off' baseline (independent of the fixture's stored value)
    # to exercise the on-demand recompute the toggle does.
    spec.display_phases = False
    spec.phase_patterns = None
    win.show_specimen_plots([spec])
    check("baseline: display_phases off -> action unchecked",
          not spec.display_phases and not win.ui.actionShowPhases.isChecked())
    check("baseline: per-phase curves cleared", spec.phase_patterns is None)
    check("baseline: no phase-coloured lines on the plot", _phase_lines(win) == 0)

    # User ticks the menu item.
    win.ui.actionShowPhases.setChecked(True)
    check("toggle on: display_phases set on the shown specimen",
          spec.display_phases is True)
    check("toggle on: recomputed so per-phase curves now exist",
          bool(getattr(spec, "phase_patterns", None)))
    check("toggle on: one phase-coloured line per phase drawn",
          _phase_lines(win) == NPHASES)

    # User unticks it.
    win.ui.actionShowPhases.setChecked(False)
    check("toggle off: display_phases cleared", spec.display_phases is False)
    check("toggle off: phase-coloured lines gone", _phase_lines(win) == 0)

    # A per-specimen edit (what the specimen dialog / tree toggles do) must be
    # mirrored by the checkmark without looping back through the handler.
    win.ui.actionShowPhases.setChecked(True)  # display_phases on again
    spec.display_phases = False               # direct model edit -> rebuild
    check("mirror: direct display_phases edit unchecks the action",
          not win.ui.actionShowPhases.isChecked())
    check("mirror: and the curves are gone", _phase_lines(win) == 0)

    # Empty selection: toggling is a no-op, never raises.
    win.show_specimen_plots([])
    try:
        win.ui.actionShowPhases.setChecked(True)
        no_raise = True
    except Exception:  # noqa: BLE001
        no_raise = False
    check("empty selection: toggling is a safe no-op", no_raise)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- show-phases action verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
