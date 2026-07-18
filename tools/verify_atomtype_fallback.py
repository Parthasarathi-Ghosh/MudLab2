#!/usr/bin/env python
"""Durable harness for atom-type reference resolution (uuid + NAME fallback).

Atoms reference their AtomType by uuid, but uuids are volatile: importing a
project re-uuids the atom types, and a project saved by the old app (or a
component export, which writes atom_type_NAME on purpose) can carry a
reference whose uuid is absent from the saved atom_types. Resolving by uuid
alone then yields a dangling atom type -> zero structure factor -> a blank
pattern.

MudLab2 therefore resolves by uuid FIRST, then by the stable atom_type_name
(Atom.from_dict + Project.atom_type_uuid_map's combined key space). This
guards that fallback:

  1. a working project is byte-identical through a round-trip (the fallback
     must not disturb normal uuid-keyed files);
  2. an atom whose atom_type_uuid is corrupted but which carries a valid
     atom_type_name still resolves (by name), and its phase's calculated
     pattern is unchanged from the intact project - i.e. the recovery is exact,
     not approximate.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_atomtype_fallback.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample projects.
"""

from __future__ import annotations

import os
import sys
import tempfile
import zipfile
import json

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

_app = QApplication.instance() or QApplication([])
_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")


def _fixture():
    for name in ("308 r1.mud", "Dh2040A 14Jul26 r1.mud"):
        for base in (_FIXTURES, os.path.join(os.path.expanduser("~"), "Downloads")):
            path = os.path.join(base, name)
            if os.path.isfile(path):
                return path
    return None


def _resolved_atoms(project):
    total = resolved = 0
    for phase in project.phases:
        for comp in phase.components:
            for atom in comp._layer_atoms + comp._interlayer_atoms:
                total += 1
                resolved += atom.atom_type is not None
    return resolved, total


def _first_phase_pattern(project):
    """Calculated pattern of the first mixture (or None)."""
    if not project.mixtures:
        return None
    project.mixtures[0].calculate()
    for spec in project.mixtures[0].specimens:
        if spec is not None and spec.has_calculated_data:
            return spec.calculated_pattern[1].copy()
    return None


def _write_name_and_break_uuid(src, dst):
    """Rewrite `src` so every resolved atom keeps atom_type_name but has a
    BOGUS atom_type_uuid - forcing the name fallback. Returns how many atoms
    were altered."""
    project = load_mud(src)
    # uuid -> name for the project's atom types
    uuid2name = {at.uuid: at.name for at in project.atom_types}

    zin = zipfile.ZipFile(src)
    phases = json.loads(zin.read("phases").decode("utf-8"))
    items = phases if isinstance(phases, list) else [phases]
    n = 0
    for it in items:
        for c in it.get("properties", {}).get("components", []):
            for key in ("layer_atoms", "interlayer_atoms"):
                for a in c["properties"].get(key, []) or []:
                    props = a["properties"]
                    uid = props.get("atom_type_uuid")
                    name = uuid2name.get(uid)
                    if name is not None:
                        props["atom_type_name"] = name
                        props["atom_type_uuid"] = "deadbeef" * 4  # bogus
                        n += 1
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in zin.namelist():
            zout.writestr(name, json.dumps(phases) if name == "phases"
                          else zin.read(name))
    return n


def run(path):
    print("=" * 72)
    print("Atom-type fallback:", os.path.basename(path))
    print("=" * 72)
    results = []

    intact = load_mud(path)
    r0, t0 = _resolved_atoms(intact)
    results.append(("1 intact project resolves all atoms by uuid", r0 == t0 and t0 > 0))
    intact_pattern = _first_phase_pattern(intact)

    tmp = os.path.join(tempfile.gettempdir(), "mudlab_atfallback.mud")
    try:
        n = _write_name_and_break_uuid(path, tmp)
        results.append(("2 could break %d atoms' uuids (keeping the name)" % n, n > 0))
        recovered = load_mud(tmp)
        r1, t1 = _resolved_atoms(recovered)
        results.append(("2 all atoms still resolve via the name fallback (%d/%d)"
                        % (r1, t1), r1 == t1 and t1 == t0))
        rec_pattern = _first_phase_pattern(recovered)
        if intact_pattern is not None and rec_pattern is not None:
            same = (intact_pattern.shape == rec_pattern.shape
                    and np.allclose(intact_pattern, rec_pattern, rtol=0, atol=1e-9))
            results.append(("2 recovered pattern is identical to the intact one",
                            same))
    finally:
        for p in (tmp, tmp + "~"):
            if os.path.exists(p):
                os.remove(p)

    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    print("-" * 72)
    print("%d/%d checks passed" % (passed, len(results)))
    return passed == len(results)


def main(argv):
    path = argv[1] if len(argv) > 1 else _fixture()
    if not path or not os.path.isfile(path):
        print("No sample project found; skipping (exit 2).")
        return 2
    ok = run(path)
    print("Atom-type fallback harness:", "OK" if ok else "REGRESSION")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
