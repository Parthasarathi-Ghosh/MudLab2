"""Application entry point: python -m mudlab."""

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QStyleFactory

from mudlab import APP_NAME, ORG_NAME, __version__
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

    # Windows system UI font.
    app.setFont(QFont("Segoe UI", 9))
    return app


def main() -> int:
    app = create_app(sys.argv)
    splash, started = show_splash()   # branded splash while the window builds
    window = MainWindow()
    window.show()
    window.raise_()
    splash.finish_after(_MIN_VISIBLE_MS, started)  # closes on the event loop
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
