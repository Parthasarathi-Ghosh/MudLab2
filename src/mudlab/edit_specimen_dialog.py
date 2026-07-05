"""Edit Specimen dialog logic. The design lives in ui/edit_specimen.ui.

Ported from the GTK SpecimenView (specimen/glade/specimen.glade, notebook
edit_specimen). Modeless like the old DialogView; see ui/WIRING.md for the
field mapping and what remains placeholder until the specimen model exists.
"""

from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QDialog, QHeaderView, QWidget

from mudlab.line_properties_widget import LinePropertiesWidget
from mudlab.ui.ui_edit_specimen import Ui_EditSpecimenDialog


class EditSpecimenDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditSpecimenDialog()
        self.ui.setupUi(self)

        # Inline line-properties components (old: event boxes receiving the
        # Experimental/CalculatedLinePropertiesView glade views).
        self.exp_line = LinePropertiesWidget(self, with_cap=True, default_color="#000000")
        self.ui.expLineLayout.addWidget(self.exp_line)
        self.calc_line = LinePropertiesWidget(self, with_cap=False, default_color="#FF0000")
        self.ui.calcLineLayout.addWidget(self.calc_line)

        self._setup_pattern_tables()

        self.ui.buttonBox.rejected.connect(self.reject)

    def set_specimen_name(self, name: str) -> None:
        self.ui.specimen_name.setText(name)

    def _setup_pattern_tables(self) -> None:
        # Placeholder models until the specimen model is ported (Qt signals).
        self.experimental_model = QStandardItemModel(0, 2, self)
        self.experimental_model.setHorizontalHeaderLabels(["2θ (°)", "Intensity (counts)"])
        self.calculated_model = QStandardItemModel(0, 2, self)
        self.calculated_model.setHorizontalHeaderLabels(["2θ (°)", "Intensity (counts)"])
        self.exclusion_model = QStandardItemModel(0, 2, self)
        self.exclusion_model.setHorizontalHeaderLabels(["From (°2θ)", "To (°2θ)"])

        views_models = (
            (self.ui.specimen_experimental_pattern, self.experimental_model),
            (self.ui.specimen_calculated_pattern, self.calculated_model),
            (self.ui.specimen_exclusion_ranges, self.exclusion_model),
        )
        for view, model in views_models:
            view.setModel(model)
            view.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )

        # A few demo data points so the tables can be judged visually.
        for two_theta, intensity in ((2.0, 45.0), (2.02, 48.0), (2.04, 44.0), (2.06, 51.0)):
            self.experimental_model.appendRow(
                [QStandardItem(f"{two_theta:.2f}"), QStandardItem(f"{intensity:.1f}")]
            )
