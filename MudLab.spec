# -*- coding: utf-8 -*-
# PyInstaller spec for MudLab. Build with build.cmd; output lands in dist\MudLab\.
# Targets 64-bit Windows 10 and later (the platform this environment runs on).

a = Analysis(
    ["src/mudlab/__main__.py"],
    pathex=["src"],
    binaries=[],
    # Bundle the app's runtime data files (kept under src/mudlab/data), e.g. the
    # composition-conversion table read by calculations/composition.py. The .ui
    # files do NOT need bundling - they are compiled to ui_*.py modules.
    #
    # Keep `datas` free of tools/sample_projects/*.mud. Those are test-only
    # fixtures that must never ship in a release (see .gitattributes
    # export-ignore); no app code imports them.
    datas=[("src/mudlab/data", "mudlab/data")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="MudLab",
    console=False,
    # Force UTF-8 mode (PEP 540) inside the frozen app, matching the dev launchers.
    options=[("X utf8", None, "OPTION")],
    icon="src/mudlab/data/icons/mudlab.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="MudLab",
)
