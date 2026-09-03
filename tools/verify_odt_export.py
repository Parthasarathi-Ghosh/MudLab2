#!/usr/bin/env python
"""Exporting a documentation page as an Open Document Text file.

Qt can write ODF and MudLab used to use it, but it emits every heading as an
ordinary paragraph wearing a heading-like style. The file looks right and has
no structure: a word processor's navigator shows nothing and an automatic table
of contents comes out empty. For a reference document whose whole shape is its
headings, that is most of the value gone - so the ODT is written here instead,
from the Markdown source, with no dependency beyond the standard library.

Three format details are easy to get wrong and fatal when you do, and all three
are pinned below: the `mimetype` entry must be FIRST in the archive and STORED
uncompressed; a heading must be a heading ELEMENT carrying an outline level
rather than a paragraph in a heading style; and no hyperlink may name a target
without a scheme.

That last one cost a shipped release of the feature. A scheme-less
`xlink:href` is a reference to a part INSIDE the ODT package, so a link like
"user-manual.md" names a part that does not exist and Word refuses the whole
document - "Word found unreadable content", then "the file appears to be
corrupted". Every one of the four shipped pages links to a sibling that way, so
every one of them failed. Well-formed XML and a valid ZIP say nothing about
this, which is why the check below is on the href values themselves.

The finding came from driving Word over COM against a bisection of the source.
That is not repeatable in CI, so what is asserted here is the mechanical rule
Word was enforcing, and the shipped documents are held to it too.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_odt_export.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import zipfile
from xml.dom import minidom

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from mudlab.file_parsers.odt_export import (  # noqa: E402
    heading_slug, markdown_to_content, write_odt,
)

#: Every hyperlink target in an exported document, as written.
HREF = re.compile(r'xlink:href="([^"]*)"')
#: A target a reader resolves for itself: it has a scheme, or it points within
#: this same document. Anything else is a reference into the ODT package.
RESOLVABLE = re.compile(r"^(#|//|[A-Za-z][A-Za-z0-9+.\-]*:)")

results: list[tuple[str, bool]] = []
SCRATCH = tempfile.mkdtemp(prefix="odt-")

SAMPLE = """# Title

