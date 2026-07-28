"""Bundled branding assets (icons / logo).

The application icon and logo are the original MudLab icons, shipped under
``data/icons/`` so they are available in both a source run and the frozen build
(MudLab.spec bundles the whole ``data`` tree).
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

_ICON_DIR = os.path.join(os.path.dirname(__file__), "data", "icons")

# Windows-facing .ico used for the frozen executable (see MudLab.spec).
APP_ICO = os.path.join(_ICON_DIR, "mudlab.ico")

_ICON_SIZES = (16, 24, 32, 48, 64, 128)


def icon_path(name: str) -> str:
    return os.path.join(_ICON_DIR, name)


def app_icon() -> QIcon:
    """The application icon (taskbar / window title bar / About), built from the
    per-size PNGs so Qt picks the crispest one; falls back to the multi-res
    ``.ico`` or the large PNG."""
    icon = QIcon()
    for size in _ICON_SIZES:
        path = icon_path("mudlab_icon_%dx%d.png" % (size, size))
        if os.path.isfile(path):
            icon.addFile(path)
    if icon.isNull():
        for fallback in (APP_ICO, icon_path("mudlab.png")):
            if os.path.isfile(fallback):
                icon.addFile(fallback)
                break
    return icon


def logo_pixmap(size: int = 96) -> QPixmap:
    """The MudLab logo scaled to `size` px square (for the About dialog)."""
    for name in ("mudlab.png", "mudlab_icon_128x128.png"):
        path = icon_path(name)
        if os.path.isfile(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return pixmap.scaled(
                    size, size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
    return QPixmap()
