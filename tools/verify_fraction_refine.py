#!/usr/bin/env python
"""Batch 1 of the per-phase fraction refine flag (old app: fractions_mask).

Each phase slot can be flagged refine / fixed for the mixture Optimize. The model
stores it in raw_properties["fractions_mask"] (1 = refine) and the optimiser
already honours it; this covers the new Mixture API and the end-to-end behaviour:

  - fraction_refine defaults True (absent/short mask = all-free, matching the
    engine); set_fraction_refine creates + writes the mask so it persists;
  - the mask round-trips through to_dict/from_dict and stays the right length as
    phase slots are added / removed;
  - a length-drifted / garbage mask off disk is healed on load (from_dict) so it
    always matches the phase count - the optimiser reads it by index;
  - a FIXED fraction stays exactly put through optimise, while a free one is
    refined (and the whole vector still sums to 1).

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_fraction_refine.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np
from PySide6.QtWidgets import QApplication

from mudlab.calculations.mixture import optimize_mixture
from mudlab.file_parsers.mud_project import load_mud, save_mud
from mudlab.models.mixture import Mixture

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in [os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")] + \
            sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        if not os.path.isfile(path):
            continue
        project = load_mud(path)
        if project.mixtures and project.mixtures[0].m >= 2:
            return path, project
    return None, None


PATH, PROJECT = _fixture()
if PROJECT is None:
    print("No fixture with a >=2-slot mixture; skipping (exit 2).")
    raise SystemExit(2)


def main():
    mix = PROJECT.mixtures[0]
    print("fixture: %s  (%d phase slots)" % (os.path.basename(PATH), mix.m))

    # --- API (relative to the fixture's own initial mask, which may fix slots) ---
    mix.set_fraction_refine(0, False)
    check("set False: slot 0 no longer refines", not mix.fraction_refine(0))
    mix.set_fraction_refine(0, True)
    check("set True: slot 0 refines again", mix.fraction_refine(0))
    check("set writes a full-length mask",
          isinstance(mix.raw_properties.get("fractions_mask"), list)
          and len(mix.raw_properties["fractions_mask"]) == mix.m)
    # Toggling one slot leaves the others' refine state alone (baseline captured
    # right before the isolated toggle).
    baseline = [mix.fraction_refine(j) for j in range(mix.m)]
    mix.set_fraction_refine(mix.m - 1, not baseline[mix.m - 1])
    check("toggle: only the touched slot changes",
          [mix.fraction_refine(j) for j in range(mix.m - 1)] == baseline[:mix.m - 1])

    # --- round-trip: explicit known states survive save/reload ---
    proj2 = load_mud(PATH)
    m2 = proj2.mixtures[0]
    m2.set_fraction_refine(0, False)
    m2.set_fraction_refine(1, True)
    tmp = os.path.join(tempfile.mkdtemp(), "fr.mud")
    save_mud(proj2, tmp)
    back = load_mud(tmp).mixtures[0]
    check("round-trip: fixed slot 0 survives save/reload", not back.fraction_refine(0))
    check("round-trip: refined slot 1 survives save/reload", back.fraction_refine(1))

    # --- slot add / remove keep the mask aligned ---
    m3 = load_mud(PATH).mixtures[0]
    m3.set_fraction_refine(0, False)  # create the mask
    j = m3.add_phase_slot("Extra")
    check("add slot: mask grew and the new slot refines",
          len(m3.raw_properties["fractions_mask"]) == m3.m and m3.fraction_refine(j))
    m3.del_phase_slot(0)  # remove the fixed slot 0
    check("del slot: mask shrank in step",
          len(m3.raw_properties["fractions_mask"]) == m3.m)

    # --- load heals a length-drifted / garbage mask off disk (audit risk) ----
    # A corrupt or legacy .mud can carry a mask whose length != the phase count;
    # the optimiser reads it by index, so an over-long one would IndexError. Inject
    # one, save (to_dict writes it verbatim), reload (from_dict normalises it).
    m0 = mix.m
    _ABSENT = object()

    def reload_with_mask(mask):
        proj = load_mud(PATH)
        raw = proj.mixtures[0].raw_properties
        if mask is _ABSENT:
            raw.pop("fractions_mask", None)
        else:
            raw["fractions_mask"] = mask
        tmp_ = os.path.join(tempfile.mkdtemp(), "m.mud")
        save_mud(proj, tmp_)
        return load_mud(tmp_).mixtures[0]

    over = reload_with_mask([1] * (m0 + 3))          # too long
    check("normalize: an over-long mask is trimmed to m on load",
          len(over.raw_properties["fractions_mask"]) == over.m)
    optimize_mixture(over, n_starts=1)               # would IndexError unhealed
    check("normalize: optimise runs on a healed (once over-long) mask", True)

    short = reload_with_mask([0, 1])                 # too short (m0 >= 2)
    hs = short.raw_properties["fractions_mask"]
    check("normalize: a short mask pads to m, kept flags intact, new slots refine",
          len(hs) == short.m and hs[0] == 0 and hs[1] == 1 and all(hs[2:]))

    garbage = reload_with_mask("nonsense")           # not a list
    check("normalize: a non-list mask is dropped (falls back to all-free)",
          "fractions_mask" not in garbage.raw_properties)

    absent = reload_with_mask(_ABSENT)               # never had one
    check("normalize: an absent mask stays absent (all-free, no bloat)",
          "fractions_mask" not in absent.raw_properties)

    # --- end-to-end: a FIXED fraction stays put through optimise -------------
    # Perturb the fractions off their stored optimum + free ALL slots, so an
    # optimise genuinely moves them (the fixture ships at its own optimum).
    def perturbed():
        m = load_mud(PATH).mixtures[0]
        m.fractions = np.full(m.m, 1.0 / m.m, dtype=float)  # equal start
        for k in range(m.m):
            m.set_fraction_refine(k, True)
        return m

    free = perturbed()
    start = np.array(free.fractions, float)
    optimize_mixture(free, n_starts=4)
    check("control: a free optimise DOES move the fractions",
          float(np.max(np.abs(np.array(free.fractions, float) - start))) > 1e-3)

    mixF = perturbed()
    mixF.fractions[0] = 0.5           # a distinctive, fixed value
    mixF.set_fraction_refine(0, False)
    optimize_mixture(mixF, n_starts=4)
    check("optimise: the FIXED slot-0 fraction is unchanged (0.5)",
          abs(float(mixF.fractions[0]) - 0.5) < 1e-9)
    check("optimise: fractions still sum to 1",
          abs(float(np.sum(mixF.fractions)) - 1.0) < 1e-6)
    check("optimise: a FREE slot did move from the equal start",
          float(np.max(np.abs(np.array(mixF.fractions[1:], float) - start[1:]))) > 1e-3)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- fraction-refine (fractions_mask) verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
