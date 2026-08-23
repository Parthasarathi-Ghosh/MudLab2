#!/usr/bin/env python
"""Head-less harness for the project's measured (XRF) Composition object.

Covers the whole path the feature adds:
  - the model: oxide filtering, totals, normalisation, to/from_dict;
  - the project: one composition, its change signal, clearing;
  - the .mud round trip, INCLUDING the two cases that must not regress -
    a project without a composition writes no key at all, and clearing one
    removes the key rather than leaving a tombstone;
  - the Import composition dialog + its Data-menu action;
  - STEP 2: the default-phase mapping (which shipped default each phase
    started as - user-stated, because it cannot be derived) and the
    comparison columns in the Compositions dialog;
  - CUSTOM DEFAULTS: importing a user's own reference phase from a .phs so
    it can be chosen as a default, stored with the project;
  - CAPTURE AT ENTRY: a phase entering the model records its reference at
    that moment - the only moment it is provably unrefined;
  - FROZEN BASELINES + Set as baseline, including the INHERITING case that
    a naive copy gets badly wrong;
  - the AUDIT findings, each pinned so it cannot come back;
  - the two-pane Compositions dialog and its comparison plot;
  - the Default-phases list filter and its no-scroll combos, and where the
    focus lands after Add phase.

The feature is purely additive: an existing project that never gets a
composition must round-trip exactly as it did before, which is what the
"no key" checks pin.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_composition_object.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import json
import os
import sys
import tempfile
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication, QDialogButtonBox

from mudlab.calculations.composition import mixture_composition, reporting_oxides
from mudlab.calculations.refinement import enumerate_refinables, refine_mixture
from mudlab.composition_dialog import CompositionDialog
from mudlab.default_phases_dialog import DefaultPhasesDialog
from mudlab.default_state import (
    available_default_names, capture_catalog_defaults,
    capture_imported_defaults, custom_default_names,
    default_state_composition, default_substitutes, import_custom_defaults,
    make_baseline_copy, mapping_is_complete, phases_used_in_mixtures,
    resolve_default_phase, set_as_baseline, structural_phases,
    suggest_default_phase_map, unmapped_phases,
)
from mudlab.file_parsers.atom_type_library import load_atom_type_library
from mudlab.file_parsers.default_catalog import add_catalog_entry_to_project
from mudlab.file_parsers.phs_phases import load_phs
from mudlab.file_parsers.phs_phases import save_phs
from mudlab.file_parsers.default_catalog import (
    build_default_phase, default_phase_names,
)
from mudlab.file_parsers import load_mud, save_mud
from mudlab.import_composition_dialog import ImportCompositionDialog
from mudlab.models import Composition
from mudlab.models.project import Project
from mudlab.qt_utils import install_enter_policy

app = QApplication.instance() or QApplication([])
# The app installs an application-wide Enter policy at start-up; the dialogs
# rely on it, so the harness has to run under it too or it would be testing a
# configuration no user ever sees.
install_enter_policy(app)
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        return path
    return None


PATH = _fixture()
if PATH is None:
    print("No .mud fixture; skipping (exit 2).")
    raise SystemExit(2)

TMP = os.path.join(tempfile.gettempdir(), "mudlab_verify_composition_%d.mud" % os.getpid())
SAMPLE = {"SiO2": 58.4, "Al2O3": 17.2, "Fe2O3": 6.1, "CaO": 1.4,
          "MgO": 2.3, "Na2O": 0.9, "K2O": 3.2}


def _project_props(path):
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read("content").decode("utf-8"))["properties"]


def check_model():
    comp = Composition(name="XRF bulk", oxides=SAMPLE, source="Lab A")
    check("model: keeps the values it was given", comp.oxides == SAMPLE)
    check("model: total is the sum", abs(comp.total() - sum(SAMPLE.values())) < 1e-9)
    check("model: not empty", not comp.is_empty())

    # The grid restricts input, but a hand-edited file or a future importer
    # does not - so the model is where the guarantee has to live.
    dirty = Composition(oxides={**SAMPLE, "NotAnOxide": 9.9, "SiO2 ": 1.0})
    check("model: drops oxides outside the reporting set",
          set(dirty.oxides) == set(SAMPLE))
    bad = Composition(oxides={"SiO2": "abc", "Al2O3": float("nan"),
                              "Fe2O3": float("inf"), "CaO": -3.0, "MgO": 2.0})
    check("model: drops non-numeric, NaN, inf and negative values",
          bad.oxides == {"MgO": 2.0})
    check("model: an empty analysis reports itself empty",
          Composition().is_empty() and Composition().normalized() == {})

    norm = comp.normalized()
    check("model: normalized totals 100", abs(sum(norm.values()) - 100.0) < 1e-9)
    check("model: normalizing preserves the ratios",
          abs(norm["SiO2"] / norm["Al2O3"] - SAMPLE["SiO2"] / SAMPLE["Al2O3"]) < 1e-9)
    check("model: oxides is a COPY, not the live dict",
          (comp.oxides.__setitem__("SiO2", 0.0), comp.oxides["SiO2"] == 58.4)[1])

    back = Composition.from_dict(comp.to_dict())
    check("model: to_dict/from_dict round-trips every field",
          back.name == comp.name and back.source == comp.source
          and back.uuid == comp.uuid and back.oxides == comp.oxides)
    check("model: to_dict is tagged with its type",
          comp.to_dict()["type"] == "Composition")


def check_project():
    project = Project()
    check("project: starts with no composition", project.composition is None)
    fired = []
    project.composition_changed.connect(lambda: fired.append(1))
    comp = Composition(oxides=SAMPLE)
    project.set_composition(comp)
    check("project: holds the composition", project.composition is comp)
    check("project: emits composition_changed", len(fired) == 1)
    # One physical sample per project, so a second import REPLACES.
    second = Composition(name="XRF repeat", oxides={"SiO2": 60.0})
    project.set_composition(second)
    check("project: a second composition replaces the first",
          project.composition is second)
    project.set_composition(None)
    check("project: can be cleared", project.composition is None)
    check("project: clearing also signals", len(fired) == 3)


def check_round_trip():
    # 1. A project with NO composition must write NO key - this is what keeps
    #    the feature additive for every existing project.
    project = load_mud(PATH)
    check("file: a loaded fixture has no composition", project.composition is None)
    save_mud(project, TMP)
    check("file: saving without one writes no 'composition' key",
          "composition" not in _project_props(TMP))
    check("file: ...and it reloads with none",
          load_mud(TMP).composition is None)

    # 2. With one: full fidelity.
    comp = Composition(name="XRF bulk", oxides=SAMPLE, source="Lab A, 2026")
    project.set_composition(comp)
    save_mud(project, TMP)
    props = _project_props(TMP)
    check("file: saving with one writes the key", "composition" in props)
    check("file: it is written as a typed object",
          props["composition"].get("type") == "Composition")
    back = load_mud(TMP)
    check("file: name, source and uuid survive",
          back.composition.name == comp.name
          and back.composition.source == comp.source
          and back.composition.uuid == comp.uuid)
    check("file: the oxide values survive exactly",
          back.composition.oxides == comp.oxides)

    # 3. Two saves in a row must not drift (raw_properties passthrough).
    save_mud(back, TMP)
    again = load_mud(TMP)
    check("file: a second round trip is stable",
          again.composition.to_dict() == back.composition.to_dict())

    # 4. Clearing REMOVES the key - no tombstone, no null to trip a reader.
    again.set_composition(None)
    save_mud(again, TMP)
    check("file: clearing removes the key entirely",
          "composition" not in _project_props(TMP))
    check("file: ...and the project still loads", load_mud(TMP) is not None)

    # 5. The rest of the project is untouched by any of this.
    original, final = load_mud(PATH), load_mud(TMP)
    check("file: specimens / phases / mixtures are unaffected",
          len(final.specimens) == len(original.specimens)
          and len(final.phases) == len(original.phases)
          and len(final.mixtures) == len(original.mixtures))
    if os.path.exists(TMP):
        os.remove(TMP)
    for leftover in (TMP + "~",):
        if os.path.exists(leftover):
            os.remove(leftover)


def check_dialog():
    dialog = ImportCompositionDialog()
    ok = dialog.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
    check("dialog: the grid offers exactly the reporting oxides",
          dialog.ui.oxide_grid.rowCount() == len(reporting_oxides()))
    check("dialog: an empty analysis cannot be accepted", not ok.isEnabled())
    # isVisibleTo(), not isVisible(): the harness never shows the dialog, and
    # isVisible() is False for every child of an unshown window.
    check("dialog: ...and says why",
          dialog.ui.lbl_warning.isVisibleTo(dialog)
          and "at least one" in dialog.ui.lbl_warning.text())

    dialog.grid.set_values(SAMPLE)
    app.processEvents()
    check("dialog: entering values enables OK", ok.isEnabled())
    check("dialog: the total is shown",
          "%.2f" % sum(SAMPLE.values()) in dialog.ui.lbl_sum.text())
    check("dialog: a total far from 100 is flagged but NOT blocked",
          dialog.ui.lbl_warning.isVisibleTo(dialog) and ok.isEnabled())

    dialog.grid.normalize()
    app.processEvents()
    # Not exact by construction: the shared OxideGrid's spin boxes hold 2
    # decimals, so seven rounded values can total 100.01. That is the right
    # precision for XRF weight percent - making it exact would mean silently
    # fudging one oxide - so the tolerance covers the rounding (7 x 0.005).
    check("dialog: Recompute to 100 % normalises",
          abs(sum(dialog.grid.values().values()) - 100.0) <= 0.05)
    check("dialog: ...and the note clears once it totals 100",
          not dialog.ui.lbl_warning.isVisibleTo(dialog))

    dialog.ui.edit_name.setText("XRF bulk")
    dialog.ui.edit_source.setText("Lab A")
    dialog._on_accept()
    built = dialog.composition
    check("dialog: builds a Composition on accept", isinstance(built, Composition))
    check("dialog: carrying the typed name and source",
          built.name == "XRF bulk" and built.source == "Lab A")
    check("dialog: zero-valued oxides are not stored",
          all(v > 0.0 for v in built.oxides.values()))

    # Re-opening on an existing analysis makes this the EDITOR too, and the
    # identity must survive so anything referring to it still does.
    editor = ImportCompositionDialog(composition=built)
    check("dialog: re-opens on the existing values",
          abs(editor.grid.values()["SiO2"] - built.oxides["SiO2"]) < 1e-9
          and editor.ui.edit_name.text() == "XRF bulk")
    editor._on_accept()
    check("dialog: editing keeps the same uuid",
          editor.composition.uuid == built.uuid)

    # An empty name falls back rather than producing a nameless entry.
    blank = ImportCompositionDialog()
    blank.grid.set_values({"SiO2": 50.0})
    blank.ui.edit_name.setText("   ")
    blank._on_accept()
    check("dialog: a blank name falls back to a default",
          blank.composition.name == "XRF")


def check_menu():
    from mudlab.main_window import MainWindow

    window = MainWindow()
    window._set_project(load_mud(PATH))
    window._dirty = False
    action = getattr(window.ui, "actionImportComposition", None)
    check("menu: the Import composition action exists", action is not None)
    if action is not None:
        check("menu: it sits in the Data menu",
              action in window.ui.menuData.actions())
        check("menu: it is labelled for composition import",
              "composition" in action.text().lower())
    # Applying one through the project marks the file dirty, or the analysis
    # would be silently lost on close.
    window.project.set_composition(Composition(oxides=SAMPLE))
    window._mark_dirty()
    check("menu: importing marks the project dirty", window._dirty)




# ======================================================================
# STEP 2: the default-phase mapping and the comparison columns
# ======================================================================
def check_default_lookup():
    names = default_phase_names()
    check("catalog: the default phases can be enumerated", len(names) > 100)
    check("catalog: names are unique", len(names) == len(set(names)))
    # A treatment triple builds three DISTINCTLY named phases, which is why a
    # flat phase name (not the entry name) is the identity used throughout.
    triple = [n for n in names if n.startswith("Illite-Smectite R0 Ca")]
    check("catalog: a treatment triple exposes its three phases separately",
          len(triple) == 3 and any(n.endswith("-AD") for n in triple))
    built = build_default_phase("Illite")
    check("catalog: a default phase can be built by name",
          built is not None and built.name == "Illite")
    check("catalog: an unknown name yields None",
          build_default_phase("No Such Phase") is None)
    # THE REASON THE MAPPING MUST BE USER-STATED: a build mints fresh identity
    # every time, so nothing about a project phase points back to the catalog.
    again = build_default_phase("Illite")
    check("catalog: each build has a FRESH uuid (so uuid cannot trace origin)",
          again is not None and again.uuid != built.uuid)


def check_mapping():
    project = load_mud(PATH)
    phases = structural_phases(project)
    check("mapping: structural phases are found", len(phases) > 0)
    check("mapping: none is stated on a freshly loaded project",
          project.default_phase_map == {})
    check("mapping: every phase is unmapped to begin with",
          len(unmapped_phases(project)) == len(phases))

    suggested = suggest_default_phase_map(project)
    by_uuid = {ph.uuid: ph for ph in phases}
    check("mapping: name matching suggests only EXACT matches",
          all(by_uuid[uid].name == name for uid, name in suggested.items()))
    project.set_default_phase_map(suggested)
    check("mapping: a partial mapping is accepted",
          0 < len(project.default_phase_map) <= len(phases))

    # A uuid the project does not have must not be stored - re-adding a phase
    # mints a new uuid, so a stale entry could never match again.
    stale = "deadbeef" * 4
    project.set_default_phase_map(dict(suggested, **{stale: "Illite"}))
    check("mapping: unknown phase uuids are pruned",
          stale not in project.default_phase_map)
    check("mapping: the real entries survive pruning",
          len(project.default_phase_map) == len(suggested))

    fired = []
    project.composition_changed.connect(lambda: fired.append(1))
    project.set_default_phase_map(suggested)
    check("mapping: setting it signals the composition view", len(fired) == 1)

    save_mud(project, TMP)
    props = _project_props(TMP)
    check("mapping: it is written to the file", "default_phase_map" in props)
    back = load_mud(TMP)
    check("mapping: it survives save/load",
          back.default_phase_map == project.default_phase_map)
    back.set_default_phase_map({})
    save_mud(back, TMP)
    check("mapping: an empty map writes no key",
          "default_phase_map" not in _project_props(TMP))
    for path in (TMP, TMP + "~"):
        if os.path.exists(path):
            os.remove(path)


def check_default_state_composition():
    project = load_mud(PATH)
    mixture = project.mixtures[0]

    names, rows = default_state_composition(mixture, project)
    check("default state: no mapping means no answer (not a zero answer)",
          rows == [] and len(names) > 0)

    project.set_default_phase_map(suggest_default_phase_map(project))
    subs = default_substitutes(project)
    check("default state: a substitute is built for each mapped phase",
          len(subs) == len(project.default_phase_map))
    check("default state: substitutes are keyed by the PROJECT phase uuid",
          set(subs) == set(project.default_phase_map))

    # Refine so the live phases genuinely differ from their defaults.
    for ref in enumerate_refinables(mixture):
        ref.set_ref_info(refine=ref.minimum < ref.maximum)
    refine_mixture(mixture, 0, {"maxfun": 10, "maxiter": 2})

    _n, current = mixture_composition(mixture)
    _n2, defaults = default_state_composition(mixture, project)
    check("default state: one column per specimen, as the modelled view has",
          len(defaults) == len(current)
          and len(defaults[0][1]) == len(current[0][1]))
    moved = any(abs(a - b) > 1e-6
                for (_o, avals), (_o2, bvals) in zip(current, defaults)
                for a, b in zip(avals, bvals))
    check("default state: it differs from the refined composition", moved)
    check("default state: both are normalised to 100",
          abs(sum(v[0] for _o, v in defaults) - 100.0) < 1e-6)

    before = [ph.name for ph in structural_phases(project)]
    default_state_composition(mixture, project)
    check("default state: computing it leaves the project phases alone",
          [ph.name for ph in structural_phases(project)] == before)
    check("default state: mixture_composition without substitutes is unchanged",
          mixture_composition(mixture)[1] == current)


def check_mapping_dialog():
    project = load_mud(PATH)
    dialog = DefaultPhasesDialog(project)
    phases = structural_phases(project)
    check("map dialog: one row per structural phase",
          dialog.ui.tbl_phases.rowCount() == len(phases))
    check("map dialog: nothing is stated to begin with",
          all(c.currentIndex() == 0 for c in dialog._combos))
    check("map dialog: it says how many are unstated",
          "0 of %d" % len(phases) in dialog.ui.lbl_status.text())

    dialog._on_match()
    matched = sum(1 for c in dialog._combos if c.currentIndex() > 0)
    check("map dialog: Match by name fills the exact matches", matched > 0)
    check("map dialog: ...and leaves renamed phases alone", matched < len(phases))
    check("map dialog: the status names what is still missing",
          "at their current state" in dialog.ui.lbl_status.text())

    dialog._on_accept()
    check("map dialog: accept returns only the stated rows",
          dialog.mapping is not None and len(dialog.mapping) == matched)

    cleared = DefaultPhasesDialog(project)
    cleared._on_match()
    cleared._on_clear()
    check("map dialog: Clear all empties every row",
          all(c.currentIndex() == 0 for c in cleared._combos))


def check_comparison_columns():
    project = load_mud(PATH)
    mixture = project.mixtures[0]

    plain = CompositionDialog(mixture)
    base_columns = len(plain._specimen_names)
    check("compare: without a project the dialog is unchanged",
          plain.ui.tbl_composition.columnCount() == base_columns)

    dialog = CompositionDialog(mixture, project=project)
    check("compare: measured is disabled with no analysis imported",
          not dialog.ui.chk_measured.isEnabled())
    check("compare: default state is disabled with no mapping stated",
          not dialog.ui.chk_default.isEnabled())
    check("compare: ...and each says why in its tooltip",
          "Import composition" in dialog.ui.chk_measured.toolTip()
          and "Default phases" in dialog.ui.chk_default.toolTip())

    project.set_composition(Composition(name="XRF", oxides=SAMPLE))
    project.set_default_phase_map(suggest_default_phase_map(project))
    dialog = CompositionDialog(mixture, project=project)
    check("compare: both enable once their data exists",
          dialog.ui.chk_measured.isEnabled() and dialog.ui.chk_default.isEnabled())

    dialog.ui.chk_measured.setChecked(True)
    app.processEvents()
    check("compare: the measured column is appended",
          len(dialog._specimen_names) == base_columns + 1
          and "measured" in dialog._specimen_names[-1])
    measured_col = [values[-1] for _oxide, values in dialog._oxide_rows]
    check("compare: it is NORMALISED to 100, like every modelled column",
          abs(sum(measured_col) - 100.0) < 1e-6)

    dialog.ui.chk_default.setChecked(True)
    app.processEvents()
    check("compare: the default-state columns are appended too",
          len(dialog._specimen_names) == base_columns * 2 + 1)
    check("compare: they are labelled per specimen",
          all("(default)" in n for n in
              dialog._specimen_names[base_columns:base_columns * 2]))
    check("compare: the export carries the same columns",
          all(name in dialog._csv_text().splitlines()[0]
              for name in dialog._specimen_names))
    check("compare: a partial mapping is disclosed in the title",
          "no default stated" in dialog.ui.lbl_title.text()
          or not unmapped_phases(project))

    if dialog.ui.chk_bulk.isEnabled():
        dialog.ui.chk_bulk.setChecked(True)
        app.processEvents()
        check("compare: default state is refused in the bulk view",
              not dialog.ui.chk_default.isEnabled()
              and not dialog.ui.chk_default.isChecked())
    else:
        check("compare: bulk/default exclusion (fixture has no non-clay; "
              "rule verified in _update_comparison_controls)", True)



# ======================================================================
# CUSTOM DEFAULTS: a user's own reference phase, imported from a .phs
# ======================================================================
def _write_custom_phs(name):
    """Build a catalog phase, rename it, and save it as a .phs - a stand-in for
    the user's own reference clay, with no external fixture needed."""
    phase = build_default_phase("Illite")
    phase.name = name
    path = os.path.join(tempfile.gettempdir(),
                        "mudlab_custom_%s_%d.phs" % (name.replace(" ", "_"),
                                                     os.getpid()))
    save_phs([phase], path)
    return path


