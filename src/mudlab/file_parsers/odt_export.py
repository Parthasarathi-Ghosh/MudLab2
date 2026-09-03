"""Write a Markdown document as an Open Document Text file.

Qt can already export ODF, and for a quick save it is fine — but it writes
every heading as an ordinary paragraph carrying a large bold style. The result
*looks* right and has no structure: a word processor's navigator shows nothing,
and "insert table of contents" produces an empty one. For a reference document
whose whole shape is its headings, that is most of the value gone.

This writes the structure instead: real heading elements carrying outline
levels, real lists, real tables. The file then behaves like a document someone
authored — navigable, and able to generate its own contents.

No dependency is needed. An ODT is a ZIP of XML parts, and the parts this needs
are small. Two details of the format are easy to get wrong and fatal when you
do:

* the ``mimetype`` entry must come **first** in the archive and be **stored
  uncompressed**. It is how a reader identifies the format before unpacking
  anything, and an ODT that compresses it is rejected by strict readers.
* a heading must be a ``text:h`` element with an outline level. A paragraph
  wearing a heading's style is not a heading, which is exactly the trap Qt's
  own writer falls into.

The Markdown understood here is the subset the shipped documentation actually
uses — headings, paragraphs, bullet and numbered lists, tables, block quotes,
horizontal rules, bold, italic, inline code and links. Anything else degrades
to plain text rather than failing.
"""

from __future__ import annotations

import re
import zipfile

_MIME = "application/vnd.oasis.opendocument.text"

_MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:media-type="%s"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
""" % _MIME

_NS = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
    'xmlns:xlink="http://www.w3.org/1999/xlink"'
)

#: Heading styles, and the body styles the converter uses. Named in ODF's
#: encoded form ("Heading_20_1" is "Heading 1"), which is what a word processor
#: recognises as its own built-in styles rather than as something foreign.
_STYLES = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles %s office:version="1.2">
 <office:styles>
  <style:style style:name="Standard" style:family="paragraph" style:class="text"/>
  <style:style style:name="Heading" style:family="paragraph"
      style:parent-style-name="Standard" style:class="text">
   <style:paragraph-properties fo:margin-top="0.35cm" fo:margin-bottom="0.18cm"
       fo:keep-with-next="always"/>
   <style:text-properties style:font-name="Segoe UI" fo:font-weight="bold"/>
  </style:style>
%s
  <style:style style:name="Quotations" style:family="paragraph"
      style:parent-style-name="Standard">
   <style:paragraph-properties fo:margin-left="1cm" fo:margin-right="1cm"
       fo:margin-top="0.2cm" fo:margin-bottom="0.2cm"/>
   <style:text-properties fo:font-style="italic"/>
  </style:style>
  <style:style style:name="Table_20_Contents" style:display-name="Table Contents"
      style:family="paragraph" style:parent-style-name="Standard"/>
  <style:style style:name="Table_20_Heading" style:display-name="Table Heading"
      style:family="paragraph" style:parent-style-name="Table_20_Contents">
   <style:text-properties fo:font-weight="bold"/>
  </style:style>
  <style:style style:name="Bold" style:family="text">
   <style:text-properties fo:font-weight="bold"/>
  </style:style>
  <style:style style:name="Italic" style:family="text">
   <style:text-properties fo:font-style="italic"/>
  </style:style>
  <style:style style:name="Code" style:family="text">
   <style:text-properties style:font-name="Consolas"/>
  </style:style>
  <style:style style:name="Horizontal_20_Line" style:display-name="Horizontal Line"
      style:family="paragraph" style:parent-style-name="Standard">
   <style:paragraph-properties fo:margin-top="0.2cm" fo:margin-bottom="0.2cm"
       fo:border-bottom="0.06pt solid #808080"/>
  </style:style>
  <text:list-style style:name="L_Bullet">
%s
  </text:list-style>
  <text:list-style style:name="L_Number">
%s
  </text:list-style>
 </office:styles>
</office:document-styles>
""" % (
    _NS,
    "\n".join(
        '  <style:style style:name="Heading_20_%d" style:display-name="Heading %d"\n'
        '      style:family="paragraph" style:parent-style-name="Heading"\n'
        '      style:default-outline-level="%d">\n'
        '   <style:text-properties fo:font-size="%dpt"/>\n'
        '  </style:style>' % (n, n, n, size)
        for n, size in ((1, 20), (2, 16), (3, 13), (4, 12), (5, 11), (6, 11))
    ),
    # A list carries no bullet or number of its own: the LIST STYLE supplies
    # them, per level. Without one, a reader falls back to its default and a
    # numbered list comes out bulleted - the ordered/unordered distinction, and
    # the indent that shows nesting, both vanish.
    "\n".join(
        '   <text:list-level-style-bullet text:level="%d" text:bullet-char="%s">\n'
        '    <style:list-level-properties text:space-before="%.1fcm"'
        ' text:min-label-width="0.5cm"/>\n'
        "   </text:list-level-style-bullet>" % (level, char, 0.4 * level)
        for level, char in ((1, "•"), (2, "◦"), (3, "▪"),
                            (4, "•"), (5, "◦"))
    ),
    "\n".join(
        '   <text:list-level-style-number text:level="%d" style:num-format="1"'
        ' style:num-suffix=".">\n'
        '    <style:list-level-properties text:space-before="%.1fcm"'
        ' text:min-label-width="0.6cm"/>\n'
        "   </text:list-level-style-number>" % (level, 0.4 * level)
        for level in (1, 2, 3, 4, 5)
    ),
)

