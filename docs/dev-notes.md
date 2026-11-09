# MudLab2 developer / debugging notes

Architecture and integrity notes for maintainers — the "why it is wired this
way" that does not belong in the end-user manual. Detailed widget↔model wiring
lives in [`src/mudlab/ui/WIRING.md`](../src/mudlab/ui/WIRING.md); the deferred /
remaining work is in [`remaining-work.md`](remaining-work.md).

---

## Object-graph linkage (Mixture · Specimen · Phase · treatment variants)

The Mixture–Specimen–Phase relationships are the backbone of the project. This
section is the source of truth for how they are linked, where the "truth" lives,
and what each deletion does. Guarded by
[`tools/verify_link_integrity.py`](../tools/verify_link_integrity.py).

### Where the truth lives — two representations, linked by uuid

There is **no single linkage object and no built-in validator**. Integrity is
held across two layers, each authoritative for a different job:

**Persistence truth = uuids.** Every `Specimen` and `Phase` has a stable `uuid`.
Everything links by that string:

| Link | Stored as | On |
|---|---|---|
| Mixture → its specimens (rows) | `specimen_uuids` (n) | `Mixture` |
| Mixture → its phases (n×m grid) | `phase_uuids` (n×m) | `Mixture` |
| Phase → its reference phase | `based_on_uuid` | `Phase` |
| Component → its template | `linked_with_uuid` | `Component` |

The project's `_phases` / `_specimens` lists are the master registries;
`Project.phase_uuid_map()` / `specimen_uuid_map()` (and the global
`{uuid: component}` map built in `resolve_phase_references`) are the resolvers.
**This is what the `.mud` persists and what round-trips.**

**Runtime truth = resolved object pointers.** At load, `Mixture.from_dict`
resolves the uuid grids into object grids — `mixture.specimens` and
`mixture.phase_matrix` — and `resolve_phase_references` binds `phase.based_on` /
`component.linked_with`. **These object refs are what `calculate()` and the
read-through getters actually read.**

The two are held **separately and are not derived from each other at save time**
(deliberate — see the note in `models/mixture.py`). So the invariant to verify at
any point is:

> `mixture.phase_matrix == resolve(mixture.phase_uuids)` and
> `mixture.specimens == resolve(mixture.specimen_uuids)` (with `"" ↔ None`), and
> a live `based_on` / `linked_with` pointer matches its stored uuid, and every
> non-empty uuid resolves to a live project object.

Every edit must update **both** representations by hand (`set_phase_at`,
`unset_phase`, `set_specimen_at`, `unset_specimen` each write the object grid
*and* the uuid grid). Load-time resolution uses `.get(uuid)`, so a **dangling
uuid silently becomes `None`** (an empty cell) rather than raising.
`verify_link_integrity.py` asserts the whole invariant statically across the
sample fixtures (currently clean: 0 dangling) and after each deletion cascade.

There is **no explicit "phase set" object** — a treatment-variant set (air-dried
/ glycolated / heated forms of one clay) is *emergent* from the `based_on` tree
plus the component `linked_with` graph. `based_on` is directional and one parent
per phase; "mutually linked" really means "children inherit from a shared base".

### Deletion cascades — what is automatic, what is a gap

