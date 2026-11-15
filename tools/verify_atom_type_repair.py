#!/usr/bin/env python
"""Repair at load: atom types a project's atoms name but the project lacks.

MudLab 1.0.4 and 1.1.0 could save a broken project. Edit Phases -> component ->
Import CIF... added the atom types a CIF needed (potassium, for an illite) to
the editor's private copy of the atom-type list, never to the project's. A
saved project writes only its own list, so on reload those atoms had no atom
type and scattered nothing - silently. The import itself is fixed
(verify_structure_library.py); `mud_project.restore_missing_atom_types` repairs
the projects that were already saved, and the main window says so.

Checked here, on a project saved EXACTLY as the old code saved it (the CIF's
component installed without its atom types reaching the project):

1. The file really is broken: the potassium has no atom type in it.
2. Loading restores K1+ from the built-in library, once, and every atom of the
   component resolves to the project's own atom types; the phase's calculated
   pattern then differs from the broken one (the potassium scatters again).
3. Saved again and reloaded, nothing more needs restoring.
4. A sound project is untouched: nothing restored, its atom-type list as saved.
5. A name the library does not know is left alone, without an error.
6. Opening the broken project in the main window says what was restored and
   marks the project unsaved, so closing without saving cannot lose it again.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_atom_type_repair.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

app = QApplication.instance() or QApplication([])

from mudlab.calculations.goniometer import get_machine_correction_range  # noqa: E402
from mudlab.calculations.specimen import calculate_phase_intensities  # noqa: E402
from mudlab.cif_import_dialog import CifImportDialog  # noqa: E402
from mudlab.file_parsers.default_catalog import add_catalog_entry_to_project  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.models import Project  # noqa: E402
from mudlab.models.goniometer import Goniometer  # noqa: E402

ILLITE = os.path.join(_REPO, "structures", "Clays", "Illite-1M__AMCSD-0005015.cif")
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def atoms_of(phase):
    out = []
    for component in phase.components:
        out += list(component._layer_atoms) + list(component._interlayer_atoms)
    return out


def pattern(phase):
    gonio = Goniometer()
    gonio.min_2theta, gonio.max_2theta, gonio.steps = 2.0, 45.0, 2151
    theta = np.radians(np.linspace(2.0, 45.0, 2151) * 0.5)
    correction = get_machine_correction_range(gonio, theta)
    return calculate_phase_intensities(
        theta, gonio.wavelength, gonio.wavelength_distribution, gonio.soller1,
        gonio.soller2, gonio.mcr_2theta, correction, [phase])[0]


def broken_project_file(folder) -> str:
    """A project saved the way 1.0.4 / 1.1.0 saved it: two Kaolinite phases
    whose components were each replaced by an illite from a CIF, the illites'
    potassium types held only by the components, never by the project. Two, so
    the repair must restore K1+ ONCE and point both phases' atoms at it."""
    project = Project()
    add_catalog_entry_to_project(project, "Kaolinite")
    add_catalog_entry_to_project(project, "Kaolinite")
    for phase in project.phases:
        dialog = CifImportDialog(None, path=ILLITE,
                                 atom_type_map=project.atom_type_uuid_map())
        dialog._on_accept()
        phase.components[0] = dialog.component   # the old install: no adopt
        dialog.deleteLater()
    path = os.path.join(folder, "broken.mud")
    save_mud(project, path)
    return path


