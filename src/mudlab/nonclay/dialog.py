"""Read-only non-clay decomposition dialog (EXPERIMENTAL, Slice 2).

Mirrors CompositionDialog: it reports what mudlab.nonclay computes and NEVER
edits the mixture. The user loads measured non-clay reference curves and runs the
Case-A decomposition; the results are an intensity share (semi-quantitative), not
weight %. Delete src/mudlab/nonclay/ to retract the whole feature.

Deferred to Slice 2b (Finding 31): CIF/.str reference construction via the
goniometer, XRF mass-balance weight %, and the Si absolute scale. This first cut
covers measured references + the residual decomposition + detection.
"""

from __future__ import annotations

import csv
import io
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFileDialog, QLabel,
    QListWidgetItem, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from mudlab.calculations.composition import load_conversion_table
from mudlab.nonclay.chemistry import mass_balance, mineral_composition
from mudlab.nonclay.decompose import decompose_mixture
from mudlab.nonclay.references import load_reference
from mudlab.nonclay.structure import reference_from_cif
from mudlab.nonclay.ui_nonclay import Ui_NonclayDialog

_PATTERN_FILTER = (
    "Pattern files (*.xy *.txt *.dat *.csv *.xrdml *.raw *.rasx *.uxd);;"
    "All files (*)"
)


def _normalize_composition(raw):
    """Drop non-positive oxides and normalise the rest to 100 wt% (the pure-phase
    convention the mass balance uses). Returns {} if nothing positive."""
    kept = {ox: v for ox, v in raw.items() if v > 0}
    total = sum(kept.values())
    if not total:
        return {}
    return {ox: 100.0 * v / total for ox, v in kept.items()}


