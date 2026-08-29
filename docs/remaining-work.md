# MudLab2 — remaining & deferred work

Snapshot as of 2026-08-29 (V1 = main = origin @ `8a4684b`, v1.0.3 released). The GTK→Qt/PySide6
port is far along: the analytics/calc
engine is golden-validated, both major editors (Edit Phases, Edit Mixtures) are
feature-complete, and the default-phase catalog now matches old MudLab/PyXRD (80
entries, all R0–R3 models). This is the single canonical to-do — it folds in the
memory audit notes; update it as items land.

## Requested 2026-08-23 (user's list — all done except #4)

Recorded verbatim in intent; the notes under each are what the code says today,
so whoever picks one up starts from facts rather than a search.

1. ~~**Main pattern plot — three changes.**~~ — **DONE 2026-08-23.** Grid off
   (in `draw_pattern`, not in the shared `style_axes` — seven other charts still
   want theirs); a minor tick every degree with an adaptive labelled step
   (1/2/5/10/20, resolving to 1 when zoomed in); and the specimen name + Rp /
   Rwp / GoF moved from the left margin into the upper-right index, ahead of the
   mixture blocks, with the reserved 18% of width given back to the plot. Note
   `display_label_pos` is now inert — the property stays (persisted, old app
   reads it) but its Edit Project control is disabled with a tooltip.
   verify_plot_axes_index.py 27/27.

2. ~~**Discard the MudLab2 splash and copy the OLD app's exactly**~~ — **DONE
   2026-08-23.** Faithful port of the old palette, order, typography, 220 px
   logo, separator and five-second hold; the branding decision it reverses has
   been struck from the splash note. See the TODO entry for the three porting
   traps (points not pixels, per-widget margins become spacers, rounded corners
   need a translucent top level). verify_splash.py 35/35.

3. ~~**Plot export (SVG + bitmap) on the Composition dialog's plot context
   menu.**~~ — **DONE 2026-08-23.** Right-click gives "Save plot as..."
   (SVG / PDF / PNG / TIFF / JPEG) and "Copy plot image", reusing the Save Graph
   size dialog and a now-shared `plot_controller.save_figure`. TIFF is written
   LZW-compressed — matplotlib's default is uncompressed, which at the size
   dialog's 8000×4800 default produced a 153 MB file.
   verify_composition_plot_export.py 18/18.

4. **CIF component import with built-in c\* projection — ANSWER: no, not
   available.** Edit Phases' component import accepts **`.cmp` only**
   (`CMP_FILTERS = "Component files (*.cmp);;All files (*.*)"`,
   `component_widget._on_import_component`, line ~449). There is no CIF path
   anywhere in the component importer, and therefore no c\* projection of atom
   positions. What *does* exist is a CIF reader for the experimental non-clay
   phases (`nonclay/structure.py`: `_parse_cif`, `reference_from_cif`,
   `reflections_from_cif`) — but it produces a 3-D reflection stick list and an
   oxide composition, **not** the 1-D projection onto c\* that a clay component
   needs. So this is a real feature to build, not a switch to flip: the missing
   piece is projecting the CIF's fractional atom positions onto c\* and binning
   them into layer/interlayer atoms with `z` + `pn`.

5. ~~**Component pane "Show Structure" button**~~ — **DONE 2026-08-23.**
   Ported as `component_diagram.py` (Qt-free builder) plus a modeless viewer
   with Copy and Save-as-text. Verified on a 2:1 and a 1:1 clay.
   verify_structure_diagram.py 36/36.

6. **A Reset feature on Phase objects — ANSWER: feasible, and most of it already
   exists.** `default_state.py` already records what every phase *started as*
   and can rebuild it: `capture_catalog_defaults` / `capture_imported_defaults`
   store the mapping at the moment a phase enters the model,
   `resolve_default_phase(project, name)` rebuilds that reference on demand, and
   `set_as_baseline` / `freeze_baseline` / `make_baseline_copy` already handle
   the hard part (severing inheritance and re-cloning atoms so a frozen copy
   cannot drift). A "Reset phase" would be: resolve the phase's recorded default
   → copy its values back over the live phase → recompute. Open questions to put
   to the user before building: does Reset restore the **shipped default** or the
   **user's own baseline** when both exist; does it reset structure only or also
   fractions/scales; and — since phases are SHARED across mixtures — does a reset
   apply everywhere that phase is used (it must, there is one object).

7. ~~**Rename "Import composition" → "Edit composition", move it to a new
   "Composition" menu, and add removal.**~~ — **DONE 2026-08-23.** New top-level
   **Composition** menu with *Edit composition…* (reads *Enter composition…*
   until one exists) and *Remove composition* (disabled until one exists,
   confirms, marks the project dirty).

