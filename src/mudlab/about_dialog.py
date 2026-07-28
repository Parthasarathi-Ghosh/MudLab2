"""About MudLab dialog. Design: ui/about.ui.

The old app used a Gtk.AboutDialog; this is the Qt equivalent - the MudLab logo,
name, version and one-line description, plus the runtime library versions filled
in at open time.
"""

from __future__ import annotations

import platform

import matplotlib
import numpy as np
import scipy
from PySide6 import __version__ as PYSIDE6_VERSION
from PySide6.QtWidgets import QDialog, QWidget

from mudlab import APP_NAME, __version__
from mudlab.resources import app_icon, logo_pixmap
from mudlab.ui.ui_about import Ui_AboutDialog


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)
        self.setWindowIcon(app_icon())

        self.ui.lbl_logo.setPixmap(logo_pixmap(96))
        self.ui.lbl_name.setText(APP_NAME)
        # Larger, bold product name.
        font = self.ui.lbl_name.font()
        font.setPointSize(font.pointSize() + 8)
        font.setBold(True)
        self.ui.lbl_name.setFont(font)

        self.ui.lbl_version.setText("Version %s" % __version__)
        self.ui.lbl_libs.setText(
            "Python %s · PySide6 %s · NumPy %s · SciPy %s · Matplotlib %s"
            % (platform.python_version(), PYSIDE6_VERSION,
               np.__version__, scipy.__version__, matplotlib.__version__)
        )

        self.ui.buttonBox.rejected.connect(self.reject)
