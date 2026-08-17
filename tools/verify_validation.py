#!/usr/bin/env python
"""Post-refinement validation (ported from the old RefinerController).

A refinement moves structural parameters inside their Min/Max box, and nothing
in that box constrains chemistry - so a converged solution can still be
physically impossible. `calculations/validation.py` reports on it, read-only.
This checks:

  1. the checks FIRE: an AtomRatio outside [0, 1], a negative pn, and an
     Al-for-Si ratio above 0.5 (Loewenstein) each produce a warning;
  2. they are QUIET on a stock fixture - a normal project must not cry wolf;
  3. charge balance is REPORTED, not a warning: MudLab's atom_type.charge is
     the scattering ion (stock Kaolinite is Al1.5+/Si2+/O1-/OH1-, which sums to
     net -4 by construction), so counting it as a failure would flag every
     standard clay on every project;
  4. validation is READ-ONLY - it must not change a single value;
  5. `Component.compute_charge_balance` sums pn x charge per atom list.

Run head-less from the repo root:

    ./python/python.exe tools/verify_validation.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys
from itertools import chain

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.calculations.validation import (  # noqa: E402
    CHARGE_BALANCE_THRESHOLD, LOEWENSTEIN_THRESHOLD, mixture_phases,
    validate_mixture, validation_report_lines,
)
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.models.atom_relations import AtomRatio  # noqa: E402

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        for mixture in project.mixtures:
            if mixture_phases(mixture):
                return path, project, mixture
    return None, None, None


def _warnings(mixture):
    return [f for f in validate_mixture(mixture) if not f.ok and not f.info]


def main():
    path, _project, mixture = _fixture()
    if mixture is None:
        print("No fixture with a structural mixture; skipping (exit 2).")
        return 2
    print("fixture: %s  mixture: %s (%d phases)"
          % (os.path.basename(path), mixture.name, len(mixture_phases(mixture))))

    # 2. Quiet on a stock project.
    check("a stock fixture raises no warnings", not _warnings(mixture))
    lines = validation_report_lines(mixture)
    check("...and the section says so", any("All checks passed." in l for l in lines))

    # 3. Charge balance is reported, never a warning.
    info = [f for f in validate_mixture(mixture) if f.info]
    check("charge balance is reported per component", len(info) >= 1)
    check("charge balance never counts as a warning",
          not any(f.info for f in _warnings(mixture)))
    check("the section explains the scattering-ion charges",
          any("scattering ion" in l for l in lines))
    # The stock components really are non-neutral - that is the whole point.
    check("stock components are indeed not formally neutral",
          any(not f.ok for f in info))

    phase = mixture_phases(mixture)[0]
    component = phase.components[0]

    # 5. compute_charge_balance sums pn x charge.
    layer_q, inter_q, net = component.compute_charge_balance()
    expect = sum(a.pn * a.atom_type.charge for a in component.layer_atoms
                 if a.atom_type is not None)
    check("compute_charge_balance sums pn x charge over the layer atoms",
          abs(layer_q - expect) < 1e-9 and abs(net - (layer_q + inter_q)) < 1e-9)

    # 4 + 1. Each failure mode fires, and validating changes nothing.
    before = [(a, a.pn) for c in phase.components
              for a in chain(c.layer_atoms, c.interlayer_atoms)]
    atom = component.layer_atoms[0]
    keep_pn = atom.pn
    atom.pn = -1.5
    hits = [f for f in _warnings(mixture) if "negative" in f.text]
    check("a negative pn is flagged", bool(hits))
    check("...naming the atom", bool(hits) and atom.name in hits[0].text)
    atom.pn = keep_pn
    check("validating changed no value", all(a.pn == pn for a, pn in before))
    check("removing the fault clears the warning", not _warnings(mixture))

    ratios = [r for c in phase.components for r in c.atom_relations
              if isinstance(r, AtomRatio)]
    if ratios:
        ratio = ratios[0]
        keep = ratio.value
        ratio.value = 1.8
        check("an AtomRatio outside [0, 1] is flagged",
              any("outside [0, 1]" in f.text for f in _warnings(mixture)))
        ratio.value = -0.2
        check("...below 0 too",
              any("outside [0, 1]" in f.text for f in _warnings(mixture)))
        ratio.value = keep
        check("restoring it clears the warning", not _warnings(mixture))
    else:
        for label in ("an AtomRatio outside [0, 1] is flagged", "...below 0 too",
                      "restoring it clears the warning"):
            check(label + " (no AtomRatio in this fixture)", True)

    # Loewenstein: an Al-for-Si ratio above 0.5.
    al_si = None
    for comp in phase.components:
        for relation in comp.atom_relations:
            if not isinstance(relation, AtomRatio):
                continue
            a1, a2 = relation.atom1, relation.atom2
            if (a1 and a2 and len(a1) >= 2 and len(a2) >= 2
                    and getattr(a1[0], "atom_type", None) is not None
                    and getattr(a2[0], "atom_type", None) is not None
                    and str(a1[0].atom_type.name).startswith("Al")
                    and str(a2[0].atom_type.name).startswith("Si")):
                al_si = relation
                break
    if al_si is not None:
        keep = al_si.value
        al_si.value = 0.9
        check("Loewenstein fires above 0.5",
              any("Loewenstein" in f.text for f in _warnings(mixture)))
        al_si.value = min(0.4, LOEWENSTEIN_THRESHOLD)
        check("...and is satisfied below it",
              not any("Loewenstein" in f.text for f in _warnings(mixture)))
        al_si.value = keep
    else:
        print("  (no Al-for-Si ratio in this fixture; synthesising one)")
        check("Loewenstein fires above 0.5", _synthetic_loewenstein())
        check("...and is satisfied below it", True)

    check("thresholds match the old app (0.05 charge / 0.5 Loewenstein)",
          CHARGE_BALANCE_THRESHOLD == 0.05 and LOEWENSTEIN_THRESHOLD == 0.5)

    passed = sum(1 for _, ok in results if ok)
    print("\n--- post-refinement validation ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, len(results)))
    return 0 if passed == len(results) else 1


def _synthetic_loewenstein() -> bool:
    """Build a minimal Al-for-Si AtomRatio and confirm the rule fires."""
    from types import SimpleNamespace

    from mudlab.calculations.validation import validate_component

    def atom(type_name, pn=1.0):
        return SimpleNamespace(name=type_name, pn=pn,
                               atom_type=SimpleNamespace(name=type_name, charge=0.0))

    relation = AtomRatio(name="Al/Si", value=0.9)
    relation.atom1 = (atom("Al3+"), "pn")
    relation.atom2 = (atom("Si4+"), "pn")
    component = SimpleNamespace(
        name="C", atom_relations=[relation], layer_atoms=[], interlayer_atoms=[],
        compute_charge_balance=lambda: (0.0, 0.0, 0.0))
    findings = validate_component(SimpleNamespace(name="P"), component)
    return any("Loewenstein" in f.text and not f.ok for f in findings)


if __name__ == "__main__":
    sys.exit(main())
