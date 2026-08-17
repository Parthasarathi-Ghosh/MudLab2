"""Post-refinement physical validation of a mixture's phases (read-only).

Ported from the old app's ``RefinerController._build_validation_report``, which
appended these checks to the refinement report. A refinement moves structural
parameters within their Min/Max box, and nothing in that box constrains
chemistry - so a converged solution can still be physically impossible. These
checks say so instead of letting a nonsense model look like a good fit.

Three checks per component:

  1. **AtomRatio range** - a substituting fraction must lie in [0, 1]; outside
     it the relation produces a negative ``pn``.
  2. **Loewenstein's rule** - for an Al-for-Si substitution, Al/(Al+Si) in the
     tetrahedral sheet may not exceed 0.5 (no Al-O-Al linkages).
  3. **Charge balance** - layer + interlayer charge per unit cell should cancel
     to within ``CHARGE_BALANCE_THRESHOLD``.
  Plus a direct scan for negative ``pn`` on any atom.

NOTHING here mutates the model: it reads the state left by whichever solution
the user kept. Pure analytics, so it is testable head-less and reusable outside
the refinement dialog.
"""

from __future__ import annotations

from itertools import chain

from mudlab.models.atom_relations import AtomRatio

#: Largest |net charge| per unit cell still considered balanced.
CHARGE_BALANCE_THRESHOLD = 0.05
#: Largest Al/(Al+Si) tetrahedral substitution allowed by Loewenstein's rule.
LOEWENSTEIN_THRESHOLD = 0.5


class Finding:
    """One validation result. ``ok`` False means it is a warning; ``info`` marks
    a reported measurement that must NOT count as a warning (see the
    charge-balance note in ``component_charge_balance_finding``)."""

    __slots__ = ("ok", "text", "info")

    def __init__(self, ok: bool, text: str, info: bool = False) -> None:
        self.ok = bool(ok)
        self.text = text
        self.info = bool(info)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        kind = "info" if self.info else ("ok" if self.ok else "WARN")
        return "<Finding %s %r>" % (kind, self.text)


def mixture_phases(mixture) -> list:
    """The distinct structural phases in a mixture's grid, in encounter order.

    ``phase_matrix`` is a specimens x slots grid that repeats the same phase
    object across specimen rows, and can hold raw / non-clay phases with no
    components at all - so identity-deduplicate and keep only what has
    components to validate."""
    phases, seen = [], set()
    for row in getattr(mixture, "phase_matrix", None) or []:
        for phase in row or []:
            if phase is None or not hasattr(phase, "components"):
                continue
            if id(phase) not in seen:
                seen.add(id(phase))
                phases.append(phase)
    return phases


def _is_al_for_si(relation) -> bool:
    """True when the relation substitutes Al for Si on the same site, i.e. the
    case Loewenstein's rule governs."""
    a1, a2 = relation.atom1, relation.atom2
    if not (a1 and a2 and len(a1) >= 2 and len(a2) >= 2):
        return False
    if a1[1] != "pn" or a2[1] != "pn":
        return False
    t1 = getattr(a1[0], "atom_type", None)
    t2 = getattr(a2[0], "atom_type", None)
    if t1 is None or t2 is None:
        return False
    return str(t1.name).startswith("Al") and str(t2.name).startswith("Si")


