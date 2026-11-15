# Plan: shipping the curated structure collection

Planned 2026-11-15. Two phases:

1. **Next release:** ship the collection as a visible `Structures` folder beside
   `MudLab.exe`, and make the CIF file dialogs open there.
2. **The release after:** a Structure Library dialog for browsing the collection
   and adding a structure as a phase.

**Status:** phase 1 is built (2026-11-15) and awaits a release; phase 2 is not
started. The open work is also listed in [remaining-work.md](remaining-work.md).

## What ships

The 65 published structures chosen for clay XRD (curation proposal v1, approved
2026-11-15). Each CIF is the published file, copied byte for byte; only the file
name is new (`<Mineral>__COD-n.cif` / `<Mineral>__AMCSD-n.cif`). About 450 KB in
total.

```
Structures/
  README.md       what the folder is, how to use it in MudLab, terms of use
  CREDITS.md      the citation for every structure, grouped by mineral family
  manifest.csv    one row per file: group, mineral, kind, formula, citation
                  fields, COD/AMCSD id, conditions note, sha256
  Clays/          18 layer silicates   -> Import CIF... (a component)
  Non-clays/      47 other minerals    -> Import Non-Clay, Calibrate FWHM
```

**Clays** are the 18 structures flagged as layered during curation: kaolinite,
dickite, nacrite, lizardite-1T, chamosite, talc, pyrophyllite, illite-1M,
illite-2M1, muscovite-2M1, paragonite-2M1, phlogopite, annite, montmorillonite,
nontronite, hectorite, vermiculite, clinochlore. **Non-clays** are the other 47,
including sepiolite and palygorskite: their ribbon structures do not project into
a layer stack. The split only says which dialog the file suits. Every file reads
in both readers, so a clay can also be added as a fixed non-clay pattern.

**Not included** (stated in README.md so users are not left guessing):
beidellite, saponite and halloysite have no usable published refinement, and
MudLab's model components cover them; glauconite is left out for now, because
every COD entry is the idealised Drits 2010 model.

**Terms.** COD structures are public domain. AMCSD structures may be used *"so
long as proper attribution is given to the journal article"*. Hence CREDITS.md
travels with the files, and README.md asks users to cite the article whenever
they use a structure. The repository licence covers the code. README.md states
that the data carry their own terms.

## Phase 1 — visible folder, dialogs open there

### 1. Into the repository

- Add `structures/` at the repository root. Do not put it in `src/mudlab/data`:
  everything there is bundled into the build's internal folder, so the files
  would be hidden from users and, with step 2, shipped twice.
- The repository copy becomes the master. The maintainer's CIF workspace keeps
  the provenance: source downloads, proposal and selection spec.
