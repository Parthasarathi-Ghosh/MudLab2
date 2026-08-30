#!/usr/bin/env python
"""Deriving the glycolated and heated states of a clay from its air-dried one.

A CIF is one structure in one state, and nobody deposits a second refinement of
the same sample after glycol solvation - so the treated states a clay workflow
needs have to be BUILT. They can be, because a treatment changes the gallery
between layers, not the layer itself: MudLab's six shipped Di-Smectite states
carry the identical ten layer atoms and differ only in `d001` and
`interlayer_atoms`.

The check that matters is the transplant. A shipped 2:1 layer tops out at 0.654
nm and an imported one at 0.671; copying interlayer heights verbatim would push
the guests into the layer beneath. What must carry across is the GALLERY - the
repeat less the layer - so the derived state has the donor's gallery sitting on
its own layer, and a basal spacing that differs from the donor's by exactly the
layer-thickness difference.

Corpus-free: the base component is built in code, so this runs anywhere.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_treatment_states.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab import treatment_variants as tv  # noqa: E402
from mudlab.file_parsers.atom_type_library import atom_type_library_map  # noqa: E402
from mudlab.file_parsers.default_catalog import (  # noqa: E402
    build_catalog_entry_by_name,
)
from mudlab.models.phase import Phase  # noqa: E402
from mudlab.models.project import Project  # noqa: E402

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def phase_from(name: str, phase_name: str):
    """A single-component phase built from a shipped catalog entry."""
    source = build_catalog_entry_by_name(name)[0]
    phase = Phase(name=phase_name)
    phase.components = [source.components[0]]
    return phase


def main():  # noqa: C901 - a checklist
    library = atom_type_library_map()

    # ------------------------------------------------------ what is refused
    kaolinite = phase_from("Kaolinite", "K")
    possible, why = tv.can_derive(kaolinite)
    check("a 1:1 clay is refused - it has no gallery to fill", not possible
          and "1:1" in why)
    check("...and the refusal explains why", "swell" in why or "glycol" in why)

    two_components = Phase(name="two")
    two_components.components = list(
        build_catalog_entry_by_name("Illite")[0].components) * 2
    possible, why = tv.can_derive(two_components)
    check("a multi-component phase is refused", not possible and "ONE" in why)
    check("no phase at all is refused", not tv.can_derive(None)[0])

    illite = phase_from("Illite", "Illite 0005015")
    check("a 2:1 clay is accepted", tv.can_derive(illite)[0])

    # -------------------------------------------------------- the transplant
    base = illite.components[0]
    donor = tv.shipped_state("Di-Smectite", "2GLY", library)
    check("a shipped state loads (%s)" % (donor and donor.name), donor is not None)
    base_top = tv.layer_top(base)
    donor_gallery = tv.gallery_height(donor)

    variant = tv.transplant_gallery(base, donor, library)
    check("the derived state keeps the donor's gallery exactly "
          "(%.4f vs %.4f nm)" % (tv.gallery_height(variant), donor_gallery),
          abs(tv.gallery_height(variant) - donor_gallery) < 1e-9)
    check("...on its OWN layer, so the layer top is unchanged (%.4f nm)"
          % tv.layer_top(variant),
          abs(tv.layer_top(variant) - base_top) < 1e-9)
    expected = base_top + donor_gallery
    check("...giving d001 = layer + gallery (%.4f nm)" % variant.d001,
          abs(variant.d001 - expected) < 1e-9)
    check("...which differs from the donor's by the layer difference "
          "(%.4f nm)" % (variant.d001 - donor.d001),
          abs((variant.d001 - donor.d001)
              - (base_top - tv.layer_top(donor))) < 1e-9)
    check("...and default_c follows d001",
          abs(variant.default_c - variant.d001) < 1e-9)

    check("the gallery species come from the donor (%d rows)"
          % len(variant.interlayer_atoms),
          len(variant.interlayer_atoms) == len(donor.interlayer_atoms)
          and len(variant.interlayer_atoms) > 0)
    check("...no guest is left inside the layer",
          all(a.default_z > base_top - 1e-9 for a in variant.interlayer_atoms))
    unresolved = [a.name for a in variant.layer_atoms + variant.interlayer_atoms
                  if a.atom_type is None]
    check("...and every atom still resolves to a scattering factor%s"
          % ("" if not unresolved else " -> %s" % unresolved), not unresolved)

    # Nothing may be shared by identity with the component it came from, or the
    # two would alias on save.
    base_ids = {a.uuid for a in base.layer_atoms + base.interlayer_atoms}
    new_ids = {a.uuid for a in variant.layer_atoms + variant.interlayer_atoms}
    check("the derived component has its own identity",
          variant.uuid != base.uuid and not (base_ids & new_ids))
    # ...but the atom TYPES are the project's, not copies of them.
    shared = [a for a in variant.layer_atoms
              if a.atom_type is not None
              and a.atom_type is library.get(a.atom_type.name)]
    check("...while its atom types are the project's own objects, not clones",
          len(shared) == len([a for a in variant.layer_atoms
                              if a.atom_type is not None]))

    # ------------------------------------------------------- the whole series
    project = Project()
    series = phase_from("Illite", "Illite 0005015")
    project.add_phase(series)
    created = tv.derive(project, series, "Di-Smectite", "1WAT", library)
    check("deriving makes the two treated phases (%s)"
          % ", ".join(p.name for p in created), len(created) == 2)
    check("...named for their treatment",
          any(p.name.endswith("-EG") for p in created)
          and any(p.name.endswith("-350") for p in created))
    check("...and they join the project (%d phases)" % len(project.phases),
          len(project.phases) == 3)

    glycol = next(p for p in created if p.name.endswith("-EG"))
    heated = next(p for p in created if p.name.endswith("-350"))
    check("the glycolated state is the most expanded (%.3f > %.3f > %.3f nm)"
          % (glycol.components[0].d001, series.components[0].d001,
             heated.components[0].d001),
          glycol.components[0].d001 > heated.components[0].d001)

    for phase in created:
        component = phase.components[0]
        check("%s links its component to the base" % phase.name,
              component.linked_with is series.components[0])
        check("%s inherits the layer rather than owning it" % phase.name,
              all(getattr(component, flag) for flag in tv.INHERIT_FROM_BASE))
        check("%s keeps its OWN gallery" % phase.name,
              not component.inherit_interlayer_atoms
              and not component.inherit_default_c)
        check("%s is based on the air-dried phase" % phase.name,
              getattr(phase, "based_on", None) is series)

    # The point of linking: refine the layer once and the series follows.
    moved = series.components[0].layer_atoms[0]
    original = moved.default_z
    moved.default_z = original + 0.05
    followed = glycol.components[0].layer_atoms[0].default_z
    check("moving an atom in the base moves it in the derived states too "
          "(%.4f -> %.4f)" % (original, followed),
          abs(followed - (original + 0.05)) < 1e-9)
    moved.default_z = original

    # ----------------------------------------------------------- the way in
    import mudlab.edit_phases_dialog as epd

    source = open(epd.__file__, encoding="utf-8").read()
    check("Edit Phases offers it on the phase list",
          "Create treatment states" in source
          and "_on_create_treatment_states" in source)

    from mudlab.treatment_states_dialog import TreatmentStatesDialog

    chooser = TreatmentStatesDialog(None, phase=series)
    check("the chooser offers every shipped family (%d)"
          % chooser.cmb_family.count(),
          chooser.cmb_family.count() == len(tv.FAMILIES))
    check("...and every hydration state (%d)" % chooser.cmb_state.count(),
          chooser.cmb_state.count() == len(tv.STATES))
    check("...returning keys the deriver understands",
          chooser.family() in tv.FAMILIES
          and chooser.base_state() in dict(tv.STATES))

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Treatment states derived from an air-dried clay")
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
