# Documentation track

A **parallel work track**, picked up during idle time and put down again when
bug-fixing or feature work needs the session. Nothing here blocks a release
except where a deliverable says so.

**To switch in:** type `/docs` (or say "docs track"). That reads this file,
picks up at *Where we stopped*, and continues.
**To switch out:** just give a normal task. Before switching out, whatever was
in progress gets written back into *Where we stopped* below, so the next session
resumes without re-deriving anything.

---

## The three deliverables

| # | Document | File | Audience | Status |
|---|---|---|---|---|
| 1 | **Walkthrough** — the essential path through the UI, start to finish | `docs/getting-started.md` | A new user with a scan and no idea where to click | **Draft done, awaiting review** |
| 2 | **How it works** — the algorithms in prose. No code, no variable names | `docs/how-it-works.md` | A clay scientist who wants to know what the numbers mean | **COMPLETE** — all six batches written |
| 3 | **Technical reference** — for bug-fixing and future development | `docs/technical-reference.md` | Whoever maintains this next (including us, later) | Slow track |

### How these relate to what already exists

`docs/user-manual.md` (1257 lines) already exists and is **feature-by-feature
reference** — accurate for MudLab2's UI and worth keeping. It is *not* any of
the three above; it is the detailed middle layer.

The intended shape:

```
getting-started.md   the front door   -> links into user-manual.md for detail
user-manual.md       the reference    (already written, keep growing it)
how-it-works.md      the theory       (#2)
technical-reference.md  the internals (#3)
```

Do **not** fold `user-manual.md` into #1. #1 is deliberately short; its job is
to get someone from a raw file to a saved result without deciding anything they
do not have to decide.

---

## Source material to collate

Two repositories' worth. Nothing here has been merged yet except where #1 says
so.

