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
        if "uuid" in props:
            gonio.uuid = props["uuid"]
        return gonio

    def to_dict(self) -> dict:
        props = dict(self.raw_properties)
        for key in _SCALAR_KEYS:
            props[key] = getattr(self, key)
        # Preserve the raw wavelength_distribution string verbatim (there is
        # no UI to edit it yet, so it never changes); only encode from the
        # list when none was loaded, so round-trips stay byte-identical.
        if "wavelength_distribution" not in props:
            props["wavelength_distribution"] = json.dumps(
                [[float(w), float(f)] for w, f in self.wavelength_distribution]
            )
        props["uuid"] = self.uuid
        return {"type": "Goniometer", "properties": props}
