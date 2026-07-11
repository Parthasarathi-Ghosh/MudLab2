# Wiring notes

## Model layer (Qt signals - mudlab/models/)

The old mvc framework is NOT ported. `models/properties.py` provides the
`Prop` descriptor (stores the value, emits the owner's named Qt signal on
change - the old PropIntel signal names data_changed / visuals_changed
are kept). `models/specimen.py` and `models/project.py` keep the old
property names (`display_experimental`, `display_exp_color`, ...); the
Project re-emits child specimen signals so views listen to the project
only, and emits `specimens_changed` on add/remove.

Live today: the specimens dock (`mudlab/specimens_model.py` adapter,
two-way checkbox sync), the plot stack (draws real
experimental/calculated patterns styled by the project display
properties), the window title, and live-applying Edit Project / Edit
Specimen dialogs (`bind_project` / `bind_specimen`). Import Specimens
parses text XY/CSV/DAT patterns (`mudlab/file_parsers/xy_parser.py`);
vendor binary formats (RD, RAW, CPI, UDF, ...) port later from the old
`file_parsers/xrd_parsers`. Now modeled: goniometer, markers, atom types,
and the whole pattern-calculation engine - phases, components, CSDS,
probabilities and mixtures (see the batch checklist in TODO.md). Mixtures
save from the model now (Edit Mixtures makes fractions/scales/background
editable), and phases save the modeled fields too - Edit Phases makes name/
sigma*/CSDS-mean, the R0 F params, and each component (c-axis scalars +
layer/interlayer atoms) editable; Phase/Component/Atom.to_dict keep
everything else verbatim by uuid. Within a phase, only the unit-cell a/b
(ucp) and atom relations still round-trip verbatim (their editors pending). The F5 Refresh Graph action and any Edit Mixtures
edit run `project.calculate()` / `mixture.calculate()` (each specimen's
calculated pattern). Not yet modeled: exclusion ranges; not yet ported:
the mixture fraction/scale/bg refinement optimizer (the calc path
re-applies the current solution).

## Project files (.mud) - mudlab/file_parsers/mud_project.py

Old-format compatible (deflated ZIP: `content` JSON with
`file://<part>` placeholders + `version` + `specimens`/`phases`/
`atom_types`/`mixtures` parts; pattern data is a JSON string of rows,
calculated lines may carry extra per-phase columns - only the first two
are read). **Data preservation rule:** loading keeps the full property
dicts verbatim (`raw_properties` on Project/Specimen), and saving writes
the modeled values back INTO that raw tree - so phases, mixtures, atom
types, goniometers, markers, exclusion ranges, line properties and uuids
from old projects survive MudLab2 round-trips untouched (verified
byte-identical against both sample projects). New files carry version
"0.1.10"; loaded files keep their own version tag. The MudLab2-only
`source` field is not written (the old loader would not accept it).

Main-window wiring (old AppController equivalents): `actionNewProject`
(confirm-discard, then opens Edit Project like the old app),
`actionOpenProject` (confirm-discard + error dialog on parse failure),
`actionSaveProject` (Save As when no filename), `actionSaveProjectAs`.
Dirty tracking sets on any project data/visuals/specimens signal and
clears on load/save; `closeEvent` guards quitting with unsaved changes.
Not yet ported: the old last-folder persistence
(user_data_dir/last_folder.txt) and the `check_for_changes()` hash-based
dirty detection (ours is signal-based and slightly more eager).

## edit_project.ui (Edit Project dialog)

Ported from the GTK ProjectView (`project/glade/project.glade`, notebook
`nbk_edit_project`, 4 tabs). Logic class: `mudlab/edit_project_dialog.py`
(`EditProjectDialog`); opened modeless by `actionEditProject` (old:
`ProjectController` + `view.project.present()`).

- Object names match the old glade ids (`project_name`, `project_author`,
  `project_date`, `project_description`, `project_layout_mode`,
  `project_axes_*`, `project_display_*`, `spin_display_*`,
  `spin_project_axes_*`), so the old adapter list in
  `project/controllers.py` greps cleanly.
- **Combo index -> model value maps** live at the top of
  `edit_project_dialog.py` (`LAYOUT_MODES`, `AXES_YNORMALIZERS`,
  `AXES_LIMITS`, `PATTERN_LINE_STYLES`, `PATTERN_MARKERS`,
  `MARKER_STYLES`, `MARKER_BASES`, `MARKER_TOPS`, `MARKER_ALIGNS`) —
  identical order to the old `settings.py` choice dicts.
- **Layout mode combo is temporary**: only FULL mode will be used in
  MudLab2; the combo exists for wiring parity and can be deleted later
  (also delete `LAYOUT_MODES` and the old `full_mode_only` handling).
