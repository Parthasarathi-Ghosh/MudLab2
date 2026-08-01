#!/usr/bin/env python
"""Batch 2 of snapshot-on-detach: Component.snapshot_inherited().

Treatment variants share their clay layers across phases by COMPONENT LINKING
(e.g. the glycolated phase's Illite is linked_with the air-dried phase's Illite
and inherits its atoms). Deleting the base phase severs that link, so without a
snapshot the dependant reverts to its own (stale/empty) atoms and its calculated
pattern jumps. snapshot_inherited() bakes the resolved values into own storage
first - sharing the template's atom objects so the component's own relation->atom
references stay valid.

On a freshly saved .mud the dependant's own values already equal the inherited
ones, so the shift only appears once the base has been EDITED after linking (the
"edit the base, then delete it" workflow). Each check therefore edits the
template first to force the divergence, then verifies:

  - the child's resolved values track the edited template (inheritance works),
    and diverge from the child's stale own values;
  - snapshot() bakes the edited resolved values into own storage (atoms shared,
    identity kept) and clears the inherit flags, so unlink preserves them;
  - unlinking WITHOUT the snapshot reverts to the stale own values (the bug);
  - END TO END: a specimen's calculated pattern is preserved across
    snapshot+unlink, but shifts when unlinked without the snapshot;
  - a component that inherits nothing is a no-op.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_snapshot_component.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication

from mudlab.file_parsers.mud_project import load_mud

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _linked_component(project):
    """A (phase, component) where the component links a template and inherits
    its layer atoms - the structural case that matters."""
    for phase in project.phases:
        for comp in getattr(phase, "components", []):
            if comp.linked_with is not None and comp.inherit_layer_atoms:
                return phase, comp
    return None, None


def _find_fixture():
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        phase, comp = _linked_component(load_mud(path))
        if comp is not None:
            return path
    return None


PATH = _find_fixture()
if PATH is None:
    print("No fixture with a linked, layer-atom-inheriting component; skip (exit 2).")
    raise SystemExit(2)


def _scalars(c):
    return (round(c.cell_a, 12), round(c.cell_b, 12), round(c.d001, 12),
            round(c.default_c, 12), round(c.delta_c, 12), round(c.lattice_d, 12))


def _atom_ids(c):
    return ([id(a) for a in c.layer_atoms], [id(a) for a in c.interlayer_atoms])


def _edit_template(t):
    """Perturb every scalar a linked child inherits, so the child's resolved
    values diverge from its stale own values (simulates editing the base)."""
    t._d001 += 0.30
    t._default_c += 0.30
    t._delta_c += 0.05
    t._lattice_d += 0.02
    t._ucp_a.value += 0.05
    t._ucp_b.value += 0.05


def _specimen_using(project, phase):
    """A specimen whose mixture slot holds `phase`, and its mixture."""
    for mix in project.mixtures:
        for i, spec in enumerate(mix.specimens):
            if spec is not None and phase in mix.phase_matrix[i]:
                return mix, spec
    return None, None


def main():
    phase, comp = _linked_component(load_mud(PATH))
    print("fixture: %s  (phase %r, linked component %r)"
          % (os.path.basename(PATH), phase.name, comp.name))

    # --- Component-level invariance across snapshot + unlink ----------
    # (edit the template first so the child's resolved values diverge from its
    # stale own values - otherwise a freshly-loaded child's own == resolved.)
    project = load_mud(PATH)
    _, comp = _linked_component(project)
    own_before = _scalars(comp)                 # own == resolved on load
    _edit_template(comp.linked_with)
    resolved_edited = _scalars(comp)            # now reads the edited template
    before_ids = _atom_ids(comp)
    check("setup: child resolved values track the edited template",
          resolved_edited != own_before)

    baked = comp.snapshot_inherited()
    check("snapshot: reports it baked something", baked is True)
    check("snapshot: all inherit flags cleared",
          not any([comp.inherit_ucp_a, comp.inherit_ucp_b, comp.inherit_d001,
                   comp.inherit_default_c, comp.inherit_delta_c,
                   comp.inherit_layer_atoms, comp.inherit_interlayer_atoms,
                   comp.inherit_atom_relations]))
    comp.set_linked_with(None)
    check("unlink: linked_with cleared", comp.linked_with is None)
    check("invariance: snapshot kept the EDITED resolved values (not stale own)",
          _scalars(comp) == resolved_edited)
    check("invariance: atom objects shared (identity kept)", _atom_ids(comp) == before_ids)

    # Contrast: unlink WITHOUT snapshot reverts to the stale own values.
    project = load_mud(PATH)
    _, comp2 = _linked_component(project)
    own2 = _scalars(comp2)
    _edit_template(comp2.linked_with)
    comp2.set_linked_with(None)  # no snapshot
    check("contrast: unlink without snapshot reverts to stale own values",
          _scalars(comp2) == own2 and _scalars(comp2) != resolved_edited)

    # --- END TO END: a specimen's calculated pattern ------------------
    def _pattern_after(snapshot: bool):
        project = load_mud(PATH)
        phase, _ = _linked_component(project)
        mix, spec = _specimen_using(project, phase)
        if mix is None:
            return None, None
        for c in phase.components:            # edit every linked template
            if c.linked_with is not None:
                _edit_template(c.linked_with)
        mix.calculate()
        edited = spec.calculated_pattern[1].copy()
        for c in phase.components:
            if c.linked_with is not None:
                if snapshot:
                    c.snapshot_inherited()
                c.set_linked_with(None)
        mix.calculate()
        return edited, spec.calculated_pattern[1]

    edited, after_snap = _pattern_after(snapshot=True)
    if edited is not None:
        check("end-to-end: pattern preserved after snapshot+unlink",
              after_snap.shape == edited.shape and np.allclose(after_snap, edited))
        _, after_plain = _pattern_after(snapshot=False)
        check("end-to-end: pattern SHIFTS when unlinked without snapshot",
              not np.allclose(after_plain, edited))
    else:
        print("  (no specimen uses the linked phase; skipped the pattern checks)")

    # --- No-op on a component that inherits nothing -------------------
    project = load_mud(PATH)
    plain = None
    for ph in project.phases:
        for c in getattr(ph, "components", []):
            if c.linked_with is None:
                plain = c
                break
        if plain is not None:
            break
    if plain is not None:
        before = _scalars(plain), _atom_ids(plain)
        did = plain.snapshot_inherited()
        after = _scalars(plain), _atom_ids(plain)
        check("no-op: snapshot on an unlinked component reports nothing baked",
              did is False)
        check("no-op: its values are unchanged", before == after)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- snapshot-on-detach (component) verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