8. ~~**Exporters for the old app's `.mud` and for `.pyxrd`.**~~ — **DONE
   2026-08-23**, under **Project → Export**. The old-app exporter is verified by
   actually loading its output under the old app's own interpreter, with a
   control proving a native save fails there. The PyXRD exporter is a real
   schema translation (sample_length/absorption move back onto the Specimen,
   wavelength distribution → single wavelength, ADS group, refine_method
   remapped) verified structurally against 12 real `.pyxrd` files — **but PyXRD
   itself has never opened the output**, and the export dialog says so.
   Still worth doing when PyXRD is available: open an exported `.pyxrd` in real
   PyXRD and confirm the strip/map list. See `verify_exporters.py`.

### Requested 2026-08-23, second round

9. ~~**Peaks dialog: rename, hide during plot interaction, keep sorted.**~~ —
   **DONE 2026-08-23.** Renamed to Peaks (visible strings only; the model and
   the `.mud` key stay `marker`); steps aside for a Sample pick and while Match
   Minerals is open; the list re-sorts when a position is *committed*.
   Required a cancel path for armed picks (Esc) — without it a hidden dialog
   could be stranded. verify_peaks_dialog.py 37/37.

**Deferred at the user's request (2026-08-23):**

- **#4 CIF component import with c\* projection** — **STAGE 1 DONE
  2026-08-30, no UI yet.** `src/mudlab/file_parsers/cif_component.py` reads a
  CIF, projects it along c\* and builds a Component; `verify_cif_component.py`
  (42 checks) measures it against 73 published RRUFF/AMCSD clay structures the
  user keeps outside the repo (`MUDLAB_CIF_CORPUS` points elsewhere; absent, it
  skips with exit 2).

  Settled, with evidence:

  - Height above (001) is `z_fractional x d001` **exactly**, x and y
    contributing nothing — so a boundary parallel to (001) is in the same place
    in 3-D as after projecting. 3-D is still needed, but for **bonding**: the
    hydroxyl test and the layer/interlayer split run on the structure before it
    is collapsed, which is the only way to tell interlayer water from hydroxyl.
  - Faithfulness: anion content preserved **73/73**, divisor 1 and 2 alike.
    Against MudLab's own components: kaolinite r = 0.9994, illite 0.9537, talc
    0.9530, chlorite 0.9347, every atom type resolving.
  - Nothing is persisted that the old GTK app cannot read, so CIF provenance
    has nowhere to live and none is invented.

  **Next (stage 2): the review dialog.** Nothing should be committed to a phase
  until the user has seen and can override the four things the projector has to
  guess — O vs OH per row, the fold divisor, the layer/interlayer split, and
  d001. Two known disagreements to surface there: chlorite's brucite sheet is
  framework-bonded so it lands in *layer* where our shipped Chlorite puts it in
  *interlayer*; and sepiolite is a channel mineral with no MudLab bucket, so it
  should be refused rather than approximated. Treatment variants are stage 3
  and should reuse component **linking** (inherit layer atoms, keep own d001 and
  interlayer), which is how the shipped smectites already do air-dried → glycol
  → heated. Note a CIF is NOT necessarily the air-dried state: the four
  montmorillonite CIFs project to 0.97, 1.11, 1.22 and 1.22 nm, so the importer
  must ask which state it represents.
- ~~**#6 A Reset feature on Phase objects**~~ — **DONE 2026-08-26**: right-click
  a phase in Edit Phases → *Reset to shipped default*. Structure only; name,
  colour and inheritance kept; requires a stated default (Default Phases
  dialog). verify_phase_reset.py 27/27.
- *(superseded)* feasible and mostly already built on
  `default_state`'s captured defaults. THREE QUESTIONS FOR THE USER FIRST:
  does Reset restore the shipped default or the user's own baseline when both
  exist; structure only, or fractions/scales too; and — since phases are SHARED
  across mixtures — confirmation that a reset necessarily applies everywhere
  that phase is used.

## Public repo presentation (deferred 2026-08-29)

Raised when asking whether the GitHub link can be given to users. **It can** —
a full re-audit that day found no secrets, no email addresses, no local paths
or usernames in tracked files, no `.mud` fixture anywhere in the history (not
merely absent from HEAD), and none of the unpublished non-clay method work.
These four are presentation only, and all are small.

- **The repo has no description, homepage or topics.** The header beside the
  name is empty, which is the first thing a visitor reads. `gh repo edit
  --description ... --homepage ...` sets it.
- **`README.md` opens with a developer note** — *"Working folder is `MudLab2`
  while the legacy MudLab is still installed"* — and carries no download link
  above the fold. A user landing on the repo root meets build instructions
  before they meet the program.
- **GitHub reports the licence as "Other"**, not BSD-3-Clause, so the sidebar
  badge is unhelpful. `LICENSE` is genuine BSD 3-Clause; the two copyright
  lines (Dumon 2013, Ghosh 2026) most likely defeat GitHub's detector. Worth
  ten minutes only because a cautious institution notices.
