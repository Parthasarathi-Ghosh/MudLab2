"""Application entry point: python -m mudlab."""

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QStyleFactory

from mudlab import APP_NAME, ORG_NAME, __version__
from mudlab.qt_utils import install_enter_policy
from mudlab.main_window import MainWindow
from mudlab.resources import app_icon
from mudlab.splash import show_splash, _MIN_VISIBLE_MS


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
    splash, started = show_splash()   # branded splash while the window builds
    window = MainWindow()
    # Fill the available screen area (the .ui's fixed 1280x800 default left a gap
    # on wider screens); the normal size is kept as the restore geometry.
    window.showMaximized()
    window.raise_()
    splash.finish_after(_MIN_VISIBLE_MS, started)  # closes on the event loop
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
