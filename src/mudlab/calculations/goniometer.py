"""Goniometer angle conversions and intensity corrections, ported as-is
from the old mudlab/calculations/goniometer.py.

Angle helpers use Bragg's law (wavelengths in nm). The correction helpers
(Lorentz-polarisation factor, machine correction range) take theta angles
in RADIANS as the old code did.
"""

from __future__ import annotations

from math import radians, sqrt, tan

import numpy as np
from scipy.special import erf

from mudlab.calculations.math_tools import sqrt2pi, sqrt8


# ----------------------------------------------------------------------
# Lorentz-polarisation factor (Soller-slit S/T terms)
# ----------------------------------------------------------------------
def get_S(soller1, soller2):
    _S = sqrt((soller1 * 0.5) ** 2 + (soller2 * 0.5) ** 2)
    _S1S2 = soller1 * soller2
    return _S, _S1S2


def get_T(range_theta, sigma_star, soller1, soller2):
    sigma_star = float(max(sigma_star, 1e-18))
    S, _ = get_S(soller1, soller2)
    range_st = np.sin(range_theta)
    Q = S / (sqrt8 * range_st * sigma_star)
    return (
        erf(Q) * sqrt2pi / (2.0 * sigma_star * S)
        - 2.0 * range_st * (1.0 - np.exp(-(Q ** 2.0))) / (S ** 2.0)
    )


def get_lorentz_polarisation_factor(range_theta, sigma_star, soller1, soller2, mcr_2theta):
    """Lorentz-polarisation factor for the given sigma-star, Soller slits,
    monochromator Bragg angle and theta range (radians)."""
    T = get_T(range_theta, sigma_star, soller1, soller2)
    pol = np.cos(np.radians(mcr_2theta)) ** 2
    return T * (1.0 + pol * (np.cos(2.0 * range_theta) ** 2)) / np.sin(range_theta)


# ----------------------------------------------------------------------
# Machine correction range (auto-divergence, absorption, sample length)
# ----------------------------------------------------------------------
def get_fixed_to_ads_correction_range(range_theta, goniometer=None):
    return np.sin(range_theta)


def get_machine_correction_range(goniometer, range_theta):
    """Intensity correction factor over a theta range (radians) for the
    goniometer's slit mode, sample absorption and sample length."""
    range_st = np.sin(range_theta)
    correction_range = np.ones_like(range_theta)

    # Automatic divergence slits:
    if goniometer.divergence_mode == "AUTOMATIC":
        correction_range = correction_range * get_fixed_to_ads_correction_range(
            range_theta, goniometer
        )
    # Sample absorption:
    if goniometer.has_absorption_correction:
        absorption = goniometer.absorption * goniometer.sample_surf_density * 1e-3
        if absorption > 0.0:
            correction_range = correction_range * np.minimum(
                1.0 - np.exp(-2.0 * absorption / range_st), 1.0
            )
    # Sample length (fixed slits only):
    if goniometer.divergence_mode == "FIXED" and goniometer.divergence > 0:
        l_rta = goniometer.sample_length / (
            goniometer.radius * tan(radians(goniometer.divergence))
        )
        correction_range = correction_range * np.minimum(range_st * l_rta, 1)
    return correction_range


# ----------------------------------------------------------------------
# Angle <-> d-spacing conversions (Bragg's law; wavelengths in nm)
# ----------------------------------------------------------------------
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
