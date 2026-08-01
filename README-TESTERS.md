# MudLab — tester build (pre-release)

Thank you for helping test **MudLab**. This is a **pre-release** build shared for
feedback **before** the public release — please don't redistribute it.

You can confirm the exact build from **Help → About** inside the app (it shows the
version, e.g. `0.2.0-rc1`); please quote that version in any feedback.

## Running it (no installation)

1. **Unzip** the folder anywhere you like (Desktop, Documents, a USB stick…).
2. Open the extracted **`MudLab`** folder and double-click **`MudLab.exe`**.
3. That's it — no installer, no admin rights, nothing written to the registry.

> **Keep the folder together.** `MudLab.exe` needs the `_internal` folder next to
> it. Move or copy the **whole `MudLab` folder**, not just the `.exe`.

### First-launch warnings (expected for a pre-release)

- **Windows SmartScreen** — you may see *"Windows protected your PC / unknown
  publisher."* This is because the build isn't code-signed yet. Click
  **More info → Run anyway**.
- **Antivirus** — a packaged Python app is occasionally flagged as a false
  positive. If your AV quarantines it, restore/allow it (or add an exclusion for
  the folder).

Neither warning means anything is wrong — they're just what Windows shows for a
new, unsigned executable.

## Checking the build is intact (optional)

From a terminal (PowerShell or Command Prompt) in the extracted folder:

```
MudLab.exe --selftest > selftest.txt
type selftest.txt
```

It should end with `SELFTEST PASS` — that confirms the bundled data (mineral and
scattering tables, the default clay-phase library, icons) all loaded.

## What to try

- Open your own projects and measured patterns (`.mud`, PyXRD `.pyxrd`, and text
  `.xy` / `.csv` / `.dat`, plus Bruker/Rigaku raw formats).
- Add phases (including the built-in default clay phases), assign them to
  mixtures, and **Refine** — watch the live convergence plot.
- Detect peaks, match minerals, edit the goniometer, export compositions.
- Anything that feels slow, wrong, confusing, or crashes.

> **Sample projects are not included** — please test with your own data.

## Reporting feedback

Please include:

- the **version** (Help → About),
- **what you did** (steps to reproduce),
- **what you expected vs. what happened**, and a screenshot if it helps.

Send it to: _<add your channel here — e.g. a private issue tracker or email>_.

Your data stays on your machine — MudLab does not send anything anywhere.
