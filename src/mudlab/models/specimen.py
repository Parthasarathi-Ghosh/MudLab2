"""Specimen model (Qt signals).

Property names follow the old mudlab.specimen.models.Specimen so the port
greps cleanly; storage and change notification are pure Qt. Signals mirror
the old semantics: data_changed for pattern data, visuals_changed for
display switches and labels.
"""

from __future__ import annotations

import uuid as _uuid

import numpy as np
from PySide6.QtCore import QObject, Signal

from mudlab.models.properties import Prop

DEFAULT_WAVELENGTH = 0.154056  # nm, CuKα1 (old settings default)


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
        self.goniometer = None  # set from the .mud (Goniometer model)
        self.project = None  # set by Project.add_specimen
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

    def set_calculated_pattern(self, x, y) -> None:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if x.shape != y.shape:
            raise ValueError("x and y must have the same length")
        self._calc_x, self._calc_y = x, y
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

        for marker in list(self._markers):
            if marker.position < min_2theta or marker.position > max_2theta:
                self.remove_marker(marker)

        self._exclusion_ranges = [
            (a, b) for a, b in self._exclusion_ranges
            if min(a, b) >= min_2theta and max(a, b) <= max_2theta
        ]

        self.data_changed.emit()
        return True
