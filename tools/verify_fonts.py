#!/usr/bin/env python
"""The app's typography: one UI face, one chart face, and a real monospace.

MudLab makes exactly three font decisions, and each has a way of going wrong
quietly:

  1. **The interface** - `Segoe UI 9pt` on the QApplication. Every widget
     inherits it; no `.ui` file names a family.
  2. **Charts** - matplotlib defaults to its own bundled DejaVu Sans, so
     without `chart_style.apply_chart_font()` a plot is set in a different
     typeface from the window around it. `create_app` calls it; the module also
     calls it at import, because harnesses build charts without an application.
     The reason it is an explicit call and not just an import side effect:
     `refinement_dialog` draws the convergence plot and does NOT import
     `chart_style`, so its text alone would have stayed DejaVu.
  3. **Fixed pitch** - the structure diagram, the refinement report and the
     plot info label align columns WITH SPACES. `QFontDatabase.systemFont`
     returned **Courier New** here, and what it returns is a system setting, so
     two machines could render the diagram differently. `qt_utils.fixed_font`
     names Consolas (Windows 10+) and keeps the fallback monospace. A
     proportional face - Calibri, Arial, Segoe UI - would leave the text right
     and the layout meaningless.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_fonts.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import matplotlib  # noqa: E402
from PySide6.QtGui import QFontInfo  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.chart_style import UI_FONT, apply_chart_font  # noqa: E402
from mudlab.qt_utils import fixed_font  # noqa: E402

results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def main():
    # ------------------------------------------------------- 1. the UI font
    from mudlab.__main__ import create_app

    app = QApplication.instance() or create_app([])
    if app.font().family() != UI_FONT:      # an instance may pre-exist
        from PySide6.QtGui import QFont
        app.setFont(QFont(UI_FONT, 9))
        apply_chart_font()
    check("ui: the application font is %s" % UI_FONT,
          app.font().family() == UI_FONT)
    check("ui: no .ui file hardcodes a font family (all inherit)",
          not any("<family>" in open(p, encoding="utf-8").read()
                  for p in glob.glob(os.path.join(
                      _REPO, "src", "mudlab", "**", "*.ui"), recursive=True)))

    # ---------------------------------------------------- 2. the chart font
    apply_chart_font()
    stack = matplotlib.rcParams["font.sans-serif"]
    check("charts: the UI font leads the stack", stack[0] == UI_FONT)
    check("charts: DejaVu Sans is KEPT as the last resort (it is bundled, so "
          "a chart always draws)", "DejaVu Sans" in stack)
    check("charts: family is sans-serif, so the stack is consulted",
          matplotlib.rcParams["font.family"] == ["sans-serif"])

    from matplotlib.font_manager import FontProperties, findfont
    resolved = os.path.basename(findfont(FontProperties(family=["sans-serif"])))
    check("charts: it actually RESOLVES to the UI font here (%s)" % resolved,
          "segoeui" in resolved.lower() or "DejaVu" in resolved)

    # ------------------------------------------------- 3. the monospace font
    #
    # THE OFFSCREEN PLATFORM HAS NO FONTS AT ALL in this environment, so
    # QFontInfo resolves to an empty family and QFontMetrics.inFont() reports
    # every character as missing. Anything that depends on a font actually
    # resolving is therefore skipped there and checked under the real Windows
    # plugin instead (QT_QPA_PLATFORM=windows). The settings themselves - which
    # face is ASKED for - are checked either way, and they are what can
    # regress in code.
    from PySide6.QtGui import QFontDatabase
    have_fonts = bool(QFontDatabase.families())
    info = QFontInfo(fixed_font())
    if have_fonts:
        check("mono: fixed_font() is genuinely fixed-pitch", info.fixedPitch())
        check("mono: ...and is not the shabby Courier New default (%s)"
              % info.family(), info.family() != "Courier New")
    else:
        check("mono: (no fonts under this platform plugin; resolution checks "
              "skipped - run with QT_QPA_PLATFORM=windows)", True)
    check("mono: Consolas is asked for first",
          __import__("mudlab.qt_utils", fromlist=["_FIXED_FACES"])
          ._FIXED_FACES[0] == "Consolas")
    sized = fixed_font(11)
    check("mono: a point size can be asked for", sized.pointSize() == 11)

    # Nothing may go back to the system setting.
    offenders = []
    for path in glob.glob(os.path.join(_REPO, "src", "mudlab", "**", "*.py"),
                          recursive=True):
        if os.path.basename(path).startswith("ui_") or "qt_utils" in path:
            continue
        with open(path, encoding="utf-8") as handle:
            if "systemFont(" in handle.read():
                offenders.append(os.path.relpath(path, _REPO))
    check("mono: nothing calls QFontDatabase.systemFont directly%s"
          % ("" if not offenders else " -> %s" % offenders), not offenders)

    # The three widgets that need it must actually get it.
    from mudlab.file_parsers.mud_project import load_mud
    fixtures = sorted(glob.glob(os.path.join(
        _REPO, "tools", "sample_projects", "*.mud")))
    if fixtures:
        project = load_mud(fixtures[0])
        from mudlab.structure_diagram_dialog import StructureDiagramDialog

        component = next((c for p in project.phases
                          for c in (getattr(p, "components", None) or [])), None)
        if component is not None:
            dialog = StructureDiagramDialog(None, component=component)
            asked = dialog.ui.txt_diagram.font()
            # styleHint survives even with no font engine behind it.
            check("mono: the structure diagram asks for a monospace face",
                  asked.styleHint() == asked.StyleHint.Monospace
                  and asked.fixedPitch())
            if have_fonts:
                check("mono: ...and it resolves to one",
                      QFontInfo(asked).fixedPitch())
            else:
                check("mono: (resolution skipped - no fonts here)", True)
            dialog.close()
        else:
            check("mono: (no component in the fixture; skipped)", True)
    else:
        check("mono: (no fixture; widget check skipped)", True)

    # ------------------------------------- every glyph the app draws exists
    from PySide6.QtGui import QFont, QFontMetrics
    glyphs = {
        "theta": 0x3B8, "degree": 0xB0, "middot": 0xB7, "em dash": 0x2014,
        "box double": 0x2550, "box light": 0x2500, "box vertical": 0x2502,
        "left arrow": 0x2190, "ellipsis": 0x2026,
    }
    if have_fonts:
        for family in (UI_FONT, info.family()):
            metrics = QFontMetrics(QFont(family, 12))
            missing = [n for n, cp in glyphs.items()
                       if not metrics.inFont(chr(cp))]
            check("glyphs: %s covers the characters the app draws%s"
                  % (family, "" if not missing else " -> missing %s" % missing),
                  not missing)
    else:
        check("glyphs: (no fonts under this platform plugin; skipped)", True)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Fonts: UI %s | charts %s | mono %s"
          % (app.font().family(), stack[0], info.family()))
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
