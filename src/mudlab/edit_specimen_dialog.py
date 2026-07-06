"""Edit Specimen dialog logic. The design lives in ui/edit_specimen.ui.

Ported from the GTK SpecimenView (specimen/glade/specimen.glade, notebook
edit_specimen). Modeless and live-applying like the old DialogView:
`bind_specimen()` fills the widgets from a Specimen model and edits write
straight back to it (Qt signals propagate to the dock and plots).
"""

from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QDialog, QHeaderView, QWidget

from mudlab.goniometer_widget import GoniometerWidget
from mudlab.line_properties_widget import LinePropertiesWidget
from mudlab.models import Specimen
from mudlab.ui.ui_edit_specimen import Ui_EditSpecimenDialog


class EditSpecimenDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditSpecimenDialog()
        self.ui.setupUi(self)

        self._specimen: Specimen | None = None
        self._updating = False

        # Inline line-properties components (old: event boxes receiving the
        # Experimental/CalculatedLinePropertiesView glade views).
        self.exp_line = LinePropertiesWidget(self, with_cap=True, default_color="#000000")
        self.ui.expLineLayout.addWidget(self.exp_line)
        self.calc_line = LinePropertiesWidget(self, with_cap=False, default_color="#FF0000")
        self.ui.calcLineLayout.addWidget(self.calc_line)

        # Inline goniometer setup (old: InlineGoniometerView event box).
        self.goniometer = GoniometerWidget(self)
        self.ui.goniometerLayout.addWidget(self.goniometer)

        self._setup_pattern_tables()
        self._connect_editors()

        self.ui.buttonBox.rejected.connect(self.reject)

    # ------------------------------------------------------------------
    # Model binding (live apply, old adapter behavior)
    # ------------------------------------------------------------------
    def bind_specimen(self, specimen: Specimen) -> None:
        self._specimen = specimen
        self._updating = True
        try:
            self.ui.specimen_name.setText(specimen.name)
            self.ui.specimen_sample_name.setText(specimen.sample_name)
            self.ui.specimen_source.setPlainText(specimen.source)
            for checkbox, prop in self._checkbox_props():
                checkbox.setChecked(getattr(specimen, prop))
            self.ui.display_vshift_spb.setValue(specimen.display_vshift)
            self.ui.display_vscale_spb.setValue(specimen.display_vscale)
            self.ui.display_residual_scale_spb.setValue(specimen.display_residual_scale)
        finally:
            self._updating = False
        self._fill_pattern_tables(specimen)

    def _checkbox_props(self):
        return (
            (self.ui.specimen_display_experimental, "display_experimental"),
            (self.ui.specimen_display_calculated, "display_calculated"),
            (self.ui.specimen_display_phases, "display_phases"),
            (self.ui.specimen_display_derivatives, "display_derivatives"),
            (self.ui.specimen_display_residuals, "display_residuals"),
            (self.ui.specimen_display_stats_in_lbl, "display_stats_in_lbl"),
        )

    def _connect_editors(self) -> None:
        self.ui.specimen_name.textChanged.connect(
            lambda text: self._write("name", text)
        )
        self.ui.specimen_sample_name.textChanged.connect(
            lambda text: self._write("sample_name", text)
        )
        self.ui.specimen_source.textChanged.connect(
            lambda: self._write("source", self.ui.specimen_source.toPlainText())
        )
        for checkbox, prop in self._checkbox_props():
            checkbox.toggled.connect(
                lambda checked, p=prop: self._write(p, checked)
            )
        self.ui.display_vshift_spb.valueChanged.connect(
            lambda value: self._write("display_vshift", value)
        )
        self.ui.display_vscale_spb.valueChanged.connect(
            lambda value: self._write("display_vscale", value)
        )
        self.ui.display_residual_scale_spb.valueChanged.connect(
            lambda value: self._write("display_residual_scale", value)
        )

    def _write(self, prop: str, value) -> None:
        if self._specimen is not None and not self._updating:
            setattr(self._specimen, prop, value)

    # ------------------------------------------------------------------
    # Pattern tables
    # ------------------------------------------------------------------
    def _setup_pattern_tables(self) -> None:
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

    def _fill_pattern_tables(self, specimen: Specimen) -> None:
        # Read-only view of the data; editing/add/remove connect with the
        # pattern model port.
        for model, (x, y) in (
            (self.experimental_model, specimen.experimental_pattern),
            (self.calculated_model, specimen.calculated_pattern),
        ):
            model.removeRows(0, model.rowCount())
            for xi, yi in zip(x, y):
                model.appendRow(
                    [QStandardItem(f"{xi:.4f}"), QStandardItem(f"{yi:.2f}")]
                )
