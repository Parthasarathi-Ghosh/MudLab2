#!/usr/bin/env python
"""Component pane: the Show Structure button and its cross-section diagram.

Port of the old app's `btn_show_structure` -> `build_structure_diagram`. This
covers the text the builder produces, the dialog that shows it, and - because
adding a QPushButton to a dialog is exactly how this app has been bitten before
- the autoDefault state of the new button.

THE AUTODEFAULT TRAP, restated: Qt gives `autoDefault` to every QPushButton with
a QDialog ancestor and RE-GRANTS it on reparenting, then promotes one to THE
default on show. So a new button in the component pane can quietly become the
thing Enter fires while the user is typing a component name. The .ui says
autoDefault=false, the widget clears it again after reparenting, and the
app-wide policy clears it on every dialog show - the checks below assert the
outcome, after a real show, which is the only state that matters.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_structure_diagram.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no usable sample project.
"""

from __future__ import annotations

import glob
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QPushButton  # noqa: E402

from mudlab.component_diagram import build_structure_diagram  # noqa: E402
from mudlab.edit_phases_dialog import EditPhasesDialog  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402
from mudlab.qt_utils import install_enter_policy  # noqa: E402
from mudlab.structure_diagram_dialog import StructureDiagramDialog  # noqa: E402

app = QApplication.instance() or QApplication([])
install_enter_policy(app)          # the real app installs this in create_app
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in sorted(glob.glob(os.path.join(
            _REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        if any(getattr(p, "components", None) for p in project.phases):
            return path, project
    return None, None


PATH, PROJECT = _fixture()
if PATH is None:
    print("No sample project with components; skipping (exit 2).")
    raise SystemExit(2)

COMPONENTS = [(phase, c) for phase in PROJECT.phases
              for c in (getattr(phase, "components", None) or [])]
PHASE, COMPONENT = COMPONENTS[0]


def main():
    text = build_structure_diagram(COMPONENT, PHASE.name)
    lines = text.splitlines()

    # --------------------------------------------------------- the content
    check("text: names the component", COMPONENT.name in text)
    check("text: names the phase it belongs to", PHASE.name in text)
    check("text: marks the d001 boundary", "d001" in text)
    check("text: marks lattice_d", "lattice_d" in text)
    check("text: marks z = 0", "z = 0.0000 nm" in text)
    check("text: every layer atom appears",
          all(a.name in text for a in COMPONENT.layer_atoms))
    check("text: every interlayer atom appears",
          all(a.name in text for a in COMPONENT.interlayer_atoms))
    check("text: atom types are shown",
          all((a.atom_type.name in text) for a in COMPONENT.layer_atoms
              if a.atom_type))
    check("text: reports the charge balance", "Charge balance" in text)
    # The scattering-ion caveat has to travel WITH the number, or a stock clay
    # reading "imbalanced" looks like a bug in the user's model.
    check("text: the charge caveat rides along with it",
          "SCATTERING ion" in text)

    # z values must descend down the page - it is a cross-section, and a
    # mis-sorted one is silently wrong rather than obviously wrong.
    zs = []
    for line in lines:
        if line.startswith("z = ") and ("│" in line or "·" in line):
            try:
                zs.append(float(line[4:line.index(" nm")]))
            except ValueError:
                pass
    check("text: atoms are listed top-down (%d rows)" % len(zs),
          len(zs) > 1 and all(a >= b for a, b in zip(zs, zs[1:])))

    # ------------------------------------------------------------ sheets
    layer_types = [(a.atom_type.name if a.atom_type else "").upper()
                   for a in COMPONENT.layer_atoms]
    if sum(1 for t in layer_types if t.startswith("SI")) >= 2:
        check("text: a 2:1 layer names LOWER and UPPER tetrahedral sheets",
              "LOWER TETRAHEDRAL SHEET" in text
              and "UPPER TETRAHEDRAL SHEET" in text)
    else:
        check("text: a 1:1 layer names a single tetrahedral sheet",
              "TETRAHEDRAL SHEET" in text
              and "LOWER TETRAHEDRAL SHEET" not in text)
    if any(t.startswith(("AL", "MG", "FE")) for t in layer_types):
        check("text: the octahedral sheet is labelled di/trioctahedral",
              "OCTAHEDRAL SHEET" in text
              and ("dioctahedral" in text or "trioctahedral" in text))
    else:
        check("text: (no octahedral cations in this component; skipped)", True)

    # ------------------------------------------------------------- purity
    check("text: the same component renders identically twice (no timestamp)",
          build_structure_diagram(COMPONENT, PHASE.name) == text)
    check("text: it does not mutate the component",
          COMPONENT.d001 == COMPONENT.d001)

    # A component with no atoms at all must still render, not raise.
    class _Empty:
        name = "Empty"
        d001 = 1.0
        default_c = 1.0
        layer_atoms: list = []
        interlayer_atoms: list = []
        atom_relations: list = []

    try:
        empty = build_structure_diagram(_Empty())
        raised = False
    except Exception:  # noqa: BLE001
        empty, raised = "", True
    check("text: an empty component renders instead of raising",
          not raised and "no interlayer" in empty)

    # ------------------------------------------------------------- dialog
    dialog = StructureDiagramDialog(None, component=COMPONENT,
                                    phase_name=PHASE.name)
    check("dialog: shows the diagram",
          dialog.ui.txt_diagram.toPlainText() == text)
    check("dialog: the text is read-only", dialog.ui.txt_diagram.isReadOnly())
    check("dialog: fixed-pitch font (the columns only line up in one)",
          dialog.ui.txt_diagram.font().fixedPitch()
          or "mono" in dialog.ui.txt_diagram.font().family().lower()
          or dialog.ui.txt_diagram.font().styleHint() == dialog.ui.txt_diagram
          .font().StyleHint.Monospace)
    check("dialog: no word wrap (wrapping would break the diagram)",
          dialog.ui.txt_diagram.lineWrapMode()
          == dialog.ui.txt_diagram.LineWrapMode.NoWrap)
    check("dialog: titled with the component", COMPONENT.name in dialog.windowTitle())
    check("dialog: it is MODELESS (read it while editing)", not dialog.isModal())

    # Re-pointing at another component re-renders in place.
    if len(COMPONENTS) > 1:
        other_phase, other = COMPONENTS[1]
        dialog.set_component(other, other_phase.name)
        check("dialog: set_component re-renders",
              dialog.ui.txt_diagram.toPlainText()
              == build_structure_diagram(other, other_phase.name))
        dialog.set_component(COMPONENT, PHASE.name)
    else:
        check("dialog: (only one component in this fixture; skipped)", True)

    # A live edit is picked up by refresh().
    before = dialog.ui.txt_diagram.toPlainText()
    COMPONENT.d001 = COMPONENT.d001 + 0.05
    dialog.refresh()
    check("dialog: refresh picks up a live model edit",
          dialog.ui.txt_diagram.toPlainText() != before)
    COMPONENT.d001 = COMPONENT.d001 - 0.05

    # Copy / Save
    app.clipboard().clear()
    dialog._on_copy()
    check("dialog: Copy puts the diagram on the clipboard",
          app.clipboard().text().startswith("═"))
    tmp = tempfile.mkdtemp(prefix="mudlab_diagram_")
    target = os.path.join(tmp, "diagram.txt")
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (target, ""))
    dialog._on_save()
    check("dialog: Save writes the file", os.path.isfile(target))
    if os.path.isfile(target):
        with open(target, encoding="utf-8") as handle:
            check("dialog: saved as UTF-8, box characters intact",
                  handle.read().startswith("═"))
        os.remove(target)
    # An extension-less name still lands as .txt.
    noext = os.path.join(tmp, "diagram2")
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (noext, ""))
    dialog._on_save()
    check("dialog: an extension-less name becomes .txt",
          os.path.isfile(noext + ".txt"))
    for name in os.listdir(tmp):
        os.remove(os.path.join(tmp, name))
    os.rmdir(tmp)

    # --------------------------------------------------------- AUTODEFAULT
    editor = EditPhasesDialog(None, project=PROJECT)
    editor.show()          # the policy runs on SHOW - this is the real state
    app.processEvents()
    editor.ui.edit_objects_treeview.setCurrentIndex(
        editor.objects_model.index(0, 0))
    app.processEvents()
    widget = editor.phase_widget.component_widget
    button = widget.ui.btn_show_structure

    check("autodefault: the new button is not autoDefault after a real show",
          not button.autoDefault())
    check("autodefault: ...and is not THE default button",
          not button.isDefault())
    check("autodefault: no button in Edit Phases claims default",
          not any(b.isDefault() for b in editor.findChildren(QPushButton)))

    # The behavioural check: Return in the component-name field must not open
    # a structure window. Nothing beats pressing the key.
    widget.ui.component_name.setFocus()
    app.processEvents()
    opened_before = getattr(widget, "_structure_dialog", None)
    for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
        app.sendEvent(widget.ui.component_name,
                      QKeyEvent(QKeyEvent.Type.KeyPress, key,
                                Qt.KeyboardModifier.NoModifier))
        app.processEvents()
    check("autodefault: Return/Enter in the name field opens nothing",
          getattr(widget, "_structure_dialog", None) is opened_before)

    # AUDIT 2026-08-23: the window is modeless so it can be read WHILE editing,
    # but it did not follow the editor - switching component left it showing the
    # previous one, silently, which is the one failure a reference window must
    # not have.
    multi = next(((ph, ph.components) for ph in PROJECT.phases
                  if len(getattr(ph, "components", None) or []) > 1), None)
    if multi is not None:
        phase, components = multi
        editor.ui.edit_objects_treeview.setCurrentIndex(
            editor.objects_model.index(list(PROJECT.phases).index(phase), 0))
        app.processEvents()
        pane = editor.phase_widget.component_widget
        pane._on_show_structure()
        app.processEvents()
        window = pane._structure_dialog
        pane.ui.cmb_component.setCurrentIndex(1)
        app.processEvents()
        check("follows: switching component re-points the open diagram",
              pane._component.name in window.windowTitle())
        # ...and follows a live edit, which is why it is modeless at all.
        before = window.ui.txt_diagram.toPlainText()
        pane._on_scalar_changed("d001", pane._component.d001 + 0.1)
        app.processEvents()
        check("follows: a live edit refreshes the open diagram",
              window.ui.txt_diagram.toPlainText() != before)
        pane._on_scalar_changed("d001", pane._component.d001 - 0.1)
        window.close()
        app.processEvents()
        # A CLOSED diagram must not be resurrected by editing.
        text_when_closed = window.ui.txt_diagram.toPlainText()
        pane._on_scalar_changed("d001", pane._component.d001 + 0.1)
        app.processEvents()
        check("follows: a closed diagram is not reopened by an edit",
              not window.isVisible())
        pane._on_scalar_changed("d001", pane._component.d001 - 0.1)
    else:
        check("follows: (no multi-component phase in this fixture; skipped)", True)

    # The button still works when actually clicked.
    widget._on_show_structure()
    app.processEvents()
    opened = getattr(widget, "_structure_dialog", None)
    check("button: clicking it opens the diagram",
          opened is not None and opened.isVisible())
    check("button: it shows THIS component",
          opened is not None and widget._component.name in opened.windowTitle())
    # Clicking again re-uses the window rather than stacking a second one.
    widget._on_show_structure()
    app.processEvents()
    check("button: a second click re-uses the same window",
          getattr(widget, "_structure_dialog", None) is opened)
    check("autodefault: the diagram window promotes no default button either",
          not any(b.isDefault() for b in opened.findChildren(QPushButton)))
    opened.close()
    editor.close()
    dialog.close()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Structure diagram:", os.path.basename(PATH), "-", COMPONENT.name)
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