**0. In use = in a mixture — deletion is REFUSED.** A phase or specimen a
mixture still holds cannot be deleted: `Project.remove_phase` /
`remove_specimen` return `False` and change nothing. Emptying a live model's
cells behind the user's back is the damage this gate exists to prevent — the
old app cascade-cleared, and this is a deliberate divergence.
`Project.phase_usage(phase)` → `[(mixture, [(row, slot), …]), …]` and
`specimen_usage(specimen)` → `[(mixture, [row, …]), …]` answer *where*, and
`qt_utils.in_use_message` turns that into the refusal text ("… is still used by
Mix1 (3 cells) — free it in Edit Mixtures"). Both UI paths refuse **before**
their confirmation prompt (Edit Phases' Remove; the specimen tree's Remove,
which refuses a mixed selection wholesale rather than half-deleting it).
**Inheritance is not membership**: a `based_on` parent or a `linked_with`
template with no mixture cell is still deletable — that severing is safe
(snapshot-on-detach, §4). Guarded by `verify_in_use_deletion.py`.

**1. Delete a specimen** — `Project.remove_specimen` (automatic, once it is not
in any mixture). Disconnects its signals, drops it from `_specimens`, and
cascades `mixture.unset_specimen` into every mixture → that row's
`specimens[i] = None` **and** `specimen_uuids[i] = ""` (both reps). The row
stays (scale / bgshift / phase cells kept); `calculate()` skips `None` rows.
Emits `specimens_changed` + `data_changed`. Nothing else references a specimen.
The cascade is now belt-and-braces (the usage gate means there is nothing left
to clear), kept because it is the invariant `verify_link_integrity` checks. ✅

**2. Delete a mixture** — `Project.remove_mixture` (minimal, leaves staleness).
Just drops it from `_mixtures`. **No cascade, no signal, no recompute.** Its
specimens keep their last calculated pattern *and* `phase_patterns` (per-phase
curves) — now stale. A specimen left in no other mixture is **orphaned**:
`refresh()`/`calculate()` only iterate mixtures, so nothing ever recomputes or
clears it. ⚠️ The caller must clear/recompute + refresh; orphaned specimens are a
real staleness gap.

**3. Delete a phase** — `Project.remove_phase`. A phase **in a mixture is
refused** (§0); what follows is what happens to a freed one. Drops it from
`_phases`; clears its own `based_on`; detaches any
phase `based_on` it (`set_based_on(None)`); unlinks any component `linked_with`
its components (`set_linked_with(None)`); cascades `mixture.unset_phase` (a no-op after
the gate, kept as the invariant). The slot/column stays (label + fraction kept).
Emits `phases_changed` + `data_changed`. ⚠️ `data_changed` **redraws but does not
recompute** — a freed cell's contribution stays in the displayed curve until an
F5/refresh.

**4. Delete a treatment-variant member** — the subtle one. A *leaf* (nothing
depends on it) removes cleanly; the base and siblings are unaffected. Deleting the
**base** (or any node others depend on) detaches every dependant via
`set_based_on(None)` / `set_linked_with(None)`. Because inheritance is a
**read-through overlay** (`Phase._resolved` walks to the first non-inheriting
ancestor and returns *its* own value) while each child **always stores its own
value** (`to_dict` persists own, never the read-through values), a child that was
*displaying/computing* the base's value but *storing* a different own value will,
on detach, revert to its own stored value — sigma*, CSDS, the F/W stacking
probabilities, and (via components) d001, cell params, even atom sets — which
would change the child's calculated pattern.

**Snapshot-on-detach (implemented).** To stop that silent shift, `remove_phase`
now BAKES each dependant's resolved values into its own storage before severing:
`Phase.snapshot_inherited()` (sigma*/CSDS/color/probabilities) and
`Component.snapshot_inherited()` (cell scalars + atom lists/relations). Component
atoms are baked by SHARING the template's objects (a fresh own list of the same
objects) so the component's own relation→atom uuid references stay valid; the
rare case where two components share one template component is de-duplicated by
`Component.reclone_atoms` (fresh-uuid copies via the `.cmp` serialize→remap path).
The base can therefore be edited and then deleted with the dependants' patterns
unchanged. Guarded by `verify_snapshot_detach.py`, `verify_snapshot_component.py`,
`verify_remove_phase_snapshot.py`. NB: duplicate atom uuids across linked
components are a benign, pre-existing norm (old-app inlining), so the dedup targets
object aliasing, not uuid uniqueness.

**UI.** Deleting a base in Edit Phases warns and names its dependants
(`Project.phase_dependants` + `edit_phases_dialog.deletion_confirm_message`),
saying their values are kept. Explicitly detaching in the phase / component
editors (picking "(none)") offers keep-vs-revert (`inheritance_detach.
ask_detach_choice`, gated by `Phase/Component.has_inherited_values()`): "keep"
snapshots first, "revert" is the old fall-back-to-own. Guarded by
`verify_remove_phase_dialog.py` + `verify_detach_choice.py`.

### Phase identity & the refiner (who owns refined values)

**Default-phase load gives fully fresh identities.**
`add_catalog_entry_to_project` → `Phase.create_empty` (fresh phase uuid) +
`load_default_component` → `load_cmp`, which forces *every* component and atom
uuid fresh (uuid_remap). Atom *types* are de-duplicated **by name** onto the
project's own (reference data, shared, never refined). So loading the same
default twice yields two fully independent phases with distinct
phase/component/atom uuids and **no uuid clash** — only the atom-type objects are
shared.

