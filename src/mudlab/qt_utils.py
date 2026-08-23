"""Small Qt helpers shared by the dialogs."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QDialog, QDialogButtonBox, QPushButton,
)


def clear_auto_default(root, keep_button_box: bool = True) -> int:
    """Stop Enter from firing a button that nobody asked it to.

    Qt gives ``autoDefault`` to every QPushButton with a QDialog ancestor (also
    on reparenting), and on show it promotes one to THE default - so Return in
    any field that does not consume it activates that button. Which button wins
    is just tab order, and in this app the winner kept being a destructive one:
    **Add** in Edit Phases / Mixtures / Atom Types / Markers, and **Refine** in
    the refinement window, where a stray Return started a run that rewrites the
    model and can take minutes.

    A button box's **AcceptRole** button (OK / Save) is LEFT ALONE: there, Enter
    activating OK is the standard behaviour a modal form should have, and the
    role is the app's own declaration that the dialog has an accept action.

    Only AcceptRole. Sparing every button-box button was tried and was wrong:
    the editor dialogs' boxes hold a lone **Close (RejectRole)**, which Qt then
    promoted, so Enter shut the editor while the user was typing in it - a
    different wrong answer to the same question. Reject / Close already have
    their key, and it is Esc.

    This does NOT change what Enter does inside an input. A QLineEdit still
    commits on Return (editingFinished), a spin box still interprets its text,
    and an item view still commits the cell - measured. Firing a button was an
    extra effect layered on top, never the thing that saved the value.

    Returns how many buttons were changed, which is what a test can assert on.
    """
    changed = 0
    for button in root.findChildren(QPushButton):
        if button.autoDefault() or button.isDefault():
            button.setAutoDefault(False)
            button.setDefault(False)
            changed += 1
    # Clear everything, then hand it back to the accept button - rather than
    # excluding it from the sweep. Excluding needs to recognise "the same
    # button" across two lookups, and an id()-keyed set is UNSOUND here: the
    # wrappers `buttons()` yields are temporaries, so CPython frees one and
    # reuses its address for the next, and the set ends up sparing the wrong
    # button (measured: it spared Cancel and cleared OK). Setting the flag
    # explicitly needs no identity comparison at all.
    if keep_button_box:
        accept = QDialogButtonBox.ButtonRole.AcceptRole
        for box in root.findChildren(QDialogButtonBox):
            for button in box.buttons():
                if box.buttonRole(button) == accept:
                    button.setAutoDefault(True)
                    button.setDefault(True)
    return changed


class _EnterPolicy(QObject):
    """Applies `clear_auto_default` to this app's dialogs, on every show.

    An application-wide filter rather than a call in each dialog: the trap is a
    property of Qt, not of any one dialog, so a per-dialog call is a rule
    someone has to remember for every dialog ever added - and it was already
    missed four times. Filtering on Show also runs AFTER the whole construction
    chain, so it catches buttons a subclass (or a late rebind) adds.

    Scoped to this project's own dialogs: Qt's own (QMessageBox, QFileDialog)
    are left exactly as Qt intends.
    """

    def eventFilter(self, obj, event) -> bool:
        if (event.type() == QEvent.Type.Show
                and isinstance(obj, QDialog)
                and type(obj).__module__.startswith("mudlab")):
            clear_auto_default(obj)
        return False


_ENTER_POLICY: _EnterPolicy | None = None


def install_enter_policy(app) -> "_EnterPolicy":
    """Install the Enter policy on `app` (idempotent).

    Called once at start-up. The policy is: Enter accepts only where a
    QDialogButtonBox declares an AcceptRole button; otherwise it commits the
    field you are in and does nothing else; Esc always closes.
    """
    global _ENTER_POLICY
    if _ENTER_POLICY is None:
        _ENTER_POLICY = _EnterPolicy()
        app.installEventFilter(_ENTER_POLICY)
    return _ENTER_POLICY


class ColorButton:
    """Make a plain QPushButton behave like a color swatch button.

    The button shows the current color and its hex code; clicking opens the
    native color dialog. (Replaces the old GtkColorButton.) The initial
    color is read from the button text set in the .ui file. `on_change` is
    called with the new QColor after a user pick (not on programmatic
    set_color, so filling a dialog from a model does not echo back).
    """

    def __init__(self, button: QPushButton, on_change=None) -> None:
        self._button = button
        self.on_change = on_change
        color = QColor(button.text())
        self._color = color if color.isValid() else QColor("#000000")
        self._apply()
        button.clicked.connect(self._pick)

    @property
    def color(self) -> QColor:
        return QColor(self._color)

    def hex(self) -> str:
        return self._color.name()

    def set_color(self, color: QColor | str) -> None:
        color = QColor(color)
        if color.isValid():
            self._color = color
            self._apply()

    def _pick(self) -> None:
        color = QColorDialog.getColor(
            self._color, self._button.window(), "Select color"
        )
        if color.isValid():
            self._color = color
            self._apply()
            if self.on_change is not None:
                self.on_change(QColor(color))

    def _apply(self) -> None:
        luminance = (
            0.299 * self._color.red()
            + 0.587 * self._color.green()
            + 0.114 * self._color.blue()
        )
        text_color = "#000000" if luminance > 128 else "#ffffff"
        self._button.setText(self._color.name())
        self._button.setStyleSheet(
            f"background-color: {self._color.name()}; color: {text_color};"
        )
