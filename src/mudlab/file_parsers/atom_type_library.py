"""Built-in atom-type scattering-factor library.

The old app shipped `atomic scattering factors.atl` - a CSV of the
Waasmaier & Kirfel analytical scattering-factor coefficients for every element
and common ion - and let a phase's atoms resolve their `par_a`/`par_b`
coefficients from it by NAME. MudLab2 had no such library: atom types only
carried scattering factors when they came in from a loaded `.mud`, so a `.cmp`
component (whose atoms reference atom types by name) computed a blank pattern on
its own.

This ports that library. `load_atom_type_library()` reads the bundled CSV
(`mudlab/data/atomic_scattering_factors.csv`, the old `.atl` verbatim) into
`AtomType` models; `atom_type_library_map()` keys them by name for resolving
atom references. It is the prerequisite for the default-phase catalog (a
default component's atoms resolve against this) and backs the Edit Atom Types
"fill from element" picker.

CSV columns (16): atom_nr, name, charge, weight, debye, par_c, par_a1..par_a5,
par_b1..par_b5. Source: D. Waasmaier & A. Kirfel, Acta Cryst. A51 (1995) 416.
"""

from __future__ import annotations

import csv
import os

import numpy as np

from mudlab.models.atom_type import AtomType

_LIBRARY_CSV = os.path.join(
    os.path.dirname(__file__), os.pardir, "data", "atomic_scattering_factors.csv"
)


def load_atom_type_library(path: str | None = None) -> list[AtomType]:
    """Every atom type in the bundled library (or `path`), in file order. A
    fresh AtomType per row (new uuids), so callers own the returned objects."""
    types: list[AtomType] = []
    with open(path or _LIBRARY_CSV, "r", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)  # header row
        for row in reader:
            if len(row) < 6 or not row[0].strip():
                continue
            try:
                atom_type = AtomType(name=row[1])
                atom_type.atom_nr = int(float(row[0]))
                atom_type.charge = float(row[2])
                atom_type.weight = float(row[3])
                atom_type.debye = float(row[4])
                atom_type.par_c = float(row[5])
                # Pad/truncate the coefficient arrays to length 5 (a few library
                # rows carry fewer than five terms).
                par_a = [float(x) for x in row[6:11]]
                par_b = [float(x) for x in row[11:16]]
                atom_type.par_a = np.array((par_a + [0.0] * 5)[:5])
                atom_type.par_b = np.array((par_b + [0.0] * 5)[:5])
            except ValueError:
                continue  # a malformed row - skip it, keep the rest
            types.append(atom_type)
    return types


def atom_type_library_map(path: str | None = None) -> dict:
    """`{name: AtomType}` for resolving atom references by name (e.g. a default
    component's atoms). Later names win on the rare duplicate."""
    return {atom_type.name: atom_type for atom_type in load_atom_type_library(path)}