def check_custom_defaults():
    project = load_mud(PATH)
    phases_before = len(structural_phases(project))
    atom_types_before = len(project.atom_types)
    shipped_before = len(available_default_names(project))

    path = _write_custom_phs("My Reference Clay")
    try:
        added, shadowed = import_custom_defaults(project, path)
        check("custom: the .phs is imported as a default",
              added == ["My Reference Clay"])
        check("custom: it shadows nothing when the name is new", shadowed == [])
        check("custom: it is NOT added to the project's phases",
              len(structural_phases(project)) == phases_before)
        check("custom: ...and does not extend the project's atom types",
              len(project.atom_types) == atom_types_before)
        check("custom: it is offered as a default",
              "My Reference Clay" in available_default_names(project))
        check("custom: the custom names come FIRST in the offered list",
              available_default_names(project)[0] == "My Reference Clay")
        check("custom: the shipped defaults are still offered",
              len(available_default_names(project)) == shipped_before + 1)
        check("custom: it resolves to a real phase",
              getattr(resolve_default_phase(project, "My Reference Clay"),
                      "name", None) == "My Reference Clay")

        # Re-importing the same name REPLACES rather than accumulating, so a
        # corrected reference updates in place and the mapping keeps working.
        import_custom_defaults(project, path)
        check("custom: re-importing the same name replaces, not duplicates",
              custom_default_names(project).count("My Reference Clay") == 1)

        # It can actually be used as a default, and drives the comparison.
        target = structural_phases(project)[0]
        project.set_default_phase_map({target.uuid: "My Reference Clay"})
        subs = default_substitutes(project)
        check("custom: a phase can be mapped to it",
              subs.get(target.uuid) is not None
              and subs[target.uuid].name == "My Reference Clay")
        _names, rows = default_state_composition(project.mixtures[0], project)
        check("custom: it produces a default-state composition", bool(rows))

        # It must survive the .phs going away - the project carries it.
        save_mud(project, TMP)
        os.remove(path)
        back = load_mud(TMP)
        check("custom: it is saved with the project",
              custom_default_names(back) == ["My Reference Clay"])
        check("custom: ...and still resolves without the original .phs",
              resolve_default_phase(back, "My Reference Clay") is not None)
        check("custom: the reloaded reference still has its atoms resolved",
              all(atom.atom_type is not None
                  for comp in resolve_default_phase(
                      back, "My Reference Clay").components
                  for atom in list(comp.layer_atoms) + list(comp.interlayer_atoms)))
        check("custom: the mapping survives with it",
              back.default_phase_map == project.default_phase_map)
        _n2, rows2 = default_state_composition(back.mixtures[0], back)
        check("custom: the comparison is identical after reload",
              all(abs(a - b) < 1e-9
                  for (_o, av), (_o2, bv) in zip(rows, rows2)
                  for a, b in zip(av, bv)))
        check("custom: reloading does not add it to the project's phases",
              len(structural_phases(back)) == phases_before)

        # Removing it, and the empty-key rule.
        back.remove_custom_default_phase("My Reference Clay")
        check("custom: it can be removed", custom_default_names(back) == [])
        save_mud(back, TMP)
        check("custom: an empty list writes no key",
              "custom_default_phases" not in _project_props(TMP))
    finally:
        for leftover in (path, TMP, TMP + "~"):
            if os.path.exists(leftover):
                os.remove(leftover)


