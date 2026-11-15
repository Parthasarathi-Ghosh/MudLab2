#!/usr/bin/env python
"""Put the licence of everything the Windows release bundles into its
`licenses` folder, and fail if anything bundled has no licence to put there.

The release bundles Python, Qt for Python (PySide6) with the Qt libraries,
NumPy, SciPy, Matplotlib and the libraries they use. Each licence requires its
notice to travel with a binary copy: the BSD/MIT/PSF ones ask for the notice
and licence text, and the LGPL under which Qt is used asks for the LGPL and GPL
texts and for the user to be told where the Qt source is. Until 1.1.0 only
NumPy's texts reached the package (PyInstaller happens to keep its metadata).

What is bundled is read from the BUILD, not from a list: the modules in the
executable's archive (PyInstaller's PYZ table of contents) and the folders,
extension modules and DLLs in `_internal`. Each one must be standard library,
MudLab itself, Python's or Microsoft's runtime, or belong to an installed
distribution whose licence files can be copied. Anything else stops the build,
so a new dependency cannot ship without its licence.

package.cmd runs this after the PyInstaller build, before the zip:

    python tools/collect_licenses.py --dist dist/MudLab --toc build/MudLab/PYZ-00.toc

`--out` writes somewhere other than <dist>/licenses (the tests use it).
Exit codes: 0 = written, 1 = something bundled has no licence.
"""

from __future__ import annotations

import argparse
import ast
import importlib.metadata as md
import os
import re
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
#: The GNU texts the PySide6 wheels do not include (they ship only a note for
#: commercial Qt licensees). Downloaded from gnu.org; canonical checksums.
GNU_TEXTS = {
    "LGPL-3.0.txt": os.path.join(_HERE, "licenses", "LGPL-3.0.txt"),
    "GPL-3.0.txt": os.path.join(_HERE, "licenses", "GPL-3.0.txt"),
}
#: Distributions that make up Qt for Python, reported as one component.
QT_DISTS = {"pyside6", "pyside6_essentials", "pyside6_addons", "shiboken6"}
#: Licence files of the Qt distributions that do not apply: MudLab uses Qt
#: under the LGPL, not a commercial licence.
QT_SKIP = {"LicenseRef-Qt-Commercial.txt"}
#: PyInstaller's own bootstrap modules, part of the executable.
PYINSTALLER_PREFIXES = ("pyimod", "pyi_", "_pyi_")
#: DLLs at the top of _internal, by owner.
PYTHON_DLLS = re.compile(r"^(python3\d*|libcrypto-\d+|libssl-\d+|libffi-\d+|sqlite3)\.dll$", re.I)
MSVC_DLLS = re.compile(r"^(msvcp140(_\d+)?|vcruntime140(_\d+)?|concrt140|vcomp140)\.dll$", re.I)
LICENCE_NAME = re.compile(r"(licen[cs]e|copying|notice)", re.I)


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def bundled_modules(dist_dir: str, toc_path: str) -> set[str]:
    """Top-level module names the build contains."""
    names: set[str] = set()
    with open(toc_path, encoding="utf-8") as handle:
        toc = ast.literal_eval(handle.read())

    def walk(node):
        if isinstance(node, tuple) and len(node) == 3 and node[2] == "PYMODULE":
            names.add(node[0].split(".")[0])
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)

    walk(toc)
    internal = os.path.join(dist_dir, "_internal")
    for entry in os.listdir(internal):
        full = os.path.join(internal, entry)
        if os.path.isdir(full):
            if entry.endswith((".dist-info", ".libs")):
                continue  # metadata, or a package's vendored DLLs
            names.add(entry)
        elif entry.lower().endswith(".pyd"):
            names.add(entry.split(".")[0])
    return names


def bundled_dlls(dist_dir: str) -> list[str]:
    internal = os.path.join(dist_dir, "_internal")
    return sorted(e for e in os.listdir(internal)
                  if e.lower().endswith(".dll") and os.path.isfile(os.path.join(internal, e)))


