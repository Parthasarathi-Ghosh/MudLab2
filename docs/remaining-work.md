# MudLab2 — remaining & deferred work

Snapshot as of 2026-08-01 (V1 in sync with origin @ `1f0e4bb`). The GTK→Qt/PySide6
port is far along: the analytics/calc
engine is golden-validated, both major editors (Edit Phases, Edit Mixtures) are
feature-complete, and the default-phase catalog now matches old MudLab/PyXRD (80
entries, all R0–R3 models). This is the single canonical to-do — it folds in the
memory audit notes; update it as items land.

## Deferred by design (working, intentionally postponed)
- **Parameter-LANDSCAPE plot — NOT planned (decided 2026-08-01).** Its data source
  was the brute-force grid scan, which was intentionally removed (Basin Hopping
  dominates it). Building it would require re-adding a *constrained* grid scan; not
  on the roadmap. (The residual-vs-iteration **progress plot is now DONE** — see
  Recently completed.)
- **Phase-intensity cache** — old-app performance optimization; deferred (correctness
  unaffected).
  (**Per-phase plot curves — DONE.** Each phase's calculated contribution now
  draws in its own `display_color`; a mixture recompute captures them on the
  specimen (`phase_patterns`, transient/never saved) and the graph draws one
  curve per phase under the total. Driven by the per-specimen `display_phases`
  flag — the specimen dialog / tree "Sep" toggles, plus a new
  **View ▸ Show phase patterns** convenience that bulk-flips the shown specimens
  and recomputes on demand. Guarded by `tools/verify_phase_curves.py` and
  `tools/verify_show_phases_action.py`.)

## Unported editors / dialogs (real remaining work)
- **Splash screen** (optional).

## Placeholder / stubbed features (visible but not fully wired)
- **Exclusion-ranges import/export** in Edit Specimen — not ported.

## Unported file formats
- **`.cpi` / `.rd` / `.brml`** (rare). Done: Bruker RAW1–4, Rigaku `.raw`, `.xrdml`,
  `.rasx`, `.xy`/`.uxd`.

