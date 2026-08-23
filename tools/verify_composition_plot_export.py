#!/usr/bin/env python
"""Composition dialog: exporting the comparison chart from its context menu.

The table beside the chart already had Copy and Export buttons; the chart had
no way out of the dialog at all. Right-clicking it now offers "Save plot as..."
(SVG, PDF and bitmaps) and "Copy plot image".

The export reuses the main window's Save Graph flow - the same size/DPI dialog,
and the same `plot_controller.save_figure`, which was lifted out of PatternPlot
into a module-level function for the purpose. That matters mostly for its
`finally`: the interactive figure size is restored even when saving fails, and
a second hand-rolled copy would be the obvious place to lose it.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_composition_plot_export.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no sample project with a mixture.
"""

from __future__ import annotations

import glob
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog  # noqa: E402

from mudlab.composition_dialog import CompositionDialog  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.specimen_dialogs import SaveGraphSizeDialog  # noqa: E402

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in sorted(glob.glob(os.path.join(
            _REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        if project.mixtures:
            return path, project
    return None, None


PATH, PROJECT = _fixture()
if PATH is None:
    print("No sample project with a mixture; skipping (exit 2).")
    raise SystemExit(2)

_ACCEPT = QDialog.DialogCode.Accepted


def _pick(path):
    """Point the next file dialog at `path`."""
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (path, ""))


def main():
    dialog = CompositionDialog(PROJECT.mixtures[0], project=PROJECT)

    # ------------------------------------------------------------- the menu
    menu = dialog.plot_menu()
    labels = [a.text() for a in menu.actions()]
    check("menu: offers a save entry", any("Save plot" in t for t in labels))
    check("menu: offers a copy entry", any("Copy plot" in t for t in labels))
    check("menu: every entry explains itself",
          all(a.toolTip() for a in menu.actions()))
    check("menu: the canvas actually raises it (custom context menu policy)",
          dialog._canvas.contextMenuPolicy().name == "CustomContextMenu")

    # The size dialog is modal; accept it without showing.
    SaveGraphSizeDialog.exec = lambda self: _ACCEPT

    tmp = tempfile.mkdtemp(prefix="mudlab_comp_plot_")
    before = tuple(dialog._figure.get_size_inches())

    # --------------------------------------------------- formats round-trip
    # SVG is the one the user asked for by name; the bitmaps and PDF come with
    # the same flow.
    sizes = {}
    for ext in ("svg", "png", "pdf", "tif", "jpg"):
        target = os.path.join(tmp, "chart." + ext)
        _pick(target)
        dialog._on_save_plot()
        ok = os.path.isfile(target) and os.path.getsize(target) > 0
        sizes[ext] = os.path.getsize(target) if ok else 0
        check("save: %s is written and non-empty" % ext.upper(), ok)

    check("save: SVG really is vector (an <svg> document, not a bitmap)",
          open(os.path.join(tmp, "chart.svg"), "r", encoding="utf-8",
               errors="replace").read(400).lstrip().startswith(("<?xml", "<svg")))

    # Matplotlib writes TIFF uncompressed - 153 MB at the size dialog's default
    # 8000x4800. save_figure asks for LZW, so it must land far below that.
    check("save: TIFF is compressed (%.1f MB, not ~150 MB)"
          % (sizes["tif"] / 1e6), 0 < sizes["tif"] < 40e6)

    # ------------------------------------------------------------ behaviour
    check("save: the on-screen figure size is restored afterwards",
          tuple(dialog._figure.get_size_inches()) == before)

    noext = os.path.join(tmp, "chart_noext")
    _pick(noext)
    dialog._on_save_plot()
    check("save: an extension-less name becomes .png",
          os.path.isfile(noext + ".png"))

    # Cancelling the picker must write nothing at all.
    listing = set(os.listdir(tmp))
    _pick("")
    dialog._on_save_plot()
    check("save: cancelling the file picker writes nothing",
          set(os.listdir(tmp)) == listing)

    # Cancelling the SIZE dialog must not even reach the picker.
    SaveGraphSizeDialog.exec = lambda self: QDialog.DialogCode.Rejected
    reached = {"picker": False}

    def _tripwire(*a, **k):
        reached["picker"] = True
        return ("", "")

    QFileDialog.getSaveFileName = staticmethod(_tripwire)
    dialog._on_save_plot()
    check("save: cancelling the size dialog stops before the file picker",
          not reached["picker"])

    # A write that fails must be reported, not raised - and must still put the
    # interactive size back (the `finally` in save_figure).
    SaveGraphSizeDialog.exec = lambda self: _ACCEPT
    from PySide6.QtWidgets import QMessageBox

    warned = []
    QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(a[2]))
    _pick(os.path.join(tmp, "no_such_dir", "chart.png"))
    try:
        dialog._on_save_plot()
        raised = False
    except Exception:  # noqa: BLE001
        raised = True
    check("save: an unwritable path is reported, not raised",
          not raised and bool(warned))
    check("save: ...and the on-screen size survives the failure",
          tuple(dialog._figure.get_size_inches()) == before)

    # --------------------------------------------------------------- copy
    app.clipboard().clear()
    dialog._on_copy_plot()
    check("copy: the clipboard holds an image",
          not app.clipboard().pixmap().isNull())

    for name in os.listdir(tmp):
        os.remove(os.path.join(tmp, name))
    os.rmdir(tmp)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Composition plot export:", os.path.basename(PATH))
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