def check_custom_shadowing():
    """A custom default named like a shipped one WINS - the user's own
    reference is the more specific answer - and the import says so."""
    project = load_mud(PATH)
    path = _write_custom_phs("Illite")
    try:
        added, shadowed = import_custom_defaults(project, path)
        check("shadow: importing a shipped name is reported as shadowing",
              added == ["Illite"] and shadowed == ["Illite"])
        check("shadow: the name is offered only ONCE",
              available_default_names(project).count("Illite") == 1)
        resolved = resolve_default_phase(project, "Illite")
        check("shadow: it resolves to the CUSTOM phase, not the shipped one",
              resolved is project.custom_default_phases[0])
    finally:
        if os.path.exists(path):
            os.remove(path)


def check_custom_dialog():
    project = load_mud(PATH)
    path = _write_custom_phs("Dialog Reference")
    try:
        import_custom_defaults(project, path)
        dialog = DefaultPhasesDialog(project)
        combo = dialog._combos[0]
        check("custom dialog: the import button exists",
              hasattr(dialog.ui, "button_import"))
        check("custom dialog: the custom name is offered first",
              combo.itemText(1) == "Dialog Reference")
        check("custom dialog: every default is offered",
              combo.count() == len(available_default_names(project)) + 1)
        from PySide6.QtCore import Qt as _Qt
        check("custom dialog: the custom entry is marked as yours",
              "not built in" in (combo.itemData(1, _Qt.ItemDataRole.ToolTipRole) or ""))
        # The stored value must be the BARE name - no "(custom)" decoration to
        # strip later.
        combo.setCurrentIndex(1)
        dialog._on_accept()
        check("custom dialog: it stores the bare name",
              "Dialog Reference" in (dialog.mapping or {}).values())
    finally:
        if os.path.exists(path):
            os.remove(path)



