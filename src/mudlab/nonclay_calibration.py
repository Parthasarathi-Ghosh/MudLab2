"""FWHM calibration from a standard (path-2 phase B, batch 1).

Fit the single Gaussian peak width (FWHM, deg 2theta) whose *computed* standard
pattern best matches a *measured* scan of that standard - the instrumental peak
width to apply to computed NonClayPhases. A built-in Silicon standard is
provided; any ``[(d_angstrom, intensity)]`` reflection list works.

The fit is 1-D over the FWHM; at each trial the rendered standard is matched to
the measurement by a linear ``scale * render + offset`` (absorbs the intensity
scale and a flat background), and the FWHM that minimises the residual wins.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize_scalar

from mudlab.models import Goniometer
from mudlab.models.nonclay_phase import NonClayPhase
from mudlab.nonclay.structure import reflections_from_cif_text

# Silicon (diamond, Fd-3m, a = 5.4309 A) written as its 8 atoms with identity
# symmetry, so the CIF parser needs no space-group expansion.
_SILICON_CIF = """data_silicon
_cell_length_a 5.4309
_cell_length_b 5.4309
_cell_length_c 5.4309
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_space_group_symop_operation_xyz
x,y,z
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Si1 0.0 0.0 0.0
Si2 0.0 0.5 0.5
Si3 0.5 0.0 0.5
Si4 0.5 0.5 0.0
Si5 0.25 0.25 0.25
Si6 0.25 0.75 0.75
Si7 0.75 0.25 0.75
Si8 0.75 0.75 0.25
"""

_SI_CACHE: list | None = None


def silicon_reflections() -> list:
    """The built-in Silicon standard as ``[(d_angstrom, intensity)]`` (cached).
    d-spacings are wavelength-independent, so the same list serves any scan.
    Computed over a wide 2theta range so it covers low-d lines a longer-wavelength
    or high-angle scan may reach (the fit window clips to the measured range)."""
    global _SI_CACHE
    if _SI_CACHE is None:
        refl, _ox = reflections_from_cif_text(
            _SILICON_CIF, Goniometer(), tt_lo=4.0, tt_hi=155.0)
        _SI_CACHE = refl
    return list(_SI_CACHE)


@dataclass
class FwhmCalibration:
    fwhm: float               # fitted FWHM, deg 2theta
    shift: float              # fitted 2theta displacement (deg); 0 if not fitted
    scale: float              # linear scale of the rendered standard
    offset: float             # flat background
    residual: float           # ||scale*render + offset - measured|| / ||measured||
    two_theta: np.ndarray     # measured grid used for the fit (within fit_range)
    measured: np.ndarray      # measured intensities on that grid
    fitted: np.ndarray        # scale*render(fwhm) + offset (for an overlay)


def _linear_fit(rendered, measured):
    """Least-squares ``a*rendered + b ~ measured``; returns (a, b, fitted, resid)
    where resid = ||fitted - measured|| / ||measured||."""
    design = np.column_stack([rendered, np.ones_like(rendered)])
    (a, b), *_ = np.linalg.lstsq(design, measured, rcond=None)
    fitted = a * rendered + b
    denom = float(np.linalg.norm(measured)) or 1.0
    return float(a), float(b), fitted, float(np.linalg.norm(fitted - measured) / denom)


def _reflection_span(reflections, wavelength_nm, margin=1.0):
    """(lo, hi) deg 2theta covering the reflections at this wavelength."""
    lam = float(wavelength_nm) * 10.0  # nm -> Angstrom
    tts = []
    for d, _i in reflections:
        s = lam / (2.0 * d)
        if s < 1.0:
            tts.append(np.degrees(2.0 * np.arcsin(s)))
    if not tts:
        return None
    return min(tts) - margin, max(tts) + margin


def calibrate_fwhm(reflections, wavelength_nm, measured_x, measured_y,
                   bounds=(0.02, 2.0), fit_range=None, fit_shift=True,
                   shift_bounds=(-0.5, 0.5)) -> FwhmCalibration:
    """Fit the FWHM whose rendered standard best matches
    ``(measured_x, measured_y)``.

    ``fit_shift`` also fits a 2theta displacement (a specimen/goniometer zero
    shift), so it does not leak into the width - without it a shifted scan biases
    the FWHM too wide. The fit is nested 1-D (outer shift, inner FWHM), both
    bounded, with a per-trial linear scale + flat-background. ``fit_range`` =
    (lo, hi) deg 2theta limits the fit (default: the reflections' span at this
    wavelength). Returns a :class:`FwhmCalibration`."""
    x = np.asarray(measured_x, dtype=float)
    y = np.asarray(measured_y, dtype=float)
    standard = NonClayPhase()
    standard.set_reflections(reflections)

    if fit_range is None:
        span = _reflection_span(reflections, wavelength_nm)
        fit_range = span if span is not None else (float(x.min()), float(x.max()))
    lo, hi = fit_range
    win = (x >= lo) & (x <= hi)
    if int(win.sum()) < 5:                # too narrow a window: fit the whole scan
        win = np.ones_like(x, dtype=bool)
    xw, yw = x[win], y[win]

    def _best_at_shift(shift):
        # Rendering on (xw - shift) slides the computed pattern by +shift, so a
        # positive shift matches a measurement whose peaks sit high of theory.
        def objective(fwhm):
            rendered = standard.render_on_grid(xw - shift, wavelength_nm, fwhm=fwhm)
            return _linear_fit(rendered, yw)[3]
        opt = minimize_scalar(objective, bounds=bounds, method="bounded")
        return float(opt.fun), float(opt.x)

    if fit_shift:
        shift_opt = minimize_scalar(
            lambda s: _best_at_shift(s)[0], bounds=shift_bounds, method="bounded")
        shift = float(shift_opt.x)
    else:
        shift = 0.0
    _res, fwhm = _best_at_shift(shift)
    rendered = standard.render_on_grid(xw - shift, wavelength_nm, fwhm=fwhm)
    scale, offset, fitted, residual = _linear_fit(rendered, yw)
    return FwhmCalibration(fwhm, shift, scale, offset, residual, xw, yw, fitted)
