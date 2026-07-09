"""Analytical routines ported as-is from the old mudlab.calculations."""

from mudlab.calculations.goniometer import (
    get_2t_from_nm,
    get_nm_from_2t,
    get_nm_from_t,
    get_t_from_nm,
)
from mudlab.calculations.statistics import (
    GoF,
    R_squared,
    Rp,
    Rpder,
    Rpe,
    Rpw,
    derive,
)

__all__ = [
    "get_2t_from_nm", "get_nm_from_2t", "get_nm_from_t", "get_t_from_nm",
    "GoF", "R_squared", "Rp", "Rpder", "Rpe", "Rpw", "derive",
]
