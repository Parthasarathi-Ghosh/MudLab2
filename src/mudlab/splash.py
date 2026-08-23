"""Startup splash screen. Design: ui/splash.ui.

A deliberate, faithful copy of the OLD GTK MudLab's splash
(`mudlab/application/splash.py`) - the user prefers it, so this REVERSES the
earlier decision to brand the Qt build distinctly. Everything visible is matched:
the palette, the element order, the point sizes, the per-element spacing, the
220 px logo, the hairline separator, and the five-second minimum on screen.

Faithful to, specifically:

* palette `BG` / `TEXT_FG` / `ACCENT` are the old BG_COLOR / TEXT_COLOR / ACCENT;
* order is logo, title, tagline, version, separator, status - the old app put
  the version AFTER the tagline (the Qt build had them the other way round);
* GTK `set_margin_bottom(n)` under each widget becomes a fixed n-px spacer,
  since the old box had spacing 0 and did its spacing per-widget;
* sizes are POINTS, not pixels - GTK's "Segoe UI Bold 26" is 26 pt, and using
  px here would render the title noticeably small;
* the window is content-sized (the old one was `set_resizable(False)` with no
  explicit size), with 12 px rounded corners, which needs a translucent
  top-level plus a rounded child card in Qt.

The one deliberate difference is mechanical, not visual: the old `close()`
BLOCKS in `sleep(0.1)` while pumping GTK events. `hold_for` does the same thing
with Qt's event loop, but it lives in the caller's control flow so the main
window can be built DURING the wait instead of after it - the user sees the
identical sequence (splash for 5 s, then the window), without the startup
actually costing 5 s plus the build.
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from mudlab import APP_NAME, __version__
from mudlab.resources import logo_pixmap
from mudlab.ui.ui_splash import Ui_SplashScreen

# --- colour palette (the old app's, matching the logo) ---
BG = "#1a2a3a"          # dark blue-grey
TEXT_FG = "#d0dce8"     # light blue-grey
ACCENT = "#e8b84b"      # gold from the Python logo

# Kept as an alias: the old harness and any caller importing VERSION_FG still
# work, and the version really is drawn in the accent colour.
VERSION_FG = ACCENT

LOGO_HEIGHT = 220       # old: pixbuf scaled to 220 px tall, aspect preserved
CORNER_RADIUS = 12      # old CSS: border-radius: 12px

# The old close() waits until 5 s have passed since the splash appeared.
_MIN_VISIBLE_MS = 5000

_FONT = "'Segoe UI', 'Segoe UI Variable', sans-serif"

_QSS = """
#splashCard {{
    background-color: {bg};
    border-radius: {radius}px;
}}
#lbl_name {{
    color: {text};
    font-family: {font};
    font-size: 26pt;
    font-weight: bold;
}}
#lbl_tagline, #lbl_version, #lbl_status {{
    font-family: {font};
    font-size: 10pt;
}}
#lbl_tagline, #lbl_status {{ color: {text}; }}
#lbl_version {{ color: {accent}; }}
#separator {{
    border: none;
    border-top: 1px solid {rule};
    margin-left: 20px;
    margin-right: 20px;
}}
""".format(bg=BG, text=TEXT_FG, accent=ACCENT, font=_FONT,
           radius=CORNER_RADIUS,
           # GTK's themed Gtk.Separator on this background reads as a faint
           # lightening of it, not a hard line.
           rule="#33475b")


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
        self.setObjectName("SplashScreen")
        # Rounded corners only work if the top level is transparent - otherwise
        # the window's own square background paints over them.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle(APP_NAME)

        self.ui.lbl_logo.setPixmap(logo_pixmap(LOGO_HEIGHT))
        self.ui.lbl_name.setText(APP_NAME)
        self.ui.lbl_version.setText("v%s" % __version__)
        self.setStyleSheet(_QSS)

        self.adjustSize()       # content-sized, like the old non-resizable window
        self.setFixedSize(self.sizeHint())
        self._centre()

    def _centre(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(geo.center() - self.rect().center())

    def set_message(self, text: str) -> None:
        """Update the bottom status line (the old app's set_message)."""
        self.ui.lbl_status.setText(text)
        QApplication.processEvents()   # the old one pumped GTK here too

    def hold_for(self, min_visible_ms: int, started: float) -> None:
        """Block until `min_visible_ms` has passed since `started` (a
        time.monotonic() stamp), pumping events so the splash stays painted.

        The old app's close() did exactly this - sleep(0.1) in a loop while
        draining the GTK queue - so the splash is guaranteed its full five
        seconds however fast the machine is.
        """
        while True:
            remaining = min_visible_ms / 1000.0 - (time.monotonic() - started)
            if remaining <= 0:
                break
            time.sleep(min(0.1, remaining))
            QApplication.processEvents()


def show_splash() -> tuple["SplashScreen", float]:
    """Create, show and paint the splash immediately (before the main window is
    built). Returns the splash and a start timestamp for `hold_for`."""
    splash = SplashScreen()
    splash.show()
    QApplication.processEvents()  # paint it now, before the slow window build
    return splash, time.monotonic()
