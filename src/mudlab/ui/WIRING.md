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
calculated pattern). Specimen exclusion ranges are modeled
(Specimen.exclusion_selector) and mask the fit/refine residual + the
R-factors; the mixture Optimize and the structural Refinement window (both
L-BFGS-B based) are live.

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

**PyXRD `.pyxrd` open (2026-07-18).** A `.pyxrd` is a PyXRD project in the
SAME ZIP+JSON container, and its modeled data is already `.mud`-standard
(all `type` strings are the modern short names - `Phase`, `R0G2Model`, ...;
the only `pyxrd`/`PyXRD` token is prose in the project description). So
`load_mud` reads it as-is - MudLab2's schema loader needs none of the old
app's "slip" step, which is just a `pyxrd.`->`mudlab.` class-PATH remap
(`generic/io/json_codec.py`) that only its class-registry codec required.
The one structural gap (no `version` part) is filled by `save_mud`, which
always writes version "0.1.10". So opening a `.pyxrd` and saving yields a
proper `.mud` (verified: 6 parts incl. `version`, zero `pyxrd.` leakage,
reloads + calc intact). The open dialog offers both (`OPEN_PROJECT_FILTERS`
= `*.mud *.pyxrd`); Save is `.mud`-only (`SAVE_PROJECT_FILTERS`). Opening a
`.pyxrd` is treated as a CONVERSION: `_open_project` retargets
`project.filename` to the `.mud` sibling and marks the project dirty, so
the original `.pyxrd` is never overwritten and Save produces the `.mud`.
NOTE: a PyXRD-computed calculated pattern is ~2x MudLab2's (a PyXRD-vs-
mudlab absolute-intensity convention; shape matches to corr 0.999997, and
scale is a free fit param so it does not affect fitting) - do NOT treat a
`.pyxrd`'s stored pattern as a machine-precision golden. For golden
fixtures, recompute in the app (or the old app) and save as `.mud`.

Main-window wiring (old AppController equivalents): `actionNewProject`
(confirm-discard, then opens Edit Project like the old app),
`actionOpenProject` (confirm-discard + error dialog on parse failure;
accepts `.mud`/`.pyxrd`), `actionSaveProject` (Save As when no filename),
`actionSaveProjectAs` (`.mud` only). Dirty tracking sets on any project
data/visuals/specimens signal and clears on load/save; `closeEvent` guards
quitting with unsaved changes. Not yet ported: the old last-folder
persistence
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
  `specimen_source` (a QPlainTextEdit) shows `specimen.source`; on Import,
  `import_specimen_files` fills it via `xrd_import.build_source_string(path, x,
  metadata)` - the file name + 2θ range/step/points (any format), plus any
  `parse_pattern_metadata` fields (`.xrdml`: wavelength / count time / sample /
  date / radius; `.rasx`: wavelength / X-ray tube target+kV+mA / date / scan
  speed; `.uxd`: wavelength / anode+kV+mA / count time / date / radius; Bruker
  `.raw`: count time [RAW1+RAW3] + RAW1 Kα1/Kα2 wavelength). The file's Kα1
  wavelength is applied to the specimen's goniometer. Rigaku 'FI' `.raw` stays
  axis-only (its metadata header is not reverse-engineered). Was empty before
  (2026-08-05; `verify_import_source`, 42/42).
- Display tab fields map to old specimen properties:
  `display_experimental/calculated/phases/derivatives/residuals`,
  `display_stats_in_lbl` (Rp in label), `display_vshift` (-10..10),
  `display_vscale` and `display_residual_scale` (0..1e9, default 1).
- The two group boxes host `LinePropertiesWidget` instances (see below)
  in `expLineLayout` / `calcLineLayout` (old: `specimen_exp_line` /
  `specimen_calc_line` event boxes).
