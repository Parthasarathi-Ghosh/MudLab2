#!/usr/bin/env python
"""Durable harness for the About / branding work, run head-less.

Covers:
  - version well-formed + consistency (mudlab.__version__ is the single source;
    pyproject.toml is asserted equal to it);
  - branding assets (resources.app_icon has every packaged size; the logo and
    the .ico exist) and that a QIcon built from them is a valid window icon;
  - the branded About dialog (name / version / tagline / library line / logo /
    window icon / title).

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_about.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import re
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication

import mudlab
from mudlab.about_dialog import AboutDialog
from mudlab.resources import APP_ICO, app_icon, icon_path, logo_pixmap

app = QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def check_version():
    # src/mudlab/__init__.py __version__ is the single source of truth; assert it
    # is well-formed (not a hardcoded value, so a bump touches only __init__ +
    # pyproject) and that pyproject stays in step with it.
    check("version is well-formed (semver)",
          re.match(r"^\d+\.\d+\.\d+([.\-+].*)?$", mudlab.__version__) is not None)
    pyproject = open(os.path.join(_REPO, "pyproject.toml"), encoding="utf-8").read()
    pv = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)
    check("pyproject version matches package version", pv == mudlab.__version__)
    check("app name is MudLab", mudlab.APP_NAME == "MudLab")


def check_assets():
    for size in (16, 24, 32, 48, 64, 128):
        p = icon_path("mudlab_icon_%dx%d.png" % (size, size))
        check("icon PNG %dpx bundled" % size, os.path.isfile(p))
    check(".ico bundled (for the frozen exe)", os.path.isfile(APP_ICO))

    icon = app_icon()
    check("app_icon() is not null", not icon.isNull())
    sizes = {(s.width(), s.height()) for s in icon.availableSizes()}
    check("app_icon() carries every packaged size",
          {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128)} <= sizes)
    check("logo_pixmap() is not null", not logo_pixmap(96).isNull())

    # A valid application/window icon.
    app.setWindowIcon(app_icon())
    check("QApplication window icon set from app_icon()", not app.windowIcon().isNull())


def check_about_dialog():
    dlg = AboutDialog()
    check("About: name is MudLab", dlg.ui.lbl_name.text() == "MudLab")
    check("About: version label matches the package version",
          dlg.ui.lbl_version.text() == "Version %s" % mudlab.__version__)
    check("About: tagline present", "Diffraction" in dlg.ui.lbl_tagline.text())
    check("About: credits original PyXRD by Mathijs Dumon",
          dlg.ui.lbl_credit.text() == "Original PyXRD by Mathijs Dumon.")
    libs = dlg.ui.lbl_libs.text()
    check("About: library versions line filled",
          all(name in libs for name in ("Python", "PySide6", "NumPy", "SciPy", "Matplotlib")))
    check("About: logo pixmap set", not dlg.ui.lbl_logo.pixmap().isNull())
    check("About: window icon set", not dlg.windowIcon().isNull())
    check("About: title is 'About MudLab'", dlg.windowTitle() == "About MudLab")
    dlg.deleteLater()


def main():
    check_version()
    check_assets()
    check_about_dialog()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- About / branding verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
