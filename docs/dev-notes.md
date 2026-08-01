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
on detach, **silently revert to its own stored value** — sigma*, CSDS, the F/W
stacking probabilities, and (via components) d001, cell params, even atom sets can
change, and with them the child's calculated pattern. There is **no
snapshot-on-detach**: the app does not bake the resolved values into the child
before severing. The `remove_phase` docstring's "the dependant keeps the values it
had stored" is literally true but easy to misread — it keeps its *own* stored
values, not the ones it was showing through inheritance.

### Known gaps (candidate work)

- **No integrity validator in the app** — the invariant above is enforced only by
  convention + the test harness. (This is the #5-class fragility from the
  per-phase audit, [[mudlab2-per-phase-audit]].) `verify_link_integrity.py` is the
  guardrail; there is no in-app `validate()`.
- **`remove_mixture` staleness** — no recompute/clear/refresh; orphaned specimens
  keep a frozen calc + per-phase overlay forever.
- **No snapshot-on-detach** — deleting a base silently shifts dependants' computed
  values (scenario 4). If we add snapshotting (bake resolved → own before
  severing), decide whether it is silent or user-confirmed.