_ESCAPES = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"))


def _escape(text: str) -> str:
    for old, new in _ESCAPES:
        text = text.replace(old, new)
    return text


_INLINE = re.compile(
    r"\*\*(?P<bold>.+?)\*\*"
    r"|(?<!\*)\*(?P<italic>[^*]+)\*(?!\*)"
    r"|`(?P<code>[^`]+)`"
    r"|\[(?P<label>[^\]]+)\]\((?P<href>[^)]+)\)"
)


def _inline(text: str) -> str:
    """Markdown emphasis, code and links as ODF text spans."""
    out = []
    position = 0
    for match in _INLINE.finditer(text):
        out.append(_escape(text[position:match.start()]))
        if match.group("bold") is not None:
            out.append('<text:span text:style-name="Bold">%s</text:span>'
                       % _inline(match.group("bold")))
        elif match.group("italic") is not None:
            out.append('<text:span text:style-name="Italic">%s</text:span>'
                       % _inline(match.group("italic")))
        elif match.group("code") is not None:
            out.append('<text:span text:style-name="Code">%s</text:span>'
                       % _escape(match.group("code")))
        else:
            href = match.group("href").strip()
            out.append('<text:a xlink:type="simple" xlink:href="%s">%s</text:a>'
                       % (_escape(href), _inline(match.group("label"))))
        position = match.end()
    out.append(_escape(text[position:]))
    return "".join(out)


def _paragraph(text: str, style: str = "Standard") -> str:
    return '<text:p text:style-name="%s">%s</text:p>' % (style, _inline(text))


def _heading(text: str, level: int) -> str:
    """A REAL heading: the element, with its outline level.

    This is the whole point of the module. A paragraph in a heading style looks
    identical and is invisible to a navigator or an automatic contents list.
    """
    return ('<text:h text:style-name="Heading_20_%d" text:outline-level="%d">'
            '%s</text:h>' % (level, level, _inline(text)))


def _table(rows: list) -> str:
    """An ODF table from Markdown pipe rows; the first row is the header."""
    if not rows:
        return ""
    columns = max(len(r) for r in rows)
    out = ['<table:table table:name="Table%d">' % (abs(hash(str(rows))) % 9999)]
    out.append('<table:table-column table:number-columns-repeated="%d"/>' % columns)
    for index, row in enumerate(rows):
        style = "Table_20_Heading" if index == 0 else "Table_20_Contents"
        out.append("<table:table-row>")
        for column in range(columns):
            cell = row[column] if column < len(row) else ""
            out.append('<table:table-cell office:value-type="string">%s'
                       "</table:table-cell>" % _paragraph(cell, style))
        out.append("</table:table-row>")
    out.append("</table:table>")
    return "".join(out)


def _split_row(line: str) -> list:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\|[\s:|-]+\|?", line.strip()))