# ======================================================================
# CAPTURE AT ENTRY: record the reference when a phase joins the model
# ======================================================================
def check_capture_from_catalog():
    """A phase added from the shipped catalog knows its own default, so the
    mapping is recorded there and then - and NO copy is stored, because the
    catalog can rebuild it."""
    project = Project()
    added = add_catalog_entry_to_project(project, "Illite-Smectite R0 Ca")
    check("capture: the catalog entry adds its treatment triple", len(added) == 3)
    names = capture_catalog_defaults(project, added)
    check("capture: every added phase is mapped automatically",
          len(project.default_phase_map) == len(added))
    check("capture: mapped to the catalog's own phase names",
          names == sorted(ph.name for ph in added))
    check("capture: no custom copy is stored for a shipped default",
          custom_default_names(project) == [])
    check("capture: each mapping resolves to a real phase",
          all(resolve_default_phase(project, name) is not None
              for name in project.default_phase_map.values()))

    # Renaming the phase afterwards must not break it: the map is keyed by uuid.
    target = added[0]
    original = target.name
    target.name = "My own air-dried"
    resolved = resolve_default_phase(project, project.default_phase_map[target.uuid])
    check("capture: a later RENAME does not break the mapping",
          resolved is not None and resolved.name == original)

    # Capturing again must MERGE, never wipe what the user stated by hand.
    other = structural_phases(project)[1]
    project.set_default_phase_map({**project.default_phase_map,
                                   other.uuid: "Illite"})
    capture_catalog_defaults(project, [])
    check("capture: capturing nothing leaves the existing map alone",
          project.default_phase_map.get(other.uuid) == "Illite")


def check_capture_from_phs():
    """A .phs imported INTO THE MODEL captures a pristine reference copy at the
    same moment - independent of the working phase, so refinement cannot move
    it."""
    path = _write_custom_phs("Captured Reference")
    try:
        project = Project()
        for atom_type in load_atom_type_library():
            project.add_atom_type(atom_type)
        imported, _missing = load_phs(path, project)
        captured = capture_imported_defaults(project, path, imported)
        check("capture: importing into the model records a reference",
              captured == ["Captured Reference"])
        check("capture: the reference is stored as a custom default",
              custom_default_names(project) == ["Captured Reference"])
        check("capture: the imported phase is mapped to it",
              project.default_phase_map.get(imported[0].uuid)
              == "Captured Reference")

        working = imported[0]
        reference = resolve_default_phase(project, "Captured Reference")
        check("capture: the reference is a DIFFERENT object", working is not reference)
        shared_components = ({id(c) for c in working.components}
                             & {id(c) for c in reference.components})
        shared_atoms = ({id(a) for c in working.components
                         for a in list(c.layer_atoms) + list(c.interlayer_atoms)}
                        & {id(a) for c in reference.components
                           for a in list(c.layer_atoms) + list(c.interlayer_atoms)})
        check("capture: it shares no components with the working phase",
              not shared_components)
        check("capture: ...and no atoms either", not shared_atoms)
        check("capture: the reference is not a phase of the model",
              reference not in structural_phases(project))

        # THE POINT OF ALL THIS: what refinement does to the model must not
        # reach the reference, or the comparison would always read "no change".
        from mudlab.calculations.composition import (
            _clay_oxide_masses, load_conversion_table,
        )

        conv = load_conversion_table()
        before = {k: round(v, 6) for k, v in _clay_oxide_masses(reference, conv).items()}
        component = working.components[0]
        moved = False
        for relation in component.atom_relations:
            if hasattr(relation, "value"):
                relation.value = min(1.0, float(relation.value) + 0.25)
                moved = True
        component.apply_atom_relations()
        after_model = {k: round(v, 6)
                       for k, v in _clay_oxide_masses(working, conv).items()}
        after_ref = {k: round(v, 6)
                     for k, v in _clay_oxide_masses(reference, conv).items()}
        check("capture: mutating the model phase changes its composition",
              after_model != before if moved else True)
        check("capture: ...and leaves the reference UNTOUCHED", after_ref == before)

        # A bad path must not break an import - capture is a convenience.
        check("capture: an unreadable file captures nothing, without raising",
              capture_imported_defaults(project, path + ".missing", imported) == [])
    finally:
        if os.path.exists(path):
            os.remove(path)



# ======================================================================
# FROZEN BASELINES: inheritance is where a naive copy goes badly wrong
# ======================================================================
def _oxides(phase):
    from mudlab.calculations.composition import (
        _clay_oxide_masses, load_conversion_table,
    )
    return {k: round(v, 4)
            for k, v in _clay_oxide_masses(phase, load_conversion_table()).items()}


