#!/usr/bin/env python
"""Head-less harness for the startup splash screen.

The splash is a deliberate, faithful copy of the OLD GTK MudLab's splash - the
user prefers it, so the earlier "brand it distinctly" decision was reversed.
This pins the things that make it a COPY rather than merely similar: the exact
palette, the element ORDER (the old app put the version after the tagline), the
"v<version>" wording, the 220 px logo, the separator, and the five-second
minimum on screen.

The old design's numbers, for reference (mudlab/application/splash.py):

    BG_COLOR "#1a2a3a", TEXT_COLOR "#d0dce8", ACCENT "#e8b84b"
    logo 220 px tall, title "Segoe UI Bold 26", the rest "Segoe UI 10"
    margins 30/24/40/40, per-widget bottom margins 14/2/10/18/14
    close() waits until 5 s have elapsed since the splash appeared

NOTE ON FONTS: under the offscreen platform this environment has ZERO font
families, so every glyph is tofu and any width/height assertion is meaningless.
Nothing here asserts a rendered size for that reason - the geometry was checked
by rendering with the real Windows font stack instead.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_splash.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from mudlab import APP_NAME, __version__
from mudlab.splash import (
    ACCENT, BG, CORNER_RADIUS, LOGO_HEIGHT, TEXT_FG, VERSION_FG,
    _MIN_VISIBLE_MS, SplashScreen, show_splash,
)

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def main():
    s = SplashScreen()
    qss = s.styleSheet()

    # ---------------------------------------------------------- content
    check("content: name is the app name", s.ui.lbl_name.text() == APP_NAME)
    check("content: version reads 'v<version>' like the old app",
          s.ui.lbl_version.text() == "v%s" % __version__)
    check("content: the old tagline, verbatim",
          s.ui.lbl_tagline.text()
          == "X-ray Diffraction Analysis of Disordered Layered Minerals")
    check("content: status starts on the old 'Loading ...'",
          s.ui.lbl_status.text() == "Loading ...")
    check("content: logo pixmap set", s.ui.lbl_logo.pixmap() is not None
          and not s.ui.lbl_logo.pixmap().isNull())
    check("content: logo is scaled to the old 220 px",
          s.ui.lbl_logo.pixmap().height() == LOGO_HEIGHT)

    # ------------------------------------------------------- old palette
    check("palette: background is the old #1a2a3a", BG == "#1a2a3a")
    check("palette: text is the old #d0dce8", TEXT_FG == "#d0dce8")
    check("palette: accent is the old gold #e8b84b", ACCENT == "#e8b84b")
    check("palette: the version uses the accent", VERSION_FG == ACCENT)
    check("palette: background reaches the stylesheet", BG in qss)
    check("palette: accent reaches the stylesheet", ACCENT in qss)
    check("palette: title + tagline + status use the text colour",
          qss.count(TEXT_FG) >= 2)

    # ---------------------------------------------- typography (as POINTS)
    # GTK's "Segoe UI Bold 26" is 26 POINTS; px here would render it small.
    check("type: title is 26pt bold", "font-size: 26pt" in qss
          and "font-weight: bold" in qss)
    check("type: the rest is 10pt", "font-size: 10pt" in qss)
    check("type: Segoe UI is asked for first", "'Segoe UI'" in qss)

    # ------------------------------------------------------------ layout
    # The old order is logo, title, tagline, VERSION, separator, status - the
    # Qt build previously had version above tagline.
    layout = s.ui.splashLayout
    order = []
    for i in range(layout.count()):
        item = layout.itemAt(i)
        widget = item.widget()
        if widget is not None:
            order.append(widget.objectName())
    check("layout: old element order (version AFTER the tagline)",
          order == ["lbl_logo", "lbl_name", "lbl_tagline", "lbl_version",
                    "separator", "lbl_status"],
          )
    check("layout: the hairline separator is present and horizontal",
          s.ui.separator.frameShape() == s.ui.separator.Shape.HLine)
    margins = layout.contentsMargins()
    check("layout: old margins 40/30/40/24",
          (margins.left(), margins.top(), margins.right(), margins.bottom())
          == (40, 30, 40, 24))
    check("layout: spacing 0 (the old box spaced per widget, not globally)",
          layout.spacing() == 0)
    # Those per-widget bottom margins become fixed spacers here.
    spacers = [layout.itemAt(i).spacerItem().sizeHint().height()
               for i in range(layout.count())
               if layout.itemAt(i).spacerItem() is not None]
    check("layout: per-widget gaps 14/2/10/18/14 preserved as spacers",
          spacers == [14, 2, 10, 18, 14])
    check("layout: every label is centred",
          all(w.alignment() & Qt.AlignmentFlag.AlignHCenter
              for w in s.findChildren(QLabel)))

    # ------------------------------------------------------- window setup
    check("window: frameless splash",
          bool(s.windowFlags() & Qt.WindowType.FramelessWindowHint))
    check("window: stays on top", bool(s.windowFlags()
                                       & Qt.WindowType.WindowStaysOnTopHint))
    check("window: non-resizable, like the old set_resizable(False)",
          s.minimumSize() == s.maximumSize())
    check("window: content-sized (no inherited 480x300 box)",
          s.maximumSize().width() != 480 or s.maximumSize().height() != 300)
    # Rounded corners need a translucent top level, else the window's own
    # square background paints over them.
    check("window: translucent, so the %dpx corners actually round"
          % CORNER_RADIUS,
          s.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
    check("window: the radius is on the card, not the window",
          "#splashCard" in qss and "border-radius: %dpx" % CORNER_RADIUS in qss)

    # ---------------------------------------------------------- messages
    s.set_message("Loading application ...")
    check("status: set_message updates the status line",
          s.ui.lbl_status.text() == "Loading application ...")

    # ------------------------------------------------------ show / hold
    s2, started = show_splash()
    check("show_splash: returns a SplashScreen + a float timestamp",
          isinstance(s2, SplashScreen) and isinstance(started, float))
    check("show_splash: the splash is visible", s2.isVisible())

    check("timing: the old five-second minimum", _MIN_VISIBLE_MS == 5000)
    # Already elapsed -> returns at once.
    t0 = time.monotonic()
    s2.hold_for(_MIN_VISIBLE_MS, time.monotonic() - 10.0)
    check("hold_for: returns immediately once the minimum has passed",
          time.monotonic() - t0 < 0.5)
    # Not yet elapsed -> actually waits (a short window, so the harness is fast).
    t0 = time.monotonic()
    s2.hold_for(300, time.monotonic())
    waited = time.monotonic() - t0
    check("hold_for: blocks for the remainder (%.2fs of 0.30s)" % waited,
          0.25 <= waited < 1.5)
    s2.close()
    check("close: the splash goes away", not s2.isVisible())

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("--- splash screen verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