def classify(dist_dir: str, toc_path: str):
    """Return (distributions, problems): the installed distributions the build
    contains, by normalised name, and what could not be accounted for."""
    stdlib = set(sys.stdlib_module_names)
    owners = md.packages_distributions()
    dists: dict[str, md.Distribution] = {}
    problems: list[str] = []
    for name in sorted(bundled_modules(dist_dir, toc_path)):
        if name in stdlib or name == "mudlab" or name.startswith(PYINSTALLER_PREFIXES):
            continue
        found = owners.get(name)
        if not found:
            problems.append("module %r is bundled but belongs to no installed "
                            "distribution, so its licence is unknown" % name)
            continue
        for dist_name in found:
            dists[_norm(dist_name)] = md.distribution(dist_name)
    for dll in bundled_dlls(dist_dir):
        if not (PYTHON_DLLS.match(dll) or MSVC_DLLS.match(dll)):
            problems.append("DLL %r is bundled but is neither Python's nor "
                            "Microsoft's runtime" % dll)
    return dists, problems


def licence_files(dist: md.Distribution) -> list:
    """The licence files a distribution ships in its own metadata folder."""
    out = []
    for path in dist.files or []:
        parts = path.parts
        if not parts or not parts[0].endswith(".dist-info"):
            continue
        if "licenses" in parts[1:-1] or LICENCE_NAME.search(path.name):
            if path.name not in QT_SKIP:
                out.append(path)
    return out


def licence_name(dist: md.Distribution) -> str:
    meta = dist.metadata
    expression = meta.get("License-Expression")
    if expression:
        return expression
    text = (meta.get("License") or "").strip()
    if text and "\n" not in text and len(text) <= 60:
        return text
    classifiers = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or []
                   if c.startswith("License ::")]
    return "; ".join(classifiers) or "see the licence files"


def _copy(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)


def collect(dist_dir: str, toc_path: str, out_dir: str) -> list[str]:
    """Write the licences folder. Returns the problems (empty = complete)."""
    dists, problems = classify(dist_dir, toc_path)
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    rows = []  # (component, version, licence, folder)

    # Python itself. Its LICENSE.txt also covers the libraries the Windows
    # build of Python carries (OpenSSL, libffi, bzip2, xz, ...).
    py_licence = os.path.join(sys.base_prefix, "LICENSE.txt")
    py_folder = "Python-%d.%d.%d" % sys.version_info[:3]
    if os.path.isfile(py_licence):
        _copy(py_licence, os.path.join(out_dir, py_folder, "LICENSE.txt"))
        rows.append(("Python", "%d.%d.%d" % sys.version_info[:3],
                     "PSF-2.0 (and the libraries its LICENSE.txt lists)", py_folder))
    else:
        problems.append("Python's LICENSE.txt was not found at %s" % py_licence)

    # Qt for Python and Qt: one component, under the LGPL.
    qt = {k: v for k, v in dists.items() if k in QT_DISTS}
    qt_version = ""
    if qt:
        qt_version = next(iter(qt.values())).version
        qt_folder = "PySide6-Qt-%s" % qt_version
        for name, src in GNU_TEXTS.items():
            if os.path.isfile(src):
                _copy(src, os.path.join(out_dir, qt_folder, name))
            else:
                problems.append("%s is missing from tools/licenses" % name)
        rows.append(("Qt for Python and the Qt libraries (%s)"
                     % ", ".join(sorted(d.metadata["Name"] for d in qt.values())),
                     qt_version, "LGPL-3.0-only (chosen of LGPL-3.0 / GPL-2.0 / GPL-3.0)",
                     qt_folder))

    # Everything else: the licence files from each distribution's metadata.
    for key in sorted(k for k in dists if k not in QT_DISTS):
        dist = dists[key]
        name, version = dist.metadata["Name"], dist.version
        folder = "%s-%s" % (name, version)
        files = licence_files(dist)
        if not files:
            problems.append("%s %s is bundled but ships no licence file" % (name, version))
            continue
        for path in files:
            relative = os.path.join(*path.parts[1:])  # drop the .dist-info folder
            _copy(str(dist.locate_file(path)), os.path.join(out_dir, folder, relative))
        rows.append((name, version, licence_name(dist), folder))

    # Matplotlib's bundled fonts carry their own licences beside them; keep a
    # copy here too, so one folder holds every notice.
    fonts = os.path.join(dist_dir, "_internal", "matplotlib", "mpl-data", "fonts", "ttf")
    if os.path.isdir(fonts):
        for entry in sorted(os.listdir(fonts)):
            if entry.upper().startswith("LICENSE"):
                _copy(os.path.join(fonts, entry),
                      os.path.join(out_dir, "matplotlib-fonts", entry))
        rows.append(("Fonts bundled with Matplotlib (DejaVu, STIX)", "",
                     "see the licence files (also beside the fonts in "
                     "_internal\\matplotlib\\mpl-data\\fonts\\ttf)", "matplotlib-fonts"))

    _write_notices(out_dir, rows, qt_version)
    return problems