- GtkColorButtons became QPushButtons opening the native `QColorDialog`;
  current value via `EditProjectDialog.button_color(btn)`; defaults
  black/#FF0000/black as in old `settings.py`.
- Manual x/y range spinboxes enable only when their Scale combo is
  Manual (old sensitivity behavior). Ranges/steps copied from the old
  GtkAdjustments (x: 0-180 °2θ; y: 0-1e12 counts, step 100; linewidths
  1-100).
- Old behavior to port: fields applied to the Project model live (no
  OK/Cancel — hence the single Close button); title-bar title is plain
  "Edit Project"; changing name/layout updates main-window title and
  widget visibility.
- The `specimen_popup` context menu and `vbox_specimens` panel that also
  live in project.glade belong to the specimens dock (see below), NOT to
  this dialog.

## edit_specimen.ui (Edit Specimen dialog)

Ported from the GTK SpecimenView (`specimen/glade/specimen.glade`,
notebook `edit_specimen`, `specimen/views/specimens.py`). Logic class:
`mudlab/edit_specimen_dialog.py` (`EditSpecimenDialog`), modeless; opened
by double-clicking a specimen row (old: row-activated on the specimens
tree -> `edit_specimen`). The old `edit_specimen` context-menu action must
open the same dialog when the specimens context menu is added.

- Tabs: General (specimen_name, specimen_sample_name, specimen_source),
  Display, Experimental, Calculated, Exclusion ranges, Goniometer.
- Display tab fields map to old specimen properties:
  `display_experimental/calculated/phases/derivatives/residuals`,
  `display_stats_in_lbl` (Rp in label), `display_vshift` (-10..10),
  `display_vscale` and `display_residual_scale` (0..1e9, default 1).
- The two group boxes host `LinePropertiesWidget` instances (see below)
  in `expLineLayout` / `calcLineLayout` (old: `specimen_exp_line` /
  `specimen_calc_line` event boxes).
- Pattern tables (`specimen_experimental_pattern`,
  `specimen_calculated_pattern`, `specimen_exclusion_ranges`) hold
  placeholder QStandardItemModels; the real models come from the ported
  specimen model (Qt signals). Buttons keep their old ids
  (`btn_add_experimental_data`, `btn_del_experimental_data`,
  `btn_import_experimental_data`, `btn_export_experimental_data`,
  `btn_export_calculated_data`, `btn_add_exclusion_range`,
  `btn_del_exclusion_ranges`, `btn_import_exclusion_ranges`,
  `btn_export_exclusion_ranges`) and are not yet connected.
- Goniometer tab: `goniometerLayout` placeholder for the future
  goniometer component (old: InlineGoniometerView / goniometer.glade);
  remove `lblGonioPlaceholder` when it lands.
- Old full-mode-only widgets in this dialog (hidden in VIEWER mode):
  calculated/phases/stats checkboxes, derivatives/residuals checkboxes,
  Calculated tab, Exclusion ranges tab - irrelevant once layout modes are
  dropped (FULL only).

## line_properties.ui (reusable line style editor)

`mudlab/line_properties_widget.py` (`LinePropertiesWidget`), used twice in
the Edit Specimen Display tab. Old: `generic/views/glade/lines/
experimental_props.glade` + `calculated_props.glade` (one component here;
`with_cap=False` hides the cut-off row for the calculated variant).

- Fields: color_button (+inherit_color), linewidth 1-100 (+inherit_lw),
  linestyle (+inherit_ls), marker (+inherit_marker), cap_value
  ("Cut-off value [counts]", experimental only).
- "Use default X" checked -> paired editor disabled; the value then
  inherits from the project display settings (old inherit_* properties on
  the pattern models).
- Combo item order matches `PATTERN_LINE_STYLES` / `PATTERN_MARKERS` in
  `edit_project_dialog.py`.
- Colors use `mudlab/qt_utils.py` `ColorButton` (native QColorDialog),
  shared with the Edit Project dialog.

## object_store.ui (generic list + properties shell)

`mudlab/object_store_dialog.py` (`ObjectStoreDialog`), ported from the GTK
ObjectListStoreView (`generic/views/glade/object_store.glade`). Reused by
Edit Phases now and by Edit Atom Types / Edit Mixtures / Edit Behaviours
later (old AppView child_views all used this shell; phases/mixtures used
the NoMinMax variant - Qt dialogs have no min/max buttons anyway).

- Left: Objects group with `edit_objects_treeview` + `button_add_object`,
  `button_del_object`, `button_load_object` (Import), `button_save_object`
  (Export), and `extraLayout` (old `extra_box`) for per-store extras.
