"""Specimen utility dialogs: trim, statistics, save-graph size.

Ported from specimen/glade/trim_dialog.glade, statistics.glade and
save_graph_size.glade.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from mudlab.ui.ui_save_graph_size import Ui_SaveGraphSizeDialog
from mudlab.ui.ui_statistics import Ui_StatisticsDialog
from mudlab.ui.ui_trim_dialog import Ui_TrimDataDialog

# Combo index -> scope (old cmb_scope items order).
TRIM_SCOPES = ("specimen", "all")

# Export presets: (label, width px, height px, dpi) - old settings.OUTPUT_PRESETS.
SAVE_GRAPH_PRESETS = (
    ("Landscape Large print", 8000, 4800, 300),
    ("Landscape Medium print", 6000, 3800, 300),
    ("Landscape Small print", 4000, 2800, 300),
    ("Portrait Large print", 4800, 8000, 300),
    ("Portrait Medium print", 3800, 6000, 300),
    ("Portrait Small print", 2800, 4000, 300),
)


class TrimDataDialog(QDialog):
    """Permanently clip specimens to a 2-theta range (old TrimController).

    Trimming is destructive and also drops markers and exclusion ranges that
    fall outside the new limits, so the dialog names what will go before the
    user commits. Scope trims either the selected specimen or every loaded
    one; "all" pre-fills the range shared by every specimen, since a range
    wider than that would fail on some of them.
    """

    def __init__(
        self, parent: QWidget | None = None, specimen=None, specimens=None
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_TrimDataDialog()
        self.ui.setupUi(self)
        self._specimen = specimen
        self._specimens = list(specimens or ([specimen] if specimen else []))
        self.ui.cmb_scope.currentIndexChanged.connect(self._on_scope_changed)
        self.ui.spin_min_2theta.valueChanged.connect(self._update_warning)
        self.ui.spin_max_2theta.valueChanged.connect(self._update_warning)
        self.ui.buttonBox.accepted.connect(self._on_accept)
        self.ui.buttonBox.rejected.connect(self.reject)
        if specimen is not None:
            self._fill_range_from([specimen])
        self._update_warning()

    @property
    def scope(self) -> str:
        return TRIM_SCOPES[self.ui.cmb_scope.currentIndex()]

    def _targets(self) -> list:
        return self._specimens if self.scope == "all" else [self._specimen]

    def _fill_range_from(self, specimens) -> None:
        """Pre-fill min/max with the range common to `specimens` (for a single
        specimen that is just its own range; across several it is the overlap
        - the widest lower bound and the narrowest upper one)."""
        mins, maxs = [], []
        for spec in specimens:
            x, _ = spec.experimental_pattern
            if len(x) >= 2:
                mins.append(float(np.min(x)))
                maxs.append(float(np.max(x)))
        if not mins or max(mins) >= min(maxs):
            return
        for spin, value in (
            (self.ui.spin_min_2theta, max(mins)),
            (self.ui.spin_max_2theta, min(maxs)),
        ):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    def _on_scope_changed(self, _index: int) -> None:
        self._fill_range_from(self._targets())
        self._update_warning()

    def _count_removals(self, specimen, min_2t, max_2t) -> tuple[int, int]:
        n_markers = sum(
            1 for m in specimen.markers
            if m.position < min_2t or m.position > max_2t
        )
        n_excl = sum(
            1 for a, b in specimen.exclusion_ranges
            if not (min(a, b) >= min_2t and max(a, b) <= max_2t)
        )
        return n_markers, n_excl

    def _update_warning(self, *_args) -> None:
        min_2t = self.ui.spin_min_2theta.value()
        max_2t = self.ui.spin_max_2theta.value()
        markers = excl = 0
        for spec in self._targets():
            if spec is None:
                continue
            n_m, n_e = self._count_removals(spec, min_2t, max_2t)
            markers += n_m
            excl += n_e
        parts = []
        if markers:
            parts.append("%d marker%s" % (markers, "" if markers == 1 else "s"))
        if excl:
            parts.append("%d exclusion range%s" % (excl, "" if excl == 1 else "s"))
        self.ui.lbl_removal_warning.setText(
            "The following will also be removed: %s." % " and ".join(parts)
            if parts else ""
        )
        self.ui.lbl_removal_warning.setVisible(bool(parts))

    def _on_accept(self) -> None:
        min_2t = self.ui.spin_min_2theta.value()
        max_2t = self.ui.spin_max_2theta.value()
        if min_2t >= max_2t:
            QMessageBox.information(
                self, "Trim data", "Min °2θ must be less than Max °2θ."
            )
            return
        failed = [
            spec.name or "(unnamed)"
            for spec in self._targets()
            if spec is not None and not spec.trim(min_2t, max_2t)
        ]
        if failed:
            QMessageBox.information(
                self, "Trim data",
                "The following specimen(s) could not be trimmed because the "
                "selected range contains fewer than 2 data points:\n%s"
                % "\n".join(failed),
            )
        self.accept()


class StatisticsDialog(QDialog):
    """Old StatisticsView; opened from the specimens context menu."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_StatisticsDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.rejected.connect(self.reject)

    def set_statistics(
        self, points: int, chi2: float, R2: float, Rp: float, Rwp: float, Re: float
    ) -> None:
        self.ui.lbl_points.setText(str(points))
        self.ui.lbl_chi2.setText(f"{chi2:.4f}")
        self.ui.lbl_R2.setText(f"{R2:.4f}")
        self.ui.lbl_Rp.setText(f"{Rp:.2f}")
        self.ui.lbl_Rwp.setText(f"{Rwp:.2f}")
        self.ui.lbl_Re.setText(f"{Re:.2f}")


class SaveGraphSizeDialog(QDialog):
    """Size/DPI options shown when saving the graph (old: an expander
    embedded in the GTK save dialog; Qt native dialogs cannot embed custom
    widgets, so this runs as a small dialog before the file picker)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_SaveGraphSizeDialog()
        self.ui.setupUi(self)
        for label, *_ in SAVE_GRAPH_PRESETS:
            self.ui.cmb_presets.addItem(label)
        self.ui.cmb_presets.currentIndexChanged.connect(self._apply_preset)
        self._apply_preset(0)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

    def _apply_preset(self, index: int) -> None:
        _label, width, height, dpi = SAVE_GRAPH_PRESETS[index]
        self.ui.entry_width.setValue(width)
        self.ui.entry_height.setValue(height)
        self.ui.entry_dpi.setValue(dpi)
