"""Ask the two things deriving treatment states cannot work out on its own.

**Which family's gallery to borrow.** Smectite and vermiculite differ by layer
charge, which a single refined structure does not show; di- and tri-octahedral
could be guessed from the octahedral count, but the smectite/vermiculite
distinction cannot, so the whole choice is asked rather than half-guessed.

**Which state the phase is already in.** A CIF is not necessarily air-dried -
the four montmorillonite structures in the reference corpus project to 0.97,
1.11, 1.22 and 1.22 nm, which spans dehydrated to one water layer. The answer
does not change the derived states (they are the glycolated and heated forms
either way); it is recorded in the phase name so the series says what it is.

Built in code rather than from a `.ui` file: it is two combo boxes and a
button box, and the layout carries no design decisions worth a designer file.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout,
)

from mudlab.qt_utils import clear_auto_default
from mudlab.treatment_variants import FAMILIES, STATES, gallery_height, layer_top


class TreatmentStatesDialog(QDialog):
    """Choose the donor family and say what state the base phase is in."""

    def __init__(self, parent=None, phase=None):
        super().__init__(parent)
        self.setWindowTitle("Create treatment states")
        self._phase = phase

        root = QVBoxLayout(self)
        component = (phase.components[0] if phase is not None
                     and getattr(phase, "components", None) else None)
        summary = QLabel(
            "Building the glycolated and heated states of <b>%s</b>.<br>"
            "Its layer is %.3f nm thick with a %.3f nm gallery; the derived "
            "states keep that layer and replace the gallery."
            % (getattr(phase, "name", "this phase"),
               layer_top(component) if component else 0.0,
               gallery_height(component) if component else 0.0)
            if component else "Building the treatment states of this phase.")
        summary.setWordWrap(True)
        root.addWidget(summary)

        form = QFormLayout()
        self.cmb_family = QComboBox()
        for family in FAMILIES:
            self.cmb_family.addItem(family)
        self.cmb_family.setToolTip(
            "Whose gallery to borrow. Smectite and vermiculite differ by layer "
            "charge, which one refined structure does not reveal, so this "
            "cannot be worked out from the file.")
        form.addRow("Gallery from", self.cmb_family)

        self.cmb_state = QComboBox()
        for key, label in STATES:
            self.cmb_state.addItem("%s (%s)" % (label, key), key)
        self.cmb_state.setToolTip(
            "What state this phase is already in. A published structure is "
            "usually air-dried, but not always - the reference montmorillonite "
            "structures span dehydrated to one water layer.")
        form.addRow("This phase is", self.cmb_state)
        root.addLayout(form)

        note = QLabel(
            "The new phases are <i>based on</i> this one and their components "
            "are <i>linked</i> to its component, so refining the layer refines "
            "all three together.")
        note.setWordWrap(True)
        root.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        clear_auto_default(self)
        self.resize(520, 240)

    def family(self) -> str:
        return self.cmb_family.currentText()

    def base_state(self) -> str:
        return self.cmb_state.currentData() or "1WAT"
