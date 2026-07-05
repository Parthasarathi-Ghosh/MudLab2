"""Main window logic. The design lives in ui/main_window.ui (edit in Qt Designer).

Structure mirrors the GTK main window of the original MudLab
(application/glade/application.glade). See ui/WIRING.md for the mapping of
every widget/action and what still needs to be connected as the port
progresses.
"""

from __future__ import annotations

import platform

import matplotlib
import numpy as np
import scipy
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6 import __version__ as PYSIDE6_VERSION
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSizePolicy,
    QStyleFactory,
)

from mudlab import APP_NAME, __version__
from mudlab.edit_project_dialog import EditProjectDialog
from mudlab.edit_specimen_dialog import EditSpecimenDialog
from mudlab.ui.ui_main_window import Ui_MainWindow

TITLE_FORMAT = "MudLab - {}"

NAV_HINTS = "Zoom - Ctrl++ / Ctrl+-   |   Reset - Ctrl+0"

# Chart colors: validated light-mode palette (surface, ink, hairlines, series hue).
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES_BLUE = "#2a78d6"

# Minimum height of one plot in the portrait stack; a single plot expands
# to fill the viewport, multiple plots overflow into the vertical scrollbar.
PLOT_MIN_HEIGHT = 340

ZOOM_STEP = 1.25

