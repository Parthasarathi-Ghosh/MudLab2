#!/usr/bin/env python
"""Help -> Manual (F1): that it opens, renders, and that its own links work.

`actionManual` shipped in v1.0.0 through v1.0.2 as a **dead action** - the
QAction and its F1 shortcut existed in the generated UI with no handler in any
source file, so pressing F1 did nothing at all. That is the regression this
pins first.

The rest is about the documentation staying navigable. Qt's Markdown reader
emits no anchors for headings, so `scrollToAnchor` is inert and every "Contents"
list would be dead links; the dialog recomputes GitHub's slugs itself. The
consequence is that a renamed heading silently breaks its own table of contents,
which no one would notice by reading the file - so every internal link in every
shipped document is resolved here.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_manual.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import os
import re
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QDesktopServices  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from mudlab.manual_dialog import (  # noqa: E402
    EXPORT_FORMATS, HOME_DOCUMENT, PRINTING_AVAILABLE, SCIENCE_DOCUMENT,
    ManualDialog, docs_dir, heading_slug,
)

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def headings_in(text):
    """{slug: heading text} for every ATX heading, skipping fenced code."""
    out = {}
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            out[heading_slug(match.group(2))] = match.group(2)
    return out


def main():  # noqa: C901 - a checklist
    docs = docs_dir()
    check("the docs directory resolves (%s)" % os.path.basename(docs),
          os.path.isdir(docs))
    home = os.path.join(docs, HOME_DOCUMENT)
    check("...and holds the document F1 opens (%s)" % HOME_DOCUMENT,
          os.path.isfile(home))
    check("...and the full reference it links to (user-manual.md)",
          os.path.isfile(os.path.join(docs, "user-manual.md")))

    # ------------------------------------------------- 1. the dead action
    real_question = QMessageBox.question
    QMessageBox.question = staticmethod(
        lambda *a, **k: QMessageBox.StandardButton.No)
    warned = []
    real_warning = QMessageBox.warning
    QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(a[2:3]))
    # Export reports success with an information box. An unstubbed modal does
    # not fail the harness - it HANGS it, waiting for a click that never comes.
    real_information = QMessageBox.information
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    try:
        from mudlab.main_window import MainWindow

        window = MainWindow()
        app.processEvents()
        check("Help -> Manual has a shortcut (%s)"
              % window.ui.actionManual.shortcut().toString(),
              window.ui.actionManual.shortcut().toString() == "F1")
        check("the manual is not open before it is asked for",
              getattr(window, "_manual_dialog", None) is None)
        window.ui.actionManual.trigger()
        app.processEvents()
        dialog = window._manual_dialog
        check("triggering the action OPENS the manual (the dead-action fix)",
              isinstance(dialog, ManualDialog) and dialog.isVisible())
        check("...on the walkthrough (%s)" % dialog.ui.browser.source().fileName(),
              dialog.ui.browser.source().fileName() == HOME_DOCUMENT)
        check("...with no warning raised", not warned)

        rendered = dialog.ui.browser.toPlainText()
        html = dialog.ui.browser.toHtml()
        check("the markdown actually renders (%d chars, %d headings)"
              % (len(rendered), html.count("<h2")),
              len(rendered) > 5000 and html.count("<h2") >= 10)
        check("...as rich text, not as raw markdown",
              "##" not in rendered and "**" not in rendered)

        # Reopening must reuse the instance, so the reader returns to their page.
        dialog.close()
        window.ui.actionManual.trigger()
        app.processEvents()
        check("reopening reuses the same window rather than stacking copies",
              window._manual_dialog is dialog)

        # Enter must not fire Back/Contents/Close while someone is reading.
        auto = [b.autoDefault() for b in (dialog.ui.btn_back,
                                          dialog.ui.btn_contents,
                                          dialog.ui.btn_close)]
        check("no button claims autoDefault (Enter cannot fire one) %s" % auto,
              not any(auto))

        # ------------------------------------------- 2. navigation
        check("Back starts disabled", not dialog.ui.btn_back.isEnabled())
        dialog._on_anchor(QUrl("user-manual.md"))
        app.processEvents()
        check("a link to a sibling document loads it (%d chars)"
              % len(dialog.ui.browser.toPlainText()),
              dialog.ui.browser.source().fileName() == "user-manual.md"
              and len(dialog.ui.browser.toPlainText()) > 20000)
        check("...rendered as markdown too, not as source",
              dialog.ui.browser.toHtml().count("<h2") > 5)
        check("...and Back becomes available", dialog.ui.btn_back.isEnabled())
        dialog._go_back()
        app.processEvents()
        check("Back returns to the walkthrough",
              dialog.ui.browser.source().fileName() == HOME_DOCUMENT)

        # An http link must go to the browser, NOT be loaded in this widget as
        # if it were a local file.
        opened = []
        real_open = QDesktopServices.openUrl
        QDesktopServices.openUrl = staticmethod(
            lambda url: opened.append(url.toString()) or True)
        try:
            dialog._on_anchor(QUrl("https://example.invalid/x"))
            app.processEvents()
        finally:
            QDesktopServices.openUrl = real_open
        check("an external link goes to the web browser %s" % opened,
              opened == ["https://example.invalid/x"]
              and dialog.ui.browser.source().fileName() == HOME_DOCUMENT)

        # Print and Export act on the page SHOWN. With an error notice up
        # there is no page, and they used to fall back to the walkthrough -
        # exporting a document the reader was not looking at, silently.
        warned.clear()
        dialog.show_document("definitely-not-here.md")
        app.processEvents()
        check("with no page loaded, Print and Export are disabled",
              not dialog.ui.btn_export.isEnabled()
              and not dialog.ui.btn_print.isEnabled())
        dialog.show_document(SCIENCE_DOCUMENT)
        app.processEvents()
        check("...and they come back when a page loads again",
              dialog.ui.btn_export.isEnabled())
        warned.clear()

        # A missing document must explain itself, not raise.
        warned.clear()
        found = dialog.show_document("no-such-document.md")
        check("a missing document warns instead of crashing",
              found is False and bool(warned))
        warned.clear()

        # ------------------------------- 3. every internal link resolves
        dialog.show_document(HOME_DOCUMENT)
        app.processEvents()
        broken = []
        for name in sorted(f for f in os.listdir(docs) if f.endswith(".md")):
            with open(os.path.join(docs, name), encoding="utf-8") as handle:
                text = handle.read()
            slugs = headings_in(text)
            for target in re.findall(r"\]\(([^)]+)\)", text):
                target = target.strip()
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                doc_part, _, fragment = target.partition("#")
                if doc_part:
                    if not os.path.isfile(os.path.join(docs, doc_part)):
                        broken.append("%s -> %s (no such file)" % (name, target))
                        continue
                    if fragment:
                        with open(os.path.join(docs, doc_part),
                                  encoding="utf-8") as handle:
                            if fragment not in headings_in(handle.read()):
                                broken.append("%s -> %s (no such heading)"
                                              % (name, target))
                elif fragment and fragment not in slugs:
                    broken.append("%s -> #%s (no such heading)" % (name, fragment))
        check("every link in every shipped document resolves%s"
              % ("" if not broken else " -> %s" % broken[:5]), not broken)

        # ...and that the viewer really scrolls to them, not just that the
        # heading exists in the file.
        dialog.resize(800, 600)
        dialog.show()
        app.processEvents()
        with open(home, encoding="utf-8") as handle:
            home_text = handle.read()
        anchors = [a for a in re.findall(r"\]\(#([^)]+)\)", home_text)]
        check("the walkthrough has a table of contents (%d entries)"
              % len(anchors), len(anchors) >= 8)
        unmoved = []
        for anchor in anchors:
            bar = dialog.ui.browser.verticalScrollBar()
            bar.setValue(0)
            app.processEvents()
            dialog._scroll_to(anchor)
            app.processEvents()
            if bar.value() <= 0:
                unmoved.append(anchor)
        # The first entry legitimately sits at the top of the document.
        unmoved = [a for a in unmoved if a != anchors[0]]
        check("every contents entry scrolls the view%s"
              % ("" if not unmoved else " -> %s" % unmoved), not unmoved)

        # ------------------------------------------- 4. quote styling
        dialog.show_document(HOME_DOCUMENT)
        app.processEvents()
        document = dialog.ui.browser.document()
        block = document.begin()
        quoted = tinted = 0
        while block.isValid():
            fmt = block.blockFormat()
            if fmt.leftMargin() > 0 and not fmt.indent():
                quoted += 1
                if fmt.background().style():
                    tinted += 1
            block = block.next()
        check("block quotes are found and tinted (%d of %d)" % (tinted, quoted),
              quoted > 0 and tinted == quoted)


        # ------------------------------- 4b. styling must not break layout
        #
        # The quote tinting edits the document, and editing between `setSource`
        # and the document's FIRST layout leaves that layout permanently wrong:
        # paragraphs lay out to zero height, so a long page renders as a run of
        # bare headings with every character still present. `toPlainText` is no
        # help - the text is all there - so this compares laid-out HEIGHT with
        # the same document rendered without the styling pass.
        #
        # Two conditions are load-bearing and were both got wrong first time,
        # producing a check that passed with the bug reintroduced: it must use
        # a FRESH dialog (a reused one has a warm layout and does not collapse)
        # and it must test EVERY bundled document, because the largest one
        # happens not to show it.
        from PySide6.QtGui import QTextDocument
        from PySide6.QtWidgets import QTextBrowser

        doc_files = [n for n in os.listdir(docs) if n.endswith('.md')]
        collapsed = []
        for name in sorted(doc_files):
            fresh = ManualDialog()
            fresh.resize(900, 780)
            fresh.show()
            app.processEvents()
            fresh.show_document(name)
            app.processEvents()
            styled = fresh.ui.browser.document().documentLayout().documentSize().height()

            plain = QTextBrowser()
            plain.resize(fresh.ui.browser.width(), fresh.ui.browser.height())
            plain.setSearchPaths([docs])
            plain.show()      # an unshown widget never lays out, and reports 0
            app.processEvents()
            plain.setSource(QUrl(name), QTextDocument.ResourceType.MarkdownResource)
            app.processEvents()
            unstyled = plain.document().documentLayout().documentSize().height()

            if unstyled <= 0 or styled < unstyled * 0.95:
                collapsed.append("%s (%.0f of %.0f px)" % (name, styled, unstyled))
            plain.deleteLater()
            fresh.close()
            fresh.deleteLater()
        check("styling never collapses a document's layout%s"
              % ("" if not collapsed else " -> %s" % collapsed), not collapsed)

        # ...and the anchors must land where the headings are, not all at the
        # bottom. A collapsed layout still "scrolls" - every position is simply
        # the maximum - so checking that a click moves the view proves nothing.
        longest = max(doc_files, key=lambda n: os.path.getsize(os.path.join(docs, n)))
        dialog.show_document(longest)
        app.processEvents()
        with open(os.path.join(docs, longest), encoding="utf-8") as handle:
            targets = re.findall(r"\]\(#([^)]+)\)", handle.read())
        bar = dialog.ui.browser.verticalScrollBar()
        landed = []
        for target in targets:
            bar.setValue(0)
            app.processEvents()
            dialog._scroll_to(target)
            app.processEvents()
            landed.append(bar.value())
        distinct = len(set(landed))
        check("contents entries land at distinct positions, not all at the "
              "bottom (%d distinct of %d)" % (distinct, len(landed)),
              len(landed) >= 8 and distinct >= len(landed) - 4)
        # NOT monotonicity: a document may legitimately link backwards, and
        # this manual does - a cross-reference in the component section points
        # back at the atom-relations heading. What a collapsed layout destroys
        # is the SPREAD, since every position becomes the maximum.
        span = (max(landed) - min(landed)) / max(1, bar.maximum())
        check("...spread across the document rather than bunched at the end "
              "(%.0f%% of the scroll range)" % (100 * span), span > 0.6)

        # --------------------------------- 5. opening the science directly
        window.ui.actionHowItWorks.trigger()
        app.processEvents()
        check("Help -> How MudLab Works opens the science document (%s)"
              % dialog.ui.browser.source().fileName(),
              dialog.ui.browser.source().fileName() == SCIENCE_DOCUMENT)
        check("...on its own shortcut (%s)"
              % window.ui.actionHowItWorks.shortcut().toString(),
              window.ui.actionHowItWorks.shortcut().toString() == "Shift+F1")
        check("...reusing the one viewer rather than opening a second",
              window._manual_dialog is dialog)
        window.ui.actionManual.trigger()
        app.processEvents()
        check("...and Help -> Manual still opens the walkthrough",
              dialog.ui.browser.source().fileName() == HOME_DOCUMENT)

        # ------------------------------------------- 6. print and export
        check("the viewer offers printing and exporting",
              dialog.ui.btn_print.text().startswith("Print")
              and dialog.ui.btn_export.text().startswith("Export"))
        check("...without claiming autoDefault",
              not dialog.ui.btn_print.autoDefault()
              and not dialog.ui.btn_export.autoDefault())
        check("printing is available in this build", PRINTING_AVAILABLE)
        check("...and the print button follows that",
              dialog.ui.btn_print.isEnabled() == PRINTING_AVAILABLE)

        # QtPrintSupport is the only Qt module the program uses for one
        # feature, and it was absent from the v1.0.3 bundle because nothing
        # imported it. A release that loses it again would fail only when
        # someone pressed Print.
        with open(os.path.join(_REPO, "MudLab.spec"), encoding="utf-8") as handle:
            spec = handle.read()
        check("the frozen build is told to ship QtPrintSupport",
              "PySide6.QtPrintSupport" in spec)

        # Export must produce real files, and must go through the DIALOG so
        # this tests what ships: ODT is written by the program's own writer
        # (see verify_odt_export.py for its structure) and the rest by Qt, and
        # a check that called the writers directly would miss a mis-wired
        # dialog entirely.
        import tempfile
        import zipfile

        from PySide6.QtWidgets import QFileDialog

        dialog.show_document(SCIENCE_DOCUMENT)
        app.processEvents()
        scratch = tempfile.mkdtemp(prefix="manual-export-")
        real_save = QFileDialog.getSaveFileName
        written = []
        try:
            for label, extension, _fmt in EXPORT_FORMATS:
                target = os.path.join(scratch, "page" + extension)
                QFileDialog.getSaveFileName = staticmethod(
                    lambda *a, _t=target, _l=label, **k: (_t, _l))
                dialog._export()
                size = os.path.getsize(target) if os.path.isfile(target) else 0
                written.append((extension, size))
        finally:
            QFileDialog.getSaveFileName = real_save
        check("every offered export format writes a non-empty file %s" % written,
              all(size > 500 for _e, size in written))

        odt = os.path.join(scratch, "page.odt")
        check("...and the ODT is a real Open Document package",
              zipfile.is_zipfile(odt)
              and "content.xml" in zipfile.ZipFile(odt).namelist())
        with zipfile.ZipFile(odt) as package:
            body = package.read("content.xml").decode("utf-8", "ignore")
        check("...carrying the document's actual text",
              "Reichweite" in body and "Loewenstein" in body)
        # The point of writing the ODT ourselves: Qt's export produces none of
        # these, so the file navigates nowhere and builds an empty contents.
        check("...and REAL headings, which Qt's own ODF export does not give "
              "(%d)" % body.count("<text:h "), body.count("<text:h ") > 30)

        window._dirty = False
        dialog.close()
        window.close()
    finally:
        QMessageBox.question = real_question
        QMessageBox.warning = real_warning
        QMessageBox.information = real_information

    # --------------------------------------- 5. the frozen build ships them
    #
    # ...and ships ONLY them. `docs/` also holds development material - the
    # remaining-work list, the documentation plan, dev notes - which is of no
    # use to a user and reads like an accident when found in a release. The
    # rule is "every document reachable by a link from the manual, and nothing
    # else", checked in both directions so that adding a page to the manual
    # fails here until it is bundled, and bundling an internal note fails too.
    with open(os.path.join(_REPO, "MudLab.spec"), encoding="utf-8") as handle:
        spec = handle.read()
    bundled = set(re.findall(r'\("docs/([^"]+)",\s*"mudlab/docs"\)', spec))
    check("MudLab.spec bundles the manual beside the package (%d files)"
          % len(bundled), bool(bundled))
    check("...and not the whole docs tree",
          '("docs", "mudlab/docs")' not in spec)

    reachable, queue = set(), [HOME_DOCUMENT]
    while queue:
        name = queue.pop()
        if name in reachable or not os.path.isfile(os.path.join(docs, name)):
            continue
        reachable.add(name)
        with open(os.path.join(docs, name), encoding="utf-8") as handle:
            body = handle.read()
        for target in re.findall(r"\]\(([^)#]+)", body):
            target = target.strip()
            if target.endswith(".md"):
                queue.append(target)
    check("every document the manual can reach is bundled%s"
          % ("" if reachable <= bundled else " -> missing %s"
             % sorted(reachable - bundled)), reachable <= bundled)
    check("no development-only document is shipped%s"
          % ("" if bundled <= reachable else " -> %s" % sorted(bundled - reachable)),
          bundled <= reachable)

    # --------------------------------------------- 6. it cannot hang the app
    #
    # Everything the manual does is synchronous on the GUI thread: parsing the
    # Markdown, laying it out, restyling the quotes, and the block walk behind
    # a Contents click. All of it is linear in document size, and the budget
    # below is ~100x the measured cost of the largest shipped document, so it
    # fails on a change of ALGORITHM rather than on a slow machine.
    import time

    dialog = ManualDialog()
    worst = 0.0
    for name in sorted(reachable):
        start = time.perf_counter()
        dialog.show_document(name)
        dialog._scroll_to("no-such-heading-full-scan")
        worst = max(worst, time.perf_counter() - start)
    dialog.close()
    check("the slowest document loads well inside a frame budget (%.0f ms)"
          % (worst * 1000), worst < 1.0)

    check("heading_slug follows GitHub's rules",
          heading_slug("3. Check the specimen's settings")
          == "3-check-the-specimens-settings"
          and heading_slug("Stored setups (Load / Store)")
          == "stored-setups-load--store")

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("In-app manual (Help -> Manual, F1)")
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
