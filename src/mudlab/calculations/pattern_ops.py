"""Experimental-pattern operations (background, smooth, noise, shift, strip,
peak properties).

Ported from the old mudlab.generic.models.lines.experimental_line
(ExperimentalLine). In the old app these were *methods* on the pattern model,
mutating `data_y[:, 0]` in place under a `data_changed.hold_and_emit()`. Here
they are **pure functions**: numpy arrays in, new numpy arrays out. The model
layer (models/specimen.py) owns the mutation and the signal, so the numerics
are testable without a specimen, a goniometer or a Qt event loop.

The numerics are ported verbatim - the same window lengths, the same noise
estimate, the same displacement correction - so a pattern processed here
matches the old app point-for-point (see tools/verify_pattern_ops.py).

Two-step operations (shift, strip, peak properties) split into a *compute*
function that previews without touching the data and an *apply* function that
commits, mirroring the old setup_*/update_* -> commit split that let the plot
draw a live preview.
"""

from __future__ import annotations

from collections import namedtuple

import numpy as np
from scipy.integrate import trapezoid
from scipy.interpolate import UnivariateSpline

from mudlab.calculations.goniometer import (
    get_2t_from_nm,
    get_fixed_to_ads_correction_range,
    get_t_from_nm,
)
from mudlab.calculations.math_tools import add_noise as _add_noise
from mudlab.calculations.math_tools import smooth as _smooth

# Old settings.PATTERN_SHIFT_TYPE. "Displacement" corrects for sample-height
# displacement (the correction varies across the pattern); "Linear" subtracts a
# constant 2-theta offset. The old app ships "Displacement" and has no UI to
# change it, so it is a module constant here rather than a settings file.
PATTERN_SHIFT_TYPE = "Displacement"

# Background types (old bg_type, combo order in background.ui).
BG_LINEAR = 0
BG_PATTERN = 1

# Smoothing types (old smooth_type, combo order in smoothing.ui).
SMOOTH_BLACKMAN = 0
SMOOTH_SAVGOL = 1
SMOOTH_GAUSSIAN = 2
SMOOTH_MOVING_AVG = 3
SMOOTH_SPLINE = 4
SMOOTH_BUTTERWORTH = 5

#: Default smoothing degree per type (old setup_smooth_variables).
SMOOTH_DEFAULT_DEGREES = {
    SMOOTH_BLACKMAN: 5,
    SMOOTH_SAVGOL: 5,
    SMOOTH_GAUSSIAN: 3,
    SMOOTH_MOVING_AVG: 5,
    SMOOTH_SPLINE: 10,
    SMOOTH_BUTTERWORTH: 10,
}


# ----------------------------------------------------------------------
# Background removal
# ----------------------------------------------------------------------
def remove_background(
    y,
    bg_type: int = BG_LINEAR,
    bg_position: float = 0.0,
    bg_pattern=None,
    bg_scale: float = 0.0,
):
    """Subtract a background from the intensities (old remove_background).

    - ``BG_LINEAR``: subtract the constant ``bg_position``.
    - ``BG_PATTERN``: subtract ``bg_pattern * bg_scale + bg_position``. A
      no-op when both scale and position are zero (the old guard), and when
      no pattern was loaded.

    Returns a new array; the input is not modified.
    """
    y = np.asarray(y, dtype=float)
    bg = None
    if bg_type == BG_LINEAR:
        bg = bg_position
    elif bg_type == BG_PATTERN and bg_pattern is not None:
        if not (bg_position == 0 and bg_scale == 0):
            bg = np.asarray(bg_pattern, dtype=float) * bg_scale + bg_position
    if bg is None or y.size == 0:
        return y.copy()
    return y - bg


def find_bg_position(y) -> float:
    """The lowest intensity in the pattern - the old app's starting guess for
    a linear background (old find_bg_position)."""
    y = np.asarray(y, dtype=float)
    if y.size == 0:
        return 0.0
    return float(np.min(y))


# ----------------------------------------------------------------------
# Smoothing
# ----------------------------------------------------------------------
def smooth_data(y, smooth_type: int = SMOOTH_BLACKMAN, smooth_degree: float = 0.0):
    """Smooth the intensities (old smooth_data).

    ``smooth_degree`` <= 0 is a no-op (the old app resets the degree to 0
    after applying, so a second OK does nothing). Each type reads the degree
    differently - window half-width, Gaussian sigma, spline smoothing factor -
    exactly as the old app did.

    Returns a new array; the input is not modified.
    """
    y = np.asarray(y, dtype=float)
    if smooth_degree <= 0 or y.size == 0:
        return y.copy()

    from scipy.ndimage import gaussian_filter1d, uniform_filter1d
    from scipy.signal import butter, filtfilt, savgol_filter

    degree = int(smooth_degree)
    if smooth_type == SMOOTH_BLACKMAN:
        return _smooth(y, degree)
    if smooth_type == SMOOTH_SAVGOL:
        wl = 2 * degree + 1
        poly = min(degree, 5)
        if poly >= wl:
            poly = wl - 1
        return savgol_filter(y, window_length=wl, polyorder=poly)
    if smooth_type == SMOOTH_GAUSSIAN:
        return gaussian_filter1d(y, sigma=degree)
    if smooth_type == SMOOTH_MOVING_AVG:
        return uniform_filter1d(y, size=2 * degree + 1)
    if smooth_type == SMOOTH_SPLINE:
        x_idx = np.arange(len(y), dtype=float)
        s = float(degree) * len(y) / 100.0
        return UnivariateSpline(x_idx, y, s=s)(x_idx)
    if smooth_type == SMOOTH_BUTTERWORTH:
        wn = min(1.0 / degree, 0.99)
        b, a = butter(4, wn, btype="low")
        return filtfilt(b, a, y)
    return y.copy()