def main() -> int:
    print("=" * 72)
    print("Restoring missing atom types at load")
    print("=" * 72)
    folder = tempfile.mkdtemp()
    path = broken_project_file(folder)

    with zipfile.ZipFile(path) as archive:
        saved_types = [t["properties"]["name"]
                       for t in json.loads(archive.read("atom_types"))]
    check("the file is broken as 1.0.4/1.1.0 left it: K1+ is not among its atom "
          "types (%s)" % ", ".join(saved_types), "K1+" not in saved_types)

    project = load_mud(path)
    phase = project.phases[0]
    check("loading restores K1+, once (%s)" % project.restored_atom_types,
          project.restored_atom_types == ["K1+"]
          and [t.name for t in project.atom_types].count("K1+") == 1)
    every_atom = [a for p in project.phases for a in atoms_of(p)]
    check("every atom of both phases resolves to one of the project's own types",
          every_atom and all(
              a.atom_type is not None and any(a.atom_type is t for t in project.atom_types)
              for a in every_atom))
    potassium = {id(a.atom_type) for a in every_atom if a.atom_type and a.atom_type.name == "K1+"}
    check("...both phases' potassium share the ONE restored atom type",
          len(potassium) == 1
          and sum(1 for a in every_atom if a.atom_type and a.atom_type.name == "K1+") >= 2)
    repaired = pattern(phase)
    restored_k = next((t for t in project.atom_types if t.name == "K1+"), None)
    broken_atoms = [a for a in atoms_of(phase)
                    if restored_k is not None and a.atom_type is restored_k]
    for atom in broken_atoms:
        atom.atom_type = None
    broken = pattern(phase)
    for atom in broken_atoms:
        atom.atom_type = restored_k
    change = float(np.max(np.abs(repaired - broken)) / max(np.max(repaired), 1e-12))
    check("the potassium scatters again: the pattern changes by %.1f%% of its peak"
          % (100 * change), broken_atoms and change > 0.01)

    again_path = os.path.join(folder, "repaired.mud")
    save_mud(project, again_path)
    again = load_mud(again_path)
    check("saved again and reloaded, nothing more needs restoring",
          again.restored_atom_types == []
          and all(a.atom_type is not None for a in atoms_of(again.phases[0])))

    sound = Project()
    add_catalog_entry_to_project(sound, "Kaolinite")
    sound_path = os.path.join(folder, "sound.mud")
    save_mud(sound, sound_path)
    reloaded = load_mud(sound_path)
    check("a sound project is untouched: nothing restored, the same atom types",
          reloaded.restored_atom_types == []
          and sorted(t.name for t in reloaded.atom_types)
          == sorted(t.name for t in sound.atom_types))

    # An atom naming a type the library does not know: left alone, no error.
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    phases = json.loads(parts["phases"])
    text = json.dumps(phases).replace('"atom_type_name": "K1+"',
                                      '"atom_type_name": "Unobtainium9+"')
    parts["phases"] = text.encode("utf-8")
    odd_path = os.path.join(folder, "unknown.mud")
    with zipfile.ZipFile(odd_path, "w") as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    try:
        odd = load_mud(odd_path)
        loaded = True
    except Exception:  # noqa: BLE001
        odd, loaded = None, False
    check("a name the library does not know is left alone, without an error",
          loaded and odd.restored_atom_types == []
          and any(a.atom_type is None for a in atoms_of(odd.phases[0])))

    from mudlab.main_window import MainWindow

    told = []
    real_open, real_info = QFileDialog.getOpenFileName, QMessageBox.information
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (path, ""))
    QMessageBox.information = staticmethod(lambda *a, **k: told.append(str(a[2])))
    try:
        window = MainWindow()
        window._open_project()
        check("opening it in MudLab says what was restored",
              len(told) == 1 and "K1+" in told[0] and "Save the project" in told[0])
        check("...and marks the project unsaved, so the repair is not lost",
              window._dirty is True)
        told.clear()
        QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (sound_path, ""))
        window._dirty = False
        window._open_project()
        check("a sound project opens with no message and stays saved",
              not told and window._dirty is False)
        window.setWindowModified(False)
        window._dirty = False
        window.deleteLater()
    finally:
        QFileDialog.getOpenFileName = real_open
        QMessageBox.information = real_info

    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    passed = sum(ok for _, ok in results)
    print("%d/%d checks passed" % (passed, len(results)))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
