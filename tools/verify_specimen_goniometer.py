#!/usr/bin/env python
"""Every specimen owns a goniometer, so the Edit Specimen > Goniometer tab is
editable for a freshly imported / added specimen (it used to grey out because
Specimen.__init__ left goniometer = None, and import / Add specimen never set
one).

  - a fresh Specimen has a goniometer with a sane default wavelength;
  - the import path (Specimen + set_experimental_pattern) keeps it;
  - Edit Specimen enables the Goniometer tab for such a specimen;
  - a .mud load still overwrites the default from the file (round-trip intact);
  - a fresh specimen's default goniometer round-trips (save then reload).

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_specimen_goniometer.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication

from mudlab.edit_specimen_dialog import EditSpecimenDialog
from mudlab.file_parsers.mud_project import load_mud, save_mud
from mudlab.models import Project, Specimen

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def main():
    # 1. A fresh specimen has a goniometer with a sane wavelength.
    spec = Specimen(name="imported")
    check("a fresh specimen has a goniometer (not None)",
          spec.goniometer is not None)
    check("its default wavelength is sane (~CuKa 0.1541 nm)",
          spec.goniometer is not None
          and abs(spec.goniometer.wavelength - 0.154056) < 1e-6)

    # 2. The import path (parse -> Specimen -> set_experimental_pattern) keeps it.
    spec.set_experimental_pattern(np.linspace(5, 70, 100), np.ones(100))
    check("an imported specimen (with data) still has a goniometer",
          spec.goniometer is not None and spec.has_experimental_data)

    # 3. Edit Specimen enables the Goniometer tab for it.
    dialog = EditSpecimenDialog()
    dialog.bind_specimen(spec)
    check("Edit Specimen enables the Goniometer tab (not greyed)",
          dialog.goniometer.isEnabled())
    check("the tab is bound to the specimen's goniometer",
          dialog.goniometer._goniometer is spec.goniometer)

    # 4. A .mud load still overwrites the default from the file.
    fixture = None
    for p in [os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")] + \
            sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        if os.path.isfile(p):
            fixture = p
            break
    if fixture is not None:
        project = load_mud(fixture)
        loaded = next((s for s in project.specimens
                       if s is not None and s.goniometer is not None), None)
        # The loaded goniometer reflects the file (e.g. its 2θ range), i.e. it is
        # not just the bare default we now start from.
        check("a loaded specimen's goniometer comes from the file",
              loaded is not None
              and "goniometer" in loaded.raw_properties)
    else:
        print("  (no fixture; skipped the load-overwrite check)")

    # 5. A fresh specimen's default goniometer round-trips through save/reload.
    proj = Project(name="p")
    fresh = Specimen(name="fresh")
    fresh.set_experimental_pattern(np.linspace(5, 70, 50), np.ones(50))
    proj.add_specimen(fresh)
    tmp = os.path.join(tempfile.mkdtemp(), "p.mud")
    save_mud(proj, tmp)
    back = load_mud(tmp).specimens[0]
    check("a fresh specimen's goniometer survives save/reload",
          back.goniometer is not None
          and abs(back.goniometer.wavelength - 0.154056) < 1e-6)

    _check_live_recompute()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("--- specimen-goniometer verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


def _settle(win, limit=10.0):
    """Spin until the main window's coalescing goniometer timer has fired."""
    app.processEvents()
    deadline = time.time() + limit
    while win._gonio_timer.isActive() and time.time() < deadline:
        app.processEvents()
    app.processEvents()


