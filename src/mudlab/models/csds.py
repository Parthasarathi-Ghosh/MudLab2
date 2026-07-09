"""CSDS distribution model (Drits log-normal).

Ported from the old DritsCSDSDistribution (phases/models/CSDS.py). Only the
average crystallite size is stored/refinable; the alpha/beta log-normal
parameters are the fixed Drits (1997) constants, and minimum/maximum are
derived from the average. Provides the distribution array + mean via
`calculations.csds.calculate_distribution`.
"""

from __future__ import annotations

# Drits (1997) log-normal constants (the values the old __init__ applies).
DRITS_ALPHA_SCALE = 0.9485
DRITS_ALPHA_OFFSET = -0.0017
DRITS_BETA_SCALE = 0.1032
DRITS_BETA_OFFSET = 0.0034

LOG_NORMAL_MAX_CSDS_FACTOR = 2.5  # old settings.LOG_NORMAL_MAX_CSDS_FACTOR


class DritsCSDSDistribution:
    def __init__(self, average: float = 10.0) -> None:
        self.average = average
        self.alpha_scale = DRITS_ALPHA_SCALE
        self.alpha_offset = DRITS_ALPHA_OFFSET
        self.beta_scale = DRITS_BETA_SCALE
        self.beta_offset = DRITS_BETA_OFFSET

    @property
    def minimum(self) -> int:
        return 1

    @property
    def maximum(self) -> int:
        return int(LOG_NORMAL_MAX_CSDS_FACTOR * self.average)

    def distribution(self):
        """(distribution array indexed by layer count, arithmetic mean)."""
        from mudlab.calculations.csds import calculate_distribution

        return calculate_distribution(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DritsCSDSDistribution":
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        return cls(average=props.get("average", 10.0))
