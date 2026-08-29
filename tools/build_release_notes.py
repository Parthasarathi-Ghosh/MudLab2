#!/usr/bin/env python
"""Assemble the GitHub release notes for a tagged build.

The workflow used to publish with `generate_release_notes` alone, which gives a
bare commit changelog and a title of just the tag - so every release had to be
retitled and rewritten by hand afterwards, and 1.0.3 shipped that way for the
few minutes before someone noticed.

Two pieces instead:

  * `.github/release-notes-template.md` - the parts that are the same every
    time (download and unzip, the manual, the antivirus rescue, requirements,
    licence), with `{{VERSION}}` and `{{HIGHLIGHTS}}` to fill in.
  * `docs/release-notes/<version>.md` - what is NEW in this release, written
    while the work is fresh and committed BEFORE the tag is pushed. This is the
    only part a human writes, and writing it is the point: the boilerplate can
    be generated, the highlights cannot.

If the highlights file is missing the notes are still complete and correct -
they simply carry a visible placeholder saying the highlights were not written,
which is far better than a silently empty release. `--strict` turns that into
an error instead, which is how the verification harness insists that a version
about to be tagged has its highlights ready.

Usage:

    python tools/build_release_notes.py --version 1.0.3 --out NOTES.md
"""

from __future__ import annotations

import argparse
import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(_REPO, ".github", "release-notes-template.md")
HIGHLIGHTS_DIR = os.path.join(_REPO, "docs", "release-notes")

_MISSING = """## New in {version}

_Release highlights were not written for this version. See the commit log
below for what changed._"""


def highlights_path(version: str) -> str:
    return os.path.join(HIGHLIGHTS_DIR, "%s.md" % version)


def build(version: str, strict: bool = False) -> str:
    """The full release-notes body for `version`."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("version must be x.y.z, not %r" % version)

    with open(TEMPLATE, encoding="utf-8") as handle:
        template = handle.read()

    path = highlights_path(version)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            highlights = handle.read().strip()
    elif strict:
        raise FileNotFoundError(
            "no release highlights for %s - write %s before tagging"
            % (version, os.path.relpath(path, _REPO))
        )
    else:
        highlights = _MISSING.format(version=version)

    body = template.replace("{{HIGHLIGHTS}}", highlights)
    body = body.replace("{{VERSION}}", version)

    leftover = re.findall(r"\{\{[^}]*\}\}", body)
    if leftover:
        raise ValueError("unsubstituted placeholders remain: %s" % leftover)
    return body


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="x.y.z")
    parser.add_argument("--out", help="write here instead of stdout")
    parser.add_argument("--strict", action="store_true",
                        help="fail when the highlights file is missing")
    args = parser.parse_args(argv)

    try:
        body = build(args.version, strict=args.strict)
    except (ValueError, FileNotFoundError, OSError) as error:
        print("release notes: %s" % error, file=sys.stderr)
        return 1

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        written = os.path.isfile(highlights_path(args.version))
        print("release notes for %s -> %s (%d bytes, highlights: %s)"
              % (args.version, args.out, len(body.encode("utf-8")),
                 "yes" if written else "MISSING - placeholder used"))
    else:
        sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
