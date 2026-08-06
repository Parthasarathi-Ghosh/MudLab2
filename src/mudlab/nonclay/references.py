"""Load a non-clay reference pattern as a RawPatternPhase container.

A reference is a fixed curve the Case-A fit scales; ``RawPatternPhase`` is the
container. The curve can come from a measured file (preferred for accuracy -
Finding 19) or, later, from a structure via the from-CIF calculator in
``tools/nonclay_experiments/structure_pattern.py``. ``apply_lpf`` stays False:
the reference is taken in observed-intensity space (Finding 11); the E1 gate
(``tools/nonclay_experiments/e1_refspace.py``) checks that precondition.
"""

from __future__ import annotations

import os

import numpy as np

from mudlab.file_parsers.xrd_import import parse_pattern
from mudlab.models.raw_pattern_phase import RawPatternPhase


def reference_from_arrays(x, y, name) -> RawPatternPhase:
    """Wrap an (x, y) curve as a non-clay reference."""
    phase = RawPatternPhase(name=name)
    phase.set_raw_pattern(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
    return phase


def load_reference(path, name=None) -> RawPatternPhase:
    """Load a measured reference curve (any format the shipped importer reads)."""
    x, y = parse_pattern(path)
    return reference_from_arrays(
        x, y, name or os.path.splitext(os.path.basename(path))[0])