## Minor gaps / edge cases
- **Component atom-relations inheritance toggle** — `component_inherit_atom_relations`
  is read-only (a linked component always follows its template's relations).
- **Driven-relation conflict resolution** — old `driven_by_other` conflict machinery
  not ported (chaining works; guardrails are simpler).
- **Last-folder memory** for file dialogs — not ported.
- **R1G5+/R2G4+/R3G3+** — NOT incomplete: never implemented upstream either; MudLab2
  matches PyXRD's `RGbounds` exactly.

## Audit findings — corrections, polish & fragile spots
Folded in from the memory audit notes ([[mudlab2-peakdetect-mineral-audit]],
[[mudlab2-wld-editor-audit]], [[mudlab2-csv-gonio-audit]], [[mudlab2-default-catalog-audit]]).

**Behavior gaps (candidate fixes):**
- **Goniometer edits don't live-recompute the plot** — `goniometer.data_changed` has
  NO listeners, so editing the emission spectrum, loading a stored setup, or changing
  any goniometer field (radius, soller, …) updates + persists the model but the
  calculated curve only refreshes on the next recompute (a phase/mixture/atom edit, a
  refinement, or reload). Whole Goniometer-tab, pre-existing. Fix: bridge
  `goniometer.data_changed` → specimen recompute/replot.
- **`add_atom_type` emits no signal** — a concurrently-open Edit Atom Types list won't
  refresh when a default phase adopts atom types (fix = one-line `atom_types_changed`
  signal).
- **`RefinementDialog` + non-modal `MatchMineralsDialog` need `WA_DeleteOnClose`** —
  parented-`exec()`/`show()` accumulation, the same class the CompositionDialog cleanup
  fixed.
- **Applied-goniometer-setup name is transient** — shown on `lbl_applied_gonio` but not
  persisted (old app stored it in `specimen.source`); forgotten when Edit Specimen is
  reopened. Deliberate simplification (the widget has no specimen ref).

**Polish (trivial / cosmetic):**
- **Muscovite catalog entry** — `Muscovite.cmp` is bundled but not offered (faithful to
  old app; trivial to add).

**Faithful-but-fragile calc spots (ported as-is; don't "fix" without care):**
- **`get_best_threshold` divide-by-zero** on a flat histogram region → a benign stderr
  RuntimeWarning during Detect Peaks (its sibling `get_best_prominence` guards it; the
  classic one never did). Converges fine on real data; the differential test matches
  the old code exactly.
- **Wavelength editor has no range validation** — a typo like `1.544` (missing leading
  zero) drives `arcsin(...) > 1` (RuntimeWarning + a silently-ignored line, not a NaN
  pattern); deleting all rows falls back to the 0.154056 default.
- **`score_minerals([], …)` crashes** in `find_closest` (empty peak list); every call
  site guards it, but the function itself is unsafe.
- **Mineral loader stale abbreviation** — a `mineral_references.csv` header line 26–49
  chars long keeps the previous entry's abbreviation (old parser's exact bug).

**Deployment:**
- **Frozen-build bundling untested** — verify PyInstaller ships every `src/mudlab/data`
  subdir (all with spaces in the name): `default components/`,
  `default wavelength distributions/`, `default goniometers/`, plus the CSVs
  (`mineral_references.csv`, `atomic_scattering_factors.csv`,
  `composition_conversion.csv`) before a release.

## Test-fixture / validation gaps (not features)
- **R1G4** has no full-pattern `.mud` golden — validated via an old-app *matrix* golden
  + the shared reps=1 calc path (`verify_higher_r`).
- Some R/G goldens rely on `.pyxrd` structures rather than clean `.mud` (the old-MudLab
  save bug that re-uuid'd atom types).

## Doc cleanup (done, but comments lag — not real work)
Stale "not done" markers in WIRING.md / TODO.md for features completed (mostly recently):
the default-phase catalog (TODO still shows `[ ]`; WIRING calls it "a placeholder"),
the higher-R models (`get_correct_probability_model not ported`), display colour
("not modeled yet", 3 spots), the atom-relations editor / based_on inheritance UI, and
Add Phase / Add Mixture wiring. Also: `edit_phase_widget.py` still claims "the
composition summary is the only remaining phase-editor piece" — but no phase-level
composition widget exists (composition is a *mixture* feature, and it's done), so that
line is stale or refers to an un-built phase-composition panel.

## Recently completed (was on this list)
- **Refinement progress plot** — the Refinement window now shows a live
  convergence plot (best Rp vs evaluations) in a "Progress" group, fed by the
  existing per-evaluation progress signal and redrawn on a ~150 ms throttle timer
  (a run of thousands of evaluations only appends points; a final redraw lands on
  finish). One refiner, optional hooks — no forked copy. The parameter-landscape
  view stays dropped. Guarded by `tools/verify_refine_progress_plot.py`.
- **Per-phase plot curves** — each phase's calculated contribution draws in its own
  `display_color` (transient `Specimen.phase_patterns`), driven by `display_phases`
  (specimen dialog / tree "Sep" toggles + a **View ▸ Show phase patterns**
  convenience). Audited; pairing hardened (row-count guard + contract, audit #5).
  Guarded by `verify_phase_curves.py` + `verify_show_phases_action.py`.
- **Snapshot-on-detach** — deleting/detaching a base phase no longer silently
  shifts a dependant's calculated pattern: `Phase/Component.snapshot_inherited()`
  bake the resolved values first; `remove_phase` snapshots dependants (mid-chain
  order-safe); Edit-Phases delete warns + names dependants; explicit detach offers
  keep/revert without disturbing normal link/unlink. Model + UI, audited. See
  `docs/dev-notes.md`. Guarded by `verify_snapshot_detach/_component`,
  `verify_remove_phase_snapshot/_dialog`, `verify_detach_choice`,
  `verify_detach_ui_noninterference`.
- **Object-graph link integrity** — `docs/dev-notes.md` documents the
  Mixture-Specimen-Phase uuid↔object model (+ phase identity / refiner sharing);
  `tools/verify_link_integrity.py` asserts the invariant across the fixtures and
  the deletion cascades.
- **About dialog + branding** — bundled the MudLab icon set under `data/icons/`;
  the app/window/taskbar icon is wired (`resources.app_icon`, `create_app`
  setWindowIcon, MainWindow setWindowIcon) and the frozen `.exe` uses `mudlab.ico`
  (MudLab.spec). A branded `AboutDialog` (about.ui + about_dialog.py) replaces the
  `QMessageBox.about` placeholder: logo, name, version, tagline, and the runtime
  library versions. Version bumped to **0.2.0** (`__init__` + pyproject). Guarded
  by `tools/verify_about.py`.
- **Mineral-preview overlay** — selecting a mineral in Match Minerals (either
  list) now draws its reflections as magenta sticks on the main plot (2θ from
  d-spacing, height ∝ relative intensity), via a transient
  `Specimen.mineral_preview` + `PatternPlot` sticks. The "Specimen range"
  checkbox is re-enabled (limits sticks to the scanned 2θ range); the preview
  clears on close. Guarded by `tools/verify_mineral_preview.py`.
- **Original-pattern overlay (live data-op preview)** — the line/data-op dialogs
  (Remove Background, Smooth, Shift, Strip Peak, Add Noise) now draw a live
  preview of the result over the original pattern on the main plot while open,
  clearing on close. Foundation: non-mutating `Specimen.preview_*`, a
  `PatternPlot.set_preview`/`clear_preview` overlay (zoom-preserving), and
  `main_window.set_pattern_preview`/`clear_pattern_preview`. Smooth's "show
  original" checkbox is re-enabled (hides the base line to judge the smoothed
  curve alone). Guarded by `tools/verify_pattern_preview.py` +
  `tools/verify_data_op_preview.py`.
- **Stored goniometer setups** — the Goniometer tab's "Load setup" combo now
  lists 12 bundled `.gon` presets (+ user-saved ones) and applies the chosen one
  via `Goniometer.apply_setup` (full reset, keeps uuid; handles the legacy
  single-`lambda` format); "Store setup" saves the current goniometer to a `.gon`
  (`file_parsers/gon_file.py`, user dir via QStandardPaths). Guarded by
  `tools/verify_goniometer_setup.py`.
- **CSV import options** — new `file_parsers/csv_io.py` is the common CSV
  import/export (auto-detect + explicit separator / decimal-sign / header) that
  `xy_parser`, `wld_file` and the pattern-export path now all delegate to. A
  `CsvImportDialog` (separator/decimal/header + live preview, sniff-prefilled)
  is offered by a shared `import_pattern` helper wired into the experimental-,
  raw-phase- and background-pattern imports; `parse_pattern` takes an optional
  `CsvOptions`. Guarded by `tools/verify_csv_import.py`.
- **Wavelength-distribution editor** — the goniometer's "Edit emission spectrum"
  button now opens an editable (wavelength nm, fraction) table with Add / Remove
  and `.wld` import/export (5 default presets bundled under
  `data/default wavelength distributions/`). `Goniometer.set_wavelength_distribution`
  invalidates the verbatim raw string so edits persist (untouched goniometers
  still round-trip byte-identically); the Goniometer tab now shows the dominant
  wavelength. Guarded by `tools/verify_wavelength_distribution.py`.
- **Detect Peaks** — wired end-to-end: `calculations/peak_detection.py` ports the
  billauer + scipy detectors and the threshold/prominence histograms; the dialog
  plots the "# of peaks vs cut-off" curve with a draggable line and coupled
  fields, and OK adds markers via `Specimen.auto_add_peaks`. Guarded by
  `tools/verify_peak_detection.py` + `tools/verify_detect_peaks.py`.
- **Match Minerals** — real reference data (`data/mineral_references.csv`, 228
  minerals) + `score_minerals`; the dialog auto-matches against the target
  markers, lists scores, and "Append labels" writes abbreviations onto markers.
  Guarded by `tools/verify_match_minerals.py`. (Reference-peak preview overlay
  now also done — see above.)

---
**Biggest genuinely-remaining items:** the optional splash screen and the rare
unported formats (`.cpi`/`.rd`/`.brml`). No standalone editors/dialogs remain.
(Per-phase curves, snapshot-on-detach and the refinement progress plot are now
done; the parameter-landscape plot is intentionally dropped.)
