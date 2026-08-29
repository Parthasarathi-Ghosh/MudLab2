# MudLab

**Version 1.0.3** - X-ray diffraction analysis of disordered layered minerals.

Windows desktop application built with PySide6 (Qt 6), NumPy, SciPy, and
Matplotlib. Working folder is `MudLab2` while the legacy MudLab is still
installed; the product name is **MudLab**.

## Releases

Tagging `v*` (or running the **Build portable Windows package** workflow by
hand) builds the release on a clean Windows runner and attaches the zip.
Locally, `package.cmd` builds the same package: a clean PyInstaller build,
a frozen self-test, then `MudLab-<version>-win64-portable.zip` - a no-install
folder that users unzip and run. Keep the version in step across
`src/mudlab/__init__.py` (the source of truth), `pyproject.toml` and
`version_info.txt`; `tools/verify_release_metadata.py` checks that they agree
and that no project fixtures reached the build.
`tools/verify_bundle_dependencies.py` - run by `package.cmd` as step 3/6 -
fails the build if any bundled binary needs a library that is not inside the
package; that is what keeps "portable" true on a machine with no Microsoft
runtime installed. `tools/run_all.py` runs the whole verification suite.

Licensed BSD 3-Clause - see `LICENSE`. MudLab descends from PyXRD / MudLab by
Mathijs Dumon, whose copyright notice travels with every binary release.

## Self-contained environment

Everything needed to develop and run the app lives inside this folder.
There is no dependency on any Python installation, registry entry, or
site-packages outside of it.

| Component | Version | Where |
|---|---|---|
| Python (official portable build) | 3.14.6 | `python\` |
| PySide6 | 6.11.1 | `python\Lib\site-packages` |
| NumPy | 2.5.0 | `python\Lib\site-packages` |
| SciPy | 1.18.0 | `python\Lib\site-packages` |
| Matplotlib | 3.11.0 | `python\Lib\site-packages` |
| PyInstaller (build tool) | 6.21.0 | `python\Lib\site-packages` |

The runtime is the official CPython release published by the CPython team on
nuget.org (a full distribution that runs from a folder - no installer, no
registry). `scripts\setup_env.ps1` recreates `python\` from scratch on any
machine, so `python\` itself does not need to be committed (it is
git-ignored).

## Layout

```
MudLab2\
  python\           bundled CPython runtime + all libraries (git-ignored)
  src\mudlab\       application source code
  src\mudlab\ui\    Qt Designer .ui files + compiled ui_*.py (see its README)
  scripts\          environment setup script
  run.cmd           run the app with the bundled Python
  python.cmd        run the bundled Python directly (scripts, pip, REPL)
  designer.cmd      open the bundled Qt Designer (command line)
  Launch PySide6 Designer.bat   double-click to open Qt Designer
  build_ui.cmd      recompile all .ui files to ui_*.py
  build.cmd         build the Windows executable with PyInstaller
  MudLab.spec       PyInstaller build configuration
  requirements.txt  pinned direct dependencies
```

## Everyday commands

```bat
run.cmd                      Start the app
python.cmd -m pip list       Use the bundled Python / pip
designer.cmd path\to\x.ui    Edit a GUI design in Qt Designer
build_ui.cmd                 Recompile .ui designs after editing
build.cmd                    Build dist\MudLab\MudLab.exe
```

## GUI design workflow

Every GUI component has a `.ui` file in `src\mudlab\ui\` that can be
opened and modified in Qt Designer (bundled - `designer.cmd`). The `.ui`
files are the source of truth for layout/design; `build_ui.cmd` compiles
them to `ui_*.py`, and the Python classes in `src\mudlab\` contain logic
only. Details and rules: `src\mudlab\ui\README.md`.

## Building the executable

`build.cmd` produces `dist\MudLab\MudLab.exe` - a windowed (no console)
64-bit application with Python and all libraries bundled inside. The build
is 64-bit Windows only; Qt 6.11 officially supports Windows 10 (21H2 or
later) and Windows 11, so the executable targets Windows 10+ by
construction.

## UTF-8 policy

Only UTF-8 text encoding is permitted anywhere in this project.

- All source and config files are UTF-8 (`.editorconfig` and
  `.vscode\settings.json` enforce this in editors).
- Every launcher (`run.cmd`, `python.cmd`, `build.cmd`) runs Python with
  `-X utf8` plus `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8`, so the
  interpreter is always in UTF-8 mode (PEP 540): file I/O, stdio, and pipes
  default to UTF-8 regardless of the Windows locale/ANSI code page.
- The frozen executable enables the same UTF-8 mode via `MudLab.spec`.
- In code, never pass a non-UTF-8 `encoding=` argument; plain
  `open(path)` is fine because UTF-8 mode makes UTF-8 the default.

## Renaming: retiring the legacy MudLab

Shipping this app as "MudLab" while the old MudLab is still installed is
possible; nothing here conflicts with it:

- During development this project is only files in this folder. The built
  `MudLab.exe` lives in `dist\` and can coexist with the installed legacy
  app indefinitely - executable names only clash if two files share one
  directory.
- Points of contact to watch at release time: the install directory, Start
  Menu shortcut names, file-type associations, and per-user settings/data
  locations. Keep them different from the legacy app's while both are
  installed (e.g. install to a new directory), or simply retire the old app
  first: uninstall it, then this app takes over the name cleanly.
- If the legacy app stores per-user settings under a "MudLab" key or
  folder and you want a clean break, change `ORG_NAME` in
  `src\mudlab\__init__.py` before first release, or plan a one-time
  settings migration.
