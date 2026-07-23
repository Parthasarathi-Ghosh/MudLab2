#!/usr/bin/env python
"""Durable harness for the bundled default-component catalog (Step 2).

The reference clay-layer components ship as `.cmp` files under
`src/mudlab/data/default components/`. Each is a ZIP of Component JSON whose
atoms reference atom types by name; resolved against the built-in scattering-
factor library they must produce a computable phase. This checks:

  1. the bundle is complete: every `.cmp` the generator recipe names is present,
     and every bundled `.cmp` is a valid (non-corrupted) ZIP.
  2. every default component loads + resolves its atoms against the library
     (each atom gets a real atom type with non-zero scattering factors).
  3. a phase built from each single-layer default component computes a NON-blank
     pattern (the whole point - the library + components together are usable).

Run head-less from the repo root:

    ./python/python.exe tools/verify_default_components.py

Exit codes: 0 = all pass, 1 = a regression, 2 = the bundle is missing.
"""

from __future__ import annotations

import os
import sys
import zipfile
from itertools import chain

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402

from mudlab.file_parsers.atom_type_library import atom_type_library_map  # noqa: E402
from mudlab.file_parsers.default_catalog import (  # noqa: E402
    default_components_dir, load_default_component,
)
from mudlab.models.phase import Phase  # noqa: E402

# The 4-char aliases -> .cmp path the generator recipe uses (a representative
# set covering every referenced file). If one is missing the catalog can't build.
_RECIPE_FILES = [
    "Chlorite.cmp", "Kaolinite.cmp", "Illite.cmp", "Serpentine.cmp", "Talc.cmp",
    "Margarite.cmp", "Paragonite.cmp", "Leucophyllite.cmp",
    "Di-Smectite/Di-Smectite - Ca 2WAT.cmp", "Di-Smectite/Di-Smectite - Ca 1WAT.cmp",
    "Di-Smectite/Di-Smectite - Ca Dehydr.cmp", "Di-Smectite/Di-Smectite - Ca 2GLY.cmp",
    "Di-Smectite/Di-Smectite - Ca 1GLY.cmp", "Di-Smectite/Di-Smectite - Ca Heated.cmp",
    "Tri-Smectite/Tri-Smectite - Ca 2WAT.cmp",
    "Di-Vermiculite/Di-Vermiculite - Ca 2WAT.cmp",
]
_SINGLE_LAYER = [
    "Chlorite.cmp", "Kaolinite.cmp", "Illite.cmp", "Serpentine.cmp", "Talc.cmp",
    "Margarite.cmp", "Paragonite.cmp", "Leucophyllite.cmp",
]

results = []


def check(label, ok):
    results.append((label, bool(ok)))


def run():
    root = default_components_dir()
    all_cmp = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith(".cmp"):
                all_cmp.append(os.path.join(dirpath, name))

    # 1. Bundle complete + intact.
    check("1 the default-component bundle exists with >= 27 files",
          len(all_cmp) >= 27)
    missing = [rel for rel in _RECIPE_FILES
               if not os.path.isfile(os.path.join(root, rel))]
    check("1 every recipe-referenced .cmp is present", not missing)
    if missing:
        print("    missing:", missing)
    check("1 every bundled .cmp is a valid ZIP (not eol-corrupted)",
          all(zipfile.is_zipfile(p) for p in all_cmp))

    # 2. Every component loads + resolves against the library.
    lib = atom_type_library_map()
    unresolved = []
    for rel in _RECIPE_FILES:
        comps = load_default_component(rel, lib)
        for c in comps:
            for atom in chain(c.layer_atoms, c.interlayer_atoms):
                at = getattr(atom, "atom_type", None)
                if at is None or float(np.sum(at.par_a)) == 0.0:
                    unresolved.append((rel, atom.name))
    check("2 every default component's atoms resolve to library scattering factors",
          not unresolved)
    if unresolved:
        print("    unresolved (first 5):", unresolved[:5])

    # 3. Each single-layer default component builds a computable phase.
    rng = np.linspace(1, 30, 300)
    stl = 2 * np.sin(np.radians(rng / 2)) / 1.5406
    blank = []
    for rel in _SINGLE_LAYER:
        comps = load_default_component(rel, lib)
        phase = Phase(name=rel, G=1)
        phase.components = comps
        intensity = phase.get_intensity(rng, stl, 0.5, 0.5, 0.0)
        if not (np.any(intensity > 0) and float(np.max(intensity)) > 0):
            blank.append(rel)
    check("3 every single-layer default component computes a NON-blank pattern",
          not blank)
    if blank:
        print("    blank:", blank)
    return None


def main():
    print("=" * 72)
    print("Default-component catalog bundle")
    print("=" * 72)
    if not os.path.isdir(default_components_dir()):
        print("Default-component bundle missing; skipping (exit 2).")
        return 2
    rc = run()
    if rc == 2:
        return 2
    passed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        passed += bool(ok)
    print("-" * 72)
    print("Default-components harness: %d/%d checks: %s"
          % (passed, len(results), "OK" if passed == len(results) else "REGRESSION"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