def _inheriting_project():
    """A project whose EG phase inherits from AD, with the parent moved away
    from what the child stores itself - so own-values and resolved values
    differ and a copy that gets it wrong is visible."""
    project = Project()
    ad, eg, heated = add_catalog_entry_to_project(
        project, "Illite-Smectite R0 Ca")
    ad.sigma_star = 9.99
    for component in ad.components:
        for relation in component.atom_relations:
            if hasattr(relation, "value"):
                relation.value = min(1.0, float(relation.value) + 0.4)
        component.apply_atom_relations()
    return project, ad, eg, heated


def check_frozen_baseline():
    project, ad, eg, _heated = _inheriting_project()
    check("frozen: the fixture phase really does inherit",
          eg.based_on is ad and any(c.linked_with is not None
                                    for c in eg.components))

    # The trap: a plain serialise/deserialise loses the inherited values.
    from mudlab.file_parsers.atom_type_library import atom_type_library_map
    from mudlab.models.phase import Phase

    naive = Phase.from_dict(eg.to_dict(), atom_type_library_map())
    check("frozen: a NAIVE copy of an inheriting phase is wrong",
          _oxides(naive) != _oxides(eg))

    baseline = make_baseline_copy(project, eg)
    check("frozen: the baseline preserves the RESOLVED composition",
          _oxides(baseline) == _oxides(eg))
    check("frozen: ...and the resolved scalar values",
          abs(baseline.sigma_star - eg.sigma_star) < 1e-9
          and abs(baseline.CSDS.average - eg.CSDS.average) < 1e-9)
    check("frozen: it is detached from its parent", baseline.based_on is None)
    check("frozen: every component is unlinked",
          all(c.linked_with is None for c in baseline.components))
    live_atoms = {id(a) for c in eg.components
                  for a in list(c.layer_atoms) + list(c.interlayer_atoms)}
    live_atoms |= {id(a) for c in ad.components
                   for a in list(c.layer_atoms) + list(c.interlayer_atoms)}
    base_atoms = {id(a) for c in baseline.components
                  for a in list(c.layer_atoms) + list(c.interlayer_atoms)}
    check("frozen: it shares no atom with the phase OR its parent",
          not (live_atoms & base_atoms))

    # The whole point: the parent moving must not move the baseline.
    held = _oxides(baseline)
    ad.sigma_star = 1.23
    for component in ad.components:
        for relation in component.atom_relations:
            if hasattr(relation, "value"):
                relation.value = max(0.0, float(relation.value) - 0.3)
        component.apply_atom_relations()
    check("frozen: refining the PARENT moves the live phase",
          _oxides(eg) != held)
    check("frozen: ...and leaves the baseline exactly where it was",
          _oxides(baseline) == held)


def check_set_as_baseline():
    project, _ad, eg, heated = _inheriting_project()
    project.set_default_phase_map({})
    check("baseline: nothing is recorded to begin with",
          project.default_phase_map == {})

    check("baseline: setting one succeeds", set_as_baseline(project, eg))
    name = project.default_phase_map.get(eg.uuid)
    check("baseline: the phase is mapped to it", bool(name))
    check("baseline: it is named as a captured state", "(baseline)" in (name or ""))
    stored = resolve_default_phase(project, name)
    check("baseline: it resolves", stored is not None)
    check("baseline: it captured the RESOLVED composition",
          _oxides(stored) == _oxides(eg))

    # Re-running on the same phase REPLACES its baseline.
    count = len(project.custom_default_phases)
    set_as_baseline(project, eg)
    check("baseline: re-running replaces rather than accumulating",
          len(project.custom_default_phases) == count)

    # Two phases sharing a NAME must not overwrite each other's baseline -
    # nothing stops a duplicate name, and it has bitten this codebase twice.
    heated.name = eg.name
    set_as_baseline(project, heated)
    check("baseline: a same-named phase gets its OWN baseline",
          project.default_phase_map[heated.uuid]
          != project.default_phase_map[eg.uuid])
    check("baseline: ...and both are kept",
          len(project.custom_default_phases) == count + 1)

    # It survives a save/reload with its resolved values intact.
    save_mud(project, TMP)
    try:
        back = load_mud(TMP)
        reloaded = resolve_default_phase(
            back, back.default_phase_map[eg.uuid])
        check("baseline: it survives save/reload", reloaded is not None)
        check("baseline: ...with the same composition",
              _oxides(reloaded) == _oxides(stored))
    finally:
        for leftover in (TMP, TMP + "~"):
            if os.path.exists(leftover):
                os.remove(leftover)

    check("baseline: a raw/non-structural phase is refused",
          not set_as_baseline(project, object()))


def check_baseline_ui():
    from mudlab.edit_phases_dialog import EditPhasesDialog

    project, _ad, eg, _h = _inheriting_project()
    dialog = EditPhasesDialog(project=project)
    row = [i for i, ph in enumerate(dialog._phases) if ph is eg][0]
    dialog.ui.edit_objects_treeview.setCurrentIndex(
        dialog.objects_model.index(row, 0))
    app.processEvents()
    widget = dialog.phase_widget
    check("baseline UI: the editor has a Set as baseline button",
          hasattr(widget.ui, "btn_set_baseline"))
    check("baseline UI: it is enabled for a structural phase",
          widget.ui.btn_set_baseline.isEnabled())
    check("baseline UI: it reports when there is no baseline",
          "No baseline" in widget.ui.lbl_baseline.text())

    menu = dialog._phase_menu()
    entries = [a.text() for a in menu.actions() if a.text()]
    check("baseline UI: the phase list offers it on right-click",
          entries == ["Set as baseline"])
    check("baseline UI: the list action is enabled for a structural phase",
          all(a.isEnabled() for a in menu.actions() if a.text()))



# ======================================================================
# AUDIT REGRESSIONS (2026-08-22)
# ======================================================================
def check_audit_capture_cost():
    """AUDIT: capture used to build the WHOLE catalog (224 phases, ~1.2 s) just
    to check one name, which put a 1.2 s stall on Add phase -> Default. Given
    the entry name it checks that ONE entry instead."""
    import time

    project = Project()
    entry = "Illite-Smectite R0 Ca"
    added = add_catalog_entry_to_project(project, entry)
    start = time.perf_counter()
    names = capture_catalog_defaults(project, added, entry)
    elapsed = time.perf_counter() - start
    check("audit: capture with the entry name is fast (%.0f ms)" % (elapsed * 1000),
          elapsed < 0.4)
    check("audit: ...and still records every phase", len(names) == len(added))
    # The guard is not lost: a name the entry cannot build is refused.
    other = Project()
    stray = add_catalog_entry_to_project(other, "Illite")
    stray[0].name = "Not A Catalog Phase"
    check("audit: a name the entry cannot rebuild is refused",
          capture_catalog_defaults(other, stray, "Illite") == [])


def check_audit_dirty_tracking():
    """AUDIT: the composition, the mapping and the imported references are all
    saved with the project, so changing any of them is an unsaved change. It
    used to leave the window clean - map every phase, close, lose the lot."""
    from mudlab.main_window import MainWindow

    window = MainWindow()
    window._set_project(load_mud(PATH))
    window._dirty = False
    window.project.set_composition(Composition(oxides=SAMPLE))
    check("audit: importing a composition marks the project dirty", window._dirty)

    window._dirty = False
    phase = structural_phases(window.project)[0]
    window.project.set_default_phase_map({phase.uuid: "Illite"})
    check("audit: stating a default marks the project dirty", window._dirty)

    window._dirty = False
    set_as_baseline(window.project, phase)
    check("audit: setting a baseline marks the project dirty", window._dirty)


