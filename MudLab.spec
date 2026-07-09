# -*- coding: utf-8 -*-
# PyInstaller spec for MudLab. Build with build.cmd; output lands in dist\MudLab\.
# Targets 64-bit Windows 10 and later (the platform this environment runs on).

a = Analysis(
    ["src/mudlab/__main__.py"],
    pathex=["src"],
    binaries=[],
    # Keep `datas` free of tools/sample_projects/*.mud. Those are test-only
    # fixtures that must never ship in a release (see .gitattributes
    # export-ignore). No app code imports them, so an empty list already
    # excludes them - do not add them here.
    datas=[],
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
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="MudLab",
)
