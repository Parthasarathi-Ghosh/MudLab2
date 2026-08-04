#!/usr/bin/env python
"""Durable harness for .phs phase import / export (Batch 4), run head-less.

A .phs is a ZIP of "<index>###<uuid>" -> Phase JSON members; atoms reference
atom types by NAME, so a phase imports against whatever atom types the target
project holds. This covers:

  1. export writes a valid .phs (ZIP, "<i>###<uuid>" members);
  2. round-trip into a fresh project seeded with the atom types - the phase
     resolves its atom types (nothing missing) and keeps name / G / components;
  3. import into a project WITHOUT the atom types reports them missing;
  4. re-importing a phase already in the project DEEP-remaps every colliding
     uuid (phase, component AND atom) so nothing aliases the existing copy;
  5. a based_on family round-trips: the parent is written first and the child's
     based_on link is re-resolved within the imported set.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_phs_import.py

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

from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.file_parsers.phs_phases import load_phs, save_phs  # noqa: E402
from mudlab.models import Project  # noqa: E402
from mudlab.models.phase import Phase  # noqa: E402

_FIXTURE = "308 r1.mud"
FIXTURE = os.path.join(_REPO, "tools", "sample_projects", _FIXTURE)
if not os.path.isfile(FIXTURE):
    FIXTURE = os.path.join(os.path.expanduser("~"), "Downloads", _FIXTURE)

_app = QApplication.instance() or QApplication([])
results = []


def check(label, ok):
    results.append((label, bool(ok)))


def _seed_project_with_atom_types(source):
    proj = Project()
    for at in source.atom_types:
        proj.add_atom_type(at)
    return proj


def run(tmp):
    project = load_mud(FIXTURE)
    src = project.phases[0]

    # 1. Export writes a valid .phs.
    phs = os.path.join(tmp, "one.phs")
    save_phs([src], phs)
    with zipfile.ZipFile(phs) as z:
        names = z.namelist()
    check("1 .phs is a ZIP with one '<i>###<uuid>' member",
          len(names) == 1 and names[0].startswith("0###")
          and names[0].split("###")[1] == src.uuid)

    # 2. Round-trip into a fresh project that has the atom types.
    fresh = _seed_project_with_atom_types(project)
    imported, missing = load_phs(phs, fresh)
    check("2 one phase imported", len(imported) == 1 and len(fresh.phases) == 1)
    got = imported[0]
    check("2 name / G / component count preserved",
          got.name == src.name and got.G == src.G
          and len(got.components) == len(src.components))
    check("2 atom types resolve by name (nothing missing)", missing == [])
    check("2 imported atoms are bound to an atom type",
          all(a.atom_type is not None
              for c in got.components
              for a in c._layer_atoms + c._interlayer_atoms))

    # 3. Import into a project WITHOUT the atom types -> reported missing.
    bare = Project()
    _, missing_bare = load_phs(phs, bare)
    check("3 missing atom types reported when the project lacks them",
          len(missing_bare) > 0)

    # 4. Collision: re-import into the SAME source project. The DEEP remap must
    #    give the phase AND every component / atom a fresh uuid, so nothing in
    #    the re-imported copy aliases the original.
    def _uuids(phase):
        us = {phase.uuid}
        for c in phase.components:
            us.add(c.uuid)
            for a in c._layer_atoms + c._interlayer_atoms:
                us.add(a.uuid)
        return us

    n0 = len(project.phases)
    src_uuids = _uuids(src)
    imp2, _ = load_phs(phs, project)
    new = imp2[0]
    check("4 collision -> a phase was added with a fresh uuid",
          len(project.phases) == n0 + 1 and new.uuid != src.uuid)
    check("4 deep remap -> no component/atom uuid aliases the original",
          _uuids(new).isdisjoint(src_uuids))
    check("4 re-imported atoms still resolve their atom types (by name)",
          all(a.atom_type is not None
              for c in new.components
              for a in c._layer_atoms + c._interlayer_atoms))

    # 4b. Persistence: the project holding the original + the re-imported phase
    #     saves and reloads with NO duplicate component uuids and every atom
    #     resolved - the .mud corruption the deep remap prevents.
    out = os.path.join(tmp, "with_reimport.mud")
    save_mud(project, out)
    reloaded = load_mud(out)
    comp_uuids = [c.uuid for ph in reloaded.phases for c in ph.components]
    check("4b saved .mud has no duplicate component uuids",
          len(comp_uuids) == len(set(comp_uuids)))
    check("4b every atom still resolves after save/reload",
          all(a.atom_type is not None for ph in reloaded.phases
              for c in ph.components
              for a in c._layer_atoms + c._interlayer_atoms))

    # 5. based_on family: parent written first, link re-resolved on import.
    parent = Phase.create_empty(G=2, R=0, name="Parent")
    child = Phase.create_empty(G=2, R=0, name="Child")
    check("5 child can be based on the parent", child.set_based_on(parent))
    fam = os.path.join(tmp, "family.phs")
    save_phs([child, parent], fam)   # deliberately child-first
    with zipfile.ZipFile(fam) as z:
        ordered = sorted(z.namelist(), key=lambda n: int(n.split("###")[0]))
    check("5 parent is written first in the family",
          ordered[0].split("###")[1] == parent.uuid)
    fam_proj = Project()
    imp_fam, _ = load_phs(fam, fam_proj)
    ichild = next((p for p in imp_fam if p.name == "Child"), None)
    iparent = next((p for p in imp_fam if p.name == "Parent"), None)
    check("5 based_on re-resolved within the imported family",
          ichild is not None and iparent is not None
          and ichild.based_on is iparent)

    # 6. The Import/Export file filter offers .phs only - no misleading "All
    # files" option (import reads nothing else; export always writes .phs).
    from mudlab.file_parsers.phs_phases import PHS_FILTERS
    check("6 file filter is .phs only (no 'All files')",
          "*.phs" in PHS_FILTERS
          and "*.*" not in PHS_FILTERS and "All files" not in PHS_FILTERS)


def main():
    print("=" * 72)
    print("Phase file (.phs) import / export")
    print("=" * 72)
    if not os.path.isfile(FIXTURE):
        print("No sample project found; skipping (exit 2).")
        return 2
    with tempfile.TemporaryDirectory(prefix="mudlab_phs_") as tmp:
        run(tmp)
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("PHS-import harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
