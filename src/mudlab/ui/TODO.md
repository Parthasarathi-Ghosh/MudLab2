# GUI port checklist: dialogs & windows

Status of every window/dialog/component being recreated from the GTK
MudLab (`C:\GitHub\MudLab`, glade files under `...\site-packages\mudlab\`).

**Keep this file current: update it whenever a component is added,
completed, or descoped.** Wiring details live in [WIRING.md](WIRING.md).

Legend: **done** = .ui + logic exist and are wired for GUI trial;
**partial** = done but contains placeholder slots for missing
sub-components.

Model status (2026-07-06): Project + Specimen Qt-signal models exist
(mudlab/models/); the specimens dock, plot stack, window title, Edit
Project and Edit Specimen dialogs are live against them, and Import
Specimens loads real text XY/CSV patterns. Phases, mixtures, atom
types, goniometer, markers, and project save/load are still
placeholder-driven.

## Recreated

| Component | New files | Old source | Status |
|---|---|---|---|
| Main window | main_window.ui, main_window.py | application/glade/application.glade | done (plot stack, specimens dock, menus/toolbar; plot controller port pending) |
| Edit Project | edit_project.ui, edit_project_dialog.py | project/glade/project.glade (nbk_edit_project) | done (layout-mode combo is temporary) |
| Edit Specimen | edit_specimen.ui, edit_specimen_dialog.py | specimen/glade/specimen.glade | done (hosts line properties + goniometer components) |
| Line properties (reusable) | line_properties.ui, line_properties_widget.py | generic/views/glade/lines/experimental_props.glade + calculated_props.glade | done |
| Object store shell (reusable) | object_store.ui, object_store_dialog.py | generic/views/glade/object_store.glade | done (buttons not yet connected) |
| Edit Phases | edit_phase.ui, edit_phase_widget.py, edit_phases_dialog.py | phases/glade/phase.glade + shell | partial (CSDS, probabilities, components tabs are placeholders) |
| Edit Atom Types | edit_atom_type.ui, edit_atom_type_widget.py, edit_atom_types_dialog.py | atoms/glade/atoms.glade + shell | done (live scattering-factor plot; synthetic demo coefficients) |
| About box | QMessageBox.about placeholder | about_window in application.glade | partial (branding: logo, icons, version) |
| Edit Mixtures | edit_mixture.ui, edit_mixture_widget.py, edit_mixtures_dialog.py | mixture/views/glade/edit_mixture.glade + shell | done (placeholder read-only matrix; editable combos-per-cell matrix comes with the model port) |
| Add Phase dialog | add_phase.ui, add_phase_dialog.py | phases/glade/addphase.glade | done (G 1-6, R 0-4; placeholder default-phase catalog; wired to Edit Phases Add button) |
| Goniometer component | goniometer.ui, goniometer_widget.py | goniometer/glade/goniometer.glade | done (plugged into Edit Specimen; wavelength-distribution editor still to do) |
| Remove Background | background.ui, line_dialogs.py | generic/views/glade/lines/background.glade | done (op applies with model port) |
| Smooth Data | smoothing.ui, line_dialogs.py | lines/smoothing.glade | done (op applies with model port) |
| Shift Pattern | shifting.ui, line_dialogs.py | lines/shifting.glade | done (reference presets working; op applies with model port) |
| Add Noise | add_noise.ui, line_dialogs.py | lines/add_noise.glade | done (op applies with model port) |
| Strip Peak | strip_peak.ui, line_dialogs.py | lines/strip_peak.glade | done (eye-dropper sampling with plot-controller port) |
| Peak Properties | peak_properties.ui, line_dialogs.py | lines/peak_properties.glade | done (copy-to-clipboard working; computation with model port) |
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

### Markers
- [ ] Edit Markers window - EditMarkersView (specimen/views/markers.py)
- [ ] Edit Marker dialog - specimen/glade/edit_marker.glade
- [ ] Detect peaks - specimen/glade/find_peaks.glade + find_peaks_dialog.glade
- [ ] Match minerals - specimen/glade/match_minerals.glade

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
- [ ] Specimens context menu - specimen_popup in project/glade/project.glade (on the specimens dock tree)
- [ ] About dialog branding + window/app icons - application/icons/
- [ ] Splash screen - application/splash.py (optional)

### Not planned
- Behaviours (add_behaviour.glade, edit_insitu_behaviour.glade) - feature
  was disabled in the old app; revisit only if revived.
- edit_dialog.glade, none.glade, inline_ols.glade - GTK plumbing with no
  Qt equivalent needed (QDialog, empty-selection state, and plain
  QTreeView cover these).
