"""Per-specimen fit statistics (derived, not persisted).

Mirrors the old Statistics model (specimen/models/statistics.py): computes
the R-factors and the residual pattern from a specimen's experimental and
calculated patterns. Values are lazily computed and cached; the cache is
cleared when the specimen's data changes.

Exclusion ranges are not modeled yet, so statistics are computed over the
full overlapping pattern (old app masked out exclusion ranges via
get_exclusion_selector - add that when exclusion ranges are ported).
"""

from __future__ import annotations

import numpy as np

from mudlab.calculations import GoF, R_squared, Rp, Rpder, Rpe, Rpw, derive


class SpecimenStatistics:
    def __init__(self, specimen) -> None:
        self._specimen = specimen
        self._cache: dict | None = None

    def invalidate(self) -> None:
        self._cache = None

    @property
    def has_data(self) -> bool:
        s = self._specimen
        return (
            s.has_experimental_data
            and s.has_calculated_data
            and s.experimental_pattern[1].size == s.calculated_pattern[1].size
        )

    def _compute(self) -> dict:
        if self._cache is not None:
            return self._cache
        if not self.has_data:
            self._cache = {}
            return self._cache
        exp = self._specimen.experimental_pattern[1]
        calc = self._specimen.calculated_pattern[1]
        self._cache = {
            "points": int(exp.size),
            "R2": float(R_squared(exp, calc)),
            "Rp": float(Rp(exp, calc)),
            "Rwp": float(Rpw(exp, calc)),
            "Re": float(Rpe(exp, calc, 0)),
            "GoF": float(GoF(exp, calc)),
        }
        return self._cache

    # Individual accessors (0.0 when there is no calculated pattern).
    def _value(self, key: str) -> float:
        return self._compute().get(key, 0.0)

    @property
    def points(self) -> int:
        return int(self._compute().get("points", 0))

    @property
    def R2(self) -> float:
        return self._value("R2")

    @property
    def Rp(self) -> float:
        return self._value("Rp")

    @property
    def Rwp(self) -> float:
        return self._value("Rwp")

    @property
    def Re(self) -> float:
        return self._value("Re")

    @property
    def GoF(self) -> float:
        return self._value("GoF")

    @property
    def residual_pattern(self) -> tuple[np.ndarray, np.ndarray]:
        """(x, exp_y - calc_y) or empty arrays when there is no calc data."""
        if not self.has_data:
            return np.empty(0), np.empty(0)
        x, exp = self._specimen.experimental_pattern
        calc = self._specimen.calculated_pattern[1]
        return x, exp - calc

    def derivative_residual(self) -> tuple[np.ndarray, np.ndarray]:
        """(x, d/dx exp - d/dx calc), smoothed (old derived residual)."""
        if not self.has_data:
            return np.empty(0), np.empty(0)
        x, exp = self._specimen.experimental_pattern
        calc = self._specimen.calculated_pattern[1]
        return x, derive(exp) - derive(calc)

    def as_dict(self) -> dict:
        return dict(self._compute())
