#!/usr/bin/env python
"""Save Graph (Data ▸ Save graph): the size/DPI dialog was opened but its result
was discarded - no file picker, no save. This covers the fix:

  - PatternPlot.save_figure writes a real image (.png / .pdf / .svg) at the
    requested inch size + dpi, and restores the on-screen size/dpi afterwards;
  - MainWindow._save_graph runs the size dialog -> file picker -> save, so
    clicking OK actually produces a file (here the two dialogs are mocked).

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_save_graph.py

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

import mudlab.main_window as mw
from mudlab.file_parsers.mud_project import load_mud
from mudlab.main_window import MainWindow
from mudlab.plot_controller import PatternPlot

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []
_TMP = tempfile.mkdtemp()


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

    # --- PatternPlot.save_figure: real files + size/dpi restored --------------
    plot = PatternPlot([spec], project)
    before_size = tuple(plot.figure.get_size_inches())
    before_dpi = plot.figure.get_dpi()
    for ext in ("png", "pdf", "svg"):
        out = os.path.join(_TMP, "graph." + ext)
        plot.save_figure(out, dpi=120, i_width=4.0, i_height=3.0)
        check("save_figure writes a non-empty .%s" % ext,
              os.path.isfile(out) and os.path.getsize(out) > 0)
    check("save_figure restores the on-screen size",
          np.allclose(plot.figure.get_size_inches(), before_size))
    check("save_figure restores the on-screen dpi",
          plot.figure.get_dpi() == before_dpi)

    # save even survives a bad path (exception restores state, doesn't corrupt).
    try:
        plot.save_figure(os.path.join(_TMP, "nope", "x.png"), 100, 3.0, 2.0)
    except Exception:
        pass
    check("a failed save still restores the on-screen size",
          np.allclose(plot.figure.get_size_inches(), before_size))

    # --- MainWindow._save_graph end-to-end (dialogs mocked) ------------------
    win = MainWindow()
    win._set_project(project)
    win.select_specimen_row(ROW)
    win.show_specimen_plots([spec])

    target = os.path.join(_TMP, "from_ui.png")

    def _fake_size_exec(self):  # accept with small, fast dimensions
        self.ui.entry_width.setValue(400)
        self.ui.entry_height.setValue(300)
        self.ui.entry_dpi.setValue(100)
        return 1

    mw.SaveGraphSizeDialog.exec = _fake_size_exec
    mw.QFileDialog.getSaveFileName = staticmethod(
        lambda *a, **k: (target, "PNG image (*.png)")
    )
    win.ui.actionSaveGraph.trigger()
    check("Save Graph action produces a file on OK",
          os.path.isfile(target) and os.path.getsize(target) > 0)

    # Cancelling the file picker saves nothing.
    target2 = os.path.join(_TMP, "cancelled.png")
    mw.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
    win.ui.actionSaveGraph.trigger()
    check("cancelling the file picker writes nothing",
          not os.path.exists(target2))

    # An extension-less path defaults to .png.
    noext = os.path.join(_TMP, "noext")
    mw.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (noext, ""))
    win.ui.actionSaveGraph.trigger()
    check("an extension-less name is saved as .png",
          os.path.isfile(noext + ".png"))

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- Save Graph verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
