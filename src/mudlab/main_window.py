"""Main window logic. The design lives in ui/main_window.ui (edit in Qt Designer).

Structure mirrors the GTK main window of the original MudLab
(application/glade/application.glade); the window is driven by the
Qt-signal Project/Specimen models. See ui/WIRING.md for the mapping and
remaining ports.
"""

from __future__ import annotations

import os
import platform

import matplotlib
import numpy as np
import scipy
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6 import __version__ as PYSIDE6_VERSION
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QStyleFactory,
)

from mudlab import APP_NAME, __version__
from mudlab.calculations import get_nm_from_2t
from mudlab.edit_atom_types_dialog import EditAtomTypesDialog
from mudlab.edit_markers_dialog import EditMarkersDialog
from mudlab.edit_mixtures_dialog import EditMixturesDialog
from mudlab.edit_phases_dialog import EditPhasesDialog
from mudlab.edit_project_dialog import EditProjectDialog
from mudlab.edit_specimen_dialog import EditSpecimenDialog
from mudlab.file_parsers import load_mud, parse_xy, save_mud
from mudlab.line_dialogs import (
    AddNoiseDialog,
    PeakPropertiesDialog,
    RemoveBackgroundDialog,
    ShiftPatternDialog,
    SmoothDataDialog,
    StripPeakDialog,
)
from mudlab.models import Project, Specimen
from mudlab.plot_controller import PatternPlot
from mudlab.specimen_dialogs import (
    SaveGraphSizeDialog,
    StatisticsDialog,
    TrimDataDialog,
)
from mudlab.specimens_model import SpecimensModel
from mudlab.ui.ui_main_window import Ui_MainWindow

TITLE_FORMAT = "MudLab - {}"

NAV_HINTS = (
    "Zoom - Scroll or Ctrl+Scroll   |   "
    "Pan - Shift+Scroll or ←→   |   Reset - Right-click"
)

ZOOM_STEP = 1.25  # Ctrl++ / Ctrl+- menu zoom

