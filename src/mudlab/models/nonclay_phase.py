"""Non-clay phase model (experimental, "path 2").

A ``NonClayPhase`` is a :class:`~mudlab.models.raw_pattern_phase.RawPatternPhase`
that ALSO carries a declared oxide composition. Like a raw phase it has no
crystal structure - it contributes a fixed measured/computed pattern to the
mixture (scaled by its fraction), and it is never structurally refined. Unlike a
raw phase it knows its chemistry, so it feeds the bulk oxide composition. See
the phase-``type`` gating notes:

  (a) contributes to the pattern + its fraction is optimised  -> reuses the raw
      pattern path (``get_diffracted_intensity`` dispatches "NonClayPhase" to
      ``_get_raw_intensity``);
  (b) never structurally refined                              -> free
      (``enumerate_refinables`` only enumerates ``type == "Phase"``);
  (c) contributes to composition                              -> the ``oxides``
      dict feeds ``composition.bulk_composition``, a SEPARATE additive view;
      the clay-only ``mixture_composition`` and the XRF mass balance that reads
      it are untouched.

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
        self.fwhm = DEFAULT_FWHM  # deg 2theta, constant Gaussian FWHM for the render
        # Optional Caglioti angle-dependent width (U, V, W): FWHM(theta)^2 =
        # U*tan^2(theta) + V*tan(theta) + W (deg^2). None => the constant fwhm.
        self.caglioti: tuple[float, float, float] | None = None

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
        """Set a constant width (and drop any Caglioti angle dependence)."""
        self.fwhm = max(0.001, float(fwhm))
        self.caglioti = None

    def set_caglioti(self, u: float, v: float, w: float) -> None:
        self.caglioti = (float(u), float(v), float(w))

    def clear_caglioti(self) -> None:
        self.caglioti = None

    def fwhm_at(self, two_theta_deg, caglioti=None):
        """The Gaussian FWHM (deg 2theta) at a 2theta position: constant
        ``self.fwhm`` unless a Caglioti (U, V, W) is set/given."""
        cag = caglioti if caglioti is not None else self.caglioti
        if cag is None:
            return self.fwhm
        u, v, w = cag
        t = np.tan(np.radians(np.asarray(two_theta_deg, dtype=float) * 0.5))
        val = u * t * t + v * t + w
        return np.sqrt(np.maximum(val, 1e-6))

    # -- rendering (computed phases) --------------------------------------
    def render_on_grid(self, two_theta_deg, wavelength_nm, fwhm=None, caglioti=None):
        """Render the reflection list onto a 2theta grid (deg) at
        ``wavelength_nm``: each d-spacing -> its 2theta at that wavelength, a
        Gaussian whose width is the constant ``fwhm`` (or ``self.fwhm``), OR the
        angle-dependent Caglioti width when ``caglioti``/``self.caglioti`` is set.
        Zeros when there are no reflections.

        An explicitly passed width wins over the stored one, either way round: a
        given ``caglioti`` overrides everything, and a given constant ``fwhm``
        overrides a stored ``self.caglioti`` (the caller asked for one width, so
        silently rendering an angle-dependent one would be a trap)."""
        grid = np.asarray(two_theta_deg, dtype=float)
        y = np.zeros_like(grid)
        if not self.reflections:
            return y
        lam = float(wavelength_nm) * 10.0  # nm -> Angstrom
        if caglioti is not None:
            cag = caglioti
        else:
            cag = None if fwhm is not None else self.caglioti
        const_fwhm = self.fwhm if fwhm is None else float(fwhm)
        for d, inten in self.reflections:
            s = lam / (2.0 * d)
            if s >= 1.0:
                continue  # d < lambda/2: no reflection at this wavelength
            tt = np.degrees(2.0 * np.arcsin(s))
            fwhm_r = float(self.fwhm_at(tt, cag)) if cag is not None else const_fwhm
            sigma = max(1e-6, fwhm_r / 2.35482)
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
        props["caglioti"] = list(self.caglioti) if self.caglioti is not None else None
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
        cag = props.get("caglioti")
        if cag and len(cag) == 3:
            try:
                phase.caglioti = (float(cag[0]), float(cag[1]), float(cag[2]))
            except (TypeError, ValueError):
                pass
        return phase


def _positive(value) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False
