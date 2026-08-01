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
    #: The phase LIST changed (added / removed) - the phase editor rebuilds
    #: its list and its based_on / linked_with candidate combos, which name
    #: every phase in the project.
    phases_changed = Signal()

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
        """Atom-reference resolution map for loading components: keyed by BOTH
        uuid and name (they never collide), so an atom resolves by uuid and
        falls back to its stable name when the uuid is dangling (see
        Atom.from_dict). Name keys are added first so a uuid always wins on the
        off chance a name equals a uuid string."""
        by_name = {at.name: at for at in self._atom_types}
        by_uuid = {at.uuid: at for at in self._atom_types}
        return {**by_name, **by_uuid}

    # ------------------------------------------------------------------
    # Phases (calc models; still saved verbatim via raw passthrough)
    # ------------------------------------------------------------------
    @property
    def phases(self) -> tuple:
        return tuple(self._phases)

    def add_phase(self, phase) -> "object":
        self._phases.append(phase)
        self.phases_changed.emit()
        return phase

    def remove_phase(self, phase) -> None:
        """Remove a phase and clear every reference to it.

        Ported from the old Project.on_phase_removed, which **cascade-clears
        rather than refusing**: a phase can always be deleted, and whatever
        pointed at it silently falls back to its own stored values. Concretely:

        1. the removed phase's own `based_on` link,
        2. any phase based_on the removed one (the dependant keeps the values
           it had stored - inheritance is a read-time overlay, so it simply
           stops reading through),
        3. any component elsewhere linked_with one of the removed phase's
           components (the old app does this via its removed-signal broadcast;
           MudLab2 has no object pool, so the project walks the graph),
        4. every mixture cell holding the phase (the slot stays, the cell
           empties).

        Deleting a phase is irreversible in the old app too - there is no undo,
        and nothing is written until the user saves.
        """
        if phase not in self._phases:
            return
        self._phases.remove(phase)

        phase.set_based_on(None)
        for other in self._phases:
            if other.based_on is phase:
                # Bake the inherited values before detaching so the dependant's
                # calculated pattern does not silently shift (snapshot-on-detach).
                other.snapshot_inherited()
                other.set_based_on(None)

        removed_components = {id(c) for c in phase.components}
        snapshotted = []
        if removed_components:
            for other in self._phases:
                for comp in other.components:
                    if (comp.linked_with is not None
                            and id(comp.linked_with) in removed_components):
                        comp.snapshot_inherited()  # bake before unlinking
                        snapshotted.append(comp)
                        comp.set_linked_with(None)
            self._dedup_shared_atoms(snapshotted)

        for mixture in self._mixtures:
            mixture.unset_phase(phase)

        self.phases_changed.emit()
        self.data_changed.emit()

    def phase_dependants(self, phase) -> list:
        """Phases that read from `phase` - directly based_on it, or with a
        component linked to one of its components. Deleting `phase` detaches them
        (snapshot-on-detach bakes their values in first). Used to warn before a
        base-phase deletion; order follows the project's phase list."""
        comp_ids = {id(c) for c in getattr(phase, "components", [])}
        out = []
        for other in self._phases:
            if other is phase:
                continue
            if other.based_on is phase or any(
                    c.linked_with is not None and id(c.linked_with) in comp_ids
                    for c in getattr(other, "components", [])):
                out.append(other)
        return out

    def _dedup_shared_atoms(self, components) -> None:
        """After snapshotting linked components (which SHARE the template's atom
        objects), give fresh-uuid copies to any component that ended up sharing
        atoms with an earlier one, so a save cannot emit duplicate atom uuids.
        Rare - only when two components linked the same template component."""
        seen: set[int] = set()
        atom_type_map = None
        for comp in components:
            atoms = comp._layer_atoms + comp._interlayer_atoms
            if any(id(a) in seen for a in atoms):
                if atom_type_map is None:
                    atom_type_map = self.atom_type_uuid_map()
                comp.reclone_atoms(atom_type_map)
                atoms = comp._layer_atoms + comp._interlayer_atoms
            for a in atoms:
                seen.add(id(a))

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

    def remove_mixture(self, mixture) -> None:
        """Drop a mixture from the project. Nothing back-references a mixture
        (phases / specimens do not know which mixtures use them), so there is no
        cascade - unlike remove_phase / remove_specimen. The specimens it drove
        keep their last calculated pattern until the next recompute."""
        if mixture in self._mixtures:
            self._mixtures.remove(mixture)

    def calculate(self) -> None:
        """Recompute every mixture's calculated patterns (non-optimising).
        Each mixture stores the result back on its specimens, whose
        data_changed then refreshes the plot."""
        for mixture in self._mixtures:
            mixture.calculate()

    def refresh(self) -> None:
        """Refresh every mixture the way the old update_all_mixtures did:
        optimise the ones with auto_run set, else re-apply their current
        solution. This is the F5 Refresh Graph semantics."""
        for mixture in self._mixtures:
            mixture.update()

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
            # Clear the specimen out of every mixture (old
            # Project.on_specimen_removed -> mixture.unset_specimen). Without
            # this the mixture keeps a row pointing at a specimen that is no
            # longer in the project: calculate() writes patterns onto the
            # removed object and, worse, the optimiser keeps fitting against
            # it - so deleting a bad specimen would not change the refinement.
            for mixture in self._mixtures:
                mixture.unset_specimen(specimen)
            specimen.project = None
            specimen.setParent(None)
            specimen.deleteLater()
            self.specimens_changed.emit()
            self.data_changed.emit()
