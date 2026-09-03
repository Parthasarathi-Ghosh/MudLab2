# From a published structure to a treatment series

**Method, theory and assumptions for CIF component import and the derivation of
treatment states.**

*Written 2026-08-30, when both features were built. This is a development
document: it names files and functions, and it records the reasoning and the
measurements so the method can be argued with later rather than rediscovered.
The user-facing account of the same science is in
[`how-it-works.md`](how-it-works.md); the instructions are in
[`user-manual.md`](user-manual.md).*

Two features, one pipeline:

```
published CIF ──▶ projection along c* ──▶ review ──▶ component in a phase
                                                            │
                                                            ▼
                                              derived -EG and -350 phases
```

**Contents**

1. [The two representations](#1-the-two-representations)
2. [Crystallographic background](#2-crystallographic-background)
3. [Why one dimension is enough](#3-why-one-dimension-is-enough)
4. [Reading the file](#4-reading-the-file)
5. [Bonding, in three dimensions](#5-bonding-in-three-dimensions)
6. [Folding a multi-layer cell](#6-folding-a-multi-layer-cell)
7. [Building the component](#7-building-the-component)
8. [What is guessed, and the review step](#8-what-is-guessed-and-the-review-step)
9. [Evidence](#9-evidence)
10. [Deriving treatment states](#10-deriving-treatment-states)
11. [Assumptions, stated to be challenged](#11-assumptions-stated-to-be-challenged)
12. [Known gaps](#12-known-gaps)
13. [Code and harnesses](#13-code-and-harnesses)

---

## 1. The two representations

A **CIF** (Crystallographic Information File) records a complete
three-dimensional structure: a unit cell, a set of symmetry operators, and a
list of atom sites with fractional coordinates, occupancies and displacement
parameters. It is the standard deposition format, and the reference corpus used
here comes from the American Mineralogist Crystal Structure Database via RRUFF.

A **MudLab component** records a one-dimensional profile: atom rows, each with
a height in nanometres, an amount, and an atom type, split into a *layer* set
and an *interlayer* set, plus a basal spacing and the cell's a and b lengths.

The gap between them is a projection, and it is lossy on purpose. Everything
below is about doing it defensibly and saying where it can be wrong.

---

## 2. Crystallographic background

### Unit cells and fractional coordinates

A crystal is described by a repeating box — the unit cell — with edge lengths
*a*, *b*, *c* and angles α (between b and c), β (between a and c) and γ
(between a and b). An atom's position is given as **fractional coordinates**
*(x, y, z)*, each the distance along the corresponding edge as a fraction of
its length. Fractional coordinates make the description independent of the
cell's absolute size.

Clay layers lie in the *a-b* plane and stack along *c*, so *z* is the
coordinate that matters here — but only after a correction, because in most
clays *c* is **not** perpendicular to the layers (see §3).

### Symmetry operators

A CIF normally lists only the **asymmetric unit** — the smallest set of atoms
from which the rest follow by symmetry — together with the operators that
generate the others. An operator is written as a coordinate triple such as
`-x, y+1/2, -z`. Applying every operator to every listed site, and wrapping the
results back into the cell, gives the full contents.

Skipping this step would under-count the structure badly. A C-centred monoclinic
cell in `C 1 2/m 1` has **eight** operators; reading only the listed sites would
give an eighth of the atoms and a correspondingly wrong composition.

### Space groups of clay minerals

A space group names the complete symmetry of a structure. Clay minerals occupy
a narrow range of them, because a phyllosilicate layer is built from a
pseudo-hexagonal net and its symmetry is largely fixed by how successive layers
are rotated and shifted. The reference corpus, 73 published structures, shows
the pattern:

| Space group | Count | Crystal system | Minerals in the corpus |
|---|---|---|---|
| `C 1 2/m 1` (C2/m) | 20 | monoclinic | illite, montmorillonite, chlorite, nontronite, hectorite |
| `P 3 1 m` | 16 | trigonal | lizardite |
| `P n c n` | 10 | orthorhombic | sepiolite |
| `C 1` | 5 | triclinic setting | kaolinite, chlorite |
| `C 1 c 1` (Cc) | 4 | monoclinic | vermiculite, kaolinite |
| `P 63 c m` | 4 | hexagonal | lizardite |
| `C -1` | 3 | triclinic | talc, chlorite |
| `P 1` | 3 | triclinic | lizardite, montmorillonite |
| `C 1 2 1` (C2) | 3 | monoclinic | illite, vermiculite |
| `C 1 2/c 1` (C2/c) | 2 | monoclinic | talc, vermiculite |
| `P -3 m 1` | 1 | trigonal | brucite |
| `P 63` | 1 | hexagonal | lizardite |
| `P 1 21/n 1` | 1 | monoclinic | sepiolite |

Three groupings, and each says something:

- **Monoclinic, C-centred** — the 2:1 minerals. The C-centring reflects the
  layer's own two-fold symmetry, and β is typically 95–105°, which is exactly
  why the projection needs care.
- **Trigonal and hexagonal** — the 1:1 trioctahedral serpentines. A lizardite
  layer keeps the hexagonal symmetry of its sheets because it has no
  interlayer cation to lower it, and its polytypes differ in how layers rotate
  by multiples of 60°.
- **Triclinic** — kaolinite and talc, where layer offsets break every axis.
  Kaolinite is the reason the projection cannot simply use *c* sin β: its cell
  has α ≈ 91.7°, β ≈ 104.9° and γ ≈ 89.8°, all different from 90°.

Sepiolite's orthorhombic `P n c n` is the outlier in more than symmetry: it is a
channel mineral, not a basal-repeat clay, and is refused on those grounds (§8).

### Polytypes, and cells that stack more than one layer

Clays of identical composition can stack differently. These **polytypes** are
named by the number of layers in the repeat and the resulting symmetry: 1M and
2M₁ and 2M₂ and 3T for micas, 1T and 2H₁ and 2H₂ for lizardite — all present in
the corpus.

For this method the consequence is arithmetic. A 2H polytype has a
crystallographic *c* covering **two** layers, so its cell's basal repeat is
twice the layer spacing a clay analyst means by *d*(001). Importing it without
noticing would give a component of double thickness with half the layers' worth
of atoms at each height. That is what §6 exists to prevent.

---

## 3. Why one dimension is enough

### Oriented mounts and the basal series

A clay preparation is made by settling platy crystals onto a flat surface so
their layers lie parallel to it — deliberately textured, because that is what
makes the basal reflections strong. What such a mount diffracts usefully is the
**00ℓ series**, which depends only on how scattering matter is distributed
along the stacking direction. Two atoms at the same height contribute
identically to a basal reflection however far apart they lie in the plane.

### The projection is exact

The relevant direction is **not** the crystallographic *c* axis but the normal
to the layers — the reciprocal-space direction **c\***. In a monoclinic or
triclinic clay these differ, and using *c* would be wrong.

Write the cell in a Cartesian frame with **a** along x and **b** in the x-y
plane. Then

```
a = (a, 0, 0)
b = (b cos γ, b sin γ, 0)
c = (c cos β, c (cos α − cos β cos γ)/sin γ, V / (a b sin γ))
```

Two facts follow immediately, and they are the whole justification:

1. **a and b have no z-component at all.** An atom's height above the layer
   plane therefore depends on its fractional *z* alone; *x* and *y* contribute
   nothing.
2. **The z-component of c is V/(a b sin γ)**, which is the (001) interplanar
   spacing — the basal spacing *d*(001).

So height = *z* × *d*(001), exactly. Verified numerically on triclinic
kaolinite: two atoms sharing a fractional *z* but with entirely different
(x, y) come out at the same height to **0.00e+00**.

The basal spacing is computed as **V / |a × b|**, which equals *c* sin β for a
monoclinic cell and remains correct for a triclinic one, where *c* sin β is not.

**Consequence for design:** a boundary that is a plane parallel to (001) sits in
the same place whether it is sought in three dimensions or after projecting, so
projecting first costs nothing in locating it. What projection destroys is *x*
and *y* — and therefore **bonding** — which is why §5 happens first.

### What is lost

The *hk* reflections; stacking faults expressed as lateral offsets; any
distinction between polytypes that differ only in layer rotation. None of this
is measured by a basal-series analysis of an oriented mount.

---

## 4. Reading the file

### CIF lexical structure

A CIF is more structured than it looks, and three features must be handled or
the reader silently invents data. All three are documented in the American
Mineralogist CIF Guide, and none is exercised by the reference corpus — every
file parsed while the reader was still wrong about them.

- **Data blocks.** A file may hold several, each beginning `data_`, and the
  guide *requires* one per refinement when a paper reports more than one
  structure. Merging their atom sites would fabricate a structure that was
  never published. Only the first block carrying an atom-site loop is used.
- **Semicolon-delimited text.** A value may span lines between `;` markers and
  contain anything at all, including lines that look like tags or atom rows —
  `_refine_special_details` routinely describes constraints in prose. Such
  blocks are skipped whole.
- **Comments.** A `#` outside quotes begins a comment, and one may sit on its
  own line *inside a loop header*; the guide's own multiple-occupancy example
  annotates a tag list that way. Stopping the tag list at the comment destroys
  the loop.

Loop bodies are read as a **token stream chunked by the tag count**, not one
row per line, because CIF places no such requirement on layout and a long row
may wrap.

Numbers carry a standard uncertainty in parentheses — `5.2000(19)` — which is
stripped everywhere.

### Which tag is authoritative

`_atom_site_type_symbol` names the chemical species and is used first;
`_atom_site_label` is a site identifier and is only a fallback. That ordering
matters because labels are free-form: real files use `SiT1`, `Fe2+M`, `AlM2`,
`O-H3`. An `O-H` label is also taken as a declaration that the oxygen is a
hydroxyl — better evidence than any distance test can produce.

A site with zero occupancy is a declared vacancy and is not an atom.

### Symmetry expansion, and files without operators

Every operator is applied to every site and the results wrapped into the cell,
duplicates dropped. A file with no operator loop is read as **P1** — and said
so, in the report, because if the true cell is not P1 the structure is missing
atoms and every amount is too low.

Generating operators from a space-group *name* is deliberately not attempted.
It would mean shipping the operator sets for 230 groups with their settings and
origin choices, and getting that subtly wrong is worse than not doing it: the
structure would look right while carrying wrong multiplicities, so every
amount, and therefore the reported composition, would be wrong with nothing on
screen to say so. Every corpus file has explicit operators, because American
Mineralogist requires them.

---

## 5. Bonding, in three dimensions

### Why before projection

Projection preserves height exactly but destroys *x* and *y*. Two oxygens can
sit at the same height and be chemically different — one bridging between
silicon tetrahedra, one a hydroxyl in the octahedral sheet, one a water
molecule in the gallery. Only their **neighbourhoods** separate them, and the
neighbourhood is three-dimensional. So every site is classified before the
profile is collapsed, and the verdict travels with it.

### The criteria

Ordinary crystal chemistry, applied with periodic boundary conditions over the
26 neighbouring cell images:

| Bond | Cut-off | Meaning |
|---|---|---|
| Si–O | 1.85 Å | tetrahedral coordination |
| M–O (Al, Mg, Fe, …) | 2.35 Å | octahedral coordination |
| O–H | 1.25 Å | hydroxyl |

and the classification that follows:

- an oxygen **bonded to Si** is a framework oxygen — bridging or apical;
- an oxygen with **no Si neighbour but coordinated to octahedral cations** is a
  **hydroxyl**: in a phyllosilicate the OH sits in the octahedral sheet and
  never bonds to silicon;
- an oxygen bonded to **neither** is a **guest** — interlayer water;
- a cation coordinated to layer anions is framework; one that is not is an
  interlayer cation.

The hydroxyl/water distinction is the one the projected profile cannot make,
and getting it wrong is not cosmetic: hydroxyl and water are different
scatterers, tabulated separately. Tested on the vermiculite structures, the rule
correctly separates 6–8 water oxygens that a height rule merges into the layer.

Hydrogen itself is **evidence, not a row**: it decides which oxygens are
hydroxyls and is then dropped, because MudLab models OH as a single scatterer
and has no hydrogen atom type.

---

## 6. Folding a multi-layer cell

### Detecting the repeat

A published cell may stack two or more identical layers (§2, polytypes). The
repeat is detected **on the projected profile**, not on the 3-D sites: the
profile is tested for invariance under a shift of 1/n along the stacking
direction, for n = 4, 3, 2.

Testing in three dimensions instead misses exactly the cells worth folding,
because successive layers are usually displaced in *a* and *b* as well as in
*c* — talc's two-layer cell by roughly −a/3 — and those offsets defeat a 3-D
match while being invisible along c\*. This is the one place where losing *x*
and *y* helps.

### The merge rule

Folding maps every level into one repeat. Coincident levels **merge by summing**
their amounts, and the 1/n scale is applied once at the end.

The alternative — keeping the larger of two coincident levels and discarding the
rest, while still dividing by n — counts shared content once and then halves it
again. Measured on the corpus: **0 of 12** folded cells preserved their anion
totals before this was corrected; **11 of 12** after, with the twelfth failing
for an unrelated reason.

---

## 7. Building the component

### Origin

One repeat has to start somewhere. The origin is placed **immediately after the
widest empty band** in the profile — that band is the interlayer gap, so the
layer lands at the bottom and the interlayer above it, which is the arrangement
MudLab's own shipped components use: Muscovite's basal oxygen sits at 0.0 and
its interlayer potassium at 0.831 of a 1.002 nm repeat. Anchoring on the lowest
atom instead splits the layer across the wrap.

Verified against a real import: illite comes out with basal oxygen at 0.0000 and
potassium at 0.8365 — the shipped Muscovite convention, reproduced from the CIF.

### Rows, amounts and atom types

Sites are grouped by species and height into rows. A row's amount is the summed
occupancy of its sites, divided by the fold divisor. Heights are converted to
nanometres.

Each row is mapped to one of MudLab's clay atom types — the ionised forms the
shipped components use (`Si2+`, `Al1.5+`, `O1-`, `OH1-`, `H2O`, `K1+` …),
because a neutral atom and an ion scatter measurably differently. Water maps to
its own type, not to hydroxyl: they differ by a whole hydrogen.

If the destination project lacks a type the structure needs — importing a
montmorillonite into a project built from illite needs magnesium and lithium —
it is named before the import is accepted and added on acceptance. Left
unresolved, those rows would contribute nothing to the calculated pattern,
silently, which is the worst way for a structural import to be wrong.

### Compatibility constraint

The old GTK MudLab deserialises each object with `cls(**properties)` and raises
on any key it does not know. An imported component therefore serialises with
**exactly the keys a hand-built one uses** and no others. There is consequently
nowhere to record that a component came from a CIF, and no field is invented
for it: the component **name** is the only text that travels, which is why the
name is proposed as mineral plus file identifier (`Chlorite 0004284`) — nine
corpus files are called "Chlorite" and would otherwise be indistinguishable.

---

## 8. What is guessed, and the review step

Four decisions cannot be made with certainty, and measurement says each can be
wrong. None is applied silently: the review dialog shows all four and nothing
replaces a component until it is accepted.

| Decision | Why it can be wrong |
|---|---|
| **Layers stacked in the cell** | polytype cells look like thick single layers |
| **O / OH / H₂O per row** | marginal coordination, or a file with no hydrogen |
| **Layer or interlayer per row** | trace substituents and unusual galleries |
| **Basal spacing** | follows from the fold |

The **layer type** is proposed rather than asked: counting tetrahedral sheets in
the projected layer separates the corpus cleanly — one sheet is 1:1 (kaolinite
5/5, lizardite 22/22), two is 2:1 (illite 7/7, talc 3/3, montmorillonite 4/4).
A 1:1 clay with anything in its interlayer is flagged, and that immediately
caught a real misclassification: kaolinite `0020861` places trace calcium
(amount 0.012) at 0.34 nm — mid-layer in a 0.715 nm repeat — into the gallery.

**Refused outright:** sepiolite and palygorskite. They are channel (fibrous)
minerals; MudLab models a layer and an interlayer and has nowhere to put
channel guests, so an import would produce something that looks like a clay and
is not one.

---

## 9. Evidence

### The corpus

73 published clay structures from RRUFF/AMCSD, kept outside the repository
(they are not ours to redistribute). `MUDLAB_CIF_CORPUS` points the harness at
a copy; absent, it skips rather than failing.

### The oracle problem

**Textbook mineral formulas are not a valid oracle**, and learning that cost a
full measurement pass. Published cells differ in setting, in Z, and in
occupancy convention; and the corpus contains a **fluor-hectorite** whose
"missing" hydroxyls are fluorine. An early assessment reported 37 of 73
structures as suspect, and most of those were the oracle's fault, not the
projector's.

What can be checked honestly is:

1. **Faithfulness** — does the projected profile still hold the anion content
   the CIF itself states, folded the same way?
2. **Agreement with MudLab's own shipped components**, which are real ground
   truth for the minerals they cover.

### Results

Faithfulness: **73 of 73**, every family, both fold divisors.

Against shipped components, swapping the imported component into the shipped
phase and comparing calculated patterns:

| Mineral | Basal spacing, shipped → imported | Pattern correlation |
|---|---|---|
| Kaolinite | 0.7160 → 0.7154 nm | **0.9994** |
| Illite | 0.9980 → 1.0018 nm | 0.9537 |
| Talc | 0.9400 → 0.9351 nm | 0.9530 |
| Chlorite | 1.4200 → 1.4265 nm | 0.9347 |

Every atom type resolved in all four.

---

## 10. Deriving treatment states

### The problem

Clay identification rests on how a mineral responds to treatment: the standard
sequence is **air-dried → ethylene-glycol solvated → heated**, and it is
diagnostic because different clays respond differently. Smectite expands under
glycol and collapses on heating; vermiculite collapses on heating but expands
less under glycol; illite and kaolinite do neither; chlorite keeps its 1.42 nm
reflection through both.

Modelling that needs one phase per treatment, assigned to the matching specimen
column of a mixture. But a CIF is one structure in one state, and the
crystallographic record is essentially always the air-dried form — nobody
deposits a refinement of the same specimen after solvation, because a solvated
smectite is not a good single-crystal subject. The treated states have to be
constructed.

### The physical claim it rests on

**A treatment changes the interlayer, not the layer.** Solvation and heating
add, replace or remove species in the gallery and therefore change the basal
spacing; they do not restructure the 2:1 sandwich.

This is not invented here. MudLab's own shipped components are built on it: all
six states of Di-Smectite (2WAT, 1WAT, Dehydr, 2GLY, 1GLY, Heated) carry the
**identical ten layer atoms** and differ only in `d001` and `interlayer_atoms`.
The catalog then links them, a treated component inheriting `ucp_a`, `ucp_b`,
`delta_c` and `layer_atoms` from the air-dried one
(`default_catalog._INHERIT_S`).

### The method

Given a phase whose single component is a 2:1 clay:

1. **Take the layer by LINK, not by copy.** The derived component sets
   `linked_with` to the base and turns on those four inherit flags.
   Consequence: refining the layer refines every state at once, which is the
   whole reason to model a series rather than three unrelated phases.

2. **Take the gallery from the corresponding shipped state** — its interlayer
   species and the space they occupy.

3. **Transplant by gallery HEIGHT, not by absolute z:**

   ```
   gallery  = donor.d001 − donor.layer_top
   new d001 = base.layer_top + gallery
   shift    = base.layer_top − donor.layer_top     (applied to every guest)
   ```

   A shipped 2:1 layer tops out at 0.654 nm and an imported illite layer at
   0.671. Copying interlayer heights verbatim would drive the guests 0.017 nm
   *into* the layer beneath. What a treatment actually changes is the
   **thickness of the gallery**, so that is what carries across, and the
   derived spacing differs from the donor's by exactly the layer-thickness
   difference. Checked to 1e-9.

4. **Create the phases** — `<name>-EG` and `<name>-350`, each `based_on` the
   original and inheriting its colour, σ\* and CSDS distribution, matching what
   the catalog does for a treated phase (`_INHERIT_PHASE`).

A worked result, from an imported illite:

```
base            d001 1.0018 nm   layer top 0.6712   gallery 0.3306
  -EG           d001 1.7032 nm   gallery 1.0320  (the donor's, exactly)
  -350          d001 0.9772 nm   gallery 0.3060
```

### What is asked, and why it cannot be computed

- **Which family's gallery to borrow** — Di-Smectite, Tri-Smectite or
  Di-Vermiculite. Smectite and vermiculite differ by **layer charge**, a
  chemical property invisible both to a diffraction pattern and to a single
  refined structure. Di- versus trioctahedral *could* be guessed from
  octahedral occupancy, but guessing half a choice is worse than asking for all
  of it.
- **Which state the phase is already in.** A published structure is usually
  air-dried but not reliably: the four corpus montmorillonites project to
  **0.97, 1.11, 1.22 and 1.22 nm** — dehydrated through one water layer.
  Assuming air-dried would silently mis-anchor the series.

### What is refused, and on what grounds

- **1:1 clays.** No interlayer gallery, no swelling, no glycolated state to
  derive. Detected by counting one tetrahedral sheet.
- **Chlorite-like structures.** 2:1 by sheet count, but the interlayer is a
  continuous hydroxide (brucite) sheet rather than exchangeable guests —
  octahedral cations in the interlayer are the signature. Filling that with
  glycol would model a mineral that does not exist.
- **Multi-component phases.** No single layer to share, so the one-to-one link
  the method depends on is unavailable.

Detecting a tetrahedral sheet by matching the literal name "Si" is not enough,
and getting this wrong once made kaolinite unclassifiable: the shipped
Kaolinite splits one sheet into `Si1`/`Si2`, Serpentine writes `" Si"` with a
leading space, and Chlorite uses the mixed-layer convention `DiSi`/`TriSi`. All
are silicon.

---

## 11. Assumptions, stated to be challenged

**Import**

1. **The oriented mount justifies a 1-D model.** True for basal-series analysis;
   false if you want *hk* information.
2. **The CIF's occupancies are the composition.** Site occupancies from a
   refinement are model-dependent, and a structure refined with a constrained
   chemistry carries that constraint into MudLab.
3. **Bond-length cut-offs classify coordination correctly.** Fixed cut-offs
   misjudge a strained or unusually long bond; a bond-valence treatment would
   be more principled.
4. **A file without symmetry operators is P1.** Stated in the report rather
   than assumed silently, but it is still what happens.

**Treatment states**

5. **The layer is invariant under treatment.** True to first order and the
   basis of the shipped components, but not exact: glycol can flex a layer, and
   heating ultimately dehydroxylates it. At 550 °C the layer is *not* the same
   object, so a derived `-350` should be read as a 350 °C model, not a 550 °C
   one.
6. **A gallery is transferable between clays of the same family.** The derived
   state wears a *reference* gallery, not this specimen's. A starting point for
   refinement, not a measurement.
7. **Gallery thickness is the transferable quantity**, rather than the guests'
   absolute positions. This is what makes the transplant layer-independent.
8. **One donor state per treatment.** EG takes 2GLY, heated takes Heated. Real
   smectites are usually interstratified and glycolate to a *mixture* of one-
   and two-layer states.
9. **Calcium is the exchangeable cation.** Every shipped family is the Ca form;
   a Na- or K-saturated clay swells differently.

---

## 12. Known gaps

- **Space-group-name-only CIFs** are read as P1 and under-expanded. The honest
  fix is a vetted operator table for the dozen groups clays actually use — the
  corpus needs `C 1 2/m 1`, `P 3 1 m`, `P n c n`, `C 1`, `C 1 c 1`, `P 63 c m`,
  `C -1`, `P 1`, `C 1 2 1`, `C 1 2/c 1`, `P -3 m 1`, `P 63` and `P 1 21/n 1`.
- **A row's element cannot be corrected** in the review dialog; Kind and Sheet
  can. Since the agreed policy is that ambiguity belongs to the user, a misread
  cation should be correctable too.
- **Interstratification** — the largest gap in the derivation (assumption 8). A
  real glycolated smectite is modelled as an R0/R1 mixture of hydration states,
  and the catalog already has the ladders (`_smectite_columns`). Deriving a
  *ladder* rather than a single state is the natural next version.
- **Only 350 °C**, and only the calcium form.
- **The stated base state is recorded but not used.** It is asked and kept in
  the series name; it should change what is derived, since a phase already
  glycolated needs no glycolated sibling.
- **Displacement parameters are discarded.** A CIF's per-site thermal
  parameters are not carried into the component, which uses its atom type's.

---

## 13. Code and harnesses

| | |
|---|---|
| `src/mudlab/file_parsers/cif_component.py` | reader, symmetry, bonding, fold, projection, component |
| `src/mudlab/cif_import_dialog.py` | the review step |
| `src/mudlab/component_widget.py` | *Import CIF…* in the component pane |
| `src/mudlab/treatment_variants.py` | `can_derive`, `transplant_gallery`, `derive` |
| `src/mudlab/treatment_states_dialog.py` | the two questions |
| `src/mudlab/edit_phases_dialog.py` | *Create treatment states…* |

| Harness | Checks | Needs the corpus |
|---|---|---|
| `tools/verify_cif_component.py` | 42 | yes — skips with exit 2 without it |
| `tools/verify_cif_import_dialog.py` | 42 | no |
| `tools/verify_treatment_states.py` | 33 | no |
