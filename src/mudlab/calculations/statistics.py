"""XRD profile-fit R-factors, ported as-is from the old
mudlab/calculations/statistics.py.

All functions take experimental and calculated intensity arrays (1D, the
y-values on a shared x-grid) and return the standard clay-XRD goodness
statistics. Ported verbatim so results match the original app.
"""

from __future__ import annotations

from math import sqrt

import numpy as np

from mudlab.calculations.math_tools import smooth


def R_squared(exp: np.ndarray, calc: np.ndarray, *args) -> float:
    """Coefficient of determination (R²)."""
    avg = np.sum(exp) / exp.size
    sserr = np.sum((exp - calc) ** 2)
    sstot = np.sum((exp - avg) ** 2)
    return 1 - (sserr / sstot)


def Rp(exp: np.ndarray, calc: np.ndarray, *args) -> float:
    """Pattern R factor (Rp), in percent."""
    return np.sum(np.abs(exp - calc)) / np.sum(np.abs(exp)) * 100


def smooth_pattern(pattern: np.ndarray) -> np.ndarray:
    return smooth(pattern, 15)


def derive(pattern: np.ndarray) -> np.ndarray:
    """First-derivative pattern (smoothed first, to tame noise)."""
    return np.gradient(smooth_pattern(pattern))


def Rpder(exp: np.ndarray, calc: np.ndarray) -> float:
    """Derived-pattern R factor (Rp')."""
    return Rp(derive(exp), derive(calc))


def Rpw(exp: np.ndarray, calc: np.ndarray) -> float:
    """Weighted pattern R factor (Rwp), in percent. Weights w = 1/Iobs.

    Rwp = sqrt( Sum[w * (obs - calc)²] / Sum[w * obs²] )
    """
    sm1 = 0.0
    sm2 = 0.0
    for i in range(exp.size):
        # Guard the 1/Iobs weight (old code divided then filtered the inf;
        # skipping Iobs==0 up front is bit-identical and avoids the warning).
        if exp[i] == 0:
            continue
        t = (exp[i] - calc[i]) ** 2 / exp[i]
        if not (np.isnan(t) or np.isinf(t)):
            sm1 += t
            sm2 += abs(exp[i])
    try:
        return sqrt(sm1 / sm2) * 100
    except (ZeroDivisionError, ValueError):
        return 0.0


def Rpe(exp: np.ndarray, calc: np.ndarray, num_params: int) -> float:
    """Expected pattern R factor (Re), in percent.

    Re = sqrt( (Points - Params) / Sum[w * obs²] )
    """
    num_points = exp.size
    return np.sqrt((num_points - num_params) / np.sum(exp ** 2)) * 100


def GoF(exp: np.ndarray, calc: np.ndarray, num_params: int = 0) -> float:
    """Goodness of Fit (chi, i.e. sqrt of reduced chi-squared).

    GoF = sqrt( Sum[w * (obs - calc)²] / (N - P) ),  w = 1/Iobs.
    GoF == 1 -> residuals at the Poisson noise level (ideal fit).
    num_params defaults to 0 (parameter-free per-specimen indicator).
    """
    num_points = exp.size
    dof = num_points - num_params
    if dof <= 0:
        return 0.0
    sm_num = 0.0
    for i in range(exp.size):
        if exp[i] > 0:
            t = (exp[i] - calc[i]) ** 2 / exp[i]
            if not (np.isnan(t) or np.isinf(t)):
                sm_num += t
    try:
        return sqrt(sm_num / dof)
    except (ZeroDivisionError, ValueError):
        return 0.0
