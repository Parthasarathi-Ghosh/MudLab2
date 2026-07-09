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
goniometers). Phases, mixtures, atom types, and goniometer remain
placeholder-driven in their editors.

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
- [ ] Batch 2: goniometer model + Lorentz-polarization/absorption factors
- [ ] Batch 3: component structure factor (unit cell + layer/interlayer atoms)
- [ ] Batch 4: CSDS distribution + stacking probabilities (Markovian)
- [ ] Batch 5: phase intensity (recursive stacking)
- [ ] Batch 6: mixture -> specimen calculated pattern + Calculate action
- [ ] exclusion-range masking of the R-factors (needs exclusion-range model)

## Recreated

| Component | New files | Old source | Status |
|---|---|---|---|
| Main window | main_window.ui, main_window.py | application/glade/application.glade | done (plot stack, specimens dock, menus/toolbar; plot controller port pending) |
| Edit Project | edit_project.ui, edit_project_dialog.py | project/glade/project.glade (nbk_edit_project) | done (layout-mode combo is temporary) |
| Edit Specimen | edit_specimen.ui, edit_specimen_dialog.py | specimen/glade/specimen.glade | done (hosts line properties + goniometer components) |
| Line properties (reusable) | line_properties.ui, line_properties_widget.py | generic/views/glade/lines/experimental_props.glade + calculated_props.glade | done |
| Object store shell (reusable) | object_store.ui, object_store_dialog.py | generic/views/glade/object_store.glade | done (buttons not yet connected) |
| Edit Phases | edit_phase.ui, edit_phase_widget.py, edit_phases_dialog.py | phases/glade/phase.glade + shell | partial (CSDS, probabilities, components tabs are placeholders) |
| Edit Atom Types | edit_atom_type.ui, edit_atom_type_widget.py, edit_atom_types_dialog.py | atoms/glade/atoms.glade + shell | done (real AtomType models from the .mud; live real ASF plot) |
| About box | QMessageBox.about placeholder | about_window in application.glade | partial (branding: logo, icons, version) |
| Edit Mixtures | edit_mixture.ui, edit_mixture_widget.py, edit_mixtures_dialog.py | mixture/views/glade/edit_mixture.glade + shell | done (placeholder read-only matrix; editable combos-per-cell matrix comes with the model port) |
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
- [ ] CSDS distribution component - phases/glade/csds.glade (param rows + matplotlib histogram; plugs into Edit Phases tab)
- [ ] Probabilities component - probabilities/glade/probabilities.glade + matrix.glade + R0_independents.glade (plugs into Edit Phases tab; old app removed the tab for R0/G1 phases)
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
