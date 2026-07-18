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
  Phase-cell reassignment and structural add/remove are disabled here; the
  Optimize button + auto-* flags were wired later (see the L-BFGS-B optimizer
  entry below), and the full Refine window is still deferred.
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
| Edit Phases | edit_phase.ui, edit_phase_widget.py, edit_phases_dialog.py, csds.ui/csds_widget.py, probabilities.ui/probabilities_widget.py, edit_component.ui/component_widget.py, atom_list.ui/atom_list_widget.py | phases/glade/phase.glade + csds/probabilities/component/layer.glade + shell | partial (bound to real Phase models; name/sigma*/CSDS-mean + R0 F params + component c-axis scalars + layer/interlayer atoms editable with live recalc; Add (empty phase, G blank components) + Remove (cascades based_on/linked_with/mixture refs) wired; unit-cell a/b, phase inheritance, colour, Import/Export (.phs) still to wire) |
| Edit Atom Types | edit_atom_type.ui, edit_atom_type_widget.py, edit_atom_types_dialog.py | atoms/glade/atoms.glade + shell | done (real AtomType models from the .mud; live real ASF plot) |
| About box | QMessageBox.about placeholder | about_window in application.glade | partial (branding: logo, icons, version) |
| Edit Mixtures | edit_mixture.ui, edit_mixture_widget.py, edit_mixtures_dialog.py | mixture/views/glade/edit_mixture.glade + shell | done (bound to the Mixture model; fractions/scales/background editable with live recalc; Optimize runs the L-BFGS-B refinement with a live residual label; Refine opens the Refinement window; auto_run/scales/bg live. Phase-cell reassign, structural add/remove, composition still to wire) |
| Refinement window | refinement.ui, refinement_dialog.py | refinement/views/glade/refinement.glade + refine_results.glade | done (refinable tree with flags/bounds, method combo + per-method options, auto-restrict/randomize, threaded Refine + Cancel + live status, Initial/Best/Last + GoF results with keep-buttons). Deferred: the progress/parameter-space plot only |
| Add Phase dialog | add_phase.ui, add_phase_dialog.py | phases/glade/addphase.glade | done (empty phase; R0 with G 1-6, or R1 which locks G=2 = only R1G2 modeled; R2+ unported; default-catalog + raw-pattern options honestly disabled; wired to Edit Phases Add) |
| Goniometer component | goniometer.ui, goniometer_widget.py | goniometer/glade/goniometer.glade | done (plugged into Edit Specimen; wavelength-distribution editor still to do) |
| Remove Background | background.ui, line_dialogs.py | generic/views/glade/lines/background.glade | done (applies: linear + pattern bg, pattern interpolated onto the specimen grid) |
| Smooth Data | smoothing.ui, line_dialogs.py | lines/smoothing.glade | done (applies: all 6 types; Show Original overlay needs the plot-controller port) |
| Shift Pattern | shifting.ui, line_dialogs.py | lines/shifting.glade | done (applies: auto-detect vs reference + manual; linear/displacement) |
| Add Noise | add_noise.ui, line_dialogs.py | lines/add_noise.glade | done (applies) |
| Strip Peak | strip_peak.ui, line_dialogs.py | lines/strip_peak.glade | done (applies; modeless; Sample buttons pick start/end; live plot preview needs the plot-controller port) |
| Peak Properties | peak_properties.ui, line_dialogs.py | lines/peak_properties.glade | done (live area/FWHM; read-only; modeless; Sample buttons + copy-to-clipboard) |
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
- [ ] Edit Atom Ratio dialog - phases/glade/ratio.glade (modal). **Batch 2a
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
  atom lists refresh. AtomContents / chained relations are listed but not
  editable yet (Batch 3); inherited relations are read-only. Also fixed the
  audit's atom-pn -> UCP gap: `_on_atoms_changed` now calls `update_ucp_values`.
- [x] Edit Atom Contents dialog - phases/glade/contents.glade. **Batch 3:**
  AtomContents (models/atom_relations.py: AtomContents + AtomContent rows) scales
  a set of atoms by one value - `atom.pn = amount*value` per row (interlayer K /
  Ca / H2O content). Modeled + golden-safe (resolved but not applied on load).
  Editor: contents.ui + contents_widget.py (name, enabled, value + a table of
  atom/amount rows with Add/Remove), embedded in the component editor's Atom
  relations group next to the AtomRatio editor (one shown per selected relation;
  "Add contents" button). Editing re-applies + cascades pn -> cell_b -> cell_a.
  Chained rows (`prop` = "value"/"__internal_sum__") are preserved but not
  listed; inherited relations read-only. Harness: verify_relations.py extended.
- [ ] Raw pattern phase editor - phases/glade/raw_pattern_phase.glade

### Markers (done - editors)
- [x] Edit Markers window - edit_markers_dialog.py (object-store shell + find peaks / match minerals extra row); EditMarkersView
- [x] Edit Marker fields - edit_marker.ui, edit_marker_widget.py (specimen/glade/edit_marker.glade)
- [x] Detect peaks - find_peaks_dialog.ui, detect_peaks_dialog.py (threshold histogram placeholder; detection with the calc-engine port)
- [x] Match minerals - match_minerals.ui, match_minerals_dialog.py (placeholder mineral list; auto-match/append with the mineral-reference port)

### Goniometer
- [ ] Wavelength distribution editor - goniometer/glade/wavelength_distribution.glade (opened by the goniometer component's Edit emission spectrum button)

### Mixtures
- [ ] Add Mixture dialog - mixture/views/glade/add_mixture.glade (for the Edit Mixtures shell's Add button)
- [ ] Composition summary - opened by btn_composition in the mixture editor

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
- [ ] Phase-intensity cache (deferred perf, user-deferred): the old
  calculations/phases._phase_intensity_cache + its "use intensity cache"
  checkbox were never ported. Re-adding it (keyed by phase params, always-on,
  bounded like _csds_cache) would speed up refining multi-phase mixtures where
  only some phases are flagged (the unchanged phases would cache-hit each
  outer trial). Not essential; no checkbox needed.

### Other
- [ ] CSV import options - generic/views/glade/csv_import.glade
- [x] Specimens context menu - main_window `_build_specimens_menu` (Add/Import, Edit specimen, Edit markers, View statistics, Remove specimen; per-specimen items need a single selection)
- [ ] About dialog branding + window/app icons - application/icons/
- [ ] Splash screen - application/splash.py (optional)

### Not planned
- Behaviours (add_behaviour.glade, edit_insitu_behaviour.glade) - feature
  was disabled in the old app; revisit only if revived.
- edit_dialog.glade, none.glade, inline_ols.glade, shift_dialog.glade -
  GTK plumbing with no Qt equivalent needed (QDialog with button box,
  empty-selection state, and plain QTreeView cover these).
