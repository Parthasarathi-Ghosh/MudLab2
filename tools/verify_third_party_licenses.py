#!/usr/bin/env python
"""Guard tools/collect_licenses.py, which writes the release's licenses folder.

Before 1.1.0 the Windows release bundled Python, Qt/PySide6 (LGPL), SciPy,
Matplotlib and a dozen smaller libraries, and shipped the licence texts of
NumPy alone. The collector now reads what a build bundles and copies each
component's licence, failing the build when something bundled cannot be
accounted for. This harness checks that it does both:

1. On a synthetic build (so it runs anywhere, CI included): every bundled
   third-party distribution gets a non-empty folder and a line in
   THIRD-PARTY-NOTICES.txt; Python's licence is copied; Qt gets the canonical
   LGPL-3.0 and GPL-3.0 texts, the source links and the statement that its
   DLLs may be replaced; the note for commercial Qt licensees is left out;
   standard library, MudLab, PyInstaller's bootstrap and the Python and MSVC
   runtime DLLs need no folder.
2. It FAILS on what it cannot account for: a bundled module of no installed
   distribution, an unknown DLL, a missing GNU text.
3. Where a real build exists (build/ and dist/ from package.cmd), the real
   bundle is fully accounted for.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_third_party_licenses.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import sys
import tempfile

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "collect_licenses", os.path.join(_REPO, "tools", "collect_licenses.py"))
cl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cl)

#: The canonical texts as gnu.org publishes them.
CANONICAL = {
    "LGPL-3.0.txt": "e3a994d82e644b03a792a930f574002658412f62407f5fee083f2555c5f23118",
    "GPL-3.0.txt": "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986",
}

results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def synthetic_build(root, modules, extra_files=()):
    """A minimal dist/MudLab plus PYZ table of contents."""
    dist = os.path.join(root, "dist", "MudLab")
    internal = os.path.join(dist, "_internal")
    for folder in ("PySide6", "shiboken6", "numpy", "numpy.libs", "scipy",
                   "scipy.libs", "PIL", "mudlab", "numpy-2.5.0.dist-info",
                   os.path.join("matplotlib", "mpl-data", "fonts", "ttf")):
        os.makedirs(os.path.join(internal, folder), exist_ok=True)
    for name in ("python314.dll", "python3.dll", "VCRUNTIME140.dll",
                 "MSVCP140_1.dll", "libssl-3.dll", "_ssl.pyd",
                 "base_library.zip") + tuple(extra_files):
        open(os.path.join(internal, name), "wb").close()
    ttf = os.path.join(internal, "matplotlib", "mpl-data", "fonts", "ttf")
    for name in ("LICENSE_DEJAVU", "LICENSE_STIX"):
        with open(os.path.join(ttf, name), "w", encoding="utf-8") as handle:
            handle.write("font licence\n")
    toc = os.path.join(root, "PYZ-00.toc")
    entries = [(m, "x.py", "PYMODULE") for m in modules]
    with open(toc, "w", encoding="utf-8") as handle:
        handle.write(repr(("PYZ-00.pyz", entries)))
    return dist, toc


BASE_MODULES = ["json", "mudlab.models", "pyimod02_importers", "pyparsing",
                "six", "dateutil.parser", "PIL.Image", "matplotlib.pyplot"]


def check_synthetic():
    tmp = tempfile.mkdtemp()
    try:
        dist, toc = synthetic_build(tmp, BASE_MODULES)
        out = os.path.join(tmp, "licenses")
        problems = cl.collect(dist, toc, out)
        check("synthetic build: collected with nothing unaccounted for%s"
              % ("" if not problems else " -> %s" % problems), not problems)
        notices = open(os.path.join(out, "THIRD-PARTY-NOTICES.txt"),
                       encoding="utf-8").read()
        folders = sorted(e for e in os.listdir(out) if os.path.isdir(os.path.join(out, e)))
        empty = [f for f in folders if not any(files for _r, _d, files in os.walk(os.path.join(out, f)))]
        check("every component folder holds at least one licence file%s"
              % ("" if not empty else " -> empty: %s" % empty), not empty)
        check("every folder is named in THIRD-PARTY-NOTICES.txt",
              all("Folder:  %s" % f in notices for f in folders))
        wanted = ["Python", "Qt for Python", "numpy", "scipy", "matplotlib",
                  "pillow", "pyparsing", "six", "python-dateutil"]
        missing = [w for w in wanted if w.lower() not in notices.lower()]
        check("the notices name every bundled component (%s)%s"
              % (", ".join(wanted), "" if not missing else " -> missing %s" % missing),
              not missing)
        stdlib_named = [w for w in ("json", "mudlab", "pyimod") if "\n%s " % w in notices]
        check("standard library, MudLab and PyInstaller's bootstrap get no entry",
              not stdlib_named)
        py = [f for f in folders if f.startswith("Python-")]
        py_text = (open(os.path.join(out, py[0], "LICENSE.txt"), encoding="utf-8",
                        errors="replace").read() if py else "")
        check("Python's LICENSE.txt is copied (PSF licence)",
              "PYTHON SOFTWARE FOUNDATION LICENSE" in py_text)
        qt = [f for f in folders if f.startswith("PySide6-Qt-")]
        qt_dir = os.path.join(out, qt[0]) if qt else ""
        for name, digest in CANONICAL.items():
            path = os.path.join(qt_dir, name)
            check("Qt gets the canonical %s" % name,
                  os.path.isfile(path) and _sha(path) == digest)
        check("the note for commercial Qt licensees is left out",
              not any("Commercial" in f for _r, _d, fs in os.walk(out) for f in fs))
        check("the notices give Qt's source and say its DLLs may be replaced",
              "download.qt.io" in notices and "pyside-setup" in notices
              and "replace them" in notices)
        check("the notices cover the MSVC runtime and the crystal structures",
              "Visual C++ runtime" in notices and "Structures" in notices)
        fonts = os.path.join(out, "matplotlib-fonts")
        check("Matplotlib's font licences are gathered too",
              os.path.isfile(os.path.join(fonts, "LICENSE_DEJAVU"))
              and os.path.isfile(os.path.join(fonts, "LICENSE_STIX")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_failures():
    tmp = tempfile.mkdtemp()
    try:
        dist, toc = synthetic_build(tmp, BASE_MODULES + ["notarealpackage.core"])
        problems = cl.collect(dist, toc, os.path.join(tmp, "out1"))
        check("FAILS on a bundled module of no installed distribution",
              any("notarealpackage" in p for p in problems))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    tmp = tempfile.mkdtemp()
    try:
        dist, toc = synthetic_build(tmp, BASE_MODULES, extra_files=("mystery.dll",))
        problems = cl.collect(dist, toc, os.path.join(tmp, "out2"))
        check("FAILS on an unknown DLL", any("mystery.dll" in p for p in problems))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    tmp = tempfile.mkdtemp()
    saved = dict(cl.GNU_TEXTS)
    try:
        cl.GNU_TEXTS["LGPL-3.0.txt"] = os.path.join(tmp, "absent.txt")
        dist, toc = synthetic_build(tmp, BASE_MODULES)
        problems = cl.collect(dist, toc, os.path.join(tmp, "out3"))
        check("FAILS when a GNU text is missing", any("LGPL-3.0.txt" in p for p in problems))
    finally:
        cl.GNU_TEXTS.clear()
        cl.GNU_TEXTS.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)


def check_real_build():
    toc = os.path.join(_REPO, "build", "MudLab", "PYZ-00.toc")
    dist = os.path.join(_REPO, "dist", "MudLab")
    if not (os.path.isfile(toc) and os.path.isdir(os.path.join(dist, "_internal"))):
        check("real build: none on this machine; skipped", True)
        return
    tmp = tempfile.mkdtemp()
    try:
        problems = cl.collect(dist, toc, os.path.join(tmp, "licenses"))
        check("real build: everything bundled is accounted for%s"
              % ("" if not problems else " -> %s" % problems[:3]), not problems)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_repo():
    for name, digest in CANONICAL.items():
        path = os.path.join(_REPO, "tools", "licenses", name)
        check("tools/licenses/%s is the canonical gnu.org text" % name,
              os.path.isfile(path) and _sha(path) == digest)
    portable = open(os.path.join(_REPO, "README-PORTABLE.md"), encoding="utf-8").read()
    check("the bundled README points at the licenses folder",
          "THIRD-PARTY-NOTICES.txt" in portable and "LGPL" in portable)


def main() -> int:
    print("=" * 72)
    print("Third-party licences in the release (tools/collect_licenses.py)")
    print("=" * 72)
    check_synthetic()
    check_failures()
    check_real_build()
    check_repo()
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    passed = sum(ok for _, ok in results)
    print("%d/%d checks passed" % (passed, len(results)))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
