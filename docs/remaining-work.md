# MudLab2 — remaining & deferred work

Snapshot as of 2026-07-24 (origin/V1 @ `8696ef3`). The GTK→Qt/PySide6 port is far
along: the analytics/calc engine is golden-validated, both major editors (Edit
Phases, Edit Mixtures) are feature-complete, and the default-phase catalog now
matches old MudLab/PyXRD (80 entries, all R0–R3 models). This lists what is *not*
done. Kept as the canonical to-do; update it as items land.

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
- **Wavelength-distribution editor** — goniometer "Edit emission spectrum"
  (`wavelength_distribution.glade`).
- **CSV import options** dialog (`csv_import.glade`).
- **About dialog** branding + window/app icons (currently a `QMessageBox.about`
  placeholder).
- **Splash screen** (optional).

## Placeholder / stubbed features (visible but not fully wired)
- **Detect Peaks** — dialog exists; actual peak detection not connected (graph
  placeholder).
- **Match Minerals** — uses placeholder mineral references; reference-data port not done.
- **Stored goniometer setups** — "Load setup" combo is a placeholder.
- **Original-pattern overlay** in the line/data-op dialogs — not ported.
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

## Audit follow-ups / polish (see memory audit notes)
- **`add_atom_type` emits no signal** — a concurrently-open Edit Atom Types list won't
  refresh when a default phase adopts atom types (fix = one-line `atom_types_changed`
  signal).
- **Muscovite catalog entry** — `Muscovite.cmp` is bundled but not offered (faithful to
  old app; trivial to add).
- **`RefinementDialog` `WA_DeleteOnClose`** — same parented-`exec()` accumulation the
  CompositionDialog cleanup fixed.
- **Frozen-build bundling untested** — verify PyInstaller ships
  `src/mudlab/data/default components/` (note the space) + the CSVs before a release.

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

---
**Biggest genuinely-remaining items:** wavelength-distribution editor, Detect Peaks
wiring, Match Minerals reference data, About/branding.
