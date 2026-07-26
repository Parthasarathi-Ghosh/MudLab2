# MudLab2 — remaining & deferred work

Snapshot as of 2026-07-26 (local V1 @ `84a9924`, 2 commits ahead of origin @
`8696ef3`, unpushed). The GTK→Qt/PySide6 port is far along: the analytics/calc
engine is golden-validated, both major editors (Edit Phases, Edit Mixtures) are
feature-complete, and the default-phase catalog now matches old MudLab/PyXRD (80
entries, all R0–R3 models). This is the single canonical to-do — it folds in the
memory audit notes; update it as items land.

## Deferred by design (working, intentionally postponed)
- **Refinement progress/results plot** — residual-vs-iteration / parameter-landscape
  plot (old `RefineHistory` / `refine_results.glade`). Record-history hook exists,
  disabled.
- **Phase-intensity cache** — old-app performance optimization; deferred (correctness
  unaffected).
- **Per-phase plot curves** — `display_color` is modeled/editable/round-tripped, but
  the graph draws only the specimen total, so colour is metadata-only until a
  per-phase overlay exists.

## Unported editors / dialogs (real remaining work)
- **About dialog** branding + window/app icons (currently a `QMessageBox.about`
  placeholder).
- **Splash screen** (optional).

## Placeholder / stubbed features (visible but not fully wired)
- **Exclusion-ranges import/export** in Edit Specimen — not ported.
- **Mineral-preview overlay** — the Match Minerals "Specimen range" checkbox and
  the magenta reference-peak preview it drove are deferred (checkbox disabled);
  matching + label output are wired. Depends on a per-curve plot overlay (same
  gap as per-phase curves / original-pattern overlay).

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
  Guarded by `tools/verify_match_minerals.py`. (Preview overlay still deferred,
  see above.)

---
**Biggest genuinely-remaining items:** About/branding. Then the deferred-by-design
plot overlays (per-phase curves, original-pattern overlay, refinement progress)
and the rare unported formats (`.cpi`/`.rd`/`.brml`).
