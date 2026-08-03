# MudLab2 user manual

Guide to using the MudLab2 GUI. This manual grows as features are added.

## Contents

- [Opening projects (including PyXRD files)](#opening-projects-including-pyxrd-files)
- [Adding and removing phases](#adding-and-removing-phases)
- [Phase inheritance ("based on")](#phase-inheritance-based-on)
- [Component linking and inheritance](#component-linking-and-inheritance)
- [Atom relations (substitutions and contents)](#atom-relations-substitutions-and-contents)
- [Mixtures: assigning phases to slots](#mixtures-assigning-phases-to-slots)
- [Importing measured patterns (CSV options)](#importing-measured-patterns-csv-options)
- [Preparing experimental data](#preparing-experimental-data)
- [Markers, peak detection, and mineral matching](#markers-peak-detection-and-mineral-matching)
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

Removing a phase also cleans up everything that pointed at it, so nothing is
left dangling:

- any phase that was **based on** the removed one stops inheriting and keeps the
  values it currently shows (it falls back to its own stored numbers);
- any component **linked** to one of the removed phase's components is unlinked;
- the phase is cleared from every **mixture** — its slot stays, but the cell
  that named it becomes empty, so you can assign a different phase there.

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

### Deleting a phase that a mixture uses

Removing a phase in **Edit Phases** does **not** break your mixtures. Every cell
that named the deleted phase simply **empties** — the slot itself stays, the
fraction is kept, and the cell shows **(none)**. The mixture keeps calculating
(the emptied slot contributes nothing), and you can drop a different phase into
that cell whenever you like.

> **I added a phase to a mixture, then deleted it in Edit Phases — is the
> mixture now invalid?** No. The mixture stays usable; only the cells that
> referenced the deleted phase go blank, ready for a replacement. Nothing is
> left dangling and no error is raised.

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
   between where it should be and where it actually is.
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

---

## Markers, peak detection, and mineral matching

Markers label reflections on a pattern by 2θ position (and the d-spacing they
correspond to). Open **Edit Markers** for the current specimen to add, remove,
and edit them by hand, or use the two tools at the bottom of the list to build
and label a marker set automatically.

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

Each specimen carries a goniometer setup (**Edit Specimen → Goniometer** tab).
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
