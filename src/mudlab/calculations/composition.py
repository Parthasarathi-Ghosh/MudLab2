"""Oxide composition of a mixture's specimens.

Ported as-is from the old mudlab Mixture.get_composition_matrix. For each
specimen the modeled phases contribute their atoms' element weights, which are
converted to the usual reporting oxides (SiO2, Al2O3, Fe2O3, CaO, MgO, Na2O,
K2O) via a fixed conversion table and normalised to 100 wt%.

The per-atom contribution is::

    pn x atom_type.weight x (component_weight_fraction x phase_fraction) x oxide_factor

where the component weight fraction is the phase's mean weight of that component
(``probabilities.get_distribution_array()`` - the old ``mW``). Raw-pattern
phases (no structure) and empty cells contribute nothing.

The conversion factors live in ``mudlab/data/composition_conversion.csv`` (the
old app's factors verbatim; its ``Al2O2`` *label* typo is corrected to the
chemically-correct ``Al2O3`` the factor 1.8895 actually represents - a
display-only change, the number is unchanged and composition is never saved).
This is pure analytics - the Compositions dialog only renders what this returns.
"""

from __future__ import annotations

import csv
import os
import re
from collections import OrderedDict
from itertools import chain

_CONV_CSV = os.path.join(
    os.path.dirname(__file__), os.pardir, "data", "composition_conversion.csv"
)
_SCAT_CSV = os.path.join(
    os.path.dirname(__file__), os.pardir, "data", "atomic_scattering_factors.csv"
)


def load_conversion_table(path: str | None = None) -> "OrderedDict[int, tuple[str, float]]":
    """``atom_nr -> (oxide_name, element->oxide wt% factor)``, in file order (so
    the reported oxide rows keep the old app's ordering). The first line is a
    comment header and is skipped, exactly as the old reader did."""
    table: "OrderedDict[int, tuple[str, float]]" = OrderedDict()
    with open(path or _CONV_CSV, "r", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)  # skip the header comment line
        for row in reader:
            if len(row) < 3:
                continue
            nr, name, factor = row[0], row[1], row[2]
            table[int(nr)] = (name, float(factor))
    return table


def reporting_oxides(conversion: dict | None = None) -> list[str]:
    """The distinct reporting oxides in table order (SiO2, Al2O3, Fe2O3, ...) -
    the oxide set the composition table and the non-clay oxide grid share."""
    conv = conversion if conversion is not None else load_conversion_table()
    order: list[str] = []
    for name, _factor in conv.values():
        if name not in order:
            order.append(name)
    return order


_ELEMENT_INFO: dict | None = None


def _element_info() -> dict:
    """``{element_symbol: (atom_nr, atomic_weight)}`` for the neutral atoms
    (charge 0) in the scattering CSV; cached."""
    global _ELEMENT_INFO
    if _ELEMENT_INFO is None:
        info: dict[str, tuple[int, float]] = {}
        with open(_SCAT_CSV, "r", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader, None) or []
            idx = {name.strip(): i for i, name in enumerate(header)}
            ni, nm, ch, wt = (idx.get("atom_nr", 0), idx.get("name", 1),
                              idx.get("charge", 2), idx.get("weight", 3))
            for row in reader:
                if len(row) <= wt or row[ch].strip() != "0":
                    continue
                info[row[nm].strip()] = (int(float(row[ni])), float(row[wt]))
        _ELEMENT_INFO = info
    return _ELEMENT_INFO


_FORMULA_TOKEN = re.compile(r"[A-Z][a-z]?|\d+\.?\d*|\(|\)|[.·*]")
# A '.' with digits on both sides: "Si2.5O8" (decimal subscript) and
# "Al2O3.2SiO2" (segment separator) are written identically, so the reading is
# genuinely ambiguous - see formula_dot_is_ambiguous.
_DIGIT_DOT_DIGIT = re.compile(r"\d\.\d")


