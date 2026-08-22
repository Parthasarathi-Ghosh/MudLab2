# GUI port checklist: dialogs & windows

Status of every window/dialog/component being recreated from the GTK
MudLab (`C:\GitHub\MudLab`, glade files under `...\site-packages\mudlab\`).

**Keep this file current: update it whenever a component is added,
completed, or descoped.** Wiring details live in [WIRING.md](WIRING.md).

Legend: **done** = .ui + logic exist and are wired for GUI trial;
**partial** = done but contains placeholder slots for missing
sub-components.

Plot interactions (2026-07-08): the old MainPlotController is ported as
PatternPlot (plot_controller.py) - scroll/Ctrl+scroll/Shift+scroll
zoom-pan, arrow-key pan, right-click reset, crosshair + drag Δ2θ/Δd
measurement, the live 2θ/d/Ie/Ic status readout, a reusable eye-dropper
position pick (Select Point + the marker/strip-peak/peak-property Sample
buttons), and marker double-click selection (opens Edit Markers).

Model status (2026-07-08): Project + Specimen + Marker Qt-signal models
exist (mudlab/models/); the specimens dock, plot stack, window title,
Edit Project / Edit Specimen / Edit Markers dialogs are live against
them, Import Specimens loads real text XY/CSV patterns, and markers load/
draw/edit/save for real. Project New/Open/Save/Save As work with the old
.mud format (data-preserving round-trip incl. phases/mixtures/atom types/
goniometers). Atom types, goniometer, (Edit Mixtures, 2026-07-10) the
mixture fraction/scale/background matrix, and (Edit Phases, 2026-07-10)
the phase name/sigma*/CSDS-mean are live against real models; the phase
probabilities and components tabs remain to wire.

Editor wiring (2026-07-10, batches): the calc-engine models are being
bound to their editors so parameters become editable with a live recalc.
- [x] Batch 1: Edit Mixtures - fractions / scales / background shifts are
  editable and bound to the Mixture model; every edit recomputes the
  pattern and redraws (the F5 path). Mixtures now save from the model
  (to_dict passthrough keeps masks / refine options / auto flags / uuid).
  Phase-cell reassignment is wired (2026-07-21: per-cell combo ->
  Mixture.set_phase_at, invalid phases greyed via Phase.is_valid; harness
  tools/verify_mixture_assign.py), and so is structural add/remove (Batch 2,
  2026-07-21: Add phase/specimen/both buttons + header context menus for
  rename/remove/assign; add_phase_slot/del_phase_slot/add_specimen_slot/
  del_specimen_slot/set_specimen_at/set_phase_label; harness
  tools/verify_mixture_structure.py). The Optimize button + auto-* flags were
  wired later (see the L-BFGS-B optimizer entry below), and the full Refine
  window is deferred.
- [x] Batch 2: Edit Phases CSDS mean + sigma* - the phase name, sigma*
  orientation factor and CSDS mean are editable and bound to the Phase /
  DritsCSDSDistribution models; the CSDS component (csds.ui + csds_widget.py,
  mean spinbox + live log-normal histogram + derived range) fills the CSDS
  tab. Every edit recomputes all mixtures and redraws. Phases now save from
  the model (Phase.to_dict passthrough keeps components / probabilities /
  ref_info / display_color / based_on / inherit flags / uuid; non-Phase
  entries stay verbatim, matched by uuid). Phase inheritance, display colour,
  the inherit flags, and Add/Remove phase are disabled - later batches.
- [x] Batch 3: Edit Phases probabilities (F params -> W/P) - the R0 (G-1)
  independent variables Fi = Wi/sum(Wi..Wg) are editable spinboxes bound to
  the R0Probability model, with the derived weight fractions W and junction
  matrix P shown read-only (probabilities.ui + probabilities_widget.py, the
  G-1 inputs + GxG tables built dynamically per phase). The tab only shows
  for G>=2 (removed for single-component phases, like the old app). Editing
  an F re-derives W/P and recomputes the pattern; F params save via
  Phase.to_dict. Verified: F1 0.8->0.6 gives W=[0.6,0.4], pattern moves,
  round-trips; G=1 phases hide the tab; harness 5/5.
- [x] Batch 4a: Edit Phases component scalars - the component editor
  (edit_component.ui + component_widget.py) with a component selector and
  editable c-axis scalars (name, d001/cell length c, default_c, delta_c)
  bound to the Component model; derived cell a/b, volume and charge balance
  shown read-only. Editing recomputes the structure factor + pattern live;
  components save via Component.to_dict (atoms / ucp / relations / uuid kept
  verbatim). Verified: d001 edit shifts the peak, the G=2 IS phase selector
  switches Illite<->Di-Smectite, edits round-trip, unedited stays JSON-equal.
- [x] Batch 4b: Edit Phases component atom lists - the layer + interlayer
  atom tables (atom_list.ui + atom_list_widget.py): editable name / Def. Z /
  # (pn) + an Element combo drawn from the project atom types, read-only
  Calc. Z, and Add/Remove. Editing recomputes the structure factor and
  refreshes weight/charge + the pattern. Atom.to_dict + Component.to_dict now
  serialize the atoms (uuid/stretch_z/ref_info kept verbatim). Verified: pn +
  element edits move charge and pattern, add/remove update the model, edits
  round-trip, unedited stays JSON-equal, harness 5/5.

Calculation engine (2026-07-08): the fit-statistics groundwork is ported
(calculations/statistics.py + math_tools.smooth; SpecimenStatistics via
Specimen.statistics) - real Rp/Rwp/Re/R²/GoF drive the Statistics dialog,
the GoF-in-label option, and the 65/35 residual difference band on the
plot.

Pattern-calculation engine (bottom-up batches - the biggest analytics
port, produces the calculated pattern from scratch):
- [x] Batch 1: atomic scattering factors - calculations/atoms.py
  (get_atomic_scattering_factor/get_structure_factor), AtomType model
  (models/atom_type.py) loaded from the .mud, Edit Atom Types dialog on
  real data. Verified: O->8, Fe->26 electrons at s=0; round-trip identical.
- [x] Batch 2: goniometer model + intensity corrections - Goniometer
  model (models/goniometer.py) loaded/saved per specimen (round-trip
  identical; wavelength_distribution string preserved verbatim), the LP
  factor + Soller S/T terms + machine correction range (auto-divergence /
  absorption / sample-length) in calculations/goniometer.py, and the Edit
  Specimen Goniometer tab bound to the real model. Specimen.wavelength now
  comes from the model. Verified LP factor falls off with angle; get_S
  matches the formula.
- [x] Batch 3: component structure factor - calculations/components.py
  (get_factors: sums atom structure factors over layer + interlayer atoms,
  recalculating interlayer z from the d-spacing z_factor, plus the phase
  term). Atom + Component models (models/component.py) load from the .mud
  and resolve atom references by uuid (project.atom_type_uuid_map). Calc
  groundwork only - components saved verbatim at the time; the component
  editor is wired later (see the editor-wiring batches). Verified against the
  Illite component: 11 atoms resolve, |SF| falls off with angle, intensity
  is finite/non-negative.
- [x] Batch 4: CSDS distribution + stacking probabilities - the Drits
  log-normal CSDS (calculations/csds.py + models/csds.py; average stored,
  Drits constants fixed, min/max derived) and the R0 (independent)
  stacking model (models/probabilities.py: (G-1) F params -> g×g W
  diagonal + P transition matrices). Only R0 is ported (all samples are
  R0G1/R0G2); R1-R3 Markovian models come when a project needs them. Calc
  groundwork - CSDS/probabilities editors wire with the phase-editor port.
  Verified: CSDS sums to 1 with a sensible mean; mixed-layer IS phases
  give W=[0.8, 0.2] (80/20 illite-smectite) with valid stochastic P.
- [x] Batch 5: phase intensity (recursive stacking) - calculations/phases.py
  (get_intensity: folds component structure factors + CSDS distribution +
  W/P stacking matrices into a phase's diffracted intensity via the Drits
  recursive stacking summation, then applies the LP factor) and the calc
  Phase model (models/phase.py: G/components/CSDS/probabilities/sigma_star,
  loaded from the .mud, saved verbatim until the phase editor is wired).
  math_tools.mmult + Component volume/weight + R0Probability.valid added.
  Verified against both sample projects: illite 10.1 A, kaolinite 7.2 A,
  chlorite 7.1 A, and the mixed-layer / smectite phases reproduce the
  AD -> EG -> 350C sequence (15 A -> 17 A -> 10 A) exactly.
- [x] Batch 6: mixture -> specimen calculated pattern + Calculate action -
  calculations/specimen.py (calculate_phase_intensities: per-phase
  corrected + wavelength-distributed intensities; calculate_scaled_
  intensities: fractions x scale + bg-shift -> total) and the Mixture model
  (models/mixture.py: the specimen x phase-slot grid, loaded from the .mud,
  saved verbatim). Project.calculate() drives all mixtures; the F5 "Refresh
  Graph" action recomputes and redraws the red calculated curve. Verified
  END-TO-END against the OLD app's stored calculated patterns: 5/6 sample
  specimens match to floating-point (RMS ~1e-7, corr 1.000000), the 6th to
  0.2% - the full chain atoms -> SF -> CSDS -> stacking -> phase -> mixture
  reproduces the GTK reference.
- [x] exclusion ranges (2theta regions the fit ignores) - DONE, all three
  sub-batches. Model: Specimen.exclusion_ranges + set_exclusion_ranges (emits
  data_changed) + exclusion_selector(2theta) (boolean mask; all-True with no
  ranges; parsed from / saved to the .mud JSON string). HONOURED by: the
  mixture fit residual (calculations/mixture.py _Problem.residual masks
  observed+calculated via ctx.selected), the structural refinement (inherits
  it through optimize_mixture), the R-factors (SpecimenStatistics._compute
  masks exp+calc), and the plot shading (plot_controller axvspan per range,
  deduped, zero-width skipped). NOT honoured (by design): the calculated
  pattern itself (exclusion only changes the fit metric, not the diffractogram)
  and - deliberately deferred (#4) - the residual/derivative DIFFERENCE bands
  (statistics.residual_pattern / derivative_residual draw over the FULL range;
  the shading marks what is excluded). Edge cases (verified): multiple ranges
  union cleanly (a point in ANY range is out, no double-count); start>end is
  normalised by a lo/hi swap in the selector AND the shading (the model stores
  what you typed); start==end and out-of-data ranges exclude ~0 points (safe
  no-op); delete restores those points. Editor: the Edit Specimen exclusion
  tab (edit_specimen_dialog.py) - add/delete/edit rows commit to
  set_exclusion_ranges (malformed rows skipped); import/export disabled.
- [x] mixture fraction/scale/bg-shift refinement (L-BFGS-B optimizer) -
  DONE. Core: calculations/mixture.py (masks from fractions_mask + auto_scales/
  auto_bg, per-specimen phase-intensity cache, mean-Rp objective, L-BFGS-B,
  finalize; Mixture.optimize()/current_residual()/update()). GUI: the Edit
  Mixtures Optimize button runs it under a busy cursor with a UI-boundary
  error dialog, updates the matrix + a live "Residual (Rp)" label and redraws;
  the auto_run/auto_scales/auto_bg checkboxes are editable + persisted (they
  pick the free variables), and F5 Refresh Graph optimises auto_run mixtures
  (project.refresh()) else re-applies. Still deferred: the full Refinement
  WINDOW (btn_refine: method selection, refinable tree, live status) and the
  auto-run-on-every-edit behaviour (manual edits apply, only F5/Optimize
  refine). Debugging notes: scipy 1.18 dropped fmin_l_bfgs_b'"'"'s iprint arg (it
  is silent by default); the core does NOT swallow exceptions (fail loud - the
  GUI wraps it), the objective is guarded finite (_PENALTY), a diverged solve
  keeps the current solution.
- [x] per-phase fraction refine checkbox (2026-08-04) - the fraction cell in the
  Edit Mixtures matrix now has a checkbox (old app `fractions_mask`) bound to
  Mixture.fraction_refine/set_fraction_refine. Unchecked = that phase's fraction
  is held fixed by Optimize (for manual setting); the optimiser renormalises the
  remaining free fractions to 1 - sum(fixed). Harnesses tools/verify_fraction_
  refine.py (model + optimise) + tools/verify_fraction_refine_ui.py (checkbox).

Regression harnesses (all head-less, bundled interpreter, exit 0 = pass /
1 = regression / 2 = no samples; pass .mud paths to point elsewhere):
- `tools/verify_calc_engine.py` guards the CALC path - recomputes the
  sample projects and diffs the result against the calculated pattern the
  old GTK app stored in the .mud (the gold standard). Run after touching any
  calc-engine file.
- `tools/verify_roundtrip.py` guards the PERSISTENCE path - load -> save ->
  reload keeps the modeled parts JSON-equal (A), every editable field
  survives a round-trip (B), and the calc is unchanged by a round-trip (C).
  Run after touching a model to_dict / from_dict or the file parser.
- `tools/verify_optimizer.py` guards the OPTIMIZER - re-optimising the stored
  solution never worsens it, a perturbed start (scales->1, bg->0) recovers,
  the solution stays valid, and no-free-vars is a safe no-op. Run after
  touching calculations/mixture.py or the objective/masks.
- `tools/verify_refinement.py` guards the structural REFINEMENT - refinables
  enumerate, a flagged param perturbed then refined recovers, all three
  methods run finite, ref_info round-trips. The heaviest harness (nested
  optimize). Run after touching calculations/refinement.py.
- `tools/verify_linking.py` guards COMPONENT LINKING - linked children resolve
  to their template, inherited properties read through (and non-inherited read
  own), editing a template propagates, inherited d001/delta_c are skipped as
  refinables, and links survive a round-trip. Run after touching
  models/component.py, the phase loader, or the refinable enumeration.
- `tools/verify_ucp.py` guards UNIT-CELL PROPERTIES - cell a/b read the stored
  (not recomputed) value on load incl. stale UCPs, derivation sources resolve,
  editing recomputes + cascades (pn -> cell_b -> cell_a), and value/enabled/
  factor/constant survive a round-trip. Run after touching
  models/unit_cell_prop.py or the component cell a/b handling.
- `tools/verify_relations.py` guards ATOM RELATIONS (AtomRatio + AtomContents) -
  the atom refs resolve, the stored pn is kept on load (not applied -
  golden-safe), editing a relation re-derives the atoms' pn and cascades to
  cell_b -> cell_a, and the relation fields survive a round-trip. Run after
  touching models/atom_relations.py or the component relation handling.
- `tools/verify_phase_inheritance.py` guards PHASE-LEVEL `based_on` - based_on
  resolves, an inherited stacking F reads the PARENT's value (the child's stored
  F is stale), W/P follow, a parent edit propagates, inherited sigma*/CSDS/F are
  skipped as refinables, and the child re-serialises its OWN stale F. Also
  asserts a *discriminating* fixture exists (else the read-through could be
  silently broken). Run after touching models/phase.py or models/probabilities.py.
- `tools/verify_pattern_ops.py` guards the DATA OPERATIONS' numerics
  (background / smooth / noise / shift / strip / peak area+FWHM / trim). These
  are destructive and the old app stores only the result, so there is no golden
  .mud: it diffs against the LIVE old `math_tools.py` (loaded by path), against
  analytic ground truth (Gaussian area/FWHM, the displacement formula), and
  against invariants. Includes the trim-persistence regression guard (a trim
  must survive save/reload, per-phase calc columns intact). Run after touching
  calculations/pattern_ops.py or models/specimen.py.
- `tools/verify_data_op_dialogs.py` guards the DATA-OP DIALOGS themselves
  (offscreen Qt). Asserts each one *actually changes* the pattern - they shipped
  for a long time looking finished while applying nothing - and that every
  refusal path leaves the data alone, keeps the dialog open, and says why. Run
  after touching line_dialogs.py or specimen_dialogs.py.
- `tools/verify_phase_crud.py` guards ADD/REMOVE PHASE at the MODEL layer -
  the four cascade rules of remove_phase (own based_on, dependants' based_on,
  linked_with components, mixture cells) plus persistence (add and remove must
  survive save/reload), and remove_specimen unsetting the specimen from
  mixtures. Run after touching project.py / mixture.py / the phase part of the
  saver.
- `tools/verify_phase_dialogs.py` guards the ADD/REMOVE dialog WIRING (offscreen
  Qt): button state (Add/Remove on, Import/Export off with a reason), the Add
  dialog offering only the ported empty-phase path (R locked to 0), and the
  three views (project.phases / the dialog's _phases snapshot / the tree rows)
  staying in lock-step through add, remove, decline and add-then-remove. Run
  after touching edit_phases_dialog.py or add_phase_dialog.py.
- `tools/verify_r1.py` guards R1 (Reichweite-1) STACKING - the R1G2 probability
  model added in Batch R1a. Dispatch, analytic W/P (re-derived independently),
  P-rows-differ (genuinely R1, not an R0 collapse), per-parameter inheritance
  read-through (W1/P11 through to the based_on parent), discrimination vs R0,
  and byte-identical round-trip. Fixture: `Dh537A.mud`. NOTE: every R1 phase
  there has W1 ~ 0.73, so the golden calc only exercises the W1>0.5 branch - the
  W1<=0.5 branch is guarded only by the synthetic `2b` check. Run after touching
  models/probabilities.py. The golden-calc proof itself is in
  `verify_calc_engine.py` (Dh537A added to its default set).
- `tools/verify_higher_r.py` guards ALL higher-R STACKING models (R1G3, R2G2,
  R2G3, R3G2 - everything on `_MarkovProbability`). Per model: dispatch,
  matrix shape / reps (`= G^(R-1)`, so 1/2/3/4), validity (stationary W +
  active-row-stochastic P), per-parameter inheritance read-through,
  editor/refiner enumeration, byte-identical round-trip + edit persistence.
  R2G2 and R2G3 also get an INDEPENDENT matrix re-derivation - R2G3's matters
  because its fixture pins G1-G4 at 0.5 (non-discriminating), so the golden
  cannot see the G ratios; the re-derivation checks them at G=0.6 across both
  W1 branches. The golden-calc correctness proof is in `verify_calc_engine.py`
  (the Illite-Smectite R/G series + MPDO twins, all corr 1.000000). Run after
  touching models/probabilities.py.

**Sample fixtures (2026-07-14).** `Dh2040A.mud` was withdrawn (faulty). The four
in use, and what each is for:

| Fixture | What it is | Why it matters |
|---|---|---|
| `308 r1.mud` | a normal project, after refinement | the long-standing baseline. DOES use phase-level `based_on` (IS EG/350 based on IS AD, inheriting sigma*/CSDS/colour + `inherit_F1`) - but non-discriminating: its inherited values coincide with the children's stored ones, so it cannot detect a broken read-through |
| `Dh2040A 14Jul26.mud` | phases + a mixture assigned; NO manual adjustments, not refined. The Illite phase is not required by the experimental data (fraction 0) | uses `based_on`, but every inherited value coincides with the child's stored one, so inheritance is INVISIBLE here - a "does it still load" case |
| `Dh2040A 14Jul26 r1.mud` | same, with MANUAL phase-property adjustments, inheritance links left INTACT. Not refined | **discriminating (positive)**: parent F1 = 0.17 while the children still store a stale 0.8, so the read-through is observable. This is the file that exposed the phase-inheritance correctness bug |
| `Dh2040A 14Jul26 r2.mud` | same manual adjustments, but inheritance intentionally UNLINKED (per-flag: EG's `inherit_F1` off, 350's left on) | **discriminating (negative + positive in one file)**: EG must use its OWN F1 = 0.3 and ignore the parent, while 350 must use the PARENT's 0.17 and ignore its stale 0.8. Catches inheritance being applied where it should NOT be |

Together r1 + r2 pin the per-flag read-through in BOTH directions; a bug either
way breaks the golden patterns.

**Optimizer cold-start robustness (FIXED 2026-07-16).** The standalone mixture
Optimise is now a **multi-start** search (`optimize_mixture(mixture, n_starts)`;
`Mixture.optimize` defaults to `n_starts=4`): start 1 is the exact current
solution (so the result never worsens), start 2 is a least-squares scale/bg warm
start (obs ~= scale*signal + bgshift*correction is a 2-param linear fit for the
current fractions), and the rest are random-fraction restarts (deterministic
seed), keeping the best. This recovers <= the stored optimum on all four
fixtures from a cold start (was 2 failures). Diagnosis en route: the unrefined
`Dh2040A 14Jul26.mud`'s stored solution is itself SUBOPTIMAL (we now reach ~59.8
vs its stored 61.99). The structural-refinement inner loop still calls
`optimize_mixture` with the single-start fast path (`n_starts=1`, unchanged), so
refinement runtime is unaffected (verify_refinement ~180 s, 84/84). Guard:
`tools/verify_optimizer.py` 32/32.

## Recreated

| Component | New files | Old source | Status |
|---|---|---|---|
| Main window | main_window.ui, main_window.py | application/glade/application.glade | done (plot stack, specimens dock, menus/toolbar; plot controller port pending) |
| Edit Project | edit_project.ui, edit_project_dialog.py | project/glade/project.glade (nbk_edit_project) | done (layout-mode combo is temporary) |
| Edit Specimen | edit_specimen.ui, edit_specimen_dialog.py | specimen/glade/specimen.glade | done (hosts line properties + goniometer components) |
| Line properties (reusable) | line_properties.ui, line_properties_widget.py | generic/views/glade/lines/experimental_props.glade + calculated_props.glade | done |
| Object store shell (reusable) | object_store.ui, object_store_dialog.py | generic/views/glade/object_store.glade | done (Add/Remove wired by the Edit Phases subclass; Import/Export still per-subclass) |
| Edit Phases | edit_phase.ui, edit_phase_widget.py, edit_phases_dialog.py, csds.ui/csds_widget.py, probabilities.ui/probabilities_widget.py, edit_component.ui/component_widget.py, atom_list.ui/atom_list_widget.py, ucp.ui/ucp_widget.py | phases/glade/phase.glade + csds/probabilities/component/layer.glade + shell | partial (bound to real Phase models; name/sigma*/CSDS-mean + R0 F params + component c-axis scalars + unit-cell a/b (UnitCellPropWidget) + layer/interlayer atoms editable with live recalc; phase inheritance (based_on combo + per-property inherit flags + greying) and the display colour (modeled hex, reads through based_on; harness verify_phase_color.py) wired; Add + Remove + phase Import/Export (.phs) + component Import/Export (.cmp) wired; atom relations fully editable (AtomRatio + AtomContents editors, plus relation-to-relation chaining and relation-value refinement, 2026-07-22). Remaining: only the composition summary. NOTE: display_color round-trips + is editable and now drives both the per-phase curves and the mixture-legend swatches on the plot) |
| Edit Atom Types | edit_atom_type.ui, edit_atom_type_widget.py, edit_atom_types_dialog.py | atoms/glade/atoms.glade + shell | done (real AtomType models from the .mud; live real ASF plot; "Fill from element" picker fills weight + scattering-factor coefficients from the built-in library, 2026-07-22) |
| About box | QMessageBox.about placeholder | about_window in application.glade | partial (branding: logo, icons, version) |
| Edit Mixtures | edit_mixture.ui, edit_mixture_widget.py, edit_mixtures_dialog.py | mixture/views/glade/edit_mixture.glade + shell | done (bound to the Mixture model; fractions/scales/background editable with live recalc; per-cell phase reassignment via a validity-gated combo (set_phase_at; invalid phases greyed); structural add/remove wired (Add phase/specimen/both buttons + header context menus to rename/remove a slot and assign/remove a specimen); Optimize runs the L-BFGS-B refinement with a live residual label; Refine opens the Refinement window; auto_run/scales/bg live; the Composition button opens the per-specimen oxide summary. Fully wired) |
| Refinement window | refinement.ui, refinement_dialog.py | refinement/views/glade/refinement.glade + refine_results.glade | done (foldable refinable tree with editable value/min/max + flags, right-click menu incl. auto-restrict/randomize, selected-count + budget + warning readouts, method combo + per-method options, threaded Refine + Cancel + live status, Initial/Best/Last + GoF results with keep-buttons + detailed report, + a live convergence PROGRESS plot best-Rp-vs-evals with per-specimen curves, throttled at 150 ms; verify_refine_progress_plot). Parameter-space/landscape plot intentionally dropped (brute-force removed). |
| Import composition | import_composition.ui, import_composition_dialog.py | (new - no old-app equivalent) | done 2026-08-22 (measured XRF oxide analysis, one per project; reuses OxideGrid so the oxide set matches the modelled composition; Data menu; verify_composition_object 46/46) |
| Add Phase dialog | add_phase.ui, add_phase_dialog.py | phases/glade/addphase.glade | done (empty phase; R0 with G 1-6, or R1 which locks G=2 = only R1G2 modeled; R2+ unported; raw-pattern option wired; **default-catalog picker wired** (2026-07-22, 19 built-in reference clays via file_parsers/default_catalog.py); wired to Edit Phases Add) |
| Goniometer component | goniometer.ui, goniometer_widget.py | goniometer/glade/goniometer.glade | done (plugged into Edit Specimen; Edit emission spectrum wired to the wavelength-distribution editor) |
| Remove Background | background.ui, line_dialogs.py | generic/views/glade/lines/background.glade | done (applies: linear + pattern bg, pattern interpolated onto the specimen grid) |
| Smooth Data | smoothing.ui, line_dialogs.py | lines/smoothing.glade | done (applies: all 6 types; Show Original overlay needs the plot-controller port) |
| Shift Pattern | shifting.ui, line_dialogs.py | lines/shifting.glade | done (applies: auto-detect vs reference + manual; linear/displacement) |
| Add Noise | add_noise.ui, line_dialogs.py | lines/add_noise.glade | done (applies) |
| Strip Peak | strip_peak.ui, line_dialogs.py | lines/strip_peak.glade | done (applies; modeless; drag across the pattern to select start/end via _RangeSelectMixin + arm_range_pick; single "Keep peak %" op - keep_percent (fractional, min 0; 0 = classic strip) + retained noise_level, compute_reduce_pattern = bg_line + keep*(y-bg_line)+noise, no background notch; live plot preview via PatternPlot.set_preview / Specimen.preview_strip) |
| Peak Properties | peak_properties.ui, line_dialogs.py | lines/peak_properties.glade | done (live area/FWHM; read-only; modeless; drag across the pattern to select start/end via _RangeSelectMixin; copy-to-clipboard) |
| Trim Data | trim_dialog.ui, specimen_dialogs.py | specimen/glade/trim_dialog.glade | done (applies; scope specimen/all, shared-range prefill, marker/exclusion removal warning) |
| Statistics | statistics.ui, specimen_dialogs.py | specimen/glade/statistics.glade | done (unwired until the specimens context menu exists) |
| Save Graph size | save_graph_size.ui, specimen_dialogs.py | specimen/glade/save_graph_size.glade | done (runs before the native save dialog; export with plot-controller port) |

## To do

### Phase editing family
- [x] Component linking (foundation, Batch L1) - models/component.py. A
  component can be linked to a template component in another phase (old
  `linked_with` + eight `inherit_*` flags): the same clay layer reused across
  phases (e.g. an illite layer in both a discrete illite phase and an
  illite-smectite mixed-layer phase). Inheritance is a **read-time overlay** -
  an inherited property reads through to the template's value while the child
  keeps its own stored copy (byte-identical round-trip) - and **per-property**:
  a glycolated smectite inherits cell a/b + delta_c + layer atoms from its
  2-water template but keeps its own d001 (the air-dried -> glycolated ->
  heated swelling states). Links resolve by uuid after all phases load
  (mud_project.load_mud builds a project-wide component map); an inherited
  d001/delta_c is skipped as a refinable (calculations/refinement.py, old
  is_refinable = not inherited). Phase-level `based_on` inheritance was deferred
  at this point and implemented later (see the phase-inheritance entry). Harness:
  tools/verify_linking.py (resolve/read-through/selective/propagation/
  refinable-skip/round-trip); golden calc + round-trip unchanged.
- [x] Component linking editor (Batch L2 + L3) - component_widget.py + the
  edit_component.ui "Component linking" group. The linked_with combo lists every
  component in the project ("Phase / Component" + "(not linked)"); picking one
  links this component (Component.set_linked_with), "(not linked)" unlinks and
  clears the inherit flags. set_linked_with refuses a self-link / cycle (a
  rejected pick reverts the combo); candidates thread down via
  EditPhasesDialog._link_candidates -> bind_phase -> bind_components. On a linked
  component, ticking an inherit box greys the field (it reads through to the
  template) and recomputes; checkboxes enable only when linked. d001 (follows
  the cell-c gate) + atom-relations checkboxes are read-only. NOTE: more
  permissive than the old app (which linked only within phase based_on); when
  based_on is ported it will drive links positionally. Verified: link/unlink/
  inherit/cycle-guard via GUI smoke; runtime-created links round-trip;
  harnesses unchanged.
- [x] CSDS distribution component - csds.ui + csds_widget.py (mean spinbox +
  live log-normal histogram + derived range; plugged into Edit Phases CSDS
  tab, bound to DritsCSDSDistribution). Old: phases/glade/csds.glade.
- [x] Probabilities component - probabilities.ui + probabilities_widget.py
  (R0 only: editable (G-1) F spinboxes + read-only W/P tables, built
  dynamically; tab shown only for G>=2). Old: probabilities/glade/
  probabilities.glade + matrix.glade + R0_independents.glade. R1-R3 Markovian
  models come when a project needs them.
- [x] Component editor - edit_component.ui + component_widget.py (selector +
  c-axis scalars + atom lists). Old: phases/glade/component.glade.
- [x] Unit cell property editor - phases/glade/unit_cell_prop.glade (inside the
  component editor). **Batch 1a (model):** cell a/b are UnitCellProperty
  objects (models/unit_cell_prop.py) - fixed (typed value) or derived
  (value = factor*prop + constant, prop = the component's cell_b or an atom pn:
  cell_a = 0.57735*cell_b, cell_b = k*pn + const). The .mud's stored value can
  be STALE and the old app's stored pattern used it, so the model KEEPS the
  stored value on load and only recomputes (Component.update_ucp_values) on an
  edit - never at load (golden calc unchanged). Derivation sources resolve by
  uuid (mud_project builds a component+atom object map, resolve_ucp_props).
  Harness: tools/verify_ucp.py (61 checks). **Batch 1b (UI):** a reusable
  UnitCellPropWidget (ucp.ui + ucp_widget.py) embedded twice (a, b) in the
  component editor - an "Derived" toggle, the value spin (active when fixed),
  and factor x prop-combo + constant (active when derived; combo = the atoms'
  pn + the other cell). Editing recomputes + cascades (cell_b feeds cell_a) +
  redraws; a changed prop rewrites its [uuid, attr] (dirty flag, round-trip
  safe); inherited cell a/b disable the widget (via L2's is_inherited).
- [x] Layer / interlayer atom lists - atom_list.ui + atom_list_widget.py
  (name/Def.Z/pn + element combo + add/remove). Old: phases/glade/layer.glade.
- [x] Edit Atom Ratio dialog - phases/glade/ratio.glade (modal). **Batch 2a
  (model, DONE):** AtomRatio (models/atom_relations.py) splits an occupancy
  between two atoms - `atom1.pn = value*sum`, `atom2.pn = (1-value)*sum` (the
  OctFe octahedral Fe/Mg substitution). The component holds a modeled
  `_atom_relations` list (AtomRatio objects; AtomContents + relation-to-relation
  chaining entries kept VERBATIM until Batch 3). Golden-safe: relations resolve
  by uuid but are NOT applied on load (the stored pn is kept and reproduces the
  old app's pattern); `apply_atom_relations` runs only on an edit and then
  cascades pn -> cell_b -> cell_a (fixes the audit's atom-pn -> UCP gap).
  `atom_relations` is a read-through property (inherit_atom_relations). Harness:
  tools/verify_relations.py (104 checks). **Batch 2b (UI, DONE):** the component
  editor's "Atom relations" group - a `cmb_relation` selector + Add ratio /
  Remove + the embedded AtomRatioWidget (ratio.ui + ratio_widget.py: name,
  enabled, atom1/atom2 combos, value, sum). Editing re-applies the relation
  (sets the atoms' pn) and cascades pn -> cell_b -> cell_a + recomputes; the
  atom lists refresh; inherited relations are read-only. Also fixed the
  audit's atom-pn -> UCP gap: `_on_atoms_changed` now calls `update_ucp_values`.
- [x] Edit Atom Contents dialog - phases/glade/contents.glade. **Batch 3:**
  AtomContents (models/atom_relations.py: AtomContents + AtomContent rows) scales
  a set of atoms by one value - `atom.pn = amount*value` per row (interlayer K /
  Ca / H2O content). Modeled + golden-safe (resolved but not applied on load).
  Editor: contents.ui + contents_widget.py (name, enabled, value + a table of
  atom/amount rows with Add/Remove), embedded in the component editor's Atom
  relations group next to the AtomRatio editor (one shown per selected relation;
  "Add contents" button). Editing re-applies + cascades pn -> cell_b -> cell_a.
  inherited relations read-only. Harness: verify_relations.py.
- [x] Atom-relation CHAINING + value refinement (2026-07-22). **Chaining:** an
  AtomContents row may target a sibling relation - `prop` = "value" drives that
  relation's value, "__internal_sum__" drives an AtomRatio's sum (from
  `amount*value`), then re-applies it so the driven atoms follow (re-entrancy
  guard breaks cycles; component.resolve_relations now passes a {uuid: relation}
  map). The contents editor lists EVERY row with a Target combo (atoms + sibling
  relations: a ratio offers RATIO/SUM, a contents its value) and refuses a
  cycle. **Refinement:** enumerate_refinables now exposes each relation `value`
  (AtomRatio fraction bounds [0,1] / AtomContents multiplier), EXCEPT inherited,
  disabled, or driven relations (old AtomRelation.is_refinable); the setter
  re-applies so pn (and derived cell) update before the calc. Harness:
  tools/verify_relation_chain_refine.py (11).
- [x] Raw pattern phase editor - phases/glade/raw_pattern_phase.glade
  (edit_raw_pattern_phase.ui + edit_raw_pattern_phase_widget.py: name + import
  + preview; hosted in Edit Phases, routed by phase.type; batch 2). Batch 3
  DONE: import parsers (file_parsers/xrd_import.py) - .xrdml, Rigaku .rasx,
  ASCII/.xy(+BOM), Bruker .raw v1-3; deferred Bruker RAW4 + non-Bruker "FI"
  .raw (reverse-engineering). Guard: tools/verify_xrd_import.py.

### Markers (done - editors)
- [x] Edit Markers window - edit_markers_dialog.py (object-store shell + find peaks / match minerals extra row); EditMarkersView
- [x] Edit Marker fields - edit_marker.ui, edit_marker_widget.py (specimen/glade/edit_marker.glade)
- [x] Detect peaks - find_peaks_dialog.ui, detect_peaks_dialog.py (threshold/prominence histogram + draggable cut-off; OK adds markers via Specimen.auto_add_peaks / calculations.peak_detection)
- [x] Match minerals - match_minerals.ui, match_minerals_dialog.py (real mineral_references.csv + score_minerals; auto-match, manual add/remove, append labels; reference-peak preview overlay via Specimen.mineral_preview + PatternPlot magenta sticks, Specimen-range filter; verify_mineral_preview.py)

### Goniometer
- [x] Wavelength distribution editor - wavelength_distribution.ui, wavelength_distribution_dialog.py (goniometer/glade/wavelength_distribution.glade); opened by the goniometer component's Edit emission spectrum button; editable (nm, fraction) table + Add/Remove + .wld import/export; Goniometer.set_wavelength_distribution persists edits; verify_wavelength_distribution.py
- [x] Stored goniometer setups - goniometer_widget.py Load setup combo + Store setup button; file_parsers/gon_file.py (.gon load/save/list), 12 bundled presets under data/default goniometers/, Goniometer.apply_setup (full reset, keeps uuid, legacy lambda); verify_goniometer_setup.py

### Mixtures
- [x] Add / Remove mixture (Edit Mixtures shell, 2026-07-22). NO dialog: the old
  add_mixture.glade type-chooser (regular vs in-situ) was ABANDONED dead code -
  in-situ mixtures were never finished (InSituMixture commented out everywhere)
  and create_new_object_proxy just `return Mixture(...)`. So the shell's Add
  button creates a blank regular `Mixture(name="New Mixture")` directly
  (edit_mixtures_dialog._on_add_mixture -> project.add_mixture, list row +
  select), which the user builds with the editor's Add phase/specimen buttons.
  Remove (`_on_remove_mixture` -> new `Project.remove_mixture`; no cascade,
  nothing back-references a mixture) is wired too, fixing the other dead shell
  button. Harness tools/verify_add_mixture.py (10).
- [ ] Default-phase catalog (Add Phase dialog's disabled option). MULTI-PART -
  a default component's atoms reference atom types by NAME and need scattering
  factors, so it is blocked on an atom-type library (the old app's `.atl`).
  Sequence:
  - [x] **Step 1 - atom-type scattering-factor library (2026-07-22).** The old
    `atomic scattering factors.atl` (Waasmaier-Kirfel CSV) is bundled at
    `mudlab/data/atomic_scattering_factors.csv`; `file_parsers/atom_type_library.py`
    (`load_atom_type_library` / `atom_type_library_map`) reads it into AtomType
    models by name. Backs the Edit Atom Types "Fill from element" picker and is
    the prerequisite for the catalog (proven: Kaolinite.cmp resolves against the
    library -> non-blank pattern; without it -> blank). Harness
    tools/verify_atom_type_library.py (9). Bundled via MudLab.spec `datas`.
  - [x] **Step 2 - bundle the 27 default-component `.cmp` files (2026-07-22).**
    Copied verbatim to `mudlab/data/default components/` (9 single-layer +
    Di-Smectite/Di-Vermiculite/Tri-Smectite x6). `.gitattributes` now marks
    `*.cmp`/`*.phs` binary (they are ZIPs - defends against eol corruption, like
    `.mud`). Accessor `file_parsers/default_catalog.py`
    (`default_components_dir` / `load_default_component` - resolves against the
    library by default). Harness tools/verify_default_components.py (5): all
    resolve to library scattering factors + single-layer clays compute non-blank
    patterns. Bundled via MudLab.spec `datas` (src/mudlab/data).
  - [x] **Step 3 - generator recipe / in-memory builder (2026-07-22).**
    `default_catalog.py` `build_catalog_entry` ports the old phaseworker: a
    4-char component code selects the `.cmp` files, per-phase `based_on` +
    per-component `linked_with` names wire the Ca-AD -> Ca-EG -> Ca-350 chains,
    inherit flags applied. `is_modeled` gates to R0 (any G) / R1G2 (R1G3/R2/R3
    unported). `default_catalog_entries` lists the offerable entries. Covers the
    8 single-layer clays + 3 expandable families (Di-Smectite/Tri-Smectite/
    Di-Vermiculite, AD/EG/350) - all G=1. Harness tools/verify_default_catalog.py
    (13): chains build with right based_on/linked_with + distinct d001
    (1.50/1.686/0.96) + all compute. NO `.phs` bundled - built in memory on demand.
  - [x] **Step 3b - mixed-layer interstratified families + probability
    inheritance (2026-07-22).** Added `inherit_all()` to the probability models
    (R0 / R1G2 / generic; mirror of clear_inheritance); the builder calls it
    after set_based_on when a phase description has `inherit_probabilities` (a
    no-op at G=1). Recipe helper `_interstratified` adds Illite- / Kaolinite- /
    Talc- / Chlorite-Smectite at R0 AND R1G2 (G=2: a fixed clay inheriting the
    AD copy entirely + a smectite inheriting only its layer). Harness extended
    (21): treated phases inherit the AD's stacking RATIO (editing the AD flows
    through) + both components linked + all compute.
  - [x] **Optional tail - full mixed-layer catalog (2026-07-22).** Refactored
    the recipe onto a generalized `_build_family(columns)` (a hydration LADDER
    per smectite family + fixed-clay columns). Aliased the 1WAT/1GLY/Dehydr
    states; added SS/SSS multi-hydration (Di-/Tri-Smectite, Di-Vermiculite),
    higher-order 2-clay (Illite-/Kaolinite-/Talc-/Chlorite-Smectite at 1-3
    smectite states), and 3-clay (Illite-/Kaolinite-Chlorite-Smectite). Catalog
    is now 42 entries (later 80, see below). Harness verify_default_catalog incl.
    a full sweep: every entry builds valid + computable.
  - [x] **Higher-R model EXPOSURE (2026-07-22, uncommitted).** The R1G3/R1G4/
    R2G2/R2G3/R3G2 probability MODELS were already ported + golden-validated
    (verify_higher_r 53/53); they were just not reachable from new-phase/UI/
    catalog paths (stale "only R0/R1G2" docstrings). Exposed via:
    probabilities.py `create_probability(R,G)` + `is_supported_rg` /
    `supported_g_range` (RGbounds: R0 G1-6, R1 G2-4, R2 G2-3, R3 G2);
    Phase.create_empty uses the factory (no longer forces R1->G2); add_phase
    dialog R 0-3 with G range per R; default_catalog is_modeled -> is_supported_rg
    + `_build_family` max_r 4. Catalog **42 -> 80 entries** (full old-app parity,
    +23 R2/R3), all build valid + compute. Harness verify_probability_factory
    (6); verify_phase_dialogs + verify_default_catalog updated. Suite 30/30.
  - [x] **Step 4 - Add Phase default-catalog picker (2026-07-22).** add_phase_
    dialog.py lists `default_catalog_entries()` (rdb_default_phase enabled;
    btn_generate_phases obsolete - the catalog is built in memory, nothing to
    regenerate). edit_phases_dialog `_on_add_phase` "default" path calls
    `add_catalog_entry_to_project` (default_catalog.py): builds the entry, merges
    its atom types into the project BY NAME (reuse existing / adopt library),
    adds the phase-set (a single clay, or an AD/EG/350 triple), selects the
    first. `Atom.to_dict` writes the re-pointed atom_type, so it round-trips.
    Harness tools/verify_add_default_phase.py (11): empty-project add, dedup (no
    duplicate Si/O), triple, .mud round-trip. verify_phase_dialogs updated
    (default option now enabled). Catalog is 19 entries (8 single-layer + 3
    expandable + 4 interstratified x R0/R1G2).
- [x] Composition summary - btn_composition in the mixture editor (2026-07-22).
  Per-specimen oxide wt% (old Mixture.get_composition_matrix): each atom
  contributes pn x atom_type.weight x (component weight fraction x phase
  fraction) x oxide factor, accumulated by element, converted to SiO2/Al2O3/
  Fe2O3/CaO/MgO/Na2O/K2O (mudlab/data/composition_conversion.csv; the old app's
  factors verbatim, its "Al2O2" label typo corrected to Al2O3 - display only,
  the factor is unchanged) and normalised to 100 per specimen.
  Analytics: calculations/composition.py; modal CompositionDialog
  (composition.ui, oxides x specimens table + Copy/Export CSV). Raw phases +
  empty cells contribute nothing. Harness tools/verify_composition.py (11).
  MudLab.spec now bundles src/mudlab/data.

### Refinement (structural-parameter refinement, distinct from mixture Optimize)
- [x] Phase A: refinables framework + engine - calculations/refinement.py.
  enumerate_refinables(mixture) collects the phases' refinable structural
  params (sigma*, CSDS mean, R0 F params, component d001/delta_c), each a
  Refinable with value get/set into the live model + [min,max,refine] read/
  written into raw_properties ref_info (round-trips via to_dict). Refiner runs
  an outer SciPy method over the FLAGGED params; each trial inner-optimises
  fractions/scales/bg (optimize_mixture) - the old nested get_optimized_
  residual. Two convergent SciPy methods kept - 0 = L-BFGS-B (unchanged, so
  .mud refine_method_index 0 still maps), 1 = Basin Hopping; the deap ones
  (no deap) and Brute force (coarse grid, no convergence, combinatorial
  runtime - Basin Hopping dominates it) were dropped. Mixture.refine()/
  refinables() + refine_mixture() returns the Refiner (initial/best/last +
  apply methods). Debugging: no iprint (scipy 1.18), objective guarded finite,
  fail-loud (GUI wraps), stop hook for cancel, disabled record_history hook.
- [x] Phase B1: the Refinement window - refinement.ui + refinement_dialog.py
  (RefinementDialog). A table of the mixture's refinables (Parameter / Value /
  editable Min / Max / Refine toggle, bound to mixture.refinables() +
  Refinable.set_ref_info, round-trips), a method combo (0 = L-BFGS-B, 1 =
  Basin Hopping, persisted to refine_method_index), a Refine button (made
  threaded in Phase C - see below), and the Initial / Best / Last residuals
  with Keep buttons (refiner.apply_*). Opened from the Edit Mixtures
  btn_refine; refreshes that editor on close. Old: refinement.glade +
  refine_results.glade.
- [x] Phase B2: per-method options + helpers (refinement_dialog.py). A form
  rebuilt per method - L-BFGS-B (maxfun/maxiter), Basin Hopping (niter/T/
  stepsize) - seeded from and persisted to the mixture's refine_options[index]
  (round-trips). auto_restrict sets Min/Max to v*0.8 / v*1.2 for flagged
  params; randomize sets each flagged param to uniform(min,max) and recomputes
  the starting pattern. (Inner optimiser limits stay fixed; the old inner_*
  options are not exposed.)
- [x] Phase C: threaded refinement - the Refine button now runs on a
  background QThread (_RefineWorker in refinement_dialog.py), so the window
  stays responsive. A live status label shows "Refining... N evaluations,
  best Rp = X" (engine on_progress hook -> Refiner.update, emitted as a queued
  Qt signal), and Cancel sets a threading.Event wired to the engine `stop`
  hook (keeps the best-so-far). The worker only mutates the plain calc models
  and emits no signals from the calc path; the recompute + plot redraw happen
  on the GUI thread in the finished handler; closeEvent cancels + joins. See
  the "Robustness & long runs" note in calculations/refinement.py.
  The results output (Initial/Best/Last residuals + Keep buttons + a GoF
  (best solution) readout, mean per-specimen GoF) is inline in the window.
- [ ] Progress/results PLOT (deferred, not needed now): the refinement
  progress plot + results/history window (refine_results.glade / the disabled
  Refiner.record_history + Refiner.history hook; old get_plot_samples plotted
  residual-vs-iteration + parameter samples). The Create-plot checkbox /
  Show-plot button / plot dialog are intentionally omitted. With Brute force
  gone the parameter-space plot has little value (the other two methods only
  sample a convergence trajectory, not the residual surface).
- [x] Refiner-UI round three (2026-08-22) - the three suggestions the round-two
  audit left open, all three done. (1) EDITABLE VALUE COLUMN restored (the old
  GTK app always allowed it; MudLab2 had made it read-only because nothing
  wrote a typed number back). _EditableCellDelegate now admits Value as well as
  Min/Max, and _on_value_edited writes the model, recomputes, refreshes the
  results/report and flags the row as hand-set. Deliberately NOT clamped to
  Min/Max - those are search bounds, not validity limits. (2) WARNING LINE
  (lbl_param_warning, below the tree) - it is the fix for the silent skips:
  a ticked parameter whose Min >= Max is dropped by Refiner.__init__ without a
  word, and a value outside its bounds is CLIPPED so the run does not start
  where the cell says. Both are now named, their cells tinted, and a third
  message reports hand-set values; every message resets itself the moment the
  condition clears (the label hides entirely, so a clean dialog has no empty
  strip). Messages are kept terse ON PURPOSE - spelled out, three of them
  wrapped to ten lines and took 152 px off a 415 px tree; the reasoning lives
  in the label + per-cell tooltips. (3) PER-SPECIMEN Rp CURVES in the progress
  plot - the reported Rp is a MEAN, so one curve cannot show a run that
  improves one specimen by degrading another (measured on 308 r1: mean 35.34 ->
  34.98 while "308 400" got WORSE, 41.87 -> 42.26). _Problem.residual is now
  defined in terms of a new residual_parts(), optimize_mixture(with_breakdown=
  True) returns it for the applied solution, and Refiner tracks the breakdown
  OF THE BEST so the thin curves always average to the bold one (asserted to
  1e-9). Costs one extra objective evaluation per trial, only when a progress
  consumer exists - measured inside run-to-run noise (3.76 s vs 3.86 s). NOTE
  on_progress is now a THREE-argument callback. verify_refine_progress_plot
  122/122 (was 101), verify_refinement 140; full suite 68. Manual: new
  "Refining a mixture" chapter in docs/user-manual.md.
- [ ] Phase-intensity cache (deferred perf, user-deferred): the old
  calculations/phases._phase_intensity_cache + its "use intensity cache"
  checkbox were never ported. Re-adding it (keyed by phase params, always-on,
  bounded like _csds_cache) would speed up refining multi-phase mixtures where
  only some phases are flagged (the unchanged phases would cache-hit each
  outer trial). Not essential; no checkbox needed.

### Other
- [x] Measured (XRF) composition object (2026-08-22) - NEW project-level feature,
  step 1 of 2. `models/composition.py` `Composition` (name / source / uuid /
  oxides) held as `Project.composition` (optional, ONE per project - a project
  describes one physical sample and its specimens are treatment variants), with
  a `composition_changed` signal. Data -> Import composition opens
  `import_composition_dialog.py` (ui/import_composition.ui), which reuses the
  shared `OxideGrid` so the oxide set is EXACTLY `reporting_oxides()` - the same
  rows the modelled composition reports, which is what makes the two comparable;
  an oxide the model cannot produce could not take part in the comparison. Has
  "Recompute to 100 %" (the modelled composition is always normalised to 100, so
  a raw 97 % analysis would otherwise read as a difference that is not there;
  note the grid holds 2 decimals so it can land on 100.01 - rounding, not a bug).
  Re-opening the menu item EDITS the existing analysis (same uuid) rather than
  adding a second. The model filters on set: non-reporting oxides, non-numeric,
  NaN/inf and negatives are dropped, so a hand-edited file cannot poison the
  comparison. PERSISTENCE is a `composition` property of the Project, written
  ONLY when one exists and REMOVED when cleared - a project that never has one
  round-trips exactly as before (guarded). FILE COMPATIBILITY: measured, the old
  GTK app CANNOT read a project carrying one (`cls(**properties)` -> TypeError on
  any unknown key; a new archive entry fails identically - only embedding in
  `description` survives, which was rejected as too fragile since that field is a
  user-editable text box). This is the accepted divergence the planned old-app /
  PyXRD EXPORTERS will handle. Harness verify_composition_object.py (46).
- [x] Composition COMPARISON (2026-08-22, step 2 of the same feature). The
  Compositions dialog gained two optional column sets, both OFF by default so
  the view opens exactly as before: (a) the measured XRF analysis as one column,
  NORMALISED to 100 (every modelled column is, so a raw 97 % analysis would
  otherwise read as a real difference); (b) the DEFAULT-PHASE STATE, one column
  per specimen - the composition the mixture would have with every phase still
  as the catalog ships it, weighted by the fractions the fit found. Computed by
  `mixture_composition(..., substitutes={phase uuid: replacement phase})` - the
  SAME loop, so the two columns cannot drift apart. New `default_state.py`
  bridges the catalog (file_parsers) and the composition calc (calculations),
  which deliberately does not depend on it. New `default_catalog.default_phase_
  index()/default_phase_names()/build_default_phase()` (lazy, ~1.2 s once, 224
  unique default PHASE names - a treatment triple builds three distinctly named
  phases, so the phase name is the identity, not the entry name).
  THE MAPPING IS USER-STATED AND CANNOT BE DERIVED - measured: a catalog build
  mints FRESH uuids every time, the phase records nothing about its origin, and
  users rename (the catalog's "Illite-Smectite R0 Ca-AD" is a real project's
  "IS R0 Ca-AD"; only 3 of 6 fixture phases match by name). So
  `default_phases_dialog.py` (ui/default_phases.ui) states it once per phase,
  with Match-by-name doing EXACT matches only (a fuzzy guess would corrupt the
  comparison invisibly), stored as `Project.default_phase_map` {phase uuid:
  default phase name} and persisted like `composition` - written only when
  non-empty, removed otherwise, stale uuids pruned on set. An unmapped phase
  falls through to its current state and is NAMED in the title, so a partial
  mapping gives a partial answer rather than a wrong one. Bulk view and the
  default column are mutually exclusive: bulk weights by fraction alone, the
  clay-only view by fraction x formula mass, so together they would put two
  conventions in one table. `bind_mixture(project=...)` threads the project to
  the dialog; without one it behaves exactly as before.
  MEASURED FINDINGS worth keeping: Optimize does NOT change a Phase (only
  fractions/scales/bg, which live on the Mixture) - only REFINEMENT does, via
  (1) atom relations rewriting atom pn (Illite Fe2O3 39.9 -> 134.3, Al2O3 178.4
  -> 118.2 on a 10-eval run) and (2) stacking probabilities changing the
  component weights (`_component_weights` = probabilities.get_distribution_
  array(); 0.8/0.2 -> 0.8675/0.1325). sigma*/CSDS/d001/delta_c do not affect
  composition at all. Harness verify_composition_object.py now 91.
- [x] Original-pattern overlay / live data-op preview - line_dialogs.py _SpecimenDialog._compute_preview + Specimen.preview_* (non-mutating) + PatternPlot.set_preview/clear_preview + main_window.set_pattern_preview; Remove Background/Smooth/Shift/Strip/Add Noise preview live over the original, clear on close; verify_pattern_preview.py + verify_data_op_preview.py
- [x] CSV import options - csv_import.ui, csv_import_dialog.py (generic/views/glade/csv_import.glade); separator/decimal/header + live preview; common file_parsers/csv_io.py drives all CSV import/export; offered by the shared import_pattern helper; verify_csv_import.py
- [x] Specimens context menu - main_window `_build_specimens_menu` (Add/Import, Edit specimen, Edit markers, View statistics, Remove specimen; per-specimen items need a single selection)
- [x] About dialog branding + window/app icons - about.ui, about_dialog.py (logo/name/version/tagline/lib versions); resources.py app_icon()/logo_pixmap; data/icons/ (mudlab.ico + sized PNGs); create_app/MainWindow setWindowIcon; MudLab.spec .exe icon; version 0.2.0; verify_about.py
- [x] Snapshot-on-detach - Phase/Component.snapshot_inherited() bake resolved values (sigma*/CSDS/color/probabilities; cell scalars + shared atom/relation objects) into own storage before a detach so a dependant's calculated pattern does not silently shift; Component.reclone_atoms de-dups the rare two-links-one-template aliasing (.cmp remap path); Project.remove_phase snapshots dependants + Project.phase_dependants drives the dependant-aware delete warning (deletion_confirm_message); explicit detach in the phase/component editors offers keep/revert (inheritance_detach.ask_detach_choice, gated by has_inherited_values). Model + UI. See docs/dev-notes.md. verify_snapshot_detach/verify_snapshot_component/verify_remove_phase_snapshot/verify_remove_phase_dialog/verify_detach_choice
- [x] Per-phase plot curves - calculations/specimen.py calculate_specimen_pattern(return_phase_patterns) captures each phase's scaled contribution; Mixture.calculate stores it via Specimen.set_calculated_pattern(phase_patterns) into the transient Specimen.phase_patterns (never saved); PatternPlot.draw_pattern draws one curve per phase in phase.display_color, gated by display_phases + display_calculated. View > Show phase patterns (actionShowPhases) bulk-flips the shown specimens, recomputes on demand, mirrors per-specimen state (Sep column / Edit Specimen); _set_project recomputes at load when phases are on. verify_phase_curves.py + verify_show_phases_action.py
- [x] Phase index / mixture legend (2026-08-04) - PatternPlot._draw_mixture_legend (port of old plot_mixtures) draws an upper-right AnchoredOffsetbox indexing every mixture that owns a shown specimen: mixture name, then per phase slot "<label>: <fraction%>" + a colour swatch (FancyBboxPatch) per non-empty phase cell in the phase's display_color (same as its per-phase curve). Always drawn, independent of display_phases. verify_mixture_legend.py
- [x] Convert data to fixed slit / to ADS (2026-08-04) - the two Data-menu actions were dead (defined + in the menu but connected to nothing, no backing op). Now wired: pattern_ops.convert_slit(x, y, to_ads) rescales by sin(theta) (fixed<->ADS divergence geometry; the old Specimen.convert_to_fixed/ads), Specimen.convert_to_fixed/ads apply it, MainWindow._convert_slit confirms then applies to the single selected specimen (added to _data_op_actions so they grey out). verify_convert_slit.py + verify_convert_slit_ui.py
- [x] Save Graph fix (2026-08-05) - the action opened the size dialog but discarded it (no file picker, no save) so OK did nothing. Now MainWindow._save_graph runs the size dialog -> QFileDialog -> PatternPlot.save_figure (PNG/PDF/SVG at the chosen inch size + dpi, on-screen size restored; port of the old save_figure). verify_save_graph.py
- [x] Main window maximizes on startup (2026-08-05) - __main__.main uses window.showMaximized() instead of show(), restoring the old-app behaviour (the .ui's fixed 1280x800 default was not full width on wider screens).
- [x] Shift Pattern reference line (2026-08-05) - the old app's fixed dotted vertical at the reference reflection's target 2theta was never ported (dialog opened, no line). Now ShiftPatternDialog -> MainWindow.set_shift_reference/clear_shift_reference -> PatternPlot draws a dotted teal vertical at get_2t_from_nm(SHIFT_POSITIONS[i], wavelength); fixed against the shift value, clears on Manual/close. verify_shift_reference.py
- [x] Strip Peak / Peak Properties range selection by drag (2026-08-16) - replaced the two eye-dropper Sample buttons (cmd_sample_start/end, one plot click each) with dragging across the pattern, reusing the crosshair drag-highlight. _RangeSelectMixin arms MainWindow.arm_range_pick on show/window-activation (disarms on close); PatternPlot.set_range_select_enabled makes a left-drag highlight the swept span independent of the Crosshair toggle and, on release, on_range_select(plot, x0, x1) fills both start/end spinboxes ascending (still editable). Buttons removed from both .ui; hint label added. verify_range_select.py (19/19).
- [x] Strip Peak "Keep peak %" (2026-08-16) - Strip Peak is now a single operation that attenuates the peak toward the endpoint background line instead of always removing it: pattern_ops.compute_reduce_pattern returns bg_line + keep*(y-bg_line) [+ noise] as a StripPattern (keep=0 flattens like a strip, 1 = unchanged, fractional % allowed, min 0), so the window edges stay on the line = NO background notch (a raw y-scale would suppress the background and leave steps at the edges). The separate "Replace with straight line" mode was dropped as redundant - Keep 0% + noise reproduces it exactly; the noise_level control is retained and auto-estimated on a range change. Reuses apply_strip/preview_strip. verify_strip_reduce.py (24/24).
- [x] Applied goniometer-setup name persists (2026-08-18) - the 4th and last behaviour gap. The name shown on lbl_applied_gonio now survives reopening Edit Specimen and a save/reload, and CLEARS as soon as any goniometer field is hand-edited (a shown name must always mean "these values ARE that setup"). STORED IN specimen.source as a labelled "Goniometer setup: <name>" line, NOT as a Goniometer property: a strict compatibility audit against the old GTK app proved it deserialises every object with cls(**properties) and raises TypeError on ANY unknown key, so a new Goniometer.setup_name would make every MudLab2-saved .mud unreadable there (a new .mud archive entry would too - the loader injects each entry as a Project property). source is a field the old app already has, and where IT kept this same information. models/specimen.py gains goniometer_setup_name()/with_goniometer_setup_name(); GoniometerWidget.bind_goniometer now takes the specimen. COMPATIBILITY AUDIT RESULT: the old app loads a MudLab2 file exercising every MudLab2-only feature (setup name, display_phases, exclusion_ranges, refine_method_index/options, fractions_mask, display_color, *_ref_info) and accepts every object via its own from_json; the ONE break is NonClayPhase, a MudLab2-only TYPE (KeyError there). Note a static key comparison cries wolf (~11 false extras) because the old app accepts many names via pop_kwargs aliases. verify_goniometer_setup 35/35; full suite 68.
- [x] Refine round-two AUDIT (2026-08-18) - 3 real findings FIXED. (1) NAMES ARE NOT UNIQUE: two phases (or two components of one phase) sharing a name had their parameters MERGED into one tree branch, with no way to tell which owned which - Refinable now carries a stable group_key (ids from _phase_refinables) and the tree groups by that, not by the displayed names. (2) The evaluation-budget label CLAIMED A TOTAL it could not deliver: measuring showed scipy's maxfun/maxiter count its own solver steps, not model evaluations, so maxiter=3 produced 28 evaluations against a predicted 9, and the Basin Hopping "total" was worse still (cap 200 -> 89 evaluations where UNCAPPED gave 71, because a local run converges long before the cap). It now states only what is true: the exact parameter count plus each method's own limits, no fabricated totals. The BH cap is KEPT - it still prevents the pathological 15000-per-run case - but is no longer described as a computable budget. (3) The report recomputed every phase's intensities on EVERY write (~0.15 s, 0.47 s per keep); new per_specimen_residuals_from_patterns reads the specimens' current calculated patterns instead - identical to 1e-9, ~1300x faster, keep now 0.31 s. Audited clean otherwise: the tuple path form keeps a pipe-containing phase name intact, inheritance filtering unchanged, leaves/groups still correct. verify_refine_progress_plot 101/101, verify_refinement extended; full suite 68.
- [x] Refine tree follow-ups (2026-08-18) - "Refine" column header spelled out again (costs ~24 px, given back to the name column: tree min 400->425, dialog 1400->1430 / min 1385); Select all + Unselect all now also Expand all, so the result is not hidden behind folded branches; new lbl_selected "N of M selected" beside the instruction above the tree, refreshed by every path that can change a flag (populate, a tick, select/unselect all, _refresh_values after auto-restrict/randomise). Harness now pins L-BFGS-B wherever it RUNS a refinement and restores it after the Basin-Hopping layout check (the method persists on the mixture) - per the user's standing instruction never to drive a UI test with Basin Hopping. verify_refine_progress_plot 88/88; full suite 68.
- [x] Refine dialog: refinables TREE + right-click menu (2026-08-18) - the flat parameter table became a foldable tree, the old app's design (its refinables GtkTreeView had expanders and showed each node's own text_title): a group row per phase, a nested group per component, one leaf per parameter. Refinable now carries group/title (label stays the joined string for the report), so the tree never splits a name on " | ". Opens FOLDED, indentation 12 (Qt default ~20 is too wide for a 3-level tree). Right-click menu on the tree - Expand all / Fold all / Select all / Unselect all / Auto restrict / Randomise - REPLACES the Auto-restrict and Randomize buttons, which are removed; the four model-touching entries grey out while a refinement runs. _tree_menu() builds the menu and _on_tree_menu() shows it, split so a harness can inspect it without entering a modal exec() loop (patching QMenu.exec does NOT work - it is a C++ slot, and the harness hung on a real modal menu). The three keep buttons are now side by side. GOTCHAS found by rendering: leaves need ItemIsUserCheckable or the Refine box does not draw at all, and header.setStretchLastSection(False) is required because Qt stretches the last section by default and, with the name column also stretching, that leaves a permanent horizontal scrollbar. WIDTH: the tree frees the name column (it held full paths needing 432-564 px, now group names ~150), but the FOUR NUMERIC COLUMNS were the real floor at ~370 px - compacting them (fixed 72 px Value/Min/Max, "Ref." header) took the tree from 468 to 414 px and the dialog default from 1440 to 1400 (minimum 1360, still binding). Frame 2 (592 px) is now the widest panel and sets the floor, so further narrowing means shrinking the plot or moving the options. verify_refine_progress_plot 79/79; full suite 68 harnesses.
- [x] Refine report/UI AUDIT (2026-08-18) - 1 real bug FIXED: the report said "Applied: nothing yet" on finish and withheld the validation section, but refine_mixture LEAVES THE MODEL AT THE BEST SOLUTION (verified: the refinables equal best_solution when the finished handler runs). It now reports "Best solution (left by the refinement)" vs "(kept)" after a button, and validation appears on finish - restoring old-app parity, since the old app validated right after its own apply_best_solution(). Also compacted the tabular charge-balance line to the 64-col report width. Audited CLEAN otherwise: cancelled runs note the cancel; a second run clears and rewrites (single Time line, new progress series); no-refiner / empty-series / single-point cases are safe; 5000 evaluations thin to 20 rows; raw phases + empty cells validate without crashing; and at the 1350x580 minimum every frame fits (table and report inside their frames, plot and buttons visible). verify_refine_progress_plot 56/56 - the new report: checks drive a REAL short refinement, with the method pinned to L-BFGS-B because the dialog REMEMBERS the method and Basin Hopping "iterations" are full restarts (that cost minutes before pinning). verify_validation 17/17; full suite 68 harnesses.
- [x] Refine-mixture dialog: DETAILED REPORT (2026-08-18) - ports the old app's txt_refine_log / RefinerController.populate_log into txt_report, a read-only fixed-pitch QPlainTextEdit under the three Keep buttons in frame 3. _write_report fills it when a run FINISHES and again on every _on_apply, so it always describes the solution currently applied (GoF recomputed from the freshly calculated patterns). Contents: method, parameter count, elapsed time (new _refine_started/_elapsed), which solution is applied, a per-parameter Initial/Best/Last table, residuals + GoF, and a progress log. Two deliberate differences from the old app: the old per-ITERATION log becomes the per-EVALUATION progress series (record_history stays OFF so a long run cannot grow unbounded), thinned to _MAX_PROGRESS_ROWS evenly spaced rows; and the AUDIT corrected the "Applied" line: refine_mixture LEAVES THE MODEL AT THE BEST SOLUTION (normally and on cancel), so the on-finish report says "Best solution (left by the refinement)" - an earlier version said "nothing applied yet" and withheld the validation section that the old app showed at exactly that point; keeping a solution flips it to "(kept)". The three buttons are now labelled Initial / Best / Last (the "Keep" wording moved to the lblKeepWhich prompt). Frame 3 widened (min 300, horstretch 3) and the dialog minimum re-bound to 1350 (layout minimum 1344) so nothing clips.
- [x] Post-refinement VALIDATION (2026-08-18) - calculations/validation.py + Component.compute_charge_balance (verbatim port of the old model method), appended to the refinement report once a solution is applied; read-only. Ports the old _build_validation_report: AtomRatio value must be in [0, 1], Al-for-Si substitution must satisfy Loewenstein (<= 0.5), no pn may be negative - each is something a refinement CAN cause, since nothing in a parameter's Min/Max box constrains chemistry. DELIBERATE DIVERGENCE: charge balance is REPORTED, not judged. atom_type.charge is the SCATTERING ion of the type, not a formal charge (stock Kaolinite = Al1.5+ / Si2+ / O1- / OH1-, summing to net -4 BY CONSTRUCTION), so the old app's |net| > 0.05 warning flagged every standard clay on every project, refined or not, and buried the checks that mean something; the per-component numbers are still printed and still marked balanced/not, they just do not count towards the verdict. component_charge_balance_finding documents the one-line revert to strict parity. verify_validation.py 17/17 (each failure mode fires, a stock fixture stays quiet, nothing is mutated).
- [x] Refine-mixture dialog: THREE-FRAME layout (2026-08-16) - was one tall QVBoxLayout stack; now a wide row of three group boxes (framesRow) plus a dialog-wide bottom bar. Frame 1 grpParameters "1. Parameters to refine" = tbl_refinables + Auto-restrict/Randomize; frame 2 grpRefine "2. Refinement" = method combo + Refine/Cancel (top row), the per-method options grid (2 label+spin pairs per row, so maxfun/maxiter read side by side and Basin Hopping's three wrap), then grpProgress with the convergence plot; frame 3 grpResult "3. Result" = the four residual/GoF readouts + the three Keep buttons stacked; bottomRow = lbl_status (left) + Close (right). Proportions via each frame's sizePolicy horstretch 5/4/2 (the layout `stretch` property is mis-generated by pyside6-uic as a translated string - do not use it). Default 1360x680, minimum 1310x580 chosen to sit just above the layout's own 1304 minimum so it BINDS and no frame can be squeezed into clipping. Supporting fixes found by measuring: progress Figure figsize 4.0->2.2 (a FigureCanvas's sizeHint is figsize x dpi = ~560 px, which made the middle frame hog the row and pushed the table into a horizontal scrollbar); parameter names elide on one line (wordWrap off + ElideRight) with a full-text tooltip, since word wrap doubled every row height and halved how many of ~42 parameters were visible; option labels shortened to "Function calls"/"Iterations" with _OPTION_TOOLTIPS for precision. The dialog was ALREADY modal via exec(); the .ui now also says modal: true. verify_refine_progress_plot.py 34/34 (14 new `layout:` checks pin frame membership, side-by-side order, the wrapping options grid and no-clipping-at-minimum).
- [x] Mixture legend: SHOWN-ONLY swatches (2026-08-16) - the upper-right phase index drew one colour-swatch column per specimen OF THE MIXTURE, shown or not, so a multi-specimen mixture put up swatches for curves the user could not see. PatternPlot._draw_mixture_legend now builds its columns from the mixture's DISPLAYED specimens only (shown_rows, matched by id() - Specimen has no __eq__ and two specimens must never collapse into one column); the mixture name, slot labels and fractions are still listed in full, since they belong to the mixture and not to the selection. The old harness passed either way (its fixture shows ALL of the mixture's specimens), so the swatch check now counts per shown row and a subset check asserts one specimen draws its row only (4 swatches vs 12 for the full selection). verify_mixture_legend.py 13/13.
- [x] Remove Background / Smooth / Add Noise are MODELESS (2026-08-16) - they went through MainWindow._run_data_op -> exec(), which froze the plot so their live preview could not be zoomed into to judge it (Strip Peak / Shift / Peak Properties were already modeless). New _show_data_op mirrors those: one tracked instance per class in _data_op_dialogs, closed + rebuilt per open so it binds the CURRENT selection rather than a stale specimen. No WA_DeleteOnClose - the tracked reference is close()d on re-open and deleting the C++ object under it would turn that into a crash. The one shared plot preview overlay means the last parameter change wins when two are open (pre-existing limit). verify_data_op_dialogs.py 61/61 (new `modeless:` checks drive the real MainWindow: not modal, visible without exec, bound specimen, re-open replaces, preview reaches the real plot + clears on close, no selection opens nothing).
- [x] NonClayPhase path-2 (c)/(f)/(w) AUDIT (2026-08-16) - audited the three deferred items for correctness; 3 real bugs FIXED. (w) the Caglioti fit cold-started Nelder-Mead at shift 0 with a 0.00025 deg initial step (< a peak width), so a DISPLACED standard scan converged into a neighbouring-peak minimum and silently returned a nonsense width (+0.08 deg -> width wrong by 0.12 deg; +0.30 deg -> ran to the shift bound, residual 0.99) - it is now warm-started from the constant-FWHM fit (which finds the displacement with a bounded search), falls back to that fit's (0,0,FWHM^2) when it cannot beat it, honours fit_shift/bounds (both were silently ignored) and keeps the width inside bounds across the fit window (it used to be able to collapse the peaks to the 1e-3 deg render floor). (f) the tokenizer merged digit-dot-digit, so segment notation silently lost its multipliers (K2O.Al2O3.6SiO2 -> SiO2 23.4 instead of 64.8) and a leading coefficient was dropped (3CaO.Al2O3) - the '.' reading is genuinely ambiguous vs a decimal subscript (Si2.5), so parse_formula gained dot_as_separator + formula_dot_is_ambiguous (only flags inputs where the two readings differ - a hydrate does not, its water is dropped) and the oxide grid asks; leading coefficients now multiply their own segment only. (c) a non-reporting oxide key was counted in the phase's own total, shrinking its share of its own fraction. Also: an explicit fwhm= now overrides a stored Caglioti in render_on_grid, the editor shows the mid-angle width when re-binding a Caglioti phase, and the bulk-vs-clay-only weighting difference (~1 wt%) is documented in the chk_bulk tooltip. verify_nonclay_phase 67/67, verify_nonclay_calibration 31/31, verify_composition 36/36; full suite 67/67 harnesses.
- [x] NonClayPhase path-2 PHASE B: FWHM calibration from a standard (2026-08-16) - fit the instrumental peak width by matching a standard's computed pattern to a measured scan. nonclay_calibration.py: built-in Silicon standard (silicon_reflections, embedded Si CIF via structure.reflections_from_cif_text) + calibrate_fwhm (nested 1-D fit of FWHM AND a 2theta zero-shift so displacement does not inflate the width, per-trial linear scale+background). CalibrateFwhmDialog (ui/calibrate_fwhm.ui): pick standard (Silicon default or a CIF) + open a measured scan + Fit -> FWHM/shift/residual + measured-vs-fitted overlay; a "Calibrate..." button in the editor FWHM row (computed phases only) applies it, and an "Apply to all computed non-clay phases" checkbox emits EditNonClayPhaseWidget.apply_fwhm_to_all -> EditPhasesDialog._apply_fwhm_to_all sets every computed NonClayPhase (instrumental width is shared). Bonus: _reflections_and_oxides now drops systematically-absent/negligible reflections. verify_nonclay_calibration.py 15/15 + verify_nonclay_phase.py 50/50. Isolation guard sanctions the 3 path-2 nonclay importers.
- [x] NonClayPhase path-2 (w) CAGLIOTI ANGLE-DEPENDENT WIDTH (2026-08-16) - a computed NonClayPhase can carry a Caglioti width (U,V,W): FWHM(theta)^2 = U*tan^2 + V*tan + W, instead of one constant FWHM. NonClayPhase.caglioti (optional; None = constant), fwhm_at(2theta), render_on_grid uses per-reflection width, round-trips in .mud (a phase without caglioti stays constant - clean migration); set_fwhm() reverts to constant. Calibration: calibrate_fwhm(..., caglioti=True) fits (U,V,W)+shift via Nelder-Mead (FwhmCalibration.caglioti); the Calibrate dialog gains a "Fit angle-dependent width (Caglioti)" checkbox; the editor applies it (spinbox shows a mid-angle width, a read-only lbl_caglioti shows U/V/W; editing the constant FWHM reverts), with apply_caglioti_to_all -> EditPhasesDialog._apply_caglioti_to_all across all computed phases. verify_nonclay_calibration.py 19/19 + verify_nonclay_phase.py 64/64; no regressions. Path-2 deferred backlog now EMPTY.
- [x] NonClayPhase path-2 (f) FORMULA PARSER (2026-08-16) - the oxide grid gets a "Fill from formula" input: calculations/composition.parse_formula(formula) parses a chemical formula (elements + counts + parentheses + hydrate dots, e.g. NaAlSi3O8, CaMg(CO3)2, CaSO4.2H2O) into element counts, converts each element to its reporting oxide via the conversion table (element mass x factor) and normalises to 100%. Only the 7 reporting cations (Si/Al/Fe/Ca/Mg/Na/K) map to oxides; H/C/O and other cations (Ti/Mn/S...) are dropped (the oxide set is 7-wide). OxideGrid.fill_from_formula centralises parse+fill (shared by the import dialog + the editor via edit_formula/button_formula in each .ui); an unconvertible formula shows an info message, grid unchanged. Validated vs albite/orthoclase/calcite/dolomite/gypsum. verify_composition.py 27/27 + verify_nonclay_phase.py 53/53. Deferred still: (w) Caglioti width.
- [x] NonClayPhase path-2 (c) BULK COMPOSITION (2026-08-16) - non-clay phases now contribute to composition, additively. calculations/composition.bulk_composition(mixture) = each phase's own oxide composition normalised to 100% weighted by its fraction (clay Phase from atoms via _clay_oxide_masses; NonClayPhase from its stored oxides), a semi-quant fraction-weighted average (fractions are the same non-rigorous amounts clay-only uses - no ZMV; a mass-weighted bulk would need per-phase molecular weights = the (f) formula parser). SEPARATE function: clay-only mixture_composition + the XRF mass balance (nonclay/chemistry.py) are UNCHANGED. CompositionDialog gets an "Include non-clay phases (bulk)" checkbox (chk_bulk), enabled only when mixture_has_nonclay(mixture); default clay-only. verify_composition.py 20/20; no regressions (nonclay 32/32, calc_engine 23/23). Deferred still: (f) formula parser, (w) Caglioti width.
- [x] NonClayPhase path-2 PHASE A: live width tuning + specimen-wavelength render (2026-08-16) - a COMPUTED (CIF) NonClayPhase now stores its reflections as (d_angstrom, intensity) (nonclay.structure.reflections_from_cif) + a tunable fwhm, instead of a baked 2theta curve. phases.get_diffracted_intensity renders a computed phase from those AT THE SPECIMEN WAVELENGTH (recovered from range_stl via _wavelength_from_stl) broadened to fwhm - so positions + width are specimen-consistent, like a structural Phase but from a fixed stick list (never refined). NonClayPhase.render_on_grid/preview_pattern/rebuild_stored_pattern; is_computed splits computed vs measured (measured falls back to _get_raw_intensity). Editor gains a Peak FWHM spinbox shown only for computed phases (setRowVisible on is_computed); changing it re-renders + recomputes (unlike oxide edits). Import renders a live CIF preview at spin_fwhm (default 0.10). reflections + fwhm round-trip in .mud; a pre-phase-A baked phase (no reflections) stays baked on load. verify_nonclay_phase.py 36/36; verify_nonclay isolation guard updated to sanction import_nonclay_dialog.py (32/32). DEFERRED: composition (c), formula parser, FWHM calibration from a standard (phase B).
- [x] NonClayPhase / Import Non-Clay ("path 2", 2026-08-16) - a new phase type "NonClayPhase" = a RawPatternPhase (stored pattern) that ALSO carries an oxide composition. Behaviour is type-gated: (a) contributes its pattern + its fraction is optimised (get_diffracted_intensity dispatches it to _get_raw_intensity), (b) never structurally refined (enumerate_refinables only takes type=="Phase" - free), (c) contributes to composition = DEFERRED (oxides stored/editable now; a bulk composition is a follow-up, kept additive so clay-only mixture_composition + the XRF mass balance stay intact). New: models/nonclay_phase.py, oxide_grid.py (shared oxide->wt% grid, spinboxes min 0), import_nonclay_dialog.py + ui/import_nonclay.ui ("Import Non-Clay" button in the Edit Phases objects frame -> measured pattern via import_pattern OR CIF-with-atoms via nonclay.structure.reference_from_cif -> pattern+oxides; name/colour/preview/validation), edit_nonclay_phase_widget.py + ui/edit_nonclay_phase.ui (right-side editable oxide grid). Loader + _MODELED persist it. composition.reporting_oxides() helper. Formula parser DEFERRED. verify_nonclay_phase.py (26/26). Promoted to a mainstream feature 2026-08-16.
- [x] Edit Phases Import filter (2026-08-05) - PHS_FILTERS dropped the misleading "All files (*.*)" option (import reads only .phs; export always writes .phs). verify_phs_import.py guards it.
- [x] Imported/added specimen goniometer (2026-08-05) - Specimen.__init__ left goniometer=None, so import + Add specimen produced a specimen with no goniometer and Edit Specimen greyed the whole Goniometer tab. Now defaults Goniometer() (CuKα; a .mud load overwrites it); tab is editable. verify_specimen_goniometer.py.
- [x] Import specimen Source box + metadata (2026-08-05) - the General-tab Source box was empty after import. Now import fills specimen.source via xrd_import.build_source_string (File + 2theta range/step/points for any format) + parse_pattern_metadata; the file's Ka1 wavelength is applied to the goniometer. Metadata readers: .xrdml (wavelength / count time / sample / date / radius) + .rasx (wavelength / X-ray tube target+kV+mA / date / scan speed, from Data*/MesurementConditions*.xml) + .uxd (_WL1/_WL2 per _WL_UNIT, _ANODE, _KV/_MA, _STEPTIME, _DATEMEASURED, _GONIOMETER_RADIUS) + Bruker .raw (count time RAW1+RAW3; RAW1 alpha1/alpha2 wavelength). Rigaku 'FI' .raw stays axis-only (header not reverse-engineered). verify_import_source.py (44/44). CPS FIX (2026-08-05): RAW1 now normalises to counts-per-second by its time_step (was raw counts - old-app oversight); RAW3/.xrdml/.uxd already did. STILL OPEN: applying slit/radius geometry (only reported, not applied); RAW3 wavelength offset (not located); RAW2 count time offset (RAW2 stays counts).
- [x] Specimen.source .mud round-trip (2026-08-05) - _specimen_to_dict popped 'source' (wrong comment - the old app HAS a source property) and it was absent from SPECIMEN_PROPS, so the Source box was never saved. Added to SPECIMEN_PROPS + dropped the pop; round-trips + old-app compatible. verify_import_source.py.
- [x] Splash screen - splash.py + ui/splash.ui (SplashScreen), shown by __main__.main while the window builds, auto-closes after a ~700ms minimum. Branded teal-slate bg + reused icon + gold version number to distinguish this Qt build from the old GTK MudLab. verify_splash.py

### Not planned
- Behaviours (add_behaviour.glade, edit_insitu_behaviour.glade) - feature
  was disabled in the old app; revisit only if revived.
- edit_dialog.glade, none.glade, inline_ols.glade, shift_dialog.glade -
  GTK plumbing with no Qt equivalent needed (QDialog with button box,
  empty-selection state, and plain QTreeView cover these).
