"""Mixture model for the pattern-calculation engine.

Ported from the old mudlab.mixture.models.Mixture (calc subset). A mixture
is a specimen × phase-slot grid: each column is a phase slot (label +
per-slot weight fraction) and each row is a specimen (with its own scale
and background shift). A grid cell names which phase fills that slot for
that specimen - the same slot can hold a different variant per specimen
(e.g. the air-dried / glycolated / heated form of one clay).

`calculate()` turns the grid into each specimen's calculated pattern via
calculations.specimen, storing it back on the specimen so the plot draws
the red calculated curve over the experimental data.

Only the non-optimising calculation is ported here; the L-BFGS-B fraction/
scale/background refinement is the separate Refinement window family.
"""

from __future__ import annotations

import numpy as np

from mudlab.calculations.specimen import calculate_specimen_pattern


class Mixture:
    def __init__(self, name: str = "") -> None:
        self.name = name
        self.phase_labels: list[str] = []        # column labels (m slots)
        self.specimen_uuids: list[str] = []      # n specimens (rows)
        self.phase_uuids: list[list[str]] = []   # n × m phase uuid grid
        self.fractions = np.array([], dtype=float)  # m (per phase slot)
        self.scales = np.array([], dtype=float)     # n (per specimen)
        self.bgshifts = np.array([], dtype=float)   # n (per specimen)
        self.specimens: list = []                # resolved Specimen models (n)
        self.phase_matrix: list[list] = []       # resolved Phase grid (n × m)
        # Full .mud property dict kept verbatim so unmodeled fields
        # (fractions_mask, refine_method_index/options, auto_* flags, uuid)
        # survive a load/save round-trip; to_dict writes the modeled values
        # back into it.
        self.raw_properties: dict = {}

    @property
    def n(self) -> int:
        """Number of specimens (rows)."""
        return len(self.specimen_uuids)

    @property
    def m(self) -> int:
        """Number of phase slots (columns)."""
        return len(self.phase_labels)

    def calculate(self) -> None:
        """Compute and store every specimen's calculated pattern."""
        for i, specimen in enumerate(self.specimens):
            if specimen is None:
                continue
            phases = self.phase_matrix[i] if i < len(self.phase_matrix) else []
            scale = float(self.scales[i]) if i < len(self.scales) else 1.0
            bgshift = float(self.bgshifts[i]) if i < len(self.bgshifts) else 0.0
            two_theta, total = calculate_specimen_pattern(
                specimen, phases, scale, self.fractions, bgshift
            )
            specimen.set_calculated_pattern(two_theta, total)

    def current_residual(self) -> float:
        """Mean Rp of the current (un-optimised) solution against the
        experimental patterns."""
        from mudlab.calculations.mixture import get_current_residual

        return get_current_residual(self)

    def optimize(self) -> float:
        """Refine fractions / scales / background shifts to minimise the mean
        Rp residual (L-BFGS-B), then recompute the stored patterns. Returns
        the achieved residual."""
        from mudlab.calculations.mixture import optimize_mixture

        residual = optimize_mixture(self)
        self.calculate()
        return residual

    @classmethod
    def from_dict(
        cls, data: dict, phase_uuid_map: dict, specimen_uuid_map: dict
    ) -> "Mixture":
        props = data.get("properties", {})
        mix = cls(name=props.get("name", ""))
        mix.raw_properties = dict(props)
        mix.phase_labels = list(props.get("phases") or [])
        mix.specimen_uuids = list(props.get("specimen_uuids") or [])
        mix.phase_uuids = [list(row) for row in (props.get("phase_uuids") or [])]
        mix.fractions = np.asarray(props.get("fractions") or [], dtype=float)
        mix.scales = np.asarray(props.get("scales") or [], dtype=float)
        mix.bgshifts = np.asarray(props.get("bgshifts") or [], dtype=float)
        mix.specimens = [specimen_uuid_map.get(u) for u in mix.specimen_uuids]
        mix.phase_matrix = [
            [phase_uuid_map.get(u) for u in row] for row in mix.phase_uuids
        ]
        return mix

    def to_dict(self) -> dict:
        """Serialize back to a .mud mixture dict, overwriting only the modeled
        fields on top of the verbatim raw properties (so masks, refine
        options, auto_* flags and uuid survive)."""
        props = dict(self.raw_properties)
        props["name"] = self.name
        props["phases"] = list(self.phase_labels)
        props["specimen_uuids"] = list(self.specimen_uuids)
        props["phase_uuids"] = [list(row) for row in self.phase_uuids]
        props["fractions"] = [float(x) for x in self.fractions]
        props["scales"] = [float(x) for x in self.scales]
        props["bgshifts"] = [float(x) for x in self.bgshifts]
        return {"type": "Mixture", "properties": props}
