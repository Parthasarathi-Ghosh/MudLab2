"""Specimen model (Qt signals).

Property names follow the old mudlab.specimen.models.Specimen so the port
greps cleanly; storage and change notification are pure Qt. Signals mirror
the old semantics: data_changed for pattern data, visuals_changed for
display switches and labels.
"""

from __future__ import annotations

import json
import uuid as _uuid
from math import log

import numpy as np
from PySide6.QtCore import QObject, Signal

from mudlab.calculations import get_nm_from_2t
from mudlab.models.goniometer import Goniometer
from mudlab.models.properties import Prop

DEFAULT_WAVELENGTH = 0.154056  # nm, CuKα1 (old settings default)


def _peak_label(two_theta: float, wavelength: float) -> str:
    """Auto-peak marker label = the d-spacing (nm) at `two_theta`, formatted
    with a decimal count that grows for finer spacings (old auto_add_peaks:
    ``"%%.%df" % (3 + min(int(log(nm, 10)), 0)) % nm``). Clamped to >=0
    decimals so a pathological sub-angstrom spacing cannot raise."""
    nm = get_nm_from_2t(two_theta, wavelength) if two_theta != 0 else 0.0
    if nm <= 0:
        return "0"
    decimals = max(0, 3 + min(int(log(nm, 10)), 0))
    return "%.*f" % (decimals, nm)


