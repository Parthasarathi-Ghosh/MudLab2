"""FWHM calibration from a standard (path-2 phase B, batch 1).

Fit the single Gaussian peak width (FWHM, deg 2theta) whose *computed* standard
pattern best matches a *measured* scan of that standard - the instrumental peak
width to apply to computed NonClayPhases. A built-in Silicon standard is
provided; any ``[(d_angstrom, intensity)]`` reflection list works.

The fit is 1-D over the FWHM (nested inside a 1-D search for the 2theta
displacement); at each trial the rendered standard is matched to the measurement
by a linear ``scale * render + offset`` (absorbs the intensity scale and a flat
background), and the FWHM that minimises the residual wins. An angle-dependent
Caglioti ``(U, V, W)`` width can be fitted instead (``caglioti=True``), seeded
from that constant fit.
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
    fwhm: float               # fitted FWHM, deg 2theta (for Caglioti: at a mid angle)
    shift: float              # fitted 2theta displacement (deg); 0 if not fitted
    scale: float              # linear scale of the rendered standard
    offset: float             # flat background
    residual: float           # ||scale*render + offset - measured|| / ||measured||
    two_theta: np.ndarray     # measured grid used for the fit (within fit_range)
    measured: np.ndarray      # measured intensities on that grid
    fitted: np.ndarray        # scale*render + offset (for an overlay)
    caglioti: tuple | None = None  # (U, V, W) when angle-dependent width was fitted


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
                   shift_bounds=(-0.5, 0.5), caglioti=False) -> FwhmCalibration:
    """Fit the width whose rendered standard best matches
    ``(measured_x, measured_y)``.

    ``fit_shift`` also fits a 2theta displacement (a specimen/goniometer zero
    shift), so it does not leak into the width - without it a shifted scan biases
    the width too wide. With ``caglioti=False`` (default) a single constant FWHM
    is fitted (nested 1-D: outer shift, inner FWHM). With ``caglioti=True`` the
    constant fit still runs first and then seeds an angle-dependent Caglioti
    ``(U, V, W)`` fit (FWHM(theta)^2 = U*tan^2 + V*tan + W); the result's
    ``.caglioti`` carries it and ``.fwhm`` is the width at a mid angle (for
    display). Each trial does a linear scale + flat-background fit.

    ``bounds`` is the allowed FWHM range in both modes - for Caglioti the width
    must stay inside it across the whole fit window, which is what keeps the
    peaks physical. ``fit_range`` = (lo, hi) deg 2theta limits the fit (default:
    the reflections' span at this wavelength)."""
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
    constant = FwhmCalibration(fwhm, shift, scale, offset, residual, xw, yw, fitted)
    if caglioti:
        return _calibrate_caglioti(standard, wavelength_nm, xw, yw, constant,
                                   bounds, shift_bounds, fit_shift)
    return constant


def _calibrate_caglioti(standard, wavelength_nm, xw, yw, constant,
                        bounds, shift_bounds, fit_shift):
    """Fit Caglioti (U, V, W) (+ a 2theta shift) for the angle-dependent width,
    WARM-STARTED from the constant-FWHM fit.

    The start matters: this is a Nelder-Mead search over a residual that is
    multi-modal in the shift (neighbouring reflections give their own minima),
    and NM's default initial simplex steps the shift by 0.00025 deg - far less
    than a peak width - so a cold start at shift 0 silently converged to a
    neighbouring minimum whenever the standard scan was displaced (a 0.08 deg
    displacement returned a width wrong by 0.12 deg; 0.30 deg ran to the shift
    bound and returned nonsense). The constant fit finds the displacement
    robustly (bounded 1-D search), so starting from its (FWHM, shift) puts NM in
    the right basin. The constant fit is also the fallback: a Caglioti result
    that does not beat it is replaced by its equivalent (0, 0, FWHM^2), so
    "angle-dependent" can never come out worse than "constant"."""
    from scipy.optimize import minimize

    lo_w, hi_w = float(bounds[0]), float(bounds[1])
    tan_half = np.tan(np.radians(np.asarray(xw, dtype=float) * 0.5))

    def _params(vec):
        return (vec[0], vec[1], vec[2], float(vec[3]) if fit_shift else 0.0)

    def objective(vec):
        u, v, w, shift = _params(vec)
        # The width must stay inside `bounds` across the whole fit window:
        # without this the fit can drive it to the render's 1e-3 deg floor
        # (peaks thinner than the step, matching nothing) and call that a fit.
        squared = u * tan_half * tan_half + v * tan_half + w
        if squared.min() <= lo_w * lo_w or squared.max() >= hi_w * hi_w:
            return 1e9
        if not (shift_bounds[0] <= shift <= shift_bounds[1]):
            return 1e9
        rendered = standard.render_on_grid(
            xw - shift, wavelength_nm, caglioti=(u, v, w))
        return _linear_fit(rendered, yw)[3]

    start = [0.0, 0.0, constant.fwhm ** 2]
    if fit_shift:
        start.append(constant.shift)
    opt = minimize(objective, start, method="Nelder-Mead",
                   options={"xatol": 1e-5, "fatol": 1e-8, "maxiter": 4000})
    u, v, w, shift = _params([float(t) for t in opt.x])
    if float(opt.fun) > constant.residual:
        # No better than one constant width: report that, as a Caglioti triple.
        u, v, w, shift = 0.0, 0.0, constant.fwhm ** 2, constant.shift
    w = max(1e-6, w)
    cag = (u, v, w)
    rendered = standard.render_on_grid(xw - shift, wavelength_nm, caglioti=cag)
    scale, offset, fitted, residual = _linear_fit(rendered, yw)
    mid_tan = np.tan(np.radians(float(np.median(xw)) * 0.5))
    fwhm_mid = float(np.sqrt(max(1e-6, u * mid_tan * mid_tan + v * mid_tan + w)))
    return FwhmCalibration(fwhm_mid, shift, scale, offset, residual, xw, yw, fitted, cag)