- Right: Properties group; `set_properties_widget()` inserts the editor
  into `propertiesLayout` inside the `vwp_edit_object` scroll area.
- `object_selected` Signal(QModelIndex) fires on selection; the buttons
  are not yet connected (old: controllers handled add/del/load/save with
  parser-driven file dialogs).

## edit_phases.ui-less window: EditPhasesDialog + edit_phase.ui

`mudlab/edit_phases_dialog.py` subclasses ObjectStoreDialog (title "Edit
Phases", columns Phase | R | G) and hosts `mudlab/edit_phase_widget.py`
(`EditPhaseWidget`, design `edit_phase.ui`, old `phases/glade/phase.glade`
EditPhaseView). Opened modeless by `actionEditPhases`, rebuilt per open
with the project. Bound to the real Phase models via
`bind_phase(phase, on_changed)` (2026-07-10); selection fills the form and
the CSDS component.

- Editable + bound: `phase_name` (editingFinished) and `phase_sigma_star`
  (0-90°, valueChanged). `phase_G`/`phase_R` are read-only (G = component
  count, R from the probability model). Every accepted edit calls
  `on_changed` -> `project.calculate()`, so the pattern redraws live.
- CSDS tab: the real `CSDSWidget` (csds.ui + csds_widget.py) sits in
  `csdsLayout`; the "insert here" label is hidden. It has the mean spinbox
  (`csds_average`), a derived min-max label (`csds_range`) and a live
  matplotlib histogram of the Drits log-normal distribution, bound to the
  phase's DritsCSDSDistribution.
- Probabilities tab: the real `ProbabilitiesWidget` (probabilities.ui +
  probabilities_widget.py) sits in `probabilitiesLayout`. R0 only: the
  (G-1) independent F spinboxes (`Fi = Wi/sum(Wi..Wg)`) are editable and
  bound to the R0Probability model; the derived W (1xG) and P (GxG) tables
  are read-only; all built dynamically per phase. The tab is removed/
  re-inserted per phase so it only shows for G>=2 (old app'
  `remove_probabilities()` for single-component R0/G1 phases).
- Components tab: the real `EditComponentWidget` (edit_component.ui +
  component_widget.py) sits in `componentsLayout`. A `cmb_component`
  selector picks one of the phase's G components; its c-axis scalars
  (name, `component_d001`, `component_default_c`, `component_delta_c`) are
  editable and bound to the Component model, with cell a/b, volume and
  charge balance read-only. The `grpLayerAtoms` / `grpInterlayerAtoms` group
  boxes each hold an `AtomListWidget` (atom_list.ui + atom_list_widget.py):
  a table of Atom name / Def. Z / Calc. Z (read-only) / # (pn) / Element
  (an atom-type combo from the project atom types) with Add/Remove. Editing
  a scalar or an atom recomputes the structure factor + pattern; atom edits
  also refresh the component weight / charge balance.
- Disabled until later batches: `phase_display_color` +
  `phase_inherit_display_color`, `phase_based_on` + `phase_inherit_sigma_star`
  + `phase_inherit_CSDS_distribution` (phase inheritance / visuals not
  modeled), the object-store Add/Remove/Import/Export buttons (structural),
  and the component unit-cell a/b editors (read-only for now).
- Saving: `Phase.to_dict` writes name/sigma*/CSDS-mean over the verbatim
  `raw_properties`; `save_mud` replaces each raw "Phase" entry by uuid and
  keeps non-Phase entries (e.g. RawPatternPhase) untouched.
- Still to port around this window: the Add Phase dialog
  (`addphase.glade`: radio choice empty/default/raw phase, G 1-12, R 0-4,
  default-phase catalog combo), EditRawPatternPhaseView
  (`raw_pattern_phase.glade`), and the atom ratio/contents dialogs
  (`ratio.glade`, `contents.glade`).

## Edit Atom Types: EditAtomTypesDialog + edit_atom_type.ui

`mudlab/edit_atom_types_dialog.py` subclasses ObjectStoreDialog (title
"Edit Atom Types") and hosts `mudlab/edit_atom_type_widget.py`
(`EditAtomTypeWidget`, design `edit_atom_type.ui`, old
`atoms/glade/atoms.glade` EditAtomTypeView). Opened modeless by
`actionEditAtomTypes`.

- Fields keep old ids: `atom_name`, `atom_atom_nr`, `atom_weight`,
  `atom_debye` (Debye-Waller), `atom_charge`, and the scattering factor
  coefficients `atom_par_a1..a5`, `atom_par_b1..b5`, `atom_par_c`.
- The Scattering factor plot (old `view_graph` + `update_figure(x, y)`)
  is a Matplotlib canvas inserted into `scatteringLayout`; it currently
  recomputes f(s) = Σ aᵢ·e^(−bᵢ·s²) + c live on coefficient edits with
  x = sin(θ)/λ. The old app plotted against 2θ (goniometer conversion,
  fed by the controller) - switch to that with the model port.
- Placeholder list: three demo atom types; atom numbers/weights are real
  but the coefficient sets are synthetic. Real data lives in the old
  app's data file `mudlab/data/atomic scattering factors.atl` - port it
  with the atom type model.

## Edit Mixtures: EditMixturesDialog + edit_mixture.ui

`mudlab/edit_mixtures_dialog.py` subclasses ObjectStoreDialog (title
"Edit Mixtures") and hosts `mudlab/edit_mixture_widget.py`
(`EditMixtureWidget`, design `edit_mixture.ui`, old
`mixture/views/glade/edit_mixture.glade` EditMixtureView). Opened
modeless by `actionEditMixtures`.

- Kept old ids: `mixture_name`, `mixture_auto_run`, `btn_optimize`,
  `btn_refine`, `btn_composition`, `tbl_matrix`, `btn_add_phase`,
  `btn_add_specimen`, `btn_add_both`, `mixture_auto_scales`,
  `mixture_auto_bg`.
- Bound to the real Mixture model via `bind_mixture(mixture, on_changed)`
  (2026-07-10). `tbl_matrix` is phase-slot rows x specimen columns, with
  two fixed header rows (Abs. scale, Bg. shift) and a Fraction column.
  Editable numeric cells (scales per specimen, background per specimen,
  fraction per slot) write straight to the model arrays; `itemChanged`
  validates (bad input reverts) and calls `on_changed` -> `mixture.
  calculate()`, so the pattern redraws live. Phase cells show the assigned
  phase name read-only. Row/col constants live in the widget module.
- Refinement (2026-07-10): `btn_optimize` runs `Mixture.optimize()`
  (L-BFGS-B, calculations/mixture.py) under a busy cursor inside a
  UI-boundary try/except -> `QMessageBox` on failure (the optimizer core
  fails loud; this is the only safety net). On success it re-populates the
  matrix with the refined solution and updates the `lbl_residual`
  "Residual (Rp)" label (also shown on bind via `Mixture.current_residual`).
  The `mixture_auto_run/scales/bg` checkboxes are editable and persisted
  (stored in `raw_properties`); they select which variables Optimize frees
  (fractions_mask from the .mud gates fractions). F5 Refresh Graph calls
  `project.refresh()` -> `Mixture.update()`, which optimises auto_run
  mixtures and re-applies the rest.
- `btn_refine` (2026-07-11) opens the Refinement window
  (`refinement_dialog.py` RefinementDialog) for structural-parameter
  refinement; the mixture editor re-populates when it closes. See the
  Refinement window section below.
- Still disabled (later batches / other ports): the phase-per-cell combo
  (reassigning a slot's phase), btn_add_phase/specimen/both (structural),
  `btn_composition` (composition summary), and the Add Mixture dialog
  (`add_mixture.glade`) for the shell's Add button.
- Saving: `Mixture.to_dict` writes the modeled fields over the verbatim
  `raw_properties`, so masks / refine options / auto flags / uuid survive;
  `save_mud` rewrites the mixtures part from the models when any is loaded.

## Refinement window: RefinementDialog + refinement.ui

`mudlab/refinement_dialog.py` (`RefinementDialog`, design `refinement.ui`,
old `refinement/views/glade/refinement.glade` + `refine_results.glade`).
Opened modal from the Edit Mixtures `btn_refine` for the current mixture;
structural-parameter refinement, distinct from `btn_optimize`
(fractions/scales/bg). Engine: `calculations/refinement.py` (see the
"Robustness & long runs" note there).

- `tbl_refinables`: a row per `mixture.refinables()` - Parameter (label) /
  Value (read-only) / Min / Max (editable) / Refine (checkable). Edits go
  through `Refinable.set_ref_info`, which writes the `<name>_ref_info` triple
  (round-trips via the phase/component to_dict).
- `cmb_method`: 0 = L-BFGS-B, 1 = Basin Hopping (persisted to
  `refine_method_index`). `optionsLayout` holds a per-method options form
  (maxfun/maxiter, or niter/T/stepsize) seeded from / saved to
  `refine_options[index]`. `btn_auto_restrict` sets Min/Max to v*0.8..v*1.2
  for flagged params; `btn_randomize` sets flagged params to uniform(min,max)
  and recomputes.
- `btn_refine` runs `refine_mixture` on a background QThread
  (`_RefineWorker`), so the window stays responsive. `_set_running` locks the
  tree / method / options / helpers / Close and enables `btn_cancel`;
  `lbl_status` shows "Refining... N evaluations, best Rp = X" (engine
  `on_progress` -> queued `progress` signal). `btn_cancel` sets a
  `threading.Event` wired to the engine `stop` hook (keeps best-so-far). The
  worker only mutates the plain calc models + emits `progress`/`finished`/
  `failed`; `finished`/`failed` run on the GUI thread - `finished` calls
  `mixture.calculate()` (the plot redraw), shows Initial/Best/Last residuals
  + a GoF-of-best readout (`lbl_gof`, mean per-specimen GoF via
  `_compute_gof`) and enables `btn_apply_initial/best/last`
  (-> `refiner.apply_*`); `failed`
  -> `QMessageBox` (the model was already restored by the engine).
  `closeEvent` cancels + joins the thread.
- Deferred (not needed now): the progress/results plot (disabled
  `Refiner.record_history` hook; no Create-plot / Show-plot / plot dialog).

## Add Phase dialog: add_phase.ui

`mudlab/add_phase_dialog.py` (`AddPhaseDialog`), modal, old
`phases/glade/addphase.glade` AddPhaseView. Opened by the Edit Phases
shell's Add button; on accept a placeholder row is appended (real
creation of empty/default/raw phases comes with the phase model port).

- Three radio choices (old ids kept): `rdb_empty_phase` (with `G` spin
  1-6 and `R` spin 0-4), `rdb_default_phase` (with `cmb_default_phases` +
  `btn_generate_phases`), `rdb_raw_pattern`. Radios enable their own
  container (old `update_sensitivities`).
- Result accessors mirror the old view: `phase_type`
  ("empty"/"default"/"raw"), `G`, `R`, `default_phase`.
- R is forced to 0 and disabled while G == 1 (Reichweite needs >1
  component).
- The default-phase catalog is a placeholder list; the old app filled it
  from the default phases directory (.phs files) and could regenerate
  them (`btn_generate_phases`, with spinner + progress bar) - port with
  the phase model.

## Goniometer component: goniometer.ui

`mudlab/goniometer_widget.py` (`GoniometerWidget`), old
`goniometer/glade/goniometer.glade` InlineGoniometerView. Inserted into
the Edit Specimen Goniometer tab (`goniometerLayout`); reuse it anywhere
a goniometer setup is edited. Bound live to the specimen's `Goniometer`
model (`bind_goniometer`) - edits write to the model, which feeds the
intensity-correction calculations (batch 2 below).

- Four groups with old ids kept: General (`gonio_radius_spb`,
  `gonio_min_2theta_spb` 0-160, `gonio_max_2theta_spb` 0-100,
  `steps_spn_btn1` 1-5000), Sample (`sample_length_spb`,
  `sample_surf_density_spb`, `gonio_has_absorption_correction` +
  `absorption_spb` [cm²/g]), Primary beam (`btn_edit_wld` ->
  wavelength-distribution editor still to do, `gonio_divergence_mode`,
  `gonio_div_value_spb`, `gonio_has_soller1` + `gonio_soller1_spb`),
  Secondary beam (`gonio_has_soller2` + `gonio_soller2_spb`,
  `gonio_mcr2t_spb` monochromator 2θ).
- `DIVERGENCE_MODES = ("AUTOMATIC", "FIXED")` maps combo indexes to the
  old model values; on AUTOMATIC the value spin suffix switches from °
  (slit angle) to cm (irradiated length), as the old controller did.
- Soller/absorption checkboxes enable their paired spins.
- Bottom row (old ids): `cmb_import_gonio` ("Load setup", placeholder
  item until the stored setups port), `btn_export_gonio` ("Store setup"),
  `lbl_applied_gonio` (shows the applied setup name).

## Specimen-operation dialogs (lines + trim/statistics/save-size)

Nine small modal dialogs. Logic: `mudlab/line_dialogs.py`
(RemoveBackground, SmoothData, ShiftPattern, AddNoise, StripPeak,
PeakProperties) and `mudlab/specimen_dialogs.py` (TrimData, Statistics,
SaveGraphSize). Old sources: `generic/views/glade/lines/*.glade` and
`specimen/glade/{trim_dialog,statistics,save_graph_size}.glade`. The
main-window actions open them (`actionRemoveBackground`,
`actionSmoothData`, `actionShiftPattern`, `actionAddNoise`,
`actionStripPeak`, `actionPeakProperties`, `actionTrimData`,
`actionSaveGraph`); OK currently applies nothing - the operations hook up
with the specimen model port.

- **Remove Background** (`background.ui`): `bg_type` Linear/Pattern
  switches `bg_view_stack` (old swapped tables into bg_view_container).
  Linear: `bg_position`. Pattern: file row (`bg_pattern_file` +
  `btn_browse_bg`, native file dialog; filters come with the parser
  port), `bg_scale`, `bg_offset`. Old extra: bg_type change triggered
  `find_bg_position` (auto-suggest); port with model.
- **Smooth Data** (`smoothing.ui`): `smooth_type` (Moving Triangle,
  Savitzky-Golay, Gaussian, Moving Average, Smoothing Spline, Butterworth
  - `SMOOTH_TYPES` map), `spin_degree` 1-600 (default 3),
  `smooth_show_original`.
- **Shift Pattern** (`shifting.ui`): `shift_position` reference list
  (Quartz/Silicon/Zincite/Corundum/Goethite/Gibbsite/Manual;
  `SHIFT_POSITIONS` maps to d-spacings in nm), `spin_shift_value` ±10 nm;
  selecting a reference fills the value and locks the spin, Manual
  unlocks it.
- **Add Noise** (`add_noise.ui`): `spin_fraction` 0-1 (default 0.10).
- **Strip Peak** (`strip_peak.ui`): `strip_startx`/`strip_endx` +
  `cmd_sample_start`/`cmd_sample_end` (eye-dropper sampling on the
  pattern - connect with the plot controller), `noise_level`.
- **Peak Properties** (`peak_properties.ui`): start/end + sample buttons,
  result labels `peak_area_result`/`peak_fwhm_result`
  (`set_results(area, fwhm)`), `btn_copy_results` copies both to the
  clipboard.
- **Trim Data** (`trim_dialog.ui`): irreversibility warning, `cmb_scope`
  (This specimen only / All loaded specimens -> `TRIM_SCOPES`),
  `spin_min_2theta`/`spin_max_2theta` 0-180.
- **Statistics** (`statistics.ui`): read-only χ², R², Rp, Rwp, Re, data
  points via `set_statistics(...)`. NOT yet reachable from the UI - the
  old `view_statistics` action lives in the future specimens context
  menu.
- **Save Graph** (`save_graph_size.ui`): old GTK embedded this as an
  expander inside the save dialog; Qt native dialogs cannot embed custom
  widgets, so it runs as a small pre-dialog (presets fill
  `entry_width`/`entry_height`/`entry_dpi`), then the native save dialog
  follows (with the plot controller port).

## Markers: Edit Markers + Detect Peaks + Match Minerals

- **Edit Markers** (`edit_markers_dialog.py`) subclasses ObjectStoreDialog
  (title "Edit Markers - <specimen>", columns Marker | Position) and hosts
  `edit_marker_widget.py` (`EditMarkerWidget`, design `edit_marker.ui`,
  old `specimen/glade/edit_marker.glade`). The old EditMarkersView put a
  find_peaks.glade vbox under the list; here `btn_find_peaks` /
  `btn_match_minerals` go in the shell's `extraLayout`. Opened by
  `actionEditMarkers` and the context menu for the current single
  specimen; rebuilt per open so it targets that specimen. Match minerals
  is disabled until a marker is selected (old set_selection_state).
- **EditMarkerWidget** binds live to a `Marker` model (`bind_marker`):
  edits write to the marker and the plot refreshes via visuals_changed.
  Fields keep old ids: `marker_label`, `spb_position`/`spb_nanometer`
  (2θ <-> nm sync is live, via the specimen wavelength), `marker_visible`,
  and appearance/connector/offset groups with the inherit ("default")
  checkboxes (`marker_inherit_*` set the flag AND disable their editor).
  Choice maps (MARKER_STYLES/ALIGNS/BASES/TOPS) match settings.py.
  `cmd_sample` arms the main window's eye-dropper: the next plot click
  fills the position (see the Plot area section).

## Fit statistics (mudlab/calculations/statistics.py + models/statistics.py)

The old R-factor routines are ported verbatim in
`calculations/statistics.py` (R_squared, Rp, Rpw=Rwp, Rpe=Re, GoF,
derive/Rpder) with `smooth` in `calculations/math_tools.py`. They take the
experimental and calculated intensity arrays (aligned on a shared x-grid,
as the old app assumed - verified against the sample projects).

`SpecimenStatistics` (`models/statistics.py`, reached via
`Specimen.statistics`) computes these lazily and caches them; the cache
clears on the specimen's `data_changed`. `has_data` is False when there is
no calculated pattern (e.g. bulk/heated specimens) - stats are then 0 and
the Statistics dialog/GoF label are skipped. Wired into:
- **Statistics dialog** (`_show_statistics`): points, R², Rp, Rwp, Re, and
  the χ² field showing reduced chi-squared (= GoF²).
- **GoF-in-label** (`PatternPlot.draw_pattern`): with
  `display_stats_in_lbl`, the left-margin label appends
  `Rp = x%% / Rwp = x%% / GoF = x.xxx` (old Specimen.label).

- **Residual difference band** (`PatternPlot._draw_stats_band`, port of
  old plot_statistics): when a specimen has a calculated pattern and
  `display_residuals`/`display_derivatives` is on, its slot splits - the
  patterns take the top 65% (spec_scale ×0.65, offset raised by the band
  height) and the bottom 35% holds the difference curve (exp − calc for
  residuals, or the derivative residual), drawn centered on a faint zero
  line, scaled by half the reduced spec_scale × `display_residual_scale`,
  in the Rietveld-convention violet `RESIDUAL_COLOR`. No band for
  no-calc specimens.

Not yet: exclusion-range masking of the R-factors (old
get_exclusion_selector; exclusion ranges aren't modeled yet, samples have
none), and the separate der_exp/der_calc derivative curves (only the
derivative residual is drawn).

## Marker model (mudlab/models/marker.py)

`Marker` (Qt signals) keeps the old property names; `Specimen.markers`
holds them (`add_marker`/`remove_marker`, marker.visuals_changed chained
to the specimen). The inheritable props (color, angle, style, align,
base, top, top_offset) fall back to the project's `display_marker_*`
when their `inherit_*` flag is set - resolved by the `effective_*`
accessors (old InheritableMixin). Loaded from / saved to each specimen's
`markers` list in the .mud file (`Marker.from_dict`/`to_dict`, round-trip
verified byte-identical incl. uuid/anno_label).

`PatternPlot.draw_pattern` renders markers per specimen (port of the old
plot_marker_line + plot_marker_text): base_y from `effective_base`
(0 X-axis / 1 experimental / 2 calculated / 3 min / 4 max of the plotted
curves), a connector line for real line styles (none/offset draw no
line), and a rotated label (anno_label or label) at
`rotation = 90 - effective_angle`, honoring align/color and the top /
top_offset / y_offset placement. Marker line/label artists are pickable:
double-clicking selects the marker (see the Plot area section). Not yet
drawn: the "offset" style's special Y-offset line.
- **Detect Peaks** (`detect_peaks_dialog.py`, `find_peaks_dialog.ui`, old
  find_peaks_dialog.glade): modal; pattern/algorithm combos, threshold +
  steps + #peaks, and the # peaks-vs-threshold histogram canvas in
  `graphLayout`. Detection runs with the calc-engine port.
- **Match Minerals** (`match_minerals_dialog.py`, `match_minerals.ui`, old
  match_minerals.glade): NON-modal (old view kept it above the main
  window so the plot stays interactive). All-minerals list (placeholder,
  from the future mineral_references.csv port) <-> matched list with
  transfer buttons; auto-match and append-labels run with the reference
  data port. Button ids follow the old glade: `btn_rtl` = add (minerals
  -> matches, `on_add_match_clicked`), `btn_ltr` = remove
  (`on_del_match_clicked`). `min_distance` in Detect Peaks is hidden (old
  prominence-algorithm-only field; MudLab2 offers Threshold only).

## Specimens context menu (old specimen_popup)

`main_window._build_specimens_menu()` builds the right-click menu on the
specimens dock tree (context-menu policy set in `_setup_specimens_panel`):
Add Specimen, Import Specimens, then Edit specimen / Edit markers / View
statistics (enabled only for a SINGLE selected specimen) and Remove
specimen (any non-empty selection, with a confirm dialog). View
statistics opens the StatisticsDialog (zeros until the statistics port).
Old context-menu-only actions still pending: Replace data, Export data.

# main_window.ui

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

## Plot area (PatternPlot)

The central widget hosts **one** Matplotlib canvas: `PatternPlot` in
`mudlab/plot_controller.py` - one shared axes with all selected specimens
stacked, the mudlab style. (The scroll area + `plotStackLayout` from the
portrait-stack era remain in the .ui as the canvas host; the classic
scrollbar override in `_setup_plot_area()` is kept but the bar is never
active.)

- Drawing (`PatternPlot.draw_pattern`, port of the old plot_specimens):
  vertical offset stacking (`display_plot_offset` per `display_group_by`
  group), Y-scale normalization (`axes_ynormalize`: multi / single / raw
  counts), per-specimen vshift/vscale, specimen-name labels in the left
  margin at `display_label_pos`, y-axis hidden unless `axes_yvisible`,
  manual/auto x-limits from the axes settings. A single selection is
  simply the N=1 case. Not yet drawn: markers, exclusion hatches,
  residual/derivative statistics panels, mixture legends, per-pattern
  line-property overrides.
- Interactions (port of the old MainPlotController, old wheel mapping):
  plain scroll = 2θ-zoom ×1.15 around the cursor, Ctrl+scroll =
  intensity-zoom, Shift+scroll = pan 10% of the span; zooms clamp to the
  home extent with x ≥ 0 / y ≥ 0. ←/→ keys pan (canvas takes click
  focus), right-click resets to the home view, and user zoom is preserved
  across model-driven redraws (reset on selection change). Menu zoom
  (`actionZoomIn`/Out/Reset, Ctrl++/-/0) drives the same methods. The
  axes never autoscale after the initial draw (old controllers.py:108),
  so interaction artists can never alter the view ranges.
- `actionCrosshair` toggles the dashed crosshair cursor (#555555); with
  it active, left-drag draws the orange (#FF6600) measurement highlight
  over every curve and the status bar shows Δ2θ/Δd.
- Eye-dropper position picking (old EyeDropper) is a reusable one-shot on
  the main window: `arm_position_pick(callback, hint)` sets a crosshair
  cursor and, on the next left click on a pattern, calls
  `callback(plot, x_pos)` and disarms. Users: `actionSamplePoint` (arms
  `_report_sampled_point` -> info dialog of experimental/calculated
  values), the Edit Marker `cmd_sample` (fills the marker position, which
  writes to the bound marker and syncs nm), and the Strip Peak /
  Peak Properties `cmd_sample_start`/`cmd_sample_end` (fill their
  start/end fields). Those two dialogs are MODELESS so the plot stays
  clickable while picking.
- Marker double-click selection (old ClickCatcher): marker line/label
  artists are pickable when `on_marker_pick` is wired; a double-click
  (tracked manually, 0.5 s window, like the old app) calls
  `MainWindow._on_marker_picked` -> opens Edit Markers for the marker's
  specimen and selects it (`EditMarkersDialog.select_marker`).
- Mouse motion drives the old status readout (Bragg conversion in
  `mudlab/calculations/goniometer.py`, ported as-is; wavelength = the
  dominant entry of the specimen's goniometer wavelength distribution,
  `Specimen.wavelength`, CuKα1 default): single specimen -> 2θ, d, Ie,
  Ic interpolated from the patterns; multiple -> 2θ and d only,
  `*`-marked, with d from the FIRST specimen (old multi behavior,
  `PatternPlot.multi`).
- Still with later ports: the per-pattern operation previews
  (background/smooth/noise/strip lines of
  the old plot_specimen).

### Statistics band + GoF label (port when the calculation engine lands)

Exact old behavior (plot_specimens/plot_statistics in plotters.py and
Specimen.label in specimen/models/base.py):

- **Difference curve below each specimen plot:** when the specimen has a
  calculated pattern and `display_residuals` (or `display_derivatives`)
  is on, the specimen's allocated slot splits - the patterns keep the TOP
  65% (`spec_scale *= 0.65`, pattern offset shifted up by the band
  height) and the BOTTOM 35% becomes the statistics band
  (`stats_height = 0.35 * spec_reqst_height`). The residual pattern
  (experimental − calculated, `specimen.statistics.residual_pattern`) is
  drawn CENTERED in that band: offset + 0.5·height, scale =
  spec_scale · 0.5 · `display_residual_scale`, alpha 0.75. With
  `display_derivatives`, the derivative patterns (der_residual, der_exp,
  der_calc) draw in the same band at alpha 0.65.
- **Residuals/GoF under the sample name:** with `display_stats_in_lbl`
  on, the left-margin label becomes multi-line:
  `sample_name\nRp = x.x%\nRwp = x.x%\nGoF = x.xxx`
  (old Specimen.label property). NOTE: the old plot label shows
  **sample_name**, not the specimen name; MudLab2 currently labels with
  `name` (safer while imported files may have an empty sample_name) -
  decide at port time.
- The statistics values (Rp, Rwp, GoF, residual/derivative patterns)
  come from `mudlab/calculations/statistics.py` (Rp, Rpw, derive, GoF) +
  the SpecimenStatistics model - both part of the calculation-engine
  port.

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
| `actionRefreshGraph` | `refresh_graph` | `on_refresh_graph`: `update_all_mixtures()` + redraw. *Wired: `MainWindow._refresh_graph` -> `project.calculate()` (all mixtures, non-optimising) + `_refresh_plots`; F5.* |
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
