"""Non-clay phase model (experimental, "path 2").

A ``NonClayPhase`` is a :class:`~mudlab.models.raw_pattern_phase.RawPatternPhase`
that ALSO carries a declared oxide composition. Like a raw phase it has no
crystal structure - it contributes a fixed measured/computed pattern to the
mixture (scaled by its fraction), and it is never structurally refined. Unlike a
raw phase it knows its chemistry, so it can (later) feed a bulk oxide
composition. See the phase-``type`` gating notes:

  (a) contributes to the pattern + its fraction is optimised  -> reuses the raw
      pattern path (``get_diffracted_intensity`` dispatches "NonClayPhase" to
      ``_get_raw_intensity``);
  (b) never structurally refined                              -> free
      (``enumerate_refinables`` only enumerates ``type == "Phase"``);
  (c) contributes to composition                              -> DEFERRED (the
      ``oxides`` dict is stored + editable now; wiring it into a bulk
      composition is a follow-up so the clay-only ``mixture_composition`` and
      the XRF mass balance stay untouched).

``oxides`` is ``{oxide_name: wt%}`` over the reporting oxides
(``composition.reporting_oxides``), stored as entered (normalisation happens at
composition time). It round-trips in the .mud alongside the raw pattern.
"""

from __future__ import annotations

import numpy as np

from mudlab.models.raw_pattern_phase import RawPatternPhase

# Default Gaussian peak width for rendering a CIF reflection list (deg 2theta).
DEFAULT_FWHM = 0.10


class NonClayPhase(RawPatternPhase):
    """A raw-pattern phase that also declares its oxide composition.

    Two flavours share this model:
      - a **measured** non-clay: the ``raw_pattern`` is a fixed measured curve
        (``reflections`` empty); it resamples like a RawPatternPhase.
      - a **computed** (CIF) non-clay: it carries a ``reflections`` list of
        ``(d_angstrom, intensity)`` and renders its pattern from those at the
        specimen wavelength, broadened to ``fwhm``. Because the positions are
        d-spacings the pattern is specimen-wavelength-correct, and the width is
        tunable after import (path-2 phase A).
    """

    def __init__(self, name: str = "") -> None:
        super().__init__(name)
        self.type = "NonClayPhase"
        # {oxide_name: wt%}; empty until imported/entered.
        self.oxides: dict[str, float] = {}
        # CIF reflections [(d_angstrom, intensity 0..100)]; empty for a measured
        # non-clay. Present => the pattern is rendered from these (is_computed).
        self.reflections: list[tuple[float, float]] = []
        self.fwhm = DEFAULT_FWHM  # deg 2theta, Gaussian FWHM for the render

    @property
    def is_computed(self) -> bool:
        """True when the pattern is rendered from a CIF reflection list (so the
        FWHM is tunable), False for a fixed measured curve. Matches the render
        dispatch, which gates on the list being non-empty."""
        return bool(self.reflections)

    def set_reflections(self, reflections) -> None:
        self.reflections = [
            (float(d), float(i)) for d, i in (reflections or []) if float(d) > 0
        ]

    def set_fwhm(self, fwhm: float) -> None:
        self.fwhm = max(0.001, float(fwhm))

    # -- rendering (computed phases) --------------------------------------
    def render_on_grid(self, two_theta_deg, wavelength_nm, fwhm=None):
        """Render the reflection list onto a 2theta grid (deg) at
        ``wavelength_nm``: each d-spacing -> its 2theta at that wavelength, a
        Gaussian of the given/stored FWHM. Zeros when there are no reflections."""
        grid = np.asarray(two_theta_deg, dtype=float)
        y = np.zeros_like(grid)
        if not self.reflections:
            return y
        lam = float(wavelength_nm) * 10.0  # nm -> Angstrom
        sigma = max(1e-6, (self.fwhm if fwhm is None else float(fwhm)) / 2.35482)
        for d, inten in self.reflections:
            s = lam / (2.0 * d)
            if s >= 1.0:
                continue  # d < lambda/2: no reflection at this wavelength
            tt = np.degrees(2.0 * np.arcsin(s))
            y += inten * np.exp(-0.5 * ((grid - tt) / sigma) ** 2)
        return y

    def preview_pattern(self, wavelength_nm, lo=4.0, hi=80.0, step=0.02):
        x = np.arange(lo, hi, step)
        return x, self.render_on_grid(x, wavelength_nm)

    def rebuild_stored_pattern(self, wavelength_nm, lo=4.0, hi=80.0, step=0.02) -> None:
        """Re-render the cached ``raw_pattern`` from the reflections at the
        current FWHM (call at import and after a FWHM change). No-op for a
        measured phase."""
        if not self.reflections:
            return
        x, y = self.preview_pattern(wavelength_nm, lo, hi, step)
        self.set_raw_pattern(x, y)

    def set_oxides(self, oxides) -> None:
        """Store the oxide composition, dropping non-positive entries and
        coercing to float (so a blank grid cell is simply absent)."""
        self.oxides = {
            str(k): float(v)
            for k, v in dict(oxides or {}).items()
            if _positive(v)
        }

    @property
    def has_composition(self) -> bool:
        return any(v > 0 for v in self.oxides.values())

    # -- serialization -----------------------------------------------------
    def to_dict(self) -> dict:
        data = super().to_dict()
        data["type"] = "NonClayPhase"
        props = data["properties"]
        props["oxides"] = dict(self.oxides)
        props["reflections"] = [[d, i] for d, i in self.reflections]
        props["fwhm"] = float(self.fwhm)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "NonClayPhase":
        phase = super().from_dict(data)  # cls == NonClayPhase, so type is set
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        phase.set_oxides(props.get("oxides"))
        phase.set_reflections(props.get("reflections"))
        if props.get("fwhm") is not None:
            try:
                phase.fwhm = float(props["fwhm"])
            except (TypeError, ValueError):
                pass
        return phase


def _positive(value) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False
