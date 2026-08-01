#!/usr/bin/env python
"""Head-less harness for the startup splash screen.

The splash is branded to distinguish this Qt MudLab from the old GTK MudLab
(shared name + icon): a distinct teal-slate background, the reused icon, and a
prominent version number. This checks the content, the branding/frameless setup,
and the show / auto-close plumbing.

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
from PySide6.QtWidgets import QApplication

from mudlab import APP_NAME, __version__
from mudlab.splash import BG, VERSION_FG, SplashScreen, show_splash

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def main():
    s = SplashScreen()

    # Content
    check("content: name is the app name", s.ui.lbl_name.text() == APP_NAME)
    check("content: version shows the current version (%s)" % __version__,
          s.ui.lbl_version.text() == "version %s" % __version__)
    check("content: tagline present", bool(s.ui.lbl_tagline.text().strip()))
    check("content: logo pixmap set (reused icon)",
          s.ui.lbl_logo.pixmap() is not None and not s.ui.lbl_logo.pixmap().isNull())

    # Branding / distinct look
    check("brand: object name targets the stylesheet", s.objectName() == "SplashScreen")
    check("brand: distinct teal-slate background applied",
          BG in s.styleSheet())
    check("brand: version drawn in the gold accent",
          VERSION_FG in s.styleSheet())

    # Splash window setup
    check("window: frameless splash",
          bool(s.windowFlags() & Qt.WindowType.FramelessWindowHint))
    check("window: fixed size (non-resizable splash)",
          s.minimumSize() == s.maximumSize() and s.maximumSize().width() == 480)

    # set_message
    s.set_message("Loading project...")
    check("status: set_message updates the status line",
          s.ui.lbl_status.text() == "Loading project...")

    # show_splash returns a visible splash + a start stamp
    s2, started = show_splash()
    check("show_splash: returns a SplashScreen + a float timestamp",
          isinstance(s2, SplashScreen) and isinstance(started, float))
    check("show_splash: the splash is visible", s2.isVisible())

    # finish_after closes on the event loop (min already elapsed -> ~immediate)
    s2.finish_after(0, time.monotonic() - 10.0)
    app.processEvents()
    check("finish_after: the splash closes once the minimum has elapsed",
          not s2.isVisible())

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("--- splash screen verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
