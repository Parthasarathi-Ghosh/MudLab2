#!/usr/bin/env python
"""Durable harness for stored goniometer setups (.gon), run head-less.

The goniometer tab's "Load setup" combo and "Store setup" button were
placeholders. This harness drives the wired feature + its parser/model support
and asserts:

  - gon_file load/save/list round-trips and reads every bundled preset;
  - Goniometer.apply_setup fully resets the modeled parameters from a setup
    (keeping the goniometer's own uuid), handling both the modern format
    (= our to_dict) and the legacy single-`lambda` files, and persists through
    a .mud save;
  - the GoniometerWidget populates the combo, loads a setup on pick (with a
    confirmation), stores the current setup to a .gon, and shows the applied
    name.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_goniometer_setup.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project.
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

# Modal boxes block head-less; record instead of show.
_boxes = []
for _name in ("warning", "critical", "information"):
    setattr(QMessageBox, _name, staticmethod(
        lambda parent, title, text, *a, _n=_name, **k: _boxes.append((_n, title, text))
    ))

import mudlab.goniometer_widget as gw
from mudlab.file_parsers.gon_file import (
    DEFAULT_GONIO_DIR, list_setups_in, load_gon, save_gon,
)
from mudlab.file_parsers.mud_project import load_mud, save_mud
from mudlab.goniometer_widget import GoniometerWidget
from mudlab.models import Goniometer

_FIXTURE_NAME = "308 r1.mud"
FIXTURE = os.path.join(_REPO, "tools", "sample_projects", _FIXTURE_NAME)
if not os.path.isfile(FIXTURE):
    FIXTURE = os.path.join(os.path.expanduser("~"), "Downloads", _FIXTURE_NAME)

app = QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _setup_index(widget, prefix):
    combo = widget.ui.cmb_import_gonio
    return next(i for i in range(combo.count())
               if combo.itemText(i).startswith(prefix))


# ----------------------------------------------------------------------
# Parser
# ----------------------------------------------------------------------
def check_parser():
    setups = list_setups_in(DEFAULT_GONIO_DIR)
    check("list_setups_in: 12 bundled presets, sorted", len(setups) == 12
          and [n for n, _ in setups] == sorted(n for n, _ in setups))
    check("list_setups_in: missing dir -> []", list_setups_in("/no/such/dir") == [])
    # Every bundled file loads to a properties dict.
    ok = all(isinstance(load_gon(p), dict) and load_gon(p) for _, p in setups)
    check("load_gon: every bundled preset parses", ok)
    # Non-goniometer JSON raises.
    bad = os.path.join(tempfile.mkdtemp(), "bad.gon")
    with open(bad, "w", encoding="utf-8") as handle:
        handle.write('{"nope": 1}')
    try:
        load_gon(bad)
        check("load_gon: non-setup file raises", False)
    except ValueError:
        check("load_gon: non-setup file raises", True)
    # save_gon -> load_gon round-trip.
    g = Goniometer()
    g.radius = 33.0
    out = os.path.join(tempfile.mkdtemp(), "rt.gon")
    save_gon(out, g.to_dict())
    check("save_gon/load_gon round-trip", load_gon(out).get("radius") == 33.0)


# ----------------------------------------------------------------------
# Model: apply_setup
# ----------------------------------------------------------------------
def check_apply_setup():
    modern = os.path.join(DEFAULT_GONIO_DIR, "D8 ECO Lynxeye XE.gon")
    g = Goniometer()
    uuid = g.uuid
    fired = []
    g.data_changed.connect(lambda: fired.append(1))
    g.apply_setup(load_gon(modern))
    check("apply_setup: modern preset applies scalars",
          g.steps == 6895 and g.radius == 25.0 and g.soller1 == 2.5)
    check("apply_setup: modern preset applies wavelength distribution",
          len(g.wavelength_distribution) == 4)
    check("apply_setup: keeps the goniometer's own uuid", g.uuid == uuid)
    check("apply_setup: emits data_changed once", len(fired) == 1)
    check("apply_setup: verbatim wld raw string invalidated",
          "wavelength_distribution" not in g.raw_properties)

    # Legacy single-lambda file -> a one-line distribution.
    legacy = os.path.join(DEFAULT_GONIO_DIR, "Default.gon")
    g2 = Goniometer()
    g2.apply_setup(load_gon(legacy))
    check("apply_setup: legacy 'lambda' -> one-line distribution",
          len(g2.wavelength_distribution) == 1
          and abs(g2.wavelength - 0.154056) < 1e-6)

    # Full reset: a key absent from the setup falls back to the default.
    g3 = Goniometer()
    g3.divergence_mode = "AUTOMATIC"  # not present in the legacy Default.gon
    g3.apply_setup(load_gon(legacy))
    check("apply_setup: missing key resets to default (full reset semantics)",
          g3.divergence_mode == "FIXED")


def check_persistence():
    if not os.path.isfile(FIXTURE):
        return  # covered when a fixture is present
    project = load_mud(FIXTURE)
    gonio = next((s.goniometer for s in project.specimens
                  if s.goniometer is not None), None)
    if gonio is None:
        return
    gonio.apply_setup(load_gon(os.path.join(DEFAULT_GONIO_DIR, "D8 ECO Lynxeye XE.gon")))
    tmp = os.path.join(tempfile.mkdtemp(), "applied.mud")
    save_mud(project, tmp)
    rg = next(s.goniometer for s in load_mud(tmp).specimens
              if s.goniometer is not None)
    check("persistence: applied setup survives a .mud save/reload",
          rg.steps == 6895 and rg.radius == 25.0
          and len(rg.wavelength_distribution) == 4)


# ----------------------------------------------------------------------
# Widget
# ----------------------------------------------------------------------
def check_widget_populate_and_load():
    w = GoniometerWidget()
    combo = w.ui.cmb_import_gonio
    check("widget: combo = placeholder + 12 presets",
          combo.count() == 13 and combo.itemData(0) is None)
    g = Goniometer()
    w.bind_goniometer(g)
    check("widget: bind clears applied label + resets combo",
          w.ui.lbl_applied_gonio.text() == "" and combo.currentIndex() == 0)

    idx = _setup_index(w, "D8 ECO Lynxeye XE")
    # Confirm "No" -> nothing changes.
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
    before = g.steps
    w._on_load_setup(idx)
    check("widget: load cancelled leaves goniometer unchanged", g.steps == before)

    # Confirm "Yes" -> applies, refreshes fields, sets label, resets combo.
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    w._on_load_setup(idx)
    check("widget: load applies setup + refreshes the step field",
          g.steps == 6895 and w.ui.steps_spn_btn1.value() == 6895)
    check("widget: load sets applied label + resets combo",
          "D8 ECO Lynxeye XE" in w.ui.lbl_applied_gonio.text()
          and combo.currentIndex() == 0)

    # Placeholder pick (index 0, data None) is a no-op.
    steps_now = g.steps
    w._on_load_setup(0)
    check("widget: placeholder pick is a no-op", g.steps == steps_now)
    w.deleteLater()


def check_widget_store():
    tmp_user = tempfile.mkdtemp()
    orig_dir = gw._user_gonio_dir
    gw._user_gonio_dir = lambda create=False: tmp_user  # redirect user setups
    orig_save = QFileDialog.getSaveFileName
    try:
        w = GoniometerWidget()
        g = Goniometer()
        g.radius = 42.0
        w.bind_goniometer(g)
        out = os.path.join(tmp_user, "MyScope")  # no extension on purpose
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (out, ""))
        w._on_store_setup()
        check("widget: store writes a .gon (extension appended)",
              os.path.isfile(out + ".gon"))
        check("widget: stored setup carries the current values",
              load_gon(out + ".gon").get("radius") == 42.0)
        check("widget: store sets the applied label",
              "MyScope" in w.ui.lbl_applied_gonio.text())
        # The combo now lists the custom setup and it re-loads.
        idx = _setup_index(w, "MyScope")
        check("widget: stored setup appears in the combo (as custom)",
              "(custom)" in w.ui.cmb_import_gonio.itemText(idx))
        g2 = Goniometer()
        w.bind_goniometer(g2)
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
        w._on_load_setup(_setup_index(w, "MyScope"))
        check("widget: the stored custom setup re-loads", g2.radius == 42.0)
        w.deleteLater()
    finally:
        gw._user_gonio_dir = orig_dir
        QFileDialog.getSaveFileName = orig_save


def _check_applied_setup_name():
    """The applied setup NAME persists, and clears when the values stop matching.

    It lives in `specimen.source`, not on the Goniometer, for a compatibility
    reason that is easy to undo by accident: the OLD app deserialises every
    object with `cls(**properties)` and raises TypeError on ANY unknown key, so
    a new `Goniometer.setup_name` property would make every MudLab2-saved .mud
    unreadable there. `source` is a field the old app already has - and where it
    kept this same information."""
    import tempfile

    from mudlab.edit_specimen_dialog import EditSpecimenDialog
    from mudlab.models.specimen import (
        goniometer_setup_name, with_goniometer_setup_name,
    )

    # The pure helpers: set / read / replace / clear, leaving the rest alone.
    provenance = "File: 308.rd\n2theta: 3.0000 - 45.0000"
    named = with_goniometer_setup_name(provenance, "Bruker D8")
    check("setup name: stored without disturbing the import provenance",
          named.startswith(provenance)
          and goniometer_setup_name(named) == "Bruker D8")
    renamed = with_goniometer_setup_name(named, "PANalytical")
    check("setup name: applying another REPLACES it, never duplicates",
          renamed.count("Goniometer setup:") == 1
          and goniometer_setup_name(renamed) == "PANalytical")
    check("setup name: clearing restores the original text",
          with_goniometer_setup_name(renamed, "") == provenance)
    check("setup name: absent reads as empty", goniometer_setup_name(provenance) == "")

    if not os.path.isfile(FIXTURE):
        print("  (no fixture; skipped the widget + round-trip checks)")
        return
    project = load_mud(FIXTURE)
    spec = next(s for s in project.specimens if s is not None)
    other = next((s for s in project.specimens
                  if s is not None and s is not spec), None)

    dialog = EditSpecimenDialog()
    dialog.bind_specimen(spec)
    widget = dialog.goniometer
    widget._remember_setup_name("Bruker D8")
    check("setup name: applying one shows it and writes it to the specimen",
          widget.ui.lbl_applied_gonio.text() == "Goniometer: Bruker D8"
          and goniometer_setup_name(spec.source) == "Bruker D8")

    if other is not None:
        dialog.bind_specimen(other)
        check("setup name: another specimen does not inherit it",
              widget.ui.lbl_applied_gonio.text() == "")
        dialog.bind_specimen(spec)
        check("setup name: rebinding shows it again",
              widget.ui.lbl_applied_gonio.text() == "Goniometer: Bruker D8")

    # A hand-edit means the values are no longer that setup.
    widget.ui.gonio_radius_spb.setValue(widget.ui.gonio_radius_spb.value() + 1.0)
    check("setup name: a hand-edited field clears the name",
          widget.ui.lbl_applied_gonio.text() == ""
          and goniometer_setup_name(spec.source) == "")

    # ...and it survives a save/reload, which was the whole point.
    widget._remember_setup_name("Bruker D8")
    tmp = os.path.join(tempfile.mkdtemp(), "named.mud")
    save_mud(project, tmp)
    reloaded = next(s for s in load_mud(tmp).specimens if s is not None)
    check("setup name: survives save + reload",
          goniometer_setup_name(reloaded.source) == "Bruker D8")
    reopened = EditSpecimenDialog()
    reopened.bind_specimen(reloaded)
    check("setup name: the reopened dialog shows it",
          reopened.goniometer.ui.lbl_applied_gonio.text() == "Goniometer: Bruker D8")

    # COMPATIBILITY: it must never become a goniometer property.
    gonio_keys = set(spec.goniometer.to_dict().get("properties", {}))
    check("setup name: NOT written into the goniometer (old-app compatibility)",
          not any("setup" in key for key in gonio_keys))


def main():
    check_parser()
    check_apply_setup()
    check_persistence()
    check_widget_populate_and_load()
    check_widget_store()
    _check_applied_setup_name()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- goniometer-setup verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
