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
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
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
from mudlab.file_parsers.xrd_import import (
    PATTERN_FILTERS,
    build_source_string,
    parse_pattern,
    parse_pattern_metadata,
)
from mudlab.line_dialogs import (
    AddNoiseDialog,
    PeakPropertiesDialog,
    RemoveBackgroundDialog,
    ShiftPatternDialog,
    SmoothDataDialog,
    StripPeakDialog,
)
from mudlab.manual_dialog import (
    HOME_DOCUMENT, SCIENCE_DOCUMENT, ManualDialog,
)
from mudlab.models import Project, Specimen
from mudlab.plot_controller import PatternPlot
from mudlab.qt_utils import fixed_font, in_use_message
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
        self._pending_pick_cancel = None
        self._range_pick_callback = None

        # Esc abandons an armed Sample pick. Without it a dialog that hides
        # itself for the pick (the Peaks dialog) could never be recovered if
        # the user changed their mind and never clicked the plot.
        self._cancel_pick_shortcut = QShortcut(
            QKeySequence(Qt.Key.Key_Escape), self)
        self._cancel_pick_shortcut.activated.connect(self.cancel_position_pick)

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
        self._manual_dialog: ManualDialog | None = None

        self.ui.actionQuit.triggered.connect(self.close)
        self.ui.actionAbout.triggered.connect(self._show_about)
        self.ui.actionManual.triggered.connect(self._show_manual)
        self.ui.actionHowItWorks.triggered.connect(self._show_how_it_works)
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
        self.ui.actionEditComposition.triggered.connect(
            self._edit_composition)
        self.ui.actionRemoveComposition.triggered.connect(
            self._remove_composition)
        self.ui.menuComposition.aboutToShow.connect(self._sync_composition_menu)
        self.ui.actionExportOldMud.triggered.connect(
            lambda: self._export_project("old_mud"))
        self.ui.actionExportPyxrd.triggered.connect(
            lambda: self._export_project("pyxrd"))
        self.ui.actionAddSpecimen.triggered.connect(self._add_specimen)
        self.ui.actionImportSpecimens.triggered.connect(self._import_specimens)

        # Specimen-operation dialogs. Each binds the selected specimen and
        # applies its operation on OK. The old app opened these from the Edit
        # Specimen controller, so they always had a specimen; here they live on
        # the menu, so they are disabled unless exactly one specimen with data
        # is selected (_update_data_op_actions). All three are MODELESS (like
        # Strip Peak / Shift / Peak Properties below) so the plot stays
        # zoom/scroll-able while their live preview is judged; one open dialog
        # per class is tracked here so re-opening replaces it.
        self._data_op_dialogs: dict[type, QDialog] = {}
        self._data_op_actions = []
        for action, dialog_cls in (
            (self.ui.actionRemoveBackground, RemoveBackgroundDialog),
            (self.ui.actionSmoothData, SmoothDataDialog),
            (self.ui.actionAddNoise, AddNoiseDialog),
        ):
            action.triggered.connect(
                lambda _=False, cls=dialog_cls: self._show_data_op(cls)
            )
            self._data_op_actions.append(action)
        # Trim takes the whole specimen list too (it can trim all of them).
        self.ui.actionTrimData.triggered.connect(self._show_trim_data)
        self._data_op_actions.append(self.ui.actionTrimData)
        self.ui.actionSaveGraph.triggered.connect(self._save_graph)
        # Strip Peak / Peak Properties / Shift are modeless: Strip and Peak
        # Properties' Sample buttons pick positions on the plot, and Shift needs
        # the plot to stay interactive (zoom/scroll) while the preview is aligned
        # to the reference reflection - so the plot must stay clickable.
        self._strip_peak_dialog: StripPeakDialog | None = None
        self._peak_props_dialog: PeakPropertiesDialog | None = None
        self._shift_pattern_dialog: ShiftPatternDialog | None = None
        self.ui.actionStripPeak.triggered.connect(self._show_strip_peak)
        self.ui.actionPeakProperties.triggered.connect(self._show_peak_properties)
        self.ui.actionShiftPattern.triggered.connect(self._show_shift_pattern)
        self._data_op_actions.append(self.ui.actionStripPeak)
        self._data_op_actions.append(self.ui.actionPeakProperties)
        self._data_op_actions.append(self.ui.actionShiftPattern)
        # Fixed <-> ADS divergence-slit conversion (parameterless, so no dialog -
        # a confirmation gates the destructive rewrite).
        self.ui.actionConvertToFixed.triggered.connect(
            lambda: self._convert_slit(to_ads=False)
        )
        self.ui.actionConvertToADS.triggered.connect(
            lambda: self._convert_slit(to_ads=True)
        )
        self._data_op_actions.append(self.ui.actionConvertToFixed)
        self._data_op_actions.append(self.ui.actionConvertToADS)
        self._update_data_op_actions()

        # Goniometer edits recompute the calculated pattern, coalesced so a
        # spinbox drag does not walk every mixture per keystroke (see
        # _on_goniometer_changed). Must exist before the signals are wired.
        self._gonio_wired: list = []
        self._gonio_timer = QTimer(self)
        self._gonio_timer.setSingleShot(True)
        self._gonio_timer.setInterval(150)
        self._gonio_timer.timeout.connect(self._recompute_after_goniometer)

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
        # The measured composition, the default-phase map and the imported
        # reference phases all live on the project and are all saved with it,
        # so a change to any of them is an unsaved change. Without this the user
        # can map every phase, close, and be told there was nothing to save.
        project.composition_changed.connect(self._mark_dirty)
        # Keep the Composition menu honest from the start, not only once the
        # menu has been opened: aboutToShow alone left Remove ENABLED on a
        # project with no composition, which is wrong the moment anything but
        # the menu itself can reach the action (a shortcut, a toolbar).
        project.composition_changed.connect(self._sync_composition_menu)
        self._sync_composition_menu()
        # An added / imported specimen brings its own goniometer to listen to.
        project.specimens_changed.connect(self._wire_goniometer_signals)
        self._wire_goniometer_signals()

    # ------------------------------------------------------------------
    # Goniometer edits -> recompute (geometry is calc input, not decoration)
    # ------------------------------------------------------------------
    def _wire_goniometer_signals(self) -> None:
        """Listen to every specimen's goniometer.

        `Goniometer.data_changed` had NO listeners at all, so editing the radius,
        divergence, soller slits, sample length, the emission spectrum or loading
        a stored `.gon` setup wrote the model but left the calculated curve drawn
        with the geometry it was last computed with - and did not even mark the
        project dirty, so the edit could be lost on close without a prompt. Every
        goniometer parameter is an input to the calculation, so a change now
        recomputes. Re-wired on `specimens_changed` (and by `_set_project`, which
        re-runs `_connect_project_signals`); a specimen's goniometer object is
        only ever replaced at load time, before either of those."""
        for gonio in self._gonio_wired:
            try:
                gonio.data_changed.disconnect(self._on_goniometer_changed)
            except (RuntimeError, TypeError):
                pass  # went away with its project
        self._gonio_wired = []
        for specimen in self.project.specimens:
            gonio = getattr(specimen, "goniometer", None)
            if gonio is None:
                continue
            gonio.data_changed.connect(self._on_goniometer_changed)
            self._gonio_wired.append(gonio)

    def _on_goniometer_changed(self) -> None:
        # Dirty at once - the edit IS a change to save, even when there is no
        # mixture to recompute - but coalesce the recompute itself: a spinbox
        # drag fires per step, and each recompute walks every mixture.
        self._mark_dirty()
        self._gonio_timer.start()

    def _recompute_after_goniometer(self) -> None:
        """The coalesced recompute. `project.calculate()`, deliberately NOT
        `refresh()`: a geometry edit must not silently start the optimiser.

        The project's signals are held while it runs and the plots refreshed
        ONCE afterwards (the same trick `_set_project` uses): `calculate()`
        re-emits `data_changed` per specimen, and each of those rebuilds every
        plot, so a single edit was costing one refresh per specimen plus this
        one. `_mark_dirty` already ran in `_on_goniometer_changed`, and blocking
        the project does not silence the specimens themselves, so an open Edit
        Specimen still updates."""
        failure = None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.project.blockSignals(True)
        try:
            self.project.calculate()
        except Exception as exc:  # noqa: BLE001 - surface, don't crash the app
            failure = exc
        finally:
            self.project.blockSignals(False)
            QApplication.restoreOverrideCursor()
        if failure is not None:
            # Warn with the cursor already restored, not under a busy pointer.
            QMessageBox.warning(
                self, "Recalculation failed",
                "The goniometer change could not be applied to the calculated "
                "pattern:\n\n%s" % failure,
            )
            return
        self._refresh_plots()

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
        # Drop a goniometer recompute still pending from the OUTGOING project:
        # it would otherwise fire against the incoming one, recomputing it and
        # marking a freshly loaded project dirty.
        self._gonio_timer.stop()

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
        # Edit Atom Types lists the OLD project's types and is connected to its
        # atom_types_changed; close it rather than leave it editing a project
        # that is being detached.
        if self._edit_atom_types_dialog is not None:
            self._edit_atom_types_dialog.close()
            self._edit_atom_types_dialog = None
        # The modeless line dialogs target a specimen of the OLD project, which
        # is about to be detached: close them rather than let an OK edit it.
        self._close_specimen_dialogs()

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
                    on_range_select=self._on_plot_range_select,
                )
            )
        for plot in plots:
            plot.set_crosshair_enabled(self.ui.actionCrosshair.isChecked())
            # Keep a rebuilt plot in step with an open range-select dialog.
            if self._range_pick_callback is not None:
                plot.set_range_select_enabled(True)
                plot.set_pick_cursor(True)
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
        # display_phases is a persisted prop, so a real change should dirty the
        # project like the Sep-column / Edit-Specimen paths do - but blockSignals
        # below swallows the relayed visuals_changed (and with it _mark_dirty),
        # so note whether anything changes and dirty explicitly.
        changed = any(s.display_phases != enabled for s in specimens)
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
        if changed:
            self._mark_dirty()
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
        self, callback, hint: str = "Click a point on the pattern...",
        on_cancel=None,
    ) -> None:
        """Arm a one-shot pick: the next left click on a pattern calls
        callback(plot, x_pos) and disarms. Used by Select Point and the
        Sample buttons in the peaks / strip-peak / peak-property dialogs.

        `on_cancel` runs if the pick is abandoned instead (Esc). It exists
        because a caller may HIDE ITSELF to clear the plot - the Peaks dialog
        does - and without a cancel path an armed pick that is never clicked
        would strand that window with no way to bring it back.
        """
        # Arming twice: the first caller must be told, or it waits forever.
        self._cancel_pending_pick()
        self._pending_pick = callback
        self._pending_pick_cancel = on_cancel
        self.ui.statusBar.showMessage(hint + "   (Esc to cancel)")
        for plot in self.pattern_plots:
            plot.set_pick_cursor(True)

    def cancel_position_pick(self) -> None:
        """Abandon an armed pick and tell whoever armed it. Bound to Esc."""
        self._cancel_pending_pick()

    def _cancel_pending_pick(self) -> None:
        on_cancel = getattr(self, "_pending_pick_cancel", None)
        armed = self._pending_pick is not None
        self._disarm_pick()
        if armed and on_cancel is not None:
            on_cancel()

    def _disarm_pick(self) -> None:
        self._pending_pick = None
        self._pending_pick_cancel = None
        self.ui.statusBar.clearMessage()
        for plot in self.pattern_plots:
            plot.set_pick_cursor(False)

    def arm_range_pick(
        self, callback,
        hint: str = "Drag across the pattern to select the start and end...",
    ) -> None:
        """Arm range selection: a left-drag on a pattern highlights the swept
        span and, on release, calls ``callback(plot, x0, x1)`` (ascending 2theta).
        Unlike the one-shot position pick this STAYS armed - so the range can be
        refined by dragging again - until :meth:`disarm_range_pick`; the caller
        (a data-op dialog) disarms when it closes. Used by Strip Peak / Peak
        Properties instead of the old two eye-dropper Sample buttons."""
        self._range_pick_callback = callback
        self.ui.statusBar.showMessage(hint)
        for plot in self.pattern_plots:
            plot.set_range_select_enabled(True)
            plot.set_pick_cursor(True)

    def disarm_range_pick(self) -> None:
        self._range_pick_callback = None
        self.ui.statusBar.clearMessage()
        for plot in self.pattern_plots:
            plot.set_range_select_enabled(False)
            plot.set_pick_cursor(False)

    def _on_plot_range_select(self, plot, x0: float, x1: float) -> None:
        if self._range_pick_callback is not None:
            self._range_pick_callback(plot, x0, x1)

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

    def set_shift_reference(self, specimen, position: float) -> None:
        """Show the Shift dialog's reference line (2theta) on the plot(s) that
        display `specimen`."""
        for plot in self.pattern_plots:
            if specimen in plot.specimens:
                plot.set_shift_reference(position)

    def clear_shift_reference(self) -> None:
        for plot in self.pattern_plots:
            plot.clear_shift_reference()

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
            self._disarm_pick()   # also drops the cancel callback
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

        act_markers = menu.addAction("Peaks")
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
        # A specimen a mixture still holds is being fitted against: refuse before
        # asking anything, rather than pulling it out from under the model.
        blocked = [(s, u) for s, u in
                   ((s, self.project.specimen_usage(s)) for s in specimens) if u]
        if blocked:
            names = ", ".join(s.name or "specimen" for s, _u in blocked)
            # Several blocked specimens can sit in DIFFERENT mixtures, so merge
            # their usage - listing only the first one's would send the user to
            # the wrong place for the rest.
            merged: dict[int, tuple] = {}
            for _s, usage in blocked:
                for mixture, rows in usage:
                    hit = merged.setdefault(id(mixture), (mixture, []))
                    hit[1].extend(rows)
            QMessageBox.information(
                self, "Remove Specimen",
                in_use_message(names, "specimen", list(merged.values()),
                               subjects=len(blocked)))
            return
        count = len(specimens)
        what = specimens[0].name if count == 1 else f"{count} specimens"
        if QMessageBox.question(
            self, "Remove Specimen",
            f"Remove {what} from the project?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        # A modeless line dialog open on one of these would be left holding a
        # removed specimen, and its OK would edit it invisibly.
        self._close_specimen_dialogs(specimens)
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
            # Describe the source file (old app's source box) and, where the file
            # provides it, apply its wavelength to the specimen's goniometer.
            metadata = parse_pattern_metadata(path)
            specimen.source = build_source_string(path, x, metadata)
            if specimen.goniometer is not None:
                # Seed the calculation range from the scan, as the old app did
                # (create_gon_file -> reset_from_file). A goniometer setup
                # applied later resets all of it - this only fixes the default.
                specimen.goniometer.seed_range_from_data(x)
                ka1 = metadata.get("wavelength_ka1")
                if ka1:
                    specimen.goniometer.set_wavelength_distribution([(ka1, 1.0)])
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

    def _sync_composition_menu(self) -> None:
        """Remove is only meaningful when there IS one; Edit reads as Enter
        when there is not, so the label follows the state."""
        has = getattr(self.project, "composition", None) is not None
        self.ui.actionRemoveComposition.setEnabled(has)
        self.ui.actionEditComposition.setText(
            "&Edit composition..." if has else "&Enter composition...")

    def _remove_composition(self) -> None:
        """Delete the measured composition. Deliberately a SEPARATE action:
        opening the editor on an empty grid and accepting must never be a way to
        silently clear an analysis the user typed in."""
        composition = getattr(self.project, "composition", None)
        if composition is None:
            QMessageBox.information(
                self, "Remove composition",
                "This project has no measured composition.")
            return
        name = getattr(composition, "name", "") or "the measured composition"
        if QMessageBox.question(
            self, "Remove composition",
            "Remove %s from this project?\n\n"
            "The comparison with the model will no longer be available. This "
            "cannot be undone, but nothing is written until you save."
            % name,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self.project.set_composition(None)   # emits composition_changed -> dirty

    # ------------------------------------------------------------------
    # Export (Project > Export)
    # ------------------------------------------------------------------
    _EXPORT_TARGETS = {
        "old_mud": ("MudLab (old app)", ".mud",
                    "MudLab project (*.mud);;All files (*)"),
        "pyxrd": ("PyXRD", ".pyxrd",
                  "PyXRD project (*.pyxrd);;All files (*)"),
    }

    def _export_project(self, target: str) -> None:
        """Write a copy of the project in another app's format.

        An export never touches the project: not its filename, not its dirty
        flag. Saving and exporting are different acts, and conflating them would
        leave the user's real file silently un-saved.
        """
        from mudlab.file_parsers.exporters import (
            export_old_mud, export_pyxrd, suggested_name,
        )

        label, extension, file_filter = self._EXPORT_TARGETS[target]
        path, _filter = QFileDialog.getSaveFileName(
            self, "Export as %s" % label,
            suggested_name(self.project, extension), file_filter,
        )
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += extension
        writer = export_old_mud if target == "old_mud" else export_pyxrd
        try:
            report = writer(self.project, path)
        except Exception as exc:  # noqa: BLE001 - surface, don't crash
            QMessageBox.warning(
                self, "Export failed",
                "Could not write the file:\n\n%s" % exc)
            return
        # Say what did not survive. An export that quietly drops the measured
        # composition is worse than one that refuses.
        message = "Exported to:\n%s" % path
        if report.notes:
            message += "\n\nNot everything carries over:\n\n" + "\n\n".join(
                "\u2022 %s" % note for note in report.notes)
        QMessageBox.information(self, "Export as %s" % label, message)

    def _edit_composition(self) -> None:
        """Data -> Import composition: the sample's measured (XRF) analysis.

        A project describes ONE physical sample, so it holds at most one
        analysis: importing again EDITS the existing one (the dialog opens on
        its values) rather than adding a second. Cancelling changes nothing.
        """
        from mudlab.import_composition_dialog import ImportCompositionDialog

        existing = self.project.composition
        dialog = ImportCompositionDialog(self, composition=existing)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.composition is None:
            return
        self.project.set_composition(dialog.composition)
        self._mark_dirty()
        self.ui.statusBar.showMessage(
            "Composition %r imported (%d oxides, total %.2f %%)"
            % (dialog.composition.name, len(dialog.composition.oxides),
               dialog.composition.total()), 6000
        )

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

    def _close_specimen_dialogs(self, specimens=None) -> None:
        """Close the modeless specimen dialogs (the six line operations) that are
        bound to a specimen which is going away - all of them when `specimens` is
        None, as on a project swap.

        They are modeless, so they outlive the selection that opened them.
        Without this, removing a specimen (or loading another project) left one
        open still holding the detached Specimen, and its OK then applied a
        destructive, undoable edit to an object nothing displays - which looks
        exactly like the operation having done nothing. Each dialog's own
        close/reject drops its plot preview and disarms any range pick."""
        going = None if specimens is None else {id(s) for s in specimens}
        for dialog in (
            *self._data_op_dialogs.values(),
            self._strip_peak_dialog, self._peak_props_dialog,
            self._shift_pattern_dialog,
        ):
            if dialog is None or not dialog.isVisible():
                continue
            if going is None or id(dialog.specimen) in going:
                dialog.close()

    def _show_data_op(self, dialog_cls) -> None:
        """Open one of the parameterised data-op dialogs (Remove Background /
        Smooth / Add Noise) MODELESS, so the plot stays interactive (zoom,
        scroll) while its live preview is judged - the same treatment Strip Peak,
        Shift and Peak Properties get. Rebuilt per open so it binds the CURRENT
        selection: a dialog left open from a previous selection would otherwise
        keep operating on a stale specimen."""
        specimen = self._data_op_specimen()
        if specimen is None:
            return
        previous = self._data_op_dialogs.get(dialog_cls)
        if previous is not None:
            previous.close()
        dialog = dialog_cls(self, specimen=specimen)
        self._data_op_dialogs[dialog_cls] = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _convert_slit(self, to_ads: bool) -> None:
        """Rescale the selected specimen's experimental data between fixed and
        automatic (ADS) divergence-slit geometry. Parameterless and destructive,
        so a confirmation replaces the OK/Cancel gate the other data ops get from
        their dialog; the specimen's data_changed then refreshes the plot and
        marks the project dirty."""
        specimen = self._data_op_specimen()
        if specimen is None:
            return
        target = "ADS" if to_ads else "fixed slit"
        # The conversion changes the DATA's geometry but not the goniometer, and a
        # goniometer edit does not auto-recompute, so remind the user of both the
        # matching mode and the F5 that applies it.
        mode = "Automatic" if to_ads else "Fixed"
        reply = QMessageBox.question(
            self, "Convert data",
            "Convert %s's experimental data to %s geometry?\n\n"
            "This rescales the pattern in place and cannot be undone "
            "(save the project to keep it).\n\n"
            "To make the calculated pattern match, set this specimen's "
            "Goniometer → Divergence mode to %s afterwards, then press F5 "
            "to recompute." % (specimen.name, target, mode),
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if to_ads:
            specimen.convert_to_ads()
        else:
            specimen.convert_to_fixed()

    def _show_trim_data(self) -> None:
        specimen = self._data_op_specimen()
        if specimen is None:
            return
        TrimDataDialog(
            self, specimen=specimen, specimens=list(self.project.specimens)
        ).exec()

    def _save_graph(self) -> None:
        """Export the current plot to an image (old on_save_graph ->
        plot_controller.save). Qt's native file dialog cannot embed the size
        options, so a small size/DPI dialog runs first, then the file picker,
        then the plot saves at the chosen inch size + dpi."""
        if not self.pattern_plots:
            return
        dialog = SaveGraphSizeDialog(self)
        if not dialog.exec():  # QDialog.Accepted == 1; Rejected/closed == 0
            return
        width = float(dialog.ui.entry_width.value())
        height = float(dialog.ui.entry_height.value())
        dpi = float(dialog.ui.entry_dpi.value())
        # Default name: the single shown specimen, else the project (old app).
        shown = [s for s in self._shown_specimens if s is not None]
        default_name = (shown[0].name if len(shown) == 1 and shown[0].name
                        else self.project.name) or "graph"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Graph", default_name + ".png",
            "PNG image (*.png);;PDF document (*.pdf);;SVG image (*.svg)",
        )
        if not path:
            return
        if not path.lower().endswith((".png", ".pdf", ".svg")):
            path += ".png"
        try:
            self.pattern_plots[0].save_figure(path, dpi, width / dpi, height / dpi)
        except Exception as exc:  # noqa: BLE001 - surface, don't crash
            QMessageBox.warning(
                self, "Save Graph", "Could not save the graph:\n\n%s" % exc
            )

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

    def _show_shift_pattern(self) -> None:
        specimen = self._data_op_specimen()
        if specimen is None:
            return
        # Modeless so the plot stays interactive (zoom/scroll) while the preview
        # is aligned to the reference; rebuilt per open to bind the current
        # selection (see _show_strip_peak).
        if self._shift_pattern_dialog is not None:
            self._shift_pattern_dialog.close()
        self._shift_pattern_dialog = ShiftPatternDialog(self, specimen=specimen)
        self._shift_pattern_dialog.show()
        self._shift_pattern_dialog.raise_()
        self._shift_pattern_dialog.activateWindow()

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
        self.lbl_plot_info.setFont(fixed_font())
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

    def _show_manual(self, document: str = "") -> None:
        """Open the manual viewer on `document` (the walkthrough by default).

        A Help entry must show what its label says, so each one opens its own
        page rather than whatever was last read - otherwise "Manual" would open
        the science document simply because that was opened more recently.
        Reloading is skipped when the page is ALREADY the one asked for, which
        keeps the reader's place when they merely bring the window back.
        """
        if self._manual_dialog is None:
            self._manual_dialog = ManualDialog(self)
        dialog = self._manual_dialog
        wanted = document or HOME_DOCUMENT
        if dialog.ui.browser.source().fileName() != wanted:
            dialog.show_document(wanted)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _show_how_it_works(self) -> None:
        """Help -> How MudLab Works (Shift+F1): the same viewer, opened on the
        science rather than on the walkthrough."""
        self._show_manual(SCIENCE_DOCUMENT)