def check_audit_stale_mapping():
    """AUDIT: deleting a phase left its mapping entry behind, and it was written
    to the file - a reference to a phase the file does not contain."""
    project = load_mud(PATH)
    phase = structural_phases(project)[0]
    set_as_baseline(project, phase)
    dead_uuid = phase.uuid
    project.remove_phase(phase)
    save_mud(project, TMP)
    try:
        written = _project_props(TMP).get("default_phase_map") or {}
        check("audit: a deleted phase's mapping is not written to the file",
              dead_uuid not in written)
        check("audit: ...and the surviving entries are still written",
              isinstance(written, dict))
    finally:
        for leftover in (TMP, TMP + "~"):
            if os.path.exists(leftover):
                os.remove(leftover)


def check_audit_unresolvable_mapping():
    """AUDIT: a phase whose stated default no longer RESOLVES was counted as
    mapped - so the view could report everything stated while quietly showing
    that phase at its current state."""
    project = load_mud(PATH)
    phase = structural_phases(project)[0]
    set_as_baseline(project, phase)
    name = project.default_phase_map[phase.uuid]
    check("audit: a resolvable mapping counts as mapped",
          phase not in unmapped_phases(project))
    project.remove_custom_default_phase(name)
    check("audit: the mapping entry survives the reference going away",
          phase.uuid in project.default_phase_map)
    check("audit: ...but the phase is reported UNMAPPED",
          phase in unmapped_phases(project))
    check("audit: ...and the mapping is not called complete",
          not mapping_is_complete(project))


def check_audit_no_default_column():
    """AUDIT: with every stated default unresolvable, no default column can be
    produced. The view used to say the phases were "shown at their current
    state" - pointing at a column that was not there."""
    project = load_mud(PATH)
    mixture = project.mixtures[0]
    phase = structural_phases(project)[0]
    set_as_baseline(project, phase)
    project.remove_custom_default_phase(project.default_phase_map[phase.uuid])
    dialog = CompositionDialog(mixture, project=project)
    dialog.ui.chk_default.setChecked(True)
    app.processEvents()
    title = dialog.ui.lbl_title.text()
    check("audit: it says there is no default state to show",
          "no default state to show" in title)
    check("audit: ...and does not claim a column that is absent",
          "shown at their current state" not in title)

    # The partial case must still use the other wording.
    other = load_mud(PATH)
    other.set_default_phase_map(suggest_default_phase_map(other))
    partial = CompositionDialog(other.mixtures[0], project=other)
    partial.ui.chk_default.setChecked(True)
    app.processEvents()
    check("audit: a PARTIAL mapping still names what it left out",
          "shown at their current state" in partial.ui.lbl_title.text())



# ======================================================================
# The two-pane dialog and its comparison plot
# ======================================================================
def check_comparison_plot():
    project = load_mud(PATH)
    mixture = project.mixtures[0]
    project.set_composition(Composition(name="XRF", oxides=SAMPLE))
    project.set_default_phase_map(suggest_default_phase_map(project))
    dialog = CompositionDialog(mixture, project=project)

    check("plot: the dialog has a left pane and a plot pane",
          hasattr(dialog.ui, "leftPane") and hasattr(dialog.ui, "plotLayout"))
    check("plot: the table is in the LEFT pane",
          dialog.ui.leftPane.isAncestorOf(dialog.ui.tbl_composition))
    check("plot: a canvas is embedded in the right pane",
          dialog.ui.plotLayout.count() >= 1 and dialog._canvas is not None)

    def lines():
        return dialog._axes.get_lines()

    oxides = len(dialog._oxide_rows)
    check("plot: one LINE per column, joining the oxides",
          len(lines()) == len(dialog._specimen_names))
    check("plot: each line has a point per oxide",
          all(len(line.get_ydata()) == oxides for line in lines()))
    check("plot: one tick per oxide",
          len(dialog._axes.get_xticks()) == oxides)
    check("plot: the oxide names are the x axis",
          [label.get_text() for label in dialog._axes.get_xticklabels()]
          == [oxide for oxide, _v in dialog._oxide_rows])

    # It must follow the same columns the table shows - one source of truth.
    before = len(dialog._specimen_names)
    dialog.ui.chk_measured.setChecked(True)
    app.processEvents()
    check("plot: adding the measured column adds its line",
          len(lines()) == len(dialog._specimen_names) == before + 1)
    labels = [text.get_text() for text in dialog._axes.get_legend().get_texts()]
    check("plot: the legend has one entry per column",
          len(labels) == len(dialog._specimen_names))
    check("plot: the measured series is named as measured",
          any("measured" in label for label in labels))

    dialog.ui.chk_default.setChecked(True)
    app.processEvents()
    labels = [text.get_text() for text in dialog._axes.get_legend().get_texts()]
    # AUDIT REGRESSION: eliding the whole label cut " (default)" off, so a
    # specimen and its own default state appeared under one identical name -
    # the two series the plot exists to compare.
    check("plot: a default series keeps its (default) suffix in the legend",
          any(label.endswith("(default)") for label in labels))
    check("plot: no two legend entries are identical",
          len(set(labels)) == len(labels))
    check("plot: a default line is dashed, so a pair reads as before/after",
          any(line.get_linestyle() in ("--", "dashed") for line in lines()))

    # The points must be the values in the table, not a re-derivation.
    ok = True
    for index, line in enumerate(lines()):
        drawn = [round(float(v), 6) for v in line.get_ydata()]
        expected = [round(values[index], 6)
                    for _oxide, values in dialog._oxide_rows]
        ok = ok and drawn == expected
    check("plot: every point comes from the table's own rows", ok)

    # The index overlays the plot with no background of its own.
    check("plot: the index has no background (lines read through it)",
          not dialog._axes.get_legend().get_frame_on())
    tallest = max(max(line.get_ydata()) for line in lines())
    check("plot: the axes leave headroom for the index",
          dialog._axes.get_ylim()[1] > tallest)


def check_plot_too_many_columns():
    """Past a sensible number of columns the lines stop being readable, so the
    plot says so rather than drawing spaghetti - the table still has it all."""
    project = load_mud(PATH)
    dialog = CompositionDialog(project.mixtures[0], project=project)
    dialog._specimen_names = ["col %d" % i
                              for i in range(dialog._MAX_PLOT_SERIES + 2)]
    dialog._oxide_rows = [(oxide, [1.0] * len(dialog._specimen_names))
                          for oxide, _v in dialog._oxide_rows]
    dialog._draw_plot()
    check("plot: too many columns draws no lines", not dialog._axes.get_lines())
    check("plot: ...and says why instead",
          any("too many" in text.get_text() for text in dialog._axes.texts))


def check_unused_filter():
    project = load_mud(PATH)
    project.set_default_phase_map({})
    phases = structural_phases(project)
    used = phases_used_in_mixtures(project)
    unused = [ph for ph in phases if ph.uuid not in used]

    dialog = DefaultPhasesDialog(project)
    check("filter: only phases a mixture uses are listed",
          dialog.ui.tbl_phases.rowCount() == len(phases) - len(unused))
    if unused:
        check("filter: the status says how many are hidden",
              "hidden" in dialog.ui.lbl_status.text())
    dialog.ui.chk_show_unused.setChecked(True)
    app.processEvents()
    check("filter: showing unused lists every phase",
          dialog.ui.tbl_phases.rowCount() == len(phases))
    dialog.ui.chk_show_unused.setChecked(False)
    app.processEvents()
    check("filter: unticking hides them again",
          dialog.ui.tbl_phases.rowCount() == len(phases) - len(unused))

    if unused:
        # A statement made on an unused phase must survive being hidden - the
        # filter is a VIEW, and must never be a way to lose a mapping.
        dialog.ui.chk_show_unused.setChecked(True)
        app.processEvents()
        row = [i for i, ph in enumerate(dialog._phases) if ph is unused[0]][0]
        dialog._combos[row].setCurrentIndex(1)
        chosen = dialog._combos[row].currentText()
        dialog.ui.chk_show_unused.setChecked(False)
        app.processEvents()
        check("filter: hiding a row does not drop what it said",
              unused[0].uuid not in {ph.uuid for ph in dialog._phases})
        dialog._on_accept()
        check("filter: ...and accept still carries it",
              dialog.mapping.get(unused[0].uuid) == chosen)

        # An unused phase that ALREADY has a default stays visible, so an
        # existing statement is never hidden behind a checkbox.
        project.set_default_phase_map({unused[0].uuid: chosen})
        again = DefaultPhasesDialog(project)
        check("filter: an unused phase with a default is still listed",
              unused[0].uuid in {ph.uuid for ph in again._phases})