# Specimens panel columns (old: 'Exp'/'Cal'/'Sep' toggle columns).
SPECIMEN_COLUMNS = ("Specimen", "Exp", "Cal", "Sep")
SPECIMEN_COLUMN_TOOLTIPS = (
    "Specimen name",
    "Show experimental pattern",
    "Show calculated pattern",
    "Show phase patterns separately",
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.canvases: list[FigureCanvasQTAgg] = []
        self.nav_toolbar: NavigationToolbar2QT | None = None

        self._setup_plot_area()
        self._setup_specimens_panel()
        self._setup_status_bar()

        # The dock's own show/hide action, offered in the View menu.
        toggle_dock = self.ui.specimensDock.toggleViewAction()
        toggle_dock.setText("Specimens panel")
        self.ui.menuView.addSeparator()
        self.ui.menuView.addAction(toggle_dock)
        self.resizeDocks([self.ui.specimensDock], [260], Qt.Orientation.Horizontal)

        self._edit_project_dialog: EditProjectDialog | None = None
        self._edit_specimen_dialog: EditSpecimenDialog | None = None

        self.ui.actionQuit.triggered.connect(self.close)
        self.ui.actionAbout.triggered.connect(self._show_about)
        self.ui.actionEditProject.triggered.connect(self._show_edit_project)
        self.ui.actionShowPlotToolbar.toggled.connect(self._set_plot_toolbar_visible)
        self.ui.actionZoomIn.triggered.connect(lambda: self._zoom_x(1.0 / ZOOM_STEP))
        self.ui.actionZoomOut.triggered.connect(lambda: self._zoom_x(ZOOM_STEP))
        self.ui.actionZoomReset.triggered.connect(self._zoom_reset)
        # Remaining actions are wired up as their controllers/dialogs get
        # ported (see ui/WIRING.md).

        # Like the old app: auto-select the first specimen so a plot shows.
        self.ui.specimensTree.setCurrentIndex(self.specimens_model.index(0, 0))

    def set_project_title(self, project_name: str) -> None:
        """Old AppView had title_format 'MudLab - %s' (project name)."""
        self.setWindowTitle(TITLE_FORMAT.format(project_name))

    # ------------------------------------------------------------------
    # Plot area: a portrait stack of one canvas per selected specimen
    # ------------------------------------------------------------------
    def _setup_plot_area(self) -> None:
        # The windows11 style draws transient (auto-hiding) overlay
        # scrollbars; the plot area must keep classic, always-visible ones.
        self._classic_style = QStyleFactory.create("windowsvista")
        if self._classic_style is not None:
            for bar in (
                self.ui.plotScrollArea.verticalScrollBar(),
                self.ui.plotScrollArea.horizontalScrollBar(),
            ):
                bar.setStyle(self._classic_style)

    def show_specimen_plots(self, names: list[str]) -> None:
        """Fill the portrait stack with one plot per selected specimen."""
        while self.ui.plotStackLayout.count():
            item = self.ui.plotStackLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.canvases.clear()

        for name in names:
            figure = Figure(facecolor=SURFACE, layout="constrained")
            canvas = FigureCanvasQTAgg(figure)
            canvas.setMinimumHeight(PLOT_MIN_HEIGHT)
            canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._plot_placeholder_pattern(figure, name)
            self.ui.plotStackLayout.addWidget(canvas)
            self.canvases.append(canvas)

        self._rebuild_nav_toolbar()

    def _rebuild_nav_toolbar(self) -> None:
        # The Matplotlib navigation toolbar binds to a single canvas; bind
        # it to the top plot of the stack (placeholder until the plot
        # controller port decides otherwise).
        if self.nav_toolbar is not None:
            self.removeToolBar(self.nav_toolbar)
            self.nav_toolbar.deleteLater()
            self.nav_toolbar = None
        if self.canvases:
            self.nav_toolbar = NavigationToolbar2QT(self.canvases[0], self)
            self.nav_toolbar.setObjectName("navToolbar")
            self.nav_toolbar.setWindowTitle("Plot toolbar")
            self.addToolBar(self.nav_toolbar)
            self.nav_toolbar.setVisible(self.ui.actionShowPlotToolbar.isChecked())

    def _set_plot_toolbar_visible(self, visible: bool) -> None:
        if self.nav_toolbar is not None:
            self.nav_toolbar.setVisible(visible)

    # ------------------------------------------------------------------
    # Zooming (keyboard: Ctrl++ / Ctrl+- / Ctrl+0)
    # ------------------------------------------------------------------
    def _zoom_x(self, factor: float) -> None:
        """Scale the x-range of every shown plot around its center."""
        for canvas in self.canvases:
            for axes in canvas.figure.axes:
                x0, x1 = axes.get_xlim()
                center = (x0 + x1) / 2.0
                half = (x1 - x0) / 2.0 * factor
                axes.set_xlim(center - half, center + half)
            canvas.draw_idle()

    def _zoom_reset(self) -> None:
        for canvas in self.canvases:
            for axes in canvas.figure.axes:
                axes.autoscale()
            canvas.draw_idle()

    # ------------------------------------------------------------------
    # Specimens dock
    # ------------------------------------------------------------------
    def _setup_specimens_panel(self) -> None:
        self.specimens_model = QStandardItemModel(0, len(SPECIMEN_COLUMNS), self)
        self.specimens_model.setHorizontalHeaderLabels(list(SPECIMEN_COLUMNS))
        for col, tooltip in enumerate(SPECIMEN_COLUMN_TOOLTIPS):
            self.specimens_model.setHeaderData(
                col, Qt.Orientation.Horizontal, tooltip, Qt.ItemDataRole.ToolTipRole
            )
        self.ui.specimensTree.setModel(self.specimens_model)

        header = self.ui.specimensTree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(SPECIMEN_COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        # One plot per selected row; Shift/Ctrl+click stacks several.
        self.ui.specimensTree.selectionModel().selectionChanged.connect(
            self._on_specimen_selection_changed
        )
        # Old app: double-click (row-activated) opened Edit Specimen.
        self.ui.specimensTree.doubleClicked.connect(self._on_specimen_double_clicked)

        # Placeholder rows until the project model is ported.
        for name in ("Specimen A", "Specimen B", "Specimen C"):
            self.add_specimen_row(name)

    def add_specimen_row(
        self, name: str, exp: bool = True, cal: bool = True, sep: bool = False
    ) -> None:
        name_item = QStandardItem(name)
        name_item.setEditable(False)
        row = [name_item]
        for checked in (exp, cal, sep):
            item = QStandardItem()
            item.setEditable(False)
            item.setCheckable(True)
            item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
            row.append(item)
        self.specimens_model.appendRow(row)

    def _on_specimen_selection_changed(self, *_args) -> None:
        selection = self.ui.specimensTree.selectionModel().selectedRows(0)
        names = [index.data() for index in sorted(selection, key=lambda i: i.row())]
        self.show_specimen_plots(names)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------
    def _setup_status_bar(self) -> None:
        # Old statusbar_box: lbl_nav_hints | statusbar (+ status_progress) | lbl_plot_info
        self.lbl_nav_hints = QLabel(NAV_HINTS)
        self.ui.statusBar.addWidget(self.lbl_nav_hints)

        self.status_progress = QProgressBar()
        self.status_progress.setMaximumWidth(160)
        self.status_progress.setVisible(False)
        self.ui.statusBar.addPermanentWidget(self.status_progress)

        self.lbl_plot_info = QLabel()
        self.lbl_plot_info.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.ui.statusBar.addPermanentWidget(self.lbl_plot_info)

    # ------------------------------------------------------------------
    # Status readouts (ported from AppView.update_plot_status*)
    # ------------------------------------------------------------------
    def update_plot_status(
        self,
        angularpos: float | None,
        dspacing: float | None,
        experimental: float | None = None,
        calculated: float | None = None,
        multi: bool = False,
    ) -> None:
        text = ""
        if angularpos is not None:
            d_mark = "*" if multi else ""
            text = "2θ=% 3.2f °    d=% 3.3f%s nm" % (angularpos, dspacing, d_mark)
            if experimental is not None:
                text += "    Ie=% 5d" % experimental
            if calculated is not None:
                text += "    Ic=% 5d" % calculated
        self.lbl_plot_info.setText(text)

    def update_plot_status_range(
        self, x0: float, x1: float, d0: float, d1: float, multi: bool = False
    ) -> None:
        d_mark = "*" if multi else ""
        self.lbl_plot_info.setText(
            "Δ 2θ=% 3.2f °    Δ d=% 3.3f%s nm"
            % (abs(x1 - x0), abs(d1 - d0), d_mark)
        )

    # ------------------------------------------------------------------
    # Placeholder pattern until the real plot controller is ported
    # ------------------------------------------------------------------
    @staticmethod
    def _plot_placeholder_pattern(figure: Figure, name: str) -> None:
        """Draw a fake diffraction pattern so the layout can be judged."""
        rng = np.random.default_rng(abs(hash(name)) % (2**32))
        two_theta = np.linspace(2.0, 52.0, 1200)
        pattern = np.zeros_like(two_theta) + 40.0
        for _ in range(6):
            pos = rng.uniform(5.0, 48.0)
            width = rng.uniform(0.15, 0.6)
            height = rng.uniform(200.0, 1400.0)
            pattern += height * np.exp(-0.5 * ((two_theta - pos) / width) ** 2)
        experimental = pattern + rng.normal(0.0, 18.0, two_theta.size)

        axes = figure.add_subplot(111)
        axes.plot(
            two_theta, experimental,
            color=INK_MUTED, linewidth=0.8, alpha=0.6, label="Experimental",
        )
        axes.plot(two_theta, pattern, color=SERIES_BLUE, linewidth=1.6, label="Calculated")

        axes.set_facecolor(SURFACE)
        axes.set_title(name, color=INK_PRIMARY, fontsize="medium", loc="left")
        axes.set_xlabel("2θ (°)", color=INK_SECONDARY)
        axes.set_ylabel("Intensity (counts)", color=INK_SECONDARY)
        axes.tick_params(colors=INK_MUTED)
        axes.grid(True, color=GRIDLINE, linewidth=0.8)
        axes.set_axisbelow(True)
        for side in ("top", "right"):
            axes.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            axes.spines[side].set_color(BASELINE)
        axes.legend(frameon=False, labelcolor=INK_SECONDARY, loc="upper right")

    def _on_specimen_double_clicked(self, index) -> None:
        if index.column() != 0:
            return  # double-clicks on the toggle columns just toggle
        if self._edit_specimen_dialog is None:
            self._edit_specimen_dialog = EditSpecimenDialog(self)
        dialog = self._edit_specimen_dialog
        dialog.set_specimen_name(index.data())
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _show_edit_project(self) -> None:
        # Modeless, like the old app's ProjectView.present().
        if self._edit_project_dialog is None:
            self._edit_project_dialog = EditProjectDialog(self)
        dialog = self._edit_project_dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<b>{APP_NAME}</b> {__version__}<br><br>"
            f"Python {platform.python_version()}, PySide6 {PYSIDE6_VERSION}<br>"
            f"NumPy {np.__version__}, SciPy {scipy.__version__}, "
            f"Matplotlib {matplotlib.__version__}",
        )