def _formula_counts(formula: str, dot_as_separator: bool = False) -> dict:
    """Element counts from a chemical formula. Handles parentheses with a
    multiplier, a leading segment coefficient (``3CaO·Al2O3``) and hydrate /
    segment dots (``.``/``·``/``*`` followed by an optional multiplier).
    Unknown characters are skipped. Returns ``{element: count}``.

    A ``.`` BETWEEN DIGITS is read as a decimal point (``Fe0.5Mg0.5SiO3``), so
    ``Al2O3.2SiO2`` reads as ``Al2O3.2 SiO2``; pass ``dot_as_separator=True``
    (or write ``·``/``*``) for the segment reading."""
    if dot_as_separator:
        formula = (formula or "").replace(".", "·")
    tokens = _FORMULA_TOKEN.findall(formula or "")
    pos = 0

    def read_number() -> float:
        nonlocal pos
        if pos < len(tokens) and tokens[pos][0].isdigit():
            value = float(tokens[pos])
            pos += 1
            return value
        return 1.0

    def scaled(counts, factor) -> dict:
        if factor == 1.0:
            return counts
        return {el: c * factor for el, c in counts.items()}

    def parse_group(stop) -> dict:
        nonlocal pos
        counts: dict[str, float] = {}
        lead = read_number()   # a leading coefficient multiplies this segment
        while pos < len(tokens):
            tok = tokens[pos]
            if tok == stop:
                pos += 1
                return scaled(counts, lead)
            if tok == "(":
                pos += 1
                inner = parse_group(")")
                mult = read_number()
                for el, c in inner.items():
                    counts[el] = counts.get(el, 0.0) + c * mult
            elif tok in (".", "·", "*"):
                pos += 1
                # The segments after the dot parse themselves - each reads its
                # own leading coefficient (".2H2O", "·6SiO2"), so a multiplier
                # scales only its own segment, never the ones behind it.
                rest = parse_group(stop)
                counts = scaled(counts, lead)
                for el, c in rest.items():
                    counts[el] = counts.get(el, 0.0) + c
                return counts
            elif tok[0].isalpha():
                pos += 1
                counts[tok] = counts.get(tok, 0.0) + read_number()
            else:
                pos += 1                      # stray number: skip
        return scaled(counts, lead)

    return parse_group(None)


def parse_formula(formula: str, conversion: dict | None = None,
                  dot_as_separator: bool = False) -> dict:
    """Oxide wt% ``{oxide_name: %}`` from a chemical formula (e.g. ``NaAlSi3O8``,
    ``CaCO3``, ``CaMg(CO3)2``), normalised to 100%.

    Each element is converted to its reporting oxide via the same conversion
    table the composition uses (element mass x factor); elements outside that
    table (H, C, O, and cations without a reporting oxide such as Ti/Mn/S) are
    dropped, so only the reportable oxides appear. Returns ``{}`` when nothing
    convertible is found.

    ``dot_as_separator`` reads every ``.`` as a segment/hydrate separator
    (``K2O.Al2O3.6SiO2``) instead of a decimal point (``Fe0.5Mg0.5SiO3``) - the
    two are written identically, so the caller decides; ``formula_dot_is_ambiguous``
    says when it actually matters."""
    conv = conversion if conversion is not None else load_conversion_table()
    info = _element_info()
    masses: dict[str, float] = {}
    for element, count in _formula_counts(formula, dot_as_separator).items():
        if element not in info:
            continue
        atom_nr, weight = info[element]
        if atom_nr not in conv:
            continue  # element has no reporting oxide (dropped, like composition)
        oxide, factor = conv[atom_nr]
        masses[oxide] = masses.get(oxide, 0.0) + count * weight * factor
    total = sum(masses.values())
    if total <= 0:
        return {}
    return {oxide: 100.0 * mass / total for oxide, mass in masses.items()}


def formula_dot_is_ambiguous(formula: str, conversion: dict | None = None) -> bool:
    """True when the formula's ``.`` could be read either way AND the two
    readings give different oxides.

    ``Si2.5O8`` (decimal subscript) and ``Al2O3.2SiO2`` (segment separator) are
    the same token sequence, so a ``.`` between digits cannot be resolved from
    the text alone. Most inputs are unaffected either way - a hydrate such as
    ``CaSO4.2H2O`` reports the same oxides both ways, because the water is
    dropped - so this only flags the cases where the user has to choose (the
    oxide grid asks, and ``·``/``*`` are always unambiguous separators)."""
    if not _DIGIT_DOT_DIGIT.search(formula or ""):
        return False
    conv = conversion if conversion is not None else load_conversion_table()
    decimal = parse_formula(formula, conv)
    segment = parse_formula(formula, conv, dot_as_separator=True)
    return any(
        abs(decimal.get(oxide, 0.0) - segment.get(oxide, 0.0)) > 0.05
        for oxide in set(decimal) | set(segment)
    )


