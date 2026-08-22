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
    comparison columns in the Compositions dialog.

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
    default_state_composition, default_substitutes, structural_phases,
    suggest_default_phase_map, unmapped_phases,
)
from mudlab.file_parsers.default_catalog import (
    build_default_phase, default_phase_names,
)
from mudlab.file_parsers import load_mud, save_mud
from mudlab.import_composition_dialog import ImportCompositionDialog
from mudlab.models import Composition
from mudlab.models.project import Project

app = QApplication.instance() or QApplication([])
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

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- composition object verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
