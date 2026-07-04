"""Main window: menu bar, status bar, and an embedded Matplotlib canvas."""

from __future__ import annotations

import platform

import matplotlib
import numpy as np
import scipy
from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6 import __version__ as PYSIDE6_VERSION
from PySide6.QtWidgets import QMainWindow, QMessageBox, QVBoxLayout, QWidget
from scipy.signal import savgol_filter

from mudlab import APP_NAME, __version__

# Chart colors: validated light-mode palette (surface, ink, hairlines, series hue).
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES_BLUE = "#2a78d6"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1000, 700)

        self._build_menus()
        self._build_central_widget()

        self.statusBar().showMessage(
            f"Python {platform.python_version()}  |  PySide6 {PYSIDE6_VERSION}  |  "
            f"NumPy {np.__version__}  |  SciPy {scipy.__version__}  |  "
            f"Matplotlib {matplotlib.__version__}"
        )

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = help_menu.addAction(f"&About {APP_NAME}")
        about_action.triggered.connect(self._show_about)

    def _build_central_widget(self) -> None:
        figure = Figure(facecolor=SURFACE)
        canvas = FigureCanvasQTAgg(figure)
        toolbar = NavigationToolbar2QT(canvas, self)

        axes = figure.add_subplot(111)
        self._plot_demo(axes)
        figure.tight_layout()

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        self.setCentralWidget(central)

    @staticmethod
    def _plot_demo(axes: Axes) -> None:
        """Placeholder plot proving the NumPy + SciPy + Matplotlib stack works."""
        rng = np.random.default_rng(seed=42)
        x = np.linspace(0.0, 10.0, 500)
        raw = np.sin(x) * np.exp(-x / 8.0) + rng.normal(0.0, 0.08, x.size)
        smoothed = savgol_filter(raw, window_length=51, polyorder=3)

        axes.plot(x, raw, color=INK_MUTED, linewidth=1.0, alpha=0.55, label="Raw signal")
        axes.plot(x, smoothed, color=SERIES_BLUE, linewidth=2.0, label="Smoothed (Savitzky-Golay)")

        axes.set_facecolor(SURFACE)
        axes.set_title("MudLab environment check", color=INK_PRIMARY)
        axes.set_xlabel("x", color=INK_SECONDARY)
        axes.set_ylabel("amplitude", color=INK_SECONDARY)
        axes.tick_params(colors=INK_MUTED)
        axes.grid(True, color=GRIDLINE, linewidth=0.8)
        axes.set_axisbelow(True)
        for side in ("top", "right"):
            axes.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            axes.spines[side].set_color(BASELINE)
        axes.legend(frameon=False, labelcolor=INK_SECONDARY)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<b>{APP_NAME}</b> {__version__}<br><br>"
            f"Python {platform.python_version()}, PySide6 {PYSIDE6_VERSION}<br>"
            f"NumPy {np.__version__}, SciPy {scipy.__version__}, "
            f"Matplotlib {matplotlib.__version__}",
        )
