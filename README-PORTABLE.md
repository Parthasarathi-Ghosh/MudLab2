# MudLab 1.0.0 — portable build for Windows

X-ray diffraction analysis of disordered layered minerals.

This is the **portable** build: there is no installer, nothing is written to the
registry, and it needs no administrator rights.

## Running it

1. **Unzip** the folder anywhere you like — Desktop, Documents, a USB stick.
2. Open the extracted **`MudLab`** folder and double-click **`MudLab.exe`**.

> **Keep the folder together.** `MudLab.exe` needs the `_internal` folder beside
> it. Move or copy the **whole `MudLab` folder**, never just the `.exe`.

The version is shown on the start-up splash and under **Help → About**. Quote it
in any bug report.

## First launch

- **Windows SmartScreen** may say *"Windows protected your PC / unknown
  publisher"*. This build is not code-signed. Choose **More info → Run anyway**.
- **Antivirus**: a packaged Python application is occasionally flagged as a
  false positive. If yours quarantines it, restore it or add an exclusion for
  the folder.

Neither warning means anything is wrong with the file; both are what Windows
says about any unsigned application from a small publisher.

## What it does

- Opens and saves MudLab `.mud` projects, and opens PyXRD `.pyxrd` projects.
- Imports measured patterns from `.xrdml`, `.rasx`, Bruker `.raw`, `.uxd`,
  Rigaku `.raw`, `.xy` and CSV.
- Builds clay phases from the shipped default catalog or from your own
  components, mixes them, and refines the fit against your specimens.
- Detects peaks, matches minerals, and reports the modelled composition —
  optionally against a measured XRF analysis.
- **Project → Export** writes a `.mud` the original GTK MudLab can open, or a
  `.pyxrd`. Both are lossy in ways the app tells you about at export time.

The full manual is `docs/user-manual.md` in the source repository.

## Requirements

64-bit Windows 10 or later. Nothing else — Python, Qt, NumPy, SciPy and
Matplotlib are all inside the folder.

## Licence

BSD 3-Clause. See `LICENSE`, which is included in this folder. MudLab descends
from PyXRD / MudLab by Mathijs Dumon; that copyright notice travels with this
release, as the licence requires.
