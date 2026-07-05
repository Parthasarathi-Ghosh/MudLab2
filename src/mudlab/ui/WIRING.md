# Wiring notes: main_window.ui

Ported from the GTK main window of the original MudLab
(`C:\GitHub\MudLab\...\site-packages\mudlab\application\glade\application.glade`,
class `AppView` in `application/views.py`, controller `AppController` in
`application/controllers.py`). Object names were kept recognizably close to
the old GTK ids to make grepping the old code easy while porting.

## Widgets inserted at runtime (not designable in Qt Designer)

| What | Old GTK home | New Qt home | Status |
|---|---|---|---|
| Matplotlib canvases | `matplotlib_box` (single canvas) | one canvas per selected specimen, appended to `ui.plotStackLayout` by `MainWindow.show_specimen_plots(names)` | done (placeholder patterns until the plot controller is ported) |
| Plot navigation toolbar | `navtoolbar_box` | `NavigationToolbar2QT` rebuilt on every stack change, bound to the TOP canvas of the stack; hidden, toggled by `actionShowPlotToolbar` | done (single-canvas binding is a placeholder decision) |
| Specimens model | `specimens_container` (received the project view's `scw_specimens_treeview` from `project/glade/project.glade`) | `ui.specimensTree` inside the `specimensDock` dock widget is designed in the .ui; runtime only supplies the model (currently a placeholder `QStandardItemModel`, see below) | placeholder |
| Specimens panel toggle | - | `specimensDock.toggleViewAction()` appended to the View menu as "Specimens panel" | done |
| Status bar: nav hints label | `lbl_nav_hints` | `MainWindow.lbl_nav_hints` (`addWidget`) | done |
| Status bar: progress bar | `status_progress` | `MainWindow.status_progress` (`addPermanentWidget`, hidden until a long operation runs) | done |
| Status bar: plot readout | `lbl_plot_info` | `MainWindow.lbl_plot_info` (`addPermanentWidget`, monospace font) | done |

## Specimens dock

The old left pane of the `main_pained` splitter is now a `QDockWidget`
(`specimensDock`, left area, closable/movable/floatable) holding a flat
`QTreeView` (`specimensTree`). Columns map to old per-specimen properties:

| Column | Old property | Old toggle handler |
|---|---|---|
| Specimen | `specimen.name` | (name edit via Edit Specimen dialog) |
| Exp | `specimen.display_experimental` | `ProjectController.specimen_tv_toggled` |
| Cal | `specimen.display_calculated` | same; column existed only in FULL layout mode |
| Sep | `specimen.display_phases` (show phase patterns separately) | same; FULL mode only |

- Selection is `ExtendedSelection`; row selection drives the old
  `current_specimen` / `current_specimens` model properties, which in turn
  drive the specimen/specimens action groups and the plot.
- `MainWindow.add_specimen_row(name, exp, cal, sep)` appends rows to the
  placeholder model; replace the `QStandardItemModel` with a model bridged
  to the ported project model, and route check-state changes to the
  `display_*` properties.
- The specimens context menu (see "Old actions NOT in the main window UI")
  belongs on this tree view.

## Plot area (portrait stack)

The central widget is a `QScrollArea` (`plotScrollArea`) holding
`plotStackContainer`/`plotStackLayout`, a vertical stack of Matplotlib
canvases — this is the main view:

- **Normal:** one specimen selected in the specimens tree -> one plot
  (with legend) fills the viewport.
- **Extended:** Shift/Ctrl+click multi-selection -> one plot per selected
  specimen, stacked top-to-bottom in selection-row order (portrait), each
  at least `PLOT_MIN_HEIGHT` (340 px) tall, overflowing into the vertical
  scrollbar.
- Scrollbars are classic, never auto-hiding: policy `AlwaysOn` (vertical)
  in the .ui, plus a per-scrollbar `windowsvista` style override in
  `_setup_plot_area()` because the `windows11` style draws transient
  overlay scrollbars.
- Zoom keyboard shortcuts (also in the View menu): `actionZoomIn`
  (Ctrl++), `actionZoomOut` (Ctrl+-), `actionZoomReset` (Ctrl+0).
  Placeholder implementation scales the x-range of every stacked plot
  around its center / autoscales back; replace with the plot controller's
  zoom once ported (old app: scroll-wheel zoom, Shift+scroll pan).
- Selection changes arrive via `_on_specimen_selection_changed`; the
  placeholder pattern generator `_plot_placeholder_pattern` is the seam to
  replace with real specimen data.

## Look and feel (Windows-native)

- `create_app()` in `__main__.py` sets the `windows11` style (falls back
  to `windowsvista`) and the Segoe UI 9pt system font; dialogs ported
  later should use the native `QFileDialog`/`QMessageBox` conveniences so
  they stay native.
- Standard actions carry Fluent theme icons via `iconset theme="..."`
  names in the .ui (document-new/open/save(-as), document-properties,
  application-exit, view-refresh, list-add, help-about, help-faq); Qt maps
  these to Segoe Fluent Icons on Windows. Domain actions (Phases, Trim,
  Strip peaks, ...) have no icons yet.

## Action map

Old handler names refer to `AppController`; "present X" means raising the
matching editor window (each will need its own `.ui` when ported).

| Qt action | Old GTK action | Old handler / behavior |
|---|---|---|
| `actionNewProject` | `new_project` | `on_new_project_activate`: confirm-discard-unsaved, create `Project`, open Edit Project |
| `actionOpenProject` | `open_project` | `on_open_project_activate`: confirm-discard-unsaved, load dialog (multiple parser formats), remembers last folder in `user_data_dir('MudLab')\last_folder.txt` |
| `actionSaveProject` | `save_project` | `on_save_project_activate`: save dialog if no filename, else overwrite; `JSONProjectParser.write(zipped=True)` |
| `actionSaveProjectAs` | `save_project_as` | `on_save_project_as_activate` |
| `actionEditProject` | `edit_project` | present project view |
| `actionQuit` | `exit` | confirm-discard-unsaved, then quit. *Connected to `close()`; confirmation still to port.* |
| `actionRefreshGraph` | `refresh_graph` | `on_refresh_graph`: `update_all_mixtures()` + redraw |
| `actionSaveGraph` | `save_graph` | `on_save_graph`: plot controller's save-figure dialog (default name from specimen/project) |
| `actionRemoveBackground` | `remove_bg` | single specimen: `specimen.remove_background()`; multiple: `project.remove_backgrounds(...)` |
| `actionSmoothData` | `smooth_data` | single-specimen smoothing dialog |
| `actionShiftPattern` | `shift_data` | single-specimen shift dialog |
| `actionShowPlotToolbar` | `show_plot_toolbar` (toggle) | show/hide nav toolbar. *Connected.* |
| `actionAddSpecimen` | `add_specimen` | `project.add_specimen()` |
| `actionImportSpecimens` | `import_specimens` | `project.import_multiple_specimen()` |
| `actionConvertToFixed` | `convert_to_fixed` | loop over selected specimens: `convert_to_fixed()` |
| `actionConvertToADS` | `convert_to_ads` | loop over selected specimens: `convert_to_ads()` |
| `actionEditPhases` | `edit_phases` | present phases window |
| `actionEditAtomTypes` | `edit_atom_types` | present atom types window |
| `actionEditMixtures` | `edit_mixtures` | present mixtures window |
| `actionManual` | - | `webbrowser.open(settings.MANUAL_URL)` |
| `actionAbout` | - | about dialog (old one showed logo `mudlab.png` scaled 212x160 + `settings.VERSION`). *Connected to a QMessageBox placeholder.* |
| `actionTrimData` | `trim_data` | `TrimController`/`TrimView`; reference = active specimen, falls back to first |
| `actionAddNoise` | `add_noise` | single-specimen add-noise dialog |
| `actionStripPeak` | `strip_peak` | single-specimen strip-peak dialog |
| `actionPeakProperties` | `peak_area` | single-specimen peak-properties dialog |
| `actionEditBehaviours` | `edit_behaviours` | feature disabled in old app; action kept but `visible=false` (matches GTK) |
| `actionEditMarkers` | `edit_markers` | present markers view for current specimen |
| `actionSamplePoint` | `sample_point` | eye-dropper: click a plot point, info dialog with experimental (+ calculated in FULL mode) values |
| `actionCrosshair` | `tbtn_crosshair` (toggle) | `plot_controller.set_crosshair_enabled(active)` |

## Enable/disable groups (old GtkActionGroups)

The old app enabled/disabled whole action groups; port as three lists of
QActions on `MainWindow` with two update methods
(`update_project_sensitivities(loaded)` /
`update_specimen_sensitivities(single, multiple)`):

- **project_actions** - enabled iff a project is loaded: SaveProject,
  SaveProjectAs, EditProject, AddSpecimen, ImportSpecimens, EditPhases,
  EditAtomTypes, EditMixtures, EditBehaviours (+ the auto-update toggle,
  see below). The old app also disabled the whole `main_pained`
  (= `ui.mainSplitter`) when no project is loaded.
- **specimen_actions** - enabled iff exactly ONE specimen is selected:
  SmoothData, ShiftPattern, StripPeak, AddNoise, PeakProperties,
  EditMarkers, SamplePoint (+ context-menu-only ones below).
- **specimens_actions** - enabled iff one OR more specimens are selected:
  RemoveBackground, SaveGraph, TrimData, RefreshGraph, ConvertToFixed,
  ConvertToADS (+ Remove Specimen, context-menu-only).

## Old actions NOT in the main window UI

These lived in GTK action groups but surfaced in the specimens-list
context menu / project component; add them when porting that panel:
`edit_specimen`, `del_specimen` (Remove Specimen), `replace_specimen_data`,
`export_specimen_data`, `view_statistics`, `add_marker`,
`toggle_auto_update` ("Auto-update calculated patterns").

## Layout modes

Old: `settings.DEFAULT_LAYOUT = "FULL"`, modes `FULL` / `VIEWER`; the
project model stores its own `layout_mode`. Widgets hidden in VIEWER mode
(`widget_groups['full_mode_only']`): EditPhases/EditAtomTypes/EditMixtures
toolbar buttons and menu items, SamplePoint button, and their separators.
Port as a list of QActions toggled by a `set_layout_mode(mode)` method.

## Title, status bar, icons

- Title: `MainWindow.set_project_title(name)` implements the old
  `title_format = "MudLab - %s"` (project name).
- Plot readout (`lbl_plot_info`) formats are already ported:
  `update_plot_status(2theta, d, Ie, Ic, multi)` (Ic only in FULL mode;
  `*` marks multi-specimen d-values) and
  `update_plot_status_range(x0, x1, d0, d1, multi)` for drag ranges.
- Temporary messages: `ui.statusBar.showMessage(...)` (old
  `status_message` decorator pushed e.g. "Updating display..."); the
  progress bar `status_progress` is shown during long operations.
- Window icons + about logo live in the old repo at
  `mudlab/application/icons/` (mudlab.ico, mudlab.png, 16-128 px PNGs) -
  copy them over and set the window/app icon when branding is ported.

## Behaviors to keep in mind when wiring

- Confirm-discard-unsaved-changes guard before Quit / New / Open
  (`model.check_for_changes()`).
- Main window maximizes on startup (unless DEBUG in the old app).
- After loading a project, the first specimen is auto-selected so the
  graph shows immediately.
- Plot interactions handled by the old `MainPlotController`: vertical
  crosshair, mouse-move updates the status readout, drag-highlight shows
  the delta readout, clicking a marker opens the markers view, eye-dropper
  sampling.
- Keyboard shortcuts added in the .ui (the old app used a GTK accel
  group): Ctrl+N / Ctrl+O / Ctrl+S / Ctrl+Shift+S / Ctrl+Q, F5 refresh,
  F1 manual.

## Editor windows these actions will open (future .ui files)

Old Glade sources to port, one Qt `.ui` each:
`project/glade/project.glade` (edit project + the specimens tree panel),
`specimen/glade/specimen.glade`, `edit_marker.glade`, `statistics.glade`,
`find_peaks*.glade`, `match_minerals.glade`, `trim_dialog.glade`,
`save_graph_size.glade`; `phases/glade/*.glade` (phase editor family),
`atoms/glade/atoms.glade`, `mixture/views/glade/*.glade`,
`generic/views/glade/*.glade` (generic object-list windows + line-edit
dialogs: smoothing, shifting, add_noise, strip_peak, peak_properties,
background, csv_import), `goniometer/glade/*.glade`,
`refinement/views/glade/*.glade`.