def default_smooth_degree(smooth_type: int) -> float:
    """The degree the old dialog pre-fills when the type changes."""
    return float(SMOOTH_DEFAULT_DEGREES.get(smooth_type, 5))


# ----------------------------------------------------------------------
# Noise
# ----------------------------------------------------------------------
def add_noise(y, noise_fraction: float = 0.0):
    """Add synthetic noise to the intensities (old add_noise).

    A zero/negative fraction is a no-op. Used to test how robust a refinement
    is against counting statistics.
    """
    y = np.asarray(y, dtype=float)
    if noise_fraction <= 0 or y.size == 0:
        return y.copy()
    return _add_noise(y, noise_fraction)


# ----------------------------------------------------------------------
# Divergence-slit conversion (fixed <-> automatic/ADS)
# ----------------------------------------------------------------------
def convert_slit(x, y, to_ads: bool):
    """Rescale intensities between fixed and automatic (ADS) divergence-slit
    geometry (old Specimen.convert_to_fixed / convert_to_ads).

    An automatic divergence slit opens with theta to keep the irradiated sample
    length constant, so it collects ~sin(theta) times the intensity a fixed slit
    would at the same angle. Hence fixed -> ADS multiplies by sin(theta) and
    ADS -> fixed divides by it (the correction factor is the existing
    get_fixed_to_ads_correction_range = sin(theta)).

    `x` is the 2-theta axis (degrees); `to_ads` True converts a fixed-slit
    pattern to ADS, False converts an ADS pattern to fixed slit. Returns a new y
    array (x is unchanged). Where sin(theta) == 0 (theta = 0) the point is left
    unchanged, so ADS -> fixed never divides by zero.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if y.size == 0:
        return y.copy()
    factor = get_fixed_to_ads_correction_range(np.radians(x * 0.5))  # sin(theta)
    if to_ads:
        return y * factor
    # ADS -> fixed: divide by sin(theta), leaving theta == 0 points untouched.
    result = y.copy()
    np.divide(y, factor, out=result, where=factor > 0)
    return result


# ----------------------------------------------------------------------
# Shifting
# ----------------------------------------------------------------------
def detect_shift(x, y, shift_position: float, wavelength: float) -> float:
    """The 2-theta offset between a reference reflection's expected position
    and where it actually peaks (old setup_shift_variables).

    ``shift_position`` is the reference d-spacing in nm (e.g. 0.42574 for the
    quartz 100 line); it is converted to 2-theta and the strongest point within
    +/-0.5 degrees is taken as the true position. Returns 0.0 for manual mode
    (``shift_position == 0``) or when the reference falls outside the pattern.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if shift_position == 0.0 or x.size == 0:
        return 0.0
    position = get_2t_from_nm(shift_position, wavelength=wavelength)
    if position <= 0.1:
        return 0.0
    condition = (x >= position - 0.5) & (x <= position + 0.5)
    section_x = np.extract(condition, x)
    section_y = np.extract(condition, y)
    try:
        actual_position = section_x[np.argmax(section_y)]
    except (ValueError, IndexError):
        actual_position = position
    return float(actual_position - position)


def apply_shift(
    x,
    shift_value: float,
    shift_position: float = 0.0,
    radius: float = 24.0,
    wavelength: float = 0.154056,
    shift_type: str = PATTERN_SHIFT_TYPE,
):
    """Correct the 2-theta axis by ``shift_value`` (old _apply_shift_to_array).

    "Linear" (or manual mode) subtracts the offset uniformly. "Displacement"
    models the physical cause - the sample sitting off the focusing circle -
    so the correction is largest at low angles and shrinks as 2-theta grows.

    Returns a new x array; the input is not modified.
    """
    x = np.asarray(x, dtype=float)
    if shift_type == "Linear" or shift_position == 0.0:
        return x - shift_value
    position_t = get_t_from_nm(shift_position, wavelength=wavelength)
    displacement = 0.5 * radius * shift_value / np.cos(np.radians(position_t))
    correction = 2 * displacement * np.cos(np.radians(x / 2.0)) / radius
    return x - correction


# ----------------------------------------------------------------------
# Peak stripping
# ----------------------------------------------------------------------
StripPattern = namedtuple(
    "StripPattern",
    "section_x section_y startx endx slope noise_level avg_starty avg_endy",
)