**Phases are shared OBJECTS across mixtures.** A mixture resolves its
`phase_uuids` against the project's single phase list, so the same phase in two
mixtures (or two slots) is the *same object*. `enumerate_refinables` de-dups by
`id(phase)`; the refiner's setters write the **structural** params (sigma\*, CSDS
mean, R0 F, per-component d001/delta_c, relation values) **in place** on the
shared Phase/Component. Fractions/scales/background are **per-mixture** (own
arrays on each `Mixture`), fit by the inner `optimize_mixture`.

Consequences (both intended, PyXRD behaviour): *same default twice in one mixture*
→ two independent phases refined separately (their per-slot fractions are then
non-identifiable — a degenerate fit, not a crash). *One phase in two mixtures* →
the structure is shared, so **no mixture owns it**; the last mixture refined wins
for the phase's structure, it optimises against that mixture's residual only, and
the other mixture's stored calc is stale until recomputed. Refine independent
structures by loading the phase twice. Guarded by `verify_add_default_phase.py`.

### Known gaps (candidate work)

- **No integrity validator in the app** — the invariant above is enforced only by
  convention + the test harness. (This is the #5-class fragility from the
  per-phase audit, [[mudlab2-per-phase-audit]].) `verify_link_integrity.py` is the
  guardrail; there is no in-app `validate()`.
- **`remove_mixture` staleness** — no recompute/clear/refresh; orphaned specimens
  keep a frozen calc + per-phase overlay forever.

---

## Mineral matching (Match Minerals)

Reviewed 2026-11-09. The scoring was **deliberately left unchanged**; this records
how it behaves so the analysis is not re-derived. Code: `score_minerals` in
`calculations/peak_detection.py`, `match_minerals_dialog.py`, launched from the
Peaks window (`edit_markers_dialog.py`). The scorer is not the old app's: commit
`7160503` (2026-08-15) replaced the old regression, which dropped every two-line
match with distinct intensities (quartz vanished) and ranked a sulfide first.

### How the dialog gets its peaks

1. The Peaks window's **Match minerals** button is enabled once a row is
   selected (`_on_marker_selected`) and disabled only when the list reloads empty.
2. It passes `targets = self._selected_markers() or list(self.specimen.markers)`.
3. **The list is single-selection.** `object_store.ui` sets no `selectionMode`, so
   the `QTreeView` default (`SingleSelection`) applies, and `_reload_markers`
   always selects a row. In normal use the dialog therefore receives **one**
   marker. Ctrl+click, Shift+click and Ctrl+A cannot add rows (verified by driving
   the real dialog). The all-markers fallback is reachable only by Ctrl+clicking
   the selected row to clear the selection: the button stays enabled, the
   selection is empty, and every marker becomes a target.
4. Inside the dialog the **Targets** dropdown changes the set (since
   2026-11-09, below). `_compute_marker_peaks` runs at open and on every change
   of targets, turning each target into `(d in Å, intensity)`:
   - d = `marker.get_nm_position() * 10`, Bragg at `specimen.wavelength`, which
     is `goniometer.wavelength`. A wrong wavelength means wrong d-spacings.
   - intensity = `np.interp(marker.position, exp_x, exp_y)`: the raw experimental
     pattern, background included. The calculated curve is never used, even for
     a marker placed on it. Outside the scan `np.interp` returns the edge value.
   - Hidden markers (`visible = False`) count like any other; a marker whose d
     is not positive is skipped.
5. Adding a mineral by hand scores that one mineral against the same peak list.

**The targets panel (ported 2026-11-09).** Old MudLab `71807ac8` (2026-06-05,
"multi-target Auto Match") opens with the selected marker and lets the target
set grow and shrink inside the dialog; that had not been ported, so matching ran
against one peak. It is now a **checkable dropdown** (`cmb_targets` in
`box_targets`): every peak in 2θ order, ticked = target, "n of N peaks" as the
closed box's placeholder. `_TickOnClick` turns a popup click (and Space) into a
toggle and keeps the popup open; Enter toggles via `activated`. Every change
rescores (the **Auto match** button is gone), the last target cannot be removed,
new targets are appended (the scorer sees the same peak order as before), and
Append labels writes onto the current targets. Rescoring keeps the selected
mineral and hand-added rows (`_MANUAL_ROLE`); every row now carries its
reference index and full line list, so a mineral previews the same lines from
either list. The Peaks list itself stays single-selection by design.

