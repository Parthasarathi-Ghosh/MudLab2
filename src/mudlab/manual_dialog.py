"""The in-app manual (Help -> Manual, F1).

Renders the bundled Markdown documentation in a QTextBrowser. Markdown rather
than HTML so the SAME files serve three readers - this viewer, GitHub, and
anyone opening `docs/` in an editor - and cannot drift apart.

Three things Qt's Markdown reader does not do for us, handled here:

  * **Heading anchors.** `scrollToAnchor` does nothing for a Markdown document,
    so every "Contents" list would be dead links. We build the GitHub-style
    slug for each heading ourselves and scroll to the block.
  * **Block quotes.** They survive as an indented paragraph with no styling, so
    the cautions - the parts a reader most needs to notice - read as ordinary
    text. Indented blocks get a tinted background here instead.
  * **Links.** `openLinks` is off, so nothing navigates without going through
    `_on_anchor`: sibling documents load in place (with history), fragments
    scroll, and external URLs go to the browser rather than being loaded into
    this widget as if they were local files.
"""

from __future__ import annotations

import os
import re

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import (
    QColor, QDesktopServices, QTextBlockFormat, QTextCursor, QTextDocument,
    QTextDocumentWriter,
)
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from mudlab.qt_utils import clear_auto_default
from mudlab.ui.ui_manual import Ui_ManualDialog

# Printing lives in a separate Qt module. It is imported at module scope so the
# frozen build's dependency analysis sees it - nothing else in the program uses
# it, and it was absent from the v1.0.3 bundle for exactly that reason. Guarded
# all the same: a missing module must disable one button, not break the manual.
try:
    from PySide6.QtPrintSupport import QPrintDialog, QPrinter
    PRINTING_AVAILABLE = True
except ImportError:                                   # pragma: no cover
    QPrintDialog = QPrinter = None
    PRINTING_AVAILABLE = False

#: What a page can be saved as. Nothing here needs anything installed: the ODT
#: is written by this program (`file_parsers.odt_export`) and the rest by Qt.
#: A format of None marks the one written here rather than by Qt.
EXPORT_FORMATS = (
    ("Open Document Text (*.odt)", ".odt", None),
    ("Web page (*.html)", ".html", b"HTML"),
    ("Markdown (*.md)", ".md", b"markdown"),
    ("Plain text (*.txt)", ".txt", b"plaintext"),
)

#: The document Help -> Manual opens on.
HOME_DOCUMENT = "getting-started.md"
#: The document Help -> How MudLab Works opens on.
SCIENCE_DOCUMENT = "how-it-works.md"


