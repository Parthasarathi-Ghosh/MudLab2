"""Keep-vs-revert prompt for an explicit inheritance detach.

When the user detaches a phase from its based_on reference (or a component from
its linked template) in the editors, the inherited values would otherwise snap
back to this object's own (often stale) stored values. This offers the choice:

  - "keep"   - bake the values it is currently showing into own storage first
               (snapshot_inherited), so nothing visibly changes;
  - "revert" - the old behaviour: fall back to this object's own stored values;
  - "cancel" - abort the detach.

The message text is a pure function so it can be unit-tested; the QMessageBox
wrapper is separate.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox


def detach_choice_message(subject: str, source_name: str) -> str:
    """Prompt body for detaching `subject` ("phase" / "component") from
    `source_name` (its based_on / linked template)."""
    src = source_name or "its reference"
    return (
        "This %s currently inherits values from %s.\n\n"
        "Keep those values (they are copied in, so nothing changes), or revert "
        "to this %s's own stored values?"
        % (subject, src, subject)
    )


def ask_detach_choice(parent, subject: str, source_name: str) -> str:
    """Show the keep/revert/cancel prompt. Returns "keep", "revert" or "cancel"."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle("Detach %s" % subject)
    box.setText(detach_choice_message(subject, source_name))
    keep = box.addButton("Keep values", QMessageBox.ButtonRole.AcceptRole)
    revert = box.addButton("Revert to own", QMessageBox.ButtonRole.DestructiveRole)
    cancel = box.addButton(QMessageBox.StandardButton.Cancel)
    box.setDefaultButton(keep)
    box.exec()
    clicked = box.clickedButton()
    if clicked is keep:
        return "keep"
    if clicked is revert:
        return "revert"
    return "cancel"
