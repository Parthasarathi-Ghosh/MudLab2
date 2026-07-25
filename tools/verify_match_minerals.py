#!/usr/bin/env python
"""Durable harness for the Match Minerals wiring, run head-less.

The Match Minerals dialog shipped as a placeholder: 10 hard-coded demo mineral
names, no scoring, no label output. This harness drives the wired dialog and
asserts it (a) loads the real reference set, (b) scores it against the target
markers' peaks exactly as calculations.peak_detection.score_minerals does, and
(c) writes the chosen abbreviations onto the marker labels.

A synthetic specimen is built whose experimental pattern has Gaussians exactly
at Quartz's strongest reflections, with markers placed on them, so the match is
deterministic and Quartz must score at the top. The scoring numerics
themselves are guarded by verify_peak_detection.py.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_match_minerals.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from collections import Counter

import numpy as np
from PySide6.QtWidgets import QApplication

from mudlab.calculations import get_2t_from_nm, peak_detection as pd
from mudlab.edit_markers_dialog import EditMarkersDialog
from mudlab.match_minerals_dialog import MatchMineralsDialog, _INDEX_ROLE
from mudlab.models.marker import Marker
from mudlab.models.specimen import DEFAULT_WAVELENGTH, Specimen

app = QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


_MINERALS = pd.load_mineral_references()
_BY_NAME = {name: (abbr, peaks) for name, abbr, peaks in _MINERALS}
_QUARTZ = next(n for n in _BY_NAME if n.startswith("Quartz"))


def quartz_specimen():
    """A specimen whose experimental pattern is Gaussians at Quartz's 8
    strongest reflections, with a marker placed on each."""
    abbr, peaks = _BY_NAME[_QUARTZ]
    top = sorted(peaks, key=lambda p: p[1], reverse=True)[:8]
    wl = DEFAULT_WAVELENGTH
    positions_2t = [(get_2t_from_nm(d / 10.0, wl), inten) for d, inten in top]

    x = np.linspace(5.0, 80.0, 6000)
    y = np.full_like(x, 2.0)
    for pos, inten in positions_2t:
        y = y + inten * np.exp(-0.5 * ((x - pos) / 0.12) ** 2)

    spec = Specimen(name="quartz-synth")
    spec.set_experimental_pattern(x, y)
    for pos, _inten in positions_2t:
        spec.add_marker(Marker(label="pk", position=pos))
    return spec


def specimen_for_mineral(idx):
    """A specimen with Gaussians + markers at reference-mineral `idx`'s strongest
    reflections (those with a Bragg solution inside 5-80 deg 2theta)."""
    _name, _abbr, peaks = _MINERALS[idx]
    wl = DEFAULT_WAVELENGTH
    positions = []
    for d, inten in sorted(peaks, key=lambda p: p[1], reverse=True):
        nm = d / 10.0
        if nm <= wl / 2:
            continue  # no Bragg solution (d < lambda/2)
        two_t = get_2t_from_nm(nm, wl)
        if 5.0 < two_t < 80.0:
            positions.append((two_t, inten))
        if len(positions) >= 8:
            break
    x = np.linspace(5.0, 80.0, 6000)
    y = np.full_like(x, 2.0)
    for pos, inten in positions:
        y = y + inten * np.exp(-0.5 * ((x - pos) / 0.12) ** 2)
    spec = Specimen(name="mineral-synth")
    spec.set_experimental_pattern(x, y)
    for pos, _inten in positions:
        spec.add_marker(Marker(label="pk", position=pos))
    return spec


def _minerals_row_for_index(dlg, idx):
    for row in range(dlg.minerals_model.rowCount()):
        if dlg.minerals_model.item(row, 0).data(_INDEX_ROLE) == idx:
            return row
    return None


# ----------------------------------------------------------------------
# Dialog: load / peaks / scoring
# ----------------------------------------------------------------------
def check_loads_reference_set():
    spec = quartz_specimen()
    dlg = MatchMineralsDialog(specimen=spec, targets=list(spec.markers))
    check("loads full reference set (228 minerals)",
          dlg.minerals_model.rowCount() == 228)
    # Not the old placeholder set.
    names = {dlg.minerals_model.item(r, 0).text() for r in range(dlg.minerals_model.rowCount())}
    check("reference set is real (contains Quartz, not demo-only)",
          _QUARTZ in names and "Smectite" not in names)
    dlg.deleteLater()


def check_marker_peaks_conversion():
    spec = quartz_specimen()
    dlg = MatchMineralsDialog(specimen=spec, targets=list(spec.markers))
    x, y = spec.experimental_pattern
    ok = len(dlg._marker_peaks) == len(spec.markers)
    for (ang, inten), marker in zip(dlg._marker_peaks, spec.markers):
        expect_ang = marker.get_nm_position() * 10.0
        expect_int = float(np.interp(marker.position, x, y))
        ok = ok and abs(ang - expect_ang) < 1e-9 and abs(inten - expect_int) < 1e-6
    check("marker peaks = (d-angstrom, exp intensity)", ok)
    dlg.deleteLater()


def check_auto_match_scores():
    spec = quartz_specimen()
    dlg = MatchMineralsDialog(specimen=spec, targets=list(spec.markers))
    # Auto match ran on open. Compare to score_minerals directly.
    expected = pd.score_minerals(dlg._marker_peaks, _MINERALS)
    n = dlg.matches_model.rowCount()
    same = n == len(expected)
    scores = []
    for row in range(n):
        name = dlg.matches_model.item(row, 0).text()
        abbr = dlg.matches_model.item(row, 1).text()
        score = float(dlg.matches_model.item(row, 2).text())
        scores.append(score)
        same = same and name == expected[row][0] and abbr == expected[row][1] \
            and abs(score - expected[row][4]) < 1e-4
    check("auto match rows == score_minerals output (names/abbr/scores/order)", same)
    check("matches sorted by descending score",
          scores == sorted(scores, reverse=True))
    # Quartz self-match must land at the very top.
    top_names = [dlg.matches_model.item(r, 0).text() for r in range(min(5, n))]
    check("Quartz scores in the top 5 of its own pattern", _QUARTZ in top_names)
    dlg.deleteLater()


def check_manual_add_remove():
    spec = quartz_specimen()
    dlg = MatchMineralsDialog(specimen=spec, targets=list(spec.markers))
    dlg.matches_model.removeRows(0, dlg.matches_model.rowCount())
    # Select a specific mineral in the all-minerals list and add it.
    target_name = _QUARTZ
    row = next(r for r in range(dlg.minerals_model.rowCount())
               if dlg.minerals_model.item(r, 0).text() == target_name)
    dlg.ui.tv_minerals.setCurrentIndex(dlg.minerals_model.index(row, 0))
    dlg._add_selected_match()
    added = dlg.matches_model.rowCount() == 1 \
        and dlg.matches_model.item(0, 0).text() == target_name
    check("manual add: selected mineral added to matches", added)
    # Adding the same one again is a no-op (no duplicate).
    dlg._add_selected_match()
    check("manual add: no duplicate rows", dlg.matches_model.rowCount() == 1)
    # Remove it.
    dlg.ui.tv_matches.setCurrentIndex(dlg.matches_model.index(0, 0))
    dlg._remove_selected_match()
    check("manual remove: match removed", dlg.matches_model.rowCount() == 0)
    dlg.deleteLater()


# ----------------------------------------------------------------------
# Append labels
# ----------------------------------------------------------------------
def check_append_labels():
    spec = quartz_specimen()
    targets = list(spec.markers)
    dlg = MatchMineralsDialog(specimen=spec, targets=targets)
    abbr = _BY_NAME[_QUARTZ][0]
    # Select the Quartz match row.
    q_row = next(r for r in range(dlg.matches_model.rowCount())
                 if dlg.matches_model.item(r, 0).text() == _QUARTZ)
    dlg.ui.tv_matches.setCurrentIndex(dlg.matches_model.index(q_row, 0))

    fired = []
    dlg.applied.connect(lambda: fired.append(1))
    before = [m.label for m in targets]
    dlg._on_apply()

    appended = all(
        m.label == f"{b}, {abbr}" and m.anno_label == ""
        for m, b in zip(targets, before)
    )
    check("append labels: abbreviation appended to every target", appended)
    check("append labels: emits applied signal", len(fired) == 1)

    # Applying the same abbreviation again must not duplicate it.
    dlg._on_apply()
    no_dup = all(m.label.count(abbr) == 1 for m in targets)
    check("append labels: re-apply does not duplicate", no_dup)
    dlg.deleteLater()


# ----------------------------------------------------------------------
# EditMarkers launch wiring
# ----------------------------------------------------------------------
def check_edit_markers_wiring():
    spec = quartz_specimen()
    ed = EditMarkersDialog(specimen=spec)
    # Select the first marker so Match minerals is enabled with that target.
    ed.ui.edit_objects_treeview.setCurrentIndex(ed.objects_model.index(0, 0))
    check("Match minerals enabled once a marker is selected",
          ed.btn_match_minerals.isEnabled())
    ed._on_match_minerals()
    dlg = getattr(ed, "_match_dialog", None)
    ok = isinstance(dlg, MatchMineralsDialog) and dlg.targets == [spec.markers[0]]
    check("_on_match_minerals opens dialog with the selected marker as target", ok)

    # Apply from the launched dialog reloads the host list without error.
    if dlg is not None and dlg.matches_model.rowCount():
        dlg.ui.tv_matches.setCurrentIndex(dlg.matches_model.index(0, 0))
        dlg._on_apply()
        row0 = ed.objects_model.item(0, 0)
        check("host marker list refreshes after append",
              row0 is not None and row0.text() == spec.markers[0].label)
    ed.deleteLater()


def check_duplicate_name_manual_add():
    """Bug B regression: the reference set has duplicate names (e.g. two
    "Albite, ordered"). Manually adding each must add a distinct row using its
    OWN peaks, not collapse to one entry with the last duplicate's peaks."""
    names = [n for n, _, _ in _MINERALS]
    dup_name = next(n for n, c in Counter(names).items() if c > 1)
    dup_indices = [i for i, (n, _, _) in enumerate(_MINERALS) if n == dup_name][:2]
    check("Bug B: a duplicate-named reference pair exists to test",
          len(dup_indices) == 2)

    # Markers on the FIRST duplicate's reflections, so the two entries score
    # differently (their peak lists differ) - proving distinct peaks are used.
    spec = specimen_for_mineral(dup_indices[0])
    dlg = MatchMineralsDialog(specimen=spec, targets=list(spec.markers))
    dlg.matches_model.removeRows(0, dlg.matches_model.rowCount())

    for idx in dup_indices:
        row = _minerals_row_for_index(dlg, idx)
        dlg.ui.tv_minerals.setCurrentIndex(dlg.minerals_model.index(row, 0))
        dlg._add_selected_match()

    check("Bug B: both duplicate-named entries added (not collapsed to one)",
          dlg.matches_model.rowCount() == 2)
    stored = {dlg.matches_model.item(r, 0).data(_INDEX_ROLE) for r in range(2)}
    check("Bug B: match rows keep their distinct source indices",
          stored == set(dup_indices))
    # Each row's score must equal the individual score of ITS OWN reference
    # peaks - the tell that the correct duplicate's peaks were used.
    scored_ok = True
    for r in range(2):
        idx = dlg.matches_model.item(r, 0).data(_INDEX_ROLE)
        shown = float(dlg.matches_model.item(r, 2).text())
        scored = pd.score_minerals(dlg._marker_peaks, [_MINERALS[idx]])
        expect = scored[0][4] if scored else 0.0
        scored_ok = scored_ok and abs(shown - expect) < 1e-4
    check("Bug B: each row scored from its own peaks", scored_ok)
    # Re-adding the exact same row is still a no-op (dedup by identity).
    row = _minerals_row_for_index(dlg, dup_indices[0])
    dlg.ui.tv_minerals.setCurrentIndex(dlg.minerals_model.index(row, 0))
    dlg._add_selected_match()
    check("Bug B: re-adding the same row does not duplicate it",
          dlg.matches_model.rowCount() == 2)
    dlg.deleteLater()


def main():
    check_loads_reference_set()
    check_duplicate_name_manual_add()
    check_marker_peaks_conversion()
    check_auto_match_scores()
    check_manual_add_remove()
    check_append_labels()
    check_edit_markers_wiring()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- Match Minerals verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
