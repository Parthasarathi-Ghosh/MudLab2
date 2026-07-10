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
  Phase-cell reassignment, structural add/remove and the optimizer
  (Refine / Optimize / auto-*) are disabled - later batches.
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
- [ ] Batch 4: Edit Phases components (d001, atoms, unit cell)

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
  groundwork only - the component editor UI is wired with the phase-editor
  port, so phases/components still save verbatim. Verified against the
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
- [ ] exclusion-range masking of the R-factors (needs exclusion-range model)
- [ ] mixture fraction/scale/bg-shift refinement (L-BFGS-B optimizer) -
  the Refinement window family; the calc path above only re-applies the
  stored solution (non-optimising), which is what the graph shows.

Regression harness: `tools/verify_calc_engine.py` recomputes the sample
projects and diffs the result against the calculated pattern the old GTK
app stored in the .mud (the gold standard) - run it after touching any
calc-engine file. `./python/python.exe tools/verify_calc_engine.py`
(exit 0 = within tolerance, 1 = regression, 2 = no samples found; pass
.mud paths to point at other projects).

## Recreated

| Component | New files | Old source | Status |
|---|---|---|---|
| Main window | main_window.ui, main_window.py | application/glade/application.glade | done (plot stack, specimens dock, menus/toolbar; plot controller port pending) |
| Edit Project | edit_project.ui, edit_project_dialog.py | project/glade/project.glade (nbk_edit_project) | done (layout-mode combo is temporary) |
| Edit Specimen | edit_specimen.ui, edit_specimen_dialog.py | specimen/glade/specimen.glade | done (hosts line properties + goniometer components) |
| Line properties (reusable) | line_properties.ui, line_properties_widget.py | generic/views/glade/lines/experimental_props.glade + calculated_props.glade | done |
| Object store shell (reusable) | object_store.ui, object_store_dialog.py | generic/views/glade/object_store.glade | done (buttons not yet connected) |
| Edit Phases | edit_phase.ui, edit_phase_widget.py, edit_phases_dialog.py, csds.ui, csds_widget.py, probabilities.ui, probabilities_widget.py | phases/glade/phase.glade + csds.glade + probabilities.glade + shell | partial (bound to real Phase models; name/sigma*/CSDS-mean + R0 F params editable with live recalc; components tab, inheritance, colour, Add/Remove still to wire) |
| Edit Atom Types | edit_atom_type.ui, edit_atom_type_widget.py, edit_atom_types_dialog.py | atoms/glade/atoms.glade + shell | done (real AtomType models from the .mud; live real ASF plot) |
| About box | QMessageBox.about placeholder | about_window in application.glade | partial (branding: logo, icons, version) |
| Edit Mixtures | edit_mixture.ui, edit_mixture_widget.py, edit_mixtures_dialog.py | mixture/views/glade/edit_mixture.glade + shell | done (bound to the Mixture model; fractions/scales/background editable with live recalc; phase-cell reassign + structural edits + optimizer disabled, come with later batches) |
| Add Phase dialog | add_phase.ui, add_phase_dialog.py | phases/glade/addphase.glade | done (G 1-6, R 0-4; placeholder default-phase catalog; wired to Edit Phases Add button) |
| Goniometer component | goniometer.ui, goniometer_widget.py | goniometer/glade/goniometer.glade | done (plugged into Edit Specimen; wavelength-distribution editor still to do) |
| Remove Background | background.ui, line_dialogs.py | generic/views/glade/lines/background.glade | done (op applies with model port) |
| Smooth Data | smoothing.ui, line_dialogs.py | lines/smoothing.glade | done (op applies with model port) |
| Shift Pattern | shifting.ui, line_dialogs.py | lines/shifting.glade | done (reference presets working; op applies with model port) |
| Add Noise | add_noise.ui, line_dialogs.py | lines/add_noise.glade | done (op applies with model port) |
| Strip Peak | strip_peak.ui, line_dialogs.py | lines/strip_peak.glade | done (modeless; Sample buttons pick start/end on the plot; strip op with model port) |
| Peak Properties | peak_properties.ui, line_dialogs.py | lines/peak_properties.glade | done (modeless; Sample buttons + copy-to-clipboard; area/FWHM computation with model port) |
| Trim Data | trim_dialog.ui, specimen_dialogs.py | specimen/glade/trim_dialog.glade | done (op applies with model port) |
| Statistics | statistics.ui, specimen_dialogs.py | specimen/glade/statistics.glade | done (unwired until the specimens context menu exists) |
| Save Graph size | save_graph_size.ui, specimen_dialogs.py | specimen/glade/save_graph_size.glade | done (runs before the native save dialog; export with plot-controller port) |

## To do

### Phase editing family
- [x] CSDS distribution component - csds.ui + csds_widget.py (mean spinbox +
  live log-normal histogram + derived range; plugged into Edit Phases CSDS
  tab, bound to DritsCSDSDistribution). Old: phases/glade/csds.glade.
- [x] Probabilities component - probabilities.ui + probabilities_widget.py
  (R0 only: editable (G-1) F spinboxes + read-only W/P tables, built
  dynamically; tab shown only for G>=2). Old: probabilities/glade/
  probabilities.glade + matrix.glade + R0_independents.glade. R1-R3 Markovian
  models come when a project needs them.
- [ ] Component editor - phases/glade/component.glade (plugs into Edit Phases Components tab)
- [ ] Unit cell property editor - phases/glade/unit_cell_prop.glade (inside component editor)
- [ ] Layer / interlayer atom lists - phases/glade/layer.glade (inside component editor)
- [ ] Edit Atom Ratio dialog - phases/glade/ratio.glade (modal)
- [ ] Edit Atom Contents dialog - phases/glade/contents.glade (modal)
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

### Refinement
- [ ] Refinement window - refinement/views/glade/refinement.glade
- [ ] Refine method options - refinement/views/glade/refine_method.glade
- [ ] Refinement results - refinement/views/glade/refine_results.glade
- [ ] Refinement status - refinement/views/glade/refine_status.glade

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