class Specimen(QObject):
    data_changed = Signal()
    visuals_changed = Signal()

    name = Prop("", "visuals_changed")
    sample_name = Prop("", "visuals_changed")
    source = Prop("", "data_changed")

    display_experimental = Prop(True, "visuals_changed")
    display_calculated = Prop(True, "visuals_changed")
    display_phases = Prop(False, "visuals_changed")
    display_derivatives = Prop(False, "visuals_changed")
    display_residuals = Prop(False, "visuals_changed")
    display_stats_in_lbl = Prop(False, "visuals_changed")
    display_vshift = Prop(0.0, "visuals_changed")
    display_vscale = Prop(1.0, "visuals_changed")
    display_residual_scale = Prop(1.0, "visuals_changed")

    def __init__(self, name: str = "", parent: QObject | None = None) -> None:
        super().__init__(parent)
        if name:
            self.name = name
        self.uuid = _uuid.uuid4().hex  # overwritten from the .mud on load
        self._exp_x = np.empty(0)
        self._exp_y = np.empty(0)
        self._calc_x = np.empty(0)
        self._calc_y = np.empty(0)
        self._markers: list = []
        # Exclusion ranges: (from_2theta, to_2theta) pairs the fit / stats
        # ignore (old exclusion_ranges XYListStore). Set from the .mud on load.
        self._exclusion_ranges: list[tuple[float, float]] = []
        # Every specimen owns a goniometer (default CuKα Bragg-Brentano); a .mud
        # load overwrites it from the file. A freshly imported / added specimen
        # keeps this default so its Goniometer tab is editable, not greyed out.
        self.goniometer = Goniometer()
        self.project = None  # set by Project.add_specimen
        # Transient reference-mineral overlay: [(2theta, rel_intensity), ...] or
        # None (Match Minerals preview). Never serialized.
        self.mineral_preview = None
        # Per-phase calculated contributions: [(phase, intensity), ...] on the
        # calculated x-grid, set alongside the total by a mixture recompute (for
        # the per-phase plot overlay). Transient; never serialized.
        self.phase_patterns = None
        # Verbatim .mud specimen properties (goniometer, ...) so unmodeled
        # parts survive load/save round-trips.
        self.raw_properties: dict = {}
        # Derived fit statistics (lazy; cache cleared on data_changed).
        self._statistics = None
        self.data_changed.connect(self._invalidate_statistics)

    @property
    def statistics(self):
        """Per-specimen fit statistics (old specimen.statistics)."""
        if self._statistics is None:
            from mudlab.models.statistics import SpecimenStatistics
            self._statistics = SpecimenStatistics(self)
        return self._statistics

    def _invalidate_statistics(self) -> None:
        if self._statistics is not None:
            self._statistics.invalidate()

    # ------------------------------------------------------------------
    # Exclusion ranges (2theta regions the fit / R-factors ignore)
    # ------------------------------------------------------------------
    @property
    def exclusion_ranges(self) -> tuple[tuple[float, float], ...]:
        return tuple(self._exclusion_ranges)

    def set_exclusion_ranges(self, ranges) -> None:
        """Replace the exclusion ranges with (from, to) 2theta pairs and emit
        data_changed (so the stats cache + plot refresh)."""
        self._exclusion_ranges = [
            (float(a), float(b)) for a, b in (ranges or [])
        ]
        self.data_changed.emit()

    def exclusion_selector(self, two_theta) -> np.ndarray:
        """Boolean mask over `two_theta` (degrees) that is False inside any
        exclusion range (old get_exclusion_selector). All-True with no ranges,
        so the fit/stats are unchanged until a range is added."""
        x = np.asarray(two_theta, dtype=float)
        selector = np.ones(x.shape, dtype=bool)
        for a, b in self._exclusion_ranges:
            lo, hi = (a, b) if a <= b else (b, a)
            selector &= ~((x >= lo) & (x <= hi))
        return selector

    # ------------------------------------------------------------------
    # Markers
    # ------------------------------------------------------------------
    @property
    def markers(self) -> tuple:
        return tuple(self._markers)

    def add_marker(self, marker) -> "object":
        marker._specimen = self
        marker.setParent(self)
        marker.visuals_changed.connect(self.visuals_changed)
        self._markers.append(marker)
        self.visuals_changed.emit()
        return marker

    def remove_marker(self, marker) -> None:
        if marker in self._markers:
            marker.visuals_changed.disconnect(self.visuals_changed)
            self._markers.remove(marker)
            marker._specimen = None
            marker.setParent(None)
            marker.deleteLater()
            self.visuals_changed.emit()

    def clear_markers(self) -> None:
        """Remove every marker in one batch (old Specimen.clear_markers)."""
        if not self._markers:
            return
        for marker in list(self._markers):
            marker.visuals_changed.disconnect(self.visuals_changed)
            marker._specimen = None
            marker.setParent(None)
            marker.deleteLater()
        self._markers.clear()
        self.visuals_changed.emit()

    def set_mineral_preview(self, peaks) -> None:
        """Set the reference-mineral peak overlay - a list of ``(2theta,
        rel_intensity)`` (or None / empty to clear) - and emit visuals_changed
        so the plot redraws. Transient (Match Minerals preview); never saved."""
        self.mineral_preview = list(peaks) if peaks else None
        self.visuals_changed.emit()

    def auto_add_peaks(
        self, threshold, pattern="exp", algorithm="threshold", min_distance=0.1
    ):
        """Detect peaks and add a Marker at each, labelled with its d-spacing.

        Ported from the old Specimen.auto_add_peaks: the classic algorithm uses
        the billauer detector at `threshold`; the prominence algorithm uses
        scipy with `min_distance` (°2θ) converted to samples. `pattern` selects
        the experimental ("exp") or calculated ("calc") curve, which also sets
        the new markers' base (1 vs 2). Peaks coinciding with an existing marker
        position are skipped. Returns the list of markers created.
        """
        from mudlab.calculations import peak_detection as pd
        from mudlab.models.marker import Marker

        if pattern == "calc":
            data_x, data_y = self._calc_x, self._calc_y
            base = 2
        else:
            data_x, data_y = self._exp_x, self._exp_y
            base = 1
        if data_y.size < 2:
            return []

        if algorithm == "prominence":
            span = data_x[-1] - data_x[0]
            resolution = (len(data_x) - 1) / span if span else 1.0
            min_dist_samples = max(1, int(min_distance * resolution))
            maxtab = pd.scipy_peakdetect(
                data_y, data_x,
                min_prominence=threshold, min_distance_samples=min_dist_samples,
            )
        else:
            maxtab, _ = pd.peakdetect(data_y, data_x, 5, threshold)

        existing = {m.position for m in self._markers}
        added = []
        self.blockSignals(True)
        try:
            for x, _y in maxtab:
                if x in existing:
                    continue
                marker = Marker(label=_peak_label(x, self.wavelength), position=x)
                marker.base = base
                self.add_marker(marker)  # emit suppressed while signals blocked
                added.append(marker)
        finally:
            self.blockSignals(False)
        if added:
            self.visuals_changed.emit()
        return added

    @property
    def wavelength(self) -> float:
        """Dominant X-ray wavelength in nm (from the goniometer)."""
        if self.goniometer is not None:
            return self.goniometer.wavelength
        return DEFAULT_WAVELENGTH

    # ------------------------------------------------------------------
    # Pattern data (old: experimental_pattern / calculated_pattern models)
    # ------------------------------------------------------------------
    @property
    def experimental_pattern(self) -> tuple[np.ndarray, np.ndarray]:
        return self._exp_x, self._exp_y

    @property
    def has_experimental_data(self) -> bool:
        return self._exp_x.size > 1

    def set_experimental_pattern(self, x, y) -> None:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if x.shape != y.shape:
            raise ValueError("x and y must have the same length")
        self._exp_x, self._exp_y = x, y
        self.data_changed.emit()

    @property
    def calculated_pattern(self) -> tuple[np.ndarray, np.ndarray]:
        return self._calc_x, self._calc_y

    @property
    def has_calculated_data(self) -> bool:
        return self._calc_x.size > 1

    def set_calculated_pattern(self, x, y, phase_patterns=None) -> None:
        """Store the calculated total (and, when a mixture recompute provides
        them, the per-phase contributions [(phase, intensity), ...] on the same
        x-grid for the per-phase overlay). A set without `phase_patterns` clears
        any stale ones - they always travel with the total they belong to."""
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if x.shape != y.shape:
            raise ValueError("x and y must have the same length")
        self._calc_x, self._calc_y = x, y
        self.phase_patterns = list(phase_patterns) if phase_patterns else None
        self.data_changed.emit()

    # ------------------------------------------------------------------
    # Pattern operations (old ExperimentalLine methods; numerics live in
    # calculations/pattern_ops.py). Each mutates the experimental pattern in
    # place and emits data_changed once, so the plot and the fit statistics
    # refresh. All are destructive - the old app has no undo either.
    # ------------------------------------------------------------------
    def remove_background(
        self, bg_type=0, bg_position=0.0, bg_pattern=None, bg_scale=0.0
    ) -> None:
        from mudlab.calculations import pattern_ops

        self._exp_y = pattern_ops.remove_background(
            self._exp_y, bg_type, bg_position, bg_pattern, bg_scale
        )
        self.data_changed.emit()

    def smooth_data(self, smooth_type=0, smooth_degree=0.0) -> None:
        from mudlab.calculations import pattern_ops

        self._exp_y = pattern_ops.smooth_data(self._exp_y, smooth_type, smooth_degree)
        self.data_changed.emit()

    def add_noise(self, noise_fraction=0.0) -> None:
        from mudlab.calculations import pattern_ops

        self._exp_y = pattern_ops.add_noise(self._exp_y, noise_fraction)
        self.data_changed.emit()

    def convert_to_fixed(self) -> None:
        """Rescale the experimental pattern from automatic (ADS) to fixed-slit
        divergence geometry in place (old Specimen.convert_to_fixed): divides by
        sin(theta). Does not touch the goniometer's divergence mode."""
        from mudlab.calculations import pattern_ops

        self._exp_y = pattern_ops.convert_slit(self._exp_x, self._exp_y, to_ads=False)
        self.data_changed.emit()

    def convert_to_ads(self) -> None:
        """Rescale the experimental pattern from fixed-slit to automatic (ADS)
        divergence geometry in place (old Specimen.convert_to_ads): multiplies by
        sin(theta). Does not touch the goniometer's divergence mode."""
        from mudlab.calculations import pattern_ops

        self._exp_y = pattern_ops.convert_slit(self._exp_x, self._exp_y, to_ads=True)
        self.data_changed.emit()

    def detect_shift(self, shift_position: float) -> float:
        """The offset of a reference reflection from its expected position
        (a measurement; nothing is changed)."""
        from mudlab.calculations import pattern_ops

        return pattern_ops.detect_shift(
            self._exp_x, self._exp_y, shift_position, self.wavelength
        )

    def apply_shift(self, shift_value: float, shift_position: float = 0.0) -> None:
        """Correct the 2-theta axis by `shift_value`.

        In Linear mode the whole axis moves by a constant, so the markers move
        with it to stay on their reflections (old commit_shift). The
        Displacement correction is angle-dependent, so the old app leaves the
        markers alone there.
        """
        from mudlab.calculations import pattern_ops

        if shift_value == 0.0:
            return
        radius = self.goniometer.radius if self.goniometer is not None else 24.0
        if pattern_ops.PATTERN_SHIFT_TYPE == "Linear":
            for marker in self._markers:
                marker.position = marker.position - shift_value
        self._exp_x = pattern_ops.apply_shift(
            self._exp_x, shift_value, shift_position, radius, self.wavelength
        )
        self.data_changed.emit()

    def compute_strip_pattern(self, startx, endx, noise_level=None):
        """Preview the line that would replace a peak (nothing is changed)."""
        from mudlab.calculations import pattern_ops

        return pattern_ops.compute_strip_pattern(
            self._exp_x, self._exp_y, startx, endx, noise_level
        )

    def apply_strip(self, strip) -> None:
        from mudlab.calculations import pattern_ops

        if strip is None:
            return
        self._exp_y = pattern_ops.apply_strip(self._exp_x, self._exp_y, strip)
        self.data_changed.emit()

    def compute_peak_properties(self, startx, endx):
        """Area and FWHM of the peak between two positions (a measurement)."""
        from mudlab.calculations import pattern_ops

        return pattern_ops.compute_peak_properties(
            self._exp_x, self._exp_y, startx, endx
        )

    # ------------------------------------------------------------------
    # Non-destructive previews (the live data-op overlay). Each returns the
    # experimental (x, y) the matching operation WOULD produce, without
    # touching the stored pattern or emitting - so a dialog can draw the result
    # before the user commits. They call the same pattern_ops as the mutating
    # methods above, so the preview matches what OK applies.
    # ------------------------------------------------------------------
    def preview_remove_background(
        self, bg_type=0, bg_position=0.0, bg_pattern=None, bg_scale=0.0
    ):
        from mudlab.calculations import pattern_ops

        y = pattern_ops.remove_background(
            self._exp_y, bg_type, bg_position, bg_pattern, bg_scale
        )
        return self._exp_x, y

    def preview_smooth(self, smooth_type=0, smooth_degree=0.0):
        from mudlab.calculations import pattern_ops

        return self._exp_x, pattern_ops.smooth_data(
            self._exp_y, smooth_type, smooth_degree
        )

    def preview_add_noise(self, noise_fraction=0.0):
        from mudlab.calculations import pattern_ops

        return self._exp_x, pattern_ops.add_noise(self._exp_y, noise_fraction)

    def preview_shift(self, shift_value, shift_position=0.0):
        """The 2θ axis after a shift (markers are not moved for a preview)."""
        from mudlab.calculations import pattern_ops

        if shift_value == 0.0:
            return self._exp_x, self._exp_y
        radius = self.goniometer.radius if self.goniometer is not None else 24.0
        x = pattern_ops.apply_shift(
            self._exp_x, shift_value, shift_position, radius, self.wavelength
        )
        return x, self._exp_y

    def preview_strip(self, strip):
        from mudlab.calculations import pattern_ops

        if strip is None:
            return self._exp_x, self._exp_y
        return self._exp_x, pattern_ops.apply_strip(self._exp_x, self._exp_y, strip)

    def _trim_raw_calculated(self, min_2theta: float, max_2theta: float) -> None:
        """Clip the raw .mud calculated-pattern rows to the same range.

        The calculated line is the one part of the specimen the saver keeps
        VERBATIM from raw_properties: its stored rows may carry extra
        per-phase intensity columns, and this model only keeps the first two,
        so re-encoding it from _calc_x/_calc_y would silently drop the
        per-phase curves. Trim is the only operation that changes the
        calculated pattern, so it clips the raw rows itself and keeps the two
        in step. Without this the trim is lost on save and a reloaded project
        pairs a trimmed experimental pattern with a full-range calculated one
        - which reads as a *perfect* fit (Rp 0.00), not as an error.
        """
        line = self.raw_properties.get("calculated_pattern")
        if not isinstance(line, dict):
            return
        props = line.get("properties")
        if not isinstance(props, dict) or not props.get("data"):
            return
        try:
            rows = json.loads(props["data"])
        except (ValueError, TypeError):
            return
        kept = [
            row for row in rows
            if len(row) >= 2 and min_2theta <= float(row[0]) <= max_2theta
        ]
        # Fewer than 2 points is not a pattern: drop the line entirely, which
        # matches _calc_x/_calc_y being cleared above.
        props = dict(props)
        if len(kept) >= 2:
            props["data"] = json.dumps(kept, separators=(",", ":"))
            self.raw_properties["calculated_pattern"] = {
                **line, "properties": props,
            }
        else:
            self.raw_properties.pop("calculated_pattern", None)

    def trim(self, min_2theta: float, max_2theta: float) -> bool:
        """Permanently clip the specimen to [min_2theta, max_2theta].

        Also clips the calculated pattern (it lives on its own x-grid), drops
        markers that fall outside, and drops exclusion ranges that touch or
        cross a boundary - a range straddling the new edge would silently
        change meaning, so it is removed rather than clamped (old
        Specimen.trim).

        Returns False (changing nothing) when fewer than 2 points would remain.
        """
        mask = (self._exp_x >= min_2theta) & (self._exp_x <= max_2theta)
        if mask.sum() < 2:
            return False
        self._exp_x, self._exp_y = self._exp_x[mask], self._exp_y[mask]

        if self.has_calculated_data:
            cmask = (self._calc_x >= min_2theta) & (self._calc_x <= max_2theta)
            if cmask.sum() >= 2:
                self._calc_x, self._calc_y = self._calc_x[cmask], self._calc_y[cmask]
            else:
                self._calc_x, self._calc_y = np.empty(0), np.empty(0)
            self._trim_raw_calculated(min_2theta, max_2theta)
            # Per-phase curves are on the old x-grid; drop them (a recompute
            # rebuilds them on the trimmed grid).
            self.phase_patterns = None

        for marker in list(self._markers):
            if marker.position < min_2theta or marker.position > max_2theta:
                self.remove_marker(marker)

        self._exclusion_ranges = [
            (a, b) for a, b in self._exclusion_ranges
            if min(a, b) >= min_2theta and max(a, b) <= max_2theta
        ]

        self.data_changed.emit()
        return True
