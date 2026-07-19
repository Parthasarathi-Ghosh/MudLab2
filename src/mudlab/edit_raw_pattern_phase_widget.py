"""Raw-pattern phase editor. Design: ui/edit_raw_pattern_phase.ui.

Ported from the GTK EditRawPatternPhaseView (phases/glade/raw_pattern_phase.
glade). A RawPatternPhase has no structure - it IS a measured pattern - so this
editor is deliberately simple: a name field, an "Import pattern" button, and a
read-only preview of the stored curve. There are no probabilities / components /
CSDS tabs (those belong to a computed Phase).

Plugged into the Edit Phases window's Properties pane alongside the structural
EditPhaseWidget; EditPhasesDialog shows whichever matches the selected phase's
type. Importing reads an XRD data file via file_parsers.xy_parser (.xy / .txt /
.csv / .dat); the instrument formats .xrdml / .raw are a later batch.
"""

from __future__ import annotations

from typing import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QFileDialog, QWidget

from mudlab.chart_style import INK_SECONDARY, SERIES_BLUE, SURFACE, style_axes
from mudlab.file_parsers.xy_parser import parse_xy
from mudlab.ui.ui_edit_raw_pattern_phase import Ui_EditRawPatternPhaseWidget

# Same import filter the specimen line-import dialog offers (xy_parser handles
# every one). The instrument formats .xrdml / .raw are not parsed yet.
_PATTERN_FILTERS = "XRD patterns (*.xy *.txt *.csv *.dat);;All files (*.*)"


class EditRawPatternPhaseWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditRawPatternPhaseWidget()
        self.ui.setupUi(self)

        self._phase = None
        self._on_changed: Callable[[], None] | None = None
        self._updating = False

        self.figure = Figure(facecolor=SURFACE, layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(180)
        self.ui.rawPlotLayout.addWidget(self.canvas)
        self.axes = self.figure.add_subplot(111)

        self.ui.raw_phase_name.editingFinished.connect(self._on_name_edited)
        self.ui.button_import_pattern.clicked.connect(self._on_import_clicked)

        self.setEnabled(False)
        self._refresh()

    # ------------------------------------------------------------------
    def bind_raw_phase(
        self, phase, on_changed: Callable[[], None] | None = None
    ) -> None:
        """Show and edit a RawPatternPhase. `on_changed` runs after an accepted
        edit (name change or a fresh import), so the caller recomputes the
        pattern and refreshes the list label."""
        self._phase = phase
        self._on_changed = on_changed
        self.setEnabled(phase is not None)
        self._updating = True
        try:
            self.ui.raw_phase_name.setText(phase.name if phase is not None else "")
        finally:
            self._updating = False
        self._refresh()

    # ------------------------------------------------------------------
    def _on_name_edited(self) -> None:
        if self._phase is None or self._updating:
            return
        self._phase.name = self.ui.raw_phase_name.text()
        if self._on_changed is not None:
            self._on_changed()

    def _on_import_clicked(self) -> None:
        if self._phase is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import measured pattern", "", _PATTERN_FILTERS
        )
        if path:
            self.import_from_path(path)

    def import_from_path(self, path: str) -> None:
        """Read a measured pattern from `path` into the bound phase and refresh.
        Separate from the file dialog so it can be driven head-less."""
        if self._phase is None:
            return
        x, y = parse_xy(path)
        self._phase.set_raw_pattern(x, y)
        self._refresh()
        if self._on_changed is not None:
            self._on_changed()

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        self._update_info()
        self._update_figure()

    def _update_info(self) -> None:
        phase = self._phase
        if phase is None or phase.raw_pattern_x.size < 2:
            self.ui.raw_pattern_info.setText("No pattern loaded.")
            return
        x, y = phase.raw_pattern_x, phase.raw_pattern_y
        self.ui.raw_pattern_info.setText(
            "%d points   %.3f-%.3f deg 2θ   max %.4g"
            % (x.size, float(x.min()), float(x.max()), float(y.max()))
        )

    def _update_figure(self) -> None:
        self.axes.clear()
        phase = self._phase
        if phase is not None and phase.raw_pattern_x.size >= 2:
            self.axes.plot(
                phase.raw_pattern_x, phase.raw_pattern_y,
                color=SERIES_BLUE, linewidth=1.0,
            )
            self.axes.set_xlabel("2θ [deg]", color=INK_SECONDARY)
            self.axes.set_ylabel("Intensity", color=INK_SECONDARY)
        style_axes(self.axes)
        self.canvas.draw_idle()
