"""Raw-pattern phase model.

Ported from the old mudlab / PyXRD ``RawPatternPhase`` (calc subset). Unlike a
regular :class:`~mudlab.models.phase.Phase`, a raw-pattern phase is NOT computed
from a structure: it carries a fixed, measured XRD pattern (a stored
``2theta -> intensity`` curve) and contributes that curve directly to the
mixture, scaled by its phase fraction. It has no components, atoms, CSDS or
stacking probabilities - the pattern IS the phase.

Used for the non-clay parts of a real sample (quartz, feldspar, calcite), an
amorphous hump, or an internal standard: things you cannot or do not want to
model structurally, so you drop in a measured reference and let the optimiser
fit only its scale.

The measured curve is stored INSIDE the .mud/.pyxrd, as a ``PyXRDLine`` under
the ``raw_pattern`` property (the same serialisation a specimen's experimental
pattern uses): ``properties.raw_pattern.properties.data`` is a JSON string of
``[2theta, intensity]`` rows. So loading a saved raw-pattern phase needs no
instrument-format parser (.xrdml/.raw/.xy) - those are only for IMPORTING a new
measured curve, which is a later batch. ``apply_lpf`` and ``apply_correction``
are always False (the stored pattern is taken as measured).
"""

from __future__ import annotations

import json
import uuid as _uuid

import numpy as np


def _decode_raw_pattern(data_string) -> tuple[np.ndarray, np.ndarray]:
    """Decode a PyXRDLine ``data`` string (JSON rows of ``[x, y]``) into x / y
    arrays; tolerate an already-decoded list or empty data. Mirrors
    ``mud_project._decode_pattern_data`` (kept here so the model has no
    dependency on the file parser)."""
    if isinstance(data_string, str):
        rows = json.loads(data_string) if data_string else []
    elif isinstance(data_string, list):
        rows = data_string
    else:
        rows = []
    if len(rows) < 2:
        return np.empty(0), np.empty(0)
    array = np.asarray(rows, dtype=float)
    return array[:, 0], array[:, 1]


def _encode_raw_pattern(x: np.ndarray, y: np.ndarray) -> str:
    """Encode x / y arrays into a PyXRDLine ``data`` string. Byte-for-byte the
    same format as ``mud_project._encode_pattern_data`` so a curve round-trips
    identically whichever path writes it."""
    pairs = [[float(xi), float(yi)] for xi, yi in zip(x, y)]
    return json.dumps(pairs, separators=(",", ":"))


class RawPatternPhase:
    """A phase whose diffraction contribution is a fixed measured pattern.

    Implements only the slice of the phase interface the mixture / calc / phase
    list actually use (``type``, ``uuid``, ``name``, ``apply_lpf``,
    ``apply_correction``, ``components`` [empty], ``based_on`` [None],
    ``raw_pattern_x`` / ``raw_pattern_y``, ``to_dict`` / ``from_dict``). It is a
    sibling of :class:`Phase`, not a subclass - the structural phase stays clean.
    """

    def __init__(self, name: str = "") -> None:
        self.type = "RawPatternPhase"
        self.uuid = _uuid.uuid4().hex
        self.name = name
        # A raw pattern is taken exactly as measured: no Lorentz-polarisation
        # factor and no machine correction (matches PyXRD's data_object).
        self.apply_lpf = False
        self.apply_correction = False
        # The stored measured curve (2theta degrees -> intensity).
        self.raw_pattern_x = np.empty(0)
        self.raw_pattern_y = np.empty(0)
        # Stable identity for the embedded PyXRDLine when this phase has no
        # stored line yet (a freshly created raw phase): minted ONCE so
        # repeated to_dict() calls are byte-identical. A loaded phase keeps the
        # line's stored uuid instead (preserved verbatim in raw_properties).
        self._line_uuid = _uuid.uuid4().hex
        # No structure: these let the generic phase-graph loops (link / UCP /
        # based_on resolution, remove-phase cascades) treat a raw phase as a
        # leaf with nothing to resolve.
        self.G = 0
        self.components: list = []
        self.based_on = None
        # Full .mud phase dict kept verbatim so unmodeled line properties
        # (color, line width, label, uuid) survive a round-trip; to_dict writes
        # the modeled fields (name, uuid, pattern data) back into it.
        self.raw_properties: dict = {}

    # -- phase-graph no-ops (a raw phase has no structure to resolve) -------
    def resolve_based_on(self, phase_map: dict) -> None:
        """A raw phase never inherits (no structural parameters); no-op so the
        loader's resolve loop can treat every phase uniformly."""
        return None

    def set_based_on(self, target) -> bool:
        """A raw phase cannot be based on another (nothing to inherit). Always
        a no-op; returns False so callers know nothing changed."""
        return False

    @property
    def valid_probs(self) -> bool:
        """A raw phase has a valid contribution whenever it holds >= 2 points."""
        return self.raw_pattern_x.size > 1

    # -- pattern data ------------------------------------------------------
    def set_raw_pattern(self, x, y) -> None:
        self.raw_pattern_x = np.asarray(x, dtype=float)
        self.raw_pattern_y = np.asarray(y, dtype=float)

    # -- serialization -----------------------------------------------------
    def to_dict(self) -> dict:
        """Serialize to a .mud RawPatternPhase dict: overwrite the modeled
        fields (name, uuid, and the pattern's ``data``) on top of the verbatim
        raw properties, preserving the ``raw_pattern`` line's other keys
        (color, label, uuid) so the round-trip stays byte-identical - the same
        strategy the specimen saver uses for its experimental line."""
        props = dict(self.raw_properties)
        props["uuid"] = self.uuid
        props["name"] = self.name
        line = props.get("raw_pattern")
        if not isinstance(line, dict):
            line = {
                "type": "PyXRDLine",
                "properties": {"label": "Raw pattern", "uuid": self._line_uuid},
            }
        line_props = dict(line.get("properties", {}))
        line_props["data"] = _encode_raw_pattern(
            self.raw_pattern_x, self.raw_pattern_y
        )
        props["raw_pattern"] = {
            "type": line.get("type", "PyXRDLine"),
            "properties": line_props,
        }
        return {"type": "RawPatternPhase", "properties": props}

    @classmethod
    def from_dict(cls, data: dict) -> "RawPatternPhase":
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        phase = cls(name=props.get("name", ""))
        phase.raw_properties = dict(props)
        if "uuid" in props:
            phase.uuid = props["uuid"]
        line = props.get("raw_pattern")
        if isinstance(line, dict):
            line_props = line.get("properties", {})
            x, y = _decode_raw_pattern(line_props.get("data"))
            phase.raw_pattern_x, phase.raw_pattern_y = x, y
            if line_props.get("uuid"):
                phase._line_uuid = line_props["uuid"]
        return phase