def compute_strip_pattern(x, y, startx: float, endx: float, noise_level=None):
    """Build the replacement line for stripping a peak (old
    update_strip_pattern + update_strip_pattern_noise).

    Endpoints snap to the nearest real data point; the peak is replaced by the
    straight line joining them, plus noise so the patched section does not look
    artificially clean. The noise level is estimated from the scatter within
    +/-0.1 degrees of each endpoint unless ``noise_level`` is given (the user
    can override it in the dialog).

    Returns a StripPattern, or None when the range is degenerate.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if startx == 0.0 or endx == 0.0 or x.size == 0:
        return None

    startx, endx = min(startx, endx), max(startx, endx)
    start_idx = int(np.argmin(np.abs(x - startx)))
    end_idx = int(np.argmin(np.abs(x - endx)))
    if start_idx >= end_idx:
        return None

    snapped_startx = float(x[start_idx])
    snapped_endx = float(x[end_idx])
    avg_starty = float(y[start_idx])
    avg_endy = float(y[end_idx])

    if noise_level is None:
        # Old quirk preserved: both ratios divide by avg_starty (not by their
        # own endpoint), so the estimate is scaled to the start intensity.
        condition = (x >= snapped_startx - 0.1) & (x <= snapped_startx + 0.1)
        section_start = np.extract(condition, y)
        noise_starty = 2 * np.std(section_start) / avg_starty if avg_starty != 0 else 0
        condition = (x >= snapped_endx - 0.1) & (x <= snapped_endx + 0.1)
        section_end = np.extract(condition, y)
        noise_endy = 2 * np.std(section_end) / avg_starty if avg_starty != 0 else 0
        noise_level = float((noise_starty + noise_endy) * 0.5)

    slope = (avg_starty - avg_endy) / (snapped_startx - snapped_endx)
    condition = (x >= snapped_startx) & (x <= snapped_endx)
    section_x = np.extract(condition, x)
    noise = avg_endy * 2 * (np.random.rand(*section_x.shape) - 0.5) * noise_level
    section_y = (slope * (section_x - snapped_startx) + avg_starty) + noise

    return StripPattern(
        section_x, section_y, snapped_startx, snapped_endx,
        slope, float(noise_level), avg_starty, avg_endy,
    )


def apply_strip(x, y, strip: StripPattern):
    """Replace the peak with the stripped line (old strip_peak).

    Returns a new y array; the input is not modified.
    """
    x = np.asarray(x, dtype=float)
    y = np.array(y, dtype=float)  # copy: np.put mutates
    if strip is None:
        return y
    indices = ((x >= strip.startx) & (x <= strip.endx)).nonzero()[0]
    np.put(y, indices, strip.section_y)
    return y


# ----------------------------------------------------------------------
# Peak properties (area / FWHM)
# ----------------------------------------------------------------------
PeakProperties = namedtuple(
    "PeakProperties",
    "area fwhm startx endx section_x section_y bg_curve roots root_ys",
)


def compute_peak_properties(x, y, startx: float, endx: float):
    """Integrated area and FWHM of the peak between two positions (old
    update_peak_properties).

    The endpoints snap to real data points and the line joining them is taken
    as the local background: the area is the integral above that line, and the
    FWHM comes from where a spline through the background-subtracted peak
    crosses half its maximum. A read-only measurement - it never changes the
    pattern.

    Returns a PeakProperties, or None when the range is degenerate.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if startx == 0.0 or endx == 0.0 or x.size == 0:
        return None

    startx, endx = min(startx, endx), max(startx, endx)
    start_idx = int(np.argmin(np.abs(x - startx)))
    end_idx = int(np.argmin(np.abs(x - endx)))
    if start_idx >= end_idx:
        return None

    snapped_startx = float(x[start_idx])
    snapped_endx = float(x[end_idx])
    avg_starty = float(y[start_idx])
    avg_endy = float(y[end_idx])

    bg_slope = (avg_starty - avg_endy) / (snapped_startx - snapped_endx)
    condition = (x >= snapped_startx) & (x <= snapped_endx)
    section_x = np.extract(condition, x)
    section_y = np.extract(condition, y)
    bg_curve = bg_slope * (section_x - snapped_startx) + avg_starty

    area = float(
        abs(trapezoid(section_y, x=section_x) - trapezoid(bg_curve, x=section_x))
    )

    # FWHM: spline the peak shifted down by half its height; the outermost
    # roots bracket the full width.
    fwhm_curve = section_y - bg_curve
    peak_half_max = np.max(fwhm_curve) * 0.5
    roots = np.empty(0)
    fwhm = 0.0
    try:
        spline = UnivariateSpline(section_x, fwhm_curve - peak_half_max, s=0)
        roots = spline.roots()
        if len(roots) >= 2:
            fwhm = float(np.abs(roots[0] - roots[-1]))
        root_ys = spline(roots) + peak_half_max
    except (ValueError, TypeError):
        # Too few points for a spline, or a non-monotonic section.
        root_ys = np.empty(0)

    return PeakProperties(
        area, fwhm, snapped_startx, snapped_endx,
        section_x, section_y, bg_curve, roots, root_ys,
    )
