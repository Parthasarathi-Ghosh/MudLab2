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

from mudlab.models.raw_pattern_phase import RawPatternPhase


class NonClayPhase(RawPatternPhase):
    """A raw-pattern phase that also declares its oxide composition."""

    def __init__(self, name: str = "") -> None:
        super().__init__(name)
        self.type = "NonClayPhase"
        # {oxide_name: wt%}; empty until imported/entered.
        self.oxides: dict[str, float] = {}

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
        data["properties"]["oxides"] = dict(self.oxides)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "NonClayPhase":
        phase = super().from_dict(data)  # cls == NonClayPhase, so type is set
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        phase.set_oxides(props.get("oxides"))
        return phase


def _positive(value) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False
