#!/usr/bin/env python
"""Release metadata: one version, a licence that ships, and no fixtures.

The version now appears in THREE places - `src/mudlab/__init__.py`
(the source of truth), `pyproject.toml`, and the Windows version resource in
`version_info.txt`. Nothing makes them agree on its own, and the one that drifts
silently is the resource: a wrong number there shows in the .exe's File
Properties and in corporate software inventories, where nobody would notice for
a long time.

Also pinned:

* **LICENSE exists and ships.** MudLab descends from PyXRD / MudLab (BSD
  3-Clause, (c) 2013 Mathijs Dumon). Clause 2 REQUIRES that notice to be
  reproduced in a BINARY distribution, so `package.cmd` must copy it into the
  package - not merely leave it in the repo.
* **No sample projects in the bundle.** `tools/sample_projects/*.mud` are the
  user's own data, test-only, and must never reach a release.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_release_metadata.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab import APP_NAME, __version__  # noqa: E402

results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _read(name):
    with open(os.path.join(_REPO, name), encoding="utf-8") as handle:
        return handle.read()


def main():
    # ----------------------------------------------------------- one version
    check("version: __version__ is a plain x.y.z (%s)" % __version__,
          bool(re.fullmatch(r"\d+\.\d+\.\d+", __version__)))

    pyproject = _read("pyproject.toml")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    check("version: pyproject.toml agrees",
          match is not None and match.group(1) == __version__)

    resource = _read("version_info.txt")
    check("version: the Windows resource FileVersion agrees",
          'StringStruct("FileVersion", "%s")' % __version__ in resource)
    check("version: ...and ProductVersion",
          'StringStruct("ProductVersion", "%s")' % __version__ in resource)
    # filevers/prodvers are 4-tuples: 1.0.0 -> (1, 0, 0, 0).
    parts = __version__.split(".")
    tuple_text = "(%s, %s, %s, 0)" % tuple(parts)
    check("version: filevers matches (%s)" % tuple_text,
          "filevers=%s" % tuple_text in resource)
    check("version: prodvers matches",
          "prodvers=%s" % tuple_text in resource)
    check("version: the resource names the product %r" % APP_NAME,
          'StringStruct("ProductName", "%s")' % APP_NAME in resource)

    # -------------------------------------------------------------- licence
    licence = _read("LICENSE")
    check("licence: LICENSE is present", bool(licence.strip()))
    check("licence: it is the BSD 3-Clause text",
          "BSD 3-Clause License" in licence
          and "Redistributions in binary form" in licence)
    check("licence: the UPSTREAM copyright is retained (clause 2 requires it)",
          "Mathijs Dumon" in licence)
    check("licence: the resource carries a copyright line",
          "LegalCopyright" in resource and "BSD" in resource)

    package = _read("package.cmd")
    check("licence: package.cmd copies LICENSE into the bundle",
          'copy /Y "LICENSE"' in package)
    check("package: it bundles a README for users",
          "README-PORTABLE.md" in package)
    check("package: the tester-only readme is gone",
          not os.path.exists(os.path.join(_REPO, "README-TESTERS.md")))

    # ------------------------------------------------- no fixtures in a build
    spec = _read("MudLab.spec")
    check("spec: datas does not name sample_projects",
          "sample_projects" not in spec.split("datas=")[1].split("]")[0])
    check("spec: the .exe carries the version resource",
          'version="version_info.txt"' in spec)
    check("spec: the .exe carries the app icon", "mudlab.ico" in spec)

    # If a build is present, check the REAL thing rather than the recipe.
    built = os.path.join(_REPO, "dist", "MudLab")
    if os.path.isdir(built):
        # A .mud is ALWAYS wrong in a build - those are projects, i.e. the
        # user's own data. A .cmp / .phs is only wrong OUTSIDE mudlab/data:
        # the shipped default-component catalog lives there and is MEANT to be
        # bundled (27 .cmp files as of 1.0.0). The first version of this check
        # forbade all three everywhere and cried wolf on the whole catalog.
        app_data = os.path.join("mudlab", "data")
        projects, stray_parts = [], []
        for root, _dirs, files in os.walk(built):
            inside_app_data = app_data in root
            for name in files:
                lower = name.lower()
                if lower.endswith(".mud"):
                    projects.append(os.path.join(root, name))
                elif lower.endswith((".cmp", ".phs")) and not inside_app_data:
                    stray_parts.append(os.path.join(root, name))
        check("build: no .mud projects in the bundle (%d found)"
              % len(projects), not projects)
        check("build: no loose components outside mudlab/data (%d found)"
              % len(stray_parts), not stray_parts)
        catalog = os.path.join(built, "_internal", "mudlab", "data",
                               "default components")
        check("build: the default-component catalog IS bundled",
              os.path.isdir(catalog) and any(
                  f.lower().endswith(".cmp")
                  for _r, _d, fs in os.walk(catalog) for f in fs))
        check("build: the launcher is there",
              os.path.isfile(os.path.join(built, "MudLab.exe")))
    else:
        check("build: (no dist\\MudLab yet; skipped)", True)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Release metadata: %s %s" % (APP_NAME, __version__))
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
