# MudLab2 user manual

Guide to using the MudLab2 GUI. This manual grows as features are added.

For the science behind what the program computes — what a clay layer is, how stacking is modelled, what the instrument corrections assume — see
[How MudLab works](how-it-works.md).

## Contents

- [Opening projects (including PyXRD files)](#opening-projects-including-pyxrd-files)
- [Adding and removing phases](#adding-and-removing-phases)
- [Phase inheritance ("based on")](#phase-inheritance-based-on)
- [Component linking and inheritance](#component-linking-and-inheritance)
- [Building a component from a CIF](#building-a-component-from-a-cif)
- [Treatment states: air-dried, glycolated, heated](#treatment-states-air-dried-glycolated-heated)
- [Atom relations (substitutions and contents)](#atom-relations-substitutions-and-contents)
- [Mixtures: assigning phases to slots](#mixtures-assigning-phases-to-slots)
- [Measured (XRF) composition](#measured-xrf-composition)
- [Refining a mixture](#refining-a-mixture)
- [Importing measured patterns (CSV options)](#importing-measured-patterns-csv-options)
- [Preparing experimental data](#preparing-experimental-data)
- [Peaks, peak detection, and mineral matching](#peaks-peak-detection-and-mineral-matching)
- [The goniometer emission spectrum](#the-goniometer-emission-spectrum)
- [Viewing the plot](#viewing-the-plot)

---

## Opening projects (including PyXRD files)

**Project → Open** loads a MudLab project (`.mud`). It also opens **PyXRD
projects (`.pyxrd`)** directly — pick either type in the file dialog.

A `.pyxrd` opens as a **conversion**: MudLab2 reads it, but the next **Save**
writes a new `.mud` file next to it (your original `.pyxrd` is never changed).
The project is marked unsaved when it opens, to remind you to save the `.mud`.

> **One caveat for PyXRD files.** A pattern *calculated by PyXRD* has a
> different absolute intensity scale from MudLab2's (the peak *shape* is the
> same — only the overall height differs, and the fit scales it automatically).
> So if you need a reference pattern to check MudLab2's calculation against,
> recompute it in MudLab2 (**Refresh**) after opening, rather than trusting the
> stored PyXRD pattern.

---

## Adding and removing phases

A **phase** is one diffracting clay in your model. Phases live in the project
and are edited in **Edit → Edit Phases**; the list on the left is the project's
phases, and the buttons beneath it add and remove them.

### Adding a phase

Press **Add** to open the Add Phase dialog, which offers three kinds of phase.

**Empty phase** — build one from scratch:

- Choose the **stacking order (R)** and the number of **components** (G):
  - **R0** — random, independent layer stacking. Available for 1–6 components.
  - **R1** — nearest-neighbour ordering (each layer depends on the one before
    it). Available for 2 components; choosing R1 fixes G at 2.
- You get that many blank components, named *Component 1*, *Component 2*, …
  which you then fill in on the Components tab.
- Press OK. The new phase appears in the list, selected and ready to edit — give
  it a name and define its components, atoms, stacking parameters and CSDS.

**Default phase** — pick a ready-made reference clay from the **built-in
catalog** (Kaolinite, Illite, Chlorite, Talc, the Ca-smectites and
-vermiculites, and interstratified Illite-/Kaolinite-/Talc-/Chlorite-Smectite at
R0 and R1). Choosing one adds it complete with its atoms and scattering factors,
so it computes immediately — a ready starting point you can then adjust. An
expandable clay is added as a **treatment triple** (Ca-AD / Ca-EG / Ca-350),
where the glycolated and heated forms are *based on* the air-dried one and share
its layer structure and stacking, differing only in the interlayer.

**Raw pattern phase** — a phase carrying a measured pattern (imported afterwards
in the editor), for a non-modelled component such as quartz or an internal
standard.

Longer-range ordering (**R2, R3**) and R1 with more than two components are not
available yet, so catalog entries needing them are not listed.

### Removing a phase

Select a phase and press **Remove**. Because deleting a phase cannot be undone,
MudLab2 asks you to confirm.

**A phase that a mixture uses cannot be deleted.** MudLab2 tells you which
mixture holds it and in how many cells, and stops there — nothing is asked and
nothing is changed. To delete it, open **Edit Mixtures** first and free it: set
those cells to **(none)**, or remove the phase slot entirely. Then Remove works.

This is deliberate. A phase sitting in a mixture is part of a model you have
built and probably refined; silently blanking its cells would change what that
model means without telling you.

Removing a phase that is *not* in any mixture also cleans up everything that
pointed at it, so nothing is left dangling:

- any phase that was **based on** the removed one stops inheriting and keeps the
  values it currently shows (it falls back to its own stored numbers);
- any component **linked** to one of the removed phase's components is unlinked.

Being a reference for another phase does **not** count as "in use" — you can
delete a base phase whose children still inherit from it, and their values are
kept (see below).

The removal takes effect immediately in the calculated pattern. As with every
edit, nothing is written to disk until you save the project, so a removal you
did not mean can be undone by closing without saving.

---

## Phase inheritance ("based on")

### What it is

The same clay is normally measured under several **treatments** — air-dried,
ethylene-glycol solvated, and heated. The treatments change the interlayer (a
smectite swells under glycol and collapses on heating) but *not* the mineral
itself: its crystallite size, orientation and stacking order are the same clay.

So you model one phase per treatment and **base the treated phases on a
reference phase** (usually the air-dried one). The treated phase then *inherits*
the treatment-independent parameters, and you only adjust what the treatment
actually changed.

The pay-off is in fitting: an inherited parameter exists **once**. Refine it on
the reference phase and every treatment follows — the same clay cannot come out
with a different structure per treatment, and you are not fitting the same
number three times.

### Where to find it

**Edit → Edit Phases**, select a phase. The **Based on** drop-down is at the top
of the phase properties.

### Basing one phase on another

1. In **Based on**, choose the reference phase.
   Only phases with the **same number of components** are offered — the layer
   stacking parameters pair up one-to-one, so the counts must match.
2. The inherit check-boxes become enabled. Nothing is inherited yet.

### Choosing what to inherit

- **σ\*** — tick *Inherit* next to the σ\* box.
- **CSDS distribution** — tick *Inherit from the "based on" phase* on the CSDS
  tab.
- **Stacking probabilities** — on the Probabilities tab each stacking parameter
  has its own *Inherit* box, so you can share some and keep others. The
  parameters shown depend on the phase's stacking order: an **R0** phase lists
  its **F** parameters; an **R1** phase lists **W1** and the junction
  probability **P11 / P22**.
- **Display colour** — tick *Inherit* next to the colour swatch, so a treated
  phase shares its reference's plot colour.

A ticked box greys the field and shows the **reference phase's** value. Untick it
and the phase goes back to its own value. The pattern recalculates either way.

> **The stacking parameters matter most.** They control the layer proportions
> and ordering, and therefore the shape of the pattern. If a treated phase
> should have the same illite/smectite ratio as the reference, inherit its
> stacking parameters — otherwise the two can drift apart and no longer describe
> the same clay.

### Changing an inherited value

An inherited field is greyed on the treated phase. Edit it on the **reference
phase** (the one showing *(not based on)*) and every phase based on it updates.

### Detaching

Choose **(not based on)**. If the phase is currently inheriting any values, you
are asked whether to **keep** them — the values it is showing are copied into the
phase so nothing changes — or **revert to own**, which returns every field to that
phase's own stored values (the older behaviour). The inherit boxes are cleared
either way.

Deleting the reference phase itself does the same automatically: the phases that
depend on it are detached but their current values are kept, so their patterns do
not change. The delete confirmation names those dependants.

---

## Component linking and inheritance

### What it is

A clay **phase** is built from one or more **components** — the individual clay
layers it is made of. In many projects the *same* layer appears in more than one
phase. A classic example: an illite layer exists both as a discrete **Illite**
phase and inside an **illite–smectite** mixed-layer phase; a smectite layer
appears in its air-dried, glycolated and heated forms.

Rather than re-entering that layer's structure in every phase, MudLab2 lets one
component **link** to another and **inherit** part of its definition. The linked
component is the *template*; the one that links to it reads the chosen
properties straight from the template. Change the template once and every
component that inherits from it updates automatically.

Inheritance is **per-property**. A glycolated smectite can inherit its cell
dimensions and layer atoms from its 2-water template while keeping its *own*
basal spacing (d001) — which is exactly what makes it a different swelling
state.

### Where to find it

1. Open **Edit → Edit Phases** (or the Phases toolbar button).
2. Select a phase in the list on the left.
3. Open the **Components** tab.
4. Pick a component in the **Component** drop-down at the top.

The **Component linking** group sits below the component's properties. It has:

- a **Linked with** drop-down, and
- a row of **inherit** check-boxes (Cell a, Cell b, Cell c / default c, Δc,
  Layer atoms, Interlayer atoms, and two read-only ones — see *Notes*).

### Linking a component to a template

1. In **Linked with**, choose the template component. The list shows every
   component in the project as `Phase name / Component name`.
2. The inherit check-boxes become enabled. Nothing is inherited yet — linking on
   its own does not change any values.

### Choosing what to inherit

Tick the check-box for each property you want this component to take from its
template:

- **Ticking a box** greys out that field and shows the template's value there.
  The pattern recalculates immediately.
- **Un-ticking a box** hands the field back to this component and restores its
  own value.

For example, tick **Cell a**, **Cell b** and **Layer atoms** on a glycolated
smectite to share the silicate layer with its 2-water template, but leave
**Cell c / default c** un-ticked so it keeps its own expanded spacing.

### Changing an inherited value

An inherited field is greyed on the linked component — you cannot edit it there,
because it belongs to the template. To change it, select the **template**
component (the one shown with *(not linked)*) and edit it. Every component that
inherits that property updates at once.

### Unlinking

Choose **(not linked)** in the **Linked with** drop-down. If the component is
currently inheriting any values, you are asked whether to **keep** them (copied
into this component so nothing changes) or **revert to own** (return every field
to this component's own stored values). The inherit boxes are cleared either way.

### Notes and tips

- **Inherited cell a / b also lock the cell-length editor.** When Cell a or
  Cell b is inherited, that cell's fixed/derived editor is disabled — the value
  comes from the template.
- **Two inherit check-boxes are fixed:** *d001 (follows cell c)* mirrors the
  Cell c / default c setting, and *Atom relations* inheritance is not
  independently toggleable yet (a linked component still follows its template's
  relations). The atom-relations **editor** itself is fully available — see
  [Atom relations](#atom-relations-substitutions-and-contents).
- **A component cannot link to itself**, and links cannot form a loop
  (A → B → A). Such a choice is refused and the drop-down snaps back.
- **You can link any two components.** MudLab2 does not restrict templates to a
  particular parent phase, so take care to link layers that really are the same
  clay layer.

---

### Seeing the structure

**Show Structure**, in the component pane, draws the component as a labelled
cross-section: the `d001` boundary at the top, the interlayer and what the atom
relations put in it, the `lattice_d` boundary, then the sheets — tetrahedral and
octahedral, named — with every atom's z position, `pn` and type, down to z = 0.
A 2:1 clay shows a lower and an upper tetrahedral sheet; a 1:1 clay shows one.
The octahedral sheet is labelled **dioctahedral** or **trioctahedral** from its
cation occupancy.

It reads the live model, so it shows the values the relations have actually
applied. The window stays open while you edit — it is meant to be read
alongside the editor, not instead of it. **Copy** puts the diagram on the
clipboard and **Save as text…** writes it to a `.txt` file.

> **Why does it say the charge is imbalanced?** Because the charge shown comes
> from each atom type's **scattering** ion, not its formal valence. A stock
> kaolinite reads −4.000 for that reason alone, refined or not. Treat the number
> as a relative check between your own edits, not as a verdict on the mineral.

## Building a component from a CIF

A published crystal structure can be turned into a component directly.
**Edit Phases → Components tab → Import CIF…** reads a `.cif` file, projects
its three-dimensional structure onto the c\* axis, and offers the result as a
replacement for the selected component.

The projection is genuinely lossy, and deliberately so: a CIF holds full
crystallographic coordinates, while a MudLab component holds a one-dimensional
profile — atom rows with a height and an amount, split into layer and
interlayer. Everything the projection has to *decide* is shown for review
before anything is replaced.

### The review window

**Nothing changes until you press OK.** The window has three parts.

**Component name.** Proposed from the mineral name and the file. The mineral
name alone is often not enough to tell two structures apart — a library of clay
CIFs can hold a dozen files all called *Chlorite* — so the file's identifier is
appended: *Chlorite 0004284*. Edit it freely; this name is the only thing that
travels with the component to say where it came from.

**1. What the projection had to decide.**

- **Layer type** — *1:1* or *2:1*, worked out from how many tetrahedral sheets
  the projected layer contains. A 1:1 clay (kaolinite, serpentine) has no
  interlayer to fill and does not swell; a 2:1 clay does. If a 1:1 structure
  comes out with something in its interlayer, the warning line says so, because
  that is a sign the split went wrong.
- **Layers stacked in the published cell** — many published cells contain two
  identical layers stacked along c. MudLab folds them to one. Change this if
  the basal spacing below is a multiple of what you expect; the projection
  re-runs immediately.
- **Basal spacing d001** — taken from the cell. Editable.
- A **warning line** appears beneath when something needs attention: a 1:1 clay
  with interlayer rows, atom types the project is about to gain, or a file that
  declares no symmetry operators.

**2. Projected atoms.** One row per level of the profile:

| Column | Meaning |
|---|---|
| **Atom** | the element, from the CIF |
| **Kind** | for oxygen rows only: **O**, **OH** or **H2O** |
| **z (nm)** | height above the bottom of the layer |
| **pn** | how many of that atom the cell contains |
| **Sheet** | **Layer** or **Interlayer** |

**Kind** and **Sheet** are the two the projection is most likely to get wrong,
and both are drop-downs. A hydroxyl and a water molecule are told apart by
which cations the oxygen is bonded to in the original structure — a judgement
that a marginal case can fail. Kind selects the scattering factor, so it
changes the calculated pattern; it does not affect the reported oxide
composition, which is computed from the cations.

**Reset to proposal** discards your edits and returns to what the projection
first offered.

### Atom types are added for you

A structure often needs an element the project has never used — importing a
montmorillonite into a project built from illite needs magnesium and lithium.
Those are named in the warning line before you accept and added on OK. Without
them the rows would resolve to nothing and contribute nothing to the calculated
pattern, silently, so this is not left to chance.

### What it will not import

**Sepiolite and palygorskite are refused.** They are channel (fibrous)
minerals, not basal-repeat clays; MudLab models a layer and an interlayer and
has nowhere to put channel guests, so an import would produce something that
looks like a clay and is not one.

> **A CIF with no symmetry operators is read as P1.** Most published files
> list their operators explicitly, and the import uses them. A file that names
> only a space group cannot be expanded — MudLab says so in the warning line
> rather than guessing, and if the true cell is not P1 the structure is missing
> atoms and every amount is too low. Treat such an import with suspicion.

Everything the import produces is a **starting point for refinement**, not a
measurement of your sample.

---

## Treatment states: air-dried, glycolated, heated

Clay identification depends on how a mineral responds to treatment — smectite
expands under ethylene glycol and collapses on heating, vermiculite behaves
differently again, illite and kaolinite do neither. Modelling that needs one
phase per treatment, assigned to the matching specimen in a mixture.

A published structure gives you only one of them. **Edit Phases → right-click a
phase → Create treatment states…** builds the other two.

### What it creates

Two new phases, named after the original: **-EG** (glycolated) and **-350**
(heated). Each is *based on* the original phase, and its component is *linked*
to the original's component, inheriting the layer, the cell and delta c while
keeping its own basal spacing and interlayer.

That linking is the point. **Refine the layer once and all three states follow**
— which is what makes a treatment series a model of one mineral rather than
three unrelated phases. Assign them to your glycolated and heated specimens in
Edit Mixtures.

### The two questions it asks

- **Gallery from** — *Di-Smectite*, *Tri-Smectite* or *Di-Vermiculite*. The new
  states borrow their interlayer from one of MudLab's shipped families. Whether
  a 2:1 clay is a smectite or a vermiculite is a matter of layer charge, which
  a single refined structure does not reveal, so this cannot be worked out from
  the file.
- **This phase is** — which state the phase is already in. A published
  structure is usually air-dried, but not reliably: real montmorillonite
  structures span dehydrated to one water layer.

### What it will not do

- **1:1 clays.** Kaolinite and serpentine have no interlayer gallery, do not
  swell, and have no glycolated state to derive.
- **Chlorite-like structures.** A chlorite is 2:1 but its interlayer is a
  continuous hydroxide sheet rather than exchangeable guests — it does not
  swell either, and MudLab recognises it by the octahedral cations sitting in
  the interlayer.
- **Multi-component phases.** A mixed-layer phase has no single layer to share.

> **Read the derived states as models, not measurements.** They wear a
> *reference* gallery taken from a shipped clay, not your specimen's, and they
> assume the treatment leaves the layer unchanged. That holds well for glycol
> and for moderate heating — but at 550 °C a clay dehydroxylates and the layer
> genuinely changes, so treat **-350** as a 350 °C model and not a 550 °C one.
> Every shipped family is the calcium form; a sodium- or potassium-saturated
> clay swells differently.

---

## Atom relations (substitutions and contents)

On the **Components** tab, the **Atom relations** group ties atom occupancies
together so a chemical constraint is enforced automatically. Use the selector to
pick a relation, or **Add ratio** / **Add contents** to make one; **Delete**
removes the selected relation.

### Ratio — a substitution between two atoms

An **atom ratio** shares one site between two atoms (e.g. octahedral Fe-for-Mg).
You set a **value** (the substituting fraction, 0–1) and a **sum** (the total
occupancy); MudLab2 then sets the substituting atom to `value × sum` and the
original atom to `(1 − value) × sum`. Pick the two atoms, and the occupancies —
and any cell length that derives from them — update as you edit.

### Contents — scale a set of atoms by one value

An **atom contents** relation multiplies several atoms by a single **value**
(e.g. an interlayer K / Ca / H₂O content): each row is a **target** and an
**amount**, and the target gets `amount × value`. Add or remove rows with the
buttons; set each row's target and amount in the table.

### Chaining relations together

A contents row's target doesn't have to be an atom — it can be **another
relation**, letting one relation drive another (multi-substitution). In the
Target drop-down a ratio appears as *"name: RATIO"* (drives its value) and
*"name: SUM"* (drives its sum); another contents appears by name (drives its
value). MudLab2 **refuses a target that would form a loop**. A relation that is
driven this way shows a computed value — you no longer set it directly.

### Refining a relation's value

A relation's **value** can be refined like any structural parameter: it appears
in the **Refine** window, where you flag it and set bounds. Inherited, disabled,
and driven relations are not offered (their value isn't independently free).

---

## Mixtures: assigning phases to slots

A **mixture** ties your phases to your measured specimens. Open it from
**Edit → Edit Mixtures**; the list on the left is the project's mixtures, and
selecting one shows its grid.

**Add** (below the list) creates a new, empty mixture called *New Mixture*,
selected and ready to build — rename it and use the **Add phase / Add specimen**
buttons (below) to fill in the grid. **Remove** deletes the selected mixture
(after confirming). As always, nothing is written to disk until you **Save**.

### Reading the grid

The grid has one **row per phase slot** and one **column per specimen**, plus:

- a **Fraction** column (the phase fraction for each slot), and
- two header rows at the top — **Abs. scale** and **Bg. shift**, one value per
  specimen.

Each phase cell (a slot × a specimen) names **which phase fills that slot for
that specimen**. Because it is per cell, the *same* slot can hold a *different*
phase in different specimens — e.g. the air-dried, glycolated and heated forms
of one clay across three columns.

You can type directly into any numeric cell — the **Fraction** for each slot and
the **Abs. scale** / **Bg. shift** for each specimen — and the pattern redraws as
soon as you press Enter. A value that will not parse is rejected and the old one
restored.

### Choosing which fractions Optimize refines

Each **Fraction** cell has a **checkbox**. It decides whether **Optimize** is
allowed to change that phase's fraction:

- **Ticked** (the default) — Optimize refines the fraction along with the others.
- **Unticked** — the fraction is **held fixed** at whatever value you typed.
  Optimize leaves it exactly as set and adjusts only the remaining (ticked)
  fractions, rescaling them so all the fractions still add up to 1.

Untick a box when you already **know** a phase's proportion — for example an
internal standard you weighed in — and want to set it by hand while the fit
solves for the rest. The setting is saved with the project.

### Assigning a phase to a slot

Click a phase cell to open its drop-down. It lists **(none)** and every phase
in the project; pick one to put it in that slot, or **(none)** to empty the
cell. The calculated pattern redraws immediately, and — as with every edit —
nothing is written to disk until you save.

### Only valid phases can be assigned

A phase is offered **greyed-out and unselectable** when it is not yet ready to
contribute a pattern. Hovering it explains why. A phase is *not ready* when:

- it has an **empty component slot** — a component with no atoms. A phase you
  just created with **Add** starts this way (blank *Component 1*, *Component 2*,
  …), so it produces a blank pattern and cannot be assigned until you fill its
  components with atoms (define them on the Components tab, or **import** them
  from a `.cmp` file); or
- it is a **raw-pattern phase** that does not yet hold a measured pattern.

This is the answer to a common question:

> **I created a New Phase but forgot to give its components any atoms — can I
> add it to a mixture?** No. An incomplete phase would contribute a blank
> pattern, so MudLab2 shows it greyed in the slot drop-down and will not let you
> assign it. Fill in (or import) its components' atoms and it becomes
> selectable — no separate "validate" step is needed.

### Deleting a phase or specimen that a mixture uses

You cannot. **Edit Phases** refuses to remove a phase any mixture still holds,
and the specimen list refuses to remove a specimen any mixture still holds. In
both cases MudLab2 names the mixture and how many cells (or rows) hold it.

Free it first, in **Edit Mixtures**:

- **a phase** — set its cells to **(none)** in the cell drop-down, or
  right-click the slot header and choose **Remove phase slot**;
- **a specimen** — right-click the row header and assign **(none)**, or choose
  **Remove specimen** there to drop the row. (That menu item removes the row
  from *this mixture*; it does not delete the specimen from the project.)

Emptying a cell is safe on its own: the slot stays, the fraction is kept, the
mixture keeps calculating (an empty slot contributes nothing), and you can drop
a different phase in whenever you like. Once no mixture holds the object any
more, Remove works normally.

> **I have several mixtures — do I have to free the phase from all of them?**
> Yes. The check asks whether *any* mixture still holds it, not just the one you
> were last looking at, and the message lists every mixture involved.

> **I selected several specimens and one of them is in a mixture — will the
> others be removed?** No. The whole selection is refused, so you are never left
> guessing which ones went. Free the one that is in use, then remove them
> together.

### Reusing a phase, and what refinement shares

A phase is a single object in your project. Where it matters is **who shares its
refined structure** — its sigma\*, CSDS mean, stacking parameters and per-layer
cell values. Weight **fractions, scale and background** are always separate for
each mixture; only the *structure* can be shared.

> **I loaded the same default phase twice and put both in one mixture — do they
> clash?** No. Each **Add default phase** creates a brand-new, independent phase
> (its own identity throughout), so the two are refined separately with their own
> structure. They do *not* share anything. One catch: two structurally identical
> phases in the same mixture have interchangeable fractions — the fit can only
> pin down their **sum**, not the split — so this is rarely what you want. Add a
> phase twice only when you intend the two copies to be refined into *different*
> structures.

> **I put one phase into two different mixtures — which mixture "owns" the
> refinement?** Neither: the two mixtures share that one phase's **structure**, so
> refining either mixture changes the structure **everywhere the phase is used**,
> and the last mixture you refine wins. Each mixture still keeps its own
> fractions, scale and background. This is deliberate — the same clay has the same
> structure in every sample — but be aware that refining one mixture will shift
> the other's calculated pattern (press **Refresh**/F5 to bring it up to date). If
> you want the two to refine into *independent* structures, add the phase twice
> instead (see above).

### Adding and removing slots and specimens

The grid is not fixed — you can grow or shrink it with the buttons below it:

- **Add phase** — appends a new phase slot (a row), named *New Phase* with a
  fraction of 1, its cells empty. Rename it and fill its cells (see below).
- **Add specimen** — appends a new specimen column, unassigned, with a scale of
  1 and no background shift. Assign a specimen to it (see below).
- **Add both** — adds one of each in a single step.

**Renaming, removing, and assigning** are on the grid's **headers**, so the
cells themselves stay a clean table of values:

- **Right-click a phase-slot row header** (the name down the left) for **Rename
  phase slot…** and **Remove phase slot**.
- **Right-click a specimen column header** (the name across the top) for
  **Assign specimen** (pick which measured specimen fills that column, or
  *(none)*) and **Remove specimen**.

Removing a slot or specimen takes its whole row/column with it — its fractions,
scales, background shift and cell assignments — and the rest shift up to close
the gap. As always, nothing touches disk until you **Save**.

> **How do I add a raw-pattern phase (quartz, an internal standard, …) to a
> mixture?** Press **Add phase** to make a new slot, then click its cells and
> pick the raw phase from the drop-down — exactly like assigning any phase. (A
> raw phase is only selectable once it holds a measured pattern.)

### Composition summary

Press **Composition** to see the mixture's **oxide composition** — one column
per specimen, one row per oxide (SiO₂, Al₂O₃, Fe₂O₃, CaO, MgO, Na₂O, K₂O), in
weight percent normalised to 100. It is computed from each phase's atoms
(weighted by their occupancies and the phase fractions), so it reflects the
model you have built; raw-pattern phases, which have no atoms, do not contribute.

The panel is read-only. Use **Copy** to put the table on the clipboard as CSV,
or **Export CSV…** to save it to a file.

---

## Measured (XRF) composition

**Composition → Edit composition…** records the sample's measured oxide
analysis — typically from XRF — so it can be compared against the composition
MudLab computes from your model. Until you have entered one the menu entry reads
**Enter composition…**.

A MudLab project describes **one physical sample**; its specimens are treatment
variants of that same material (air-dried, glycolated, heated). So a project
holds **at most one** analysis. Choosing the menu item again re-opens the dialog
on the values you already entered, so correcting one figure does not mean
retyping the whole analysis.

To delete the analysis, use **Composition → Remove composition**. It asks for
confirmation, and is greyed out when there is nothing to remove. Clearing the
grid in the editor is *not* a way to delete it — removal is a separate,
deliberate action, so an analysis you typed in can never be lost by accident.

### Entering the analysis

Values are **weight percent**. The grid offers a fixed set of oxides — the same
seven the modelled composition reports — and that restriction is the point: an
oxide the model can never produce could not take part in the comparison. Leave
anything you did not measure at zero; only non-zero values are stored.

- **Total** is shown as you type. If it sits far from 100 % you get a note, not
  an error — a majors-only analysis is perfectly reasonable.
- **Recompute to 100 %** scales every value so they sum to 100. Worth doing
  before comparing: the modelled composition is *always* normalised to 100, so
  an analysis totalling 97 would otherwise read as a difference that is not
  really there. (Values are held to two decimals, so the total may land on
  100.01 — that is rounding, not an error.)
- **Name** and **Source** are free text. Source is a note to yourself about the
  laboratory, method or date; MudLab never interprets it.

The analysis is stored in the project and survives save and reload. It has no
effect on any calculation — it is reference data for comparison.

### Comparing it with the model

Open a mixture's **Composition** view (Edit Mixtures → **Composition**). Two
optional columns sit beside the modelled ones:

- **Show measured (XRF) composition** — adds your analysis as one extra column,
  normalised to 100 % so it is directly comparable.
- **Show default-phase state** — adds, for each specimen, the composition the
  mixture *would* have if every phase were still in its shipped default state,
  weighted by the fractions the fit found. The difference between that and the
  modelled column is **what refinement did to the chemistry**.

Both are off by default, and each is greyed until the data behind it exists.

### The comparison plot

The right-hand pane plots exactly what the table shows: the oxides along the
bottom, and one line per column joining its values. It is the fastest way to
spot the disagreements a grid of numbers hides — a measured oxide the model has
none of, or a phase whose chemistry has moved a long way from its baseline.

- The **measured** analysis is the one strongly coloured series, since it is
  usually what you are checking against.
- A **default-state** column is drawn hollow in its specimen's own colour, so a
  specimen and its baseline read as before-and-after rather than as two
  unrelated series.

Past about ten columns the lines stop being legible, so the plot says so rather
than drawing something unreadable — the table still lists everything.

**Saving the plot.** Right-click the chart for **Save plot as…** and **Copy
plot image**. Save offers **SVG** and **PDF** (vector — they stay sharp at any
size, and are what a journal usually wants) as well as **PNG**, **TIFF** and
**JPEG**. A size and resolution box opens first, exactly as it does for
**Save Graph** on the main plot. The Copy entry puts the chart on the clipboard
so it can be pasted straight into a document.

### Which phase started as which default?

The default-state column needs to know which built-in default phase each of your
phases began as — and MudLab **cannot** work that out. Adding a default phase
gives it a brand-new identity, nothing records where it came from, and phases
are usually renamed afterwards (the catalog's *Illite-Smectite R0 Ca-AD* becomes
your *IS R0 Ca-AD*).

So you state it once, with **Default phases…** in the Composition view:

- one row per phase, with a drop-down of every built-in default phase;
- **Match by name** fills in the phases whose names still match exactly — only
  exact matches, because a wrong guess would corrupt the comparison invisibly;
- set the renamed ones yourself.

The mapping is remembered with the project. A phase you leave unstated is simply
shown at its current state, and the view says which ones those are — a partial
mapping gives a partial answer rather than a wrong one.

### Usually there is nothing to state

A phase records what it started as **when it enters the model**, so in normal use
the mapping fills itself in:

- **Add phase → Default phase** — the phase *is* the catalog's phase at that
  moment, so its default is recorded straight away. Renaming it afterwards
  changes nothing; the record follows the phase, not its name.
- **Edit Phases → Import** (a `.phs`) — a pristine copy of what you imported is
  kept as the reference at the same moment.

Either way the default is captured **before** anything can refine the phase,
which is the only moment it is provably unrefined. You only need the dialog for
phases that predate this — projects built earlier, or phases built from scratch,
which have no reference to capture.

> **Why a separate copy for an imported phase?** Refinement rewrites phases in
> place. If the reference were the same object, refining your model would refine
> the yardstick with it, and the comparison would always read "no change". The
> captured copy shares no components and no atoms with the working phase, so it
> cannot move.

### Setting a baseline yourself

Two cases capture cannot cover: a phase you built **from scratch** (it never had
a reference state), and one you built by heavily editing a catalog default — its
baseline is then the *stock* phase, so the comparison mixes your own modelling
with what refinement did.

For both, use **Set as baseline**, in the phase editor and on the phase list's
right-click menu. It records the phase exactly as it is at that moment.

Because it can only ever mean "start from here", it always asks first, and says
so plainly: everything already done to the phase becomes part of the baseline,
and the comparison will only show what changes afterwards. Setting one where a
baseline already exists replaces it, and the old one cannot be recovered.

The natural moment is **just after you finish building a phase and before you
refine it**.

> **Inherited phases are handled correctly.** A treated phase that is *based on*
> another, or whose components are *linked* to a template, is captured with its
> resolved values baked in and its links cut. So refining the parent later moves
> the phase but never its baseline. (A plain copy would get this badly wrong —
> on a test case it reported Fe₂O₃ 39.9 where the phase actually resolves to
> 167.7, because a copy without its parent falls back to its own stale values.)

### Your own reference phases

The built-in list only contains the clays MudLab ships. For a phase that was
already in your project before this — a custom mixed-layer clay, say — export it
from **Edit Phases → Export** as a `.phs` and bring it in with **Import .phs…**
in the Default phases dialog. It joins the drop-downs immediately, listed first
and marked as yours, and any phase whose name matches it is filled in for you.

> Export the phase in the state you want as the **baseline**. If it has already
> been refined, that refined state is what you are exporting — and comparing
> against it will understate what refinement changed.

Two things worth knowing:

- An imported reference is **not** a phase of your model. It never appears in
  Edit Phases or in a mixture cell — it exists only to be compared against.
- It is **saved inside the project**, so the comparison keeps working later even
  if the original `.phs` has been moved or deleted, or the project is opened on
  another machine.

Importing a reference whose name matches a built-in one replaces it *for this
project* — yours is the more specific answer — and the dialog tells you when
that happens. Re-importing a corrected `.phs` under the same name updates the
reference in place, so any mapping pointing at it keeps working.

> **What actually changes the chemistry?** Refinement, not Optimize. Optimize
> only fits fractions, scale and background, which live on the mixture — your
> phases are untouched. Refinement changes them two ways: **atom relations**
> rewrite the atoms' occupancies (a substitution like Fe-for-Al can move an
> oxide by many percent), and **stacking probabilities** change the proportions
> of the layer types in a mixed-layer phase. σ\*, CSDS, d001 and δc have no
> effect on composition at all.

> **Does this change my file?** Only if you import one. A project without a
> composition is written exactly as before. A project **with** one cannot be
> opened by the old GTK MudLab, which rejects any file property it does not
> recognise — the same limitation that applies to non-clay phases.

## Exporting to other programs

**Project → Export** writes a copy of your project in another program's format.
It is a *copy*: your own project file is untouched, it keeps its own name, and
exporting is not a substitute for saving.

Two targets:

- **MudLab (old app) project…** — a `.mud` the original GTK MudLab can open.
- **PyXRD project…** — a `.pyxrd` file.

### Why an export is needed at all

MudLab2's own `.mud` is the old format plus a few things MudLab2 added, such as
the measured composition. The old app rejects a file containing anything it does
not recognise — it will not open it at all — so a project with an XRF analysis
in it cannot be handed straight over. Exporting removes those additions on the
way out, which is precisely what lets MudLab2 keep them natively.

### What does not survive

Every export ends with a summary of what changed. Read it — the export is
deliberately lossy, and the summary is how you find out where.

Common ones:

- The **measured composition**, the record of **which default each phase started
  as**, and any **imported reference phases** are dropped. Neither target knows
  them.
- A **non-clay phase** is written as a plain measured-pattern phase. Its pattern
  and its place in the mixture are kept; its oxide chemistry is not.
- For PyXRD only: the **emission spectrum** is reduced to a single wavelength
  (PyXRD has no wavelength distribution), the **absorption correction** is not
  carried over (PyXRD stores a different quantity), and MudLab's inner-iteration
  refinement limits are removed from the saved refinement options.

> **How reliable are these?** The old-app export is checked by actually opening
> the exported file in the old MudLab. The **PyXRD export has never been opened
> in PyXRD** — it is built to match real PyXRD files field by field, but treat
> it as best-effort and check the result before relying on it.

## Refining a mixture

**Refine** (in the mixture editor) opens the refinement window, which fits the
*structural* parameters of the mixture's phases — sigma\*, the CSDS mean, the
stacking parameters, each component's d001 and δc, and any refinable atom
relation. It is not the same as **Optimize**, which only fits fractions, scale
and background; every refinement trial runs an Optimize of its own inside.

The window is **modal** — nothing else can be edited while it is open — and has
three panels: the parameters to refine, the run itself, and the results.

### Choosing parameters

The parameter list is a **tree**: one branch per phase, a nested branch per
component, and one row per parameter. It opens folded, because the phase names
are the useful overview. **Right-click** anywhere in it for:

- **Expand all** / **Fold all**
- **Select all** / **Unselect all** — these also expand, so you can see what
  changed
- **Auto restrict** — set every ticked parameter's Min/Max to ±20 % of its
  current value
- **Randomise** — move every ticked parameter to a random point inside its
  Min/Max, and recompute

Tick **Refine** on the parameters you want fitted. The count beside the heading
("*7 of 42 selected*") is the thing that decides how long a run takes: every
ticked parameter adds a dimension to the search.

**Value, Min and Max are all editable** — double-click a cell. Min and Max are
the search bounds. Typing a **Value** sets that parameter in the model straight
away and recalculates the pattern, which is how you try a value by hand or set a
starting point before refining. Two things to know about it: phases are shared
between mixtures, so it can move another mixture's pattern too, and there is
**no undo** — refine, or keep a solution, to overwrite it.

Only parameters that can genuinely be refined are listed. An **inherited**
parameter is not offered at all: it follows its parent, so refining it on the
child would do nothing — refine it on the phase or component it is based on, and
every phase that inherits it moves with it.

### The warning line

Below the tree, a line appears when something about the set-up will not do what
it looks like. It disappears by itself once you fix it, and the cells it refers
to are tinted in the tree:

- **Min not below Max** — the refiner *silently drops* such a parameter. It stays
  ticked, but it never moves. This is the only place you would notice.
- **Outside Min/Max** — the value sits outside its own bounds, so the run starts
  from the nearest bound, not from the number shown.
- **Set by hand** — a reminder that you typed a Value straight into the model.

### Running

Pick a **method** — *L-BFGS-B* (local, fast, refines from where you are) or
*Basin Hopping* (global, many random restarts, much slower). The spinners below
are that method's own limits, and the line under them says what the run may do.
It deliberately does **not** promise a total number of evaluations: the limits
count the solver's own steps, not model evaluations, and one step costs roughly
one evaluation per refined parameter plus a line search.

> **Basin Hopping's "Calls per run"** caps each local minimisation. Without a
> cap, 100 iterations can mean over a million evaluations and hours of runtime.
> Raise it if a minimum genuinely needs more work.

The window stays responsive while it runs. **Cancel** stops at the next trial and
keeps the best result so far — it is not a pause: pressing Refine again starts a
*new* run from there.

### The progress plot

The plot tracks the best Rp against the number of evaluations. The bold blue
line is the **mean** — the number quoted everywhere else — and the thin coloured
lines are the **individual specimens** behind it.

Watch the spread. A run can improve the mean by fitting one specimen better
while fitting another *worse*, and a single curve cannot show that.

### Results

When the run ends the model is left at the **best** solution, and the report
below describes it: the method and elapsed time, every refined parameter's
initial/best/last values, the residuals and GoF, the **Rp for each specimen**,
a progress log, and a post-refinement validation of the model it left behind.

The three buttons — **Initial**, **Best**, **Last** — put that solution into the
model and rewrite the report for it. A few points worth knowing:

- The model is written when the run ends and at **each button press** — never on
  closing. Closing the window (X or **Close**) neither commits nor rolls back.
- **Initial is not a full undo.** It restores the structural values and
  fractions, but scale and background are re-fitted, so they do not come back
  exactly. If you may want the original state, save before refining.

---

## Importing measured patterns (CSV options)

Patterns come in from several places — a specimen's experimental pattern, a
raw-pattern phase, and a background pattern — and they all go through the same
importer. It reads the vendor formats (Bruker/Rigaku `.raw`, Rigaku `.rasx`,
PANalytical `.xrdml`, Bruker `.uxd`) directly, and any plain-text format
(`.xy`, `.txt`, `.csv`, `.dat`, `.tab`) as two columns of numbers.

For a text file, a **CSV import options** dialog appears so you can confirm how
it is read:

- **Separator** — *Auto-detect* (the default), or force Comma / Semicolon /
  Tab / Space. Auto-detect handles most files, including whitespace-aligned
  columns.
- **Decimal sign** — *Period* or *Comma*. This is what makes European exports
  (`;`-separated with `,` decimals, e.g. `10,5;100,0`) import correctly.
- **First row contains headers** — skip a leading label row.

The **preview** underneath shows how the first rows parse with the current
settings (a header row is shown in italics), so you can tell at a glance whether
the columns line up before clicking **OK**. The settings are pre-filled from a
best guess at the file, so usually you can just confirm.

### What import records about the file

After importing, the specimen's **Source** box (Edit Specimen → *General* tab)
describes where the pattern came from: the **file name** and its **2θ range,
step and point count** (for any format).

The scan also seeds the specimen's goniometer: its **minimal 2θ**, **maximal
2θ** and **2θ steps** are set from the pattern that was just read, so an
untouched goniometer describes the measurement you actually imported rather
than the 3–45° / 2500-step default. When the file records instrument details,
those are listed in the Source box too, and the file's Kα₁ **wavelength is
applied to the goniometer** automatically:

- **PANalytical `.xrdml`** — wavelength, count time, sample name, scan date,
  goniometer radius.
- **Rigaku `.rasx`** — wavelength, X-ray tube (target, kV, mA), scan date and
  speed.
- **Bruker `.uxd`** — wavelength, X-ray tube (anode, kV, mA), count time, scan
  date, goniometer radius.
- **Bruker `.raw`** — count time (and, for the older RAW1 files, the wavelength).

Rigaku `.raw` and plain-text files record no instrument details, so beyond the
2θ range and step count they leave the goniometer at its defaults — including
the wavelength, which stays at Cu Kα₁ (0.154056 nm). If you measured on a
different tube, set it yourself on the Goniometer tab.

Everything the import seeds is a **starting point**. Applying a stored setup
from the **Load setup** drop-down (see [Stored setups](#stored-setups-load--store))
replaces *every* goniometer value, the 2θ range and step count included — so
an instrument setup you apply afterwards always wins.

---

## Preparing experimental data

Before fitting phases to a measured pattern you often need to clean it up:
remove the background, smooth counting noise, correct a specimen-height shift,
strip a contaminant peak, or cut the pattern down to the range you care about.

All of these live on the **Actions toolbar**, and Remove Background, Smooth Data
and Shift Pattern are also on the **View** menu.

Every one of them acts on the **selected specimen**. Select exactly one specimen
with experimental data in the specimens list first — otherwise the buttons stay
greyed out.

> **These operations are permanent and cannot be undone.** They rewrite the
> specimen's experimental pattern in place. Nothing is written to disk until you
> save the project, so if an operation goes wrong, close the project **without
> saving** and reopen it. If you are unsure, save a copy first.

While a Remove Background, Smooth, Shift, Strip Peak, or Add Noise dialog is
open, the main plot shows a **live preview** of the result (an orange curve)
drawn over your original pattern, so you can see exactly what each setting does
before committing. Nothing is changed until you click **OK / Apply**; **Cancel**
(or closing the dialog) removes the preview and leaves the pattern untouched.
In the Smooth dialog, **Show original** keeps the un-smoothed pattern visible
under the preview — turn it off to judge the smoothed curve on its own.

### Remove Background

Subtracts a background so only the diffracted signal remains.

- **Linear** — subtracts one flat value across the whole pattern. The field is
  pre-filled with the lowest intensity in the pattern, which is usually a good
  starting guess.
- **Pattern** — subtracts a measured background pattern (a blank scan). Browse
  to the file; it is automatically re-sampled onto your specimen's 2θ values, so
  it does not need to have been measured on the same step size. Beyond the
  background file's own range it contributes nothing.
  - **Scale factor** multiplies the background pattern before subtracting
    (use it when the blank was measured for a different counting time).
  - **Offset value** adds a constant on top of the scaled pattern.

### Smooth Data

Reduces point-to-point scatter. Choose a **Type**, and the **Degree** field
fills with a sensible default for that method — a higher degree smooths harder.

| Type | What it does |
| --- | --- |
| Moving Triangle | Blackman-window average — a good general-purpose default |
| Savitzky-Golay | Fits a local polynomial; preserves peak height and width better than a plain average |
| Gaussian | Gaussian blur; degree is the width (sigma) |
| Moving Average | Plain box average; simplest and most aggressive on sharp peaks |
| Smoothing Spline | Fits a spline; degree sets how loosely it follows the data |
| Butterworth | Low-pass filter; removes high-frequency noise |

Smooth cautiously: over-smoothing broadens peaks and will bias a refinement's
crystallite-size (CSDS) result.

### Shift Pattern

Corrects a 2θ offset, usually caused by the specimen surface sitting slightly
above or below the correct height.

1. Pick the **Position** — a reference mineral present in your sample whose peak
   position is known exactly (quartz is the usual internal standard).
2. MudLab2 finds that mineral's peak in your data and shows the offset, in °2θ,
   between where it should be and where it actually is. A **dotted vertical line**
   appears on the plot at the reference's *target* position, so you can see where
   the peak should line up; the live preview shows the shifted pattern moving
   toward it as you adjust the value. The line stays fixed at the target (it does
   not move with the value), and disappears in Manual mode and when you close.
3. Press OK to correct the pattern by that amount.

Choose **Manual** to type an offset yourself; the value resets to zero so a
previously detected offset is never reused by accident.

> **Shift before you set exclusion ranges or markers.** Shifting moves the
> pattern, but exclusion ranges stay where you put them — they are fixed 2θ
> positions, not features of the data. A range you set to mask a peak will no
> longer sit over that peak after a shift, and the refinement will exclude the
> wrong region without warning. Markers do not move either. If you have already
> shifted, check both before fitting.

**A value of 0.000 means no correction is needed** — either the reference peak
already sits exactly where it should (your pattern is already aligned), or that
reference lies outside your scanned range and could not be measured. Check that
the reference you picked is actually within your scan.

### Strip Peak

Removes a contaminant peak (e.g. a quartz reflection overlapping a clay peak) by
replacing it with the background beneath it.

1. Set **Start position** and **End position** to bracket the peak — use the
   **Sample** buttons to click the positions directly on the pattern.
2. MudLab2 joins the two endpoints with a straight line and estimates a
   **Noise level** so the patched section blends in rather than looking
   artificially flat. You can override this value.
3. Press OK. Only the data between the two positions changes.

### Peak Properties

Measures a peak's **area** and **FWHM** (full width at half maximum). This is
the only Data operation that changes nothing — it just measures.

Bracket the peak with the start/end positions (or the **Sample** buttons); the
results update as you move them. The straight line between your two endpoints is
treated as the local background, so place them on clean background either side
of the peak. **Copy Results** puts both numbers on the clipboard.

### Add Noise

Adds synthetic noise to the pattern. This is a testing tool — use it to check
how robust a refinement is against counting statistics, not on data you intend
to keep. The **Fraction** is relative to the strongest peak, so 0.05 adds noise
of about 5% of the tallest reflection.

### Trim Data

Permanently cuts the pattern down to a 2θ range — for trimming a noisy tail, or
making several specimens share one range.

- **Scope** — *This specimen only*, or *All loaded specimens*. Choosing "all"
  pre-fills the range that **every** specimen shares, since a wider range would
  fail on the ones that do not reach it.
- **Min/Max °2θ** — the range to keep.

Trimming also removes anything that falls outside the new range: markers, and
exclusion ranges. The dialog tells you what will go before you commit. An
exclusion range that only *partly* overlaps the new boundary is removed rather
than cut short, since a shortened exclusion range would no longer mean what you
set it to mean.

A trim that would leave fewer than two data points is refused, and MudLab2 names
the specimens it could not trim.

### Convert between fixed and automatic (ADS) slit

**Data → Convert to Fixed Slit** and **Data → Convert to ADS** rescale
the selected specimen's measured intensities between the two divergence-slit
geometries. A fixed divergence slit keeps the beam's angular width constant; an
**automatic** (or *variable*) divergence slit — ADS — opens as the angle
increases so the irradiated length on the sample stays constant, collecting more
intensity at higher angles. The two therefore differ by a factor of **sin θ**:

- **Convert to ADS** multiplies the intensities by sin θ (fixed → ADS).
- **Convert to Fixed Slit** divides them by sin θ (ADS → fixed).

Use this to bring a pattern into the same geometry as a reference, a background
scan, or the rest of your specimens before comparing or fitting them. Each
command acts on the single selected specimen (the menu items are greyed until
exactly one specimen with data is selected), asks for confirmation, then rewrites
the pattern in place — like the other data operations, this is **permanent and
not undoable** until you reopen without saving. The two directions are inverses,
so converting the wrong way can be undone by converting back.

> **Note:** the conversion changes only the measured data, not the specimen's
> goniometer. MudLab2's confirmation reminds you of this: after converting, set
> the **Divergence mode** on the specimen's Goniometer tab to match (**Automatic**
> for ADS, **Fixed** for fixed slit) and press **F5 (Refresh Graph)** to
> recompute, so the calculated pattern is corrected the same way. (Changing a
> goniometer setting does not recompute on its own — F5 applies it.)

---

## Peaks, peak detection, and mineral matching

The **Peaks** window (toolbar, or right-click a specimen) lists the peaks marked
on a pattern, with their positions, and lets you add, label and remove them.

### It gets out of your way

Two things need the plot rather than the window, and for both the Peaks window
**hides itself and comes back on its own**:

- pressing **Sample** to pick a position — click the pattern and the window
  returns with the position filled in. Changed your mind? Press **Esc**: the
  pick is cancelled and the window comes back either way.
- opening **Match minerals**, which draws its reference peaks on the pattern.
  The Peaks window returns when you close it.

### The list stays in order

Peaks are listed by position. Detected peaks arrive in order already; a peak you
add by hand starts at the bottom of the list at position 0, because it does not
have a position yet. As soon as you **finish setting** its position — by typing
it and pressing Enter or leaving the field, or by using **Sample** — it moves to
its proper place in the list, and stays selected so you do not lose it.

It deliberately does *not* re-sort on every keystroke: typing "25" would
otherwise jump the row once at "2" and again at "25", moving the field out from
under you mid-edit.

Each peak marks a reflection by its 2θ position, labelled with the d-spacing it
corresponds to. Add, remove and edit them by hand in the Peaks window, or use
the two tools at the bottom of the list — **Find peaks** and **Match minerals**
— to build and label a set automatically.

> **"Peak" here, "marker" in the file.** These are the same thing: the project
> file and the original MudLab both call them markers, and that has been left
> alone so files stay readable by both apps. Only the wording you see changed.

### Detect Peaks

**Find peaks** opens the Auto detect peaks dialog, which finds reflections for
you and drops a marker on each.

- **Pattern** — detect on the *Experimental* or *Calculated* curve. A curve with
  no data is greyed out.
- **Algorithm** — *Threshold (classic)* is the original height-based detector;
  *Prominence (scipy)* judges each peak by how far it rises above its
  surroundings and adds a **Min. distance (°2θ)** field so close peaks are not
  double-counted.
- **The graph** plots how many peaks are found as the cut-off changes. Drag the
  blue line (or type into **Selected threshold** / **# of peaks**) to pick the
  cut-off — the two fields stay in step, so you can aim for a peak *count* or a
  threshold *value*, whichever is easier. **Maximum** and **Steps** control the
  range and resolution of the curve.

Click **OK** to add a marker at every detected peak; each is labelled with its
d-spacing. If the specimen already has markers, MudLab2 first asks whether to
clear them (replace) or keep them (append).

### Match Minerals

With a marker selected, **Match minerals** scores a built-in reference set (228
minerals) against your markers' peak positions and tells you which minerals fit.

- The **right** list is every reference mineral; the **left** list is the
  matches, best first, with a score (higher = better fit).
- **Auto match** re-scores against the current target markers. You can also pick
  a mineral on the right and use the transfer buttons to add it to (or remove it
  from) the matches by hand.
- **Append labels** adds the selected matches' abbreviations to your markers'
  labels (for example a quartz marker becomes `… , Qz`), so the identification
  shows on the plot. Applying the same mineral twice does not duplicate it.
- **Selecting a mineral** in either list draws its reflections on the main plot
  as **magenta sticks** (positioned by 2θ, with height proportional to each
  reflection's relative intensity), so you can see at a glance whether they line
  up with your pattern. Tick **Specimen range** to show only the reflections
  that fall inside the scanned 2θ range.

The dialog stays open alongside the plot so you can keep working; closing it
removes the reference-peak overlay.

---

## The goniometer emission spectrum

Each specimen carries a goniometer setup (**Edit Specimen → Goniometer** tab). A
newly imported or added specimen starts with a **default** setup (Cu Kα,
Bragg–Brentano) — check it matches your instrument, edit any values that differ,
or apply a **stored setup** (see below). Imported patterns keep their own 2θ
range regardless, so the default range does not affect the fit.
The X-ray source is described by its **emission spectrum** — the set of
wavelengths it emits and their relative strengths. Most of the calculation uses
the **dominant** wavelength (the strongest line), shown next to the
**Wavelength (λ)** label.

Click **Edit emission spectrum** to open the editor:

- The table lists each **Wavelength (nm)** and its **Fraction** (relative
  intensity). Click a cell to edit it; non-numeric entries are rejected and the
  cell reverts.
- **Add** / **Remove** insert or delete rows.
- **Import…** replaces the whole spectrum from a `.wld` file — five presets
  (Cu, Co, Cr, Mo, and a Cu LynxEye XE profile) ship with MudLab2 and the dialog
  opens in that folder. **Export…** saves the current spectrum to a `.wld` file
  to reuse elsewhere.

Edits apply immediately to the specimen's goniometer (there is no separate
"OK" — just close when done), and the dominant wavelength updates on the
Goniometer tab. A single line with fraction 1.0 (the default) is the ordinary
monochromatic case; add the Kα₂ line, for example, to model a Kα₁/Kα₂ doublet.

### Stored setups (Load / Store)

Rather than typing every value, you can apply a whole instrument configuration
at once. The **Load setup** drop-down lists a set of bundled presets for common
diffractometers (Bruker D8, PANalytical X'Pert/Empyrean, Philips, and others),
followed by any you have saved yourself. Pick one and confirm — it replaces
*all* the goniometer values (geometry, slits, 2θ range, steps, and the emission
spectrum), and the applied name is shown at the bottom of the tab.

**Store setup** saves the current goniometer to a `.gon` file so you can reuse
it on other specimens or projects; your saved setups then appear in the
drop-down (marked *custom*). The `.gon` format is the same JSON the project file
uses for a goniometer, so setups exported from the old MudLab load here too.

### Which goniometer the calculation uses

The goniometer belongs to the **specimen**, so every specimen has its own. A
specimen's calculated pattern — and the pattern of **each phase assigned to that
specimen** — is always computed with **that specimen's own goniometer**: its
wavelength, emission spectrum, slits, 2θ range and geometry correction. No other
specimen's goniometer ever enters that specimen's calculation.

This matters when a mixture spans several specimens (for example the air-dried,
glycolated and heated preparations of one sample). Refining the mixture does
**not** pick a single goniometer for the group: each specimen's pattern is
computed with its own goniometer, and the fit is optimised against all of them
together. The mixture's shared quantities — the phase **structures** and the
phase **fractions** — are therefore fitted simultaneously through each
specimen's own instrument setup, while **scale** and **background** stay
per specimen. A practical consequence: the *same* phase produces a *different*
calculated curve in each specimen precisely because each specimen's goniometer
differs, so if two preparations were measured with different wavelengths or
optics, MudLab2 accounts for that correctly rather than forcing one setup across
the group.

---

## Viewing the plot

Each selected specimen is drawn on the shared graph with its experimental and
calculated patterns stacked. A few view options live in the **View** menu.

### Show phase patterns

By default the graph draws only the specimen *total* calculated pattern. Turn on
**View → Show phase patterns** to also overlay each phase's individual
contribution, drawn in that phase's own colour (set per phase in Edit Phases).
This shows how much each phase adds to the fit and where phases overlap.

The overlay follows the calculated pattern: if a specimen's calculated curve is
hidden, its phase curves are hidden too. The toggle is a convenience that flips
the setting on every specimen currently shown; you can also set it per specimen
from the specimen's display options (the **Sep** column in the specimens list,
or *Display phases separately* in the Edit Specimen dialog). The menu tick
mirrors whatever the shown specimens are set to.

If you switch it on right after opening a project and nothing appears yet, the
phase curves are recomputed the moment you toggle them (they are derived from the
current fit and are not stored in the file); a **Refresh** (F5) also recomputes
them. A project saved with the option on shows the curves as soon as it loads.

### The axes

There is **no background grid** — the patterns are easier to read against a
clean surface.

The 2θ axis carries a **tick every degree**. The short marks are the individual
degrees; the longer, numbered ones are spaced as widely as they need to be for
the numbers to stay legible at the current window width — every 5° on a full
4–70° scan, for instance. **Zoom in and the numbers close up**, until on a span
of a few degrees every degree is labelled; zoom back out and they spread again.
Widening the window has the same effect, since more labels then fit.

### The index (top right)

The top-right corner of the plot carries an **index**, in two parts.

First, **every specimen on show**, listed in the order they appear on the
graph — top of the list is the top curve. Each gives the specimen's name, and,
for any specimen set to show them, its **Rp**, **Rwp** and **GoF**. (Turn those
on per specimen with *Display statistics in label* in the Edit Specimen dialog.)
This information used to sit in the left margin; moving it here frees that
space, so the plot itself is now noticeably wider.

Then a **phase index** for every mixture that owns a specimen currently on show.
Each entry lists the mixture's name, then one line per phase slot giving its
**label and fraction** (as a percentage), next to a small **colour swatch** for
each specimen — in the same colour that phase's curve uses when *Show phase
patterns* is on. So you can read off, at a glance, which phase is which colour
and what proportion it makes up.

Because a slot can hold a different phase in each specimen (the air-dried,
glycolated and heated forms of one clay), a row shows one swatch per specimen —
usually the same colour across the row, but a different colour wherever a slot
holds a differently-coloured phase.

The index sits on a light panel so it stays readable where it overlaps a
pattern. It appears automatically, and shows only the parts that apply: a
specimen belonging to no mixture still gets its name listed, just without a
mixture block.

> **The label position setting does nothing now.** *Edit Project → Patterns →
> Label position* is greyed out: it positioned the specimen name in the left
> margin, and the index is anchored to the corner instead.

### Saving the graph as an image

**Data → Save graph** exports the current plot to an image file. A small dialog
appears first to choose the output **size** and **resolution**: pick one of the
print presets (landscape/portrait, large/medium/small), or set the **width**,
**height** (in pixels) and **DPI** by hand. Click **OK**, then choose where to
save and in which format — **PNG**, **PDF**, or **SVG** (PDF and SVG are vector
formats, so their DPI is not used). The file name defaults to the shown
specimen's name (or the project's).

The export uses the size you chose, not the size of the window, so you get the
same picture regardless of how the window is arranged; the on-screen plot is left
untouched.
