#!/usr/bin/env python
"""Durable harness for .cmp component import / export, run head-less.

A .cmp is a ZIP of "<uuid>" -> a Component JSON. Component import is a REPLACE
(the imported component takes a selected component's place), so the phase's
component count - and its stacking model - is unchanged. This covers:

  1. export writes a standalone .cmp (linked_with dropped, inherit flags off,
     atom types by name);
  2. round-trip: load_cmp resolves atom types by name and gives the component
     (and every atom) a FRESH uuid, so nothing aliases the source; name / cell /
     atom counts survive;
  3. import into a project WITHOUT the atom types reports them missing;
  4. through the component editor: export the selected component, import it back,
     and the phase's component is REPLACED (fresh uuid) with G unchanged.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_cmp_import.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project.
"""

from __future__ import annotations

import os
import sys
import tempfile
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import json  # noqa: E402

from PySide6.QtWidgets import QApplication, QFileDialog  # noqa: E402

from mudlab.component_widget import EditComponentWidget  # noqa: E402
from mudlab.file_parsers.cmp_components import load_cmp, save_cmp  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

_FIXTURE = "308 r1.mud"
FIXTURE = os.path.join(_REPO, "tools", "sample_projects", _FIXTURE)
if not os.path.isfile(FIXTURE):
    FIXTURE = os.path.join(os.path.expanduser("~"), "Downloads", _FIXTURE)

_app = QApplication.instance() or QApplication([])
results = []


def check(label, ok):
    results.append((label, bool(ok)))


def _atom_type_map(project):
    table = {}
    for at in project.atom_types:
        table[at.uuid] = at
        table[at.name] = at
    return table


def _atom_uuids(comp):
    return {a.uuid for a in comp._layer_atoms + comp._interlayer_atoms}


def run(tmp):
    project = load_mud(FIXTURE)
    phase = next(p for p in project.phases if p.components)
    comp = phase.components[0]

    # 1. Export writes a standalone .cmp.
    cmp_path = os.path.join(tmp, "layer.cmp")
    save_cmp([comp], cmp_path)
    with zipfile.ZipFile(cmp_path) as z:
        names = z.namelist()
        entry = json.loads(z.read(names[0]).decode("utf-8"))
    props = entry.get("properties", {})
    check("1 .cmp is a ZIP whose member is the component uuid",
          len(names) == 1 and names[0] == comp.uuid)
    check("1 export is standalone (linked_with dropped, inherit flags off)",
          props.get("linked_with_uuid", "") == ""
          and all(not props.get(k, False) for k in props if k.startswith("inherit_")))
    check("1 atoms carry atom_type_name (portable by name)",
          all(a.get("properties", {}).get("atom_type_name")
              for a in props.get("layer_atoms", []) + props.get("interlayer_atoms", [])))

    # 2. Round-trip into the SAME project's atom types -> fresh uuids, resolved.
    imported, missing = load_cmp(cmp_path, _atom_type_map(project))
    check("2 exactly one component imported", len(imported) == 1)
    new = imported[0]
    check("2 name + atom counts preserved",
          new.name == comp.name
          and len(new._layer_atoms) == len(comp._layer_atoms)
          and len(new._interlayer_atoms) == len(comp._interlayer_atoms))
    check("2 atom types resolve by name (nothing missing)", missing == [])
    check("2 component + every atom got a FRESH uuid (no alias of the source)",
          new.uuid != comp.uuid and _atom_uuids(new).isdisjoint(_atom_uuids(comp)))
    check("2 imported component is standalone (not linked)",
          new.linked_with is None)

    # 3. Import without the atom types -> reported missing.
    _, missing_bare = load_cmp(cmp_path, {})
    check("3 missing atom types reported when the project lacks them",
          len(missing_bare) > 0)

    # 4. Through the editor: export then import replaces the component, G fixed.
    widget = EditComponentWidget()
    widget.bind_components(phase.components, atom_types=project.atom_types)
    widget.ui.cmb_component.setCurrentIndex(0)
    g0 = len(phase.components)
    before = phase.components[0].uuid
    ui_cmp = os.path.join(tmp, "ui.cmp")
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (ui_cmp, ""))
    widget._on_export_component()
    check("4 editor export wrote a .cmp", os.path.isfile(ui_cmp))
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (ui_cmp, ""))
    widget._on_import_component()
    check("4 import REPLACED the phase's component (fresh uuid), G unchanged",
          len(phase.components) == g0 and phase.components[0].uuid != before)
    check("4 replaced component's atoms still resolve their atom types",
          all(a.atom_type is not None for a in phase.components[0]._layer_atoms
              + phase.components[0]._interlayer_atoms))
    widget.deleteLater()


def main():
    print("=" * 72)
    print("Component file (.cmp) import / export")
    print("=" * 72)
    if not os.path.isfile(FIXTURE):
        print("No sample project found; skipping (exit 2).")
        return 2
    with tempfile.TemporaryDirectory(prefix="mudlab_cmp_") as tmp:
        run(tmp)
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("CMP-import harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
