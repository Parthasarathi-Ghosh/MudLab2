"""Specimen intensity calculations, ported as-is from the old
mudlab/calculations/specimen.py.

Turns a set of phase intensities into a specimen's calculated pattern:

- `calculate_phase_intensities` evaluates each phase over the specimen's
  2θ range (via calculations.phases.get_intensity), applies the machine
  correction range and spreads each phase over the goniometer's emission
  spectrum (wavelength distribution).
- `calculate_scaled_intensities` combines those per-phase intensities with
  the mixture's phase fractions, the specimen scale and the background
  shift into the total calculated intensity.

The old code carried these on a SpecimenData object; here they take plain
arrays/models so the Mixture model (models.mixture) can drive them.
"""

from __future__ import annotations

import numpy as np
from scipy.interpolate import interp1d

from mudlab.calculations.goniometer import get_machine_correction_range
from mudlab.calculations.phases import get_intensity


def calculate_phase_intensities(
    range_theta,
    wavelength,
    wavelength_distribution,
    soller1,
    soller2,
    mcr_2theta,
    correction_range,
    phases,
):
    """Per-phase corrected intensities over ``range_theta`` (radians).

    ``phases`` is the list of phases assigned to this specimen (one per
    mixture phase slot; ``None`` slots yield a zero pattern). Returns an
    array of shape ``(num_phases, num_observations)``.
    """
    range_stl = 2.0 * np.sin(range_theta) / wavelength

    def interpolate_wavelength(intensity, new_wavelength, fraction):
        new_theta = np.arcsin(range_stl * new_wavelength * 0.5)
        f = interp1d(new_theta, intensity * fraction, bounds_error=False, fill_value=0.0)
        return f(range_theta)

    def apply_wavelength_distribution(intensity):
        # Faithful port of the old code's `I += interpolate_wavelength(I, ...)`:
        # each emission line ADDS a wavelength-shifted copy on top of the
        # running intensity. Gotcha: a single-line spectrum ([[wl, 1.0]], the
        # usual case) shifts by zero and so DOUBLES the intensity - that
        # constant factor is absorbed by the fitted specimen `scale`, so it is
        # correct-to-port but do not be surprised the total is ~2x the raw
        # phase intensity.
        for new_wavelength, fraction in wavelength_distribution:
            intensity = intensity + interpolate_wavelength(
                intensity, new_wavelength, fraction
            )
        return intensity

    intensities = []
    for phase in phases:
        if phase is not None:
            correction = correction_range if phase.apply_correction else 1.0
            intensity = get_intensity(
                range_theta, range_stl, soller1, soller2, mcr_2theta, phase
            ) * correction
            intensities.append(apply_wavelength_distribution(intensity))
        else:
            intensities.append(np.zeros_like(range_stl))

    return np.array(intensities, dtype=np.float64)


def calculate_scaled_intensities(
    phase_intensities, correction_range, scale, fractions, bgshift
):
    """Combine per-phase intensities with the phase fractions, specimen scale
    and background shift into (total, scaled_phase_intensities, background)."""
    fractions = np.asanyarray(fractions, dtype=float)
    background_intensity = bgshift * correction_range
    scaled_phase_intensities = (
        fractions * phase_intensities.transpose()
    ).transpose() * scale
    total_intensity = np.sum(scaled_phase_intensities, axis=0) + background_intensity
    return total_intensity, scaled_phase_intensities, background_intensity


def calculate_specimen_pattern(specimen, phases, scale, fractions, bgshift,
                               return_phase_patterns=False):
    """Convenience wrapper: compute a specimen's calculated pattern from its
    assigned ``phases`` (one per mixture phase slot), ``scale``, phase
    ``fractions`` and ``bgshift``. Returns ``(two_theta, total_intensity)``.

    With ``return_phase_patterns=True`` also returns a third element: a list of
    ``(phase, scaled_intensity)`` for each non-empty slot - the individual
    phase contributions that sum (with the background) to the total, for the
    per-phase plot overlay.

    The 2θ grid follows the experimental pattern when present (so the
    calculated curve overlays it point-for-point), else the goniometer's
    default min→max→steps range.
    """
    gonio = specimen.goniometer
    exp_x, _ = specimen.experimental_pattern
    if exp_x.size > 1:
        two_theta = exp_x
    else:
        two_theta = np.linspace(gonio.min_2theta, gonio.max_2theta, int(gonio.steps))
    range_theta = np.radians(two_theta * 0.5)

    correction_range = get_machine_correction_range(gonio, range_theta)
    phase_intensities = calculate_phase_intensities(
        range_theta,
        gonio.wavelength,
        gonio.wavelength_distribution,
        gonio.soller1,
        gonio.soller2,
        gonio.mcr_2theta,
        correction_range,
        phases,
    )
    total_intensity, scaled_phase_intensities, _ = calculate_scaled_intensities(
        phase_intensities, correction_range, scale, fractions, bgshift
    )
    if return_phase_patterns:
        # Row i of the scaled intensities is slot i; keep only the filled slots.
        phase_patterns = [
            (phase, scaled_phase_intensities[i])
            for i, phase in enumerate(phases) if phase is not None
        ]
        return two_theta, total_intensity, phase_patterns
    return two_theta, total_intensity
