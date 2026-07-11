#!/usr/bin/env python
"""Durable save/load round-trip harness for the .mud persistence path.

Complements tools/verify_calc_engine.py (which guards the *calc* path) by
guarding the *serialization* path - the Mixture/Phase/Component/Atom
to_dict work behind the editors. For each sample project it runs three
checks:

  A. Unedited round-trip is loss-free: load -> save -> reload leaves the
     modeled parts (atom_types, phases, mixtures) JSON-equal to the
     original file. Catches an accidental rewrite / dropped field.

  B. Edited fields survive: a representative edit to every editable model
     field (mixture fractions/scales/bg/name; phase name/sigma*/CSDS mean/
     R0 F param; component d001/default_c/delta_c/name; atom pn/name/
     element) is written, saved, reloaded and read back unchanged.

  C. The round-trip does not perturb the calculation: the calculated
     pattern recomputed after a plain load -> save -> reload matches the
     pattern computed before saving.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_roundtrip.py
    ./python/python.exe tools/verify_roundtrip.py "a.mud" "b.mud"

No QApplication needed (the models are plain QObjects). Exit codes:
0 = all checks pass, 1 = a regression, 2 = no sample projects found.

The default samples live in tools/sample_projects/ (gitignored, see that
folder's README), with a fallback to ~/Downloads.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile

import numpy as np

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402

_FIXTURES = os.path.join(_REPO, "tools", "sample_projects")

# Parts written from live models (the ones a round-trip must reproduce).
_MODELED_PARTS = ("atom_types", "phases", "mixtures")


def _default_projects():
    projects = []
    for name in ("308 r1.mud", "Dh2040A.mud"):
        in_repo = os.path.join(_FIXTURES, name)
        downloads = os.path.join(os.path.expanduser("~"), "Downloads", name)
        projects.append(in_repo if os.path.isfile(in_repo) else downloads)
    return projects


def _part(path, name):
    with zipfile.ZipFile(path) as archive:
        if name not in archive.namelist():
            return None
        return json.loads(archive.read(name).decode("utf-8"))


def _save_reload(project):
    tmp = os.path.join(tempfile.gettempdir(), "mudlab_rt_%d.mud" % os.getpid())
    save_mud(project, tmp)
    reloaded = load_mud(tmp)
    return tmp, reloaded


def _cleanup(tmp):
    for path in (tmp, tmp + "~"):
        if os.path.exists(path):
            os.remove(path)


def _first_phase_with_g(project, g_min):
    for phase in project.phases:
        if phase.G >= g_min:
            return phase
    return None


def _patterns(project):
    project.calculate()
    return [
        (s.uuid, s.calculated_pattern[1].copy())
        for s in project.specimens
        if s.has_calculated_data
    ]


# ----------------------------------------------------------------------
def check_unedited(path, results):
    """A. load -> save -> reload keeps the modeled parts JSON-equal."""
    project = load_mud(path)
    tmp, _ = _save_reload(project)
    try:
        for part in _MODELED_PARTS:
            before, after = _part(path, part), _part(tmp, part)
            ok = before == after
            results.append(("A unedited %-10s json-equal" % part, ok))
    finally:
        _cleanup(tmp)


def check_edited(path, results):
    """B. every editable field survives a round-trip."""
    project = load_mud(path)
    expected = {}

    if project.mixtures:
        mix = project.mixtures[0]
        if len(mix.fractions):
            mix.fractions[0] = 0.4242
            expected["mixture.fractions[0]"] = (mix, "fractions", 0, 0.4242)
        if len(mix.scales):
            mix.scales[0] = 0.1234
            expected["mixture.scales[0]"] = (mix, "scales", 0, 0.1234)
        if len(mix.bgshifts):
            mix.bgshifts[0] = 7.77
            expected["mixture.bgshifts[0]"] = (mix, "bgshifts", 0, 7.77)
        mix.name = "RT Mix"
        expected["mixture.name"] = (mix, "name", None, "RT Mix")

    phase = project.phases[0] if project.phases else None
    if phase is not None:
        phase.name = "RT Phase"
        phase.sigma_star = 4.44
        phase.CSDS.average = 21.0
        comp = phase.components[0] if phase.components else None
        if comp is not None:
            comp.d001 = 1.234
            comp.default_c = 1.222
            comp.delta_c = 0.011
            comp.name = "RT Comp"
            if comp.layer_atoms:
                comp.layer_atoms[0].pn = 3.5
                comp.layer_atoms[0].name = "RTx"

    g2 = _first_phase_with_g(project, 2)
    if g2 is not None:
        g2.probabilities.set_f(0, 0.61)

    # An atom-type (element) swap: point the first layer atom at a different
    # project atom type and check the uuid survives.
    swapped_uuid = None
    if phase is not None and phase.components and phase.components[0].layer_atoms:
        atom = phase.components[0].layer_atoms[0]
        for atom_type in project.atom_types:
            if atom_type is not atom.atom_type:
                atom.atom_type = atom_type
                swapped_uuid = atom_type.uuid
                break

    espec = project.specimens[0] if project.specimens else None
    if espec is not None:
        espec.set_exclusion_ranges([(9.9, 10.1), (20.0, 21.0)])

    tmp, reloaded = _save_reload(project)
    try:
        # Scalar-field survival.
        for label, (obj, attr, index, want) in expected.items():
            got = getattr(_locate(reloaded, obj, project), attr)
            if index is not None:
                got = got[index]
            results.append((
                "B %-22s survives" % label,
                np.isclose(got, want) if isinstance(want, float) else got == want,
            ))

        rspec = reloaded.specimens[0] if reloaded.specimens else None
        if rspec is not None:
            _check(results, "B specimen.exclusion_ranges survives",
                   list(rspec.exclusion_ranges) == [(9.9, 10.1), (20.0, 21.0)])

        rphase = reloaded.phases[0] if reloaded.phases else None
        if rphase is not None:
            _check(results, "B phase.name", rphase.name == "RT Phase")
            _check(results, "B phase.sigma_star", np.isclose(rphase.sigma_star, 4.44))
            _check(results, "B phase.CSDS.average", np.isclose(rphase.CSDS.average, 21.0))
            rcomp = rphase.components[0] if rphase.components else None
            if rcomp is not None:
                _check(results, "B component.d001", np.isclose(rcomp.d001, 1.234))
                _check(results, "B component.default_c", np.isclose(rcomp.default_c, 1.222))
                _check(results, "B component.delta_c", np.isclose(rcomp.delta_c, 0.011))
                _check(results, "B component.name", rcomp.name == "RT Comp")
                if rcomp.layer_atoms:
                    _check(results, "B atom.pn", np.isclose(rcomp.layer_atoms[0].pn, 3.5))
                    _check(results, "B atom.name", rcomp.layer_atoms[0].name == "RTx")
                    if swapped_uuid is not None:
                        at = rcomp.layer_atoms[0].atom_type
                        _check(results, "B atom.element",
                               at is not None and at.uuid == swapped_uuid)

        rg2 = _first_phase_with_g(reloaded, 2)
        if rg2 is not None:
            _check(results, "B probabilities.F1",
                   np.isclose(rg2.probabilities.f_value(0), 0.61))
    finally:
        _cleanup(tmp)


def check_calc_stable(path, results):
    """C. the calculated pattern is unchanged by a plain round-trip."""
    before = dict(_patterns(load_mud(path)))
    tmp, reloaded = _save_reload(load_mud(path))
    try:
        after = dict(_patterns(reloaded))
        if not before:
            results.append(("C calc pattern (no mixture to compute)", True))
            return
        ok = True
        for uuid, pattern in before.items():
            other = after.get(uuid)
            ok = ok and other is not None and np.allclose(pattern, other, atol=1e-9)
        results.append(("C calc pattern unchanged by round-trip", ok))
    finally:
        _cleanup(tmp)


def _locate(reloaded, obj, original):
    """Map an edited model in the ORIGINAL project to its counterpart in the
    RELOADED one (only mixtures are located here; index 0 is enough)."""
    if obj in original.mixtures and reloaded.mixtures:
        return reloaded.mixtures[0]
    return obj


def _check(results, label, ok):
    results.append((label, bool(ok)))


# ----------------------------------------------------------------------
def check_project(path):
    print("=" * 72)
    print(os.path.basename(path))
    results = []
    check_unedited(path, results)
    check_edited(path, results)
    check_calc_stable(path, results)
    failed = 0
    for label, ok in results:
        print("  %s  %s" % ("PASS" if ok else "FAIL", label))
        failed += not ok
    return len(results), failed


def main(argv):
    projects = argv[1:] or _default_projects()
    total = failed = 0
    missing = 0
    for path in projects:
        if not os.path.isfile(path):
            print("SKIP (not found): %s" % path)
            missing += 1
            continue
        checked, fail = check_project(path)
        total += checked
        failed += fail
    print("=" * 72)
    if total == 0:
        print("NOTHING VERIFIED - no sample projects were found.")
        return 2
    print("Ran %d round-trip checks across %d project(s): %d passed, %d FAILED"
          % (total, len(projects) - missing, total - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
