"""Measured (XRF) oxide composition, held once per project.

One MudLab project describes ONE physical clay sample - its specimens are
treatment variants of that sample - so a measured bulk analysis belongs to the
project, not to a specimen or a phase. It is optional: a project without one
behaves exactly as before.

It exists to be compared against the MODELLED composition
(``calculations.composition.mixture_composition``), so it deliberately uses the
same oxide set (``reporting_oxides``) and the same weight-percent convention.
That is also why the import grid restricts the user to those oxides: a value
that the model can never produce could not take part in the comparison.

FILE FORMAT NOTE. This is written as a ``composition`` property of the Project,
which the OLD GTK app cannot read - it deserialises with ``cls(**properties)``
and raises TypeError on any key it does not know (measured, not assumed; see
docs/dev-notes.md). That is a deliberate, accepted divergence: the planned
old-app / PyXRD exporters are what will strip MudLab2-only data on the way out.
Nothing here changes how an existing project without a composition round-trips.
"""

from __future__ import annotations

import uuid as _uuid

from mudlab.calculations.composition import reporting_oxides


class Composition:
    """A measured oxide analysis: ``{oxide name: weight percent}``.

    A plain (non-Qt) value object, like the calc-side models: the project owns
    it and emits the change signal, so there is no second source of truth.
    """

    def __init__(self, name: str = "XRF", oxides: dict | None = None,
                 source: str = "", uuid_: str | None = None) -> None:
        self.name = name or "XRF"
        # Free-text provenance (lab, method, date) - shown in the dialog and
        # kept in the file. Never parsed.
        self.source = source or ""
        self.uuid = uuid_ or _uuid.uuid4().hex
        self._oxides: dict[str, float] = {}
        self.set_oxides(oxides)

    # ------------------------------------------------------------------
    @property
    def oxides(self) -> dict:
        """The stored analysis. A COPY: callers (the grid especially) must not
        be able to mutate the model by holding on to this."""
        return dict(self._oxides)

    def set_oxides(self, oxides) -> None:
        """Replace the analysis, keeping only the reporting oxides and only
        finite, non-negative numbers.

        Filtering here rather than at the call site means a hand-edited file, a
        future importer and the dialog all get the same guarantees - the
        comparison never has to defend against a stray key or a NaN.
        """
        allowed = set(reporting_oxides())
        cleaned: dict[str, float] = {}
        for key, value in (oxides or {}).items():
            name = str(key)
            if name not in allowed:
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if number == number and number not in (float("inf"), float("-inf")) \
                    and number >= 0.0:
                cleaned[name] = number
        self._oxides = cleaned

    def total(self) -> float:
        return float(sum(self._oxides.values()))

    def normalized(self) -> dict:
        """The analysis scaled to 100 wt%, or an empty dict when it is empty.

        The modelled composition is always normalised to 100, so a comparison
        against a raw analysis (which may total 97 or 101) would read as a
        difference that is not really there."""
        total = self.total()
        if total <= 0.0:
            return {}
        return {name: value * 100.0 / total for name, value in self._oxides.items()}

    def is_empty(self) -> bool:
        return self.total() <= 0.0

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "type": "Composition",
            "properties": {
                "uuid": self.uuid,
                "name": self.name,
                "source": self.source,
                "oxides": dict(self._oxides),
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Composition":
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        return cls(
            name=props.get("name", "XRF"),
            oxides=props.get("oxides"),
            source=props.get("source", ""),
            uuid_=props.get("uuid"),
        )
