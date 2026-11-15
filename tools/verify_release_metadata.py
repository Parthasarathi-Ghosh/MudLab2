#!/usr/bin/env python
"""Release metadata: one version, a licence that ships, and no fixtures.

The version now appears in THREE places - `src/mudlab/__init__.py`
(the source of truth), `pyproject.toml`, and the Windows version resource in
`version_info.txt`. Nothing makes them agree on its own, and the one that drifts
silently is the resource: a wrong number there shows in the .exe's File
Properties and in corporate software inventories, where nobody would notice for
a long time.

Also pinned:

* **LICENSE exists and ships.** MudLab is BSD 3-Clause and descends from
  PyXRD, which is BSD 2-Clause, (c) 2013-2014 Mathijs Dumon. Both licences
  REQUIRE their notice in a BINARY distribution, so `package.cmd` must copy it
  into the package - not merely leave it in the repo. Until 1.1.0 LICENSE put
  Dumon's copyright (as "2013") under MudLab's BSD 3-Clause, terms he never
  used; PyXRD's own notice is now reproduced as PyXRD publishes it. LICENSE
  also states that the crystal structures are third-party data it does not
  cover, and points at the third-party licences folder.
* **The third-party licences ship.** `package.cmd` runs
  `tools/collect_licenses.py` before the zip (verify_third_party_licenses.py
  tests the collector itself).
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
    check("licence: PyXRD's own notice is reproduced as published "
          "(BSD 2-Clause, (c) 2013-2014)",
          "Copyright (c) 2013-2014, Mathijs Dumon" in licence
          and 'All rights reserved - BSD-2-Clause ("FreeBSD") License.' in licence)
    mudlab_part = licence.split("\n====")[0]
    check("licence: Dumon's copyright is not listed under MudLab's BSD 3-Clause",
          "Dumon" not in mudlab_part and "Parthasarathi Ghosh" in mudlab_part)
    check("licence: the crystal structures are excluded (third-party data)",
          "Crystal structures" in licence and "not part of MudLab" in licence
          and "AMCSD" in licence and "public domain" in licence)
    check("licence: it points at the third-party licences folder",
          "licenses" in licence and "THIRD-PARTY-NOTICES" in licence
          and "LGPL" in licence)
    check("licence: the resource carries a copyright line",
          "LegalCopyright" in resource and "BSD" in resource)
    check("licence: ...naming PyXRD's licence correctly",
          "2013-2014 Mathijs Dumon (BSD 2-Clause)" in resource)

    package = _read("package.cmd")
    check("licence: package.cmd copies LICENSE into the bundle",
          'copy /Y "LICENSE"' in package)
    collect_at = package.find("tools\\collect_licenses.py")
    check("licence: package.cmd collects the third-party licences before the zip",
          0 <= collect_at < package.find("Compress-Archive"))
    check("package: it bundles a README for users",
          "README-PORTABLE.md" in package)
    # The bundled README shipped inside 1.0.1 still saying "MudLab 1.0.0".
    # A version hardcoded in a file that goes into every release goes stale
    # silently, so it must not name one at all.
    portable = _read("README-PORTABLE.md")
    stale = re.findall(r"\d+\.\d+\.\d+", portable)
    check("package: the bundled README names no version (it would go stale)"
          + ("" if not stale else " -> found %s" % stale), not stale)
    check("package: the tester-only readme is gone",
          not os.path.exists(os.path.join(_REPO, "README-TESTERS.md")))

    # ------------------------------------------------- no fixtures in a build
    spec = _read("MudLab.spec")
    check("spec: datas does not name sample_projects",
          "sample_projects" not in spec.split("datas=")[1].split("]")[0])
    check("spec: the .exe carries the version resource",
          'version="version_info.txt"' in spec)
    check("spec: the .exe carries the app icon", "mudlab.ico" in spec)
    # The CI runner's OpenSSL (found on its PATH by PyInstaller's QtNetwork
    # hook) and the UCRT shipped in every CI release until 1.1.0, unlicensed;
    # collect_licenses.py refused them. The spec must keep dropping them.
    check("spec: drops the OpenSSL and UCRT DLLs the build machine supplies",
          "def _from_the_build_machine" in spec
          and "a.binaries = [entry for entry in a.binaries" in spec
          and "-x64" in spec and "api-ms-win-" in spec)

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