- `manifest.csv` keeps the user-facing columns and drops the development ones
  (reader results, projection notes). It gains `kind` (clay / non-clay),
  `formula` (from the CIF's `_chemical_formula_sum`) and `sha256`.
- Derive README.md and CREDITS.md from the workspace MANIFEST.md. Remove its
  references to workspace files and its curation-status wording.
- **Line endings.** `.gitattributes` has `* text=auto`, and the published files
  mix CRLF (27) and LF (38). Without a rule, git would rewrite them and the
  checksums would stop matching the published files. `structures/**/*.cif -text`
  goes in before the files are added.
- After the copy is verified, the workspace's `curated/` folder is removed, so
  there is one master copy.

### 2. Packaging

- `package.cmd`: add a step **right after the PyInstaller build and before the
  frozen self-test** that copies `structures` to `dist\MudLab\Structures`. CI
  builds through `package.cmd`, so CI picks it up with no workflow change. The
  spec's `datas` cannot do this: PyInstaller 6 places data under the internal
  folder, not beside the exe.
- `--selftest` gains a probe: the folder exists beside the exe, README.md and
  CREDITS.md are present, the CIF count equals the manifest rows, and one file
  from each subfolder reads. A build that lost the folder then fails at step 2
  instead of reaching a user.
- `README-PORTABLE.md` lists the folder.

### 3. Locating the folder

New module `mudlab/structure_collection.py`, following `manual_dialog.docs_dir`:

- `collection_dir()`: in a frozen build, `Structures` beside the executable; in a
  source checkout, the repository's `structures`; `None` when absent. It checks
  the frozen location first, so a build never reaches outside itself.
- `clays_dir()` / `nonclays_dir()` return the subfolders, or `None`.

### 4. File dialogs open in the collection

| Dialog | Opens in |
|---|---|
| Component editor → **Import CIF…** | `Clays` |
| Edit Phases → **Import Non-Clay** → Open | `Non-clays` |
| **Calibrate FWHM** → load CIF | `Non-clays` |
| The experimental non-clay dialog's CIF reference | `Non-clays` |

- The first open in a session starts in the collection. After that, each kind
  of dialog starts in the folder the user last picked from, so users with their
  own CIFs are not sent back to the collection every time. The app saves no
  settings between runs (there is no QSettings anywhere), so each new session
  starts in the collection again.
- If the folder is missing, the dialog behaves as it does today: no start folder.

### 5. Help → Structure Collection…

- A new action in `main_window.ui`, between *How MudLab Works* and *About*.
  Recompile `ui_main_window.py` (LF endings).
- It opens the folder in Explorer (`QDesktopServices.openUrl`). The tooltip
  names CREDITS.md and asks users to cite the article. If the folder is missing,
  it says so.
- Optional: one line in About, "Includes 65 published crystal structures from
  COD and AMCSD; see Structures\CREDITS.md."

### 6. Tests

New `tools/verify_structure_collection.py`:

1. Manifest ⇔ files: every CIF has a row, every row has a file, and there are no
   extras.
2. Every file's sha256 matches the manifest, so the shipped bytes are still the
   published bytes and the citations still hold.
3. Every row has authors, year, journal and a COD or AMCSD id, and CREDITS.md
   names every file.
4. Every clay imports through the clay reader with no skipped site, and every
   non-clay gives reflections at Cu Kα through the non-clay reader.
5. `collection_dir()` resolves in the source layout, and returns the
   exe-adjacent path when a frozen run is simulated.
6. Each dialog in step 4 passes the right start folder on first use and the
   last-picked folder afterwards (`QFileDialog.getOpenFileName` stubbed).
7. The Help action exists and opens the folder (`openUrl` stubbed).
8. `package.cmd` copies the folder before the self-test runs.
9. Added after phase 1 was built: every clay MudLab has its own component for
   (11 of the 18) imports, with the layer count its hint gives, to that
   component's basal spacing within 0.01 nm and a correlating 00l pattern
   (r ≥ 0.85). Reading a file says nothing about its cell. The first talc
   shipped (Drits et al. 2012, AMCSD 0020723) read perfectly but had a
   pyrophyllite-size cell, so it was replaced by Perdikatsis & Burzlaff 1981
   (AMCSD 0010839).

Also:

- `verify_cif_labels.py`: point the curated real-file checks at the in-repo
  folder. This removes the last local-path default for curated files, and those
  checks then run on CI too.
- `verify_selftest.py`: expect the new probe.

### 7. Documentation

- `user-manual.md`: a new section on the Structures folder (where it is, which
  dialog suits which file, citing, and the two-layer polytypes the importer does
  not fold — nacrite, muscovite-2M1, paragonite-2M1 — which the review dialog
  corrects).
- `getting-started.md`: one line pointing at it.
- `cif-import-and-treatment-method.md`: note the shipped collection.
- `remaining-work.md` and `src/mudlab/ui/TODO.md`: update the status.
- The release notes for the version that ships it.

### 8. Release

- The version number is decided at release time; a new feature suggests a
  minor-version bump.
- Before any push, run the usual sample-project check. `structures/` holds no
  `.mud` file, and the harness confirms it holds only CIFs and the three text
  files.

## Phase 2 — Structure Library dialog

A browser for the collection, opened from Edit Phases (a **Structure Library…**
button beside *Import Non-Clay*). Help → Structure Collection… can then open it
too, with an *Open folder* button inside for the Explorer route.

**Layout:** a search box and a group filter above a table (Mineral, Group, Kind,
Formula, Year, Source id). Below it, a details pane showing the full citation,
DOI link, conditions note and any import hint.

**Actions:**

- **Add as non-clay phase** (any structure): opens Import Non-Clay with the file
  already loaded (`ImportNonClayDialog` gains a `path=` argument), so the user
  still checks the name and peak width. On accept, it adds the phase exactly as
  Edit Phases does today.
- **New clay phase** (clays only): creates a one-component R0 phase named after
  the mineral, runs the existing CIF review dialog on the file, and on accept
  installs the component and adds the phase. This fills today's gap: a CIF can
  only replace a component of a phase that already exists. The apply step now
  in `component_widget._on_import_cif` (atom types added to the project, the
  component installed) moves into a shared function used by both places.
- **Copy citation**, **Open folder**.

**Hints:** the manifest flags the two-layer polytypes, and the details pane says
before the review opens that the layer count must be corrected there.

**Files:** `ui/structure_library.ui` + compiled `ui_structure_library.py`,
`structure_library_dialog.py`, `tools/verify_structure_library.py`, a manual
section, and a `src/mudlab/ui/TODO.md` entry. Known Qt traps that apply: clear
autoDefault after the buttons are reparented, and decide WA_DeleteOnClose
deliberately (see dev-notes).

**Tests:** all 65 rows load; search and filter narrow the rows; each action
creates the right phase type with the file's citation-named component; Cancel in
the review adds nothing; Copy citation puts the full citation on the clipboard;
a missing folder disables the dialog with a message instead of crashing.

**Open for phase 2:** whether the library should also replace the *selected*
component when it is opened from a component editor, or leave that to
Import CIF….
