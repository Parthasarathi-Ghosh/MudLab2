#!/usr/bin/env python
"""A missing bundled file must explain itself, not show a traceback.

MudLab is not code-signed, and packaged Python applications are periodically
flagged by antivirus software. On 2026-08-26 Quick Heal quarantined
matplotlib's `ft2font` extension as `Trojan.Agent` on a user's machine. The file
was simply gone, and Python reported

    cannot import name 'ft2font' from partially initialized module
    'matplotlib' (most likely due to a circular import)

whose parenthetical is actively misleading - there is no circular import. No
user can be expected to translate that into "your antivirus ate a file, restore
it". `__main__._load_main_window` catches it and says so instead.

This drives that path with the import made to fail exactly as it failed for the
user, and asserts the message names the missing file and the remedy.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_startup_guard.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import builtins
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from mudlab import APP_NAME  # noqa: E402

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def main():
    import mudlab.__main__ as entry

    shown = {}

    def fake_exec(self):
        shown["title"] = self.windowTitle()
        shown["text"] = self.text()
        shown["info"] = self.informativeText()
        shown["detail"] = self.detailedText()
        return 0

    real_exec, QMessageBox.exec = QMessageBox.exec, fake_exec
    real_import = builtins.__import__

    def quarantined(name, *args, **kwargs):
        """What quarantine looks like from Python: the module is not there."""
        if name == "mudlab.main_window" or name.startswith("matplotlib"):
            error = ImportError(
                "cannot import name 'ft2font' from partially initialized "
                "module 'matplotlib' (most likely due to a circular import)")
            error.name = "ft2font"
            raise error
        return real_import(name, *args, **kwargs)

    builtins.__import__ = quarantined
    try:
        entry._load_main_window()
        exited, code = False, None
    except SystemExit as exc:
        exited, code = True, exc.code
    finally:
        builtins.__import__ = real_import
        QMessageBox.exec = real_exec

    check("a quarantined component stops startup cleanly", exited and code == 1)
    check("a dialog is shown, not a traceback", bool(shown))

    info = shown.get("info", "")
    text = shown.get("text", "")
    check("the title names the app",
          APP_NAME in shown.get("title", ""))
    check("the message names the MISSING FILE, so the user can find it",
          "ft2font" in text)
    check("it points at antivirus, the actual cause",
          "antivirus" in info.lower())
    check("it says the build is unsigned, so the flag looks less alarming",
          "code-signed" in info.lower() or "signed" in info.lower())
    check("it gives the remedy: restore from quarantine",
          "restore" in info.lower() and "quarantine" in info.lower())
    check("...and how to stop it recurring: an exclusion",
          "exclusion" in info.lower())
    check("it covers the other cause too (a partial unzip)",
          "unzip" in info.lower())
    check("the raw error is kept, but tucked into the details",
          "ImportError" in shown.get("detail", ""))

    # The guard must not fire when nothing is wrong.
    loaded = entry._load_main_window()
    check("a healthy install still loads the main window",
          loaded is not None and loaded.__name__ == "MainWindow")

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Startup guard (antivirus quarantine)")
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