def _edit_composition(parent, oxides, current, name):
    """Modal editor for a reference's oxide wt%. Returns the normalised dict, {}
    (cleared), or None (cancelled)."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("Composition - %s" % name)
    layout = QVBoxLayout(dlg)
    hint = QLabel("Oxide wt % of the pure mineral (normalised to 100 on OK):")
    hint.setWordWrap(True)
    layout.addWidget(hint)
    table = QTableWidget(len(oxides), 1)
    table.setHorizontalHeaderLabels(["wt %"])
    table.setVerticalHeaderLabels(list(oxides))
    for i, ox in enumerate(oxides):
        text = ("%.2f" % current[ox]) if ox in current else ""
        table.setItem(i, 0, QTableWidgetItem(text))
    layout.addWidget(table)
    box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    layout.addWidget(box)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    raw = {}
    for i, ox in enumerate(oxides):
        item = table.item(i, 0)
        text = item.text().strip() if item is not None else ""
        if not text:
            continue
        try:
            raw[ox] = float(text)
        except ValueError:
            continue
    return _normalize_composition(raw)


class NonclayDialog(QDialog):
    def __init__(self, mixture, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Free the dialog when it closes (as CompositionDialog does).
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.ui = Ui_NonclayDialog()
        self.ui.setupUi(self)
        self._mixture = mixture
        self._references: list = []
        self._compositions: list = []
        self._result = None
        self._massbalance = None

        name = getattr(mixture, "name", "") or "mixture"
        self.setWindowTitle("Non-clay decomposition - %s" % name)
        self._setup_xrf_table()

        self.ui.btn_add_ref.clicked.connect(self._on_add)
        self.ui.btn_add_cif.clicked.connect(self._on_add_cif)
        self.ui.btn_edit_comp.clicked.connect(self._on_edit_composition)
        self.ui.btn_remove_ref.clicked.connect(self._on_remove)
        self.ui.btn_run.clicked.connect(self._on_run)
        self.ui.btn_copy.clicked.connect(self._on_copy)
        self.ui.btn_export.clicked.connect(self._on_export)
        self.ui.btn_close.clicked.connect(self.accept)
        self._set_results_enabled(False)

    # ------------------------------------------------------------------
    def _set_results_enabled(self, on: bool) -> None:
        self.ui.btn_copy.setEnabled(on)
        self.ui.btn_export.setEnabled(on)

    def _setup_xrf_table(self) -> None:
        """One editable wt% cell per reporting oxide (optional user input)."""
        self._xrf_oxides = [n for n, _f in load_conversion_table().values()]
        table = self.ui.tbl_xrf
        table.setColumnCount(1)
        table.setRowCount(len(self._xrf_oxides))
        table.setHorizontalHeaderLabels(["wt %"])
        table.setVerticalHeaderLabels(self._xrf_oxides)
        for i in range(len(self._xrf_oxides)):
            table.setItem(i, 0, QTableWidgetItem(""))
        table.resizeColumnsToContents()

    def _read_xrf(self) -> dict:
        out = {}
        for i, oxide in enumerate(self._xrf_oxides):
            item = self.ui.tbl_xrf.item(i, 0)
            text = item.text().strip() if item is not None else ""
            if not text:
                continue
            try:
                out[oxide] = float(text)
            except ValueError:
                continue
        return out

    def add_reference(self, reference, composition=None) -> None:
        """Add a reference plus its oxide composition (for the mass balance). A
        CIF-derived composition is passed in; otherwise it is matched by name.
        The list shows which oxides each reference contributes (quantifiable), or
        '(no composition)'. Used by the UI and the harness."""
        if not composition:
            composition = mineral_composition(getattr(reference, "name", ""))
        self._references.append(reference)
        self._compositions.append(composition)
        self.ui.list_refs.addItem(
            QListWidgetItem(self._ref_label(reference.name, composition)))

    @staticmethod
    def _ref_label(name, composition):
        if composition:
            return "%s  [%s]" % (name, ", ".join(sorted(composition)))
        return "%s  (no composition)" % name

    def _on_add(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, "Add non-clay reference", "", _PATTERN_FILTER)
        if not path:
            return
        try:
            ref = load_reference(path)
        except Exception as exc:  # surface, don't crash
            QMessageBox.warning(self, "Could not load reference", "%s" % exc)
            return
        self.add_reference(ref)

    def _on_add_cif(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, "Add non-clay reference from a structure", "",
            "Structure files (*.cif);;All files (*)")
        if not path:
            return
        specs = [s for s in self._mixture.specimens if s is not None]
        if not specs:
            QMessageBox.warning(
                self, "No specimen", "The mixture has no specimen goniometer to "
                "build the reference with.")
            return
        try:
            ref, composition = reference_from_cif(path, specs[0].goniometer)
        except Exception as exc:  # surface the ValueError message
            QMessageBox.warning(
                self, "Could not build reference from CIF", "%s" % exc)
            return
        self.add_reference(ref, composition)

    def _on_remove(self) -> None:
        row = self.ui.list_refs.currentRow()
        if row < 0:
            return
        self.ui.list_refs.takeItem(row)
        del self._references[row]
        del self._compositions[row]

    def _on_edit_composition(self) -> None:
        row = self.ui.list_refs.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "No reference", "Select a reference in the list first.")
            return
        current = self._compositions[row] or {}
        comp = _edit_composition(
            self, self._xrf_oxides, current, self._references[row].name)
        if comp is None:  # cancelled
            return
        self._compositions[row] = comp or None
        self.ui.list_refs.item(row).setText(
            self._ref_label(self._references[row].name, comp))

    def run(self) -> None:
        """Recompute the clay fit (read-only), decompose against the loaded
        references, and (if XRF oxides were entered) compute the weight-% mass
        balance. Also the public entry the harness drives."""
        self._mixture.calculate()  # make the residual current; does not refit
        self._result = decompose_mixture(self._mixture, self._references, detect=True)
        xrf = self._read_xrf()
        self._massbalance = (
            mass_balance(self._mixture, xrf, self._references, self._compositions)
            if xrf else None)
        self._populate()
        self._set_results_enabled(True)

    def _on_run(self) -> None:
        if not self._references:
            QMessageBox.information(
                self, "No references", "Add at least one non-clay reference first.")
            return
        self.run()

    # ------------------------------------------------------------------
    def _populate(self) -> None:
        res = self._result
        specs, refs = res.specimens, res.reference_names
        table = self.ui.tbl_results
        table.setColumnCount(len(specs))
        table.setRowCount(len(refs))
        table.setHorizontalHeaderLabels([s.name for s in specs])
        table.setVerticalHeaderLabels(list(refs))
        align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        for i in range(len(refs)):
            for j, sr in enumerate(specs):
                rr = sr.references[i]
                item = QTableWidgetItem(
                    "%.2f%% %s" % (rr.pct, "✓" if rr.detected else "–"))
                item.setTextAlignment(align)
                table.setItem(i, j, item)
        table.resizeColumnsToContents()

        rp = ", ".join("%s Rp %.1f" % (s.name, s.rp) for s in specs)
        tot = ", ".join("%s %.1f%%" % (s.name, s.nonclay_pct) for s in specs)
        parts = []
        mb = self._massbalance
        if mb is not None:
            wpct = dict(zip(mb.components, mb.weight_pct))
            nonclay = ", ".join("%s %.1f wt%%" % (n, wpct[n])
                                for n in mb.components if n != "clay")
            parts.append(
                "WEIGHT %% (XRF mass balance): %s vs clay %.1f wt%%. "
                "Unexplained oxides %.1f%% - improve the clay Fe/Mg atom types."
                % (nonclay or "(no known non-clay composition)",
                   wpct.get("clay", 0.0), mb.unexplained_pct))
        parts.append("Clay fit: %s.   XRD intensity share (non-clay): %s." % (rp, tot))
        parts.append("The XRD share is semi-quantitative (orientation-biased low); "
                     "the XRF weight % is orientation-independent. "
                     "✓ = detected above the mis-registration null.")
        self.ui.lbl_summary.setText("   ".join(parts))

    # ------------------------------------------------------------------
    def _csv_text(self) -> str:
        if not self._result:
            return ""
        res = self._result
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["reference", *[s.name for s in res.specimens]])
        for i, ref_name in enumerate(res.reference_names):
            row = [ref_name]
            for sr in res.specimens:
                rr = sr.references[i]
                row.append("%.2f%s" % (rr.pct, " (detected)" if rr.detected else ""))
            writer.writerow(row)
        mb = self._massbalance
        if mb is not None:
            writer.writerow([])
            writer.writerow(["weight % (XRF mass balance)"])
            for comp_name, wp in zip(mb.components, mb.weight_pct):
                writer.writerow([comp_name, "%.1f" % wp])
            writer.writerow(["unexplained oxides %", "%.1f" % mb.unexplained_pct])
        return buffer.getvalue()

    def _on_copy(self) -> None:
        QApplication.clipboard().setText(self._csv_text())

    def _on_export(self) -> None:
        name = (getattr(self._mixture, "name", "") or "nonclay").strip()
        path, _filter = QFileDialog.getSaveFileName(
            self, "Export non-clay results", "%s nonclay.csv" % name,
            "CSV files (*.csv);;All files (*)")
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".csv"
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(self._csv_text())
        except OSError as exc:
            QMessageBox.warning(
                self, "Export failed", "Could not write the file:\n\n%s" % exc)
