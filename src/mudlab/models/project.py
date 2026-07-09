"""Project model (Qt signals).

Property names follow the old mudlab.project.models.Project (the old
adapters bound widget `project_<prop>` to model `<prop>`, so these names
line up with the Edit Project dialog's widget names). The project also
acts as the signal bus: child specimen signals are re-emitted so views
only need to listen to the project.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from mudlab.models.properties import Prop
from mudlab.models.specimen import Specimen


class Project(QObject):
    data_changed = Signal()
    visuals_changed = Signal()
    specimens_changed = Signal()

    name = Prop("New Project", "visuals_changed")
    author = Prop("", "data_changed")
    date = Prop("", "data_changed")
    description = Prop("", "data_changed")
    layout_mode = Prop("FULL", "visuals_changed")  # FULL only in MudLab2

    # Pattern display defaults (old settings.py values)
    display_exp_color = Prop("#000000", "visuals_changed")
    display_calc_color = Prop("#FF0000", "visuals_changed")
    display_exp_lw = Prop(1.0, "visuals_changed")
    display_calc_lw = Prop(2.0, "visuals_changed")
    display_exp_ls = Prop("-", "visuals_changed")
    display_calc_ls = Prop("-", "visuals_changed")
    display_exp_marker = Prop("", "visuals_changed")
    display_calc_marker = Prop("", "visuals_changed")
    display_plot_offset = Prop(0.75, "visuals_changed")
    display_group_by = Prop(1, "visuals_changed")
    display_label_pos = Prop(0.35, "visuals_changed")

    # Axes
    axes_xlimit = Prop(0, "visuals_changed")  # 0 automatic, 1 manual
    axes_xmin = Prop(0.0, "visuals_changed")
    axes_xmax = Prop(70.0, "visuals_changed")
    axes_xstretch = Prop(True, "visuals_changed")
    axes_ylimit = Prop(0, "visuals_changed")
    axes_ymin = Prop(0.0, "visuals_changed")
    axes_ymax = Prop(0.0, "visuals_changed")
    axes_yvisible = Prop(False, "visuals_changed")
    axes_ynormalize = Prop(0, "visuals_changed")
    axes_dspacing = Prop(False, "visuals_changed")

    # Marker defaults
    display_marker_angle = Prop(0.0, "visuals_changed")
    display_marker_top_offset = Prop(0.0, "visuals_changed")
    display_marker_style = Prop("none", "visuals_changed")
    display_marker_color = Prop("#000000", "visuals_changed")
    display_marker_base = Prop(0, "visuals_changed")
    display_marker_top = Prop(0, "visuals_changed")
    display_marker_align = Prop("left", "visuals_changed")

    def __init__(self, name: str = "", parent: QObject | None = None) -> None:
        super().__init__(parent)
        if name:
            self.name = name
        self._specimens: list[Specimen] = []
        # File-related plain attributes (not persisted properties):
        # raw_properties keeps the full .mud property dict verbatim so that
        # parts MudLab2 does not model yet survive load/save round-trips.
        self.raw_properties: dict = {}
        self.file_version: str | None = None
        self.filename: str | None = None

    # ------------------------------------------------------------------
    # Specimens
    # ------------------------------------------------------------------
    @property
    def specimens(self) -> tuple[Specimen, ...]:
        return tuple(self._specimens)

    def add_specimen(self, specimen: Specimen) -> Specimen:
        specimen.setParent(self)
        specimen.project = self
        specimen.data_changed.connect(self.data_changed)
        specimen.visuals_changed.connect(self.visuals_changed)
        self._specimens.append(specimen)
        self.specimens_changed.emit()
        return specimen

    def remove_specimen(self, specimen: Specimen) -> None:
        if specimen in self._specimens:
            specimen.data_changed.disconnect(self.data_changed)
            specimen.visuals_changed.disconnect(self.visuals_changed)
            self._specimens.remove(specimen)
            specimen.project = None
            specimen.setParent(None)
            specimen.deleteLater()
            self.specimens_changed.emit()
