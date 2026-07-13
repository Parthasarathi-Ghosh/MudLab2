# MudLab2 user manual

Guide to using the MudLab2 GUI. This manual grows as features are added.

## Contents

- [Phase inheritance ("based on")](#phase-inheritance-based-on)
- [Component linking and inheritance](#component-linking-and-inheritance)

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
- **Stacking probabilities** — on the Probabilities tab each **F** parameter has
  its own *Inherit* box, so you can share some and keep others.

A ticked box greys the field and shows the **reference phase's** value. Untick it
and the phase goes back to its own value. The pattern recalculates either way.

> **The stacking F parameters matter most.** They control the layer proportions
> and therefore the shape of the pattern. If a treated phase should have the
> same illite/smectite ratio as the reference, inherit its F — otherwise the two
> can drift apart and no longer describe the same clay.

### Changing an inherited value

An inherited field is greyed on the treated phase. Edit it on the **reference
phase** (the one showing *(not based on)*) and every phase based on it updates.

### Detaching

Choose **(not based on)**. The link is removed, all inherit boxes for that phase
are cleared, and every field returns to that phase's own values.

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

Choose **(not linked)** in the **Linked with** drop-down. The link is removed,
all inherit boxes for that component are cleared, and every field returns to
this component's own values.

### Notes and tips

- **Inherited cell a / b also lock the cell-length editor.** When Cell a or
  Cell b is inherited, that cell's fixed/derived editor is disabled — the value
  comes from the template.
- **Two check-boxes are read-only:** *d001 (follows cell c)* mirrors the
  Cell c / default c setting, and *Atom relations* becomes active once the
  atom-relations editor is available.
- **A component cannot link to itself**, and links cannot form a loop
  (A → B → A). Such a choice is refused and the drop-down snaps back.
- **You can link any two components.** MudLab2 does not restrict templates to a
  particular parent phase, so take care to link layers that really are the same
  clay layer.
