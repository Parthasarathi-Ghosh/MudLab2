# How MudLab works

The science behind each feature: what a thing means, what MudLab assumes about
it, and how it is computed.

This is a **glossary**, not a tutorial. Read an entry when you want to know
what the program is doing on your behalf — and, just as often, what it is
taking on trust. For how to drive the program, see the
[walkthrough](getting-started.md) and the [manual](user-manual.md).

It is written in batches as the program grows. Sections marked *(to come)* are
planned but not yet written.

**Contents**

- [The material: what a clay is, to MudLab](#the-material-what-a-clay-is-to-mudlab)
  - [The layer](#the-layer)
  - [Sheets: tetrahedral and octahedral](#sheets-tetrahedral-and-octahedral)
  - [Dioctahedral and trioctahedral](#dioctahedral-and-trioctahedral)
  - [The interlayer](#the-interlayer)
  - [Layer charge, and what separates one clay from another](#layer-charge-and-what-separates-one-clay-from-another)
  - [Basal spacing](#basal-spacing)
  - [Why one dimension is enough](#why-one-dimension-is-enough)
  - [Treatment: making a clay declare itself](#treatment-making-a-clay-declare-itself)
- [From atoms to a layer](#from-atoms-to-a-layer)
  - [The coordinate everything is a function of](#the-coordinate-everything-is-a-function-of)
  - [What one atom scatters](#what-one-atom-scatters)
  - [Thermal motion](#thermal-motion)
  - [Adding the atoms up](#adding-the-atoms-up)
  - [Occupancy and substitution](#occupancy-and-substitution)
  - [The gallery stretches; the layer does not](#the-gallery-stretches-the-layer-does-not)
  - [Disorder in the spacing itself](#disorder-in-the-spacing-itself)
- *Stacking (to come)*
- *From a layer to a pattern (to come)*
- *From a pattern to an answer (to come)*
- *Identification and chemistry (to come)*

---

## The material: what a clay is, to MudLab

### The layer

A clay mineral is built from **layers** stacked one on another like pages in a
book. Each layer is a sandwich of two kinds of sheet, and the whole of clay
mineralogy follows from how those sheets are combined, what substitutes into
them, and what sits between the layers.

MudLab models a clay as exactly this: a **layer**, a **gallery** between
layers, and a rule for how layers follow one another. Nothing else about the
crystal is represented, because nothing else affects the part of the
diffraction pattern that clay analysis uses.

Three layer types account for the minerals the program ships:

| Type | Structure | Examples |
|---|---|---|
| **1:1** | one tetrahedral + one octahedral sheet | kaolinite, serpentine |
| **2:1** | octahedral sheet sandwiched between two tetrahedral sheets | illite, smectite, vermiculite, talc, the micas |
| **2:1:1** | a 2:1 layer plus a separate hydroxide sheet in the interlayer | chlorite |

MudLab tells 1:1 from 2:1 by **counting tetrahedral sheets in the layer** — one
or two. That is also why it refuses to derive glycolated states for a 1:1 clay:
having no gallery to fill, it cannot swell.

### Sheets: tetrahedral and octahedral

A **tetrahedral sheet** is a plane of linked tetrahedra, each a small cation —
usually silicon — surrounded by four oxygens. Three of the four are shared with
neighbouring tetrahedra to form a hexagonal net; the fourth, the *apical*
oxygen, points at the octahedral sheet and bonds into it. Aluminium commonly
substitutes for silicon here.

An **octahedral sheet** is a plane of larger cations — aluminium, magnesium,
iron — each surrounded by six anions. Some of those anions are the apical
oxygens of the tetrahedral sheets; the rest are **hydroxyls**, and their
presence is what makes the octahedral sheet the chemically distinctive part of
a clay.

The distinction matters to the calculation in a way beyond bookkeeping: a
hydroxyl scatters X-rays differently from a bare oxygen, so labelling one as
the other changes the computed pattern. MudLab therefore treats hydroxyl as its
own species rather than as an oxygen with a hydrogen attached.

### Dioctahedral and trioctahedral

An octahedral sheet has a fixed number of cation sites. Whether they are all
occupied is one of the sharpest divisions in clay mineralogy.

- **Trioctahedral** — every site is filled, typically by a divalent cation such
  as magnesium or ferrous iron. Talc and serpentine are trioctahedral.
- **Dioctahedral** — only two sites in three are filled, typically by a
  trivalent cation such as aluminium; the third is vacant. Kaolinite, illite
  and most smectites are dioctahedral.

The charge arithmetic explains it: three divalent cations and two trivalent
cations carry the same total charge, so a sheet balances either by filling
every site with a 2+ cation or by leaving one site in three empty and filling
the rest with 3+ cations.

MudLab reads this straight off the occupancies you give it — the total
octahedral cation content per unit cell, rounded. Four sites or fewer is
reported as dioctahedral, more as trioctahedral. It is a description of what
you entered, not an independent determination.

### The interlayer

The space between two layers is the **gallery** or interlayer. What occupies it
is the single most diagnostic thing about a clay, because it is the part that
responds to treatment.

It may hold:

- **nothing** — the layers are held by weak forces alone, as in talc and
  pyrophyllite;
- **an exchangeable cation with water** — calcium, sodium or magnesium
  surrounded by water molecules, as in smectite and vermiculite. The water
  content, and hence the spacing, varies with humidity and with the cation;
- **a cation without water** — potassium in illite and the micas, which fits
  the hexagonal hole of the tetrahedral sheet so neatly that it locks adjacent
  layers together and excludes water;
- **a continuous hydroxide sheet** — in chlorite, a brucite-like sheet that is
  bonded in place rather than exchangeable.

That last case is why MudLab refuses to derive swelling states for a
chlorite-like structure: its interlayer is part of the crystal, not a guest in
it. The program recognises the situation by finding octahedral cations sitting
in the interlayer.

### Layer charge, and what separates one clay from another

A 2:1 layer would be electrically neutral if its tetrahedral sheets were pure
silicon and its octahedral sheet held only the right cations in the right
numbers. Talc and pyrophyllite are almost exactly that, which is why they have
empty galleries and do not swell.

Real clays substitute: aluminium for silicon in the tetrahedral sheet,
magnesium or iron for aluminium in the octahedral sheet. Each substitution puts
a cation of lower charge in a site, leaving the layer with a **net negative
charge**. That charge must be balanced by cations in the interlayer, and *how
much* charge there is decides which mineral you have:

| Layer charge, per formula unit | Mineral | Interlayer behaviour |
|---|---|---|
| ~0 | talc, pyrophyllite | empty; no swelling |
| ~0.2–0.6 | **smectite** | hydrated exchangeable cations; swells readily |
| ~0.6–0.9 | **vermiculite** | hydrated exchangeable cations; swells less |
| ~1.0 | illite, micas | potassium, fixed; no swelling |

This is worth stating plainly because of a consequence MudLab has to live with:
**layer charge is not visible in a single diffraction pattern, and not visible
in a single refined crystal structure either.** It is a chemical property. So
when the program needs to know whether a 2:1 clay is a smectite or a
vermiculite — as it does when deriving treatment states — it asks you rather
than guessing. Nothing in the data answers the question.

### Basal spacing

Because the layers stack in a regular sequence, the strongest reflections come
from the repeat distance perpendicular to them — the **basal spacing**, usually
written *d*(001). It is the layer thickness plus the gallery, and it is the
number clay analysis lives on.

The spacings MudLab ships for its standard clays show the pattern:

| Mineral | Basal spacing |
|---|---|
| kaolinite | 0.716 nm |
| serpentine | 0.726 nm |
| talc | 0.94 nm |
| illite | 0.998 nm |
| chlorite | 1.42 nm |

A 1:1 layer is about 0.7 nm thick and has no gallery to speak of. A 2:1 layer
is about 0.94 nm including its own thickness when the gallery is empty, and
about 1.0 nm when potassium fills it. Chlorite's extra hydroxide sheet adds
another 0.5 nm. Smectite has no single value at all: its spacing depends on how
much water or glycol is in the gallery, which is precisely what makes it
identifiable.

Bragg's law converts a spacing to an angle,

> *n* λ = 2 *d* sin θ

so every basal reflection's position depends on the X-ray **wavelength** as
well as on the mineral. This is not a formality. If the wavelength recorded for
a scan is wrong, every spacing computed from it is wrong by the same factor,
and a mineral can be confidently misidentified — quartz measured with cobalt
radiation but read as copper comes out as a different mineral entirely.

### Why one dimension is enough

A clay crystal is three-dimensional, but MudLab represents a layer as a
**one-dimensional profile**: a list of atom heights measured perpendicular to
the layers, with an amount at each height. The lateral positions are discarded.

This is not an approximation forced by convenience; it follows from how the
sample is prepared and what is measured. A clay mount is made by settling
platy crystals onto a flat surface so that their layers lie parallel to it.
What such a preparation diffracts strongly is the *basal* series — the
reflections that arise from the stacking repeat — and those depend only on the
distribution of scattering matter along the stacking direction. Two atoms at
the same height contribute identically to a basal reflection however far apart
they lie within the layer.

The direction matters more than it first appears. The relevant axis is not the
crystallographic *c* axis but the direction perpendicular to the layers — the
reciprocal-space direction usually written **c\***. In a monoclinic or triclinic
clay the *c* axis is tilted, so the two are different. Projecting onto the
perpendicular is exact: an atom's height above the layer plane is its
fractional coordinate along *c* multiplied by the basal spacing, with no
contribution at all from the other two coordinates.

What the projection costs is everything that depends on lateral order —
the *hk* reflections, stacking faults expressed as lateral offsets, and any
distinction between two structures that differ only in how their layers are
rotated or shifted relative to one another. For basal-series clay analysis,
none of that is being measured anyway.

### Treatment: making a clay declare itself

Since layer charge cannot be seen and many clays have similar basal spacings
when air-dried, clay identification rests on **how a mineral responds to
treatment**. The standard sequence is three scans of the same sample:

1. **air-dried** — the baseline;
2. **ethylene-glycol solvated** — glycol displaces interlayer water and expands
   a swelling clay to a characteristic spacing near 1.7 nm;
3. **heated**, usually to 350 °C — the gallery is driven out and a swelling
   clay collapses to about 1.0 nm.

The diagnosis is in the *changes*, not the positions. Smectite expands under
glycol and collapses on heating. Vermiculite collapses on heating but expands
less under glycol. Illite and kaolinite do neither. Chlorite does neither but
keeps its 1.42 nm reflection through both.

MudLab models this as one phase per treatment, assigned to the matching
specimen. The layer is the same mineral throughout — a treatment changes the
gallery, not the sandwich — which is why the program can build the glycolated
and heated states from an air-dried structure, and why those states share their
layer rather than each carrying a copy of it.

Two assumptions come with that, and both have limits worth knowing. The layer
is only invariant to *first order*: heating to 550 °C drives hydroxyls out of
the octahedral sheet and genuinely changes the layer, so a derived heated state
should be read as a 350 °C model. And a derived gallery is a *reference* taken
from a standard clay, not a measurement of your specimen — a starting point for
refinement rather than a result.

---

## From atoms to a layer

Batch A described what a clay is. This section describes how MudLab turns that
description into scattered X-rays: what each atom contributes, how the
contributions combine into a layer, and which of the numbers you can edit
actually move the answer.

### The coordinate everything is a function of

Diffraction quantities are not naturally functions of angle. They are functions
of

> 2 sin θ / λ

which has units of inverse length and is the length of the scattering vector —
how far into reciprocal space a given reflection sits. Every quantity in this
section is computed against that coordinate rather than against 2θ.

Two consequences follow, and both matter in practice.

First, the same structure measured with a different X-ray wavelength produces
the *same* curve in this coordinate and a *different* curve in angle. That is
why a wavelength error is not a small distortion but a wholesale rescaling of
the pattern.

Second, scattering falls away as this coordinate grows. Low-angle reflections
are strong and sharp; high-angle ones are weak. For clay work this is
convenient — the basal reflections that carry the diagnosis sit at low angle,
where the signal is.

### What one atom scatters

An atom's ability to scatter X-rays is not a single number. It falls off as the
scattering vector grows, because the electron cloud has a size comparable to
the X-ray wavelength and the waves scattered from its near and far sides
increasingly cancel.

That falloff is tabulated, for every element and common ionisation state, as a
sum of Gaussians plus a constant:

> *f* = *c* + Σ *aᵢ* exp( − *bᵢ* *s*² ),  where *s* = sin θ / λ

MudLab uses a **five-term** expansion — five paired coefficients plus the
constant, taken from the standard crystallographic tabulations and shipped with
the program for a few hundred species. You do not enter these; you choose an
atom *type*, and the type carries them.

This is why choosing the right species matters and choosing the right *element*
is not enough. The tabulations distinguish neutral atoms from ions, and a clay
model uses the ionised forms, because a silicon that has given up electrons
scatters measurably differently from a neutral one.

It is also why **hydroxyl is a species in its own right** rather than an oxygen
with a hydrogen beside it. Hydrogen scatters X-rays so weakly that modelling it
as a separate atom would be pointless; instead the oxygen-plus-hydrogen pair is
tabulated as one scatterer with its own coefficients. Getting this wrong is not
catastrophic but is not negligible either: mislabelling a clay's hydroxyls as
plain oxygens shifts individual intensities by several per cent and the
strongest basal reflection by a few per cent.

### Thermal motion

Atoms are not at rest. They vibrate about their sites, and the vibration blurs
the electron density, which weakens scattering more at high angle than at low —
the same geometry as the falloff above, for a different reason.

The correction is a single exponential in *s*², controlled by one number per
atom type, the **temperature factor** (conventionally *B*, in Å²):

> *f* → *f* · exp( − *B* *s*² )

A larger value means a more loosely held atom and a faster falloff. In clay
work these are rarely refined; the shipped types carry sensible values, and the
correction matters mainly because omitting it entirely would leave the
calculated pattern too strong at high angle.

### Adding the atoms up

A layer's scattering is the **sum of its atoms' contributions, each carrying a
phase set by its height**. For a one-dimensional profile the phase of an atom
at height *z* is

> exp( 2π i *z* · (2 sin θ / λ) )

and the layer's structure factor is the sum over every atom of its scattering
power, times how many of that atom the cell contains, times that phase.

Three things are worth drawing out of that expression.

**Only height enters.** As batch A explained, an atom's lateral position does
not affect a basal reflection. The sum is over heights and amounts; nothing
else about the atom's position is used.

**Interference does the work.** The sum is over complex numbers, so atoms at
different heights can reinforce or cancel. This is why the *relative* positions
of the sheets within a layer control which basal orders are strong and which
are nearly absent — and why an error of a few hundredths of a nanometre in one
atom's height can change the pattern more than a large error in its amount.

**Amount is as important as identity.** An atom's contribution scales linearly
with how many of it the cell holds. This is the quantity that partial site
occupancy and cation substitution change, and it is where refinement usually
has most of its freedom.

### Occupancy and substitution

Real clays do not have clean formulas. A single octahedral site may be occupied
by aluminium in one unit cell and by magnesium or iron in the next, and what
diffraction sees is the *average*: a site with fractional amounts of several
species.

MudLab represents this directly — each atom row carries an amount that need not
be a whole number — and then lets you tie amounts together instead of typing
them independently. Two kinds of tie are available:

- a **substitution** between two species sharing a site, expressed as the
  fraction of the site taken by the first, with the second taking the
  remainder. The total occupancy of the site stays fixed while the ratio
  varies.
- a **content** rule, which scales a whole set of atoms by one shared value —
  useful when a treatment or a compositional variable moves several amounts
  together.

Both are ordinary refinable quantities. The reason to prefer them over typing
amounts by hand is not convenience but constraint: a substitution *cannot*
produce a site that is more than full, whereas two independently refined
amounts can, and a refinement given that freedom will sometimes take it.

Because amounts feed the oxide composition as well as the pattern, a
substitution refined against diffraction data also moves the chemistry the
program reports. That is a feature — the two should agree — but it means an
implausible refined composition is evidence that the structural model, not just
the fit, needs attention.

### The gallery stretches; the layer does not

A component records the basal spacing it was built with as well as the spacing
it currently has. When those differ — because the clay has swollen, or because
refinement has moved the spacing — the atoms do **not** all move in proportion.

The layer is treated as rigid and the gallery as elastic. Atoms below the
layer/interlayer boundary keep their heights exactly; atoms above it are
rescaled so that they move with the expanding or contracting gallery. A
smectite swelling from one water layer to two therefore lifts its interlayer
water and its exchangeable cation, and leaves its silicate sandwich untouched.

This is the same physical claim that lets treatment states be derived from an
air-dried structure, and it is applied here every time a pattern is computed,
not only when states are built.

### Disorder in the spacing itself

Real stacks are not perfectly periodic even when the layers are identical: the
distance from one layer to the next varies slightly. That variation blurs the
higher-order basal reflections while leaving the first order almost untouched,
because a small spread in spacing is a small fraction of a large *d* but a
large fraction of a small one.

MudLab models it with one number per component — a spread in the basal spacing
— which enters as a Gaussian damping that grows with the square of the
scattering vector. The effect looks like a temperature factor applied to the
whole layer rather than to one atom, and it is often the difference between a
calculated pattern whose high orders are too strong and one that matches.

It is worth distinguishing this from crystallite size, which is treated in the
next batch. Both weaken high-order reflections, but they are different physics:
spacing disorder is variation *within* a stack, while size broadening comes
from the stack being finite. A model can need both.

---

*Batches on stacking, instrument corrections, fitting, and identification are
planned; see the documentation plan in the repository.*
