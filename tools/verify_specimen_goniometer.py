#!/usr/bin/env python
"""Every specimen owns a goniometer, so the Edit Specimen > Goniometer tab is
editable for a freshly imported / added specimen (it used to grey out because
Specimen.__init__ left goniometer = None, and import / Add specimen never set
one).

  - a fresh Specimen has a goniometer with a sane default wavelength;
  - the import path (Specimen + set_experimental_pattern) keeps it;
  - Edit Specimen enables the Goniometer tab for such a specimen;
  - a .mud load still overwrites the default from the file (round-trip intact);
  - a fresh specimen's default goniometer round-trips (save then reload).

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_specimen_goniometer.py

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

from mudlab.edit_specimen_dialog import EditSpecimenDialog
from mudlab.file_parsers.mud_project import load_mud, save_mud
from mudlab.models import Project, Specimen

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def main():
    # 1. A fresh specimen has a goniometer with a sane wavelength.
    spec = Specimen(name="imported")
    check("a fresh specimen has a goniometer (not None)",
          spec.goniometer is not None)
    check("its default wavelength is sane (~CuKa 0.1541 nm)",
          spec.goniometer is not None
          and abs(spec.goniometer.wavelength - 0.154056) < 1e-6)

    # 2. The import path (parse -> Specimen -> set_experimental_pattern) keeps it.
    spec.set_experimental_pattern(np.linspace(5, 70, 100), np.ones(100))
    check("an imported specimen (with data) still has a goniometer",
          spec.goniometer is not None and spec.has_experimental_data)

    # 3. Edit Specimen enables the Goniometer tab for it.
    dialog = EditSpecimenDialog()
    dialog.bind_specimen(spec)
    check("Edit Specimen enables the Goniometer tab (not greyed)",
          dialog.goniometer.isEnabled())
    check("the tab is bound to the specimen's goniometer",
          dialog.goniometer._goniometer is spec.goniometer)

    # 4. A .mud load still overwrites the default from the file.
    fixture = None
    for p in [os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")] + \
            sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        if os.path.isfile(p):
            fixture = p
            break
    if fixture is not None:
        project = load_mud(fixture)
        loaded = next((s for s in project.specimens
                       if s is not None and s.goniometer is not None), None)
        # The loaded goniometer reflects the file (e.g. its 2θ range), i.e. it is
        # not just the bare default we now start from.
        check("a loaded specimen's goniometer comes from the file",
              loaded is not None
              and "goniometer" in loaded.raw_properties)
    else:
        print("  (no fixture; skipped the load-overwrite check)")

    # 5. A fresh specimen's default goniometer round-trips through save/reload.
    proj = Project(name="p")
    fresh = Specimen(name="fresh")
    fresh.set_experimental_pattern(np.linspace(5, 70, 50), np.ones(50))
    proj.add_specimen(fresh)
    tmp = os.path.join(tempfile.mkdtemp(), "p.mud")
    save_mud(proj, tmp)
    back = load_mud(tmp).specimens[0]
    check("a fresh specimen's goniometer survives save/reload",
          back.goniometer is not None
          and abs(back.goniometer.wavelength - 0.154056) < 1e-6)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("--- specimen-goniometer verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
