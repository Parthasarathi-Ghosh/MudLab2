"""Edit Specimen dialog logic. The design lives in ui/edit_specimen.ui.

Ported from the GTK SpecimenView (specimen/glade/specimen.glade, notebook
edit_specimen). Modeless and live-applying like the old DialogView:
`bind_specimen()` fills the widgets from a Specimen model and edits write
straight back to it (Qt signals propagate to the dock and plots).
"""

from __future__ import annotations

import os

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHeaderView, QMessageBox, QWidget,
)

from mudlab.file_parsers.xrd_export import EXPORT_FILTERS, save_pattern
from mudlab.file_parsers.xrd_import import PATTERN_FILTERS, parse_pattern
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
    def unbind(self) -> None:
        """Stop writing to the (possibly deleted) specimen."""
        self._specimen = None

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
        self.goniometer.bind_goniometer(specimen.goniometer)

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

        # Experimental / calculated tables are read-only; the exclusion-range
        # table is editable and drives Specimen.set_exclusion_ranges.
        self.exclusion_model.itemChanged.connect(self._on_exclusion_changed)
        self.ui.btn_add_exclusion_range.clicked.connect(self._on_add_exclusion)
        self.ui.btn_del_exclusion_ranges.clicked.connect(self._on_del_exclusion)
        for button in (
            self.ui.btn_import_exclusion_ranges,
            self.ui.btn_export_exclusion_ranges,
        ):
            button.setEnabled(False)
            button.setToolTip("Import/export exclusion ranges is not ported yet.")

        # Experimental / calculated pattern data import + export (through the
        # shared xrd_import / xrd_export dispatchers).
        self.ui.btn_import_experimental_data.clicked.connect(
            self._on_import_experimental)
        self.ui.btn_export_experimental_data.clicked.connect(
            lambda: self._export_pattern("experimental"))
        self.ui.btn_export_calculated_data.clicked.connect(
            lambda: self._export_pattern("calculated"))

    def _fill_pattern_tables(self, specimen: Specimen) -> None:
        # Read-only view of the data; editing/add/remove connect with the
        # pattern model port.
        for model, (x, y) in (
            (self.experimental_model, specimen.experimental_pattern),
            (self.calculated_model, specimen.calculated_pattern),
        ):
            model.removeRows(0, model.rowCount())
            for xi, yi in zip(x, y):
                items = [QStandardItem(f"{xi:.4f}"), QStandardItem(f"{yi:.2f}")]
                for item in items:
                    item.setEditable(False)
                model.appendRow(items)
        self._fill_exclusion_table(specimen)

    def _on_import_experimental(self) -> None:
        """Replace this specimen's experimental pattern from a data file (any
        format the shared importer reads)."""
        if self._specimen is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import experimental pattern", "", PATTERN_FILTERS
        )
        if not path:
            return
        try:
            x, y = parse_pattern(path)
        except Exception as exc:
            QMessageBox.warning(
                self, "Import pattern", "Could not read:\n%s\n\n%s" % (path, exc)
            )
            return
        self._specimen.set_experimental_pattern(x, y)
        self._fill_pattern_tables(self._specimen)

    def _export_pattern(self, which: str) -> None:
        """Export the experimental or calculated pattern to a .xy / .uxd file."""
        if self._specimen is None:
            return
        x, y = (self._specimen.experimental_pattern if which == "experimental"
                else self._specimen.calculated_pattern)
        if len(x) < 1:
            QMessageBox.information(
                self, "Export pattern",
                "There is no %s pattern to export." % which,
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export %s pattern" % which, "", EXPORT_FILTERS
        )
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".xy"
        try:
            save_pattern(path, x, y, goniometer=self._specimen.goniometer,
                         name=getattr(self._specimen, "name", ""))
        except Exception as exc:
            QMessageBox.critical(
                self, "Export pattern",
                "Could not export:\n%s\n\n%s" % (path, exc),
            )

    def _fill_exclusion_table(self, specimen: Specimen) -> None:
        self._updating = True
        try:
            self.exclusion_model.removeRows(0, self.exclusion_model.rowCount())
            for a, b in specimen.exclusion_ranges:
                self.exclusion_model.appendRow(
                    [QStandardItem(f"{a:.4f}"), QStandardItem(f"{b:.4f}")]
                )
        finally:
            self._updating = False

    # ------------------------------------------------------------------
    # Exclusion ranges
    # ------------------------------------------------------------------
    def _on_add_exclusion(self) -> None:
        if self._specimen is None:
            return
        self._updating = True
        try:
            self.exclusion_model.appendRow(
                [QStandardItem("0.0000"), QStandardItem("0.0000")]
            )
        finally:
            self._updating = False
        self._commit_exclusions()

    def _on_del_exclusion(self) -> None:
        if self._specimen is None:
            return
        rows = sorted(
            {i.row() for i in self.ui.specimen_exclusion_ranges.selectionModel().selectedRows()},
            reverse=True,
        )
        for row in rows:
            self.exclusion_model.removeRow(row)
        if rows:
            self._commit_exclusions()

    def _on_exclusion_changed(self, _item) -> None:
        if not self._updating:
            self._commit_exclusions()

    def _commit_exclusions(self) -> None:
        """Read every row back into Specimen.set_exclusion_ranges (which emits
        data_changed -> stats + plot refresh). Malformed rows are skipped."""
        if self._specimen is None:
            return
        ranges = []
        for row in range(self.exclusion_model.rowCount()):
            a_item = self.exclusion_model.item(row, 0)
            b_item = self.exclusion_model.item(row, 1)
            if a_item is None or b_item is None:
                continue
            try:
                ranges.append((float(a_item.text()), float(b_item.text())))
            except ValueError:
                continue
        self._specimen.set_exclusion_ranges(ranges)
