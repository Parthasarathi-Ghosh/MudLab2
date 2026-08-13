# Retracting the non-clay decomposition feature

The non-clay feature is **experimental** and built to be removed cleanly. It is
**read-only over the clay path** (it never edits a mixture/specimen/phase or the
`calculations/` code) and touches mainstream in exactly **one** place.

## What it consists of
- `src/mudlab/nonclay/` — the whole feature: the engine (`estimator.py`,
  `detection.py`, `decompose.py`, `references.py`) and the UI (`dialog.py` +
  `nonclay.ui` + `ui_nonclay.py`), all in one deletable package.
- `tools/verify_nonclay.py` — the harness (engine + dialog + the isolation
  invariant).
- `tools/nonclay_experiments/` — throwaway reproducibility scripts and the
  from-CIF calculator (`structure_pattern.py`).
- `docs/non-clay-analysis-notes.md` — the design / evidence notes (Findings
  1–33); `docs/nonclay-algorithm.md` — the paper-ready methods write-up.

## The one mainstream seam — grep token `NONCLAY`
- `src/mudlab/ui/edit_mixture.ui` — the `btn_nonclay` button ("Non-clay…", next
  to Composition).
- `src/mudlab/edit_mixture_widget.py` — two `# >>> NONCLAY … # <<< NONCLAY`
  blocks: the **defensive wiring** (hides the button if the package is absent)
  and the `_on_nonclay` handler.

## To disable (fastest, non-destructive)
Delete `src/mudlab/nonclay/`. The app still runs — the defensive wiring catches
the `ImportError` and hides the Non-clay button. Nothing else breaks.

## To fully retract
1. Delete `src/mudlab/nonclay/`, `tools/verify_nonclay.py`,
   `tools/nonclay_experiments/`, `docs/non-clay-analysis-notes.md`, and this
   file.
2. In `src/mudlab/ui/edit_mixture.ui`, remove the `<widget … name="btn_nonclay">`
   `<item>`, then recompile:
   `./python/Scripts/pyside6-uic.exe src/mudlab/ui/edit_mixture.ui -o src/mudlab/ui/ui_edit_mixture.py`
3. In `src/mudlab/edit_mixture_widget.py`, delete the two `NONCLAY`-fenced blocks.
4. Verify no residue:
   - `grep -rn NONCLAY src/mudlab` → empty
   - `grep -rn "mudlab.nonclay" src/mudlab` → empty

Because the clay optimize / refine / calc path is never modified, removing the
feature cannot affect clay results.
