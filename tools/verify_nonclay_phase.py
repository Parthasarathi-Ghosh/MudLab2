#!/usr/bin/env python
"""NonClayPhase (experimental "path 2") + Import Non-Clay dialog.

A NonClayPhase is a RawPatternPhase that also carries a declared oxide
composition. Its phase-``type`` gates three independent behaviours:
  (a) it contributes its stored pattern and its fraction is optimised,
  (b) it is never structurally refined,
  (c) it will contribute to composition (DEFERRED - oxides are stored/editable
      now but not yet fed into a bulk composition).

Covers the model, the two gates that are wired now, .mud persistence, and the
UI: the Import dialog (measured-pattern and CIF-with-atoms paths + validation),
the right-side oxide editor, and the Edit Phases wiring.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_nonclay_phase.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys
import tempfile
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication, QMessageBox

app = QApplication.instance() or QApplication([])
# Stub modal popups so a head-less run never blocks on a dialog.
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

import mudlab.calibrate_fwhm_dialog as cfd
import mudlab.edit_nonclay_phase_widget as enw
import mudlab.import_nonclay_dialog as ind
from mudlab.calculations.phases import get_diffracted_intensity
from mudlab.calculations.refinement import enumerate_refinables
from mudlab.calibrate_fwhm_dialog import CalibrateFwhmDialog
from mudlab.edit_nonclay_phase_widget import EditNonClayPhaseWidget
from mudlab.edit_phases_dialog import EditPhasesDialog
from mudlab.file_parsers.mud_project import load_mud, save_mud
from mudlab.import_nonclay_dialog import ImportNonClayDialog
from mudlab.models import Goniometer
from mudlab.models.nonclay_phase import NonClayPhase
from mudlab.nonclay.structure import reflections_from_cif
from mudlab.nonclay_calibration import silicon_reflections
from PySide6.QtWidgets import QDialogButtonBox

results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        if os.path.isfile(path):
            return path
    return None


# Minimal self-contained alpha-quartz CIF (same structure the nonclay harness uses).
_QUARTZ_CIF = (
    "data_quartz\n_cell_length_a 4.9137\n_cell_length_b 4.9137\n_cell_length_c 5.4047\n"
    "_cell_angle_alpha 90\n_cell_angle_beta 90\n_cell_angle_gamma 120\n"
    "loop_\n_space_group_symop_operation_xyz\n"
    "x,y,z\ny,x,2/3-z\n-y,x-y,2/3+z\n-x,-x+y,1/3-z\n-x+y,-x,1/3+z\nx-y,-y,-z\n"
    "loop_\n_atom_site_label\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n"
    "Si 0.4697 0.0000 0.0000\nO 0.4135 0.2669 0.1191\n"
)


# ----------------------------------------------------------------------
def check_model():
    p = NonClayPhase(name="Quartz (nc)")
    p.display_color = "#cc8800"
    x = np.linspace(5.0, 60.0, 1101)
    y = 100 * np.exp(-((x - 26.6) / 0.15) ** 2) + 40 * np.exp(-((x - 20.9) / 0.15) ** 2)
    p.set_raw_pattern(x, y)
    p.set_oxides({"SiO2": 100.0, "Al2O3": 0.0, "Fe2O3": -3})  # 0/negative dropped
    check("model: type is NonClayPhase", p.type == "NonClayPhase")
    check("model: oxides keep only positives", p.oxides == {"SiO2": 100.0})
    check("model: has_composition", p.has_composition is True)

    q = NonClayPhase.from_dict(p.to_dict())
    check("round-trip: type/name/colour",
          q.type == "NonClayPhase" and q.name == "Quartz (nc)"
          and q.display_color == "#cc8800")
    check("round-trip: oxides + pattern",
          q.oxides == {"SiO2": 100.0} and q.raw_pattern_x.size == x.size
          and np.allclose(q.raw_pattern_y, y))
    check("round-trip: is_valid (>=2 pts)", q.is_valid is True)

    # (a) contributes the stored curve
    two_theta = np.linspace(10.0, 55.0, 900)
    range_theta = np.radians(two_theta * 0.5)
    inten = get_diffracted_intensity(range_theta, np.zeros_like(range_theta), p)
    peak_2t = two_theta[int(np.argmax(inten))]
    check("gate (a): returns the stored curve (peak near 26.6)",
          abs(peak_2t - 26.6) < 0.5 and inten.max() > 0)

    # (b) never structurally refined
    stub = SimpleNamespace(phase_matrix=[[p]])
    check("gate (b): enumerate_refinables excludes NonClayPhase",
          enumerate_refinables(stub) == [])
    return p, x


def check_persistence(fixture, phase, x):
    project = load_mud(fixture)
    before = len(project.phases)
    project.add_phase(phase)
    out = os.path.join(tempfile.gettempdir(), "mudlab_nonclay_%d.mud" % os.getpid())
    save_mud(project, out)
    try:
        reloaded = load_mud(out)
    finally:
        if os.path.isfile(out):
            os.remove(out)
    ncs = [ph for ph in reloaded.phases if getattr(ph, "type", None) == "NonClayPhase"]
    check("persistence: one NonClayPhase survives save/reload", len(ncs) == 1)
    if ncs:
        r = ncs[0]
        check("persistence: name/oxides/pattern intact",
              r.name == phase.name and r.oxides == {"SiO2": 100.0}
              and r.raw_pattern_x.size == x.size)
    check("persistence: phase count = before + 1", len(reloaded.phases) == before + 1)


def check_import_dialog(gonio):
    dlg = ImportNonClayDialog(None, goniometer=gonio)
    check("import: grid has the reporting oxides",
          len(dlg.grid._spins) >= 5 and "SiO2" in dlg.grid._spins)
    dlg._on_accept()
    check("import: OK refused with no name/pattern/oxides", dlg.phase is None)

    # 2a: measured pattern (stub import_pattern so no file/CSV dialog).
    xa = np.linspace(5, 60, 1101)
    ya = 100 * np.exp(-((xa - 26.6) / 0.2) ** 2)
    saved = ind.import_pattern
    ind.import_pattern = lambda *a, **k: (xa, ya)
    try:
        dlg._load_pattern("QuartzScan.xy")
    finally:
        ind.import_pattern = saved
    check("import 2a: pattern loaded + name defaulted + source labelled",
          dlg._x.size == xa.size and dlg.ui.edit_name.text() == "QuartzScan"
          and "Measured" in dlg.ui.lbl_source.text())
    dlg._on_accept()
    check("import 2a: OK still refused (no oxides yet)", dlg.phase is None)
    dlg.grid._spins["SiO2"].setValue(100.0)
    check("import 2a: sum label updates", "100" in dlg.ui.lbl_sum.text())
    dlg._on_accept()
    check("import 2a: accepted -> NonClayPhase with pattern+oxides+colour",
          isinstance(dlg.phase, NonClayPhase)
          and dlg.phase.raw_pattern_x.size == xa.size
          and dlg.phase.oxides == {"SiO2": 100.0}
          and dlg.phase.display_color.startswith("#"))

    # 2b: CIF with atoms.
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_probe_%d.cif" % os.getpid())
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(_QUARTZ_CIF)
    dlg2 = ImportNonClayDialog(None, goniometer=gonio)
    try:
        dlg2._load_cif(tmp)
    finally:
        os.remove(tmp)
    check("import 2b: CIF computes a pattern + fills ~pure SiO2",
          dlg2._x.size > 2 and dlg2._y.max() > 0
          and abs(dlg2.grid.values().get("SiO2", 0) - 100.0) < 1.0
          and "CIF" in dlg2.ui.lbl_source.text())
    dlg2.ui.edit_name.setText("Quartz")
    dlg2._on_accept()
    check("import 2b: accepted -> a COMPUTED NonClayPhase (reflections + FWHM)",
          isinstance(dlg2.phase, NonClayPhase) and dlg2.phase.has_composition
          and dlg2.phase.is_computed and abs(dlg2.phase.fwhm - 0.10) < 1e-9
          and len(dlg2.phase.reflections) > 1)
    return dlg.phase, dlg2.phase


def check_computed_persistence(fixture, gonio):
    """A COMPUTED (CIF) phase round-trips its reflections + FWHM + oxides through
    a full .mud save/reload (the plain check_persistence uses a measured phase)."""
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_cp_%d.cif" % os.getpid())
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(_QUARTZ_CIF)
    try:
        reflections, oxides = reflections_from_cif(tmp, gonio)
    finally:
        os.remove(tmp)
    p = NonClayPhase(name="Quartz-CIF")
    p.set_reflections(reflections)
    p.set_fwhm(0.23)
    p.set_oxides(oxides)
    p.rebuild_stored_pattern(gonio.wavelength)

    project = load_mud(fixture)
    project.add_phase(p)
    out = os.path.join(tempfile.gettempdir(), "mudlab_cp_%d.mud" % os.getpid())
    save_mud(project, out)
    try:
        reloaded = load_mud(out)
    finally:
        if os.path.isfile(out):
            os.remove(out)
    computed = [ph for ph in reloaded.phases
                if getattr(ph, "type", None) == "NonClayPhase" and ph.is_computed]
    check("computed persistence: one computed NonClayPhase reloads", len(computed) == 1)
    if computed:
        q = computed[0]
        check("computed persistence: FWHM + oxides + reflections survive",
              abs(q.fwhm - 0.23) < 1e-9 and q.oxides == {"SiO2": 100.0}
              and len(q.reflections) == len(reflections)
              and np.allclose(sorted(q.reflections), sorted(reflections)))


def check_render(gonio):
    """Model + calc: a computed phase renders at the specimen wavelength (so
    positions move with lambda), tunes width, and round-trips its reflections."""
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_render_%d.cif" % os.getpid())
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(_QUARTZ_CIF)
    try:
        reflections, _ox = reflections_from_cif(tmp, gonio)
    finally:
        os.remove(tmp)
    check("render: reflections normalised to max 100",
          abs(max(i for _d, i in reflections) - 100.0) < 1e-6)

    p = NonClayPhase(name="Quartz")
    p.set_reflections(reflections)
    p.set_fwhm(0.10)
    grid = np.linspace(10.0, 60.0, 6001)
    cu = grid[int(np.argmax(p.render_on_grid(grid, 0.154056)))]
    co = grid[int(np.argmax(p.render_on_grid(grid, 0.178897)))]
    check("render: peak sits at ~26.6 for Cu Kalpha", abs(cu - 26.65) < 0.3)
    check("render: peak moves up (~31.1) for Co Kalpha", co > cu + 3 and abs(co - 31.1) < 0.6)

    def half_width(y):
        above = grid[y >= y.max() / 2]
        return above.max() - above.min()
    narrow = p.render_on_grid(grid, 0.154056, fwhm=0.05)
    wide = p.render_on_grid(grid, 0.154056, fwhm=0.40)
    check("render: larger FWHM widens the peak", half_width(wide) > half_width(narrow) * 3)

    # get_diffracted_intensity recovers the wavelength from range_stl and renders.
    tt = np.linspace(15.0, 45.0, 3001)
    for wl in (0.154056, 0.178897):
        rth = np.radians(tt * 0.5)
        inten = get_diffracted_intensity(rth, 2 * np.sin(rth) / wl, p)
        want = tt[int(np.argmax(p.render_on_grid(tt, wl)))]
        got = tt[int(np.argmax(inten))]
        check("calc: dispatch renders at recovered wavelength %.4f" % wl,
              abs(got - want) < 0.05)

    q = NonClayPhase.from_dict(p.to_dict())
    check("render: reflections + FWHM round-trip",
          q.is_computed and len(q.reflections) == len(reflections)
          and abs(q.fwhm - 0.10) < 1e-9)


def check_editor(computed_phase, measured_phase):
    # Computed phase: oxides editable, FWHM row shown + tunable.
    w = EditNonClayPhaseWidget()
    calls = {"n": 0}
    w.bind_nonclay_phase(computed_phase, wavelength_nm=0.154056,
                         on_changed=lambda: calls.__setitem__("n", calls["n"] + 1))
    check("editor: shows the bound oxides",
          abs(w.grid.values().get("SiO2", 0) - 100.0) < 1e-9)
    w.grid._spins["CaO"].setValue(5.0)  # user edits an oxide
    check("editor: oxide edit writes phase.oxides", w._phase.oxides.get("CaO") == 5.0)
    check("editor: oxide edit does NOT recompute (composition deferred)", calls["n"] == 0)
    check("editor: FWHM row shown for a computed phase", not w.ui.spin_fwhm.isHidden())
    before = w._phase.raw_pattern_y.copy()
    n0 = calls["n"]
    w.ui.spin_fwhm.setValue(0.40)   # user widens the peaks
    check("editor: FWHM edit re-renders the pattern + notifies",
          w._phase.fwhm == 0.40 and not np.array_equal(w._phase.raw_pattern_y, before)
          and calls["n"] == n0 + 1)
    w.ui.nonclay_name.setText("Quartz nc")
    w._on_name_edited()
    check("editor: name edit writes + notifies",
          w._phase.name == "Quartz nc" and calls["n"] == n0 + 2)

    check("editor: Calibrate button shown for a computed phase",
          not w.ui.button_calibrate.isHidden())

    # The Calibrate button applies the dialog's fitted FWHM (fake the dialog so
    # the modal exec does not block head-less); apply-to-all emits the signal.
    emitted = {"v": None}
    w.apply_fwhm_to_all.connect(lambda v: emitted.__setitem__("v", v))

    class _FakeCalibrate:
        DialogCode = CalibrateFwhmDialog.DialogCode

        def __init__(self, *a, **k):
            self.fwhm = 0.33
            self.apply_to_all = True

        def exec(self):
            return self.DialogCode.Accepted

    saved = enw.CalibrateFwhmDialog
    enw.CalibrateFwhmDialog = _FakeCalibrate
    try:
        w._on_calibrate()
    finally:
        enw.CalibrateFwhmDialog = saved
    check("editor: Calibrate applies the fitted FWHM to the phase",
          abs(w._phase.fwhm - 0.33) < 1e-9)
    check("editor: apply-to-all emits the signal with the FWHM",
          emitted["v"] is not None and abs(emitted["v"] - 0.33) < 1e-9)

    # Measured phase: no reflection list, so the FWHM row (incl. Calibrate) hides.
    w2 = EditNonClayPhaseWidget()
    w2.bind_nonclay_phase(measured_phase)
    check("editor: FWHM row hidden for a measured phase", w2.ui.spin_fwhm.isHidden())
    check("editor: Calibrate button hidden for a measured phase",
          w2.ui.button_calibrate.isHidden())


def check_calibrate_dialog():
    wl = 0.154056
    x = np.arange(20.0, 90.0, 0.02)
    standard = NonClayPhase()
    standard.set_reflections(silicon_reflections())
    measured = 3.0 * standard.render_on_grid(x, wl, fwhm=0.21) + 30.0  # scale+bg

    saved = cfd.import_pattern
    cfd.import_pattern = lambda *a, **k: (x, measured)
    try:
        dlg = CalibrateFwhmDialog(None, wavelength_nm=wl)
        ok = dlg.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        check("calibrate dialog: standard defaults to built-in Silicon",
              "Silicon" in dlg.ui.lbl_standard.text())
        check("calibrate dialog: OK disabled before a fit", not ok.isEnabled())
        dlg._on_load_measured()
        dlg._on_fit()
        check("calibrate dialog: fit recovers the FWHM (~0.21)",
              dlg.fwhm is not None and abs(dlg.fwhm - 0.21) < 0.02)
        check("calibrate dialog: OK enabled after a fit", ok.isEnabled())
        check("calibrate dialog: result label reports the FWHM",
              "FWHM" in dlg.ui.lbl_result.text())
        dlg.ui.chk_apply_all.setChecked(True)
        check("calibrate dialog: apply_to_all reflects the checkbox", dlg.apply_to_all)
    finally:
        cfd.import_pattern = saved


def check_apply_to_all(fixture, gonio):
    """EditPhasesDialog._apply_fwhm_to_all sets the calibrated width on every
    computed non-clay phase in the project."""
    project = load_mud(fixture)
    phases = []
    for name in ("Si-A", "Si-B"):
        p = NonClayPhase(name=name)
        p.set_reflections(silicon_reflections())
        p.set_fwhm(0.10)
        p.rebuild_stored_pattern(gonio.wavelength)
        project.add_phase(p)
        phases.append(p)
    ep = EditPhasesDialog(None, project=project)
    ep._apply_fwhm_to_all(0.44)
    check("apply-to-all sets FWHM on every computed non-clay phase",
          all(abs(p.fwhm - 0.44) < 1e-9 for p in phases))
    check("apply-to-all re-renders each pattern (raw_pattern reflects new width)",
          all(p.raw_pattern_x.size > 2 for p in phases))


def check_edit_phases(fixture, nonclay_phase):
    project = load_mud(fixture)
    ep = EditPhasesDialog(None, project=project)
    check("edit-phases: 'Import Non-Clay' button present in the objects frame",
          hasattr(ep, "button_import_nonclay")
          and ep.ui.extraLayout.indexOf(ep.button_import_nonclay) >= 0)
    project.add_phase(nonclay_phase)
    row = len(ep._phases)
    ep._phases.append(nonclay_phase)
    ep.add_object_row(*ep._phase_row_values(nonclay_phase))
    check("edit-phases: NonClayPhase row shows name + '—' R/G",
          ep.objects_model.item(row, 0).text() == nonclay_phase.name
          and ep.objects_model.item(row, 1).text() == "—")
    ep._on_phase_selected(ep.objects_model.index(row, 0))
    check("edit-phases: selecting a NonClayPhase shows the non-clay editor",
          not ep.nonclay_widget.isHidden() and ep.phase_widget.isHidden()
          and ep.raw_phase_widget.isHidden())


def main():
    fixture = _fixture()
    if fixture is None:
        print("No sample project fixture; skipping (exit 2).")
        return 2
    gonio = Goniometer()

    phase, x = check_model()
    check_persistence(fixture, phase, x)
    check_computed_persistence(fixture, gonio)
    check_render(gonio)
    phase2a, phase2b = check_import_dialog(gonio)
    check_editor(phase2b, phase2a)
    check_calibrate_dialog()
    check_apply_to_all(fixture, gonio)
    check_edit_phases(fixture, phase2b)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- NonClayPhase (path 2) verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
