"""Goniometer model (Qt signals).

The diffractometer setup for a specimen: geometry, slits, wavelength
distribution and sample-absorption parameters. Property names follow the
old mudlab.goniometer.models.Goniometer so the .mud keys line up. The
`wavelength` is derived from the wavelength distribution (the dominant
line), matching the old read-only property; the calculation helpers in
`calculations.goniometer` consume `soller1/soller2/mcr_2theta`,
`divergence_mode/divergence`, `radius`, `sample_length`,
`sample_surf_density`, `absorption` and `has_absorption_correction`.
"""

from __future__ import annotations

import json
import uuid

import numpy as np
from PySide6.QtCore import QObject, Signal

from mudlab.models.properties import Prop

DEFAULT_WAVELENGTH = 0.154056  # nm, CuKα1

# Scalar keys shared 1:1 with the .mud file.
_SCALAR_KEYS = (
    "radius", "divergence_mode", "divergence",
    "has_soller1", "soller1", "has_soller2", "soller2",
    "min_2theta", "max_2theta", "steps", "mcr_2theta",
    "has_absorption_correction", "absorption",
    "sample_length", "sample_surf_density",
)


class Goniometer(QObject):
    data_changed = Signal()

    radius = Prop(24.0, "data_changed")
    divergence_mode = Prop("FIXED", "data_changed")  # FIXED | AUTOMATIC
    divergence = Prop(0.5, "data_changed")
    has_soller1 = Prop(True, "data_changed")
    soller1 = Prop(2.3, "data_changed")
    has_soller2 = Prop(True, "data_changed")
    soller2 = Prop(2.3, "data_changed")
    min_2theta = Prop(3.0, "data_changed")
    max_2theta = Prop(45.0, "data_changed")
    steps = Prop(2500, "data_changed")
    mcr_2theta = Prop(0.0, "data_changed")
    has_absorption_correction = Prop(False, "data_changed")
    absorption = Prop(45.0, "data_changed")
    sample_length = Prop(1.25, "data_changed")
    sample_surf_density = Prop(20.0, "data_changed")

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.uuid = uuid.uuid4().hex
        # List of (wavelength_nm, fraction) pairs (old wavelength_distribution).
        self.wavelength_distribution: list[tuple[float, float]] = [
            (DEFAULT_WAVELENGTH, 1.0)
        ]
        self.raw_properties: dict = {}

    @property
    def wavelength(self) -> float:
        """Dominant (highest-fraction) wavelength in nm."""
        if self.wavelength_distribution:
            return float(max(self.wavelength_distribution, key=lambda wf: wf[1])[0])
        return DEFAULT_WAVELENGTH

    def set_wavelength_distribution(self, pairs) -> None:
        """Replace the emission spectrum with (wavelength_nm, fraction) pairs.

        Drops the verbatim raw string kept for byte-identical round-trips (see
        to_dict) so the edit is actually re-encoded on save, and emits
        data_changed so the derived `wavelength` and any pattern calc refresh.
        """
        self.wavelength_distribution = [
            (float(w), float(f)) for w, f in pairs
        ]
        # An edited distribution can no longer be saved verbatim.
        self.raw_properties.pop("wavelength_distribution", None)
        self.data_changed.emit()

    def seed_range_from_data(self, x) -> bool:
        """Set the calculation range from a scan that has just been imported:
        `min_2theta` / `max_2theta` from the data's extremes and `steps` from
        its point count. Answers whether anything was set.

        The old app did this for every import (`create_gon_file` ->
        `reset_from_file`), but only from the range a vendor parser *declared*,
        so a plain `.xy` fell back to the 3-45 deg / 2500-step model default and
        the goniometer then described a scan that was never taken. Reading the
        parsed axis instead works for every format we can open.

        This is a DEFAULT, not a decision: `apply_setup` resets every modelled
        parameter, so a goniometer setup applied afterwards overwrites all
        three. Seeding only settles what an untouched goniometer says.

        For a specimen that HAS experimental data these three fields do not
        reach the numerics - `calculate_specimen_pattern` grids the calculated
        pattern on the experimental axis whenever there is one - so this fixes
        the goniometer reports, what a data-less recalculation would use, and
        what the .mud / .pyxrd exporters write.
        """
        x = np.asarray(x, dtype=float).ravel()
        x = x[np.isfinite(x)]
        if x.size < 2:
            return False
        low, high = float(np.min(x)), float(np.max(x))
        # A zero-width range is exactly what makes `D8 ECO Lynxeye XE.gon`
        # calculate an empty pattern; never create one here from a constant
        # axis.
        if not high > low:
            return False
        self.blockSignals(True)
        try:
            self.min_2theta = low
            self.max_2theta = high
            self.steps = int(x.size)
        finally:
            self.blockSignals(False)
        self.data_changed.emit()
        return True

    # ------------------------------------------------------------------
    # Effective Soller values (0 when the slit is disabled)
    # ------------------------------------------------------------------
    @property
    def effective_soller1(self) -> float:
        return self.soller1 if self.has_soller1 else 0.0

    @property
    def effective_soller2(self) -> float:
        return self.soller2 if self.has_soller2 else 0.0

    # ------------------------------------------------------------------
    # Serialization (.mud)
    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict) -> "Goniometer":
        props = data.get("properties", {})
        gonio = cls()
        gonio.raw_properties = dict(props)
        for key in _SCALAR_KEYS:
            if key in props:
                setattr(gonio, key, props[key])
        wld = props.get("wavelength_distribution")
        if isinstance(wld, str) and wld:
            try:
                gonio.wavelength_distribution = [tuple(pair) for pair in json.loads(wld)]
            except (ValueError, TypeError):
                pass
        elif isinstance(wld, list):
            gonio.wavelength_distribution = [tuple(pair) for pair in wld]
        elif "lambda" in props:
            # Legacy .gon setups store a single wavelength, not a distribution.
            try:
                gonio.wavelength_distribution = [(float(props["lambda"]), 1.0)]
            except (ValueError, TypeError):
                pass
        if "uuid" in props:
            gonio.uuid = props["uuid"]
        return gonio

    def apply_setup(self, props: dict) -> None:
        """Load a stored goniometer setup (`.gon` ``properties``) into this
        goniometer, keeping its own uuid and project linkage.

        Every modeled parameter is reset from `props` (missing keys fall back to
        the model defaults, as the old reset_from_file did), so a setup fully
        defines the goniometer. Emits data_changed once."""
        fresh = Goniometer.from_dict({"properties": props})
        # Set everything under one signal (old reset_from_file held data_changed),
        # so listeners recompute once, not once per parameter.
        self.blockSignals(True)
        try:
            for key in _SCALAR_KEYS:
                setattr(self, key, getattr(fresh, key))
            self.wavelength_distribution = list(fresh.wavelength_distribution)
        finally:
            self.blockSignals(False)
        # The distribution changed, so it can no longer be saved verbatim.
        self.raw_properties.pop("wavelength_distribution", None)
        self.data_changed.emit()

    def to_dict(self) -> dict:
        props = dict(self.raw_properties)
        for key in _SCALAR_KEYS:
            props[key] = getattr(self, key)
        # Preserve the raw wavelength_distribution string verbatim so an
        # untouched goniometer round-trips byte-identically; the editor
        # (set_wavelength_distribution) pops the raw key when the distribution
        # changes, so an edit falls through to the re-encode below.
        if "wavelength_distribution" not in props:
            props["wavelength_distribution"] = json.dumps(
                [[float(w), float(f)] for w, f in self.wavelength_distribution]
            )
        props["uuid"] = self.uuid
        return {"type": "Goniometer", "properties": props}
