# Deriving treatment states — method, theory and assumptions

*Written 2026-08-30, when the feature was built. Recorded for revisiting: the
method here is deliberate but provisional, and the assumptions are listed so
they can be argued with rather than rediscovered.*

**Edit Phases → right-click a phase → Create treatment states…**

---

## The problem

Clay identification rests on how a mineral responds to treatment, not on a
single scan. The standard sequence is **air-dried → ethylene-glycol solvated →
heated (usually 350 or 550 °C)**, and it is diagnostic precisely because
different clays respond differently: smectite expands under glycol and collapses
on heating; vermiculite collapses on heating but expands less under glycol;
illite and kaolinite do neither.

Modelling that in MudLab means one phase per treatment, assigned to the
matching specimen column of a mixture.

But a **CIF is one structure in one state**. The crystallographic record for a
clay is essentially always the air-dried (or vacuum-dried) form — nobody
deposits a second single-crystal refinement of the same specimen after glycol
solvation, because a solvated smectite is not a good diffraction subject. So
the treated states a clay workflow needs cannot be imported. They have to be
constructed.

## The physical claim the method rests on

**A treatment changes the interlayer, not the layer.**

Solvation and heating add, replace or remove species in the **gallery** between
2:1 layers, changing the basal spacing. They do not restructure the 2:1 layer
itself — the tetrahedral–octahedral–tetrahedral sandwich is the same object in
every state of the same clay.

This is not an assumption invented for MudLab2: **MudLab's own shipped
components are built on it.** All six states of Di-Smectite (2WAT, 1WAT,
Dehydr, 2GLY, 1GLY, Heated) carry the *identical ten layer atoms* and differ
only in `d001` and `interlayer_atoms`. The shipped catalog then links them —
a treated component inherits `ucp_a`, `ucp_b`, `delta_c` and `layer_atoms` from
the air-dried one and keeps its own spacing and gallery
(`default_catalog._INHERIT_S`).

The derivation here does the same thing with an imported layer instead of a
shipped one.

## The method

Given a phase whose single component is a 2:1 clay in some known state:

1. **Take the layer from the imported component**, by *link* rather than by
   copy. The derived component sets `linked_with` to the base component and
   turns on the four inherit flags above. Consequence: refining the layer
   refines every state at once, which is the reason for modelling a series
   rather than three unrelated phases.

2. **Take the gallery from the corresponding shipped state.** Its interlayer
   species (water, glycol, exchangeable cation) and their arrangement are
   transplanted.

3. **Transplant by gallery height, not by absolute z.**

   ```
   gallery  = donor.d001 − donor.layer_top
   new d001 = base.layer_top + gallery
   shift    = base.layer_top − donor.layer_top      (applied to every guest)
   ```

   A shipped 2:1 layer tops out at 0.654 nm; an imported illite layer at
   0.671. Copying interlayer heights verbatim would drive the guests 0.017 nm
   *into* the layer beneath them. What is physically meaningful — and what a
   treatment actually changes — is the thickness of the gallery, so that is
   what carries across. The derived spacing therefore differs from the donor's
   by exactly the layer-thickness difference.

4. **Create the phases.** `<name>-EG` and `<name>-350`, each `based_on` the
   original phase and inheriting its colour, σ\* and CSDS distribution — again
   matching what the shipped catalog does for a treated phase
   (`_INHERIT_PHASE`).

## What is asked, and why it cannot be computed

Two questions the dialog puts to the user, because neither is present in the
structure:

- **Which family's gallery to borrow** — Di-Smectite, Tri-Smectite or
  Di-Vermiculite. Smectite and vermiculite differ by **layer charge**, which a
  single refined structure does not reveal; di- versus tri-octahedral could be
  guessed from octahedral occupancy, but guessing half of the choice is worse
  than asking for all of it.
- **Which state the phase is already in.** A published structure is usually
  air-dried but not reliably so: the four montmorillonite CIFs in the reference
  corpus project to **0.97, 1.11, 1.22 and 1.22 nm** — dehydrated through
  one-water-layer. Assuming air-dried would silently mis-anchor the series.

## What is refused, and on what grounds

- **1:1 clays** (kaolinite, serpentine). A 1:1 layer has no interlayer gallery,
  does not swell, and has no glycolated state to derive. Detected by counting
  **one tetrahedral sheet** in the projected layer.
- **Chlorite-like structures.** 2:1 by sheet count, but the interlayer is a
  continuous hydroxide (brucite) sheet rather than exchangeable guests —
  octahedral cations sitting in the interlayer are its signature. Chlorite does
  not swell; filling that sheet with glycol would model a mineral that does not
  exist.
- **Multi-component phases.** A mixed-layer phase has no single layer to share,
  so the one-to-one link the method depends on is not available.

## Assumptions, stated so they can be challenged

1. **The layer is invariant under treatment.** True to first order and the
   basis of the shipped components, but not exact: glycol solvation can flex a
   layer slightly, and heating a smectite ultimately dehydroxylates it. At
   550 °C the layer is *not* the same object, so a "-350" state derived this
   way should be read as a 350 °C model, not a 550 °C one.
2. **The gallery is transferable between clays of the same family.** The
   derived state wears a *reference* gallery, not this specimen's. It is a
   starting point for refinement, not a measurement.
3. **The gallery's thickness is the transferable quantity**, rather than the
   guests' absolute positions. This is what makes the transplant
   layer-independent.
4. **One donor state per treatment.** EG takes 2GLY and heated takes Heated.
   Real smectites are often interstratified and glycolate to a mixture of one-
   and two-layer states; the shipped catalog models that with hydration
   *ladders* of several interstratified states, which this derivation does not
   yet reproduce.
5. **Calcium is the exchangeable cation.** Every shipped family is the Ca form.
   A Na- or K-saturated clay swells differently, and no other cation is
   bundled.

## Known gaps, for the revisit

- **Interstratification.** The biggest one — see assumption 4. A real
  glycolated smectite is usually modelled as an R0/R1 mixture of states, and
  the catalog already has the machinery (`_smectite_columns`, the hydration
  ladders). Deriving a *ladder* rather than a single state is the natural next
  version.
- **Only 350 °C.** No 550 °C state is derived, and the assumption above says it
  would need a different layer, not just a different gallery.
- **Only the Ca form.**
- **The base state is recorded but not used.** The answer to "which state is
  this phase in" is asked and stored in the series name; it does not yet change
  what is derived. It should: a phase already in a 2GLY state does not need a
  glycolated sibling.

## Where the code is

| | |
|---|---|
| `src/mudlab/treatment_variants.py` | the method — `can_derive`, `transplant_gallery`, `derive` |
| `src/mudlab/treatment_states_dialog.py` | the two questions |
| `src/mudlab/edit_phases_dialog.py` | the menu action |
| `tools/verify_treatment_states.py` | 33 checks, corpus-free |
