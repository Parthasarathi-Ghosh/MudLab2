"""High-level non-clay decomposition (Case A) + result containers.

Ties the estimator (fit references to the clay-subtracted residual) to the
detection rule (quality gate + mis-registration null + floor). Every number is
SEMI-QUANTITATIVE - integrated intensity is not weight % without RIRs or an
internal standard (the Si-standard path, deferred). READ-ONLY over the clay path.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mudlab.nonclay import detection, estimator


@dataclass
class ReferenceResult:
    name: str
    area: float          # integrated area of the fitted reference contribution
    pct: float           # % of (clay + this reference), matching the null's scale
    null_pct: float      # mis-registration detection threshold
    detected: bool


@dataclass
class SpecimenResult:
    name: str
    rp: float
    nonclay_pct: float   # total non-clay share of the modelled signal
    references: list     # list[ReferenceResult]


@dataclass
class NonclayResult:
    reference_names: list
    specimens: list      # list[SpecimenResult]
    shared_amps: np.ndarray  # one amplitude per reference, shared across specimens


def decompose_specimen(specimen, references, detect=True) -> SpecimenResult:
    """Decompose a single specimen: fit the references to its residual and
    (optionally) apply the detection rule per reference."""
    rp = estimator.specimen_rp(specimen)
    fit = estimator.fit_specimen(specimen, references)
    x, _residual, clay, _corr = estimator.specimen_residual(specimen)
    a_clay = estimator.area(clay, x)
    refs = []
    for i, ref in enumerate(references):
        a = float(fit["areas"][i])
        pct = 100.0 * a / (a_clay + a) if a_clay else 0.0
        null = detection.null_threshold_pct(specimen, ref) if detect else 0.0
        flag = detection.is_detected(pct, null, rp) if detect else False
        refs.append(ReferenceResult(ref.name, a, pct, null, flag))
    return SpecimenResult(getattr(specimen, "name", "") or "specimen",
                          rp, fit["nonclay_pct"], refs)


def decompose_mixture(mixture, references, detect=True) -> NonclayResult:
    """Decompose every specimen of a mixture, plus the shared cross-specimen
    amplitude (Finding 14). The clay fit must be current (call
    ``mixture.calculate()`` / ``optimize()`` first)."""
    specimens = [s for s in mixture.specimens if s is not None]
    per = [decompose_specimen(s, references, detect=detect) for s in specimens]
    shared = (estimator.shared_fit(specimens, references)
              if specimens else np.zeros(len(references)))
    return NonclayResult([r.name for r in references], per, shared)
