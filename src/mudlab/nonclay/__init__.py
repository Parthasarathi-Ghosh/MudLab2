"""Non-clay decomposition (EXPERIMENTAL, optional, additive).

Quantifies non-clay accessory minerals by fitting reference patterns to the
clay-subtracted residual (Case A). This package is READ-ONLY over the clay path:
it consumes the existing clay fit + ``calculate_phase_intensities`` and never
mutates a model or edits ``calculations/``. Nothing in mainstream imports this
package except one fenced ``NONCLAY`` seam (Slice 3 - see the retraction
manifest, not present yet). Delete this directory to retract the engine.

Evidence base: the method notes and reproducibility scripts are kept OUTSIDE
this repository - the method is unpublished work. Every output is
SEMI-QUANTITATIVE (no RIR / internal standard yet).
"""

from mudlab.nonclay.decompose import (
    NonclayResult, ReferenceResult, SpecimenResult,
    decompose_mixture, decompose_specimen,
)
from mudlab.nonclay.dialog import NonclayDialog
from mudlab.nonclay.references import load_reference, reference_from_arrays

__all__ = [
    "decompose_mixture", "decompose_specimen", "load_reference",
    "reference_from_arrays", "NonclayResult", "SpecimenResult", "ReferenceResult",
    "NonclayDialog",
]
