"""AtomType model (Qt signals).

Holds the physical/chemical data for one ion (e.g. Fe2+ and Fe3+ are two
atom types), including the 5-term scattering-factor coefficients used by
`mudlab.calculations.atoms`. Property names follow the old
mudlab.atoms.models.AtomType so the .mud keys line up.
"""

from __future__ import annotations

import uuid

import numpy as np
from PySide6.QtCore import QObject, Signal

from mudlab.models.properties import Prop

# Scalar keys shared 1:1 with the .mud file (the par_a/par_b arrays are
# stored as par_a1..a5 / par_b1..b5, handled explicitly).
_SCALAR_KEYS = ("name", "atom_nr", "weight", "debye", "charge", "par_c")


class AtomType(QObject):
    data_changed = Signal()

    name = Prop("", "data_changed")
    atom_nr = Prop(0, "data_changed")
    weight = Prop(0.0, "data_changed")
    debye = Prop(0.0, "data_changed")
    charge = Prop(0.0, "data_changed")
    par_c = Prop(0.0, "data_changed")

    def __init__(self, name: str = "", parent: QObject | None = None) -> None:
        super().__init__(parent)
        if name:
            self.name = name
        self.uuid = uuid.uuid4().hex
        # Scattering-factor coefficient arrays (length 5), used directly by
        # calculations.atoms.get_atomic_scattering_factor.
        self.par_a = np.zeros(5)
        self.par_b = np.zeros(5)

    def scattering_factor(self, stl: np.ndarray) -> np.ndarray:
        """ASF over an array of 2·sin(θ)/λ values (nm⁻¹). Converts to the
        Å⁻² argument (·0.05)² the calc expects."""
        from mudlab.calculations.atoms import get_atomic_scattering_factor

        angstrom_range = (np.asarray(stl, dtype=float) * 0.05) ** 2
        return get_atomic_scattering_factor(angstrom_range, self)

    # ------------------------------------------------------------------
    # Serialization (.mud)
    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict) -> "AtomType":
        props = data.get("properties", {})
        atom = cls()
        for key in _SCALAR_KEYS:
            if key in props:
                setattr(atom, key, props[key])
        atom.par_a = np.array([props.get(f"par_a{i}", 0.0) for i in range(1, 6)])
        atom.par_b = np.array([props.get(f"par_b{i}", 0.0) for i in range(1, 6)])
        if "uuid" in props:
            atom.uuid = props["uuid"]
        return atom

    def to_dict(self) -> dict:
        props = {key: getattr(self, key) for key in _SCALAR_KEYS}
        for i in range(5):
            props[f"par_a{i + 1}"] = float(self.par_a[i])
            props[f"par_b{i + 1}"] = float(self.par_b[i])
        props["uuid"] = self.uuid
        return {"type": "AtomType", "properties": props}
