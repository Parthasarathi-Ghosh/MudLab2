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
from PySide6.QtGui import QColor, QDesktopServices, QTextCursor, QTextDocument
from PySide6.QtWidgets import QDialog, QMessageBox

from mudlab.qt_utils import clear_auto_default
from mudlab.ui.ui_manual import Ui_ManualDialog

#: The document Help -> Manual opens on.
HOME_DOCUMENT = "getting-started.md"


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
        self._style_quotes()
        if anchor:
            self._scroll_to(anchor)
        else:
            self.ui.browser.verticalScrollBar().setValue(0)
        return True

    def _style_quotes(self) -> None:
        """Give block quotes a tinted background.

        Qt's Markdown reader renders a quote as a paragraph with a left margin
        and nothing else, so the warnings look like body text. The margin is
        what identifies them - list items carry an indent instead, and are left
        alone."""
        document = self.ui.browser.document()
        tint = QColor(self.palette().alternateBase().color())
        block = document.begin()
        cursor = QTextCursor(document)
        cursor.beginEditBlock()
        while block.isValid():
            fmt = block.blockFormat()
            if fmt.leftMargin() > 0 and not fmt.indent():
                fmt.setBackground(tint)
                cursor.setPosition(block.position())
                cursor.setBlockFormat(fmt)
            block = block.next()
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

    def _go_back(self) -> None:
        self.ui.browser.backward()
        self._style_quotes()

    # ------------------------------------------------------------------
    def keyPressEvent(self, event) -> None:
        # F1 is the way in; let it close the manual again rather than opening
        # a second copy over the top of this one.
        if event.key() == Qt.Key.Key_F1:
            self.close()
            return
        super().keyPressEvent(event)
