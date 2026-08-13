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
    QApplication, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from mudlab.calculations.composition import load_conversion_table
from mudlab.file_parsers.xrd_import import parse_pattern
from mudlab.nonclay.chemistry import mass_balance, mineral_composition
from mudlab.nonclay.decompose import decompose_mixture
from mudlab.nonclay.instrument import instrumental_fwhm
from mudlab.nonclay.references import load_reference
from mudlab.nonclay.structure import reference_from_cif, reference_from_str
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
    accepted = dlg.exec() == QDialog.DialogCode.Accepted
    result = None
    if accepted:
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
        result = _normalize_composition(raw)
    dlg.deleteLater()  # free the modal (it is parented to `parent`)
    return result


def modelless_results(specimens, references, width_deg=3.8):
    """Per-specimen model-less fit for the modal + the harness. The baseline width
    is given in DEGREES and converted to points per specimen from its own 2theta
    step. Returns a list of (specimen, areas, shares) - the AREA is the robust
    detector; the SHARE is a relative intensity number, width-dependent, NOT a
    weight % (Findings 32-33)."""
    import numpy as np

    from mudlab.nonclay.estimator import fit_specimen_direct

    out = []
    for s in specimens:
        x = np.asarray(s.experimental_pattern[0], dtype=float)
        step = float(np.median(np.diff(x))) if x.size > 1 else 0.0
        w_pts = max(3, int(round(width_deg / step))) if step else 230
        fit = fit_specimen_direct(s, references, width=w_pts)
        total = fit["a_total"] or 0.0
        areas = [float(a) for a in fit["areas"]]
        shares = [100.0 * a / total if total else 0.0 for a in areas]
        out.append((s, areas, shares))
    return out


