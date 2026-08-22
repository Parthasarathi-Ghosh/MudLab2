"""Compositions dialog. Design: ui/composition.ui.

Ported from the old edit_mixture_controller.on_composition_clicked, which popped
a modal window showing the mixture's oxide composition (one column per specimen,
one row per oxide) with a CSV export. Here the same table is shown in a Qt
QTableWidget and can be copied to the clipboard or exported to a .csv file.

Opened modally from the Edit Mixtures editor's Composition button for the bound
mixture. Read-only - it reports what calculations.composition computes, it does
not edit the mixture.

Two optional COMPARISON columns sit beside the modelled ones:
  - the measured (XRF) analysis imported through Data -> Import composition,
    normalised to 100% so it is comparable with a modelled column;
  - the "default state" - what each specimen's composition would be if every
    phase were still as the catalog ships it, weighted by the fractions the fit
    found. That is what shows whether refinement changed the CHEMISTRY (atom
    relations rewrite occupancies; stacking probabilities change the component
    weights) rather than only the pattern.
Both are off by default, so the dialog opens exactly as it always has.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QMessageBox, QTableWidgetItem, QWidget,
)

from mudlab.calculations.composition import (
    bulk_composition, composition_to_csv, mixture_composition, mixture_has_nonclay,
)
from mudlab.default_state import (
    default_state_composition, structural_phases, unmapped_phases,
)
from mudlab.ui.ui_composition import Ui_CompositionDialog


class CompositionDialog(QDialog):
    def __init__(self, mixture, parent: QWidget | None = None,
                 project=None) -> None:
        super().__init__(parent)
        # Free the dialog when it closes instead of leaving it parented to the
        # mixture editor - otherwise each Composition click leaks one hidden
        # dialog for the editor's lifetime. Safe because exec() does not touch
        # the dialog after it returns.
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.ui = Ui_CompositionDialog()
        self.ui.setupUi(self)
        self._mixture = mixture
        # The comparison columns are project-level data (the measured analysis
        # and the default-phase map). Without a project the dialog still works
        # exactly as before - the extra controls simply stay disabled.
        self._project = project

        name = getattr(mixture, "name", "") or "mixture"
        self.setWindowTitle("Composition - %s" % name)
        # The bulk (non-clay-inclusive) view is only meaningful when the mixture
        # has a non-clay phase; default is the clay-only view (unchanged).
        self.ui.chk_bulk.setEnabled(mixture_has_nonclay(mixture))
        self.ui.chk_bulk.toggled.connect(self._update_comparison_controls)
        self.ui.chk_bulk.toggled.connect(self._refresh)
        self.ui.chk_measured.toggled.connect(self._refresh)
        self.ui.chk_default.toggled.connect(self._refresh)
        self.ui.btn_default_phases.clicked.connect(self._on_default_phases)
        self._update_comparison_controls()
        self._refresh()

        self.ui.btn_copy.clicked.connect(self._on_copy)
        self.ui.btn_export.clicked.connect(self._on_export)
        self.ui.btn_close.clicked.connect(self.accept)

    def _refresh(self, *_args) -> None:
        """Recompute for the current view (clay-only, or bulk incl. non-clays)
        and repopulate the table."""
        if self.ui.chk_bulk.isChecked():
            self._specimen_names, self._oxide_rows = bulk_composition(self._mixture)
            self.ui.lbl_title.setText(
                "Bulk oxide composition incl. non-clay phases (wt%):")
        else:
            self._specimen_names, self._oxide_rows = mixture_composition(self._mixture)
            self.ui.lbl_title.setText(
                "Oxide composition of the specimens in this mixture (wt%):")
        self._append_comparison_columns()
        self._populate()

    # ------------------------------------------------------------------
    # Comparison columns (measured XRF / default-phase state)
    # ------------------------------------------------------------------
    def _update_comparison_controls(self) -> None:
        """Enable each comparison only when the data behind it exists, and say
        why in the tooltip when it does not - a checkbox that silently does
        nothing is worse than one that is greyed with a reason."""
        project = self._project
        measured = getattr(project, "composition", None) if project else None
        has_measured = measured is not None and not measured.is_empty()
        self.ui.chk_measured.setEnabled(has_measured)
        if not has_measured:
            self.ui.chk_measured.setChecked(False)
            self.ui.chk_measured.setToolTip(
                "No measured composition in this project - import one from "
                "Data > Import composition.")

        phases = structural_phases(project) if project else []
        self.ui.btn_default_phases.setEnabled(bool(phases))
        mapped = bool(getattr(project, "default_phase_map", None)) if project else False
        # The bulk view weights each phase by fraction alone; the clay-only view
        # weights by fraction x formula mass. The default-state column is
        # computed the clay-only way, so showing it beside bulk columns would
        # put two different conventions in one table.
        bulk = self.ui.chk_bulk.isChecked()
        self.ui.chk_default.setEnabled(mapped and not bulk)
        if not mapped:
            self.ui.chk_default.setChecked(False)
            self.ui.chk_default.setToolTip(
                "State which default phase each phase started as first "
                "(Default phases...) - it cannot be worked out automatically.")
        elif bulk:
            self.ui.chk_default.setChecked(False)
            self.ui.chk_default.setToolTip(
                "Not available with the bulk view: the two weight the phases "
                "differently, so the columns would not be comparable.")

    def _append_comparison_columns(self) -> None:
        """Add the requested comparison columns to the rows just computed.

        Appended to `self._oxide_rows`, so the table, the clipboard copy and the
        CSV export all show the same thing - there is one set of columns, not a
        view that the export then has to reproduce.
        """
        project = self._project
        if project is None:
            return

        if self.ui.chk_default.isChecked():
            _names, rows = default_state_composition(self._mixture, project)
            if rows:
                by_oxide = {oxide: values for oxide, values in rows}
                for index, (oxide, values) in enumerate(self._oxide_rows):
                    extra = by_oxide.get(oxide) or []
                    self._oxide_rows[index] = (oxide, list(values) + list(extra))
                self._specimen_names = list(self._specimen_names) + [
                    "%s (default)" % name for name in _names
                ]

        if self.ui.chk_measured.isChecked():
            measured = project.composition
            # Normalised: every modelled column is normalised to 100, so a raw
            # analysis totalling 97 would read as a difference that is not real.
            values = measured.normalized()
            for index, (oxide, columns) in enumerate(self._oxide_rows):
                self._oxide_rows[index] = (
                    oxide, list(columns) + [values.get(oxide, 0.0)])
            self._specimen_names = list(self._specimen_names) + [
                "%s (measured)" % (measured.name or "XRF")]

        if not self.ui.chk_default.isChecked():
            return
        missing = unmapped_phases(project)
        if missing and len(missing) == len(structural_phases(project)):
            # NO default column could be produced at all. Saying "shown at
            # their current state" here would point at a column that is not
            # there - the honest message is that there is nothing to show.
            self.ui.lbl_title.setText(
                "%s  -  no default state to show: none of the phases has a "
                "default that can be found (use Default phases...)."
                % self.ui.lbl_title.text())
        elif missing:
            self.ui.lbl_title.setText(
                "%s  -  %d phase(s) have no default stated (%s), so they are "
                "shown at their current state."
                % (self.ui.lbl_title.text(), len(missing),
                   ", ".join(ph.name for ph in missing[:3])))

    def _on_default_phases(self) -> None:
        """State the phase -> default-phase mapping, then refresh."""
        from mudlab.default_phases_dialog import DefaultPhasesDialog

        if self._project is None:
            return
        dialog = DefaultPhasesDialog(self._project, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.mapping is None:
            return
        self._project.set_default_phase_map(dialog.mapping)
        self._update_comparison_controls()
        if dialog.mapping:
            self.ui.chk_default.setChecked(True)
        self._refresh()

    def _populate(self) -> None:
        table = self.ui.tbl_composition
        table.setColumnCount(len(self._specimen_names))
        table.setRowCount(len(self._oxide_rows))
        table.setHorizontalHeaderLabels(self._specimen_names)
        table.setVerticalHeaderLabels([oxide for oxide, _ in self._oxide_rows])
        align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        for i, (_oxide, pcts) in enumerate(self._oxide_rows):
            for j, pct in enumerate(pcts):
                item = QTableWidgetItem("%.1f" % pct)
                item.setTextAlignment(align)
                table.setItem(i, j, item)
        table.resizeColumnsToContents()

    # ------------------------------------------------------------------
    def _csv_text(self) -> str:
        return composition_to_csv(self._specimen_names, self._oxide_rows)

    def _on_copy(self) -> None:
        QApplication.clipboard().setText(self._csv_text())

    def _on_export(self) -> None:
        name = (getattr(self._mixture, "name", "") or "composition").strip()
        path, _filter = QFileDialog.getSaveFileName(
            self, "Export composition", "%s composition.csv" % name,
            "CSV files (*.csv);;All files (*)",
        )
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".csv"
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(self._csv_text())
        except OSError as exc:  # surface, don't crash the editor
            QMessageBox.warning(
                self, "Export failed", "Could not write the file:\n\n%s" % exc)
