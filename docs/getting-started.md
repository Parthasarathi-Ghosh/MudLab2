# MudLab: a first walkthrough

This is the short path through MudLab — from a raw diffractogram to a saved,
quantified result. It covers the essential steps only, in the order you will
actually do them.

For the detail behind any step, see the [user manual](user-manual.md); for
the science behind what it computes, [How MudLab works](how-it-works.md).

**Contents**

1. [Before you start](#1-before-you-start)
2. [Import your specimens](#2-import-your-specimens)
3. [Check the specimen's settings](#3-check-the-specimens-settings)
4. [Correct the pattern](#4-correct-the-pattern)
5. [Find and label the peaks](#5-find-and-label-the-peaks)
6. [Identify minerals from the peaks](#6-identify-minerals-from-the-peaks)
7. [Add the phases to your project](#7-add-the-phases-to-your-project)
8. [Build a mixture](#8-build-a-mixture)
9. [Optimize](#9-optimize)
10. [Refine](#10-refine)
11. [Save and export](#11-save-and-export)

---

## 1. Before you start

MudLab models **clay mineral diffraction patterns**. You give it one or more
measured scans and a set of candidate clay structures; it calculates what those
structures would produce, and fits them to what you measured.

Two ideas make everything else fall into place:

- **One project is one physical sample.** The specimens inside a project are
  different preparations or treatments of *that same sample* — air-dried,
  glycolated, heated — not different samples. Start a new project for a new
  sample: **Project → New Project** (`Ctrl+N`).
- **A mixture is the model.** Phases (the clay structures) and specimens (your
  scans) are just ingredients. The mixture is the table that says *which phases,
  in what proportions, explain which scans* — and that is what gets fitted.

The window has three parts: the **specimen list** on the left, the **plot** in
the middle, and the **toolbar** across the top. Everything below is reachable
from the menus; most of it is also on the toolbar.

---

## 2. Import your specimens

**Data → Import Specimens**, or the same item by right-clicking the specimen
list. Pick one or more files — you can select them all at once.

MudLab reads ASCII XY text (`.xy`, `.txt`, `.csv`, `.dat`, `.tab`) and Bruker
`.uxd`, PANalytical `.xrdml`, Rigaku `.rasx`, and `.raw` from both Bruker and
Rigaku. Each file becomes one specimen, named after the file.

The pattern appears in the plot. The specimen list has three checkbox columns
controlling what is drawn for each row: **Exp** (the measured pattern), **Cal**
(the calculated one, once you have a model) and **Sep** (each phase drawn
separately, in its own colour).

> **Plain text files:** if the columns are not picked up as you expect, the
> import offers delimiter and decimal-separator options. The decimal separator
> can never also be the delimiter — MudLab will not let you choose that.

---

## 3. Check the specimen's settings

Right-click the specimen → **Edit specimen**. Two tabs matter now.

**General** — give it a meaningful **Name** (e.g. *Air dried*, *Glycolated*,
*Heated 550*). The **Source** box shows what the file told MudLab: the 2θ range,
step and point count, and any instrument details the format recorded.

**Goniometer** — this is the one to check before anything else.

> **Check the wavelength first.**
>
> **Peak positions depend on the wavelength.** MudLab converts between angle and
> d-spacing using the wavelength on this tab, so if it is wrong, every d-spacing
> is wrong — and mineral identification (step 6) will confidently name the wrong
> mineral. Quartz measured on a cobalt tube, read as if it were copper, comes
> back as *diopside*.
>
> `.xrdml`, `.rasx`, `.uxd` and older Bruker `.raw` files record their
> wavelength and MudLab applies it automatically. **Plain text and Rigaku `.raw`
> files do not** — those silently assume copper Kα₁ (0.154056 nm). If you
> measure on anything else, set it here.

The 2θ range and step count are filled in from the scan you imported. If your
instrument is one of the presets, pick it from the **Load setup** drop-down —
that fills in geometry, slits, range and emission spectrum in one go. **Store
setup** saves your own configuration for reuse.

Repeat for each specimen. Press `F5` (**Refresh Graph**) after changing anything
that affects the calculation.

---

## 4. Correct the pattern

All of these are on the toolbar, and the common ones are also under the **View**
menu. Apply them to the selected specimen.

> **These change the data permanently and cannot be undone.** Each dialog warns
> you. Save the project first if you want a way back.

**Shift Pattern** — corrects a systematic 2θ offset. Choose an internal
standard from the list (Quartz, Silicon, Zincite, Corundum, Goethite, Gibbsite)
and MudLab detects how far that reflection sits from where it should be, then
shifts the whole pattern by that amount. Or choose **Manual** and type the
offset. Do this before anything that depends on peak positions.

**Trim** — clips the pattern to a 2θ window. Set **Min °2θ** and **Max °2θ**.
Apply to **This specimen only** or **All loaded specimens** — the latter is the
easy way to put every treatment on the same range.

**Smooth Data** — reduces noise. **Moving Triangle** is a sensible default;
Savitzky-Golay, Gaussian, moving average, spline and Butterworth are also
offered. Raise **Degree** for more smoothing. **Show Original** overlays the
untouched pattern so you can see what you are removing — check it before you
accept, because over-smoothing quietly flattens weak reflections.

**Remove Background** — subtracts a **Linear** background, a constant
**Background value**, or another **Pattern** file scaled and offset to match.

---

## 5. Find and label the peaks

Open **Peaks** (toolbar, or right-click the specimen → **Peaks**). This is the
list of marked reflections for the specimen; each has a position and a label.

Press **Find peaks** to detect them automatically:

- **Pattern** — detect on the **Experimental** or **Calculated** curve.
- **Algorithm** — **Threshold (classic)** reproduces the established method;
  **Prominence (scipy)** is the modern alternative.
- For the threshold method, **Generate parameter histogram** plots how many
  peaks you get at each threshold, so you can pick a value on the flat part of
  the curve rather than guessing. Set **Min. distance (°2θ)** to stop one broad
  reflection being counted twice.

Accept the detected peaks and they appear in the list and on the plot. You can
add, delete and reposition them by hand — each peak's label and position are
editable, and the list keeps itself sorted by position.

To place a peak by eye, select it in the list and press **Sample** next to its
**Position** — the dialog steps aside, and your next click on the pattern sets
the position. Each peak also shows its position in both °2θ and nm.

> Do not confuse this with **Select Point** on the main toolbar: that one just
> reports the data values at the point you click. It does not create a peak.

---

## 6. Identify minerals from the peaks

With peaks marked, press **Match minerals** in the Peaks dialog.

MudLab converts each marked peak to a d-spacing (using the specimen's
wavelength — see step 3) and compares it against a reference library of ICDD
powder patterns. **Auto match** scores every mineral on how well its strongest
reflections line up with yours, both in position and in relative intensity, and
lists the best candidates.

- Select a candidate to see its reference lines drawn over your pattern. This
  is the check that matters — a good score with lines that visibly miss is not
  a match.
- Move minerals you accept into **Matched minerals** with the arrow buttons.
  Use **Search minerals…** to find one by name or abbreviation and add it by
  hand.
- **Append labels** writes the accepted mineral names onto the peak labels.

This step tells you *what to model*. It does not build the model — that is next.

---

## 7. Add the phases to your project

**Data → Edit Phases**. The list on the left is your project's phases; **Add**
opens the Add Phase dialog with three choices.

**Choose a default phase** — the one to use. MudLab ships a catalog of standard
clay structures (illite, kaolinite, chlorite, smectites, vermiculites, talc,
micas and more), including the glycolated and heated states you need for
treatment series. Pick the phases matching what step 6 identified.

The other two, for when you need them:

- **Create a new phase** — build from scratch. Choose the **Reichweite** (R0 for
  random stacking, R1 for nearest-neighbour ordering) and the **# of
  components**, then fill in the structure yourself.
- **Add a raw pattern** — use a measured pattern as a phase, when you have no
  structural model for something.

A default phase arrives complete and ready to fit. You can edit anything about
it — its components, atoms, stacking probabilities and crystallite size
distribution — but for a first pass you do not need to.

> If you have a published crystal structure of your own, a component can also
> be built from a `.cif` file, and the glycolated and heated states of a 2:1
> clay can be derived from it. Both are described under
> [Building a component from a CIF](user-manual.md#building-a-component-from-a-cif)
> in the manual — they are not part of the short path, and the shipped catalog
> covers the common clays.

---

## 8. Build a mixture

**Data → Edit Mixtures**, then **Add**. The mixture is a grid: **phases are
rows, specimens are columns**.

1. **Add phase** for each phase in your model; **Add specimen** for each scan.
   (**Add both** does one of each.)
2. In each cell, choose which phase fills that row for that specimen. This is
   what lets a treatment series work: the *same* clay is a different structure
   air-dried and glycolated, so the smectite row holds the air-dried smectite in
   one column and the glycolated one in the next.
3. Set a starting **fraction** for each phase and a **scale** for each specimen.
   Rough values are fine — they are about to be fitted.

The **Rp** figure shown is the mean residual against your experimental
patterns: how far the model currently is from the measurement. Lower is better.

Tick **Auto run** to have the mixture recompute whenever something changes.

---

## 9. Optimize

Press **Optimize**.

This adjusts the **phase fractions, specimen scales and background shifts** — the
proportions, not the structures — to best match your patterns. It is fast, it
needs no setup, and it is the right first move: it tells you whether your chosen
phases can account for the pattern at all.

Watch Rp. If it drops to something sensible, your phase selection is plausible.
If it stays poor, the problem is the model, not the fit — go back to step 6 or 7
and reconsider which phases are present, before spending time refining.

**Auto-adjust absolute scales** and **Auto-adjust background shifts** let
Optimize handle those automatically each time it runs.

---

## 10. Refine

Press **Refine** to fit the **structural** parameters — the ones that describe
the clays themselves. The dialog has three parts, in order.

**1. Parameters to refine.** A tree of every parameter you could fit. Tick
**Refine** on the ones you want and set a sensible **Min**/**Max** for each. The
counter shows how many are selected, and a warning line flags problems —
parameters that will not actually be refined, values outside their own limits,
values you typed by hand.

> **Refine few parameters at a time.** Every ticked parameter adds a dimension
> to the search. A handful of well-chosen ones converges; thirty at once wanders.
> Start with the parameters you have physical reason to doubt.

**2. Refinement.** Pick a **Method** and press **Refine**. The run happens in
the background and you can watch the residual fall; **Cancel** stops it and
keeps the best solution found so far. The **Progress** figure tells you how much
work the run may do for your current selection.

> Start with **L-BFGS-B** — it is fast and local. Basin Hopping is far more
> thorough and far slower: each of its iterations is a complete restart, so a
> "few iterations" is not a small job.

**3. Result.** The **Initial**, **Best** and **Last** residual (Rp), the
goodness of fit of the best solution, and a written report of the run. Then
**Which solution do you want to keep?** — choose **Initial** to discard the run
entirely, **Best** (the usual answer), or **Last**. Your choice is what gets
written back into the mixture, and the report is rewritten to describe it.

---

## 11. Save and export

**Project → Save Project** (`Ctrl+S`) writes a `.mud` file holding everything:
specimens, patterns, phases, mixtures and results.

Other outputs:

- **View → Save Graph** exports the plot as an image or vector file, at a size
  and resolution you choose. This is the figure for your report.
- **Edit Mixtures → Composition** shows the modelled oxide composition of the
  mixture. If you have XRF data, **Composition → Enter composition…** lets you
  enter the measured values and compare them against the model.
- **Project → Export** writes the project for other software: **MudLab (old
  app) project…** and **PyXRD project…**.

> Use **Export → MudLab (old app) project…** rather than a plain save if the
> file must open in the old MudLab. The old app rejects any file containing
> features it does not know about, and the exporter strips those.

---

## Where to go next

- [User manual](user-manual.md) — the full reference: every dialog, every
  option, and the reasoning behind the defaults.
- Phase inheritance, component linking and atom relations, for when one
  structure should be derived from another rather than edited independently.
- Exclusion ranges, for leaving a contaminated 2θ window out of the fit.
