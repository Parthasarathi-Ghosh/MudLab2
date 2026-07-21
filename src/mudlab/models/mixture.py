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

    # ------------------------------------------------------------------
    # Reference integrity (old Mixture.unset_phase / unset_specimen)
    # ------------------------------------------------------------------
    # NOTE: the grid is held twice - `phase_matrix` / `specimens` (resolved
    # objects, what the calc reads) and `phase_uuids` / `specimen_uuids` (what
    # to_dict writes). Both must be updated together or the change is lost on
    # save (see `set_phase_at` / `unset_phase`), which is why we do NOT derive
    # the uuids from the objects at save time the way the old app does: a cell
    # may legitimately be None (an emptied slot, e.g. after remove_phase) while
    # its stored uuid is cleared in step - keeping the two in sync explicitly
    # avoids blanking a live reference. (Both "Phase" and "RawPatternPhase"
    # entries are modeled and resolve into `phase_matrix`.)
    def unset_phase(self, phase) -> None:
        """Clear every grid cell holding `phase`. The slot (column) stays -
        only the cells empty, exactly as the old unset_phase did, so the
        fractions and labels keep their meaning."""
        for i, row in enumerate(self.phase_matrix):
            for j, held in enumerate(row):
                if held is phase:
                    row[j] = None
                    if i < len(self.phase_uuids) and j < len(self.phase_uuids[i]):
                        self.phase_uuids[i][j] = ""  # old app's empty cell

    def unset_specimen(self, specimen) -> None:
        """Clear every row holding `specimen` (old unset_specimen)."""
        for i, held in enumerate(self.specimens):
            if held is specimen:
                self.specimens[i] = None
                if i < len(self.specimen_uuids):
                    self.specimen_uuids[i] = ""

    def set_phase_at(self, specimen_index: int, slot_index: int, phase) -> None:
        """Assign `phase` (or None to empty the cell) to a specimen row / phase
        slot, updating BOTH the resolved grid (`phase_matrix`, what the calc
        reads) and the uuid grid (`phase_uuids`, what round-trips). The slot's
        fraction and the specimen's scale are untouched. Old app: set_phase."""
        i, j = specimen_index, slot_index
        if not (0 <= i < len(self.phase_matrix)):
            return
        if not (0 <= j < len(self.phase_matrix[i])):
            return
        self.phase_matrix[i][j] = phase
        if i < len(self.phase_uuids) and j < len(self.phase_uuids[i]):
            self.phase_uuids[i][j] = phase.uuid if phase is not None else ""

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

    def optimize(self, n_starts: int = 4) -> float:
        """Refine fractions / scales / background shifts to minimise the mean
        Rp residual (L-BFGS-B), then recompute the stored patterns. Returns
        the achieved residual.

        Uses a multi-start search (least-squares scale/bg warm start + random-
        fraction restarts) so the standalone Optimise is robust to a poor
        starting point; the first start is the current solution, so the result
        is never worse. The structural refinement inner loop calls
        `optimize_mixture` directly with the single-start fast path."""
        from mudlab.calculations.mixture import optimize_mixture

        residual = optimize_mixture(self, n_starts=n_starts)
        self.calculate()
        return residual

    def update(self) -> float:
        """Refresh this mixture (old Mixture.update): optimise when auto_run is
        set, else just re-apply the current solution. Returns the residual
        (0.0 when only applied)."""
        if bool(self.raw_properties.get("auto_run", False)):
            return self.optimize()
        self.calculate()
        return 0.0

    def refinables(self) -> list:
        """The mixture's refinable structural parameters (sigma*, CSDS mean,
        F params, component d001/delta_c), flagged or not - for the Refinement
        window's parameter tree."""
        from mudlab.calculations.refinement import enumerate_refinables

        return enumerate_refinables(self)

    def refine(self, method_index: int = 0, options: dict | None = None,
               stop=None, on_progress=None) -> float:
        """Refine the flagged structural parameters with the chosen SciPy
        method (0 = L-BFGS-B, 1 = Basin Hopping), each trial inner-fitting
        fractions/scales/background. `stop` is an optional no-arg callable
        returning True to cancel a long run; `on_progress(n, best)` reports
        live progress. Recomputes the patterns and returns the best residual.
        The Refinement window instead calls calculations.refinement.
        refine_mixture directly to get the Refiner (for its Initial/Best/Last
        buttons) and to keep the recompute on the GUI thread."""
        from mudlab.calculations.refinement import refine_mixture

        refiner = refine_mixture(
            self, method_index, options, stop=stop, on_progress=on_progress
        )
        self.calculate()
        return float(refiner.best_residual) if refiner.best_residual is not None else 0.0

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
