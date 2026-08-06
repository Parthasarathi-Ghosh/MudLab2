"""Non-clay decomposition (EXPERIMENTAL, optional, additive).

Quantifies non-clay accessory minerals by fitting reference patterns to the
clay-subtracted residual (Case A). This package is READ-ONLY over the clay path:
it consumes the existing clay fit + ``calculate_phase_intensities`` and never
mutates a model or edits ``calculations/``. Nothing in mainstream imports this
package except one fenced ``NONCLAY`` seam (Slice 3 - see the retraction
manifest, not present yet). Delete this directory to retract the engine.

Evidence base: ``docs/non-clay-analysis-notes.md`` (Findings 1-20) and the
reproducibility scripts in ``tools/nonclay_experiments/``. Every output is
SEMI-QUANTITATIVE (no RIR / internal standard yet).
"""

from mudlab.nonclay.decompose import (
    NonclayResult, ReferenceResult, SpecimenResult,
    decompose_mixture, decompose_specimen,
)
from mudlab.nonclay.references import load_reference, reference_from_arrays

__all__ = [
    "decompose_mixture", "decompose_specimen", "load_reference",
    "reference_from_arrays", "NonclayResult", "SpecimenResult", "ReferenceResult",
]