def validate_component(phase, component) -> list:
    """The findings for one component of one phase."""
    label = "%s / %s" % (getattr(phase, "name", "?"),
                         getattr(component, "name", "?"))
    findings = []

    for relation in component.atom_relations:
        if not isinstance(relation, AtomRatio):
            continue
        value = float(relation.value)
        where = "[%s] Relation '%s'" % (label, relation.name)
        if not 0.0 <= value <= 1.0:
            findings.append(Finding(False, "%s: value=%.4f is outside [0, 1] - "
                                           "negative pn produced." % (where, value)))
        else:
            findings.append(Finding(True, "%s: value=%.4f in [0, 1]" % (where, value)))
        if _is_al_for_si(relation):
            if value > LOEWENSTEIN_THRESHOLD:
                findings.append(Finding(
                    False, "%s: value=%.4f exceeds %.1f - Loewenstein's rule "
                           "violated (Al-O-Al)." % (where, value, LOEWENSTEIN_THRESHOLD)))
            else:
                findings.append(Finding(
                    True, "%s: Loewenstein satisfied (%.4f <= %.1f)"
                          % (where, value, LOEWENSTEIN_THRESHOLD)))

    for atom in chain(component.layer_atoms, component.interlayer_atoms):
        if float(atom.pn) < 0.0:
            findings.append(Finding(
                False, "[%s] Atom '%s': pn=%.5f is negative."
                       % (label, atom.name, atom.pn)))

    findings.append(component_charge_balance_finding(label, component))
    return [f for f in findings if f is not None]


def component_charge_balance_finding(label: str, component):
    """Charge balance as an INFORMATION line, not a warning.

    The old app treated |net| > 0.05 as a warning. That is unusable with the
    bundled components, because MudLab's `atom_type.charge` is the SCATTERING
    ion of the atom type, not a formal charge: stock Kaolinite is built from
    Al1.5+, Si2+, O1- and OH1-, which sum to net -4 by construction. Every
    standard clay would therefore be flagged on every project, refined or not,
    which buries the checks that do mean something (a refinement CAN drive an
    AtomRatio out of [0, 1], break Loewenstein, or make a pn negative - the
    charge sum it cannot meaningfully change). So the number is still reported,
    per component, and still marked balanced/imbalanced against
    CHARGE_BALANCE_THRESHOLD - it just does not count towards the verdict. Set
    `info=False` below to restore the old app's strict behaviour."""
    try:
        layer_q, inter_q, net = component.compute_charge_balance()
    except Exception:  # noqa: BLE001 - a malformed component must not break the report
        return None
    balanced = abs(net) <= CHARGE_BALANCE_THRESHOLD
    # Kept short: this line is tabular, and the report box is a narrow column.
    short = label if len(label) <= 26 else label[:25] + "…"
    return Finding(
        balanced,
        "%-26s net %+.3f  (L %+.3f I %+.3f)" % (short, net, layer_q, inter_q),
        info=True,
    )


def validate_mixture(mixture) -> list:
    """Every finding for every component of every structural phase in the
    mixture. Read-only: call it after a solution has been applied."""
    findings = []
    for phase in mixture_phases(mixture):
        for component in phase.components:
            findings.extend(validate_component(phase, component))
    return findings


def validation_report_lines(mixture, width: int = 64) -> list:
    """The findings rendered as the report's validation section (the old app's
    layout: warnings first, then the passed checks, then a verdict)."""
    sep = "=" * width
    lines = [sep, "  Post-refinement validation  (read-only)", sep, ""]
    findings = validate_mixture(mixture)
    warnings = [f for f in findings if not f.ok and not f.info]
    passed = [f for f in findings if f.ok and not f.info]
    reported = [f for f in findings if f.info]

    if warnings:
        lines.append("  WARNINGS:")
        lines.extend("  [!] " + f.text for f in warnings)
        lines.append("")
    if passed:
        lines.append("  Passed checks:")
        lines.extend("      " + f.text for f in passed)
        lines.append("")
    if reported:
        lines.append("  Charge balance (reported, not a pass/fail - the atom")
        lines.append("  types carry scattering ion charges, e.g. Al1.5+/O1-):")
        lines.extend("      " + f.text for f in reported)
        lines.append("")
    if not findings:
        lines.append("  No components to validate.")
        lines.append("")

    if warnings:
        lines.append("  %d warning(s) above - values were NOT changed by this "
                     "check." % len(warnings))
    else:
        lines.append("  All checks passed.")
    lines.append(sep)
    return lines
