"""Import composition dialog. Design: ui/import_composition.ui.

Collects the measured (XRF) oxide analysis for the project's physical sample
and returns a :class:`~mudlab.models.composition.Composition`.

The grid is the SAME `OxideGrid` the non-clay editor and importer use, so the
oxide set is exactly the one the modelled composition reports. That restriction
is the point, not a limitation: an oxide the model can never produce could not
take part in the comparison the analysis exists for.

Opened from Data -> Import composition. It only builds the object; storing it on
the project (and confirming a replacement) is the caller's job, so the dialog
stays reusable and testable without a project.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QWidget

from mudlab.models.composition import Composition
from mudlab.oxide_grid import OxideGrid
from mudlab.ui.ui_import_composition import Ui_ImportCompositionDialog

# An analysis this far from 100 % is more likely a units or transcription slip
# than a real total, so it is worth mentioning - but never blocking: a genuine
# partial analysis (majors only) is a perfectly reasonable thing to enter.
_TOTAL_LOW, _TOTAL_HIGH = 95.0, 105.0
_WARNING_STYLE = "color: #C2410C;"


class ImportCompositionDialog(QDialog):
    def __init__(self, parent: QWidget | None = None,
                 composition: Composition | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_ImportCompositionDialog()
        self.ui.setupUi(self)
        self.composition: Composition | None = None   # set on accept

        self.grid = OxideGrid(self.ui.oxide_grid, on_changed=self._update_total)
        self.ui.lbl_warning.setStyleSheet(_WARNING_STYLE)
        self.ui.lbl_warning.setVisible(False)

        self.ui.button_normalize.clicked.connect(self.grid.normalize)
        self.ui.buttonBox.accepted.connect(self._on_accept)
        self.ui.buttonBox.rejected.connect(self.reject)

        # Editing an existing analysis re-opens on its own values, so the dialog
        # doubles as the editor and the user never retypes a whole analysis to
        # correct one figure.
        if composition is not None:
            self.ui.edit_name.setText(composition.name)
            self.ui.edit_source.setText(composition.source)
            self.grid.set_values(composition.oxides)
            self._existing_uuid = composition.uuid
        else:
            self.ui.edit_name.setText("XRF")
            self._existing_uuid = None

        self._update_total()

    # ------------------------------------------------------------------
    def _update_total(self) -> None:
        """Keep the total, the warning and the OK button in step with the grid.

        OK is refused only for an EMPTY analysis - an all-zero composition has
        nothing to compare and would just be a confusing entry in the project."""
        total = self.grid.total()
        self.ui.lbl_sum.setText("Total: %.2f %%" % total)
        if total <= 0.0:
            message = "Enter at least one oxide value."
        elif not (_TOTAL_LOW <= total <= _TOTAL_HIGH):
            # Terse on purpose: spelled out it wrapped to three lines and
            # pushed the grid up. It is a note, not an error.
            message = ("Totals %.2f %% - fine for a partial analysis; use "
                       "Recompute to 100 %% if it should sum." % total)
        else:
            message = ""
        self.ui.lbl_warning.setText(message)
        self.ui.lbl_warning.setVisible(bool(message))
        ok = self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        if ok is not None:
            ok.setEnabled(total > 0.0)

    def _on_accept(self) -> None:
        values = {name: value for name, value in self.grid.values().items()
                  if value > 0.0}
        if not values:
            return  # OK is disabled in this state; belt and braces
        self.composition = Composition(
            name=self.ui.edit_name.text().strip() or "XRF",
            oxides=values,
            source=self.ui.edit_source.text().strip(),
            # Editing keeps the identity, so anything referring to this analysis
            # still refers to it after a correction.
            uuid_=self._existing_uuid,
        )
        self.accept()