An opening paragraph with **bold**, *italic*, `code` and a
[link](https://example.invalid/page).

## A section

Some prose that wraps
across two source lines.

- first bullet
- second bullet

1. first step
2. second step

> A quoted caution.

| Mineral | Spacing |
|---|---|
| kaolinite | 0.716 nm |
| illite | 0.998 nm |

---

### A deeper heading

Closing text.
"""


def check(label, ok):
    results.append((label, bool(ok)))


def main():  # noqa: C901 - a checklist
    # ------------------------------------------------------ the container
    path = write_odt(SAMPLE, os.path.join(SCRATCH, "sample.odt"))
    check("an ODT is produced", os.path.isfile(path) and os.path.getsize(path) > 0)
    check("...and it is a ZIP package", zipfile.is_zipfile(path))

    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [e.filename for e in entries]
        first = entries[0]
        content = archive.read("content.xml").decode("utf-8")
        styles = archive.read("styles.xml").decode("utf-8")
        manifest = archive.read("META-INF/manifest.xml").decode("utf-8")
        mimetype = archive.read("mimetype").decode("utf-8")

    # A reader identifies the format from this entry before inflating
    # anything, so it must come first and must not be compressed.
    check("the mimetype entry comes FIRST (%s)" % first.filename,
          first.filename == "mimetype")
    check("...and is STORED, not compressed",
          first.compress_type == zipfile.ZIP_STORED)
    check("...and names Open Document Text",
          mimetype == "application/vnd.oasis.opendocument.text")
    check("the package carries content, styles and a manifest%s" % names,
          {"content.xml", "styles.xml", "META-INF/manifest.xml"} <= set(names))

    for part, text in (("content", content), ("styles", styles),
                       ("manifest", manifest)):
        try:
            minidom.parseString(text.encode("utf-8"))
            ok = True
        except Exception:  # noqa: BLE001
            ok = False
        check("%s.xml is well-formed XML" % part, ok)

    # ------------------------------------------------- the structure itself
    #
    # This is the whole reason the module exists. Qt's writer produces ZERO of
    # these for the same input.
    headings = re.findall(r'<text:h [^>]*text:outline-level="(\d)"', content)
    check("headings are heading ELEMENTS with outline levels (%d found)"
          % len(headings), len(headings) == 3)
    check("...at the levels the source used %s" % sorted(set(headings)),
          sorted(set(headings)) == ["1", "2", "3"])
    check("...and no heading was demoted to a plain paragraph",
          "Heading_20_1" in content and content.count("<text:h ") == 3)
    check("the heading styles are declared so a reader recognises them",
          all('style:name="Heading_20_%d"' % n in styles for n in (1, 2, 3)))
    check("...with a default outline level, which is what builds a contents "
          "list", 'style:default-outline-level="1"' in styles)

    check("bullet and numbered lists become real lists (%d lists, %d items)"
          % (content.count("<text:list "), content.count("<text:list-item>")),
          content.count("<text:list ") == 2
          and content.count("<text:list-item>") == 4)
    # A list carries no bullet or number itself - the style supplies them - so
    # without a style a numbered list renders as bullets and the distinction
    # is silently lost.
    check("...and each names a list style, so numbering survives",
          'text:style-name="L_Bullet"' in content
          and 'text:style-name="L_Number"' in content)
    check("...with those styles actually defined",
          'style:name="L_Bullet"' in styles
          and "text:list-level-style-number" in styles)

    # ODF nests a list INSIDE its parent's item. Emitting siblings instead
    # keeps every word and loses the shape, which is the failure this whole
    # module exists to avoid.
    nested = markdown_to_content("- top\n  - inner\n    - deeper\n- next\n")
    check("a nested list is nested, not flattened (%d lists)"
          % nested.count("<text:list "), nested.count("<text:list ") == 3)
    check("...inside its parent's item, as the format requires",
          "</text:p><text:list " in nested)
    check("...and every tag is balanced",
          nested.count("<text:list ") == nested.count("</text:list>")
          and nested.count("<text:list-item>") == nested.count("</text:list-item>"))
    try:
        minidom.parseString(nested.encode("utf-8"))
        nested_ok = True
    except Exception:  # noqa: BLE001
        nested_ok = False
    check("...leaving well-formed XML", nested_ok)

    check("the table becomes a real table",
          content.count("<table:table ") == 1
          and content.count("<table:table-row>") == 3)
    check("...with its header row styled apart",
          "Table_20_Heading" in content)
    check("...and its cells carrying the data",
          "kaolinite" in content and "0.998 nm" in content)

    check("a block quote gets the quotation style", "Quotations" in content)
    check("a horizontal rule survives", "Horizontal_20_Line" in content)

    # ------------------------------------------------------------- inline
    check("bold becomes a styled span", '<text:span text:style-name="Bold">' in content)
    check("italic becomes a styled span",
          '<text:span text:style-name="Italic">' in content)
    check("inline code becomes a styled span",
          '<text:span text:style-name="Code">' in content)
    check("a link becomes a real hyperlink",
          '<text:a ' in content and "example.invalid/page" in content)

    check("a wrapped paragraph is joined, not broken in two",
          "Some prose that wraps across two source lines." in content)

    # ------------------------------------------------- hyperlink targets
    #
    # THE failure that made every exported document unreadable in Word. A
    # scheme-less target names a part inside the package; the package has no
    # such part, and the reader rejects the document rather than the link.
    linked = markdown_to_content(
        "# A heading\n\n"
        "Sibling [the manual](user-manual.md), dotted [x](./x.md), "
        "parent [y](../y.md), deep [z](sub/z.md#frag), "
        "anchor [back](#a-heading), web [w](https://example.invalid/p), "
        "mail [m](mailto:a@example.invalid).\n"
    )
    targets = HREF.findall(linked)
    check("no exported link names a target inside the package %s" % targets,
          all(RESOLVABLE.match(t) for t in targets))
    check("...so the four relative forms are not linked at all",
          not any(t.endswith(".md") or "/" in t.rstrip("/")
                  for t in targets if not t.startswith("http")))
    check("...while the web and mail targets are kept",
          "https://example.invalid/p" in targets
          and "mailto:a@example.invalid" in targets)
    check("...and the fragment, which points within this same document",
          "#a-heading" in targets)
    # Dropping the link must not drop what it said.
    for label in ("the manual", "parent", "deep", "dotted"):
        check("...a dropped link keeps its text (%r)" % label, label in linked)

    # ------------------------------------------------------ bookmarks
    #
    # A fragment is only useful if something answers to it. These are what the
    # document's own Contents list lands on.
    marks = re.findall(r'<text:bookmark text:name="([^"]*)"/>', linked)
    check("a heading carries a bookmark named by its slug %s" % marks,
          marks == ["a-heading"])
    check("...by the same rule the viewer scrolls by",
          heading_slug("A heading") == "a-heading")
    repeated = re.findall(
        r'<text:bookmark text:name="([^"]*)"/>',
        markdown_to_content("# Same\n\ntext\n\n# Same\n\nmore\n"))
    check("...and a repeated heading is not bookmarked twice %s" % repeated,
          repeated == ["same"])

    # ----------------------------------------------------- fenced code
    fenced = markdown_to_content(
        "Before.\n\n```\nfirst    line\n  indented\n- not a bullet\n```\n\nAfter.\n")
    check("a fenced block becomes preformatted paragraphs (%d)"
          % fenced.count("Preformatted_20_Text"),
          fenced.count("Preformatted_20_Text") == 3)
    check("...with nothing inside it read as markup",
          "<text:list " not in fenced and "- not a bullet" in fenced)
    # ODF collapses runs of spaces exactly as HTML does, so an ASCII diagram
    # loses its shape without these.
    check("...and its indentation preserved as text:s",
          '<text:s text:c="3"/>' in fenced and '<text:s text:c="2"/>' in fenced)
    check("...and the fence markers themselves do not appear",
          "```" not in fenced)
    check("...while the surrounding text is untouched",
          "Before." in fenced and "After." in fenced)

    # ------------------------------------------------------ table names
    two = markdown_to_content(
        "| A |\n|---|\n| 1 |\n\ntext\n\n| A |\n|---|\n| 1 |\n")
    names = re.findall(r'table:name="([^"]*)"', two)
    check("two identical tables still get distinct names %s" % names,
          len(names) == 2 and len(set(names)) == 2)
    check("...deterministically, so two exports of a page agree",
          re.findall(r'table:name="([^"]*)"', markdown_to_content(
              "| A |\n|---|\n| 1 |\n\ntext\n\n| A |\n|---|\n| 1 |\n")) == names)

    # -------------------------------------------------------- XML safety
    risky = write_odt("# A & B < C\n\nText with <angle> & ampersand.\n",
                      os.path.join(SCRATCH, "escapes.odt"))
    with zipfile.ZipFile(risky) as archive:
        escaped = archive.read("content.xml").decode("utf-8")
    try:
        minidom.parseString(escaped.encode("utf-8"))
        well_formed = True
    except Exception:  # noqa: BLE001
        well_formed = False
    check("characters that would break XML are escaped", well_formed
          and "&amp;" in escaped and "&lt;angle&gt;" in escaped)

    check("an empty document still produces a valid package",
          zipfile.is_zipfile(write_odt("", os.path.join(SCRATCH, "empty.odt"))))

    # ------------------------------------------- the real shipped documents
    from mudlab.manual_dialog import docs_dir

    docs = docs_dir()
    for name in ("how-it-works.md", "user-manual.md", "getting-started.md"):
        source = os.path.join(docs, name)
        if not os.path.isfile(source):
            check("shipped: %s absent; skipped" % name, True)
            continue
        with open(source, encoding="utf-8") as handle:
            text = handle.read()
        target = write_odt(text, os.path.join(SCRATCH, name + ".odt"))
        with zipfile.ZipFile(target) as archive:
            body = archive.read("content.xml").decode("utf-8")
        expected = len(re.findall(r"^#{1,6} ", text, re.M))
        found = body.count("<text:h ")
        try:
            minidom.parseString(body.encode("utf-8"))
            ok = True
        except Exception:  # noqa: BLE001
            ok = False
        check("shipped: %s exports every heading (%d of %d) as valid XML"
              % (name, found, expected), ok and found == expected)

        # This is the one that was failing in the field. Each of these pages
        # links to a sibling page, and every such link made the whole file
        # unreadable in Word.
        stray = [t for t in HREF.findall(body) if not RESOLVABLE.match(t)]
        check("shipped: %s names no target inside the package%s"
              % (name, (" " + str(stray)) if stray else ""), not stray)
        # A Contents entry pointing at a heading that no longer exists is a
        # dead link in the ODT and in the viewer alike.
        anchors = {t[1:] for t in HREF.findall(body) if t.startswith("#")}
        bookmarks = set(re.findall(r'<text:bookmark text:name="([^"]*)"/>', body))
        missing = sorted(anchors - bookmarks)
        check("shipped: %s resolves all %d of its own anchors%s"
              % (name, len(anchors), (" missing " + str(missing)) if missing else ""),
              not missing)

    # A page that is only a contents list would be a sign the body was lost.
    check("the exported science document is substantial (%d bytes)"
          % os.path.getsize(os.path.join(SCRATCH, "how-it-works.md.odt")),
          os.path.getsize(os.path.join(SCRATCH, "how-it-works.md.odt")) > 10000)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("ODT export")
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
