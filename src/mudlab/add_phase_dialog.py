"""Add Phase dialog. Design: ui/add_phase.ui.

Ported from the GTK AddPhaseView (phases/glade/addphase.glade). Modal,
like the old view: choose between a new empty phase, a default phase from
the catalog, or a raw pattern phase.

All three paths are wired: an empty phase, a default phase from the built-in
catalog (calculations in file_parsers/default_catalog.py - the ported
generate_default_phases recipe, built in memory from the bundled `.cmp`
components), or a raw-pattern phase.

A raw-pattern phase has no structure (it carries a measured pattern), so the
G / R controls do not apply to it - selecting it disables the empty-phase
container. The pattern itself is imported afterwards in the phase editor.

Reichweite offers R0 (random, any component count) and R1 (nearest-
neighbour ordering). Only R1G2 is modeled, so choosing R1 locks G to 2;
R2+ is not ported. The empty-phase factory (Phase.create_empty) builds the
matching probability model.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QWidget

from mudlab.file_parsers.default_catalog import default_catalog_entries
from mudlab.ui.ui_add_phase import Ui_AddPhaseDialog


class AddPhaseDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_AddPhaseDialog()
        self.ui.setupUi(self)

        # The built-in default-phase catalog (ready-made reference clays). The
        # entries MudLab2 can model (R0 / R1G2) are offered; picking one builds
        # the phase-set in memory from the bundled components.
        self._catalog = [name for name, _descr in default_catalog_entries()]
        self.ui.cmb_default_phases.addItems(self._catalog)

        self.ui.rdb_empty_phase.setChecked(True)
        self.ui.rdb_default_phase.setEnabled(bool(self._catalog))
        self.ui.rdb_default_phase.setToolTip(
            "A ready-made reference clay from the built-in catalog."
        )
        self.ui.rdb_raw_pattern.setToolTip(
            "A phase built from a measured pattern (imported in the editor)."
        )
        # The old app regenerated the on-disk .phs catalog; MudLab2 builds it in
        # memory from the bundled components, so there is nothing to regenerate.
        self.ui.btn_generate_phases.setEnabled(False)
        self.ui.btn_generate_phases.setToolTip(
            "The catalog is built in; there is nothing to regenerate."
        )

        for radio in (
            self.ui.rdb_empty_phase,
            self.ui.rdb_default_phase,
            self.ui.rdb_raw_pattern,
        ):
            radio.toggled.connect(self._update_sensitivities)
        # Modeled stacking: R0 (any G) and R1G2. Offer R 0-1; R2+ is not
        # ported, and R1 exists only for 2 components (R1G2), so R=1 locks G=2.
        self.ui.R.setRange(0, 1)
        self.ui.R.setValue(0)
        self.ui.R.setToolTip(
            "R0 (random, any component count) and R1 (nearest-neighbour "
            "ordering, 2 components) are modeled. R2+ is not ported yet."
        )
        self.ui.R.valueChanged.connect(self._on_R_changed)
        self._update_sensitivities()
        self._on_R_changed(self.ui.R.value())

        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

    # ------------------------------------------------------------------
    # Result accessors (old: get_phase_type / get_G / get_R)
    # ------------------------------------------------------------------
    @property
    def phase_type(self) -> str:
        if self.ui.rdb_empty_phase.isChecked():
            return "empty"
        if self.ui.rdb_default_phase.isChecked():
            return "default"
        return "raw"

    @property
    def G(self) -> int:
        return self.ui.G.value()

    @property
    def R(self) -> int:
        return self.ui.R.value()

    @property
    def default_phase(self) -> str:
        return self.ui.cmb_default_phases.currentText()

    def _update_sensitivities(self) -> None:
        self.ui.cont_empty_phase.setEnabled(self.ui.rdb_empty_phase.isChecked())
        self.ui.cont_default_phase.setEnabled(self.ui.rdb_default_phase.isChecked())

    def _on_R_changed(self, R: int) -> None:
        """R1 is modeled only for 2 components (R1G2), so R=1 locks G to 2;
        R0 allows the full 1-6 range."""
        if R >= 1:
            self.ui.G.setRange(2, 2)
            self.ui.G.setValue(2)
            self.ui.G.setEnabled(False)
            self.ui.G.setToolTip("R1 is modeled for 2 components only (R1G2).")
        else:
            self.ui.G.setRange(1, 6)
            self.ui.G.setEnabled(True)
            self.ui.G.setToolTip("")