IMPORT_FILTERS = "XRD patterns (*.xy *.txt *.csv *.dat);;All files (*.*)"
PROJECT_FILTERS = "MudLab projects (*.mud);;All files (*.*)"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.project = Project(parent=self)
        self.pattern_plots: list[PatternPlot] = []
        self.nav_toolbar: NavigationToolbar2QT | None = None
        self._shown_specimens: list[Specimen] = []
        self._dirty = False
        self._pending_pick = None

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
        self._edit_phases_dialog: EditPhasesDialog | None = None
        self._edit_atom_types_dialog: EditAtomTypesDialog | None = None
        self._edit_mixtures_dialog: EditMixturesDialog | None = None
        self._edit_markers_dialog: EditMarkersDialog | None = None

        self.ui.actionQuit.triggered.connect(self.close)
        self.ui.actionAbout.triggered.connect(self._show_about)
        self.ui.actionNewProject.triggered.connect(self._new_project)
        self.ui.actionOpenProject.triggered.connect(self._open_project)
        self.ui.actionSaveProject.triggered.connect(self._save_project)
        self.ui.actionSaveProjectAs.triggered.connect(self._save_project_as)
        self.ui.actionShowPlotToolbar.toggled.connect(self._set_plot_toolbar_visible)
        self.ui.actionZoomIn.triggered.connect(lambda: self._zoom_x(1.0 / ZOOM_STEP))
        self.ui.actionZoomOut.triggered.connect(lambda: self._zoom_x(ZOOM_STEP))
        self.ui.actionZoomReset.triggered.connect(self._zoom_reset)
        self.ui.actionCrosshair.toggled.connect(self._on_crosshair_toggled)
        self.ui.actionSamplePoint.triggered.connect(self._start_sampling)
        self.ui.actionEditMarkers.triggered.connect(self._show_edit_markers)
        self.ui.actionEditProject.triggered.connect(self._show_edit_project)
        self.ui.actionEditPhases.triggered.connect(self._show_edit_phases)
        self.ui.actionEditAtomTypes.triggered.connect(self._show_edit_atom_types)
        self.ui.actionEditMixtures.triggered.connect(self._show_edit_mixtures)
        self.ui.actionAddSpecimen.triggered.connect(self._add_specimen)
        self.ui.actionImportSpecimens.triggered.connect(self._import_specimens)

        # Specimen-operation dialogs (modal; the actual data operations
        # connect to these once the calculation ports land).
        for action, dialog_cls in (
            (self.ui.actionRemoveBackground, RemoveBackgroundDialog),
            (self.ui.actionSmoothData, SmoothDataDialog),
            (self.ui.actionShiftPattern, ShiftPatternDialog),
            (self.ui.actionAddNoise, AddNoiseDialog),
            (self.ui.actionTrimData, TrimDataDialog),
            (self.ui.actionSaveGraph, SaveGraphSizeDialog),
        ):
            action.triggered.connect(
                lambda _=False, cls=dialog_cls: cls(self).exec()
            )
        # Strip Peak / Peak Properties are modeless: their Sample buttons
        # pick positions on the plot, so the plot must stay clickable.
        self._strip_peak_dialog: StripPeakDialog | None = None
        self._peak_props_dialog: PeakPropertiesDialog | None = None
        self.ui.actionStripPeak.triggered.connect(self._show_strip_peak)
        self.ui.actionPeakProperties.triggered.connect(self._show_peak_properties)

        # Model -> view plumbing.
        self._connect_project_signals(self.project)
        self._update_title()

    # ------------------------------------------------------------------
    # Project-level updates
    # ------------------------------------------------------------------
    def _connect_project_signals(self, project: Project) -> None:
        project.visuals_changed.connect(self._on_project_changed)
        project.data_changed.connect(self._refresh_plots)
        project.visuals_changed.connect(self._mark_dirty)
        project.data_changed.connect(self._mark_dirty)
        project.specimens_changed.connect(self._mark_dirty)

    def _update_title(self) -> None:
        """Old AppView had title_format 'MudLab - %s' (project name)."""
        self.setWindowTitle(TITLE_FORMAT.format(self.project.name))

    def _on_project_changed(self) -> None:
        self._update_title()
        self._refresh_plots()

    def _mark_dirty(self) -> None:
        self._dirty = True

    # ------------------------------------------------------------------
    # Project file handling (old: AppController load/save/new + the
    # confirm-discard-unsaved-changes guards)
    # ------------------------------------------------------------------
    def _set_project(self, project: Project) -> None:
        """Swap in a different project and rewire all views to it."""
        old_project = self.project
        old_model = self.specimens_model

        project.setParent(self)
        self.project = project
        self.specimens_model = SpecimensModel(project, self)
        self.ui.specimensTree.setModel(self.specimens_model)
        header = self.ui.specimensTree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, self.specimens_model.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        # setModel replaced the selection model: reconnect.
        self.ui.specimensTree.selectionModel().selectionChanged.connect(
            self._on_specimen_selection_changed
        )
        self._connect_project_signals(project)

        old_model.deleteLater()
        old_project.deleteLater()

        # Re-target open editor windows.
        if self._edit_project_dialog is not None:
            self._edit_project_dialog.bind_project(project)
        if self._edit_specimen_dialog is not None:
            self._edit_specimen_dialog.unbind()
            self._edit_specimen_dialog.close()

        self._shown_specimens = []
        self._update_title()
        if project.specimens:
            # Old app auto-selected the first specimen after loading.
            self.select_specimen_row(0)
        else:
            self.show_specimen_plots([])
        self._dirty = False

    def _confirm_discard_unsaved(self, question: str) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self, APP_NAME,
            "The current project has unsaved changes,\n" + question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def closeEvent(self, event) -> None:
        if self._confirm_discard_unsaved("are you sure you want to quit?"):
            event.accept()
        else:
            event.ignore()

    def _new_project(self) -> None:
        if not self._confirm_discard_unsaved(
            "are you sure you want to create a new project?"
        ):
            return
        self._set_project(Project())
        # Old behavior: a new project opens the Edit Project dialog.
        self._show_edit_project()

    def _open_project(self) -> None:
        if not self._confirm_discard_unsaved(
            "are you sure you want to load another project?"
        ):
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Load project", "", PROJECT_FILTERS
        )
        if not path:
            return
        try:
            project = load_mud(path)
        except Exception as error:  # zip/json/format errors
            QMessageBox.critical(
                self, "Parsing error",
                f"An error has occurred:\n{error}\nYour project was not loaded!",
            )
            return
        self._set_project(project)
        self.ui.statusBar.showMessage(f"Loaded {path}", 5000)

    def _save_project(self) -> None:
        if self.project.filename:
            self._save_to(self.project.filename)
        else:
            self._save_project_as()

    def _save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save project", self.project.filename or "", PROJECT_FILTERS
        )
        if not path:
            return
        if not path.lower().endswith(".mud"):
            path += ".mud"
        self._save_to(path)

    def _save_to(self, path: str) -> None:
        try:
            save_mud(self.project, path)
        except OSError as error:
            QMessageBox.critical(
                self, "Save error",
                f"An error has occurred while saving!\n{error}",
            )
            return
        self._dirty = False
        self.ui.statusBar.showMessage(f"Saved {path}", 5000)

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

    @property
    def canvases(self) -> list:
        return [plot.canvas for plot in self.pattern_plots]

    def show_specimen_plots(
        self, specimens: list[Specimen], restore_views: dict | None = None
    ) -> None:
        """Fill the portrait stack with one plot per selected specimen."""
        self._shown_specimens = list(specimens)
        while self.ui.plotStackLayout.count():
            item = self.ui.plotStackLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.pattern_plots.clear()

        restore_views = restore_views or {}
        # One canvas, one shared axes with all selected specimens stacked
        # (mudlab style); a single selection is just the N=1 case.
        plots = []
        if specimens:
            plots.append(
                PatternPlot(
                    specimens, self.project,
                    on_motion=self._on_plot_motion,
                    on_click=self._on_plot_click,
                    on_marker_pick=self._on_marker_picked,
                )
            )
        for plot in plots:
            plot.set_crosshair_enabled(self.ui.actionCrosshair.isChecked())
            view = restore_views.get(plot.view_key)
            if view is not None:
                plot.restore_view(view)
            self.ui.plotStackLayout.addWidget(plot.canvas)
            self.pattern_plots.append(plot)

        self._rebuild_nav_toolbar()

    def _refresh_plots(self) -> None:
        # Preserve user zoom across redraws (old update() behavior) and
        # drop deleted specimens.
        views = {
            plot.view_key: view
            for plot in self.pattern_plots
            if (view := plot.user_view()) is not None
        }
        current = tuple(self.project.specimens)
        self.show_specimen_plots(
            [s for s in self._shown_specimens if s in current],
            restore_views=views,
        )

    # ------------------------------------------------------------------
    # Plot interaction callbacks (old AppController.update_plot_status
    # and on_sample_point)
    # ------------------------------------------------------------------
    def _on_crosshair_toggled(self, enabled: bool) -> None:
        for plot in self.pattern_plots:
            plot.set_crosshair_enabled(enabled)

    # ------------------------------------------------------------------
    # Eye-dropper position picking (old EyeDropper)
    # ------------------------------------------------------------------
    def arm_position_pick(
        self, callback, hint: str = "Click a point on the pattern..."
    ) -> None:
        """Arm a one-shot pick: the next left click on a pattern calls
        callback(plot, x_pos) and disarms. Used by Select Point and the
        Sample buttons in the marker / strip-peak / peak-property dialogs."""
        self._pending_pick = callback
        self.ui.statusBar.showMessage(hint)
        for plot in self.pattern_plots:
            plot.set_pick_cursor(True)

    def _disarm_pick(self) -> None:
        self._pending_pick = None
        self.ui.statusBar.clearMessage()
        for plot in self.pattern_plots:
            plot.set_pick_cursor(False)

    def _start_sampling(self) -> None:
        # Old on_sample_point: the next click reports the data values.
        self.arm_position_pick(
            self._report_sampled_point, "Sampling... click a point on a pattern"
        )

    def _on_plot_click(self, plot: PatternPlot, x_pos: float) -> None:
        if self._pending_pick is not None and x_pos > 0:
            callback = self._pending_pick
            self._disarm_pick()
            callback(plot, x_pos)

    def _report_sampled_point(self, plot: PatternPlot, x_pos: float) -> None:
        specimen = plot.specimen
        message = "Sampled point:\n"
        if specimen.has_experimental_data:
            ex, ey = specimen.experimental_pattern
            message += "\tExperimental data:\t( %.4f , %.4f )\n" % (
                x_pos, float(np.interp(x_pos, ex, ey)),
            )
        if specimen.has_calculated_data:
            cx, cy = specimen.calculated_pattern
            message += "\tCalculated data:\t\t( %.4f , %.4f )" % (
                x_pos, float(np.interp(x_pos, cx, cy)),
            )
        QMessageBox.information(self, "Sample Point", message)

    def _on_marker_picked(self, marker) -> None:
        # Old ClickCatcher/show_marker: double-clicking a marker opens the
        # markers view with that marker selected.
        specimen = marker.specimen
        if specimen is None:
            return
        self._open_edit_markers(specimen, marker)

    def _on_plot_motion(self, plot: PatternPlot, x_pos: float) -> None:
        specimen = plot.specimen
        wavelength = specimen.wavelength
        if plot.drag_start_x is not None and x_pos > 0:
            x0, x1 = sorted((plot.drag_start_x, x_pos))
            self.update_plot_status_range(
                x0, x1,
                get_nm_from_2t(x0, wavelength),
                get_nm_from_2t(x1, wavelength),
                multi=plot.multi,
            )
        elif x_pos > 0:
            if plot.multi:
                # Old multi readout: 2θ and d (from the first specimen's
                # goniometer) only, marked with '*'.
                self.update_plot_status(
                    x_pos, get_nm_from_2t(x_pos, wavelength), multi=True
                )
                return
            experimental = calculated = None
            if specimen.has_experimental_data:
                ex, ey = specimen.experimental_pattern
                experimental = float(np.interp(x_pos, ex, ey))
            if specimen.has_calculated_data:
                cx, cy = specimen.calculated_pattern
                calculated = float(np.interp(x_pos, cx, cy))
            self.update_plot_status(
                x_pos, get_nm_from_2t(x_pos, wavelength), experimental, calculated
            )
        else:
            self.update_plot_status(None, None)

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
        for plot in self.pattern_plots:
            plot.zoom_x(factor)

    def _zoom_reset(self) -> None:
        for plot in self.pattern_plots:
            plot.reset_view()

    # ------------------------------------------------------------------
    # Specimens dock
    # ------------------------------------------------------------------
    def _setup_specimens_panel(self) -> None:
        self.specimens_model = SpecimensModel(self.project, self)
        self.ui.specimensTree.setModel(self.specimens_model)

        header = self.ui.specimensTree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, self.specimens_model.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        # One plot per selected row; Shift/Ctrl+click stacks several.
        self.ui.specimensTree.selectionModel().selectionChanged.connect(
            self._on_specimen_selection_changed
        )
        # Old app: double-click (row-activated) opened Edit Specimen.
        self.ui.specimensTree.doubleClicked.connect(self._on_specimen_double_clicked)

        # Old specimen_popup context menu on the specimens tree.
        self.ui.specimensTree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.ui.specimensTree.customContextMenuRequested.connect(
            self._show_specimens_menu
        )

    def _build_specimens_menu(self) -> QMenu:
        """Old specimen_popup: add/import, then per-specimen actions."""
        specimens = self._selected_specimens()
        single = len(specimens) == 1
        menu = QMenu(self)
        menu.addAction(self.ui.actionAddSpecimen)
        menu.addAction(self.ui.actionImportSpecimens)
        menu.addSeparator()

        act_edit = menu.addAction("Edit specimen")
        act_edit.setEnabled(single)
        act_edit.triggered.connect(lambda: self._show_edit_specimen(specimens[0]))

        act_markers = menu.addAction("Edit markers")
        act_markers.setEnabled(single)
        act_markers.triggered.connect(self._show_edit_markers)

        act_stats = menu.addAction("View statistics")
        act_stats.setEnabled(single)
        act_stats.triggered.connect(lambda: self._show_statistics(specimens[0]))

        menu.addSeparator()
        act_remove = menu.addAction("Remove specimen")
        act_remove.setEnabled(bool(specimens))
        act_remove.triggered.connect(lambda: self._remove_specimens(specimens))
        return menu

    def _show_specimens_menu(self, pos) -> None:
        menu = self._build_specimens_menu()
        menu.exec(self.ui.specimensTree.viewport().mapToGlobal(pos))

    def select_specimen_row(self, row: int) -> None:
        if 0 <= row < self.specimens_model.rowCount():
            self.ui.specimensTree.setCurrentIndex(self.specimens_model.index(row, 0))

    def _selected_specimens(self) -> list[Specimen]:
        selection = self.ui.specimensTree.selectionModel().selectedRows(0)
        rows = sorted(index.row() for index in selection)
        return [self.specimens_model.specimen_at(row) for row in rows]

    def _on_specimen_selection_changed(self, *_args) -> None:
        self.show_specimen_plots(self._selected_specimens())

    def _on_specimen_double_clicked(self, index) -> None:
        if index.column() != 0:
            return  # double-clicks on the toggle columns just toggle
        self._show_edit_specimen(self.specimens_model.specimen_at(index.row()))

    # ------------------------------------------------------------------
    # Specimen actions (old: project controller add/import)
    # ------------------------------------------------------------------
    def _add_specimen(self) -> None:
        specimen = Specimen(name=f"Specimen {len(self.project.specimens) + 1}")
        self.project.add_specimen(specimen)
        self.select_specimen_row(self.specimens_model.rowCount() - 1)

    def _remove_specimens(self, specimens: list[Specimen]) -> None:
        if not specimens:
            return
        count = len(specimens)
        what = specimens[0].name if count == 1 else f"{count} specimens"
        if QMessageBox.question(
            self, "Remove Specimen",
            f"Remove {what} from the project?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        # Row to land on afterwards: the first removed specimen's position,
        # clamped to what remains (rebuilding the dock model clears the
        # tree selection, so restore a sensible one - old app kept one).
        try:
            landing_row = min(self.project.specimens.index(s) for s in specimens)
        except ValueError:
            landing_row = 0
        for specimen in specimens:
            self.project.remove_specimen(specimen)
        remaining = self.specimens_model.rowCount()
        if remaining:
            self.select_specimen_row(min(landing_row, remaining - 1))
        else:
            self.show_specimen_plots([])

    def _show_statistics(self, specimen: Specimen) -> None:
        # Old view_statistics action (specimens context menu).
        dialog = StatisticsDialog(self)
        dialog.setWindowTitle(f"Statistics - {specimen.name}")
        stats = specimen.statistics
        if stats.has_data:
            # χ² field shows the reduced chi-squared (= GoF²).
            dialog.set_statistics(
                stats.points, stats.GoF ** 2, stats.R2, stats.Rp, stats.Rwp, stats.Re
            )
        dialog.exec()

    def _import_specimens(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import specimens", "", IMPORT_FILTERS
        )
        if paths:
            self.import_specimen_files(paths)

    def import_specimen_files(self, paths: list[str]) -> list[Specimen]:
        imported: list[Specimen] = []
        errors: list[str] = []
        first_new_row = self.specimens_model.rowCount()
        for path in paths:
            try:
                x, y = parse_xy(path)
            except (OSError, ValueError) as error:
                errors.append(str(error))
                continue
            specimen = Specimen(name=os.path.splitext(os.path.basename(path))[0])
            specimen.set_experimental_pattern(x, y)
            self.project.add_specimen(specimen)
            imported.append(specimen)

        if imported:
            # Old app auto-selected the first specimen after loading.
            self.select_specimen_row(first_new_row)
        if errors:
            QMessageBox.warning(
                self, "Import specimens",
                "Some files could not be imported:\n\n" + "\n".join(errors),
            )
        return imported

    # ------------------------------------------------------------------
    # Editor windows
    # ------------------------------------------------------------------
    def _show_edit_specimen(self, specimen: Specimen) -> None:
        if self._edit_specimen_dialog is None:
            self._edit_specimen_dialog = EditSpecimenDialog(self)
        dialog = self._edit_specimen_dialog
        dialog.bind_specimen(specimen)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _show_edit_project(self) -> None:
        # Modeless, like the old app's ProjectView.present().
        if self._edit_project_dialog is None:
            self._edit_project_dialog = EditProjectDialog(self)
            self._edit_project_dialog.bind_project(self.project)
        dialog = self._edit_project_dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _show_edit_phases(self) -> None:
        # Modeless, like the old app's phases view present().
        if self._edit_phases_dialog is None:
            self._edit_phases_dialog = EditPhasesDialog(self)
        dialog = self._edit_phases_dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _show_edit_atom_types(self) -> None:
        # Modeless; rebuilt per open so it reflects the current project's
        # atom types (atom types belong to the project).
        if self._edit_atom_types_dialog is not None:
            self._edit_atom_types_dialog.close()
        self._edit_atom_types_dialog = EditAtomTypesDialog(self, project=self.project)
        self._edit_atom_types_dialog.show()

    def _show_edit_mixtures(self) -> None:
        # Modeless, like the old app's mixtures view present().
        if self._edit_mixtures_dialog is None:
            self._edit_mixtures_dialog = EditMixturesDialog(self)
        dialog = self._edit_mixtures_dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _show_strip_peak(self) -> None:
        if self._strip_peak_dialog is None:
            self._strip_peak_dialog = StripPeakDialog(self)
        self._strip_peak_dialog.show()
        self._strip_peak_dialog.raise_()
        self._strip_peak_dialog.activateWindow()

    def _show_peak_properties(self) -> None:
        if self._peak_props_dialog is None:
            self._peak_props_dialog = PeakPropertiesDialog(self)
        self._peak_props_dialog.show()
        self._peak_props_dialog.raise_()
        self._peak_props_dialog.activateWindow()

    def _show_edit_markers(self) -> None:
        # Old edit_markers action: markers belong to the current specimen.
        specimens = self._selected_specimens()
        if len(specimens) == 1:
            self._open_edit_markers(specimens[0])

    def _open_edit_markers(self, specimen, marker=None) -> None:
        # Rebuilt each time so it targets the given specimen (old app reset
        # the markers view per specimen selection).
        if self._edit_markers_dialog is not None:
            self._edit_markers_dialog.close()
        self._edit_markers_dialog = EditMarkersDialog(self, specimen=specimen)
        self._edit_markers_dialog.show()
        if marker is not None:
            self._edit_markers_dialog.select_marker(marker)

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

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<b>{APP_NAME}</b> {__version__}<br><br>"
            f"Python {platform.python_version()}, PySide6 {PYSIDE6_VERSION}<br>"
            f"NumPy {np.__version__}, SciPy {scipy.__version__}, "
            f"Matplotlib {matplotlib.__version__}",
        )