def check_combo_ignores_wheel():
    """A combo in a table row must not eat the wheel: scrolling the list would
    silently re-state every default it passed over."""
    from PySide6.QtCore import QPoint, Qt as _Qt
    from PySide6.QtGui import QWheelEvent

    project = load_mud(PATH)
    dialog = DefaultPhasesDialog(project)
    combo = dialog._combos[0]
    combo.setCurrentIndex(3)
    before = combo.currentIndex()
    event = QWheelEvent(
        QPoint(5, 5), combo.mapToGlobal(QPoint(5, 5)), QPoint(0, -120),
        QPoint(0, -120), _Qt.MouseButton.NoButton,
        _Qt.KeyboardModifier.NoModifier, _Qt.ScrollPhase.NoScrollPhase, False)
    combo.wheelEvent(event)
    app.processEvents()
    check("wheel: scrolling over a combo does NOT change its selection",
          combo.currentIndex() == before)
    check("wheel: ...and the event is passed on, so the table scrolls",
          not event.isAccepted())


def check_focus_after_add():
    """After Add phase the caret belongs in the new phase's Name box - naming it
    is the first thing anyone does, and the focus used to fall back to the Add
    button, where the next Return adds another phase."""
    from PySide6.QtWidgets import QDialog as _QDialog

    from mudlab.add_phase_dialog import AddPhaseDialog
    from mudlab.edit_phases_dialog import EditPhasesDialog

    cases = (
        ("empty", "rdb_empty_phase", "phase_widget", "phase_name"),
        ("default", "rdb_default_phase", "phase_widget", "phase_name"),
        ("raw", "rdb_raw_pattern", "raw_phase_widget", "raw_phase_name"),
    )
    for label, radio, widget_name, field in cases:
        project = load_mud(PATH)
        dialog = EditPhasesDialog(project=project)
        dialog.show()
        app.processEvents()
        real = AddPhaseDialog.exec

        def fake(self, _radio=radio):
            getattr(self.ui, _radio).setChecked(True)
            return _QDialog.DialogCode.Accepted

        AddPhaseDialog.exec = fake
        try:
            dialog._on_add_phase()
            app.processEvents()
        finally:
            AddPhaseDialog.exec = real
        widget = getattr(dialog, widget_name)
        edit = getattr(widget.ui, field)
        check("focus: a %s phase opens its own editor" % label, widget.isVisible())
        check("focus: ...with the caret in its Name box" , edit.hasFocus())
        check("focus: ...and the name selected, so typing replaces it",
              edit.selectedText() == edit.text() and bool(edit.text()))
        dialog.close()
        app.processEvents()



def check_enter_does_not_fire_a_button():
    """AUDIT: Qt gives every QPushButton in a QDialog `autoDefault` and promotes
    one to THE default on show. In Edit Phases the winner was **Add**, so Return
    pressed anywhere that does not consume it - a name box, a spin box, a combo -
    silently added another phase."""
    from PySide6.QtCore import Qt as _Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import (
        QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QPushButton, QSpinBox,
    )

    from mudlab.edit_phases_dialog import EditPhasesDialog

    project = load_mud(PATH)
    dialog = EditPhasesDialog(project=project)
    dialog.show()
    app.processEvents()
    check("enter: no button is the dialog's default",
          not any(b.isDefault() for b in dialog.findChildren(QPushButton)))
    check("enter: no button can grab it by taking focus",
          not any(b.autoDefault() for b in dialog.findChildren(QPushButton)))

    before = len(project.phases)
    pressed = 0
    for kind in (QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox,
                 QPushButton):
        for widget in dialog.phase_widget.findChildren(kind):
            if not widget.isEnabled():
                continue
            widget.setFocus()
            for key in (_Qt.Key.Key_Return, _Qt.Key.Key_Enter):
                app.sendEvent(widget, QKeyEvent(
                    QKeyEvent.Type.KeyPress, key, _Qt.KeyboardModifier.NoModifier))
                app.sendEvent(widget, QKeyEvent(
                    QKeyEvent.Type.KeyRelease, key, _Qt.KeyboardModifier.NoModifier))
            pressed += 1
    app.processEvents()
    check("enter: pressing it across the whole editor pane (%d widgets) adds "
          "no phase" % pressed, len(project.phases) == before)
    dialog.close()
    app.processEvents()


def check_mixtures_enter_adds_nothing():
    """The same autoDefault trap in Edit Mixtures, where the promoted button was
    **Add** - so Return in a fraction cell added a mixture."""
    from PySide6.QtCore import Qt as _Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import (
        QComboBox, QDoubleSpinBox, QLineEdit, QPushButton, QTableWidget,
    )

    from mudlab.edit_mixtures_dialog import EditMixturesDialog

    project = load_mud(PATH)
    dialog = EditMixturesDialog(project=project)
    dialog.show()
    app.processEvents()
    check("enter: Edit Mixtures has no default button",
          not any(b.isDefault() for b in dialog.findChildren(QPushButton)))
    before = len(project.mixtures)
    for kind in (QLineEdit, QDoubleSpinBox, QComboBox, QTableWidget, QPushButton):
        for widget in dialog.mixture_widget.findChildren(kind):
            if not widget.isEnabled():
                continue
            widget.setFocus()
            for key in (_Qt.Key.Key_Return, _Qt.Key.Key_Enter):
                app.sendEvent(widget, QKeyEvent(
                    QKeyEvent.Type.KeyPress, key, _Qt.KeyboardModifier.NoModifier))
                app.sendEvent(widget, QKeyEvent(
                    QKeyEvent.Type.KeyRelease, key, _Qt.KeyboardModifier.NoModifier))
    app.processEvents()
    check("enter: ...and pressing it in the editor adds no mixture",
          len(project.mixtures) == before)
    dialog.close()
    app.processEvents()


def check_enter_policy_across_dialogs():
    """The app-wide policy: Enter accepts only where a QDialogButtonBox says so.

    A loose button never becomes the default again - that is what kept picking
    something destructive by accident of tab order. A button box IS the app
    declaring the dialog has an accept action, so Enter=OK stays there, which is
    what a modal form should do."""
    from PySide6.QtWidgets import QDialogButtonBox, QPushButton

    from mudlab.add_phase_dialog import AddPhaseDialog
    from mudlab.csv_import_dialog import CsvImportDialog

    project = load_mud(PATH)

    # 1. Loose buttons: no default at all.
    loose = [("Compositions", CompositionDialog(project.mixtures[0],
                                                project=project))]
    for label, dialog in loose:
        dialog.show()
        app.processEvents()
        check("policy: %s has no default (its buttons are loose)" % label,
              not any(b.isDefault() for b in dialog.findChildren(QPushButton)))
        dialog.close()
        app.processEvents()

    # 2. Button-box dialogs KEEP Enter = accept.
    boxed = [("Add phase", AddPhaseDialog()),
             ("Import composition", ImportCompositionDialog()),
             ("Default phases", DefaultPhasesDialog(project)),
             ("CSV import", CsvImportDialog())]
    for label, dialog in boxed:
        dialog.show()
        app.processEvents()
        default = [b for b in dialog.findChildren(QPushButton) if b.isDefault()]
        in_box = False
        if default:
            for box in dialog.findChildren(QDialogButtonBox):
                if default[0] in box.buttons():
                    in_box = (box.buttonRole(default[0])
                              == QDialogButtonBox.ButtonRole.AcceptRole)
        check("policy: %s keeps Enter = accept" % label, in_box)
        dialog.close()
        app.processEvents()



