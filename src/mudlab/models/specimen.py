"""Specimen model (Qt signals).

Property names follow the old mudlab.specimen.models.Specimen so the port
greps cleanly; storage and change notification are pure Qt. Signals mirror
the old semantics: data_changed for pattern data, visuals_changed for
display switches and labels.
"""

from __future__ import annotations

import json

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
        self._exp_x = np.empty(0)
        self._exp_y = np.empty(0)
        self._calc_x = np.empty(0)
        self._calc_y = np.empty(0)
        # Verbatim .mud specimen properties (goniometer, markers, ...) so
        # unmodeled parts survive load/save round-trips.
        self.raw_properties: dict = {}

    @property
    def wavelength(self) -> float:
        """Dominant X-ray wavelength in nm (old Goniometer.wavelength:
        the distribution's highest-fraction wavelength). Read from the
        raw goniometer data until the goniometer model is ported."""
        gonio = self.raw_properties.get("goniometer")
        if isinstance(gonio, dict):
            wld = gonio.get("properties", {}).get("wavelength_distribution")
            if isinstance(wld, str) and wld:
                try:
                    rows = json.loads(wld)
                except ValueError:
                    rows = None
                if rows:
                    best = max(rows, key=lambda row: row[1])
                    return float(best[0])
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