**While the dialog is open the plot is view-only** (user decision): zoom, pan,
right-click reset and the toolbar work; picks, marker double-click and drag
select do not. `MainWindow.set_plot_interaction_locked(locked, owner)` applies
`PatternPlot.set_interaction_locked` and re-applies it to rebuilt plots; arming
a position pick is refused meanwhile; `_open_edit_markers` raises Match Minerals
instead of rebuilding Peaks (which would destroy it). The lock remembers its
owner, because reopening defers the old dialog's deletion and its `destroyed`
lands while the new dialog holds the lock. Target peaks are highlighted via the
transient `Specimen.match_targets` (bold label on `MATCH_TARGET_COLOR`, heavier
line), never saved. `MatchMineralsDialog._end_session`, reached from `done()` and
`closeEvent`, clears preview + highlight and unlocks. Guard:
`tools/verify_match_targets.py`.

### With one target, where every session starts

With a single observed peak, `min_peaks_needed` is 1, n is 1, and the intensity
factor is the neutral 0.5. The score is `0.5 × position_factor`, at most 0.5. The
ranking is by how close **one** d-spacing is, and intensities play no part.
Measured on `308 r1.mud`, specimen 308 AD, one marker at 19.72° 2θ: 48 minerals
listed, top Biotite-2M1 at 0.49608. **Everything below about the intensity factor
applies once more peaks are ticked as targets.** On the kaolinite peak at 7.19 Å,
for example, Kaolinite-1A ranks 2nd of 8 alone (0.364) and 1st once the 4.50 and
3.58 Å peaks are ticked too (2.068).

### How a score is computed

`score = n × position_factor × intensity_factor`, per reference mineral; only
scores above 0 are listed, best first, with no cutoff.

1. Take the mineral's 15 lines with the **largest d** (lowest angle), not the
   strongest.
2. From the largest d down, take the nearest observed peak. It is a match if it
   lies within 1% of the reference d and no earlier line has claimed it.
3. At least 2 matches are needed (1 when only one peak was given).
4. `position_factor = 1 − mean(|Δd|/d) / 0.01`: 1 for exact, 0 at the window edge.
5. `intensity_factor` = Pearson r of the matched card intensities (0–100) against
   the observed counts. Negative r becomes 0, which drops the mineral. It is the
   neutral 0.5 when undefined: fewer than 2 matches, or all values on one side
   equal.

Consequences, measured on the shipped library (228 minerals):

- **Unmatched lines cost nothing.** A strong card line with no observed peak does
  not lower the score, so line-rich minerals collect chance matches in a crowded
  pattern.
- **n is not normalised.** It can reach 15 for a mineral with 15+ lines but only
  2 for a two-line card. The median mineral has 22 lines; 83 have 15 or fewer.
- **Lines are chosen by d, not strength.** For 9 minerals the strongest line
  falls outside the 15 tested, for example Illite-2M2 (2.583 Å), Microcline,
  intermed. (3.24 Å) and Bornite (1.93 Å). Lines below the scan's start still
  take places among the 15.
- **The window is 1% of d, so it widens with angle.** At Cu Kα₁ it is ±0.06° 2θ
  at 14 Å, ±0.09° at 10 Å, ±0.27° at 3.34 Å and ±0.66° at 1.54 Å, regardless of
  instrument or peak width.
- **Assignment is greedy by default.** A larger-d line claims its nearest peak
  even when a later line is closer to it; the later line then fails instead of
  trying its next-nearest peak. The claim check is per mineral only (the list
  is reset for each mineral), so one peak can count for several minerals.
  Since 2026-11-09 a **One-to-one** pairing is selectable; see below.

### Pairing modes: Greedy and One-to-one

`score_minerals(..., pairing=)` takes `PAIRING_GREEDY` (default; `_pair_greedy`
is the original loop, proven bit-identical on 92 peak lists / 3,731 rows and
pinned against a frozen copy in `tools/verify_mineral_pairing.py`) or
`PAIRING_ONE_TO_ONE` (`_pair_one_to_one`: SciPy `linear_sum_assignment`, where an
out-of-window pair costs more than all in-window pairs together, so it maximises
matches and then minimises total relative deviation; checked optimal against
brute force). Only the pairing differs; the score formula is shared. The dialog's
**Pairing** box switches between them and rescores; Greedy is the default and is
not remembered between sessions.