def _write_notices(out_dir: str, rows, qt_version: str) -> None:
    lines = [
        "MudLab - third-party software in this release",
        "=" * 46,
        "",
        "MudLab's own licence is LICENSE, beside MudLab.exe. This release also",
        "contains the software below, each under its own licence. Each folder here",
        "holds that component's licence texts as its authors publish them.",
        "",
    ]
    for component, version, licence, folder in rows:
        lines.append("%s %s" % (component, version) if version else component)
        lines.append("    Licence: %s" % licence)
        lines.append("    Folder:  %s" % folder)
        lines.append("")
    if qt_version:
        lines += [
            "Qt and Qt for Python",
            "--------------------",
            "MudLab uses Qt for Python (PySide6, shiboken6) and the Qt libraries,",
            "version %s, unmodified, under the GNU Lesser General Public License" % qt_version,
            "version 3 (LGPL-3.0.txt; it builds on the GNU GPL version 3, GPL-3.0.txt).",
            "They are the separate files in _internal\\PySide6 and _internal\\shiboken6,",
            "and you may replace them with other compatible versions of those libraries.",
            "Their source code is available from The Qt Company:",
            "  Qt:             https://download.qt.io/official_releases/qt/",
            "  Qt for Python:  https://code.qt.io/cgit/pyside/pyside-setup.git/",
            "Qt itself contains third-party components under their own licences, listed",
            "at https://doc.qt.io/qt-6/licenses-used-in-qt.html",
            "",
        ]
    lines += [
        "Microsoft Visual C++ runtime",
        "----------------------------",
        "MSVCP140*.dll, VCRUNTIME140*.dll and CONCRT140.dll in _internal are the",
        "Microsoft Visual C++ runtime, redistributed under the Microsoft Visual Studio",
        "redistribution terms.",
        "",
        "Crystal structures",
        "------------------",
        "The files in the Structures folder are published data with their own terms;",
        "see Structures\\README.md and Structures\\CREDITS.md.",
        "",
    ]
    with open(os.path.join(out_dir, "THIRD-PARTY-NOTICES.txt"), "w",
              encoding="utf-8", newline="\r\n") as handle:
        handle.write("\n".join(lines))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dist", required=True, help="the built MudLab folder")
    parser.add_argument("--toc", required=True, help="PyInstaller's PYZ-00.toc")
    parser.add_argument("--out", help="where to write (default: <dist>/licenses)")
    args = parser.parse_args(argv)
    out_dir = args.out or os.path.join(args.dist, "licenses")
    problems = collect(args.dist, args.toc, out_dir)
    if problems:
        print("Third-party licences INCOMPLETE:")
        for problem in problems:
            print("  - %s" % problem)
        return 1
    count = sum(len(files) for _root, _dirs, files in os.walk(out_dir))
    print("Third-party licences: %d files in %s" % (count, out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