def _specimen_name(mixture, index: int) -> str:
    specimen = mixture.specimens[index] if index < len(mixture.specimens) else None
    if specimen is not None and getattr(specimen, "name", ""):
        return specimen.name
    return "Specimen %d" % (index + 1)


def mixture_composition(mixture, conversion: dict | None = None,
                        substitutes: dict | None = None):
    """The mixture's oxide composition.

    Returns ``(specimen_names, oxide_rows)`` where ``oxide_rows`` is a list of
    ``(oxide_name, [wt%_for_each_specimen])`` in the conversion table's order.
    Each specimen column is normalised to 100 wt% (0 when it has no convertible
    atoms). Mirrors the old ``get_composition_matrix`` computation without its
    byte-string packing.

    ``substitutes`` optionally maps ``{phase uuid: replacement phase}``, so a
    caller can ask what the composition WOULD be with different phases in the
    same slots - the mixture's own fractions are still used. That is how the
    "default state" column is produced: the phases as the catalog ships them,
    weighted by the fractions the fit actually found. Computing it here, through
    the same loop, is what guarantees the two columns are comparable; a separate
    implementation could drift from this one silently.
    """
    conv = conversion if conversion is not None else load_conversion_table()

    # Accumulate an element-weight total per specimen row.
    per_specimen: list[dict[int, float]] = []
    for row in mixture.phase_matrix:
        totals: dict[int, float] = {}
        for j, phase in enumerate(row):
            # Clay-only composition: only a structural `type == "Phase"` phase
            # contributes oxides. An empty cell, a raw-pattern accessory, or any
            # future non-clay structural phase is skipped, so its fraction is not
            # part of the per-specimen 100% (revisit this filter if a "bulk"
            # composition including accessories is ever wanted).
            if phase is None or getattr(phase, "type", None) != "Phase":
                continue
            if substitutes:
                phase = substitutes.get(phase.uuid, phase)
            components = phase.components
            if not components:
                continue  # a Phase with no atoms yet contributes nothing
            phase_fract = float(mixture.fractions[j]) if j < len(mixture.fractions) else 0.0
            weights = _component_weights(phase)
            for k, component in enumerate(components):
                comp_fract = (weights[k] if k < len(weights) else 0.0) * phase_fract
                for atom in chain(component.layer_atoms, component.interlayer_atoms):
                    atom_type = getattr(atom, "atom_type", None)
                    if atom_type is None:
                        continue
                    nr = atom_type.atom_nr
                    if nr in conv:
                        wt = atom.pn * atom_type.weight * comp_fract * conv[nr][1]
                        totals[nr] = totals.get(nr, 0.0) + wt
        per_specimen.append(totals)

    factors = [
        (100.0 / total if total else 0.0)
        for total in (sum(t.values()) for t in per_specimen)
    ]
    specimen_names = [_specimen_name(mixture, i) for i in range(len(per_specimen))]
    oxide_rows = [
        (oxide_name, [per_specimen[i].get(nr, 0.0) * factors[i]
                      for i in range(len(per_specimen))])
        for nr, (oxide_name, _factor) in conv.items()
    ]
    return specimen_names, oxide_rows


def _component_weights(phase):
    """The phase's per-component mean weight fractions (old ``mW``); an empty
    array when the phase has no probability model."""
    probs = getattr(phase, "probabilities", None)
    getter = getattr(probs, "get_distribution_array", None)
    return list(getter()) if callable(getter) else []


