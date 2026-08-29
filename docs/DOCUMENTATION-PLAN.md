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
| 1 | **Walkthrough** — the essential path through the UI, start to finish | `docs/getting-started.md` | A new user with a scan and no idea where to click | **Draft in progress** |
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
  the 82 `tools/verify_*.py` docstrings, which are the closest thing we have to
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

**2026-08-29** — Track created. Deliverable #1 drafted end to end
(`docs/getting-started.md`): the full path from importing a scan to saving
results, with every menu path and button label verified against the running UI.

Next actions, in order:

1. **Review pass on #1 by the user.** It is a first draft; the shape is there,
   the wording will want tightening.
2. **Wire `Help → Manual` (F1).** It is currently a **dead action** — the
   `QAction` exists in `ui_main_window.py` with an F1 shortcut and no handler in
   any source file. It should open #1. Small change; worth doing before the next
   release, since "the manual is missing" is the release blocker.
3. **Screenshots for #1** — deliberately none yet. They date fast and the UI is
   still moving. Revisit once #1's text is settled.
4. Then start #2 from `notes/XRD Diffraction Calculation` + `notes/Refinement`.

**Not started:** #2, #3.
