"""Component (clay layer) structure factors, ported as-is from the old
mudlab/calculations/components.py.

A component sums the structure factors of its layer and interlayer atoms
(see calculations.atoms.get_structure_factor) and carries the phase
difference term for its d-spacing.
"""

from __future__ import annotations

from itertools import chain
from math import pi

import numpy as np

from mudlab.calculations.atoms import get_structure_factor


def calculate_z(default_z, lattice_d, z_factor):
    return lattice_d + z_factor * (default_z - lattice_d)


def get_factors(range_stl, component):
    r"""Structure factor and phase difference for a component over an array
    of ``2·sin(θ)/λ`` values (nm⁻¹).

    Interlayer atoms have their z recalculated from the component's actual
    vs default d-spacing (``z_factor``). The phase difference is
    ψ = exp(2π·stl·(d001·i − π·δd001·stl)).
    """
    z_factor = (component.d001 - component.lattice_d) / (
        component.default_c - component.lattice_d
    )

    num_layer_atoms = len(component.layer_atoms)

    sf_tot = 0.0 + 0.0j
    for i, atom in enumerate(chain(component.layer_atoms, component.interlayer_atoms)):
        atom.z = atom.default_z
        if i >= num_layer_atoms:
            atom.z = calculate_z(atom.z, component.lattice_d, z_factor)
        sf_tot += get_structure_factor(range_stl, atom)

    phi_tot = np.exp(
        2.0 * pi * range_stl * (component.d001 * 1j - pi * component.delta_c * range_stl)
    )
    return sf_tot, phi_tot