def _modelless_dialog(parent, specimens, references) -> None:
    """Modal: the MODEL-LESS fit on specimens with NO clay model (heat-degraded
    clays; identification, not modelling). Strips a morphological baseline from
    the raw pattern and fits the references to the sharp residue. The recovered
    AREA is a detector (tracks a spike 1:1); the SHARE is a relative intensity
    number, NOT a weight % - it moves with the baseline width, so the width is a
    visible control here (Findings 32-33). Weight % still comes from the XRF
    balance. Self-contained + freed on close, so retracting the package removes
    it whole."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("Model-less non-clay - unmodeled / heated specimens")
    dlg.resize(560, 440)
    layout = QVBoxLayout(dlg)
    hint = QLabel(
        "Fit the loaded references to a baseline-stripped raw pattern, for "
        "specimens with NO clay model (heat-degraded clays). The recovered AREA "
        "is a detector (tracks a spike 1:1); the SHARE is a relative intensity "
        "number, NOT a weight % - it depends on the baseline width (try it). "
        "Weight % still comes from the XRF mass balance.")
    hint.setWordWrap(True)
    layout.addWidget(hint)

    lst = QListWidget()
    for s in specimens:
        item = QListWidgetItem(getattr(s, "name", "") or "specimen")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
        lst.addItem(item)
    layout.addWidget(lst)

    controls = QHBoxLayout()
    controls.addWidget(QLabel("Baseline width (deg):"))
    spin = QDoubleSpinBox()
    spin.setRange(0.5, 12.0)
    spin.setSingleStep(0.5)
    spin.setValue(3.8)  # ~230 pts at a 0.0167 deg step (the notes' default)
    controls.addWidget(spin)
    run_btn = QPushButton("Run model-less")
    controls.addWidget(run_btn)
    controls.addStretch(1)
    layout.addLayout(controls)

    table = QTableWidget()
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    layout.addWidget(table)

    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    box.rejected.connect(dlg.reject)
    box.accepted.connect(dlg.accept)
    layout.addWidget(box)

    ref_names = [getattr(r, "name", "ref") for r in references]
    align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

    def _run() -> None:
        chosen = [specimens[i] for i in range(lst.count())
                  if lst.item(i).checkState() == Qt.CheckState.Checked]
        headers = []
        for name in ref_names:
            headers += ["%s area" % name, "%s share" % name]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(chosen))
        table.setVerticalHeaderLabels(
            [getattr(s, "name", "") or "specimen" for s in chosen])
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for r, (_s, areas, shares) in enumerate(
                    modelless_results(chosen, references, spin.value())):
                for k in range(len(references)):
                    ai = QTableWidgetItem("%.1f" % areas[k])
                    ai.setTextAlignment(align)
                    si = QTableWidgetItem("%.2f%%" % shares[k])
                    si.setTextAlignment(align)
                    table.setItem(r, 2 * k, ai)
                    table.setItem(r, 2 * k + 1, si)
        finally:
            QApplication.restoreOverrideCursor()
        table.resizeColumnsToContents()

    run_btn.clicked.connect(_run)
    _run()  # populate immediately (all specimens checked)
    dlg.exec()
    dlg.deleteLater()


class NonclayDialog(QDialog):
    def __init__(self, mixture, parent: QWidget | None = None,
                 extra_specimens=None) -> None:
        super().__init__(parent)
        # Free the dialog when it closes (as CompositionDialog does).
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.ui = Ui_NonclayDialog()
        self.ui.setupUi(self)
        self._mixture = mixture
        # Loose / unmodeled specimens (in the project but not in this mixture,
        # e.g. heat-treated variants) offered to the model-less fit (Findings
        # 32-33). Empty -> the model-less button hides itself.
        self._extra_specimens = [s for s in (extra_specimens or []) if s is not None]
        self._references: list = []
        self._compositions: list = []
        self._result = None
        self._massbalance = None
        self._fwhm = 0.10  # reference peak width (deg); set from a Si standard

        name = getattr(mixture, "name", "") or "mixture"
        self.setWindowTitle("Non-clay decomposition - %s" % name)
        self._setup_xrf_table()

        self.ui.btn_add_ref.clicked.connect(self._on_add)
        self.ui.btn_add_cif.clicked.connect(self._on_add_cif)
        self.ui.btn_edit_comp.clicked.connect(self._on_edit_composition)
        self.ui.btn_si.clicked.connect(self._on_si_standard)
        self.ui.btn_remove_ref.clicked.connect(self._on_remove)
        self.ui.btn_modelless.clicked.connect(self._on_modelless)
        self.ui.btn_modelless.setVisible(bool(self._extra_specimens))
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
            "Structure files (*.cif *.str);;All files (*)")
        if not path:
            return
        specs = [s for s in self._mixture.specimens if s is not None]
        if not specs:
            QMessageBox.warning(
                self, "No specimen", "The mixture has no specimen goniometer to "
                "build the reference with.")
            return
        builder = (reference_from_str if path.lower().endswith(".str")
                   else reference_from_cif)
        try:
            ref, composition = builder(path, specs[0].goniometer, fwhm=self._fwhm)
        except Exception as exc:  # surface the ValueError message
            QMessageBox.warning(
                self, "Could not build reference from the structure", "%s" % exc)
            return
        self.add_reference(ref, composition)

    def _on_si_standard(self) -> None:
        """Load a Si-standard measurement and set the instrumental peak width used
        when building references from a CIF (Finding 21)."""
        path, _filter = QFileDialog.getOpenFileName(
            self, "Load a Si-standard measurement", "", _PATTERN_FILTER)
        if not path:
            return
        try:
            x, y = parse_pattern(path)
        except Exception as exc:
            QMessageBox.warning(self, "Could not load Si standard", "%s" % exc)
            return
        self._fwhm = instrumental_fwhm(x, y)
        self.ui.lbl_si.setText(
            "Reference width: %.3f° (from Si standard)" % self._fwhm)

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

    def _on_modelless(self) -> None:
        """Open the model-less fit on the project's loose / unmodeled specimens
        (heat-treated variants with no clay model). Needs at least one reference;
        does NOT touch the clay path or the modeled results above."""
        if not self._references:
            QMessageBox.information(
                self, "No references", "Add at least one non-clay reference first.")
            return
        if not self._extra_specimens:
            QMessageBox.information(
                self, "No loose specimens",
                "No unmodeled (loose / heat-treated) specimens were found in the "
                "project for this mixture.")
            return
        _modelless_dialog(self, self._extra_specimens, self._references)

    def run(self) -> None:
        """Recompute the clay fit (read-only), decompose against the loaded
        references, and (if XRF oxides were entered) compute the weight-% mass
        balance. Also the public entry the harness drives. The mis-registration
        null makes this take a moment, so it runs under a wait cursor."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._mixture.calculate()  # make the residual current; does not refit
            self._result = decompose_mixture(
                self._mixture, self._references, detect=True)
            xrf = self._read_xrf()
            self._massbalance = (
                mass_balance(self._mixture, xrf, self._references, self._compositions)
                if xrf else None)
            self._populate()
            self._set_results_enabled(True)
        finally:
            QApplication.restoreOverrideCursor()

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
