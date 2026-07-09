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
        self._atom_types: list = []
        self._phases: list = []
        self._mixtures: list = []
        # File-related plain attributes (not persisted properties):
        # raw_properties keeps the full .mud property dict verbatim so that
        # parts MudLab2 does not model yet survive load/save round-trips.
        self.raw_properties: dict = {}
        self.file_version: str | None = None
        self.filename: str | None = None

    # ------------------------------------------------------------------
    # Atom types (reference data; a full periodic table of ions)
    # ------------------------------------------------------------------
    @property
    def atom_types(self) -> tuple:
        return tuple(self._atom_types)

    def add_atom_type(self, atom_type) -> "object":
        atom_type.setParent(self)
        self._atom_types.append(atom_type)
        return atom_type

    def get_atom_type(self, name: str):
        """Look up an atom type by name (old atom-type resolution by name)."""
        for atom_type in self._atom_types:
            if atom_type.name == name:
                return atom_type
        return None

    def atom_type_uuid_map(self) -> dict:
        """uuid -> AtomType, for resolving atom references in components."""
        return {at.uuid: at for at in self._atom_types}

    # ------------------------------------------------------------------
    # Phases (calc models; still saved verbatim via raw passthrough)
    # ------------------------------------------------------------------
    @property
    def phases(self) -> tuple:
        return tuple(self._phases)

    def add_phase(self, phase) -> "object":
        self._phases.append(phase)
        return phase

    def phase_uuid_map(self) -> dict:
        """uuid -> Phase, for resolving a mixture's phase-slot grid."""
        return {p.uuid: p for p in self._phases}

    # ------------------------------------------------------------------
    # Mixtures (specimen × phase-slot grids; drive the calculated pattern)
    # ------------------------------------------------------------------
    @property
    def mixtures(self) -> tuple:
        return tuple(self._mixtures)

    def add_mixture(self, mixture) -> "object":
        self._mixtures.append(mixture)
        return mixture

    def calculate(self) -> None:
        """Recompute every mixture's calculated patterns (old
        update_all_mixtures, non-optimising path). Each mixture stores the
        result back on its specimens, whose data_changed then refreshes the
        plot."""
        for mixture in self._mixtures:
            mixture.calculate()

    def specimen_uuid_map(self) -> dict:
        """uuid -> Specimen, for resolving a mixture's specimen rows."""
        return {s.uuid: s for s in self._specimens}

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
