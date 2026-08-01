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

**1. Delete a specimen** — `Project.remove_specimen` (automatic). Disconnects its
signals, drops it from `_specimens`, and cascades `mixture.unset_specimen` into
every mixture → that row's `specimens[i] = None` **and** `specimen_uuids[i] = ""`
(both reps). The row stays (scale / bgshift / phase cells kept); `calculate()`
skips `None` rows. Emits `specimens_changed` + `data_changed`. Nothing else
references a specimen. ✅

**2. Delete a mixture** — `Project.remove_mixture` (minimal, leaves staleness).
Just drops it from `_mixtures`. **No cascade, no signal, no recompute.** Its
specimens keep their last calculated pattern *and* `phase_patterns` (per-phase
curves) — now stale. A specimen left in no other mixture is **orphaned**:
`refresh()`/`calculate()` only iterate mixtures, so nothing ever recomputes or
clears it. ⚠️ The caller must clear/recompute + refresh; orphaned specimens are a
real staleness gap.

**3. Delete a phase in use** — `Project.remove_phase` (automatic, cascade-clears,
never refuses). Drops it from `_phases`; clears its own `based_on`; detaches any
phase `based_on` it (`set_based_on(None)`); unlinks any component `linked_with`
its components (`set_linked_with(None)`); cascades `mixture.unset_phase` → empties
each holding cell in both reps (`phase_matrix[i][j]=None`, `phase_uuids[i][j]=""`).
The slot/column stays (label + fraction kept). Emits `phases_changed` +
`data_changed`. ⚠️ `data_changed` **redraws but does not recompute** — the deleted
phase's contribution stays in the displayed curve until an F5/refresh.

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
