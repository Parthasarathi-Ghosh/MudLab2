"""Angle <-> d-spacing conversions, ported as-is from the old
mudlab/calculations/goniometer.py (Bragg's law; wavelengths in nm)."""

from __future__ import annotations

import numpy as np


def get_nm_from_t(theta, wavelength=0.154056, zero_for_inf=False):
    """Convert theta angles (°) to nanometer spacings."""
    return get_nm_from_2t(2.0 * theta, wavelength=wavelength, zero_for_inf=zero_for_inf)


def get_nm_from_2t(twotheta, wavelength=0.154056, zero_for_inf=False):
    """Convert 2-theta angles (°) to nanometer spacings."""
    if twotheta == 0:
        return 0.0 if zero_for_inf else 1e16
    return wavelength / (2.0 * np.sin(np.radians(twotheta / 2.0)))


def get_t_from_nm(nm, wavelength=0.154056):
    """Convert nanometer spacings to theta angles (°)."""
    return get_2t_from_nm(nm, wavelength=wavelength) / 2


def get_2t_from_nm(nm, wavelength=0.154056):
    """Convert nanometer spacings to 2-theta angles (°)."""
    twotheta = 0.0
    if nm != 0:
        twotheta = np.degrees(np.arcsin(max(-1.0, min(1.0, wavelength / (2.0 * nm))))) * 2.0
    return twotheta