- **`docs/DOCUMENTATION-PLAN.md` carries local paths** (`c:\GitHub\MudLab\`,
  `c:\GitHub\MudLab2\docs\`, lines 49 and 58). Harmless, just scruffy in a
  public repo — make them repo-relative.

**Until these are done, send users to the releases page, not the repo root:**
`https://github.com/Parthasarathi-Ghosh/MudLab2/releases/latest` lands on the
download and the notes. That remains the better link for users afterwards too.

Two related points that are decisions, not defects, and are deliberately NOT
listed as work: `docs/remaining-work.md` (this file) is a public 304-line
to-do that a *user* may read as a list of faults; and `.claude/commands/docs.md`
plus the `Co-Authored-By` trailers make the AI-assisted workflow visible, which
matters only insofar as the planned paper has its own disclosure norms.

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
- *(none — the splash screen, the last item here, is now done; see Recently completed.)*

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

**Behavior gaps — ALL CLOSED (verified 2026-08-26, the doc had gone stale):**
- ~~Goniometer edits don't live-recompute~~ — bridged; `main_window` wires each
  specimen's `goniometer.data_changed` to a debounced recompute.
- ~~`add_atom_type` emits no signal~~ — `Project.atom_types_changed` exists and fires.
- ~~`RefinementDialog` needs `WA_DeleteOnClose`~~ — set. (`MatchMineralsDialog`
  deliberately does NOT have it: its owner keeps a reference and closes it later.)
- ~~Applied-goniometer-setup name is transient~~ — persisted in `specimen.source`.

**Polish — DONE 2026-08-26:**
- ~~Muscovite catalog entry~~ — `Muscovite.cmp` was bundled but never offered
  (faithful to the old app, which shipped the component and left it out of its own
  list). Now offered; the catalog has 225 entries.

**Faithful-but-fragile calc spots — ALL FIXED 2026-08-26** (`verify_fragile_spots.py`,
19 checks). Each was a deliberate bug-for-bug port, left alone while the numerics were
validated against goldens; the numerics are unchanged by these:
- ~~`get_best_threshold` divide-by-zero~~ — a flat region gave a zero slope and 32
  "invalid value encountered in scalar divide" warnings per run. Guarded; nan still
  fails the `|R| >= 0.98` test exactly as before, so the search terminates identically
  and a real pattern still yields the same threshold.
- ~~Wavelength editor has no range validation~~ — `1.544` for `0.1544` is a valid float
  and an impossible wavelength, and nothing complained downstream because
  `get_2t_from_nm` clamps arcsin's argument: reflections silently stopped appearing.
  The editor now refuses anything outside 0.01–1.0 nm, and negative fractions, with a
  message that names the units.
- ~~`score_minerals([], …)` crashes~~ — the unsafe one was `find_closest`, which raised
  `IndexError` out of `zip(*array)` on an empty array. Every caller guarded it, so it
  never surfaced; it now answers `None`.
- ~~Mineral loader stale abbreviation~~ — a header too short to carry one kept the
  PREVIOUS mineral's. One shipped entry was short (Augite, 31 chars) and inherited
  "Aug" from the Augite above it — correct by luck. The parser now clears, and the data
  line carries its own abbreviation.

**Deployment:**
- **Frozen-build bundling — VERIFIED 2026-08-01.** A PyInstaller onedir build
  (`MudLab.spec`, PyInstaller 6.21) ships the whole `src/mudlab/data` tree to
  `_internal/mudlab/data` (all 27 `.cmp`, the 3 CSVs, icons, the goniometer +
  wavelength presets); `MudLab.exe --selftest` runs the real loaders in the frozen
  app and all resolve (the `os.path.dirname(__file__)`-relative paths work in the
  bundle), and a bare launch runs without crash. Guarded by
  `tools/verify_selftest.py`. Re-run `--selftest` on the built exe before each
  release.

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
- **Splash screen** — a branded startup splash (`splash.py` + `ui/splash.ui`,
  shown by `__main__.main` while the window builds, auto-closes after a ~700 ms
  minimum). Deliberately DISTINCT from the old GTK MudLab (shared name + icon): a
  deep teal-slate background echoing the app icon's crystal-lattice palette, the
  reused icon, and the version number in a warm gold so the higher release number
  stands out from the (capped) old app. Palette constants in `splash.py` are the
  one place to retune. Guarded by `tools/verify_splash.py`.
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
**Biggest genuinely-remaining items:** just the rare unported formats
(`.cpi`/`.rd`/`.brml`) plus a handful of small audit-noted fixes (the goniometer
live-recompute is the most user-visible) and pre-release housekeeping. No
standalone editors/dialogs remain. (Per-phase curves, snapshot-on-detach, the
refinement progress plot and the splash screen are done; the parameter-landscape
plot is intentionally dropped.)