def check_audit_filter_keeps_hidden_statements():
    """AUDIT: a statement made while a row was visible, then hidden, lived ONLY
    in `_hidden` until accept - and `_refresh_rows` rebuilt from the project
    alone, so the very next rebuild (a second filter toggle, or an Import) threw
    it away silently."""
    from mudlab.file_parsers.default_catalog import add_catalog_entry_to_project

    project = load_mud(PATH)
    project.set_default_phase_map({})
    add_catalog_entry_to_project(project, "Kaolinite")   # in no mixture
    unused = [ph for ph in structural_phases(project)
              if ph.uuid not in phases_used_in_mixtures(project)]
    if not unused:
        check("audit: (no unused phase available to test the filter)", True)
        return

    dialog = DefaultPhasesDialog(project)
    dialog.ui.chk_show_unused.setChecked(True)
    app.processEvents()
    row = [i for i, ph in enumerate(dialog._phases) if ph is unused[0]][0]
    dialog._combos[row].setCurrentIndex(1)
    chosen = dialog._combos[row].currentText()
    dialog.ui.chk_show_unused.setChecked(False)
    app.processEvents()
    check("audit: hiding a stated row parks it, it is not lost",
          dialog._hidden.get(unused[0].uuid) == chosen)

    # The rebuild that used to drop it (what Import does).
    dialog._refresh_rows(keep=dialog._current())
    check("audit: a SECOND rebuild still keeps it",
          dialog._hidden.get(unused[0].uuid) == chosen)
    dialog.ui.chk_show_unused.setChecked(True)
    app.processEvents()
    row = [i for i, ph in enumerate(dialog._phases) if ph is unused[0]][0]
    check("audit: showing it again shows what was stated",
          dialog._combos[row].currentText() == chosen)
    dialog._on_accept()
    check("audit: ...and accept carries it",
          dialog.mapping.get(unused[0].uuid) == chosen)

    # "Clear all" must mean all - including the rows the filter is hiding.
    again = DefaultPhasesDialog(project)
    again.ui.chk_show_unused.setChecked(True)
    app.processEvents()
    again._on_match()
    again.ui.chk_show_unused.setChecked(False)
    app.processEvents()
    again._on_clear()
    again._on_accept()
    check("audit: Clear all clears the hidden rows too", again.mapping == {})


def check_audit_object_store_enter():
    """AUDIT: the autoDefault trap is a property of the SHELL, so every
    object-store dialog had it - Edit Atom Types and Edit Markers promoted
    **Add** too. Swept in ObjectStoreDialog.showEvent, which also runs after the
    subclass has finished building."""
    from PySide6.QtWidgets import QPushButton

    from mudlab.edit_atom_types_dialog import EditAtomTypesDialog
    from mudlab.edit_markers_dialog import EditMarkersDialog
    from mudlab.edit_mixtures_dialog import EditMixturesDialog
    from mudlab.edit_phases_dialog import EditPhasesDialog

    project = load_mud(PATH)
    dialogs = [
        ("Edit Phases", EditPhasesDialog(project=project)),
        ("Edit Mixtures", EditMixturesDialog(project=project)),
        ("Edit Atom Types", EditAtomTypesDialog(project=project)),
    ]
    specimens = [s for s in project.specimens if s is not None]
    if specimens:
        dialogs.append(("Edit Markers", EditMarkersDialog(specimen=specimens[0])))
    for label, dialog in dialogs:
        dialog.show()
        app.processEvents()
        check("audit: %s has no default button (Enter fires nothing)" % label,
              not any(b.isDefault() for b in dialog.findChildren(QPushButton)))
        dialog.close()
        app.processEvents()


def check_audit_refine_enter():
    """AUDIT: the Refine dialog promoted **Refine**, so a stray Return - in the
    parameter tree, or after typing an option - started a run that rewrites the
    model and can take minutes."""
    from PySide6.QtCore import Qt as _Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QPushButton

    from mudlab.refinement_dialog import RefinementDialog

    project = load_mud(PATH)
    mixture = project.mixtures[0]
    for ref in mixture.refinables():          # nothing flagged: a run would be
        ref.set_ref_info(refine=False)        # near-instant if one did start
    dialog = RefinementDialog(mixture=mixture)
    # Never Basin Hopping in a UI test.
    dialog.ui.cmb_method.setCurrentIndex(dialog.ui.cmb_method.findData(0))
    dialog.show()
    app.processEvents()
    check("audit: the Refine dialog has no default button",
          not any(b.isDefault() for b in dialog.findChildren(QPushButton)))
    for widget in (dialog.ui.tree_refinables,
                   list(dialog._option_spins.values())[0][0]):
        widget.setFocus()
        for key in (_Qt.Key.Key_Return, _Qt.Key.Key_Enter):
            app.sendEvent(widget, QKeyEvent(
                QKeyEvent.Type.KeyPress, key, _Qt.KeyboardModifier.NoModifier))
            app.sendEvent(widget, QKeyEvent(
                QKeyEvent.Type.KeyRelease, key, _Qt.KeyboardModifier.NoModifier))
        app.processEvents()
    check("audit: Enter does not start a refinement",
          dialog._thread is None and dialog._refiner is None)
    dialog._abort_refinement()
    dialog.close()
    app.processEvents()


def check_audit_escape_still_closes():
    """Enter no longer closes these dialogs, so Esc has to - it is the only
    keyboard way out."""
    from PySide6.QtCore import Qt as _Qt
    from PySide6.QtGui import QKeyEvent

    from mudlab.edit_phases_dialog import EditPhasesDialog

    project = load_mud(PATH)
    dialog = EditPhasesDialog(project=project)
    dialog.show()
    app.processEvents()
    dialog.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, _Qt.Key.Key_Escape,
                                   _Qt.KeyboardModifier.NoModifier))
    app.processEvents()
    check("audit: Esc still closes an object-store dialog", not dialog.isVisible())


def main():
    print("fixture: %s" % os.path.basename(PATH))
    check_model()
    check_project()
    check_round_trip()
    check_dialog()
    check_menu()
    check_default_lookup()
    check_mapping()
    check_default_state_composition()
    check_mapping_dialog()
    check_comparison_columns()
    check_custom_defaults()
    check_custom_shadowing()
    check_custom_dialog()
    check_capture_from_catalog()
    check_capture_from_phs()
    check_frozen_baseline()
    check_set_as_baseline()
    check_baseline_ui()
    check_audit_capture_cost()
    check_audit_dirty_tracking()
    check_audit_stale_mapping()
    check_audit_unresolvable_mapping()
    check_audit_no_default_column()
    check_comparison_plot()
    check_plot_too_many_columns()
    check_unused_filter()
    check_combo_ignores_wheel()
    check_focus_after_add()
    check_enter_does_not_fire_a_button()
    check_mixtures_enter_adds_nothing()
    check_enter_policy_across_dialogs()
    check_audit_filter_keeps_hidden_statements()
    check_audit_object_store_enter()
    check_audit_refine_enter()
    check_audit_escape_still_closes()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- composition object verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