def docs_dir() -> str:
    """Directory holding the bundled Markdown documentation.

    Two layouts. In the frozen build MudLab.spec maps the repository's `docs`
    tree to `mudlab/docs`, i.e. beside this package; in a source checkout the
    package is `src/mudlab`, so the same tree is two levels up. Checking the
    frozen location first means the bundle never reaches outside itself.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    packaged = os.path.join(here, "docs")
    if os.path.isdir(packaged):
        return packaged
    return os.path.normpath(os.path.join(here, os.pardir, os.pardir, "docs"))


def heading_slug(text: str) -> str:
    """GitHub's anchor for a heading, so a Contents list written for GitHub
    also works here: lower-cased, punctuation dropped, spaces to hyphens.

    Each space becomes its own hyphen - GitHub does NOT collapse runs. Dropping
    punctuation leaves the spaces that surrounded it, so "(Load / Store)" ends
    up "load--store" with two. Collapsing here instead would make the viewer
    disagree with GitHub about exactly the headings that contain punctuation,
    and those links would be dead in one place and live in the other.
    """
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    return re.sub(r"\s", "-", slug)


class ManualDialog(QDialog):
    """Modeless viewer for the bundled documentation."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.ui = Ui_ManualDialog()
        self.ui.setupUi(self)
        # Qt re-grants autoDefault when a button is reparented into a dialog,
        # so the .ui flags alone are not enough (see docs/dev-notes.md): a
        # stray Enter must not fire Back or Close while the reader is scrolling.
        clear_auto_default(self)

        self._docs = docs_dir()
        self.ui.browser.setSearchPaths([self._docs])
        self.ui.browser.setOpenLinks(False)
        self.ui.browser.setOpenExternalLinks(False)
        self.ui.browser.anchorClicked.connect(self._on_anchor)

        self.ui.btn_back.clicked.connect(self._go_back)
        self.ui.btn_contents.clicked.connect(lambda: self.show_document(HOME_DOCUMENT))
        self.ui.btn_print.clicked.connect(self._print)
        self.ui.btn_print.setEnabled(PRINTING_AVAILABLE)
        if not PRINTING_AVAILABLE:
            self.ui.btn_print.setToolTip(
                "Printing is unavailable in this build. Export the page "
                "instead and print it from another program.")
        self.ui.btn_export.clicked.connect(self._export)
        self.ui.btn_close.clicked.connect(self.close)
        self.ui.browser.backwardAvailable.connect(self.ui.btn_back.setEnabled)
        self.ui.btn_back.setEnabled(False)

        self.show_document(HOME_DOCUMENT)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def show_document(self, name: str, anchor: str = "") -> bool:
        """Load `name` from the docs directory; optionally scroll to `anchor`.
        Answers whether the document was found."""
        path = os.path.join(self._docs, name)
        if not os.path.isfile(path):
            # Say so IN the window as well as in the box. Warning alone leaves
            # a blank viewer behind, which reads as "the manual is empty"
            # rather than "the manual is missing" - and this is reachable from
            # the constructor, so that blank window would be the first thing
            # the reader sees.
            self.ui.browser.setMarkdown(
                "## The manual could not be found\n\n"
                "MudLab looked for `%s` in:\n\n    %s\n\n"
                "The documentation is normally installed alongside the "
                "program. Reinstalling should restore it.\n" % (name, self._docs)
            )
            QMessageBox.warning(
                self, "Manual",
                "The documentation file could not be found:\n\n%s\n\n"
                "It is normally installed alongside the program." % path,
            )
            return False
        self.ui.browser.setSource(
            QUrl(name), QTextDocument.ResourceType.MarkdownResource
        )
        self._after_load(anchor)
        return True

    def _after_load(self, anchor: str = "") -> None:
        """Style and scroll a freshly loaded document."""
        self._style_quotes()
        if anchor:
            self._scroll_to(anchor)
        else:
            self.ui.browser.verticalScrollBar().setValue(0)

    def _style_quotes(self) -> None:
        """Give block quotes a tinted background.

        Qt's Markdown reader renders a quote as a paragraph with a left margin
        and nothing else, so the warnings look like body text. The margin is
        what identifies them - list items carry an indent instead, and are left
        alone."""
        document = self.ui.browser.document()
        tint = QColor(self.palette().alternateBase().color())

        # FORCE THE LAYOUT BEFORE TOUCHING THE DOCUMENT. Editing between
        # `setSource` and the first layout leaves the layout wrong and it never
        # recovers: paragraphs lay out to zero height, so a long document
        # renders as a run of bare headings with all of its text present but
        # unshown, and every anchor past the middle scrolls to the bottom
        # because its position is read from the collapsed layout. Measured on
        # this manual: 4354 px against the correct 6005 px. Asking the layout
        # for its size completes it; `setTextWidth` invalidates it again and
        # `adjustSize` only finishes part of it, so neither will do.
        document.documentLayout().documentSize()

        # SURVEY FIRST, THEN EDIT. Editing a document invalidates the block
        # iterators walking it, so advancing one while applying formats reads
        # and writes against stale blocks. The damage is not lost text - the
        # characters all survive - but wrong formats land on the wrong blocks
        # and paragraphs lay out to zero height, so a long document renders as
        # a run of bare headings. It went unseen because the symptom only
        # shows well down a document that is long enough to have one.
        targets = []
        block = document.begin()
        while block.isValid():
            fmt = block.blockFormat()
            if fmt.leftMargin() > 0 and not fmt.indent():
                targets.append(block.blockNumber())
            block = block.next()
        if not targets:
            return

        # MERGE the background in; do not re-apply the whole block format.
        # Setting a block format REPLACES it, and a quote's paragraphs carry
        # structure from the Markdown importer that does not survive the round
        # trip - re-applying what looked like the same format collapsed much of
        # the document to zero height. The text was all still there, which is
        # why it took looking at a rendered page to notice.
        tinted = QTextBlockFormat()
        tinted.setBackground(tint)

        cursor = QTextCursor(document)
        cursor.beginEditBlock()
        try:
            for number in targets:
                block = document.findBlockByNumber(number)
                if not block.isValid():
                    continue
                cursor.setPosition(block.position())
                cursor.mergeBlockFormat(tinted)
        finally:
            cursor.endEditBlock()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _on_anchor(self, url: QUrl) -> None:
        """Handle a clicked link. `openLinks` is off so every navigation lands
        here, which is what keeps an http(s) link from being loaded into this
        widget as though it were a local file."""
        if not url.scheme() or url.scheme() == "file":
            name, anchor = url.fileName(), url.fragment()
            if name:
                self.show_document(name, anchor)
            elif anchor:
                self._scroll_to(anchor)
            return
        QDesktopServices.openUrl(url)

    def _scroll_to(self, anchor: str) -> None:
        """Scroll to the heading whose GitHub slug is `anchor`.

        `QTextBrowser.scrollToAnchor` is useless on a Markdown document - Qt
        emits no anchors for headings - so the slugs are recomputed from the
        heading text and matched here."""
        wanted = anchor.lstrip("#").lower()
        block = self.ui.browser.document().begin()
        while block.isValid():
            if block.blockFormat().headingLevel() and \
                    heading_slug(block.text()) == wanted:
                cursor = QTextCursor(block)
                self.ui.browser.setTextCursor(cursor)
                self.ui.browser.ensureCursorVisible()
                # Put the heading at the top of the view rather than merely
                # on screen, which is where a reader expects to land.
                bar = self.ui.browser.verticalScrollBar()
                rect = self.ui.browser.cursorRect(cursor)
                bar.setValue(bar.value() + rect.top())
                return
            block = block.next()

    # ------------------------------------------------------------------
    # Taking the page away with you
    # ------------------------------------------------------------------
    def _print(self) -> None:
        """Print the page that is open.

        The print dialog's own "Print to PDF" is the PDF route, so there is no
        separate PDF export: one dialog, and the platform decides what it can
        offer.
        """
        if not PRINTING_AVAILABLE:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(self._document_title())
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Print %s" % self._document_title())
        if dialog.exec():
            self.ui.browser.document().print_(printer)

    def _export(self) -> None:
        """Save the page as a document.

        Written by Qt's own document writer, so ODT, HTML, Markdown and plain
        text all work with nothing installed beyond the program itself. ODT is
        offered first because it is the one that opens in a word processor and
        can be edited.
        """
        filters = ";;".join(label for label, _ext, _fmt in EXPORT_FORMATS)
        suggested = os.path.join(
            os.path.expanduser("~"),
            "%s%s" % (self._document_stem(), EXPORT_FORMATS[0][1]))
        path, chosen = QFileDialog.getSaveFileName(
            self, "Export %s" % self._document_title(), suggested, filters)
        if not path:
            return

        fmt = EXPORT_FORMATS[0][2]
        extension = EXPORT_FORMATS[0][1]
        for label, ext, code in EXPORT_FORMATS:
            if label == chosen:
                fmt, extension = code, ext
                break
        if not os.path.splitext(path)[1]:
            path += extension

        try:
            if fmt is None:
                self._write_odt(path)
            else:
                writer = QTextDocumentWriter(path)
                writer.setFormat(fmt)
                if not writer.write(self.ui.browser.document()):
                    raise OSError("the document writer refused the file")
        except (OSError, ValueError) as error:
            QMessageBox.warning(
                self, "Export",
                "The document could not be written to:\n\n%s\n\n%s"
                % (path, error))
            return
        QMessageBox.information(
            self, "Export", "Saved:\n\n%s" % path)

    def _write_odt(self, path: str) -> None:
        """Write the page as a STRUCTURED Open Document.

        From the Markdown SOURCE rather than the rendered document, because the
        structure lives in the source and Qt's own ODF export throws it away:
        it writes every heading as a paragraph in a heading-like style, so the
        file looks right, navigates nowhere, and generates an empty table of
        contents. Reading the source back gives real headings with outline
        levels, real lists and real tables.
        """
        from mudlab.file_parsers.odt_export import write_odt

        source = os.path.join(
            self._docs, self.ui.browser.source().fileName() or HOME_DOCUMENT)
        with open(source, "r", encoding="utf-8") as handle:
            write_odt(handle.read(), path)

    def _document_stem(self) -> str:
        name = self.ui.browser.source().fileName() or HOME_DOCUMENT
        return os.path.splitext(name)[0]

    def _document_title(self) -> str:
        """The page's own first heading, which is a better name than its
        filename for a print header or a save dialog."""
        block = self.ui.browser.document().begin()
        while block.isValid():
            if block.blockFormat().headingLevel() == 1 and block.text().strip():
                return block.text().strip()
            block = block.next()
        return self._document_stem()

    def _go_back(self) -> None:
        self.ui.browser.backward()
        self._after_load()

    # ------------------------------------------------------------------
    def keyPressEvent(self, event) -> None:
        # F1 is the way in; let it close the manual again rather than opening
        # a second copy over the top of this one.
        if event.key() == Qt.Key.Key_F1:
            self.close()
            return
        super().keyPressEvent(event)