def _check_live_recompute():
    """`Goniometer.data_changed` had NO listeners: a geometry edit updated the
    model but the calculated curve kept the geometry it was last computed with,
    and the project was not even marked dirty (so the edit could be lost on
    close without a prompt). Every parameter is calc input, so a change must
    recompute - coalesced, and WITHOUT starting the optimiser."""
    from mudlab.main_window import MainWindow

    fixture = next((p for p in sorted(glob.glob(
        os.path.join(_REPO, "tools", "sample_projects", "*.mud")))), None)
    if fixture is None:
        print("  (no fixture; skipped the live-recompute checks)")
        return
    project = load_mud(fixture)
    row = next((i for i, s in enumerate(project.specimens)
                if s is not None and s.has_calculated_data), None)
    if row is None:
        print("  (no calculated specimen; skipped the live-recompute checks)")
        return

    win = MainWindow()
    win._set_project(project)
    win.select_specimen_row(row)
    spec = project.specimens[row]
    check("goniometer signals are wired for every specimen",
          len(win._gonio_wired) == len([s for s in project.specimens if s is not None]))

    win._dirty = False
    before = spec.calculated_pattern[1].copy()
    spec.goniometer.radius = spec.goniometer.radius + 3.0
    check("a goniometer edit marks the project dirty at once", win._dirty)
    check("...and arms the coalescing recompute", win._gonio_timer.isActive())
    _settle(win)
    check("a radius edit recomputes the calculated pattern",
          not np.allclose(before, spec.calculated_pattern[1]))

    # A wavelength change moves the peaks - the case that silently did nothing.
    before = spec.calculated_pattern[1].copy()
    spec.goniometer.set_wavelength_distribution([(0.178897, 1.0)])  # Cu -> Co
    _settle(win)
    check("an emission-spectrum edit recomputes the calculated pattern",
          not np.allclose(before, spec.calculated_pattern[1]))

    # A burst of edits collapses into ONE recompute (a spinbox drag).
    calls = {"n": 0}
    real = win.project.calculate

    def counted():
        calls["n"] += 1
        return real()

    win.project.calculate = counted
    for step in range(6):
        spec.goniometer.radius = 20.0 + step
    _settle(win)
    check("a burst of edits coalesces into one recompute", calls["n"] == 1)
    win.project.calculate = real

    # It must NOT run the optimiser: refresh() would, calculate() must not.
    ran = {"refresh": False}
    win.project.refresh = lambda: ran.__setitem__("refresh", True)
    spec.goniometer.soller1 = 1.7
    _settle(win)
    check("the recompute does not start the optimiser (no refresh())",
          not ran["refresh"])

    # A loaded stored setup (one signal for ~15 parameters) also recomputes.
    before = spec.calculated_pattern[1].copy()
    setup = spec.goniometer.to_dict()["properties"]
    setup["radius"] = 30.0
    spec.goniometer.apply_setup(setup)
    _settle(win)
    check("applying a stored .gon setup recomputes",
          not np.allclose(before, spec.calculated_pattern[1]))

    # The payoff of marking dirty: the close guard now protects a
    # goniometer-ONLY edit, which used to be discarded without a prompt.
    check("an unsaved goniometer edit is protected by the close guard", win._dirty)

    # AUDIT: one edit must cost ONE plot refresh. calculate() re-emits
    # data_changed per specimen and each rebuilt every plot, so an edit was
    # costing one refresh per specimen PLUS the explicit one.
    refreshes = {"n": 0}
    real_refresh = win._refresh_plots

    def counted_refresh():
        refreshes["n"] += 1
        return real_refresh()

    win._refresh_plots = counted_refresh
    spec.goniometer.radius = 26.5
    _settle(win)
    check("one goniometer edit costs exactly one plot refresh",
          refreshes["n"] == 1)
    win._refresh_plots = real_refresh
    win._dirty = False   # ...so this harness can close without that prompt
    win.close()

    # AUDIT: a recompute still pending from the OUTGOING project must not fire
    # against the incoming one - it recomputed a freshly loaded project and
    # marked it dirty.
    win2 = MainWindow()
    first = load_mud(fixture)
    win2._set_project(first)
    row2 = next(i for i, s in enumerate(first.specimens) if s is not None)
    win2.select_specimen_row(row2)
    first.specimens[row2].goniometer.radius += 2.0      # arms the timer
    armed = win2._gonio_timer.isActive()
    win2._set_project(load_mud(fixture))                # swap before it fires
    win2._dirty = False
    check("a pending recompute is dropped when the project is swapped",
          armed and not win2._gonio_timer.isActive())
    _settle(win2)
    check("...so a freshly loaded project is not marked dirty", not win2._dirty)
    win2._dirty = False
    win2.close()


if __name__ == "__main__":
    sys.exit(main())