- Pattern tables (`specimen_experimental_pattern`,
  `specimen_calculated_pattern`) show the specimen's real data READ-ONLY
  (the add/del/import/export data buttons wire with the pattern-model
  port). The **exclusion-range table** (`specimen_exclusion_ranges`) IS
  wired: `_fill_exclusion_table` fills it from `specimen.exclusion_ranges`;
  `btn_add_exclusion_range` appends a `0,0` row, `btn_del_exclusion_ranges`
  removes the selected row(s), and any cell edit (`itemChanged`) runs
  `_commit_exclusions` -> reads every row back into
  `Specimen.set_exclusion_ranges` (malformed rows skipped; a `_updating`
  guard suppresses re-entrancy while filling). `data_changed` then refreshes
  the stats + plot. `btn_import/export_exclusion_ranges` are disabled (not
  ported). The other buttons keep their old ids
  (`btn_add_experimental_data`, `btn_del_experimental_data`,
  `btn_import_experimental_data`, `btn_export_experimental_data`,
  `btn_export_calculated_data`).
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
  charge balance read-only. Cell a/b are `UnitCellProperty` objects
  (models/unit_cell_prop.py, Batch 1a): fixed or derived
  (`value = factor*prop + constant`, prop = cell_b or an atom pn -
  `cell_a = 0.57735*cell_b`, `cell_b = k*pn + const`). The stored value is
  kept on load (it can be stale, and the old app's pattern used it) and only
  recomputed (`Component.update_ucp_values`) on an edit; `mud_project` resolves
  each UCP's derivation source by uuid.
  - **UCP editor (Batch 1b, ucp.ui + ucp_widget.py):** a reusable
    `UnitCellPropWidget` is embedded twice (rows for cell a and b) in the
    component form. It has an `ucp_enabled` "Derived" toggle, the `ucp_value`
    spin (active when fixed), and a `box_enabled` group `ucp_factor x ucp_prop
    + ucp_constant` (active when derived). `ucp_prop` lists the component's
    atoms (pn) + the other cell length. An edit writes to the UnitCellProperty,
    then `_on_ucp_changed` runs `update_ucp_values` (cell_b feeds cell_a),
    refreshes both value displays + volume/charge, and redraws. Changing the
    prop rewrites its `[uuid, attr]` (dirty flag, so unedited UCPs round-trip
    verbatim). Inherited cell a/b disable the whole widget (L2's is_inherited). The `grpLayerAtoms` / `grpInterlayerAtoms` group
  boxes each hold an `AtomListWidget` (atom_list.ui + atom_list_widget.py):
  a table of Atom name / Def. Z / Calc. Z (read-only) / # (pn) / Element
  (an atom-type combo from the project atom types) with Add/Remove. Editing
  a scalar or an atom recomputes the structure factor + pattern; atom edits
  also refresh the component weight / charge balance.
- Atom relations group (Batch 2b, component_widget.py + ratio.ui/ratio_widget.py):
  `cmb_relation` lists the component's relations; `btn_add_ratio` / `btn_del_relation`
  add/remove. An **AtomRatio** (substitution: `atom1.pn = value*sum`,
  `atom2.pn = (1-value)*sum`) is edited by the embedded `AtomRatioWidget`
  (`ratio_name`, `ratio_enabled`, `ratio_atom1`/`ratio_atom2` combos over the
  component's atoms, `ratio_value` 0-1, `ratio_sum`). An edit calls
  `Component.apply_atom_relations` (sets the atoms' pn, then `update_ucp_values`
  so cell_b/cell_a follow), refreshes the atom lists + derived read-outs and
  recomputes. An **AtomContents** (Batch 3, contents.ui/contents_widget.py:
  name, enabled, value + a table of atom/amount rows, `atom.pn = amount*value`)
  is edited the same way ("Add contents" button; the ratio / contents editor is
  shown per the selected relation's type). Inherited relations
  (inherit_atom_relations) are read-only.
- Relation CHAINING + value refinement (2026-07-22): an AtomContents row may
  target a sibling relation instead of an atom - the contents `Target` combo
  offers the component's atoms (prop "pn") plus its other relations (an AtomRatio
  contributes "R: RATIO" -> value and "R: SUM" -> `__internal_sum__`; an
  AtomContents contributes its value). `AtomContent.apply` drives the target
  from `amount*value` and re-applies it so the driven atoms follow; a
  re-entrancy guard on `apply_relation` breaks cycles, and the editor refuses a
  target that would loop back (`_would_cycle`). `Component.resolve_relations`
  now passes a `{uuid: relation}` map so chained rows resolve their target.
  `enumerate_refinables` (calculations/refinement.py) exposes each relation
  `value` as a refinable via `value_ref_info`, EXCEPT inherited / disabled /
  driven relations (`_driven_relation_ids`, matching the old
  `AtomRelation.is_refinable`); its setter re-applies the component's relations
  so pn (and any derived cell) update before the structure factor is recomputed.
- Component linking (Batch L1 model + Batch L2 editor): a Component can be
  linked to a template component in another phase (`linked_with` + eight
  `inherit_*` flags on `models/component.py`) - the same clay layer reused
  across phases. Inheritance is a read-time overlay (`Component._resolved_own`):
  an inherited scalar/atom-list reads through to the template, the child keeps
  its own copy for round-trip, and it is per-property (a glycolated smectite
  inherits cell a/b + delta_c + layer atoms but keeps its own d001). d001 is
  gated by `inherit_default_c`, matching the old app. `mud_project.load_mud`
  resolves the links by uuid after all phases load; `Component.is_inherited(attr)`
  gates read-only display and refinable skipping.
  - **Editor (L2/L3, component_widget.py):** the Components tab has a "Component
    linking" group - the `component_linked_with` combo and the
    `component_inherit_*` checkboxes. The combo lists every component in the
    project ("Phase / Component", plus "(not linked)"); picking one sets
    `Component.set_linked_with` (L3), picking "(not linked)" unlinks and clears
    the inherit flags. `set_linked_with` refuses a self-link or a cycle (walks
    the target's chain; a rejected pick reverts the combo). Candidates are
    threaded down from the dialog (`EditPhasesDialog._link_candidates` ->
    `bind_phase` -> `bind_components`). On a linked component, ticking an inherit
    box greys the matching field (it reads through to the template) and
    recomputes; the six editable checkboxes (cell a/b, cell c/default c, Δc,
    layer/interlayer atoms) are enabled only when linked.
    `component_inherit_d001` (follows the cell-c gate) and
    `component_inherit_atom_relations` (editor pending) are read-only. NOTE:
    this is more permissive than the old app, which only allowed linking to a
    phase's `based_on` components; MudLab2 links any two components directly by
    uuid. When phase `based_on` is ported it will drive links positionally and
    (old setter) clear manual ones.
- Still disabled: `phase_display_color` + `phase_inherit_display_color` (the
  phase display colour is a visuals-only property that is not modeled yet) and
  the object-store Add/Remove/Import/Export buttons (structural). NOTE:
  `phase_based_on` + `phase_inherit_sigma_star` + `phase_inherit_CSDS_distribution`
  ARE now wired (see the phase-`based_on` section below), and the component
  unit-cell a/b editors are editable (Batch 1b).
- Saving: `Phase.to_dict` writes name/sigma*/CSDS-mean over the verbatim
  `raw_properties`; `save_mud` replaces each modeled ("Phase" /
  "RawPatternPhase") entry by uuid and keeps any other type untouched.
- Still to port around this window: the Add Phase dialog
  (`addphase.glade`: radio choice empty/default/raw phase, G 1-12, R 0-4,
  default-phase catalog combo), the raw-pattern phase EDITOR
  (`raw_pattern_phase.glade` - batch 2, the model+calc are done, see below),
  and the atom ratio/contents dialogs (`ratio.glade`, `contents.glade`).

### Raw-pattern phases (batch 1 DONE: model + calc + round-trip)

A `RawPatternPhase` (`models/raw_pattern_phase.py`) is a phase whose
contribution is a fixed MEASURED pattern, not a computed one: it holds a stored
`2theta -> intensity` curve (`raw_pattern_x/y`) and no components/CSDS/
probabilities. Used for accessory minerals (quartz, feldspar), an amorphous
hump, or an internal standard - the optimiser fits only its scale.

- **Loading needs NO instrument-format parser.** The curve lives INSIDE the
  `.mud`/`.pyxrd` as a `PyXRDLine` (`raw_pattern.properties.data` = JSON
  `[2theta, intensity]` rows), the same serialisation a specimen's experimental
  line uses, decoded the same way (`_decode_raw_pattern`, mirrors
  `mud_project._decode_pattern_data`). `.xrdml`/`.raw`/`.xy` are IMPORT formats
  (file -> curve), only needed when creating a raw phase from a measured file -
  that is batch 3. `.xy`/`.txt`/`.csv`/`.dat` already have `xy_parser`;
  `.xrdml` (PANalytical XML) and `.raw` (Bruker) are not present and are
  deferred until wanted.
- **Calc** (`calculations/phases.py`): `get_diffracted_intensity` now branches
  on `phase.type` - `_get_raw_intensity` resamples the stored curve onto the
  goniometer 2theta grid (`np.interp`, zero outside range = PyXRD's
  `interp1d(fill_value=0)`). `apply_lpf`/`apply_correction` are False, so no LP
  factor and no machine correction; the specimen calc still applies the
  wavelength distribution to it uniformly (matches PyXRD). No change was needed
  to `calculate_phase_intensities` - it already reads `apply_*` generically.
- **Load/save** (`mud_project.py`): the loader builds a `RawPatternPhase` for
  `type == "RawPatternPhase"` (was skipped); the saver's phase-rebuild loop
  treats both `Phase` and `RawPatternPhase` as modeled (write from the live
  model by uuid; drop if removed; append if added). Byte-identical round-trip:
  `to_dict` overwrites only name/uuid/pattern-`data` over verbatim
  `raw_properties`, preserving the embedded line's other keys - and the line's
  uuid is minted ONCE per object (`_line_uuid`) so repeated `to_dict()` calls
  are stable (a fresh phase would otherwise re-mint it each save).
- **No golden fixture** (no sample project has a raw phase, as with R1G4); the
  calc is a plain interpolation, so `tools/verify_raw_pattern_phase.py` (19
  checks) validates it synthetically + a through-the-file round-trip that adds
  a raw phase to a real project and confirms the modeled phases are untouched.
- **Batch 2 DONE** = the raw-pattern phase editor + the Add dialog's raw
  option (see below). **Batch 3 DONE** = the import parsers (see "XRD import
  parsers" below).

### Raw-pattern phase EDITOR (batch 2 DONE)

`EditRawPatternPhaseWidget` (`edit_raw_pattern_phase_widget.py`,
`ui/edit_raw_pattern_phase.ui`) is a deliberately small editor - a name field,
an "Import pattern…" button, and a matplotlib preview of the stored curve. No
probabilities/components/CSDS tabs (those are a computed `Phase`).

- **EditPhasesDialog hosts BOTH editors** in the Properties pane (the structural
  `EditPhaseWidget` and the raw one), added via `set_properties_widget` and
  toggled with `show()`/`hide()`; `_on_phase_selected` routes by `phase.type`.
  The phase-list R/G columns show `—`/`—` for a raw phase (`_phase_row_values`).
- **Add Phase dialog**: `rdb_raw_pattern` is now enabled (only the default
  catalog stays disabled). Selecting it disables the empty-phase G/R container
  (`_update_sensitivities`). `EditPhasesDialog._on_add_phase` builds a
  `RawPatternPhase(name="New Raw Pattern Phase")` for `phase_type == "raw"`.
- **Import** goes through the shared `csv_import_dialog.import_pattern` helper
  (common `file_parsers.csv_io` reader + the CSV-import options dialog for text
  formats); `import_from_path(path, options=None)` is split from the file dialog
  so it is head-less testable.
- Guard: `verify_phase_dialogs.py` check 7 (Add->raw creates a RawPatternPhase,
  the raw editor is shown for it, import sets the pattern, name edit
  propagates) + the updated check 2 (raw radio enabled). Harness 75 checks.

#### NonClayPhase ("path 2", 2026-08-16, mainstream)

`NonClayPhase` (`models/nonclay_phase.py`) subclasses `RawPatternPhase` and adds
an `oxides` (`{oxide: wt%}`) dict, so it has a pattern AND a declared chemistry.
A **computed** (CIF) one also carries a `reflections` list of `(d_angstrom,
intensity)` (intensities normalised to 100) + a tunable `fwhm`; a **measured**
one has no reflections and keeps its fixed curve (`is_computed` distinguishes
them). Its behaviour is gated by `type == "NonClayPhase"`:
- **(a)** contributes its pattern + its fraction is optimised. A COMPUTED phase
  RENDERS from its reflection list **at the specimen wavelength** (recovered from
  `range_stl = 2 sin θ/λ` via `_wavelength_from_stl`) broadened to `fwhm`
  (`render_on_grid`) - so positions and width are specimen-consistent, like a
  structural `Phase` but from a fixed stick list (path-2 **phase A**). The width
  is a constant `fwhm` OR, when `caglioti` (U,V,W) is set, angle-dependent
  (`fwhm_at`: FWHM² = U·tan²θ+V·tanθ+W, path-2 **(w)**). A MEASURED phase falls
  back to `_get_raw_intensity`. Either way the fraction Optimize includes it.
- **(b)** never structurally refined - `enumerate_refinables` only takes
  `type == "Phase"`, so it is excluded for free.
- **(c)** contributes to composition - DONE (additive). `composition.
  bulk_composition(mixture)` sums each phase's own composition normalised to 100%,
  weighted by its fraction (clay `Phase`s from atoms via `_clay_oxide_masses`;
  `NonClayPhase`s from their stored oxides) - a semi-quant fraction-weighted
  average (the fractions are the same non-rigorous amounts the clay-only view
  uses; a mass-weighted bulk would need per-phase molecular weights, i.e. the
  formula parser). It is a SEPARATE function: the clay-only `mixture_composition`
  and the XRF mass balance that reads it are UNCHANGED. `CompositionDialog` shows
  it via an "Include non-clay phases (bulk)" checkbox (`chk_bulk`), enabled only
  when `mixture_has_nonclay`; default stays clay-only. verify_composition.py.

UI: **"Import Non-Clay"** is an extra button `EditPhasesDialog` adds
programmatically to the objects frame's spare `extraLayout` (the shared
`object_store.ui` is untouched). `ImportNonClayDialog` (`import_nonclay_dialog.py`
+ `ui/import_nonclay.ui`) takes a measured pattern (via the shared
`import_pattern`) OR a CIF with atoms (via `nonclay.structure.reflections_from_cif`,
which returns the `(d, I)` reflection list AND the derived oxide%); name,
`ColorButton`, the `OxideGrid` (`oxide_grid.py` - a `QTableWidget` of oxide->wt%
with 0-100 spinboxes + a "Fill from formula" input that runs
`composition.parse_formula` (path-2 (f): elements/parentheses/hydrate-dots ->
reporting oxides via the conversion table; only Si/Al/Fe/Ca/Mg/Na/K map),
shared with the editor), a live pattern preview (its
`spin_fwhm` re-renders the CIF curve), and validation (name + >=2-pt pattern +
oxide sum > 0). Selecting a NonClayPhase shows `EditNonClayPhaseWidget`
(`ui/edit_nonclay_phase.ui`) - an editable oxide grid + preview + a **Peak FWHM**
spinbox shown ONLY for a computed phase (`setRowVisible` on `is_computed`);
changing it calls `set_fwhm` + `rebuild_stored_pattern` and DOES recompute (the
pattern changed), unlike an oxide edit. A **Calibrate…** button next to it
(phase B) opens `CalibrateFwhmDialog` (`nonclay_calibration.calibrate_fwhm` fits
the width AND a 2theta zero-shift, so displacement does not inflate it, against a
built-in Silicon standard or a CIF + a measured scan); a "Fit angle-dependent
width (Caglioti)" checkbox instead fits (U,V,W) (path-2 (w)), shown in a read-only
`lbl_caglioti`. OK sets the box/Caglioti, and an "apply to all" checkbox routes
`apply_fwhm_to_all` / `apply_caglioti_to_all` -> `EditPhasesDialog.
_apply_fwhm_to_all` / `_apply_caglioti_to_all` across every computed phase
(instrumental width is shared).
Persistence: the `.mud` loader +
`_MODELED` handle `"NonClayPhase"`, and `to_dict`/`from_dict` round-trip the
reflections + fwhm (a pre-phase-A phase with no reflections stays a baked curve
on load - clean migration). `composition.reporting_oxides()` is the shared oxide
list. Nothing is deferred - (c) bulk composition, (f) the formula parser and
(w) the Caglioti width all shipped. Guards: `verify_nonclay_phase.py` (67),
`verify_nonclay_calibration.py` (31), `verify_composition.py` (36).

Audit notes (2026-08-16), worth knowing before touching this code:
- The **Caglioti fit is warm-started from the constant-FWHM fit** and must stay
  that way: a cold Nelder-Mead start steps the 2theta shift by 0.00025 deg, less
  than a peak width, so a displaced standard scan silently converged into a
  neighbouring-peak minimum. It also falls back to the constant fit's equivalent
  `(0, 0, FWHM^2)` when it cannot beat it, and `bounds` keeps the width physical
  across the whole fit window (without that the fit shrinks the peaks to the
  render's 1e-3 deg floor and "matches" nothing).
- A `.` in a formula is read as a **decimal point** (`Fe0.5`), not a separator;
  `·`/`*` are always separators. `formula_dot_is_ambiguous` flags the inputs
  where the two readings differ (a hydrate does not - its water is dropped) and
  the oxide grid asks the user which was meant.
- The bulk and clay-only views **weight differently** (fraction vs fraction x
  formula mass), so the clay oxides themselves move ~1 wt% between them. It is
  the price of putting clays and non-clays on one scale; the `chk_bulk` tooltip
  says so.

### XRD import parsers (batch 3 DONE)

`file_parsers/xrd_import.parse_pattern(path)` dispatches on extension to the
format parsers; `PATTERN_FILTERS` is the matching file-dialog filter. **Every
pattern-import site in the app goes through this one dispatcher + filter**, so
they all accept the same formats: the specimen data import
(`main_window.import_specimen_files`, `IMPORT_FILTERS = PATTERN_FILTERS`), the
background-pattern browse (`line_dialogs.RemoveBackgroundDialog._browse_pattern`)
and the raw-pattern phase editor. (The only other `.mud`/`.pyxrd` file dialogs
are project open/save, which are not pattern imports.) Ported / written from old
mudlab's `xrd_parsers`, validated against the real vendor files in
`~/Downloads/Phraser tests` (the user's data - never committed):

- **`.xrdml`** (`xrdml_parser.py`, PANalytical XML): first non-aborted scan;
  2theta from `listPositions` or `startPosition`/`endPosition`+linspace;
  intensities normalised to counts-per-second by `<commonCountingTime>`.
  Matches old mudlab's XRDMLParser EXACTLY (max|Δ|=0) on real files.
  `parse_xrdml_metadata` also reads (best-effort) the Kα1/Kα2 wavelengths
  (Angstrom→nm), count time, sample name/id, scan timestamp and beam radius.
- **`.rasx`** (`rasx_parser.py`, Rigaku - NEW, not in the lineage): a ZIP; read
  `Data<i>/Profile<j>.txt` (2theta, intensity, flag) via the shared
  `xy_parser.parse_xy_lines`. `parse_rasx_metadata` reads its
  `Data<i>/MesurementConditions<j>.xml` (Rigaku's spelling; regex allows the
  correct one too) for the Kα1/Kα2 wavelengths, X-ray target, kV/mA, start time
  and scan speed. Its 2theta grid matches the sample's `.txt`
  export exactly (intensity scale differs by ~5x between vendor exports - each
  parser faithfully reads its own file).
- **ASCII** (`xy_parser.py`): now BOM-tolerant (`utf-8-sig` + a BOM strip) and
  ignores extra columns, so a 4-column `2theta,cps + BG` `.txt` reads cols 0-1.
- **`.uxd`** (`uxd_parser.py`, Bruker DIFFRAC ASCII; ported from old mudlab's
  UXDParser): a `;`/`_KEYWORD=value` header ended by a data marker that states
  the layout - `_2THETACOUNTS`/`_2THETACPS` (paired "2theta value") or
  `_COUNTS`/`_CPS` (single column; 2theta rebuilt from `_START`/`_STEPSIZE`).
  Counts are normalised to CPS by `_STEPTIME` (a `*CPS` marker = already CPS).
  First range only. Validated on `dh232.UXD` (2676 pts, 5-60 deg, quartz peak).
  `parse_uxd_metadata` reads the same header for `_WL1`/`_WL2` (unit `_WL_UNIT`,
  usually Angstrom→nm), `_ANODE`, `_KV`/`_MA`, `_STEPTIME`, `_DATEMEASURED` and
  `_GONIOMETER_RADIUS`. (UXD tag semantics confirmed against the Bruker DIFFRAC
  format + xylib's `BT86_.UXD` sample.)
- **Bruker `.raw` v1-3** (`raw_parser.py`): ported from old mudlab's
  BrkRAWParser (NOT PyXRD - old mudlab fixed the RAW3 version detection, the
  RAW3 counting-time type, added CPS normalisation, and `x = min + step*n`).
  `parse_raw_metadata` returns the per-step count time (RAW1 `time_step`; RAW3
  header+192) and, for RAW1 only, the Kα1/Kα2 wavelengths from `alpha1`/`alpha2`
  (Angstrom→nm, sanity-gated). RAW2/RAW4 and Rigaku 'FI' `.raw` return `{}` (no
  mapped metadata). Tested on the real `uk3084R.raw` (RAW3, count time 31.9994 s)
  + synthetic RAW1/RAW3/FI fixtures. **CPS (2026-08-05):** RAW1 now also
  normalises to counts-per-second by its `time_step` (`_header_v1` used to return
  1.0 - a faithful port of an old-app oversight that left RAW1/RAW2 as raw counts
  while RAW3 was CPS). RAW2's count time is still not located, so it stays counts;
  v4 / Rigaku are as stored. Only RAW1/RAW3 (and `.xrdml` / `.uxd`) are CPS.
- **Bruker `.raw` v4** (`raw_parser._parse_v4`): `RAW4.00`, the DIFFRAC.SUITE
  segment-based container, ported from **xylib**'s bruker_raw.cpp
  load_version4 (61-byte header, global metadata segments, then range blocks;
  start_angle@+72, step_size@+80, steps@+88, hdr_size@+140; data = `steps`
  float32 after the 160-byte primary header + `hdr_size` sub-segments).
  Validated on `Dh232.raw`: a Locked-Coupled 5-80 deg / 0.02056 deg scan whose
  quartz(101) 26.5 deg and calcite(104) 29.4 deg peaks land correctly.

**Ground-truth caveat (RAW4):** the `Dh232.UXD` ASCII export is a *processed +
truncated* derivative (XCH converter: Kα2-stripped, ~3x scaled, only 5-60 deg),
so it is NOT a byte-exact golden - its integer intensities do not appear in the
`.raw` at all. It DOES confirm the axis exactly (start 5.0, step 0.02056) and
the quartz peak position, which is how RAW4 is validated in the harness.

- **Rigaku `.raw`** (`raw_parser._parse_rigaku_fi`): a DIFFERENT binary from
  Bruker's (magic `FI\0\0`), reverse-engineered against the same samples' `.rasx`
  export. The 2theta axis is three float32 (start, end, step) at offset 0x0B92;
  the intensities are `count` float32 filling the file to EOF, where
  count = (end-start)/step + 1. The float32 values match the `.rasx` EXACTLY
  (max |d| ~ 5e-12) across all six real Rigaku files. `parse_raw` dispatches on
  the `FI` magic before the Bruker path. (Those samples also exist as `.rasx`,
  which is the same data - the `.raw` is just Rigaku's binary form.)

**Ground-truth caveat (Bruker RAW4):** the `Dh232.UXD` ASCII export is a
*processed + truncated* derivative (XCH converter: Kα2-stripped, ~3x scaled,
only 5-60 deg), so it is NOT a byte-exact golden - its integer intensities do
not appear in the `.raw` at all. It DOES confirm the axis exactly (start 5.0,
step 0.02056) and the quartz peak position, which is how RAW4 is validated.

**Not yet ported:** the other lineage formats (`.cpi`, `.rd`, `.brml`). An
unknown `.raw` magic raises a clear error, shown by the editor in a message box.

Guard: `tools/verify_xrd_import.py` (26 checks) - synthetic fixtures for every
supported format (incl. hand-built Bruker RAW4 + Rigaku FI, and both UXD
layouts) + the dispatcher + the unknown-magic error + EXPORT round-trips, plus
opportunistic real-file cross-checks (`.rasx` vs `.txt` 2theta grid; Bruker RAW4
axis/peak vs the `.UXD`; Rigaku `.raw` vs its `.rasx`) that skip when absent.

### Pattern EXPORT (`file_parsers/xrd_export.py`)

The write side: `save_pattern(path, x, y, goniometer=None, name="")` dispatches
on extension over `xy_parser.save_xy` (ASCII two-column) and
`uxd_parser.save_uxd` (Bruker DIFFRAC `.uxd`, paired `_2THETACOUNTS` with
`_STEPTIME=1` so values write verbatim and round-trip through `parse_uxd`).
`EXPORT_FILTERS` is the save filter. When a `goniometer` is passed (the specimen
export does), the UXD header also carries the diffractometer setup - the real
wavelengths (`_WL1/_WL2/_WLRATIO`, nm->Angstrom x10, replacing a hard-coded
default), `_GONIOMETER_RADIUS`, `_DIVERGENCE(_MODE)`, `_SOLLER1/_SOLLER2`,
`_SAMPLE_LENGTH` - so the export is the pattern AND its geometry, not just the
curve. (ASCII XY has no header, so geometry is UXD-only.) ONLY non-proprietary text formats are offered - the binary/container
vendor formats we can read (Bruker/Rigaku `.raw`, `.rasx`, `.xrdml`) are
deliberately NOT export targets; a `.uxd` or `.xy` carries the same pattern in
an open form. Wired on the Edit Specimen dialog's data buttons
(`btn_import_experimental_data` -> `parse_pattern`;
`btn_export_experimental_data` / `btn_export_calculated_data` -> `save_pattern`),
which were previously inert. Guard: `verify_xrd_import.py` check_export +
`verify_data_op_dialogs.py` (specimen export/import through the buttons).

### Component linking + UCP: debugging notes (audit of Batches L1-L3, 1a-1b)

Behaviours that are correct but non-obvious, and known gaps - read this first
when a cell length / inheritance bug is reported.

- **The first UCP edit "de-stales" both cells.** Any UCP edit calls
  `Component.update_ucp_values`, which recomputes BOTH cell_b (from its pn/other
  source) and cell_a (from cell_b). Stored UCP `value`s in the .mud can be stale
  (`factor*prop+constant` != stored, e.g. Illite/Tri-Smectite cell_a), and we
  deliberately keep the stale value on load (golden-calc fidelity). So the first
  edit to *either* cell can shift a cell the user did not directly touch - this
  is expected recompute-on-edit, not a bug. Editing cell_b's constant also moves
  cell_a (a = factor*b): also expected (cascade), not a bug.
- **atom-pn edits recompute derived cell lengths (FIXED in Batch 2b).**
  `component_widget._on_atoms_changed` now calls `update_ucp_values` and refreshes
  the UCP widgets, so editing an octahedral cation's `pn` moves a `b = k*pn`
  UCP (and the `a = f*b` after it). Editing an AtomRatio does the same via
  `apply_atom_relations` (which applies the relation then `update_ucp_values`).
- **UCP `prop` resolves against a global {uuid: object} map.** Shared atoms
  (same uuid across linked components) collide there - last loaded wins. For
  standalone components the prop resolves to their own atom (verified for
  Illite); for a template whose atoms are shared with linked children the
  resolved atom could be a child's copy (identical value, so load/calc are
  unaffected; only an edit-time cascade could touch the wrong copy). IMPROVEMENT
  (Batch 2): prefer the component's own atoms in `resolve_ucp_props`.
- **Setting `cell_a`/`cell_b` writes the UCP `value` directly**, bypassing the
  derivation - it is overwritten on the next `update_ucp_values`. Fine for the
  read-through propagation tests; refinement never refines cell a/b.
- **`inherit_d001` is vestigial** (d001 inheritance is gated by
  `inherit_default_c`, matching the old app). Carried for round-trip, kept in
  sync with `inherit_default_c` on toggle, shown read-only.
- **Manual links are unrestricted** (any component, not just phase-`based_on`
  ones). Cycle/self-link guarded in `set_linked_with`; round-trips by uuid.
  Linking structurally different layers is allowed (user's responsibility).
- **Round-trip fidelity rests on writing OWN values, not read-through ones:**
  `Component.to_dict` writes `_d001`/`_ucp_a.value`/own atom lists (never the
  inherited values), and `UnitCellProperty.to_dict` keeps `prop` verbatim
  unless the editor set the dirty flag. Regression guards:
  `tools/verify_linking.py`, `tools/verify_ucp.py`, plus the golden
  `verify_calc_engine` and `verify_roundtrip`.

### UUID management (no registry - transient per-load maps)

MudLab2 has **no global object pool**. Every model carries `self.uuid`
(`uuid4().hex` at construction, overwritten from the .mud on load), and
references are resolved by maps built once in `mud_project.load_mud` and then
discarded - the links live on as ordinary object pointers:
`atom_type_map` (atom -> element), `phase_map` (`based_on`, mixture slots),
`component_map` (`linked_with`), `atom_map` + a per-component **own** overlay
(relation atoms, UCP `prop`), `specimen_map` (mixture rows).

- **Loading never interacts with anything already in memory.** Each load builds
  an isolated graph; loading the SAME project twice gives two graphs with
  identical uuid sets but distinct objects and zero interference (verified).
  There is nothing to collide with, so none of the old app's collision
  machinery is needed.
- **Saving does not renumber.** uuids are written as-is; identity is stable
  across save/load. (The old app calls `object_pool.change_all_uuids()` AFTER
  `save_phases`/`save_components` and BEFORE `load_phases`/`load_atom_types`/
  `load_components`, renumbering EVERY object so an import cannot clash - a
  consequence of its global pool, which also forces the pool-lookup hack in its
  `Component.__init__` for shared atoms.)
- **uuids are NOT unique in memory** - and that is expected. Linked components
  each load their own copy of the shared sub-objects, so e.g. 118 atoms carry 76
  distinct uuids (also UCPs 18/10, relations 30/26). Phases, components, atom
  types and specimens ARE unique. This is why resolution must prefer the
  component's OWN atoms (see the identity fix above).
- **to_dict must persist `uuid`.** `AtomRatio` / `AtomContents` /
  `UnitCellProperty` / `Phase` / `Component` write `props["uuid"] = self.uuid`
  (a no-op for a loaded object - it re-writes the uuid it came from, so the JSON
  stays byte-identical; without it a user-CREATED relation was saved with no
  uuid and got a fresh one on every reload). Guard: `verify_relations.py`
  "new ... keeps its uuid across save/reload".
- **FUTURE - import needs a collision policy.** The Add/Import buttons for
  phases / atom types / components are disabled. When import lands, an incoming
  object whose uuid already exists IN THE PROJECT would collide in the per-load
  maps (`phase_map` / `component_map` / `atom_map` dedup) and mis-resolve
  `based_on` / `linked_with` / relation atoms. We do NOT need the old global
  renumber - regenerate only the COLLIDING incoming uuids at import time (and
  re-point the imported object's internal references to the new ids).

### Audit notes: phase inheritance, atom relations, optimizer (2026-07-16)

- **Probe the key that CARRIES the link, not the inlined object.** A phase's
  `based_on` key is serialised as `null` even when the phase IS based on another;
  the link lives in **`based_on_uuid`**. An early probe checked `based_on` and so
  reported "no fixture uses phase inheritance", which is FALSE - every fixture
  (308 included) has `IS R0 Ca-EG`/`IS R0 Ca-350` based on `IS R0 Ca-AD`. The
  same shape applies to components (`linked_with` inlines a copy;
  `linked_with_uuid` is canonical). 308 is nonetheless NON-discriminating for
  inheritance (its parent's values coincide with the children's stored ones), so
  `Dh2040A 14Jul26 r1/r2` remain the fixtures that can actually detect a broken
  read-through - hence the harness's "a discriminating fixture exists" check.

- **FIXED - shared-atom identity in relation / UCP resolution.** Linked
  components share atom uuids and each loads its OWN copy. The load-time
  resolution used a project-wide `atom_map` (last-loaded wins), so a relation /
  UCP prop could resolve to a DIFFERENT component's copy than the one the owner's
  calc iterates. Editing such a relation then updated the wrong object and the
  pattern did not change. Fix (`mud_project.load_mud`): resolve each UCP prop /
  relation atom against the component's OWN atoms first, then the global map.
  Guard: `verify_relations.py` "own-atom identity" check + `verify_ucp`. Keep
  this precedence if that resolution is ever refactored.
- **Chaining relations are NOT applied.** A relation whose target is another
  relation (`atom1`/`atom2` or an AtomContents row with `prop` = "value" /
  "__internal_sum__") is preserved + round-trips but is skipped on apply and not
  shown in the editors. Editing the chain SOURCE does not propagate to the
  driven relation (the old app's `driven_by_other` machinery is not ported).
  Low impact: the samples' chained relations only affect the calc through their
  already-applied stored pn, which is kept.
- **Overlapping relations apply in list order (last wins).** If two relations
  drove the same atom, order would matter; the samples have zero overlap
  (checked). The old app's conflict resolution is not ported.
- **Inherited relations propagate through the atom read-through, not apply.** A
  child that inherits `atom_relations` keeps its own (stub) relations; editing
  is disabled. Because it also inherits `layer_atoms`, its calc reads the
  TEMPLATE's atoms, so editing the template's relation (which updates the
  template's own atoms) is reflected in the child - correct once the identity
  fix above is in place.
- **`inherit_display_color` is carried but inert** (the phase display colour is
  a visuals-only property not modeled yet); only `sigma_star` / `CSDS` /
  probability `F` read through at the phase level.
- **Probability F read-through follows the phase `based_on` chain**, which is
  cycle-guarded at resolve time, so `R0Probability.f_value`'s recursion cannot
  loop even though it has no guard of its own.
- **Optimizer multi-start is standalone-only.** `Mixture.optimize` uses
  `n_starts=4` (exact-current + least-squares scale/bg + random-fraction
  restarts, deterministic seed); the refinement inner loop calls
  `optimize_mixture` with `n_starts=1` (unchanged, fast). The LS warm start
  assumes the calc is linear in scale + bg-shift (it is: `scale*signal +
  bgshift*correction`). Never regress the `n_starts=1` path or refinement slows
  ~4x. Guard: `verify_optimizer` (cold-start recovery) + `verify_refinement`.

### Phase-level `based_on` inheritance (IMPLEMENTED - model; UI pending)

Old sources: `phases/models/phase.py`,
`phases/controllers/edit_phase_controller.py`,
`phases/controllers/component_controllers.py`.

**This was a correctness BUG, not just a missing feature.** Until it was
implemented, any project using phase inheritance computed WRONG patterns: the
`Dh2040A 14Jul26 r1.mud` fixture's EG/400 specimens missed the old app's stored
pattern (corr 0.83 / 0.97). With the read-through they match to floating point
(corr 1.000000). `tools/verify_calc_engine.py` + `tools/verify_phase_inheritance.py`
guard it, and the fixtures pin it in BOTH directions: **r1** keeps the links
intact (a child must use the parent's F1=0.17 over its own stale 0.8), while
**r2** unlinks per-flag (EG must use its OWN F1=0.3 and ignore the parent, while
350 still inherits). Inheriting where you should not is as wrong as not
inheriting - r2 catches that. **The load-bearing part is the stacking
probabilities**, not sigma*/CSDS:

- `probabilities` are SEPARATE objects per phase carrying `inherit_F<i>` flags.
  The child stores its OWN, usually STALE, `F<i>` and must read the parent's
  (in the refined fixture: parent F1 = 0.17, children still store 0.8). W and P
  are therefore derived on demand from the EFFECTIVE F (`R0Probability._weights`),
  so a parent edit / refinement step propagates at once.
- `CSDS_distribution` is a SHARED object (same uuid across the phases), so it is
  already stored pre-resolved - which is why only F diverged.
- `sigma_star` was unrefined (3.0 everywhere) in the fixture, so its
  inheritance is untested by the golden pattern (the read-through is correct by
  construction and covered by the propagation check).

Implementation: `Phase.based_on` + `inherit_sigma_star` /
`inherit_CSDS_distribution` / `inherit_display_color`, read-through via
`Phase._resolved` (cycle-guarded) and `R0Probability.f_value`;
`Phase.resolve_based_on` wires the child's probabilities to the parent's;
`mud_project.load_mud` resolves it before the component links. **Serialisation
writes OWN values** (`_sigma_star`, `_CSDS.average`, `own_f_params()`) so a
child round-trips its stale stored F byte-identically. Inherited sigma* / CSDS /
F are skipped as refinables (they follow the parent).

**Editor (edit_phase_widget.py + probabilities_widget.py):** the `phase_based_on`
combo lists the project's phases **with the same G** (the F params pair up
one-to-one, as the old app required) plus "(not based on)"; picking one calls
`Phase.set_based_on` (self/cycle/G guarded, a rejected pick reverts the combo),
"(not based on)" detaches and clears the inherit flags. `phase_inherit_sigma_star`
/ `phase_inherit_CSDS_distribution` are enabled only when based on something;
ticking one greys the sigma* spin / the CSDS component (it now shows the
reference phase's value) and recomputes. The **per-F "Inherit" check-boxes** live
next to each F spinbox in the probabilities widget (old `inherit_F<i>`): ticking
greys the spin and shows the parent's F. Candidates are threaded from
`EditPhasesDialog._phase_candidates` -> `bind_phase`.
DEVIATION: the old `based_on` setter also cleared every component's
`linked_with` (its component-link combo was restricted to the parent's
components); MudLab2 links components freely by uuid, so `set_based_on` leaves
them alone. `phase_display_color` + its inherit box stay disabled (the colour is
a visuals-only property that is not modeled yet).

- **Purpose (domain):** model the *same clay under different treatments* -
  air-dried / ethylene-glycol / heated (350, 550 C). The treatments change the
  interlayer (smectite swells under EG, collapses on heating) but not the
  mineralogy, so a treated phase is `based_on` a reference phase and inherits
  everything treatment-independent, overriding only the d-spacing/interlayer.
  The sample phase names show it: `IS R0 Ca-EG` / `IS R0 Ca-350` are `based_on`
  `IS R0 Ca-AD` in EVERY fixture (308 included), on top of the per-layer
  component linking.
- **Why it matters - refinement:** inherited structural params (sigma*, CSDS,
  stacking probabilities, layer chemistry) are optimised ONCE and all treatments
  follow - enforcing physical consistency and collapsing the free-parameter
  count in a multi-pattern AD+EG+heated fit.
- **What it inherits:** sigma*, CSDS distribution, display colour (InheritableMixin
  `inherit_*` flags), the stacking probabilities, and the components - setting
  `based_on` clears the child's component links and re-points each component's
  "Linked with" at the PARENT phase's components (positional; hence the
  same-`G` requirement).
- **Constraints (old app):** same project (`based_on.parent == self.parent`),
  same `G`, no cycles (`get_based_on_root`), parent serialised before child
  (`_pre_multi_save`). Round-trips as `based_on_uuid`.
- **Relationship to L1-L3:** `based_on` is the coarse phase-level wrapper that
  *gates and restricts* component linking to the parent's components. Our L3
  link/unlink UI is the freeform version (link to any component). When `based_on`
  is ported it drives those links positionally and (old setter, phase.py:119-120)
  supersedes manual ones - so the L3 combo should become based_on-aware then.
- **Implementation sketch (mirrors the linking batches):** model `Phase.based_on`
  (resolve by uuid via the existing phase map) + `inherit_sigma_star` /
  `inherit_CSDS_distribution` / `inherit_display_color` (+ probability inherit)
  as read-through getters; skip inherited sigma*/CSDS as refinables; wire the
  already-present-but-disabled `phase_based_on` combo + `phase_inherit_*`
  checkboxes; a `verify_phase_inheritance.py` harness. The component-set
  inheritance (positional re-linking) is the part that needs the golden fixture.

### R1 (Reichweite-1) stacking (Batch R1a - MODEL + calc)

R = "reach": how many preceding layers influence the next. R0 = independent
(every P row identical = the weight fractions); R1 = nearest-neighbour
ordering (P rows DIFFER). **The intensity summation was already R-agnostic**
- `calculations/phases.py` reads `rank = P.shape[1]; reps = rank // G` and
  expands with `np.repeat`, so it consumes any W/P. R1a only added the MODEL
  that produces the R1 matrices.

- `models/probabilities.py` `R1G2Probability` (old R1G2Model): two params
  `W1`, `P11_or_P22`; `_pmatrix()` ports `R1G2Model.update` verbatim (two
  branches on `W1<=0.5`, the other three P entries from row-stochasticity +
  detailed balance `Wi·Pij = Wj·Pji`). For R1G2 the matrix is 2×2, so
  `reps == 1` - the higher-`reps` path (R2/R3) is still unexercised.
- `probabilities_from_dict` now DISPATCHES on the type string: `R1G2Model` ->
  `R1G2Probability`, `R0G*` -> `R0Probability`. **Any other higher-R type still
  falls back to R0 and is silently mis-modeled** - there is no fixture for one,
  so a project using e.g. R1G3/R2 must be caught before it reaches the calc
  (a guard is TODO with R1c).
- Inheritance parallels R0's per-F flags: `inherit_W1` / `inherit_P11_or_P22`
  read the effective value through to the based_on parent (`w1_value()` /
  `p11_value()`), so a refined/edited parent propagates at once. Wired by the
  existing `Phase.resolve_based_on` -> `probabilities.set_based_on`.
- **Serialization is model-delegated (Batch R1b)**: `Phase.to_dict` no longer
  hard-codes F params - it calls `self.probabilities.write_properties(props)`,
  which each model implements (R0 writes F1..Fn + inherit_F<i>; R1G2 writes
  W1 / P11_or_P22 + their inherit flags). OWN values, so a loaded project is
  byte-identical AND an edit persists. `Phase.set_based_on`'s detach likewise
  delegates to `probabilities.clear_inheritance()` (R0 clears inherit_F, R1G2
  clears inherit_W1 / inherit_P11_or_P22) - the old code set inherit_F
  directly, a no-op stray attribute on R1 that left its real flags set.
- Fixture `Dh537A.mud` (three `IS R1 Ca-*`, EG/350 inherit from AD). The
  R0-fallback failed its golden calc at corr 0.984; R1a reproduces it at
  corr 1.000000. Guards: `verify_r1.py` (model internals) + `Dh537A` in
  `verify_calc_engine.py` (integration). **Branch-coverage caveat**: every R1
  phase there has W1 ~ 0.73, so the golden calc exercises only the `W1>0.5`
  branch; the `W1<=0.5` branch is covered by the synthetic `2b` check and the
  edit-persistence check (`W1=0.4237`) in `verify_r1.py`.
- **Refinement + editor are model-agnostic (Batch R1c)**. Each model exposes
  two descriptor lists so neither the refiner nor the editor hard-codes F:
    - `refinable_params()` -> (label, get, set, ref_info_key, bounds,
      inherited); `refinement._phase_refinables` iterates it and skips the
      inherited ones. R0 -> F1..Fn, R1G2 -> W1 / P11_or_P22. On Dh537A only
      the non-inheriting AD contributes W1/P11 (EG/350 read through).
    - `editable_params()` -> dicts (label, tooltip, get effective, set own,
      inherited, set_inherited, inherit_tooltip); `probabilities_widget`
      builds one spin + Inherit checkbox per entry and shows W/P below. The
      R1 tab therefore shows **W1 and "P11 / P22"** rows, not F. can_inherit
      (= `phase.based_on is not None`) gates the Inherit boxes; ticking greys
      the spin and shows the parent's value, unticking restores the child's
      own. R0 output is unchanged (same F labels / ref_info keys / bounds).
- **Add dialog unlocks R (Batch R1d)**: `add_phase_dialog` offers R 0-1
  (R2+ unported); `_on_R_changed` locks G to 2 when R=1 (only R1G2 exists) and
  restores G 1-6 for R0. `Phase.create_empty(G, R)` builds the matching model
  - R0 (any G) or `R1G2Probability` (forces G=2) - and `_on_add_phase` passes
  `dialog.R` through.
- **New-phase probability serialization (fixed in R1d)**: `Phase.to_dict` now
  emits a probabilities dict even when `raw_properties` had none (a freshly
  created phase), stamping the model's `type_name` (`R0G<g>Model` /
  `R1G2Model`) so `from_dict` dispatches correctly. Before this a NEW phase -
  R0 or R1 - lost its probabilities on save: it reloaded as default R0 with
  F=0.8 (a latent P2 bug that only surfaced once R1 phases could be created).
  A loaded phase keeps its stored `type` verbatim, so byte-identity holds.
- **Unported higher-R types are REFUSED on load** (not silently R0-degraded).
  `probabilities_from_dict` raises `UnsupportedProbabilityModel` for any
  recognised type other than R0*/R1G2Model (an empty dict is a new phase ->
  R0). The message is user-facing; the open-project handler already wraps
  `load_mud` in a try/except that shows it and keeps the current project. So a
  project with e.g. an R1G3 phase is rejected with "... the 'R1G3Model' ...
  model, which MudLab2 does not support yet" rather than loaded as a wrong
  R0 pattern. Guard: `verify_r1.py` check 12 (unit + a synthesised R1G3 .mud
  that `load_mud` refuses).
### R2 (Reichweite-2): R2G2 modeled - first `reps>1` proof

R2 = a layer depends on the TWO before it, so the state is a PAIR of layers
and W / P are g²×g² (4×4 for G2). This is the FIRST model to exercise the
calc's `reps = rank // G` path (`= 2` here): `phases.py` repeats the G×G
structure factors up to the 4×4 rank. That path was untested until now;
R2G2 validates it at corr 1.000000 (`verify_calc_engine` on
`Illite-Smectite R2 G2[.mud/ MPDO]`).

- `models/probabilities.py`: a shared `_MarkovProbability` base carries the
  per-parameter inheritance, validity, serialization and editor/refiner
  descriptors generically over a `PARAMS` tuple (so R2G3 / R3G2 / R1G3 will
  be a `PARAMS` list + a `_matrices()` port, nothing else). `R2G2Probability`
  (`PARAMS` = W1, P112_or_P211, P21, P122_or_P221) ports `R2G2Model.update`:
  the four pair weights and eight 3-layer junction probabilities via detailed
  balance, assembled into the 4×4 diagonal W and the block-sparse 4×4 P
  (state order x = 2i+j; a transition from (i,j) is only allowed to (j,k)).
- Every higher-R model is now this shape - a `PARAMS` list + a `_matrices()`
  port on `_MarkovProbability`, one dispatch line, validated against its
  golden. Modeled: **R1G3** (3×3, reps 1), **R2G2** (4×4, reps 2), **R2G3**
  (9×9, reps 3), **R3G2** (8×8, reps 4). Each ports the corresponding old
  `RxGyModel.update` verbatim (pair/triplet weights + junction probabilities
  via detailed balance), assembling the g^R×g^R diagonal W and block-sparse P
  where a state's transition only reaches the states sharing its trailing
  layers.
- **Validity for zero-weight states**: `_MarkovProbability.valid` checks P
  rows stochastic only for states with nonzero weight. R2G3's restrictions
  forbid consecutive expandable layers, so several pair-states have zero
  weight and legitimately all-zero P rows - the calc multiplies those rows by
  0, so they are unconstrained. (An all-rows check would wrongly report the
  phase invalid -> the calc would blank it.)
- **`get_absolute_scale` note**: it takes `np.diag(phase.W)` and indexes by
  component, so for R>=2 it reads the first G *pair/triplet* weights, not the G
  marginal single-layer weights. This is IDENTICAL to the old app (the calc is
  a verbatim port), so reproducing it is CORRECT for matching goldens; and it
  is a per-phase scalar, absorbed by the scale fit (harmless for single-phase
  fixtures). Do NOT "fix" it - it would diverge from the golden.
- Guards: `verify_calc_engine.py` (golden proof, all fixtures + MPDO twins,
  corr 1.000000) and `verify_higher_r.py` (43 checks: dispatch, shape/reps,
  validity, per-parameter inheritance, editor/refiner enumeration,
  byte-identical round-trip + edit persist, across all four models; plus an
  INDEPENDENT re-derivation of R2G2 and R2G3 matrices). **Fixture-coverage
  gap recorded**: the `R2 G3` fixtures pin G1-G4 at 0.5 (where G <-> 1-G is
  invisible), so the golden does NOT discriminate the four G ratios - they are
  guarded ONLY by the `verify_higher_r` re-derivation at G=0.6 (both W1
  branches). R1G3's fixture G-params (0.8/0.7) ARE discriminating, but its
  W1=0.5 leaves the W1>0.5 branch golden-untested (a discriminating R2G3 /
  high-W1 R1G3 fixture would close both, if wanted).

### R1G4: MATRIX-validated vs the real old app (no full-pattern fixture yet)

`R1G4Probability` (4×4, reps 1, 12 params) ports `R1G4Model.update` verbatim
from PyXRD (`C:\Users\pxgho\PyXRD`; confirmed byte-identical to old mudlab's).
It dispatches and loads like the others. There is no R1G4 `.mud` test project,
so it does not get a stored-**pattern** golden - but it gets the next best
thing, a **matrix golden against the REAL old app**: the old mudlab ships its
own Python 3.14 interpreter (`C:\GitHub\MudLab\data\bin\python3.14.exe`), so
`R1G4Model` was run there directly and its resolved W/P compared to
`R1G4Probability._matrices()`. They agree to **0.0** (`< 1e-12`) on the
default-phase parameters (the old app's CSSS/ICSS/ISSS/KCSS/KSSS/TSSS R1
library phases, found under `%LOCALAPPDATA%\MudLab\default phases`) **and both
W1 branches** - `verify_higher_r.py check_r1g4_golden` / `_R1G4_OLD_APP_GOLDEN`.
Because R1G4 is reps=1, it shares the calc path already golden-validated
end-to-end by the R1G2/R1G3 pattern fixtures, so exact matrices make its
pattern trustworthy. The only remaining gap is a saved-`.mud` **pattern**
golden: if an R1G4 project is made in the (fixed) old app, add it to
`verify_calc_engine`. The class docstring carries the same status.

**All PyXRD R/G stacking models are now present** (R0 any G; R1 G2-G4;
R2 G2-G3; R3 G2). The dispatch refuses only genuinely non-PyXRD types (e.g.
R4/G, R2G4).

### Audit notes: R/G stacking models (2026-07-19)

Full code audit of every stacking model (`models/probabilities.py`) and the
calc path they feed (`calculations/phases.py`). Method: read each `_matrices()`
against the old-app source, plus an INDEPENDENT matrix cross-check - the old
mudlab ships its own Python 3.14 interpreter (`C:\GitHub\MudLab\data\bin\
python3.14.exe`), so every old-app model (R1G2, R1G3, R2G2, R2G3, R3G2) was run
there directly and its W/P compared to MudLab2's, on BOTH branches each.

**Clean results (nothing to fix):**
- **Matrix cross-check: max |Δ| = 0.0 (`<1e-12`)** on all 5 models × both
  branches (10 param sets, incl. deliberately invalid ones as arithmetic
  stress). R1G4 was already covered the same way (`check_r1g4_golden`). So
  every model reproduces the real old app's matrices exactly, and each R2/R3
  model additionally has a golden PATTERN fixture at corr 1.000000.
- **Branch boundaries match the old source exactly**, including the deliberate
  inconsistency: R1G2/R1G3/R2G2/R3G2 switch the free junction at `<=` the
  threshold, R1G4/R2G3 at strict `<`. (At the threshold both branches are
  continuous, so it is cosmetic - but faithful.)
- **R3G2's `clamp()` calls are faithful** - the old `R3G2Model.update` has the
  same `max(min(x,1),0)` on every P/W it assigns; not a MudLab2 addition.
- **State-ordering conventions** (x = 2i+j for R2G2, 4i+2j+k for R3G2, 3i+j for
  R2G3) match the old app's `mW`/`mP` index maps; verified the calc only needs
  `_W` (=`_lW[-2]`, the g^R diagonal) and `_P` (=`_lP[-1]`), which `update()`
  writes directly and `solve()` never clobbers.

**Finding (FIXED 2026-07-19): W1 refinement/editor bounds were too loose for
the constrained models.** The old app constrains W1 to its physical domain via
`FloatProperty(minimum=...)`: **R2G2 W1>=0.5, R2G3 W1>=0.5, R3G2 W1>=2/3** (all
other params, and W1 for R0/R1, are (0,1)). MudLab2 had hard-coded `(0.0, 1.0)`
in `refinable_params()` and `spin.setRange(0.0, 1.0)` in the editor, so the
refiner could drive W1 below the threshold and the editor let a user type an
out-of-domain W1 (not silently wrong - an out-of-domain W1 makes the weights
fail to sum to 1, e.g. R3G2 `w000 = 3W1-2 < 0` clamps to 0, so `valid` is False
and the calc returns zeros, which the refiner's non-worsening guard rejects -
but refinement wasted evaluations on a flat "zeros" plateau and the editor lost
a guardrail). **Fix:** a per-parameter `BOUNDS` dict on `_MarkovProbability`
(default (0,1); R2G2/R2G3 W1 -> (0.5,1), R3G2 W1 -> (2/3,1)) now feeds both
`refinable_params()` (the bounds slot) and `editable_params()` (a new `bounds`
key), and the widget calls `spin.setRange(*spec["bounds"])`. (The 4-dp spin
rounds 2/3 to a min of 0.6667 - just ABOVE 2/3, so still safe.) Guard:
`verify_phase_dialogs.py` check 6.

**Finding (FIXED 2026-07-19): the probabilities editor truncated the W/P
tables for R>=2.** The widget hard-coded the tables to `G` and `G x G`, but for
R>=2 the state is a layer PAIR/TRIPLET so the real matrices are `g^R x g^R`
(4x4 R2G2, 8x8 R3G2, 9x9 R2G3). It silently showed only the first G weights and
the top-left `G x G` corner of P, labelled with layer names that do not
describe the states (no crash - the reads were in-bounds). Parameter *editing*
was always correct (generic over `editable_params()`), so the calculated
pattern was never affected - only the read-only matrix DISPLAY. **Fix:** the
widget now sizes the W table to `rank = len(get_distribution_array())` and P to
`rank x rank`, and labels the `g^R` axes with their state tuples (1-based layer
numbers, e.g. R2G2 `1,1 1,2 2,1 2,2`); tables with >4 columns size-to-content
and scroll, capped to ~6 visible rows so an 8x8/9x9 does not blow out the tab.
Guard: `verify_phase_dialogs.py` check 6 (table dims == rank, last cell shown,
per-model). The editor is now validated for every model, not just R1G2.

**Landmine note (correct, do NOT "fix"): `get_absolute_scale` reads the first
G diagonal entries of the g^R×g^R weight matrix, not per-component marginals.**
For R>=2 `W[0..G-1]` are the first few PAIR/TRIPLET-state weights (e.g. R2G2:
W00, W01), which are not the marginal component fractions. This is IDENTICAL to
the old app and the R2/R3 golden patterns pass at corr 1.000000 because of it -
reproducing it is required for fidelity. It is the single most surprising line
in the calc; flagged here so a future reader does not "correct" it.

**Minor (cosmetic, no action needed):** `R0Probability.valid` (line ~112) has a
tile-and-sum check that is always true once `sum(mW)==1` is asserted just above
(dead but harmless); `R2G3._matrices` sets `W2w = None` then overwrites it on
the next line (awkward, correct). Read-through inheritance (`value()` recursing
into `based_on_probs`) has no cycle guard of its own - it relies on the phase
linking layer to prevent based_on cycles (same assumption as R0; see the
linking notes). Not exercised by any current fixture; fine, but a based_on
cycle would infinite-loop.

**Verdict:** the model + calc layer is solid and faithful to the old app at
machine precision across every R/G type and both branches. One low-moderate
follow-up (W1 bounds) and one clearly-marked landmine; no correctness bug.

### Audit notes: R1 (2026-07-17)

Audited R1a-d after the fact, probing the dimensions the R1 harness did not:
remove_phase on an R1 based_on chain, a FULL refine, ref_info round-trip,
valid/invalid edges, UI detach, optimize(), and the higher-R load path.

**Clean (no R1 defect):**
- `remove_phase` on the AD parent detaches EG/350 correctly - their R1
  inherit flags clear (via `set_based_on(None)` -> `clear_inheritance`) and
  they fall back to their own stored W1 (1.0000 / 0.6211). The R1c-2 UI detach
  (based_on combo -> "(not based on)") clears the R1 flags too.
- `n_independents` is used only inside R0's own methods; nothing external
  assumes `== G-1`, so R1G2 returning 2 leaks nowhere.
- R1 refine flag + bounds round-trip through `W1_ref_info` /
  `P11_or_P22_ref_info`. `optimize()` (fractions/scales/bg) is not worsened.
- Edge params: `W1` 0 or 1 are valid-but-degenerate; `P` or `W1` out of
  [0,1] -> `valid` False; the `_pmatrix` zero-denominator guards hold (no
  divide-by-zero, all finite).
- Higher-R types (R1G3 / R2 / R3) still silently degrade to R0 on load
  (documented gap; no crash).

**FINDING - refinement can leave the model worse than it started
(PRE-EXISTING, param-agnostic; R1 only exposed it).** `optimize_mixture`
warm-starts its inner fraction/scale/bg fit from the mixture's CURRENT
fractions, so its result depends on call history. During the outer search
`best_residual` is recorded at whatever warm-start was current then;
`refine_mixture` ends with `apply_best()`, which re-runs `optimize_mixture`
from the search's FINAL warm-start and can land at a different (worse) inner
local optimum. Consequences, both real:
  1. `refiner.best_residual` **overstates** the applied fit - the Refinement
     window shows Best 19.12977 while the applied state is 19.13111. Present
     for R0 too (34.00989 shown vs 34.01048 applied).
  2. When the flagged structural param cannot net-improve, refine can leave
     the model **worse than initial** (19.13033 -> 19.13111). R1's fixture is
     already near-optimal, which is why W1 triggered it where R0 F1 (a big
     genuine improvement) masked it.
Not caused by R1 - it is a property of the warm-started multi-start optimiser
plus `apply_best`.

**FIXED (2026-07-18).** `refine_mixture` now snapshots the exact pre-refine
state (structural values + fractions/scales/background) and its genuine
"before" residual `pre_residual = get_current_residual(mixture)`. After the
search it measures what `apply_best()` actually achieved (the `apply_*`
methods now return their achieved residual); if that is not finite or is
worse than `pre_residual`, it restores the snapshot exactly (not
`apply_initial`, which would re-optimise from the wrong warm-start and could
not reproduce the before-state either). Either way `best_residual` is set to
the residual that is genuinely APPLIED, so the Refinement window's number
matches the model's real state. Net: refine is never worse than it started,
and `best_residual` never overstates. Guard: `verify_r1.py` check 13 (flags
Dh537A's already-optimal W1, asserts after <= before and
`best_residual == applied`); mutation-tested - reverting to the unguarded
`apply_best` reproduces 19.13033 -> 19.13111. The R0 fixtures do not exercise
it (there refine genuinely improves, so "never worse" is trivial), which is
why the guard lives in the R1 harness.

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
- Fill from element (2026-07-22): `atom_element_picker` lists the built-in
  scattering-factor library and, on pick, copies that element's atom_nr /
  weight / debye / charge / par_c / par_a / par_b onto the bound atom type
  (its name + uuid are LEFT intact, so atoms that reference it still resolve);
  the combo resets to its placeholder after. The library is
  `file_parsers/atom_type_library.py` reading `mudlab/data/`
  `atomic_scattering_factors.csv` (the old `.atl` verbatim - Waasmaier-Kirfel
  coefficients, bundled via MudLab.spec). This is Step 1 of the default-phase
  catalog: a default component's atoms resolve their coefficients against this
  same library. Harness `tools/verify_atom_type_library.py`.

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
  calculate()`, so the pattern redraws live. Row/col constants live in the
  widget module.
- Per-phase fraction refine flag (2026-08-04): the fraction cell also carries a
  checkbox (`_set_cell(..., check=...)`, `ItemIsUserCheckable`) bound to
  `Mixture.fraction_refine` / `set_fraction_refine` - the old app's
  `fractions_mask`. Checked = Optimize refines this phase's fraction; unchecked
  = the fraction is held fixed (for manual setting), and the optimiser
  renormalises the remaining free fractions to `1 - sum(fixed)`. The mask lives
  in `raw_properties["fractions_mask"]` (1 = refine), stays one-per-slot as slots
  are added/removed, and round-trips. `_on_item_changed` syncs the check state to
  the model before the (unchanged) fraction value falls through to the single
  `on_changed`. `Mixture.from_dict` calls `_normalize_fractions_mask()` on load
  so a length-drifted / garbage mask off disk (a corrupt or legacy .mud) is
  padded/trimmed to the phase count (or dropped) - the optimiser reads the mask
  by index and would otherwise IndexError on an over-long one. Harnesses:
  `tools/verify_fraction_refine.py` (model + optimise + load-normalise),
  `tools/verify_fraction_refine_ui.py` (the checkbox widget).
- Phase-cell assignment (2026-07-21): each phase cell is a `QComboBox`
  (`_set_phase_combo`) offering "(none)" + every project phase; choosing one
  calls `Mixture.set_phase_at(specimen_i, slot_j, phase)`, which writes BOTH
  the resolved grid (`phase_matrix`, what the calc reads) and the uuid grid
  (`phase_uuids`, what round-trips), then recomputes. `bind_mixture` now takes
  `phases=` (the dialog passes `project.phases`). A phase that is not
  `phase.is_valid` (an empty component slot -> blank pattern, or a raw phase
  with no measured pattern) is listed but DISABLED (greyed, with a tooltip) so
  it cannot be assigned - the validity gate the old app lacked. The combo
  signal is connected AFTER `setCurrentIndex`, and `_populate` calls
  `setRowCount(0)` before repopulating to drop the prior bind's cell widgets.
  Harness: `tools/verify_mixture_assign.py`.
- Refinement (2026-07-10): `btn_optimize` runs `Mixture.optimize()`
  (L-BFGS-B, calculations/mixture.py) under a busy cursor inside a
  UI-boundary try/except -> `QMessageBox` on failure (the optimizer core
  fails loud; this is the only safety net). On success it re-populates the
  matrix with the refined solution and updates the `lbl_residual`
  "Residual (Rp)" label (also shown on bind via `Mixture.current_residual`).
  `Mixture.optimize` uses a **multi-start** search (`n_starts=4`, 2026-07-16):
  the exact current solution + a least-squares scale/bg warm start + random-
  fraction restarts, keeping the best - robust to a poor starting point and
  never worse than the current solution. The structural-refinement inner loop
  calls `optimize_mixture` directly with the single-start fast path
  (`n_starts=1`), so refinement runtime is unchanged.
  The `mixture_auto_run/scales/bg` checkboxes are editable and persisted
  (stored in `raw_properties`); they select which variables Optimize frees
  (fractions_mask from the .mud gates fractions). F5 Refresh Graph calls
  `project.refresh()` -> `Mixture.update()`, which optimises auto_run
  mixtures and re-applies the rest.
- `btn_refine` (2026-07-11) opens the Refinement window
  (`refinement_dialog.py` RefinementDialog) for structural-parameter
  refinement; the mixture editor re-populates when it closes. See the
  Refinement window section below.
- Structural add/remove (2026-07-21, Batch 2): `btn_add_phase` /
  `btn_add_specimen` / `btn_add_both` append a slot or specimen via the new
  model methods `add_phase_slot("New Phase", 1.0)` / `add_specimen_slot(None,
  1.0, 0.0)` (each keeps phase_labels/fractions/fractions_mask and every
  phase_matrix + phase_uuids row/col in step; a fresh phase row is empty cells,
  a fresh specimen column is unassigned). REMOVE + rename + specimen-assignment
  live on the table's HEADERS (context menus, so the grid body stays a clean
  value matrix): right-click a phase-slot ROW header -> "Rename phase slot…"
  (`set_phase_label` via QInputDialog) / "Remove phase slot" (`del_phase_slot`);
  right-click a specimen COLUMN header -> "Assign specimen" submenu (project
  specimens + "(none)", `set_specimen_at`) / "Remove specimen"
  (`del_specimen_slot`). Headers get `CustomContextMenu` policy in
  `_install_header_menus`; the two fixed rows (scale/bg) and the Fraction column
  carry no menu. `bind_mixture` now also takes `specimens=` (the dialog passes
  `project.specimens`). Every structural edit repopulates + recomputes +
  refreshes the residual (`_after_structural_change`). Harness:
  `tools/verify_mixture_structure.py`. This closes the raw-phase-as-new-slot
  gap: Add phase, then assign the raw phase in its cells.
- Composition (2026-07-22): `btn_composition` opens the modal `CompositionDialog`
  (composition.ui / composition_dialog.py) for the bound mixture - a read-only
  oxides x specimens table of the per-specimen oxide wt% composition, with Copy
  / Export CSV. Analytics in `calculations/composition.py` (old
  Mixture.get_composition_matrix), conversion table in
  `mudlab/data/composition_conversion.csv` (bundled via MudLab.spec `datas`).
- Shell Add / Remove (2026-07-22, edit_mixtures_dialog.py): `button_add_object`
  creates a blank `Mixture(name="New Mixture")` directly - NO dialog. The old
  add_mixture.glade type-chooser (regular vs in-situ) was abandoned dead code
  (in-situ never finished; `create_new_object_proxy` just returns a Mixture), so
  Add makes a blank regular mixture, adds it to the project + list and selects
  it; the user then builds the grid with the editor's Add phase/specimen. Remove
  (`button_del_object`) confirms, then `Project.remove_mixture` (no cascade -
  nothing back-references a mixture) and reselects a neighbour. The mixture
  editor is fully wired.
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
- **Progress plot (2026-08-01)** — a `grpProgress` group box holds a live
  convergence plot (best Rp vs evaluations) on a matplotlib `FigureCanvasQTAgg`
  (`_setup_progress_plot`). `_on_progress` only APPENDS `(n_evals, best_residual)`
  and sets a dirty flag; a 150 ms `QTimer` (`_redraw_progress`) does the throttled
  redraw, so thousands of evaluations never flood the GUI. `_start_progress`
  (in `_on_refine`) resets the series + arms the timer; `_finish_progress`
  (in `_on_finished`/`_on_failed`) stops it + forces a final redraw; `closeEvent`
  stops the timer. Guarded by `tools/verify_refine_progress_plot.py`.
- Deferred / dropped: the parameter-space / landscape plot (its brute-force grid
  scan was removed; `Refiner.record_history` hook still available for a future
  full-trajectory view).

## Add Phase dialog: add_phase.ui

`mudlab/add_phase_dialog.py` (`AddPhaseDialog`), modal, old
`phases/glade/addphase.glade` AddPhaseView. Opened by the Edit Phases
shell's Add button (`EditPhasesDialog._on_add_phase`); on accept the
handler builds a real phase and appends it (Batch P2).

- Three radio choices (old ids kept): `rdb_empty_phase` (with `G` spin
  1-6 and `R` spin), `rdb_default_phase` (with `cmb_default_phases` +
  `btn_generate_phases`), `rdb_raw_pattern`. Radios enable their own
  container (old `update_sensitivities`).
- Result accessors mirror the old view: `phase_type`
  ("empty"/"default"/"raw"), `G`, `R`, `default_phase`.
- **All three paths are wired** (`rdb_empty_phase` preselected). The DEFAULT
  catalog (2026-07-22): `cmb_default_phases` lists `default_catalog_entries()`
  (the modeled R0/R1G2 built-in reference clays); on OK,
  edit_phases_dialog `_on_add_phase` calls
  `default_catalog.add_catalog_entry_to_project`, which builds the entry in
  memory from the bundled `.cmp` components + the ported recipe and adds its
  phase-set (a single clay, or an AD/EG/350 triple) with its atom types merged
  by name. `btn_generate_phases` is obsolete (the catalog is built in memory -
  nothing to regenerate) and disabled with that tooltip. RAW-pattern is wired
  too (its editor + pattern import exist).
- **R is locked to 0** (disabled, tooltip), because MudLab2 models only R0
  (random) stacking - `get_correct_probability_model(R, G)` is not ported
  for R>0, so a higher-R phase would build an invalid model. The old app's
  "R needs G>1" enable rule is therefore gone; R is simply always 0.

### Import / Export phases (.phs) (Batch 4 DONE)

`file_parsers/phs_phases.py` (`save_phs` / `load_phs`) + the `EditPhasesDialog`
Import/Export buttons (`_on_import_phases` / `_on_export_phases`). A `.phs` is a
ZIP of `<index>###<uuid>` -> Phase JSON members (same serialisation as a `.mud`
phase entry); multiple phases form a based_on family.

- **Atoms reference atom types by NAME**, so a `.phs` imports against whatever
  atom types the target project holds (MudLab2's name-fallback). Export forces
  name-based refs (`_make_portable` stamps `atom_type_name` into the export
  dict) so the file is portable even from a uuid-based `.mud`. Verified against
  the real old-app default library (Illite/Kaolinite/Chlorite `.phs` import with
  every atom resolved).
- **Export** (`save_phs`): a phase whose based_on is not in the exported set is
  written standalone (based_on dropped, inherit flags cleared); parents are
  ordered before children. `load_phs` reports atom types the project is missing
  (a warning dialog) so the user knows some atoms will be inert.
- **Collision policy - DEEP remap** (the clean replacement for the old app's
  ObjectPool re-uuid + `change_all_uuids`): before the models are built,
  `load_phs` finds every uuid in the file that already exists in the project -
  phase, component OR atom - and replaces it with a fresh one CONSISTENTLY
  across all members via a plain string replace on the serialised JSON (uuids
  are 32-hex, so this catches every reference - own uuid, based_on_uuid,
  linked_with, atom relations, UCP sources - without knowing the schema). So
  re-importing the same `.phs` into the same project never aliases an existing
  phase / component / atom, and the resulting `.mud` has no duplicate uuids. A
  file whose uuids do not collide keeps them unchanged.
- The post-load reference resolution (based_on / linked_with / UCP / relations)
  was factored out of `load_mud` into `mud_project.resolve_phase_references`,
  which `load_phs` reuses.
- Guard: `tools/verify_phs_import.py` (14 checks: export shape, round-trip into a
  seeded project, missing-atom-types report, the DEEP uuid remap + a save/reload
  with no duplicate uuids, based_on family) + `verify_phase_dialogs.py` check 8
  (export/import through the buttons).

#### Audit notes: .phs deep-remap (2026-07-20)

Reviewed `load_phs`'s string-replace deep-remap against the real default-phase
library and fixture `.mud` phases. **Verdict: correct and robust; one benign
minor gap.**

- **The string replace catches the schema-buried references** a naive
  field-based remap would miss. Real `.phs` store atom-relation / UCP atom
  references as list ELEMENTS under keys like `"prop":[...]` and `"atom2":[...]`
  (not `"key":"uuid"`), so a plain `replace(old, new)` over the JSON is exactly
  what reaches them - confirmed on `Illite.phs` / `Chlorite.phs`.
- **No false positives on real data.** Every 32-hex string is a quoted uuid:
  `display_color` is 6-hex (`#559911`), `*_ref_info` are numbers, and there are
  NO 33+ hex runs (so no partial-match of a longer hash). The core assumption
  ("any 32-lowercase-hex string is a uuid") holds for this format. (It would
  only bite if a future format embedded a 32-hex non-uuid value that ALSO equals
  a live project uuid - astronomically unlikely.)
- **uuid1 (old app) + uuid4 (new) both work** - both are 32 lowercase hex, both
  matched; the fresh replacements are uuid4.
- **Fresh uuids are guarded** against the project, the whole import, and each
  other (`while new in taken`), so a replacement can never alias a kept import
  uuid; and the chained replaces are order-independent (no `new` is any `old`,
  all olds are distinct 32-char strings).
- **based_on family under collision** re-binds correctly: re-importing a family
  remaps both members consistently, so the child's `based_on` points at the
  RE-imported parent, and the two imports are uuid-disjoint (verified).
- **MINOR gap (benign):** `_project_uuids` does not include a RawPatternPhase's
  embedded `PyXRDLine` uuid, so re-importing a raw phase leaves a duplicate
  line uuid. Harmless - nothing resolves lines by uuid (save/reload of two such
  phases works) - but for strict uniqueness a later pass could add raw-phase
  line uuids to `_project_uuids`. Not worth a change now.
- Atom-type refs are unaffected: import `atom_type_uuid`s are only remapped if
  they collide with a project phase/component/atom uuid (cross-category, never),
  and atoms resolve by NAME regardless.

### Component import / export (.cmp)

`file_parsers/cmp_components.py` (`save_cmp` / `load_cmp`) + the two buttons in
the component editor (`component_widget.py`, `btn_import_component` /
`btn_export_component` beside the component selector). A `.cmp` is a ZIP of
`<uuid>` -> a Component JSON (same serialisation as a `.mud` `components` entry);
it lets a clay-layer component (cell + atoms + relations) be reused in another
phase. Ported from old mudlab's `Component.save_components` / `load_components`.

- **Import is a REPLACE, not an add** (matching the old app): the imported
  component takes the selected component's place, so the phase's component COUNT
  - and hence its stacking model - is unchanged. A single-component `.cmp` is
  required (the editor's selector picks one component); a mismatch shows a
  message. `component_widget.bind_components` now keeps the phase's ACTUAL
  component list (not a copy) so `self._components[idx] = new` replaces it in
  place; a re-import with identical data leaves the calculated pattern unchanged
  (verified, max|d|=0).
- **Export** writes each component standalone (linked_with dropped, inherit
  flags cleared) with atom types stamped by NAME, so a `.cmp` resolves against
  whatever atom types the target project holds.
- **uuid policy:** import forces EVERY uuid fresh (component + atoms, internal
  references remapped consistently), so the imported component can never alias
  an existing object. This shares the audited deep-remap helper
  `file_parsers/uuid_remap.py` (`UUID_RE`, `project_uuids`, `remap_uuids`) with
  the `.phs` importer - phase import passes the project's uuids to remap only
  collisions; component import passes the import's own uuids to force all fresh.
- Guard: `tools/verify_cmp_import.py` (12 checks: standalone export, name/cell/
  atom-count round-trip, fresh-uuid non-aliasing, missing-atom-types, and the
  editor export->import replace with G unchanged).

### Add / Remove wiring (Batch P2)

Add and Remove live on `EditPhasesDialog`, not the generic shell (they
need the project + the phase model).

- **Add** (`_on_add_phase`): runs `AddPhaseDialog`; on accept builds the
  phase via `Phase.create_empty(G=..., name="New Phase")` - which creates
  the **G blank components** ("Component 1".."Component G") and the R0
  probabilities, mirroring the old `Phase.__init__` (MudLab2's plain
  `__init__` does not, since it is also the base for `from_dict`). Then
  `project.add_phase`, append the row, select it (so the editor binds it
  and the based_on / linked_with candidate combos, rebuilt on selection,
  pick it up).
- **Remove** (`_on_remove_phase`): confirms first via
  `deletion_confirm_message(phase, project.phase_dependants(phase))` - when
  other phases depend on this one (based_on it, or a component linked to its
  components) the box NAMES them and says their values are kept (snapshot-on-
  detach bakes them in before severing); otherwise the plain "Deleting a phase
  is irreversible!". Then `project.remove_phase` (which cascades every reference
  AND snapshots the dependants - see the phase-CRUD model notes + dev-notes.md),
  then `project.calculate()` because a mixture that used the phase now has an
  empty cell and its stored calculated pattern still carries the removed phase's
  contribution until a recompute. Reselects a neighbour.
- **Explicit detach** (phase editor `_on_based_on_changed`, component editor
  `_on_linked_with_changed`): picking "(none)" while `has_inherited_values()`
  offers `inheritance_detach.ask_detach_choice` (keep / revert / cancel) - "keep"
  calls `snapshot_inherited()` before `set_based_on(None)` / `set_linked_with(None)`
  so nothing changes; "revert" is the old fall-back-to-own; "cancel" restores the
  combo. Guarded by `verify_remove_phase_dialog.py` + `verify_detach_choice.py`.
- **Three views must stay in lock-step**: `project.phases`, the dialog's
  `self._phases` snapshot, and the tree rows. `_phases[index.row()]` is
  how a selection resolves to a phase, so any drift binds the editor to
  the wrong phase. The handlers mutate all three together. Guard:
  `tools/verify_phase_dialogs.py`.
- The dialog is rebuilt per open (`main_window._show_edit_phases`), so the
  snapshot starts fresh each time; the in-session sync only has to hold
  while one dialog is open.

### The default-phase catalog is still a placeholder

`cmb_default_phases` holds demo strings that map to nothing. The old app
filled it from the default phases directory (.phs files) and could
regenerate them (`btn_generate_phases`, spinner + progress bar) - port
with `generate_default_phases.py`. Until then `rdb_default_phase` is
disabled, so the placeholder is never reachable.

## Goniometer component: goniometer.ui

`mudlab/goniometer_widget.py` (`GoniometerWidget`), old
`goniometer/glade/goniometer.glade` InlineGoniometerView. Inserted into
the Edit Specimen Goniometer tab (`goniometerLayout`); reuse it anywhere
a goniometer setup is edited. Bound live to the specimen's `Goniometer`
model (`bind_goniometer`) - edits write to the model, which feeds the
intensity-correction calculations (batch 2 below). `bind_goniometer(None)`
disables the whole tab, so **every specimen must own a goniometer**:
`Specimen.__init__` now defaults `self.goniometer = Goniometer()` (CuKα
Bragg-Brentano; a `.mud` load overwrites it). Before this, an imported / added
specimen had `goniometer = None` and the tab was greyed out (2026-08-05 fix;
`verify_specimen_goniometer`). Import now **applies the file's Kα1 wavelength**
to that default goniometer when the format provides it (`.xrdml`, 2026-08-05);
`.xrdml`/`.raw` slit/radius geometry is still NOT applied (only reported in the
Source box - a follow-up). The calc uses the experimental 2θ grid, so beyond the
wavelength the geometry defaults are harmless. See the import Source-box note
(`build_source_string`) under the pattern-import dispatcher above.

- Four groups with old ids kept: General (`gonio_radius_spb`,
  `gonio_min_2theta_spb` 0-160, `gonio_max_2theta_spb` 0-100,
  `steps_spn_btn1` 1-5000), Sample (`sample_length_spb`,
  `sample_surf_density_spb`, `gonio_has_absorption_correction` +
  `absorption_spb` [cm²/g]), Primary beam (`btn_edit_wld` -> the
  wavelength-distribution editor, `wavelength_distribution_dialog.py`;
  `gonio_lambda_lbl` shows the dominant wavelength, `gonio_divergence_mode`,
  `gonio_div_value_spb`, `gonio_has_soller1` + `gonio_soller1_spb`),
  Secondary beam (`gonio_has_soller2` + `gonio_soller2_spb`,
  `gonio_mcr2t_spb` monochromator 2θ).
- `DIVERGENCE_MODES = ("AUTOMATIC", "FIXED")` maps combo indexes to the
  old model values; on AUTOMATIC the value spin suffix switches from °
  (slit angle) to cm (irradiated length), as the old controller did.
- Soller/absorption checkboxes enable their paired spins.
- Bottom row (old ids): stored goniometer setups. `cmb_import_gonio`
  ("Load setup") is populated by `_populate_setups` from the bundled
  presets (`file_parsers/gon_file.DEFAULT_GONIO_DIR`, 12 `.gon`) + the
  user setups dir (`_user_gonio_dir`, QStandardPaths AppData); its
  `activated` signal applies the picked `.gon` via `Goniometer.apply_setup`
  (full reset, keeps uuid; legacy single-`lambda` tolerated) after a
  confirm, then re-picks the placeholder so the same setup can re-fire.
  `btn_export_gonio` ("Store setup") writes `to_dict()` JSON via
  `gon_file.save_gon` and refreshes the combo. `lbl_applied_gonio` shows
  the applied/stored name (transient; not persisted to the specimen).
  Guard: `tools/verify_goniometer_setup.py`.

## Wavelength-distribution (emission spectrum) editor: wavelength_distribution.ui

`mudlab/wavelength_distribution_dialog.py` (`WavelengthDistributionDialog`),
old `goniometer/glade/wavelength_distribution.glade` +
`WavelengthDistributionController`. Modal; opened by the goniometer
component's `btn_edit_wld`. An editable (Wavelength nm, Fraction) table
(`tv_wld`, a `QStandardItemModel`) with `btn_add` / `btn_del` and
`btn_import` / `btn_export` for `.wld` files (parser:
`file_parsers/wld_file.py`; 5 presets bundled under
`data/default wavelength distributions/`, the import default folder).
Edits are LIVE: every cell edit / add / remove / import pushes the whole
list to `Goniometer.set_wavelength_distribution`, which pops the verbatim
raw string (so the edit is re-encoded on save; untouched goniometers still
round-trip byte-identically) and emits `data_changed`. Invalid cell text
reverts. The Goniometer tab's `gonio_lambda_lbl` refreshes to the dominant
(highest-fraction) wavelength. Guard: `tools/verify_wavelength_distribution.py`.

## CSV import options + common CSV I/O: csv_import.ui

`file_parsers/csv_io.py` is the single place the app reads/writes two-column
`(x, y)` text: `read_xy(path, options=None, min_rows=2)` (tolerant auto-detect
when `options` is None/all-default, else explicit `CsvOptions`
delimiter/decimal/has_header), `write_xy(...)`, plus `sniff` / `preview` for the
dialog. `xy_parser` (`parse_xy`/`parse_xy_lines`/`save_xy`) and `wld_file`
(`.wld`, `min_rows=1`) are thin facades over it; `xrd_export.save_pattern` and
`xrd_import.parse_pattern(path, options=None)` use it too. One-directional
imports (facades → csv_io) avoid a cycle.

`mudlab/csv_import_dialog.py` (`CsvImportDialog`, old
`generic/views/glade/csv_import.glade`): separator + decimal-sign combos, a
first-row-headers checkbox, and a live `tv_preview` (header/non-numeric rows in
italics), pre-filled from `csv_io.sniff`. `import_pattern(parent, path=None, ...)`
is the shared entry point: it picks a file (unless given one), shows the options
dialog for text formats (`xrd_import.uses_csv_options` = not a vendor format),
parses, and shows a QMessageBox on error - returning `(x, y)` or None. Wired
into the experimental-pattern import (`edit_specimen_dialog`), the raw-pattern
phase import (`edit_raw_pattern_phase_widget`), and the background-pattern
import (`line_dialogs`, which picks the file itself for the path label). Bulk
Import Specimens (`main_window`) stays on auto-detect (no per-file dialog).
Guard: `tools/verify_csv_import.py`.

## Specimen-operation dialogs (lines + trim/statistics/save-size)

Nine small modal dialogs. Logic: `mudlab/line_dialogs.py`
(RemoveBackground, SmoothData, ShiftPattern, AddNoise, StripPeak,
PeakProperties) and `mudlab/specimen_dialogs.py` (TrimData, Statistics,
SaveGraphSize). Old sources: `generic/views/glade/lines/*.glade` and
`specimen/glade/{trim_dialog,statistics,save_graph_size}.glade`. The
main-window actions open them (`actionRemoveBackground`,
`actionSmoothData`, `actionShiftPattern`, `actionAddNoise`,
`actionStripPeak`, `actionPeakProperties`, `actionTrimData`,
`actionSaveGraph`).

**IMPLEMENTED (Batches D1/D2).** Numerics:
`mudlab/calculations/pattern_ops.py` (pure functions, ported verbatim from
the old `generic/models/lines/experimental_line.py`); mutation + signal:
the `Specimen` methods (`remove_background`, `smooth_data`, `add_noise`,
`detect_shift`/`apply_shift`, `compute_strip_pattern`/`apply_strip`,
`compute_peak_properties`, `trim`). Each emits `data_changed` once, which
refreshes the plot and invalidates the statistics cache. Harness:
`tools/verify_pattern_ops.py`.

Every dialog derives from `_SpecimenDialog`, which holds the bound
specimen and **refuses to accept when nothing is bound** (so a mis-wired
action cannot silently no-op). The old app opened these from the Edit
Specimen controller, so a specimen was always present; here they live on
the main-window menu, so `_update_data_op_actions` greys them out unless
exactly one specimen with data is selected.

**Live preview overlay.** `_SpecimenDialog` draws a live preview of the
pending operation on the main plot while open: `showEvent` and every
parameter-change signal call `_update_preview`, which asks the subclass
`_compute_preview()` for `(x, y, show_original)` and forwards it to
`main_window.set_pattern_preview(specimen, x, y, show_original)`; `reject`
and a successful `_on_accept` call `clear_pattern_preview`. The result is
computed NON-destructively by the `Specimen.preview_*` methods (same
`pattern_ops` as the mutating ops, so the overlay matches what OK applies),
and `PatternPlot.set_preview` draws it in `PREVIEW_COLOR` over the original
(hiding the original only when `show_original` is False - Smooth's
checkbox), preserving the user's zoom. Add Noise / Strip previews are
representative (random). Peak Properties is a measurement and previews
nothing. Guards: `verify_pattern_preview` + `verify_data_op_preview`.

- **Remove Background** (`background.ui`): `bg_type` Linear/Pattern
  switches `bg_view_stack` (old swapped tables into bg_view_container).
  Linear: `bg_position` (pre-filled from `find_bg_position` = min(y), the
  old auto-suggest). Pattern: `bg_pattern_file` + `btn_browse_bg`,
  `bg_scale`, `bg_offset`; the chosen file is parsed with `parse_xy` and
  **interpolated onto the specimen's x-grid** (`interp1d`,
  `fill_value=0` outside its range) exactly as the old
  `line_controllers.py` did - a background measured on its own grid does
  not line up otherwise.
- **Smooth Data** (`smoothing.ui`): `smooth_type` (Moving Triangle,
  Savitzky-Golay, Gaussian, Moving Average, Smoothing Spline, Butterworth
  - `SMOOTH_TYPES` map), `spin_degree` (re-filled per type from
  `SMOOTH_DEFAULT_DEGREES`, old `setup_smooth_variables`). Each type
  reads the degree differently (window half-width / sigma / spline factor).
  `smooth_show_original` keeps the un-smoothed original visible under the
  live preview (drives `show_original` on the overlay; see below).
- **Shift Pattern** (`shifting.ui`): `shift_position` reference list
  (Quartz/Silicon/Zincite/Corundum/Goethite/Gibbsite/Manual;
  `SHIFT_POSITIONS` = d-spacings in nm), `spin_shift_value`.
  - **`spin_shift_value` is a °2θ OFFSET, not a d-spacing.** The `.ui`
    originally suffixed it " nm" and the placeholder pre-filled it with
    the reference d-spacing - both wrong, fixed in D2. Selecting a
    reference **auto-detects** the offset from the data
    (`Specimen.detect_shift`: the strongest point within ±0.5° of the
    reference's theoretical position); Manual unlocks the spin and
    **resets it to 0.0** (old `setup_shift_variables`).
  - A reference outside the scanned range detects `0.0` - it has nothing
    to measure against (old try/except). Zincite/Corundum do this on the
    308 fixture, which only reaches 35°2θ. A detected `0.0` on an
    *in-range* reference is also legitimate: `308 AD`'s quartz line sits
    at its theoretical position to 8e-6°, i.e. already shift-corrected.
    **Do not read a zero here as a broken detector.**
  - `PATTERN_SHIFT_TYPE` (pattern_ops) is `"Displacement"`, the old
    default: it models the sample sitting off the focusing circle, so the
    correction shrinks as 2θ grows. `"Linear"` subtracts a constant and
    (only then) moves the markers with the data, as the old app did.
  - **Reference line (2026-08-05, was missing).** The old app drew a fixed
    dotted vertical at the reference reflection's target 2θ; MudLab2 hadn't
    ported it (the dialog opened but no line showed). Now `ShiftPatternDialog`
    computes the target 2θ (`get_2t_from_nm(SHIFT_POSITIONS[i], specimen.
    wavelength)`) and drives `main_window.set_shift_reference` /
    `clear_shift_reference` → `PatternPlot` draws a dotted vertical in
    `SHIFT_REFERENCE_COLOR` (teal). It updates on `showEvent` + reference-combo
    change, is FIXED against the shift value (the data moves toward it), clears
    in Manual mode and on `accept`/`reject`. Harness: `verify_shift_reference`.
- **Add Noise** (`add_noise.ui`): `spin_fraction` 0-1. Noise sigma is
  `fraction * max(y)` - scaled to the strongest reflection, not per-point.
- **Strip Peak** (`strip_peak.ui`): `strip_startx`/`strip_endx` + `keep_percent`
  (fractional %, min 0) + `noise_level`. One unified op via
  `compute_reduce_pattern` -> `bg_line + keep*(y-bg_line) [+ noise]` as a
  StripPattern (endpoints stay on the line, so no background notch; `apply_strip`
  handles it unchanged). **Keep 0 % = the classic strip** (flatten onto the
  line), 100 % = unchanged; the separate "straight line" mode was dropped as
  redundant. `noise_level` is retained and auto-estimated on a range change (old
  `compute_strip_pattern` estimate) - but once the user edits it by hand the value
  STICKS (`_noise_user_set`, set by `_on_noise_changed`; auto-estimates route
  through `_set_noise` guarded by `_setting_noise`), so nudging the range never
  clobbers a chosen value. Keep 0 % + noise reproduces the old strip exactly.
  verify_strip_reduce.py.
- **Peak Properties** (`peak_properties.ui`): start/end; area/FWHM recompute
  **live** on every position change. Read-only - it never touches the pattern,
  hence no OK button.
- **Range selection (2026-08-16, replaced the Sample buttons).** Strip Peak and
  Peak Properties used to pick each endpoint with an eye-dropper
  `cmd_sample_start`/`cmd_sample_end` button (one plot click each). Both are gone;
  the range is now swept by **dragging across the pattern**, reusing the
  crosshair drag-highlight. `_RangeSelectMixin` (line_dialogs) arms
  `main_window.arm_range_pick` on `showEvent`/window-activation and disarms on
  `accept`/`reject`; a left-drag drives `PatternPlot.set_range_select_enabled` →
  the existing `_start/_update/_end_drag_highlight` and, on release,
  `on_range_select(plot, x0, x1)` fills BOTH spinboxes (ascending). The boxes stay
  editable. Range-select is independent of the Crosshair toggle. Harness:
  `verify_range_select`.
- **Trim Data** (`trim_dialog.ui`): irreversibility warning, `cmb_scope`
  (This specimen only / All loaded specimens -> `TRIM_SCOPES`),
  `spin_min_2theta`/`spin_max_2theta` 0-180. Switching to "all" pre-fills
  the range **shared** by every specimen (widest lower / narrowest upper
  bound), since a wider range would fail on some. `lbl_removal_warning`
  names the markers / exclusion ranges that will also go. Trim drops
  exclusion ranges that *straddle* a new boundary rather than clamping
  them (a clamped range would silently change meaning).

### Data operations: notes

- **All destructive, no undo** - same as the old app; nothing is written
  to the .mud until the user saves. Deliberately no extra confirmation
  the old app never had.
- **No golden reference exists** for these ops: the old app applies them
  destructively and stores only the result, so a processed pattern
  carries no record of what produced it. `verify_pattern_ops.py` leans on
  (1) the **live old code** - old `math_tools.py` is pure numpy, so it is
  loaded *by path* (the old tree's numpy is a MinGW build that will not
  import here) and its `smooth`/`add_noise` are diffed point-for-point;
  (2) **analytic ground truth** - Gaussian area/FWHM in closed form, the
  displacement formula re-derived; (3) invariants on fixture data. The
  harness is mutation-tested; see the commit for the four mutations.
- Old quirk preserved in `compute_strip_pattern`: **both** endpoint noise
  ratios divide by `avg_starty` (not each by its own endpoint). Looks
  like an old-app bug; kept for parity.

### Audit notes: data operations (Batch D, 2026-07-16)

Audited D1+D2 after the fact. Four defects found; all fixed and guarded.

**1. Trim was lost on save, and reported a FAKE PERFECT FIT.** (worst one)

`_specimen_to_dict` keeps the calculated line **verbatim** from
`raw_properties`, because its rows carry extra per-phase intensity columns
(6 in the 308 fixture) that the model does not keep - `_parse_pattern_data`
takes only the first two, so re-encoding from `_calc_x/_calc_y` would
silently drop the per-phase curves. Its comment said *"MudLab2 never
modifies it yet"*, which **D1's trim made false**.

Result: trim clipped both patterns in memory, but only the experimental one
was saved. A reloaded project then paired a trimmed experimental pattern
(1163 pts) with a full-range calculated one (2323 pts) - and
`SpecimenStatistics.has_data` refuses to compute on a size mismatch, so
every R-factor came back **0.00**. Rp 0 reads as a *perfect fit*, not as an
error. Silent wrong science, which is the worst failure mode this app has.

Fix: `Specimen._trim_raw_calculated` clips the raw rows (preserving all
columns) so raw and model stay in step. **Trim is the only operation that
touches the calculated pattern - any new one must do the same**; the
saver's comment now says so. Guarded by `check_trim_persistence`
(mutation-tested: reverting the fix fails 8 checks, printing the fake
`Rp 0.000` explicitly).

**2. Dialogs closed on a refusal**, i.e. looked exactly like success - the
very failure this batch removes. `_on_accept` called `accept()`
unconditionally, so `_apply` implementations that warned and returned early
(background-with-no-file, strip-with-no-range) still closed the dialog.
`_apply` now returns bool and `_on_accept` only closes on True.

**3. Smoothing crashed on a too-large degree.** `spin_degree` allows up to
600; Moving Triangle and Savitzky-Golay raise ValueError when the window
exceeds the pattern - reachable by trimming hard, then smoothing. The old
app let this escape as a traceback. Caught in `SmoothDataDialog._apply`
(warn + stay open). The numerics are untouched: this is UI robustness, not
an analytics change.

**4. Data ops stayed enabled after New Project.** A project with no
specimens changes no selection, so `selectionChanged` never fired and the
stale enabled state persisted. `_set_project` now calls
`_update_data_op_actions()` explicitly.

Also fixed in the harness itself: the statistics check asserted
`spec.statistics is stats` (object identity), which passes even with a
completely stale cache. It now asserts the **Rp value moves**.

**Sharp edges to know:**

- **`SpecimenStatistics` returns 0.0, not an error, when it cannot
  compute** (no calculated pattern, or an exp/calc size mismatch). For Rp
  that is indistinguishable from a perfect fit. Normally unreachable -
  `calculate_specimen_pattern` computes on the experimental grid, so the
  sizes always match - and defect 1 above was the only way to persist a
  mismatch. If R-factors ever read exactly 0.00, suspect this before
  believing the fit.
- **After Shift, the stored calculated pattern is stale**: `apply_shift`
  moves `_exp_x` but not `_calc_x`, so until the next `calculate()` the
  statistics compare intensities at shifted positions. Same as the old app
  (its `commit_shift` also only touches the experimental data), so this is
  parity, not a regression - but it is a real trap.
- **Markers only follow a Linear shift**, never a Displacement one, because
  the displacement correction is angle-dependent. `PATTERN_SHIFT_TYPE` is
  `"Displacement"`, so in practice markers never move on shift. Old app
  behaves identically.

### Audit notes: data operations x the calculation engine (2026-07-16)

Second, targeted pass. The Batch D verification stops at the specimen
boundary, so this probed the one dimension nothing had exercised: what the
calc engine / mixture / optimizer / refiner do after an op reshapes a
specimen. It was chosen because the batch's worst defect (trim vs the
saver) was of the class *"a distant module's assumption about the specimen
went stale"* - and the saver was not the only module holding one.

**Result: clean.** No code defects. `calculate_specimen_pattern` reads
`exp_x` live, so a trimmed specimen recalculates onto the trimmed grid; the
optimizer and refiner follow. Verified concretely: recalc lands on the
trimmed grid, one specimen's trim leaves its neighbours alone, refinables
still enumerate and still move the residual, `optimize()` does not worsen
it, and the mixture residual equals the mean of the per-specimen
`statistics.Rp` **exactly** (35.3352 both ways on 308 r1). Guarded by
`check_ops_x_calc_engine` (mutation-tested: making the calc ignore the
experimental grid fails 13 checks).

Two **old-app parity traps** confirmed (verified against the old
`commit_shift`; deliberately NOT changed - porting analytics as-is):

- **Exclusion ranges do NOT follow a shift.** The data moves
  (15.0845 -> 14.7845 for a 0.30° shift) but the ranges are absolute 2θ and
  stay put, so a range that masked a peak now masks the wrong region - and
  the refinement optimises against it. The old `commit_shift` never touches
  them either. Users should shift *before* setting exclusion ranges (now in
  the user manual).
- **Markers do not follow a shift in practice**, per the note above. The old
  app is internally inconsistent here and the port reproduces it faithfully:
  `_apply_shift_to_array` shifts linearly when
  `PATTERN_SHIFT_TYPE == "Linear" **or** shift_position == 0` (Manual), but
  the marker-moving branch tests only `PATTERN_SHIFT_TYPE == "Linear"`. So in
  Manual mode the data moves linearly while the markers stay put.

**A harness lesson (my check was wrong, not the code).** The first version
asserted that perturbing *the first refine-flagged* refinable moves the
residual. It failed on `Dh2040A 14Jul26.mud` - whose Illite phase sits at
fraction **0.0**, so its parameters correctly move nothing. The check now
asserts *at least one* refinable is live and prints the count (13/17 there,
21/21 on 308 r1). Assert the invariant that must hold, not one that happens
to hold on the baseline fixture.
- **Statistics** (`statistics.ui`): read-only χ², R², Rp, Rwp, Re, data
  points via `set_statistics(...)`. NOT yet reachable from the UI - the
  old `view_statistics` action lives in the future specimens context
  menu.
- **Save Graph** (`save_graph_size.ui`): old GTK embedded this as an
  expander inside the save dialog; Qt native dialogs cannot embed custom
  widgets, so it runs as a small pre-dialog (presets fill
  `entry_width`/`entry_height`/`entry_dpi`), then the native save dialog
  follows. **Fully wired 2026-08-05** (`MainWindow._save_graph`): the size
  dialog → `QFileDialog.getSaveFileName` (PNG/PDF/SVG, default name from the
  shown specimen or project) → `PatternPlot.save_figure(path, dpi, w/dpi, h/dpi)`
  (port of the old `save_figure`: applies the inch size + dpi, saves with a
  `Bbox` crop, then restores the on-screen size/dpi). Previously the action only
  opened the size dialog and discarded the result — clicking OK did nothing.
  Harness: `tools/verify_save_graph.py`.

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

Exclusion ranges (2theta regions the fit ignores) are fully wired.
`Specimen.exclusion_selector(2theta)` is a boolean mask (all-True with no
ranges; lo/hi swapped so start>end still works). It is applied by the
mixture fit residual (`calculations/mixture.py` `_Problem.residual` masks
observed+calculated), the structural refinement (inherits it via
`optimize_mixture`), the R-factors (`SpecimenStatistics._compute`), and the
plot shading (`plot_controller` draws a faint `axvspan` per range, deduped,
zero-width skipped). The Edit Specimen exclusion tab edits them live
(see edit_specimen.ui below). **Deliberately NOT masked (deferred, "#4"):**
the residual/derivative DIFFERENCE bands (`residual_pattern` /
`derivative_residual`) draw over the FULL 2theta range - so the difference
curve is still visible under the shading inside an excluded region, while the
R-factor numbers exclude it. This is a known, intentional gap (the shading
marks the region); revisit if the mismatch confuses users. Also not yet: the
separate der_exp/der_calc derivative curves (only the derivative residual is
drawn).

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
  find_peaks_dialog.glade): modal; pattern (exp/calc) + algorithm
  (Threshold classic / Prominence scipy) combos, threshold + steps +
  #peaks, and the # peaks-vs-cut-off histogram canvas in `graphLayout`
  with a draggable vertical line. Selected-threshold and #peaks stay
  coupled (forward/reverse interpolation over the histogram). OK runs
  `Specimen.auto_add_peaks` (`calculations/peak_detection.py`:
  peakdetect / scipy_peakdetect + get_best_threshold/prominence),
  creating a Marker per peak labelled with its d-spacing. `min_distance`
  is shown only for the Prominence algorithm. Launch offers to clear
  existing markers first.
- **Match Minerals** (`match_minerals_dialog.py`, `match_minerals.ui`, old
  match_minerals.glade): NON-modal (old view kept it above the main
  window so the plot stays interactive). All-minerals list (real
  `data/mineral_references.csv`, 228 entries) <-> matched list with
  transfer buttons; Auto match scores the references against the target
  markers' peaks (`score_minerals`), Append labels writes the chosen
  abbreviations onto the markers (emits `applied`, host list reloads).
  Button ids follow the old glade: `btn_rtl` = add (minerals -> matches),
  `btn_ltr` = remove. **Mineral-preview overlay:** selecting a row in either
  list (both selectionModels -> `_on_row_selected`) stamps the row's
  `_PEAKS_ROLE` reflections onto `self._last_peaks` and calls
  `Specimen.set_mineral_preview` with `_preview_peaks()` — each reference peak's
  d-spacing (angstrom/10 -> nm) converted to 2theta via `get_2t_from_nm`,
  dropping non-Bragg (`d <= lambda/2`) peaks and (when `chk_use_specimen_range`
  is on) those outside the experimental range. That transient
  `specimen.mineral_preview` [(2theta, rel_intensity)] bubbles via
  `visuals_changed -> project -> _refresh_plots`, and `PatternPlot.draw_pattern`
  draws magenta sticks (`MINERAL_PREVIEW_COLOR`, height = rel/100 * displayed
  peak height). `reject()` clears it. Never serialized. Guard:
  `tools/verify_mineral_preview.py`.

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

**Per-phase curves (2026-07-28).** `display_phases` is now functional. A mixture
recompute (`Mixture.calculate`) captures each phase's scaled contribution and
stores it on the specimen via `set_calculated_pattern(x, y, phase_patterns)` into
the transient `Specimen.phase_patterns` (a `[(phase, curve)]` list, never
serialized). `PatternPlot.draw_pattern` draws one curve per phase in
`phase.display_color` under the total, gated on `display_phases &&
display_calculated && phase_patterns`. Besides the Sep column / Edit Specimen
checkbox, **View ▸ Show phase patterns** (`actionShowPhases`) is a convenience:
`_on_show_phases_toggled` bulk-flips `display_phases` on the shown specimens
(recomputing once when the curves have not been captured yet), and
`_sync_show_phases_action` mirrors the shown specimens' state back onto the
checkmark on every rebuild (read-only, signal-blocked — no loop). `_set_project`
recomputes once at load when a stored project already has phases on, so the
transient curves appear without a manual F5.

**Phase index / mixture legend (2026-08-04).** `PatternPlot._draw_mixture_legend`
(port of the old `plot_mixtures`) draws an upper-right `AnchoredOffsetbox`
(`frameon=False`, zorder 10) indexing every mixture that owns a displayed
specimen (`any(s in mixture.specimens ...)`). Each block is the mixture name,
then one row per phase slot — `"<label>: <fraction*100:>5.1f>"` — with a colour
swatch (`FancyBboxPatch` in an `AuxTransformBox`, `mutation_scale=14`) per
non-empty phase cell across the specimens, filled with that phase's
`display_color` (the same colour its per-phase curve uses; a `getattr` +
`display_calc_color` fallback keeps a colourless phase-like from erroring). It is
**always drawn** (as in the old app, independent of `display_phases`) and simply
shows nothing when no shown specimen is in a mixture. `draw_pattern`'s
`axes.clear()` drops the previous legend, so no remove-old bookkeeping is needed.
Harness: `tools/verify_mixture_legend.py`.

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
  simply the N=1 case. Now drawn: markers, the exclusion-range shading
  (faint full-height axvspan bands), and the 65/35 residual/derivative
  statistics band. Not yet drawn: mixture legends, per-pattern
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
  values) and the Edit Marker `cmd_sample` (fills the marker position,
  which writes to the bound marker and syncs nm).
- Range picking (2026-08-16) reuses the crosshair drag-highlight instead of
  two eye-dropper clicks: `arm_range_pick(callback, hint)` enables
  `PatternPlot.set_range_select_enabled` on every plot (crosshair cursor,
  highlight on left-drag independent of the Crosshair toggle) and, on drag
  release, calls `callback(plot, x0, x1)` (ascending 2θ). Unlike the one-shot
  position pick it STAYS armed until `disarm_range_pick`. Users: the MODELESS
  Strip Peak / Peak Properties dialogs (`_RangeSelectMixin`), which arm on
  show/activation, fill their start/end spinboxes from the drag, and disarm on
  close. The plot stays clickable throughout (zoom/scroll still work).
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
| `actionSaveGraph` | `save_graph` | **Wired (2026-08-05):** `MainWindow._save_graph` → size dialog → file picker → `PatternPlot.save_figure`. See the Save Graph note above. (Was a no-op: opened the size dialog then discarded it.) |
| `actionRemoveBackground` | `remove_bg` | single specimen: `specimen.remove_background()`; multiple: `project.remove_backgrounds(...)` |
| `actionSmoothData` | `smooth_data` | single-specimen smoothing dialog |
| `actionShiftPattern` | `shift_data` | single-specimen shift dialog |
| `actionShowPlotToolbar` | `show_plot_toolbar` (toggle) | show/hide nav toolbar. *Connected.* |
| `actionAddSpecimen` | `add_specimen` | `project.add_specimen()` |
| `actionImportSpecimens` | `import_specimens` | `project.import_multiple_specimen()` |
| `actionConvertToFixed` | `convert_to_fixed` | **Wired (2026-08-04):** `_convert_slit(to_ads=False)` -> confirm -> `Specimen.convert_to_fixed()` (experimental y / sin θ). A single-specimen data op (in `_data_op_actions`), not the old multi-specimen loop. |
| `actionConvertToADS` | `convert_to_ads` | **Wired (2026-08-04):** `_convert_slit(to_ads=True)` -> confirm -> `Specimen.convert_to_ads()` (experimental y × sin θ). See below. |
| `actionEditPhases` | `edit_phases` | present phases window |
| `actionEditAtomTypes` | `edit_atom_types` | present atom types window |
| `actionEditMixtures` | `edit_mixtures` | present mixtures window |
| `actionManual` | - | `webbrowser.open(settings.MANUAL_URL)` |
| `actionAbout` | `_show_about` -> `AboutDialog(self).exec()` | branded About dialog (`about.ui`, `about_dialog.py`): `resources.logo_pixmap` + name/version (`mudlab.__version__`)/tagline + runtime lib versions. App/window icon via `resources.app_icon` (set in `create_app` + `MainWindow.__init__`); `.exe` icon = `data/icons/mudlab.ico` (MudLab.spec). Guard: `verify_about.py`. |
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
  ConvertToADS (+ Remove Specimen, context-menu-only). *NOTE: MudLab2 made all
  the data ops single-specimen (`_data_op_actions` / `_update_data_op_actions`,
  enabled iff exactly one specimen with data is selected), so ConvertToFixed /
  ConvertToADS are greyed with them rather than following the old multi-specimen
  rule.*

**Fixed <-> ADS slit conversion (2026-08-04).** `Convert to Fixed Slit` /
`Convert to ADS` rescale the selected specimen's experimental pattern
between fixed and automatic (ADS) divergence-slit geometry. An ADS slit opens
with θ to hold the irradiated length constant, collecting ~sin θ the intensity a
fixed slit would, so **fixed→ADS = × sin θ**, **ADS→fixed = ÷ sin θ** (the factor
is the existing `get_fixed_to_ads_correction_range` = sin θ; ÷ leaves θ=0 points
untouched). Numerics: `pattern_ops.convert_slit(x, y, to_ads)`; model:
`Specimen.convert_to_fixed/ads` (mutate + `data_changed`); UI:
`MainWindow._convert_slit` (a `QMessageBox` confirmation replaces the OK/Cancel a
dialog would give this parameterless op, then `data_changed` → plot refresh +
dirty). It rescales the experimental data only — it does **not** flip the
goniometer's divergence mode (faithful to the old app; the user sets the mode).
Because of that, and because a goniometer edit does not auto-recompute (the
`gonio.data_changed` no-listener gap), the confirmation **reminds** the user to
set Goniometer → Divergence mode to the matching value (Automatic for ADS, Fixed
for fixed) and press F5. Harnesses: `tools/verify_convert_slit.py` (transform +
model), `tools/verify_convert_slit_ui.py` (menu wiring + the reminder text).

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
- Window icons + about logo: the old `mudlab/application/icons/` set
  (mudlab.ico, mudlab.png, 16-128 px PNGs) is now bundled under
  `src/mudlab/data/icons/` and served by `mudlab/resources.py`
  (`app_icon()` builds a multi-size QIcon, `logo_pixmap()` the About logo).
  Applied in `create_app` (`app.setWindowIcon`) + `MainWindow.__init__`; the
  frozen `.exe` icon is `data/icons/mudlab.ico` (MudLab.spec).

## Behaviors to keep in mind when wiring

- Confirm-discard-unsaved-changes guard before Quit / New / Open
  (`model.check_for_changes()`).
- Main window maximizes on startup (unless DEBUG in the old app). **DONE
  2026-08-05:** `__main__.main` calls `window.showMaximized()` (was `show()`,
  which left the `.ui`'s fixed 1280×800 default — not full width on wider
  screens); the normal size stays the restore geometry.
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