def _clay_oxide_masses(phase, conv) -> dict:
    """Oxide masses for one structural unit of a clay ``Phase`` (component-
    weighted): ``{oxide_name: mass}``. The same per-atom term
    ``mixture_composition`` uses, gathered for a single phase."""
    masses: dict[str, float] = {}
    weights = _component_weights(phase)
    for k, component in enumerate(phase.components):
        comp_weight = weights[k] if k < len(weights) else 0.0
        for atom in chain(component.layer_atoms, component.interlayer_atoms):
            atom_type = getattr(atom, "atom_type", None)
            if atom_type is None:
                continue
            nr = atom_type.atom_nr
            if nr in conv:
                oxide, factor = conv[nr]
                masses[oxide] = masses.get(oxide, 0.0) + (
                    atom.pn * atom_type.weight * comp_weight * factor)
    return masses


def mixture_has_nonclay(mixture) -> bool:
    """True when any cell holds a NonClayPhase (so a bulk composition, which
    includes it, differs from the clay-only one)."""
    return any(
        getattr(phase, "type", None) == "NonClayPhase"
        for row in mixture.phase_matrix for phase in row
    )


def bulk_composition(mixture, conversion: dict | None = None):
    """Bulk oxide composition INCLUDING non-clay phases.

    Each phase's own oxide composition, normalised to 100%, is weighted by its
    mixture fraction and summed - a semi-quantitative fraction-weighted average.
    The fractions are the same relative amounts the clay-only composition uses;
    they are NOT rigorous weight fractions (MudLab clays carry no ZMV), so this
    is semi-quantitative, exactly like the clay-only view. Clay ``Phase``s
    contribute from their atoms; ``NonClayPhase``s from their stored oxides;
    other types and empty cells are skipped.

    NOTE the two views weight differently, so even the CLAY-only oxides shift a
    little between them: ``mixture_composition`` weights each clay by fraction x
    its formula mass (the old app's per-atom sum), while this one normalises
    every phase to 100% first, so the fraction acts as a weight fraction. That
    is the price of putting clays (no molecular weight) and non-clays (oxides
    only) on one scale; a mass-weighted bulk would need per-phase molecular
    weights. On a real three-clay mixture the difference is ~1 wt% absolute.

    ADDITIVE: the clay-only ``mixture_composition`` and the XRF mass balance that
    reads it are unchanged - this is a separate view. Returns
    ``(specimen_names, oxide_rows)`` in reporting-oxide order, each specimen
    column normalised to 100 wt%."""
    conv = conversion if conversion is not None else load_conversion_table()
    order = reporting_oxides(conv)

    per_specimen: list[dict[str, float]] = []
    for row in mixture.phase_matrix:
        totals = {oxide: 0.0 for oxide in order}
        for j, phase in enumerate(row):
            if phase is None:
                continue
            frac = float(mixture.fractions[j]) if j < len(mixture.fractions) else 0.0
            if frac <= 0:
                continue
            ptype = getattr(phase, "type", None)
            if ptype == "Phase":
                vec = _clay_oxide_masses(phase, conv)
            elif ptype == "NonClayPhase":
                # Only the reporting oxides count, and they are filtered BEFORE
                # the per-phase total: an oxide outside the reporting set (only
                # reachable from a hand-edited .mud - the grid offers just these
                # seven) would otherwise shrink the phase's share of its own
                # fraction. The clay side is already reportable-only.
                vec = {str(k): float(v)
                       for k, v in (getattr(phase, "oxides", {}) or {}).items()
                       if str(k) in totals}
            else:
                continue  # raw-pattern accessory / unknown: no composition
            total = sum(vec.values())
            if total <= 0:
                continue
            for oxide, mass in vec.items():
                if oxide in totals:
                    totals[oxide] += frac * (100.0 * mass / total)  # per-phase norm
        per_specimen.append(totals)

    factors = [
        (100.0 / total if total else 0.0)
        for total in (sum(t.values()) for t in per_specimen)
    ]
    specimen_names = [_specimen_name(mixture, i) for i in range(len(per_specimen))]
    oxide_rows = [
        (oxide, [per_specimen[i][oxide] * factors[i]
                 for i in range(len(per_specimen))])
        for oxide in order
    ]
    return specimen_names, oxide_rows


def composition_to_csv(specimen_names, oxide_rows) -> str:
    """Render the composition as CSV text (header = specimen names)."""
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["", *specimen_names])
    for oxide_name, pcts in oxide_rows:
        writer.writerow([oxide_name, *("%.1f" % p for p in pcts)])
    return buffer.getvalue()
