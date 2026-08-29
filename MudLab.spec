# -*- coding: utf-8 -*-
# PyInstaller spec for MudLab. Build with build.cmd; output lands in dist\MudLab\.
# Targets 64-bit Windows 10 and later (the platform this environment runs on).

import glob
import os
import sys


def _msvc_runtime():
    """The MSVC runtime DLLs, to be placed at the ROOT of the bundle.

    WHY THIS EXISTS (1.0.1). PyInstaller treats the Visual C++ runtime as a
    SYSTEM library and does not place it at the bundle root; it only arrives
    incidentally, inside packages that ship their own copies (PySide6,
    shiboken6, numpy.libs). That is enough on any machine with the Visual C++
    Redistributable installed - which every development machine has - and NOT
    enough on a clean one.

    In 1.0.0 that produced a package that started here and died on a user's
    machine: `_internal/` held VCRUNTIME140(_1).dll but no MSVCP140.dll, so the
    eight bundled Qt plugin DLLs that need it - including
    `platforms/qwindows.dll`, without which Qt cannot open a window at all -
    resolved it only from the system's own System32 copy.

    A build calling itself PORTABLE must not depend on something the user has
    to install. These are redistributable by design; PySide6 ships its own
    copies, which is where they are taken from (falling back to System32).

    tools/verify_bundle_dependencies.py fails the build if any bundled binary
    still needs a DLL that cannot be resolved from inside the package.
    """
    wanted = ("MSVCP140.dll", "MSVCP140_1.dll", "MSVCP140_2.dll",
              "VCRUNTIME140.dll", "VCRUNTIME140_1.dll", "CONCRT140.dll")
    roots = [os.path.join(os.path.dirname(sys.executable), "Lib",
                          "site-packages", "PySide6"),
             os.path.join(os.path.dirname(sys.executable), "Lib",
                          "site-packages", "shiboken6"),
             os.path.join(os.environ.get("SystemRoot", "C:" + os.sep + "Windows"),
                          "System32")]
    found, seen = [], set()
    for name in wanted:
        for root in roots:
            candidate = os.path.join(root, name)
            if os.path.isfile(candidate) and name.lower() not in seen:
                seen.add(name.lower())
                # "." puts it at the bundle root, beside python314.dll.
                found.append((candidate, "."))
                break
    return found


a = Analysis(
    ["src/mudlab/__main__.py"],
    pathex=["src"],
    # The MSVC runtime, forced to the bundle root - see _msvc_runtime().
    binaries=_msvc_runtime(),
    # Bundle the app's runtime data files (kept under src/mudlab/data), e.g. the
    # composition-conversion table read by calculations/composition.py. The .ui
    # files do NOT need bundling - they are compiled to ui_*.py modules.
    #
    # Keep `datas` free of tools/sample_projects/*.mud. Those are test-only
    # fixtures that must never ship in a release (see .gitattributes
    # export-ignore); no app code imports them.
    # `docs` carries the in-app manual (Help -> Manual, F1). manual_dialog
    # looks beside the package first, which is where this mapping puts it, so
    # the frozen build never reaches outside itself for documentation.
    datas=[
        ("src/mudlab/data", "mudlab/data"),
        ("docs", "mudlab/docs"),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

# UPX is OFF, explicitly. PyInstaller compresses with UPX whenever upx.exe
# happens to be on PATH, which makes the artifact depend on what is installed
# on the build machine - and UPX-packed binaries are among the strongest
# triggers for antivirus false positives, which this project has already been
# bitten by (Quick Heal quarantined matplotlib's ft2font .pyd as Trojan.Agent
# on a user's machine, 2026-08-26). Neither this machine nor the CI runner has
# UPX today; saying so here means a build never silently changes if one does.
_UPX = False

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    upx=_UPX,
    name="MudLab",
    console=False,
    # Force UTF-8 mode (PEP 540) inside the frozen app, matching the dev launchers.
    options=[("X utf8", None, "OPTION")],
    icon="src/mudlab/data/icons/mudlab.ico",
    # File Properties -> Details. Without it the .exe reports no version,
    # product name or copyright at all, which for an UNSIGNED public release is
    # both unhelpful to users and one more thing for SmartScreen to dislike.
    version="version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    upx=_UPX,
    name="MudLab",
)
