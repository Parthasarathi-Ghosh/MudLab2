"""XRF mass-balance quantification of non-clays in WEIGHT % (read-only).

Given the clay composition (from the shipped ``mixture_composition``), the
sample's XRF bulk oxide composition, and each non-clay's oxide composition, solve
by non-negative least squares for the phase weight fractions::

    XRF_oxide  ~=  W_clay * clay_comp + sum_i W_i * nonclay_comp_i

This is orientation-INDEPENDENT (chemistry), unlike the XRD intensity share which
is biased low on oriented mounts (Findings 23-24). Accuracy is limited by the
clay composition (Finding 22: Al over / Fe under / Mg-Na-Ti missing when the clay
atom types are idealised); the per-oxide residual is returned so the UI can flag
that gap. READ-ONLY: nothing here mutates a model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import nnls

from mudlab.calculations.composition import mixture_composition

# Ideal oxide compositions (wt%) for common non-clay minerals, over the reporting
# oxides. A CIF-derived composition (structure._oxide_composition) is preferred
# when available; this table serves measured references matched by name. Some
# minerals (e.g. calcite) carry oxides outside the clay set (CO2) - only the
# in-table oxides are used.
MINERAL_OXIDES = {
    "quartz": {"SiO2": 100.0},
    "albite": {"Na2O": 11.8, "Al2O3": 19.4, "SiO2": 68.7},       # NaAlSi3O8
    "orthoclase": {"K2O": 16.9, "Al2O3": 18.3, "SiO2": 64.8},    # KAlSi3O8
    "microcline": {"K2O": 16.9, "Al2O3": 18.3, "SiO2": 64.8},
    "k-feldspar": {"K2O": 16.9, "Al2O3": 18.3, "SiO2": 64.8},
    "calcite": {"CaO": 100.0},                                   # CaO only (CO2 = LOI)
}


def mineral_composition(name: str):
    """Best-effort oxide composition for a reference, matched by name; None if
    unknown (that non-clay is then left out of the mass balance)."""
    low = (name or "").lower()
    for mineral, comp in MINERAL_OXIDES.items():
        if mineral in low:
            return comp
    return None


@dataclass
class MassBalanceResult:
    components: list      # ["clay", <ref name>, ...]
    weight_pct: list      # weight % per component (sums to 100)
    oxide_order: list
    residual: list        # per-oxide (xrf - model), wt%
    unexplained_pct: float  # sum(|residual|) / sum(xrf) * 100


def mass_balance(mixture, xrf_oxides, references, compositions=None,
                 specimen_index=0):
    """Solve the oxide mass balance for one sample.

    ``xrf_oxides`` = ``{oxide_name: wt%}``; ``references`` = the non-clay
    RawPatternPhases. ``compositions`` (optional, parallel to ``references``) are
    explicit oxide dicts - a CIF-derived one takes precedence; where absent the
    composition is matched by name via MINERAL_OXIDES. Returns a
    MassBalanceResult, or None when the clay composition or the XRF is missing.
    Non-clays with no known composition are skipped."""
    _names, oxide_rows = mixture_composition(mixture)
    order = [oxide for oxide, _pcts in oxide_rows]
    clay = np.array([
        pcts[specimen_index] if specimen_index < len(pcts) else 0.0
        for _oxide, pcts in oxide_rows
    ], dtype=float)
    xrf = np.array([float(xrf_oxides.get(o, 0.0)) for o in order], dtype=float)
    if not np.any(clay) or not np.any(xrf):
        return None

    cols, comp_names = [clay], ["clay"]
    for i, ref in enumerate(references):
        comp = compositions[i] if (compositions is not None
                                   and i < len(compositions)) else None
        if not comp:
            comp = mineral_composition(getattr(ref, "name", ""))
        if not comp:
            continue
        cols.append(np.array([comp.get(o, 0.0) for o in order], dtype=float))
        comp_names.append(getattr(ref, "name", "non-clay"))

    A = np.column_stack(cols)
    weights, _rnorm = nnls(A, xrf)
    total = float(weights.sum()) or 1.0
    weight_pct = [100.0 * w / total for w in weights]
    recon = A @ weights
    residual = [float(v) for v in (xrf - recon)]
    unexplained = float(np.sum(np.abs(xrf - recon)) / (np.sum(xrf) or 1.0) * 100.0)
    return MassBalanceResult(comp_names, weight_pct, order, residual, unexplained)
