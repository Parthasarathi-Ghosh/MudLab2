#!/usr/bin/env python
"""MainWindow wiring for Data > "Convert data to fixed slit" / "Convert data to
ADS" (actionConvertToFixed / actionConvertToADS).

Batch 1 verified the transform; this checks the menu wiring:

  - both actions are in the data-op group, so they enable only when a single
    specimen with data is selected and grey out otherwise;
  - triggering the action (past its confirmation) rescales that specimen's
    experimental pattern (x sin(theta) to ADS, / sin(theta) to fixed) and marks
    the project dirty; the two directions round-trip.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_convert_slit_ui.py

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
from PySide6.QtWidgets import QApplication, QMessageBox

# The conversion pops a modal confirmation; auto-accept it (and record its text,
# to check the divergence-mode reminder) so the head-less run does not block.
_last_confirm = {"text": ""}


def _fake_question(*a, **k):
    _last_confirm["text"] = a[2] if len(a) > 2 else k.get("text", "")
    return QMessageBox.StandardButton.Yes


QMessageBox.question = staticmethod(_fake_question)

from mudlab.file_parsers.mud_project import load_mud
from mudlab.main_window import MainWindow

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    fixtures = [os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")]
    fixtures += sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud")))
    seen = set()
    for path in fixtures:
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        project = load_mud(path)
        for i, spec in enumerate(project.specimens):
            if spec is not None and spec.has_experimental_data:
                return path, i
    return None, None


PATH, ROW = _fixture()
if PATH is None:
    print("No fixture with a specimen with data; skipping (exit 2).")
    raise SystemExit(2)


def main():
    project = load_mud(PATH)
    spec = project.specimens[ROW]
    print("fixture: %s (specimen row #%d)" % (os.path.basename(PATH), ROW))

    win = MainWindow()
    win._set_project(project)

    both = (win.ui.actionConvertToFixed, win.ui.actionConvertToADS)
    check("both Convert actions are in the data-op group",
          all(a in win._data_op_actions for a in both))

    # Nothing selected -> greyed (the "enabled no-op" the group guards against).
    win.ui.specimensTree.selectionModel().clearSelection()
    win._update_data_op_actions()
    check("Convert actions disabled with no specimen selected",
          not any(a.isEnabled() for a in both))

    # Select the specimen with data -> enabled.
    win.select_specimen_row(ROW)
    win.show_specimen_plots([spec])
    check("Convert actions enabled for a single specimen with data",
          all(a.isEnabled() for a in both))

    x, y0 = spec.experimental_pattern
    y0 = np.array(y0, float)
    sin_theta = np.sin(np.radians(np.asarray(x, float) * 0.5))

    # Trigger the real action (past the auto-accepted confirmation).
    win._dirty = False
    win.ui.actionConvertToADS.trigger()
    _x, y_ads = spec.experimental_pattern
    check("Convert to ADS rescales the pattern (x sin theta)",
          np.allclose(y_ads, y0 * sin_theta))
    check("Convert to ADS marks the project dirty", win._dirty is True)
    check("ADS confirmation reminds to set Automatic mode + F5",
          "Automatic" in _last_confirm["text"] and "F5" in _last_confirm["text"])

    win.ui.actionConvertToFixed.trigger()
    _x2, y_back = spec.experimental_pattern
    check("Convert to fixed inverts it (round-trip to original)",
          np.allclose(y_back, y0, atol=1e-6))
    check("fixed confirmation reminds to set Fixed mode + F5",
          "Fixed" in _last_confirm["text"] and "F5" in _last_confirm["text"])

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- Convert-slit MainWindow wiring verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
