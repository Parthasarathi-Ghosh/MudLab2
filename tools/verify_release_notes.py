#!/usr/bin/env python
"""Release notes: assembled by the build, not written after it.

v1.0.3 published with a title of just the tag and a bare commit changelog,
because the workflow relied on `generate_release_notes` alone. It had to be
retitled and rewritten by hand minutes later. That is the failure this pins.

The arrangement now: `.github/release-notes-template.md` carries everything
that is the same every time, and `docs/release-notes/<version>.md` carries what
is new. The second is the only part a human writes.

The load-bearing check here is the last one: **the version currently in the tree
must already have its highlights file**. It fails as soon as the version is
bumped and stays failing until the notes are written - which is deliberate,
because the alternative is discovering it after the tag is public and the build
has already run. If this is the only thing failing, the fix is to write
`docs/release-notes/<version>.md`.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_release_notes.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))
sys.path.insert(0, os.path.join(_REPO, "tools"))

from mudlab import __version__  # noqa: E402

from build_release_notes import (  # noqa: E402
    HIGHLIGHTS_DIR, TEMPLATE, build, highlights_path,
)

results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def main():  # noqa: C901 - a checklist
    # ------------------------------------------------------- the template
    check("the template exists", os.path.isfile(TEMPLATE))
    with open(TEMPLATE, encoding="utf-8") as handle:
        template = handle.read()
    check("...with a place for the version", "{{VERSION}}" in template)
    check("...and a place for the highlights", "{{HIGHLIGHTS}}" in template)
    check("...and it still tells users how to survive the antivirus",
          "quarantine" in template.lower() and "false positive" in template)
    check("...and points them at the in-app manual", "**F1**" in template)

    # ---------------------------------------------------- assembling them
    body = build("1.2.3")
    check("assembling substitutes the version",
          "MudLab 1.2.3" in body and "{{" not in body)
    check("...into the asset name the build actually produces",
          "MudLab-1.2.3-win64-portable.zip" in body)
    check("...and the download URL for that tag",
          "releases/download/v1.2.3/MudLab-1.2.3-win64-portable.zip" in body)
    check("a version with no highlights still yields usable notes",
          "Release highlights were not written" in body and len(body) > 1500)

    try:
        build("not-a-version")
        rejected = False
    except ValueError:
        rejected = True
    check("a malformed version is refused", rejected)

    try:
        build("1.2.3", strict=True)
        strict_failed = False
    except FileNotFoundError:
        strict_failed = True
    check("--strict refuses a version with no highlights file", strict_failed)

    # ------------------------------------------------------- the workflow
    workflow = os.path.join(_REPO, ".github", "workflows", "build-portable.yml")
    with open(workflow, encoding="utf-8") as handle:
        yaml = handle.read()
    check("the workflow assembles the notes",
          "tools/build_release_notes.py" in yaml)
    check("...and publishes them as the body", "body_path: RELEASE_NOTES.md" in yaml)
    check("...and names the release rather than leaving it as the tag",
          re.search(r"name:\s*MudLab \$\{\{\s*steps\.pkg\.outputs\.version", yaml)
          is not None)
    check("...passing the version the package step derived",
          "--version ${{ steps.pkg.outputs.version }}" in yaml)

    # -------------------------------------------- the highlights on file
    stored = sorted(f for f in os.listdir(HIGHLIGHTS_DIR) if f.endswith(".md"))
    check("release highlights are kept in the repo (%d on file)" % len(stored),
          bool(stored))
    misnamed = [f for f in stored if not re.fullmatch(r"\d+\.\d+\.\d+\.md", f)]
    check("...each named for its version%s"
          % ("" if not misnamed else " -> %s" % misnamed), not misnamed)
    mismatched = []
    for name in stored:
        version = name[:-3]
        with open(os.path.join(HIGHLIGHTS_DIR, name), encoding="utf-8") as handle:
            first = handle.read().lstrip().splitlines()[0]
        if first.strip() != "## New in %s" % version:
            mismatched.append("%s -> %r" % (name, first))
    check("...and opening with its own heading%s"
          % ("" if not mismatched else " -> %s" % mismatched), not mismatched)

    # The one that blocks a release until the notes are written.
    this_version = os.path.relpath(highlights_path(__version__), _REPO)
    check("THIS version (%s) has its highlights written -> %s"
          % (__version__, this_version),
          os.path.isfile(highlights_path(__version__)))
    if os.path.isfile(highlights_path(__version__)):
        final = build(__version__, strict=True)
        check("...and the notes for it assemble cleanly (%d bytes)"
              % len(final.encode("utf-8")),
              "MudLab %s" % __version__ in final and "{{" not in final)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Release notes")
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