**This repo (`c:\GitHub\MudLab2\docs\`)**

| File | Lines | Feeds |
|---|---|---|
| `user-manual.md` | 1257 | #1 (UI names are accurate here), #2 |
| `dev-notes.md` | 176 | #3 |
| `remaining-work.md` | 304 | #3 |
| `nonclay-integration.md` | 40 | #2, #3 |

**The old GTK app (`c:\GitHub\MudLab\`)** — ~6100 lines total.

`docs/how-to/` (19 files): `diffraction-calculation`, `refinement`,
`composition`, `default-phases`, `default-component-structures`, `edit-phases`,
`atom-relations-substitutions`, `change-interlayer-cation`, `markers`,
`exclusion-ranges`, `goniometer-shift`, `plot-anatomy`,
`parameter-space-plots`, `project-file-format`, `file-formats`,
`import-excel-xrd`, `troubleshooting`, plus `docs/index.md` and
`docs/calculation-flow-atom-type-change.md`, `docs/dev/atom-relations-guardrails.md`.

`notes/` (14 files): `Architecture`, `XRD Diffraction Calculation`,
`Refinement`, `Mixture Model`, `Phase and Component Model`, `Atom Relations`,
`Markers and Peak Detection`, `Oxide Composition`, `CIF Import`, `File Formats`,
`MudLab Overview`, `GTK UI Conventions`, `HANDOFF-to-mudlab2`,
`HANDOFF-from-mudlab2`.

**Rough routing:**

- **#2** ← `notes/XRD Diffraction Calculation`, `notes/Refinement`,
  `notes/Mixture Model`, `notes/Phase and Component Model`,
  `notes/Markers and Peak Detection`, `notes/Oxide Composition`,
  `notes/Atom Relations`, `how-to/diffraction-calculation`,
  `how-to/refinement`, `how-to/composition`
- **#3** ← `notes/Architecture`, `notes/File Formats`, `notes/CIF Import`,
  `how-to/project-file-format`, `how-to/file-formats`,
  `docs/calculation-flow-atom-type-change.md`, this repo's `dev-notes.md`, plus
  the `tools/verify_*.py` docstrings (83 of them), which are the closest thing we have to
  a spec of intended behaviour

**Caution when collating from the old app.** Those documents describe the *GTK*
app. Menu paths, dialog names and control labels differ from MudLab2's, and some
described features were never ported (and some MudLab2 features do not exist
there). Take the *substance* — algorithms, file formats, reasoning — and
re-derive every UI instruction against MudLab2's actual widgets. `GTK UI
Conventions` in particular is obsolete here.

---

## Rules per deliverable

**#1 Walkthrough** — only the essential steps. One linear path. No branches the
reader does not need. Every menu path and button label verified against the real
UI, not remembered. Where a step has a trap that will silently ruin results
(wavelength, most of all), say so in one sentence and move on.

**#2 How it works** — prose. **No code and no actual variable or function
names.** Name the physics and the method, not the implementation. Equations are
fine; identifiers are not. A reader should finish knowing what the program is
computing and why, without being able to tell what language it is written in.

**#3 Technical reference** — the opposite: names, files, data structures, file
formats, invariants, the harnesses and what each pins. Written for someone
debugging at 2am.

---

---

## Deliverable #2 — `how-it-works.md`: the batch plan

*Planned 2026-08-30. Written in batches on purpose, so the session can leave
for bug-fixing between any two of them without losing its place.*

### What it is

**A glossary of the science behind each feature**, not a linear textbook. Each
entry names the thing, says what it means physically, states the assumptions
the app makes about it, and describes the algorithm in prose. A clay scientist
should finish an entry knowing what MudLab is computing and what it is taking
on trust.

### Its rule, restated because it is easy to slip

**Prose. No code, and no variable or function names.** Name the physics and the
method, not the implementation. Equations are welcome — Bragg's law, the
Cromer-Mann sum, the log-normal — and so are the names of published methods and
their authors. Identifiers are not: a reader should not be able to tell what
language the program is written in.

`docs/treatment-states-method.md` is a good model for the *register* — the
level of care about assumptions — but it is a developer document that names
files and functions freely, and #2 must not.

### The batches

Ordered along the physical chain, so each may lean on the previous one's
vocabulary. Any batch can still be written out of order if a feature becomes
topical.

| # | Batch | Entries | Status |
|---|---|---|---|
| A | **The material** | What a clay layer is (1:1, 2:1, 2:1:1); di- and trioctahedral sheets; the interlayer and its occupants; layer charge and why it separates smectite from vermiculite from illite; basal spacing; why a one-dimensional profile along the c\* direction is enough; treatment response | **DONE 2026-08-30** |
| B | **From atoms to a layer** | The reciprocal-space coordinate; atomic scattering factors (a FIVE-term Gaussian expansion, not the four the old note claims); thermal motion; the layer structure factor; occupancy and substitution; the gallery stretching while the layer stays rigid; spacing disorder as distinct from size broadening | **DONE 2026-08-30** |
| C | **Stacking** — the heart of the app (**DONE 2026-08-30**) | Mixed-layer clays and interstratification; Reichweite and what "R0/R1/R2/R3" claims about memory; junction probabilities and the weight/transition matrices; Markovian stacking and the recursive summation (Drits & Tchoubar 1990; Plançon 2001); crystallite thickness as a log-normal distribution and what a coherent scattering domain is | done |
| D | **From a layer to a pattern** — the instrument (**DONE 2026-08-30**) | Lorentz and polarisation factors; preferred orientation and the sigma-star parameter; Soller slits; fixed against automatic divergence slits and what converting between them assumes; sample length and beam overflow; absorption; the emission spectrum and why the wavelength decides every d-spacing | not started |
| E | **From a pattern to an answer** — fitting (**DONE 2026-08-30**) | The specimen: scale and background; the mixture as a grid of phases against specimens; what Optimize adjusts and what Refine adjusts, and why they are different problems; residuals (Rp, Rwp, goodness of fit) and what each rewards; refinement methods and their assumptions; why a good fit is not proof | not started |
| F | **Identification and chemistry** (**DONE 2026-08-30**) | Peak detection — the threshold method and the prominence method; Bragg's law and d-spacings; mineral matching, how candidates are scored, and why the wavelength must be right first; oxide composition from a structural model and what it can and cannot say; pattern corrections (background, smoothing, shift, trimming) and what each costs the data | not started |

Six batches, each a sitting. **A, B and C are the ones that carry the app's
distinctive science**; D, E and F are more widely documented elsewhere and can
lean on references.

### Where the material comes from

The code is the authority on what is *implemented*; the old app's notes are the
best summary of the theory and should be re-expressed, not copied:

- **`C:\GitHub\MudLab\notes\XRD Diffraction Calculation.md`** — the whole
  pipeline in one page, with the equations. Feeds B, C and D.
- **`notes/Refinement.md`**, **`notes/Mixture Model.md`** — feed E.
- **`notes/Phase and Component Model.md`**, **`notes/Atom Relations.md`** —
  feed A and B.
- **`notes/Markers and Peak Detection.md`**, **`notes/Oxide Composition.md`** —
  feed F.
- This repo's `docs/treatment-states-method.md` — feeds A (treatment response)
  and is already written in the right spirit.
- The calculation modules themselves carry unusually full docstrings, several
  naming their sources (Drits & Tchoubar 1990, Plançon 2001, Cromer-Mann).

### Bundling

`how-it-works.md` is user-facing, so when the first batch lands it must be
added to **`MudLab.spec`** and linked from the manual — `verify_manual.py`
fails otherwise, by design ("every document the manual can reach is bundled").
Do that with batch A, not at the end.

---

## Where we stopped

**2026-08-30** — Caught the manual up with the CIF-import feature, which
shipped after this plan was written and was documented nowhere user-facing.
`user-manual.md` gains two sections, placed with the other component material
and verified label by label against the running widgets:

- **Building a component from a CIF** — the Import CIF… button, the review
  window's three parts, the Kind/Sheet columns and why those two are the ones
  worth checking, atom types added on accept, sepiolite refused, and the P1
  caveat for a file with no symmetry operators.
- **Treatment states: air-dried, glycolated, heated** — what the derivation
  creates, the two questions it asks and why neither can be computed, what it
  refuses, and the assumptions that change how the result should be read (a
  reference gallery, not a measurement; -350 is a 350 °C model, not 550 °C;
  every shipped family is the Ca form).

`getting-started.md` gains **one pointer, not a step** — the shipped catalog
covers the common clays, so CIF import is not on the short path.

One constraint worth remembering: **`treatment-states-method.md` is NOT
bundled**, so the manual must not link to it or the link is dead in the frozen
app. `verify_manual.py` enforces that ("every document the manual can reach is
bundled"), so the user-facing assumptions are stated inline instead. Anything
new the manual links to must be added to `MudLab.spec`.

Earlier: track created 2026-08-29, deliverable #1 drafted end to end, and the
in-app viewer built so F1 opens it.

Next actions, in order:

1. **Review pass on #1 by the user.** Still a first draft; the shape is there,
   the wording will want tightening. Unchanged since it was written.
2. **Screenshots for #1** — still deliberately none. The UI moved again this
   week (Import CIF…, Create treatment states…), which is the argument for
   waiting.
3. **Write #2 batch by batch** — the batch plan is above. **All six batches are
   written** and `how-it-works.md` is bundled and linked. Deliverable #2 is
   COMPLETE as planned; what remains for it is a review pass and whatever new
   features add.
4. #3, `technical-reference.md`, after that.

**2026-08-30, later:** deferred the review pass and the screenshots at the
user's request; planned #2 as six batches (above) and wrote **batch A**. It
covers the layer types, the two kinds of sheet, di/trioctahedral occupancy, the
interlayer, layer charge (and why it is invisible to diffraction, which is why
the program asks rather than guesses), basal spacing with Bragg, why a
one-dimensional profile along c* loses nothing that basal analysis uses, and
the treatment sequence with the limits of its assumptions.

**Batch B** followed: the reciprocal-space coordinate, atomic scattering
factors, thermal motion, how atom contributions combine into a layer,
occupancy and substitution, and two things the old notes do not cover — that
the gallery is rescaled while the layer stays rigid whenever the spacing
changes, and that spacing disorder damps high orders by a different mechanism
from crystallite size. Reading the code corrected the old note on one point:
the scattering-factor expansion has **five** Gaussian terms, not four.

**Batch C** covers the stacking model: interstratification and why it is not a
mixture of two minerals, Reichweite as a claim about the mineral rather than a
fitting knob, weights and junction probabilities with detailed balance, why a
higher Reichweite *restricts* the possible compositions, how the matrix power
carries both geometry and statistics so line broadening falls out of the
statistics rather than a fitted peak shape, crystallite thickness as a coherent
scattering domain, and the absolute scale that makes fitted fractions
comparable between phases.

**A real bug surfaced while checking batch C in the app**, and it had been
shipping since the viewer was built: the quote-tinting pass edits the document
between `setSource` and its first layout, which leaves the layout permanently
collapsed — paragraphs at zero height, so a long page renders as a run of bare
headings with all its text present, and every anchor past the middle scrolls to
the bottom. Fixed by forcing the layout before editing. The first regression
check written for it PASSED with the bug reintroduced (wrong document, reused
dialog); the one that ships now fails on two documents when the fix is
removed.

**Not started:** #2, #3.
