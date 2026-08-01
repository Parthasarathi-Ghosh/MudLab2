"""Startup splash screen. Design: ui/splash.ui.

Shown while the main window builds, then closed. It is deliberately BRANDED so
this Qt MudLab is visually distinct from the older GTK MudLab (they share the
same name and icon): a deep teal-slate background echoing the app icon's
crystal-lattice palette, with the version number in a warm gold so the higher
release number - the differentiator from the (capped) old app - stands out. The
palette constants below are the single place to retune it.
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget

from mudlab import APP_NAME, __version__
from mudlab.resources import logo_pixmap
from mudlab.ui.ui_splash import Ui_SplashScreen

# Palette - tuned to the icon (teal/navy edges, cream facets, gold accents).
BG = "#1D3B44"          # deep teal-slate - distinct from the old app's system grey
BORDER = "#0F252B"
NAME_FG = "#F2F6F7"
VERSION_FG = "#E9C46A"  # gold: the higher version stands out
TAGLINE_FG = "#9DB2B8"
STATUS_FG = "#6E828A"

_MIN_VISIBLE_MS = 700   # keep the splash up long enough to register the brand

_QSS = """
QWidget#SplashScreen {{ background-color: {bg}; border: 1px solid {border}; }}
#lbl_name {{ color: {name}; font-size: 32px; font-weight: 700; }}
#lbl_version {{ color: {version}; font-size: 14px; font-weight: 600;
                letter-spacing: 1px; }}
#lbl_tagline {{ color: {tagline}; font-size: 11px; }}
#lbl_status {{ color: {status}; font-size: 10px; }}
""".format(bg=BG, border=BORDER, name=NAME_FG, version=VERSION_FG,
           tagline=TAGLINE_FG, status=STATUS_FG)


class SplashScreen(QWidget):
    """Frameless, centred, always-on-top startup splash."""

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.ui = Ui_SplashScreen()
        self.ui.setupUi(self)
        self.setObjectName("SplashScreen")  # the stylesheet targets this
        self.ui.lbl_logo.setPixmap(logo_pixmap(112))
        self.ui.lbl_name.setText(APP_NAME)
        self.ui.lbl_version.setText("version %s" % __version__)
        self.setStyleSheet(_QSS)
        self._centre()

    def _centre(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(geo.center() - self.rect().center())

    def set_message(self, text: str) -> None:
        """Update the bottom status line (e.g. 'Loading...')."""
        self.ui.lbl_status.setText(text)

    def finish_after(self, min_visible_ms: int, started: float) -> None:
        """Close the splash, but not before `min_visible_ms` has elapsed since
        `started` (a time.monotonic() stamp), so a fast startup still shows the
        brand. Non-blocking - the close is scheduled on the event loop."""
        elapsed_ms = (time.monotonic() - started) * 1000.0
        QTimer.singleShot(max(0, int(min_visible_ms - elapsed_ms)), self.close)


def show_splash() -> tuple["SplashScreen", float]:
    """Create, show and paint the splash immediately (before the main window is
    built). Returns the splash and a start timestamp for `finish_after`."""
    splash = SplashScreen()
    splash.show()
    QApplication.processEvents()  # paint it now, before the slow window build
    return splash, time.monotonic()