def markdown_to_content(text: str) -> str:
    """The `content.xml` body for a Markdown document."""
    body = []
    lines = text.splitlines()
    index = 0
    paragraph: list = []

    # Open list levels, innermost last, as (indent, kind). A nested list in ODF
    # lives INSIDE its parent's list item, so the parent item cannot be closed
    # until the nested list is - which is why the item's closing tag is
    # deferred rather than written with its paragraph.
    levels: list = []
    item_open = False

    def flush(style="Standard"):
        if paragraph:
            body.append(_paragraph(" ".join(paragraph).strip(), style))
            paragraph.clear()

    def open_list(kind, indent):
        nonlocal item_open
        body.append('<text:list text:style-name="%s">'
                    % ("L_Number" if kind == "number" else "L_Bullet"))
        levels.append((indent, kind))
        item_open = False

    def close_item():
        nonlocal item_open
        if item_open:
            body.append("</text:list-item>")
            item_open = False

    def close_list():
        """Close every open level, innermost first."""
        nonlocal item_open
        while levels:
            close_item()
            body.append("</text:list>")
            levels.pop()
            if levels:
                # this list was nested inside a parent item; that item ends here
                item_open = True
                close_item()

    while index < len(lines):
        raw = lines[index]
        line = raw.strip()

        if not line:
            flush()
            close_list()
            index += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            flush()
            close_list()
            body.append(_heading(heading.group(2).strip(),
                                 len(heading.group(1))))
            index += 1
            continue

        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", line):
            flush()
            close_list()
            body.append('<text:p text:style-name="Horizontal_20_Line"/>')
            index += 1
            continue

        if line.startswith(">"):
            flush()
            close_list()
            quote = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote.append(lines[index].strip().lstrip(">").strip())
                index += 1
            body.append(_paragraph(" ".join(q for q in quote if q), "Quotations"))
            continue

        if line.startswith("|"):
            flush()
            close_list()
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                candidate = lines[index]
                if not _is_separator(candidate):
                    rows.append(_split_row(candidate))
                index += 1
            body.append(_table(rows))
            continue

        item = re.match(r"^([-*]|\d+\.)\s+(.*)$", line)
        if item:
            flush()
            kind = "bullet" if item.group(1) in ("-", "*") else "number"
            indent = len(raw) - len(raw.lstrip())

            if not levels:
                open_list(kind, indent)
            elif indent > levels[-1][0]:
                # deeper: the new list belongs inside the item just written,
                # so that item stays open
                open_list(kind, indent)
            else:
                # same level or shallower: unwind to the matching level
                while len(levels) > 1 and indent < levels[-1][0]:
                    close_item()
                    body.append("</text:list>")
                    levels.pop()
                    item_open = True        # the parent item resumes...
                    close_item()            # ...and ends here
                close_item()
                if levels[-1][1] != kind:
                    # a bullet list following a numbered one at the same depth
                    body.append("</text:list>")
                    levels.pop()
                    open_list(kind, indent)

            content = [item.group(2).strip()]
            index += 1
            while (index < len(lines) and lines[index].strip()
                   and not re.match(r"^\s*([-*]|\d+\.)\s+", lines[index])
                   and lines[index].startswith((" ", "\t"))):
                content.append(lines[index].strip())
                index += 1
            # Left OPEN on purpose: a deeper item that follows nests inside
            # this one, and only then can it be closed.
            body.append("<text:list-item>%s" % _paragraph(" ".join(content)))
            item_open = True
            continue

        close_list()
        paragraph.append(line)
        index += 1

    flush()
    close_list()

    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<office:document-content %s office:version="1.2">\n'
            " <office:body><office:text>%s</office:text></office:body>\n"
            "</office:document-content>\n" % (_NS, "".join(body)))


def write_odt(markdown: str, path: str) -> str:
    """Write `markdown` to `path` as an Open Document Text file."""
    content = markdown_to_content(markdown)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        # FIRST and STORED, per the format: a reader identifies an ODT by
        # reading this entry without inflating anything.
        archive.writestr(
            zipfile.ZipInfo("mimetype"), _MIME, compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/manifest.xml", _MANIFEST)
        archive.writestr("styles.xml", _STYLES)
        archive.writestr("content.xml", content)
    return path
