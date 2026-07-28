"""Main window logic. The design lives in ui/main_window.ui (edit in Qt Designer).

Structure mirrors the GTK main window of the original MudLab
(application/glade/application.glade); the window is driven by the
Qt-signal Project/Specimen models. See ui/WIRING.md for the mapping and
remaining ports.
"""

from __future__ import annotations

import os

import numpy as np
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QStyleFactory,
)

from mudlab import APP_NAME
from mudlab.about_dialog import AboutDialog
from mudlab.calculations import get_nm_from_2t
from mudlab.resources import app_icon
from mudlab.edit_atom_types_dialog import EditAtomTypesDialog
from mudlab.edit_markers_dialog import EditMarkersDialog
from mudlab.edit_mixtures_dialog import EditMixturesDialog
from mudlab.edit_phases_dialog import EditPhasesDialog
from mudlab.edit_project_dialog import EditProjectDialog
from mudlab.edit_specimen_dialog import EditSpecimenDialog
from mudlab.file_parsers import load_mud, save_mud
from mudlab.file_parsers.xrd_import import PATTERN_FILTERS, parse_pattern
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

# Specimen data import offers the same formats as every other pattern import
# (the shared xrd_import dispatcher): ASCII XY, .uxd, .xrdml, .rasx, Bruker RAW.
IMPORT_FILTERS = PATTERN_FILTERS
# Open accepts .mud and PyXRD .pyxrd (same ZIP+JSON container; MudLab2's
# schema loader reads both). Save is always .mud - opening a .pyxrd converts.
OPEN_PROJECT_FILTERS = (
    "MudLab / PyXRD projects (*.mud *.pyxrd);;"
    "MudLab projects (*.mud);;"
    "PyXRD projects (*.pyxrd);;"
    "All files (*.*)"
)
SAVE_PROJECT_FILTERS = "MudLab projects (*.mud);;All files (*.*)"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowIcon(app_icon())

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
        self.ui.actionRefreshGraph.triggered.connect(self._refresh_graph)
        self.ui.actionCrosshair.toggled.connect(self._on_crosshair_toggled)
        self.ui.actionShowPhases.toggled.connect(self._on_show_phases_toggled)
        self.ui.actionSamplePoint.triggered.connect(self._start_sampling)
        self.ui.actionEditMarkers.triggered.connect(self._show_edit_markers)
        self.ui.actionEditProject.triggered.connect(self._show_edit_project)
        self.ui.actionEditPhases.triggered.connect(self._show_edit_phases)
        self.ui.actionEditAtomTypes.triggered.connect(self._show_edit_atom_types)
        self.ui.actionEditMixtures.triggered.connect(self._show_edit_mixtures)
        self.ui.actionAddSpecimen.triggered.connect(self._add_specimen)
        self.ui.actionImportSpecimens.triggered.connect(self._import_specimens)

        # Specimen-operation dialogs (modal). Each binds the selected specimen
        # and applies its operation on OK. The old app opened these from the
        # Edit Specimen controller, so they always had a specimen; here they
        # live on the menu, so they are disabled unless exactly one specimen
        # with data is selected (_update_data_op_actions).
        self._data_op_actions = []
        for action, dialog_cls in (
            (self.ui.actionRemoveBackground, RemoveBackgroundDialog),
            (self.ui.actionSmoothData, SmoothDataDialog),
            (self.ui.actionShiftPattern, ShiftPatternDialog),
            (self.ui.actionAddNoise, AddNoiseDialog),
        ):
            action.triggered.connect(
                lambda _=False, cls=dialog_cls: self._run_data_op(cls)
            )
            self._data_op_actions.append(action)
        # Trim takes the whole specimen list too (it can trim all of them).
        self.ui.actionTrimData.triggered.connect(self._show_trim_data)
        self._data_op_actions.append(self.ui.actionTrimData)
        self.ui.actionSaveGraph.triggered.connect(
            lambda: SaveGraphSizeDialog(self).exec()
        )
        # Strip Peak / Peak Properties are modeless: their Sample buttons
        # pick positions on the plot, so the plot must stay clickable.
        self._strip_peak_dialog: StripPeakDialog | None = None
        self._peak_props_dialog: PeakPropertiesDialog | None = None
        self.ui.actionStripPeak.triggered.connect(self._show_strip_peak)
        self.ui.actionPeakProperties.triggered.connect(self._show_peak_properties)
        self._data_op_actions.append(self.ui.actionStripPeak)
        self._data_op_actions.append(self.ui.actionPeakProperties)
        self._update_data_op_actions()

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
        # Per-phase curves are transient (never saved). A project stored with
        # 'display phases separately' on should show them without a manual F5,
        # so recompute once - silently, and only when something needs it. This
        # reproduces the stored calculated pattern while capturing phase_patterns.
        if any(s is not None and s.display_phases for s in project.specimens):
            project.blockSignals(True)
            try:
                for mixture in project.mixtures:
                    mixture.calculate()
            finally:
                project.blockSignals(False)
        if project.specimens:
            # Old app auto-selected the first specimen after loading.
            self.select_specimen_row(0)
        else:
            self.show_specimen_plots([])
        # Explicitly, not via the selection signal: swapping to a project with
        # no specimens changes no selection, so nothing would fire and the data
        # operations would stay enabled with nothing to act on.
        self._update_data_op_actions()
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
            self, "Load project", "", OPEN_PROJECT_FILTERS
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
        # A .pyxrd is a PyXRD project in the same container - MudLab2 reads it
        # directly (its schema loader needs none of the old app's "slip"
        # class-path remap; the modeled data is already .mud-standard). Treat
        # opening one as a CONVERSION: retarget the save to the .mud sibling so
        # the original .pyxrd is never overwritten and Save writes a proper
        # .mud (save_mud adds the version part), and mark it unsaved.
        is_pyxrd = path.lower().endswith(".pyxrd")
        if is_pyxrd:
            project.filename = os.path.splitext(path)[0] + ".mud"
        self._set_project(project)
        if is_pyxrd:
            self._dirty = True  # the conversion is not yet written
            self.ui.statusBar.showMessage(
                "Imported %s - Save to convert it to a .mud project"
                % os.path.basename(path), 8000
            )
        else:
            self.ui.statusBar.showMessage(f"Loaded {path}", 5000)

    def _save_project(self) -> None:
        if self.project.filename:
            self._save_to(self.project.filename)
        else:
            self._save_project_as()

    def _save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save project", self.project.filename or "", SAVE_PROJECT_FILTERS
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

        self._sync_show_phases_action()
        self._rebuild_nav_toolbar()

    def _refresh_graph(self) -> None:
        """Refresh all mixtures, then redraw (old on_refresh_graph ->
        update_all_mixtures + redraw_plot). F5.

        project.refresh() optimises the mixtures whose auto_run flag is set and
        re-applies the rest, so this can run the L-BFGS-B refinement - hence
        the busy cursor and the UI-boundary error guard (the optimizer core
        fails loud; this keeps the app alive). Each mixture stores its result
        on the specimens, whose data_changed refreshes the plot; an explicit
        refresh covers the no-mixture case."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.project.refresh()
        except Exception as exc:  # noqa: BLE001 - surface, don't crash
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self, "Refresh failed",
                "Refreshing the calculated patterns failed:\n\n%s" % exc,
            )
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._refresh_plots()

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

    def _on_show_phases_toggled(self, enabled: bool) -> None:
        """Bulk-flip 'display phases separately' on the shown specimens.

        This is a convenience over the per-specimen toggles (specimen dialog /
        specimens tree); the checkmark is kept in step with those by
        _sync_show_phases_action on every rebuild. When switched on before any
        mixture has been refreshed the per-phase curves have not been captured
        yet, so recompute once (no refinement) to populate them. Project
        signals are muted so the loop redraws just once at the end."""
        specimens = [s for s in self._shown_specimens if s is not None]
        if not specimens:
            return
        need_calc = enabled and not any(
            getattr(s, "phase_patterns", None) for s in specimens
        )
        self.project.blockSignals(True)
        try:
            if need_calc:
                for mixture in self.project.mixtures:
                    mixture.calculate()
            for spec in specimens:
                spec.display_phases = enabled
        finally:
            self.project.blockSignals(False)
        self._refresh_plots()

    def _sync_show_phases_action(self) -> None:
        """Reflect the shown specimens' display_phases in the View toggle
        without re-entering the toggle handler (checkmark only, no model
        change), so per-specimen edits keep it honest."""
        specimens = [s for s in self._shown_specimens if s is not None]
        on = bool(specimens) and all(s.display_phases for s in specimens)
        action = self.ui.actionShowPhases
        if action.isChecked() != on:
            blocked = action.blockSignals(True)
            action.setChecked(on)
            action.blockSignals(blocked)

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

    # ------------------------------------------------------------------
    # Live data-op preview overlay (used by the line/data-op dialogs)
    # ------------------------------------------------------------------
    def set_pattern_preview(self, specimen, x, y, show_original: bool = True) -> None:
        """Show a data-op preview curve for `specimen` on whichever plot(s)
        display it. `show_original` keeps the original experimental line under
        the preview."""
        for plot in self.pattern_plots:
            if specimen in plot.specimens:
                plot.set_preview(specimen, x, y, show_original)

    def clear_pattern_preview(self) -> None:
        for plot in self.pattern_plots:
            plot.clear_preview()

    def set_mineral_preview(self, specimen, peaks) -> None:
        """Set the Match Minerals reference-peak overlay for `specimen` and
        redraw the plot(s) showing it IN PLACE (no full rebuild), so a mineral
        selection stays cheap and never discards an active data-op preview or
        the user's zoom."""
        specimen.mineral_preview = list(peaks) if peaks else None
        for plot in self.pattern_plots:
            if specimen in plot.specimens:
                plot.refresh()

    def clear_mineral_preview(self, specimen) -> None:
        self.set_mineral_preview(specimen, None)

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
        self._update_data_op_actions()

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
                x, y = parse_pattern(path)
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
        # Modeless; rebuilt per open so it reflects the current project's
        # phases (phases belong to the project). Editing name / sigma* / CSDS
        # mean recomputes the pattern live.
        if self._edit_phases_dialog is not None:
            self._edit_phases_dialog.close()
        self._edit_phases_dialog = EditPhasesDialog(self, project=self.project)
        self._edit_phases_dialog.show()
        self._edit_phases_dialog.raise_()
        self._edit_phases_dialog.activateWindow()

    def _show_edit_atom_types(self) -> None:
        # Modeless; rebuilt per open so it reflects the current project's
        # atom types (atom types belong to the project).
        if self._edit_atom_types_dialog is not None:
            self._edit_atom_types_dialog.close()
        self._edit_atom_types_dialog = EditAtomTypesDialog(self, project=self.project)
        self._edit_atom_types_dialog.show()

    def _show_edit_mixtures(self) -> None:
        # Modeless; rebuilt per open so it reflects the current project's
        # mixtures (mixtures belong to the project). Editing a fraction /
        # scale / background recomputes the pattern live.
        if self._edit_mixtures_dialog is not None:
            self._edit_mixtures_dialog.close()
        self._edit_mixtures_dialog = EditMixturesDialog(self, project=self.project)
        self._edit_mixtures_dialog.show()
        self._edit_mixtures_dialog.raise_()
        self._edit_mixtures_dialog.activateWindow()

    # ------------------------------------------------------------------
    # Data operations (old: the Edit Specimen controller's line dialogs)
    # ------------------------------------------------------------------
    def _data_op_specimen(self):
        """The specimen the data operations target: the selected one, when
        exactly one with experimental data is selected."""
        specimens = self._selected_specimens()
        if len(specimens) == 1 and specimens[0].has_experimental_data:
            return specimens[0]
        return None

    def _update_data_op_actions(self) -> None:
        """Grey out the data operations when there is nothing to operate on -
        an enabled button that silently does nothing is worse than a disabled
        one."""
        enabled = self._data_op_specimen() is not None
        for action in self._data_op_actions:
            action.setEnabled(enabled)
            action.setToolTip(
                "" if enabled
                else "Select a single specimen with experimental data first."
            )

    def _run_data_op(self, dialog_cls) -> None:
        specimen = self._data_op_specimen()
        if specimen is None:
            return
        dialog_cls(self, specimen=specimen).exec()

    def _show_trim_data(self) -> None:
        specimen = self._data_op_specimen()
        if specimen is None:
            return
        TrimDataDialog(
            self, specimen=specimen, specimens=list(self.project.specimens)
        ).exec()

    def _show_strip_peak(self) -> None:
        specimen = self._data_op_specimen()
        if specimen is None:
            return
        # Rebuilt per open so it binds the current selection (the modeless
        # dialog would otherwise keep operating on a stale specimen).
        if self._strip_peak_dialog is not None:
            self._strip_peak_dialog.close()
        self._strip_peak_dialog = StripPeakDialog(self, specimen=specimen)
        self._strip_peak_dialog.show()
        self._strip_peak_dialog.raise_()
        self._strip_peak_dialog.activateWindow()

    def _show_peak_properties(self) -> None:
        specimen = self._data_op_specimen()
        if specimen is None:
            return
        if self._peak_props_dialog is not None:
            self._peak_props_dialog.close()
        self._peak_props_dialog = PeakPropertiesDialog(self, specimen=specimen)
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
        AboutDialog(self).exec()
