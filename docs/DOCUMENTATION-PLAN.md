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
| 2 | **How it works** — the algorithms in prose. No code, no variable names | `docs/how-it-works.md` | A clay scientist who wants to know what the numbers mean | Slow track |
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
3. **Start #2, `how-it-works.md`**, from `notes/XRD Diffraction Calculation`
   and `notes/Refinement` in the old app. Remember its rule: prose, no code and
   **no variable or function names**. `docs/treatment-states-method.md` is a
   good model for the register, though it is a developer document and names
   files freely, which #2 must not.
4. #3, `technical-reference.md`, after that.

**Not started:** #2, #3.
