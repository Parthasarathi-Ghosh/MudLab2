"""Atomic scattering and structure factors, ported as-is from the old
mudlab/calculations/atoms.py.

The atom-type argument must expose `par_a` / `par_b` (length-5 numpy
arrays), `par_c` and `debye` (floats) - the AtomType model provides these
directly.
"""

from __future__ import annotations

import logging
from math import pi

import numpy as np

logger = logging.getLogger(__name__)


def get_atomic_scattering_factor(angstrom_range, atom_type):
    r"""Atomic scattering factor for an array of ``(2·sin(θ)/λ)²`` values
    (Å⁻² units) and an atom type.

    ASF = [ c + Σᵢ aᵢ·exp(−bᵢ·(2·sinθ/λ)²) ] · exp(−debye·(2·sinθ/λ)²)
    """
    if atom_type is not None:
        asf = (
            np.sum(
                atom_type.par_a * np.exp(-atom_type.par_b * angstrom_range[..., np.newaxis]),
                axis=1,
            )
            + atom_type.par_c
        )
        asf = asf * np.exp(-atom_type.debye * angstrom_range)
        return asf
    logger.debug("get_atomic_scattering_factor: 'None found!'")
    return np.zeros_like(angstrom_range)


def get_structure_factor(range_stl, atom):
    r"""Structure factor for an array of ``2·sin(θ)/λ`` values (nm⁻¹) and an
    atom (with ``atom_type``, projected atom count ``pn`` and z-coordinate).

    SF = ASF · pn · exp(2·π·z·i·(2·sinθ/λ))
    """
    if atom is not None and atom.atom_type is not None:
        angstrom_range = (range_stl * 0.05) ** 2
        asf = get_atomic_scattering_factor(angstrom_range, atom.atom_type)
        return asf * atom.pn * np.exp(2 * pi * atom.z * range_stl * 1j)
    logger.debug("get_structure_factor: 'None found!'")
    return np.zeros_like(range_stl)
