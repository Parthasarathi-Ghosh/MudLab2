"""Application entry point: python -m mudlab."""

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QStyleFactory

from mudlab import APP_NAME, ORG_NAME, __version__
from mudlab.qt_utils import install_enter_policy
from mudlab.resources import app_icon
from mudlab.splash import show_splash, _MIN_VISIBLE_MS

# NB `mudlab.main_window` is imported inside main(), not here - see
# _load_main_window(). It is the import that pulls in matplotlib, numpy and
# scipy, and therefore the one that fails if a bundled file has gone missing.


def _load_main_window():
    """Import MainWindow, turning a missing bundled file into an explanation.

    ANTIVIRUS QUARANTINE IS THE COMMON CAUSE. MudLab is not code-signed, and
    packaged Python applications are periodically flagged by mistake - Quick
    Heal quarantined matplotlib's `ft2font` extension as `Trojan.Agent` on a
    user's machine (2026-08-26), which left the file simply absent. Python then
    reports

        cannot import name 'ft2font' from partially initialized module
        'matplotlib' (most likely due to a circular import)

    and the parenthetical is actively misleading: there is no circular import,
    the file is gone. A user cannot be expected to translate that. So the
    traceback is replaced with what actually happened and what to do about it.
    """
    try:
        from mudlab.main_window import MainWindow
        return MainWindow
    except ImportError as exc:
        from PySide6.QtWidgets import QMessageBox

        missing = getattr(exc, "name", None) or "a required component"
        app = QApplication.instance() or QApplication([])
        app.setApplicationName(APP_NAME)
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("%s cannot start" % APP_NAME)
        box.setText(
            "%s could not load <b>%s</b>, which is part of the program."
            % (APP_NAME, missing))
        box.setInformativeText(
            "This is nearly always antivirus software: %s is not "
            "code-signed, and packaged Python applications are sometimes "
            "flagged by mistake, which removes the file.<br><br>"
            "<b>To fix it:</b><br>"
            "1. Open your antivirus and look at its quarantine or vault.<br>"
            "2. <b>Restore</b> any file it took from the %s folder.<br>"
            "3. Add the %s folder to its exclusions, so it is not taken "
            "again.<br>"
            "4. Start %s again.<br><br>"
            "If nothing is quarantined, unzip the download again and keep the "
            "whole folder together." % (APP_NAME, APP_NAME, APP_NAME, APP_NAME))
        box.setDetailedText("%s: %s" % (type(exc).__name__, exc))
        box.exec()
        raise SystemExit(1)


def create_app(argv: list[str] | None = None) -> QApplication:
    """Create the QApplication with the native Windows look and feel."""
    app = QApplication(argv if argv is not None else [])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(ORG_NAME)
    # Taskbar / title-bar icon; every window without its own icon inherits it.
    app.setWindowIcon(app_icon())

    # Prefer the modern Windows 11 style (also renders on Windows 10),
    # fall back to the classic Vista style. Both draw native controls,
    # system colors, and native file dialogs.
    available = [name.lower() for name in QStyleFactory.keys()]
    for style in ("windows11", "windowsvista"):
        if style in available:
            app.setStyle(style)
            break

    # Enter accepts only where a QDialogButtonBox says so; everywhere else it
    # commits the field you are in and does nothing more. Qt's own rule -
    # promote some autoDefault button on show - kept picking a destructive one
    # by accident of tab order (Add, and Refine). See qt_utils.install_enter_policy.
    install_enter_policy(app)

    # Windows system UI font.
    app.setFont(QFont("Segoe UI", 9))
    return app


def _selftest() -> int:
    """Release / frozen-build self-check: confirm the bundled data files actually
    resolve through the real loaders (run as `MudLab --selftest`). Returns 0 if
    every check passes, 1 otherwise. A QApplication must already exist (icons)."""
    import traceback

    from mudlab.resources import app_icon, logo_pixmap

    checks: list[tuple[str, bool]] = []

    def probe(name, fn):
        try:
            checks.append((name, bool(fn())))
        except Exception:
            checks.append((name, False))
            traceback.print_exc()

    probe("app icon (data/icons)", lambda: not app_icon().isNull())
    probe("splash logo (data/icons)", lambda: not logo_pixmap(64).isNull())

    def _scattering():
        from mudlab.file_parsers.atom_type_library import atom_type_library_map
        return len(atom_type_library_map()) > 0
    probe("scattering-factor library (atomic_scattering_factors.csv)", _scattering)

    def _composition():
        from mudlab.calculations.composition import load_conversion_table
        return len(load_conversion_table()) > 0
    probe("composition table (composition_conversion.csv)", _composition)

    def _catalog():
        from mudlab.file_parsers.default_catalog import (
            build_catalog_entry_by_name, default_catalog_entries)
        entries = default_catalog_entries()
        return bool(entries) and bool(build_catalog_entry_by_name(entries[0][0]))
    probe("default catalog + a phase build (.cmp components)", _catalog)

    ok = all(v for _, v in checks)
    print("MudLab %s self-test:" % __version__)
    for name, passed in checks:
        print("  [%s] %s" % ("OK" if passed else "FAIL", name))
    print("SELFTEST %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    app = create_app(sys.argv)
    if "--selftest" in sys.argv:
        return _selftest()
    # Old-app startup sequence: the splash carries its own progress messages,
    # holds for its full five seconds, and only THEN does the main window
    # appear. The window is built during the wait rather than after it, so the
    # five seconds are the splash's, not added to the startup.
    MainWindow = _load_main_window()
    splash, started = show_splash()
    # One message, not the old app's three: its "Initializing ..." /
    # "Loading matplotlib ..." / "Loading icons ..." spanned work that in
    # MudLab2 happens at IMPORT time, before main() runs, so those would flash
    # past unread. This one spans the window build, which is the real wait.
    splash.set_message("Loading application ...")
    window = MainWindow()
    splash.hold_for(_MIN_VISIBLE_MS, started)
    splash.close()
    # Fill the available screen area (the .ui's fixed 1280x800 default left a gap
    # on wider screens); the normal size is kept as the restore geometry.
    window.showMaximized()
    window.raise_()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