Why it is an option rather than a replacement, measured on 28 real peak lists
(308 AD's marked peaks plus auto-detected peaks on every sample project): the
top match never changed and the top ten changed by at most two minerals, but
single minerals can move a lot, in both directions — Muscovite-2M1 on 308 AD's
50 detected peaks 1.78 → 3.22, Hornblende 0.73 → 0.26 (a better pairing can lower
r). On its own eight strongest lines Muscovite-2M1 ranks 5th under Greedy (behind
Illite-2M1) and 1st under One-to-one. Blocked lines are common (20 minerals on 12
peaks) but One-to-one rescues few (3): usually no other peak is in reach because
two card lines sit under one observed peak — 93 of 228 cards have two tested
lines within 1%. That is the one-to-one rule's own limit; grouping close lines
before pairing (summed intensity) would address it and was considered, not built.

### The intensity factor in practice

Pearson r ignores scale and constant offset, which is what lets 0–100 card values
be compared with counts. As a multiplier it can only lower a score. Measured with
the real scorer on the quartz card, peaks at exact positions (position_factor = 1,
so score = n × factor):

| Case | n | Factor | Score |
|---|---|---|---|
| A. 7 lines, counts proportional to the card | 7 | 1.000 | 7.00 |
| B. Same, plus a flat background of 2000 | 7 | 1.000 | 7.00 |
| C. Same, background sloping 3000 → 1000 | 7 | 0.912 | 6.38 |
| D. Only 4.26 and 3.34 Å, in the right order | 2 | 1.000 | 2.00 |
| E. Only those two, 4.26 slightly taller (3000 vs 2900) | — | dropped | 0 |
| F. 7 lines, 2.46 Å boosted by another phase (+4000) | 7 | 0.450 | 3.15 |
| G. 7 lines, three weak lines each boosted (+2500) | 7 | 0.450 | 3.15 |
| H. 7 lines, intensities scrambled | — | dropped | 0 |

- A sloping background bends the straight line r looks for, and it is steepest
  at low angles, where clay peaks sit (C).
- Quartz's 3.34 Å line is 100 and every other is 16 or less, so r mostly asks
  whether 3.34 is the tallest matched peak. One overlap that lifts another line
  above it more than halves the score (F). That 0.45 is below the 0.5 a mineral
  gets when its intensities cannot be judged at all.
- A negative r discards every position match (H).
- n can outweigh agreement: 10 matches at 0.3 score 3.0, beating 2 perfect
  matches at 2.0.
- On oriented clay mounts the basal 00l lines are far stronger than the
  random-powder card values, so even the right clay can correlate poorly.

### Two matches: only the order counts

Two points always lie on a straight line, so with n = 2,
`r = sign(ref₁ − ref₂) × sign(obs₁ − obs₂)`: +1 or −1, with the size of each
difference cancelling out. A two-line mineral scores `2 × position_factor`, or
`1 × position_factor` on an exact tie, or is dropped. With quartz's 4.26/3.34
lines (card 16/100), observed 500/3000, 2999/3000 and 30/3000 all get factor 1,
while 3000/2900 is dropped (case E).

Measured on 308 AD with **all 12 markers** as targets: 45 minerals matched exactly two lines on
position. 23 got +1, 20 were dropped and 2 tied (Pentlandite, Cobaltpentlandite),
so 25 of the 62 listed minerals (40%) rest on two lines, including 2 of the top
10. For unrelated intensities the order is a coin flip, so at n = 2 the factor
carries almost no evidence yet has the largest possible effect. Examples:

| Mineral | Card | Observed | Result |
|---|---|---|---|
| Andalusite | 82, 30 | 8, 11 | dropped: real evidence against it |
| Andesine, low (DEL) | 70, 60 | 5, 34 | dropped, though the card barely separates the lines |
| Anorthite, sod., ord. | 4, 7 | 5, 34 | full credit, though 7× observed against 1.75× on the card |

Two is the minimum for a mineral to be listed at all, and minor minerals in a
mixture often show only one or two lines above background, so this is where
they fall. If this is ever revisited, the smallest changes are a neutral 0.5 at
n = 2, or comparing the intensity ratio instead of the sign of the difference;
only the two-line case would change.
