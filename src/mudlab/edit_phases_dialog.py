"""Edit Phases window: the object-store shell hosting the phase editor,
bound to the project's real Phase models.

Old: AppView child view "phases" = NoMinMaxObjectListStoreView +
PhasesController; opened by the edit_phases action.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QMenu, QMessageBox, QPushButton, QWidget,
)

from mudlab.add_phase_dialog import AddPhaseDialog
from mudlab.edit_nonclay_phase_widget import EditNonClayPhaseWidget
from mudlab.edit_phase_widget import EditPhaseWidget
from mudlab.edit_raw_pattern_phase_widget import EditRawPatternPhaseWidget
from mudlab.default_state import (
    capture_catalog_defaults, capture_imported_defaults, set_as_baseline,
)
from mudlab.file_parsers.default_catalog import add_catalog_entry_to_project
from mudlab.file_parsers.phs_phases import PHS_FILTERS, load_phs, save_phs
from mudlab.import_nonclay_dialog import ImportNonClayDialog
from mudlab.models import Project
from mudlab.models.phase import Phase
from mudlab.models.raw_pattern_phase import RawPatternPhase
from mudlab.object_store_dialog import ObjectStoreDialog


def deletion_confirm_message(phase, dependants) -> str:
    """The confirm text for deleting `phase`. When other phases depend on it
    (based_on it, or a component linked to its components) it names them and
    explains that their values are kept (snapshot-on-detach bakes them in before
    severing, so their patterns will not change). Otherwise the plain
    irreversible-delete warning."""
    if not dependants:
        return ("Deleting a phase is irreversible!\n"
                "Are you sure you want to continue?")
    names = "\n".join("  • %s" % (d.name or "(unnamed)") for d in dependants)
    return (
        "%s is the reference for %d other phase(s):\n\n%s\n\n"
        "Deleting it will detach them. Their current values are kept, so their "
        "calculated patterns will not change.\n\n"
        "Deleting a phase is irreversible. Continue?"
        % (phase.name or "This phase", len(dependants), names)
    )


class EditPhasesDialog(ObjectStoreDialog):
    def __init__(self, parent: QWidget | None = None, project: Project | None = None) -> None:
        super().__init__(parent, title="Edit Phases", columns=("Phase", "R", "G"))
        self.project = project

        # Two editors share the Properties pane: the structural EditPhaseWidget
        # for a computed Phase, and EditRawPatternPhaseWidget for a measured
        # RawPatternPhase. _bind_selected shows whichever matches the selection.
        self.phase_widget = EditPhaseWidget(self)
        self.set_properties_widget(self.phase_widget)
        self.raw_phase_widget = EditRawPatternPhaseWidget(self)
        self.set_properties_widget(self.raw_phase_widget)
        self.raw_phase_widget.hide()
        # A third editor for the experimental NonClayPhase (oxide grid + preview).
        self.nonclay_widget = EditNonClayPhaseWidget(self)
        self.set_properties_widget(self.nonclay_widget)
        self.nonclay_widget.hide()
        self.nonclay_widget.apply_fwhm_to_all.connect(self._apply_fwhm_to_all)
        self.nonclay_widget.apply_caglioti_to_all.connect(self._apply_caglioti_to_all)

        self._phases = list(project.phases) if project is not None else []
        for phase in self._phases:
            self.add_object_row(*self._phase_row_values(phase))

        self.object_selected.connect(self._on_phase_selected)

        # Add / Remove / Import / Export are all wired now.
        self.ui.button_add_object.clicked.connect(self._on_add_phase)
        self.ui.button_del_object.clicked.connect(self._on_remove_phase)
        self.ui.button_load_object.clicked.connect(self._on_import_phases)
        self.ui.button_save_object.clicked.connect(self._on_export_phases)
        # The phase list gets the same Set-as-baseline action as the editor -
        # the editor is where attention is while a phase is being built, the
        # list is where it is when reviewing several.
        tree = self.ui.edit_objects_treeview
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._on_phase_menu)
        self.ui.button_load_object.setToolTip("Import phase(s) from a .phs file.")
        self.ui.button_save_object.setToolTip(
            "Export the selected phase(s) to a .phs file."
        )
        # Experimental: an extra button below the standard ones (in the Objects
        # frame's spare layout) that imports a NonClayPhase.
        self.button_import_nonclay = QPushButton("Import Non-Clay", self)
        self.button_import_nonclay.setToolTip(
            "Import a non-clay phase from a measured pattern or a CIF, with its "
            "oxide composition."
        )
        self.ui.extraLayout.addWidget(self.button_import_nonclay)
        self.button_import_nonclay.clicked.connect(self._on_import_nonclay)

        if self._phases:
            self.ui.edit_objects_treeview.setCurrentIndex(
                self.objects_model.index(0, 0)
            )
        else:
            self.phase_widget.bind_phase(None)

    # ------------------------------------------------------------------
    # Add / Remove (old PhasesController create/delete)
    # ------------------------------------------------------------------
    def _on_add_phase(self) -> None:
        if self.project is None:
            return
        dialog = AddPhaseDialog(self)
        if dialog.exec() != AddPhaseDialog.DialogCode.Accepted:
            return
        first_row = len(self._phases)
        # A default entry adds a whole phase-set (a single-layer clay, or an
        # AD/EG/350 treatment triple) with its atom types merged into the
        # project. The empty-phase factory builds blank components + the R0 /
        # R1G2 probabilities; a raw phase starts with no pattern.
        if dialog.phase_type == "default":
            new_phases = add_catalog_entry_to_project(
                self.project, dialog.default_phase)
            if not new_phases:
                return
            # Record what these started as, NOW, while they provably are the
            # catalog's own phases - so the composition comparison needs no
            # after-the-fact guessing. Only the mapping is stored; the catalog
            # rebuilds the phase itself on demand.
            capture_catalog_defaults(
                self.project, new_phases, dialog.default_phase)
        else:
            if dialog.phase_type == "raw":
                new_phases = [RawPatternPhase(name="New Raw Pattern Phase")]
            else:
                new_phases = [Phase.create_empty(
                    G=dialog.G, R=dialog.R, name="New Phase")]
            self.project.add_phase(new_phases[0])
        for phase in new_phases:
            self._phases.append(phase)
            self.add_object_row(*self._phase_row_values(phase))
        # Select the first new phase so its editor opens (and the candidate
        # combos, rebuilt on selection, pick up the additions).
        self.ui.edit_objects_treeview.setCurrentIndex(
            self.objects_model.index(first_row, 0)
        )
        # ...and put the caret in its NAME box. Naming it is the first thing
        # anyone does with a new phase, and without this the focus falls back to
        # the Add button - so the next keystroke goes nowhere, or worse, Return
        # adds another phase.
        self._focus_editor_name()

    def _focus_editor_name(self) -> None:
        """Focus (and select) the name field of whichever editor is showing.

        Each phase kind has its own editor and its own field, so this asks the
        visible one rather than assuming the clay editor."""
        for widget, field in (
            (self.phase_widget, "phase_name"),
            (self.raw_phase_widget, "raw_phase_name"),
            (self.nonclay_widget, "nonclay_name"),
        ):
            if not widget.isVisible():
                continue
            edit = getattr(widget.ui, field, None)
            if edit is not None:
                edit.setFocus(Qt.FocusReason.OtherFocusReason)
                edit.selectAll()   # typing replaces "New Phase" outright
            return

    def _on_phase_menu(self, pos) -> None:
        tree = self.ui.edit_objects_treeview
        self._phase_menu().exec(tree.viewport().mapToGlobal(pos))

    def _phase_menu(self) -> QMenu:
        """Right-click menu for the phase list. Built separately from showing it
        so it can be inspected without entering a modal loop (`QMenu.exec` is a
        C++ slot and cannot be monkeypatched)."""
        menu = QMenu(self)
        phase = self._selected_phase()
        action = menu.addAction("Set as baseline")
        action.setEnabled(phase is not None
                          and getattr(phase, "type", None) == "Phase"
                          and self.project is not None)
        action.setToolTip(
            "Record this phase's current state as what it is compared against "
            "in the Composition view.")
        action.triggered.connect(self._on_set_baseline_from_list)
        return menu

    def _selected_phase(self):
        rows = self.ui.edit_objects_treeview.selectionModel().selectedRows(0)
        for index in rows:
            if 0 <= index.row() < len(self._phases):
                return self._phases[index.row()]
        return None

    def _on_set_baseline_from_list(self) -> None:
        """Same action as the editor's button, and the same confirmation - it is
        delegated to the editor so the two can never drift apart."""
        phase = self._selected_phase()
        if phase is None or self.project is None:
            return
        # The editor is bound to the selected phase, so reuse its handler.
        if getattr(self.phase_widget, "_phase", None) is not phase:
            self.phase_widget.bind_phase(
                phase, atom_types=self.project.atom_types,
                link_candidates=self._link_candidates(),
                phase_candidates=self._phase_candidates(),
                project=self.project,
            )
        self.phase_widget._on_set_baseline()

    def _on_remove_phase(self) -> None:
        rows = self.ui.edit_objects_treeview.selectionModel().selectedRows(0)
        if not rows or self.project is None:
            return
        index = rows[0].row()
        if not (0 <= index < len(self._phases)):
            return
        phase = self._phases[index]
        # The old app confirms - deleting a phase is irreversible and also
        # clears every based_on / linked_with / mixture reference to it. When
        # other phases depend on this one, warn and name them: they are detached
        # but their values are baked in first (snapshot-on-detach), so their
        # patterns are preserved.
        dependants = self.project.phase_dependants(phase)
        if QMessageBox.question(
            self, "Remove phase", deletion_confirm_message(phase, dependants),
        ) != QMessageBox.StandardButton.Yes:
            return
        self.project.remove_phase(phase)  # cascades every reference to it
        # Recompute: a mixture that used the phase now has an empty cell, so
        # its stored calculated pattern still carries the removed phase's
        # contribution until this runs.
        self.project.calculate()
        del self._phases[index]
        self.objects_model.removeRow(index)
        # Reselect a neighbour so the editor keeps showing a valid phase.
        if self._phases:
            new_row = min(index, len(self._phases) - 1)
            self.ui.edit_objects_treeview.setCurrentIndex(
                self.objects_model.index(new_row, 0)
            )
        else:
            self.phase_widget.bind_phase(None)

    # ------------------------------------------------------------------
    # Import Non-Clay (experimental "path 2")
    # ------------------------------------------------------------------
    def _on_import_nonclay(self) -> None:
        if self.project is None:
            return
        dialog = ImportNonClayDialog(self, goniometer=self._project_goniometer())
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.phase is None:
            return
        phase = dialog.phase
        self.project.add_phase(phase)
        first_row = len(self._phases)
        self._phases.append(phase)
        self.add_object_row(*self._phase_row_values(phase))
        # A brand-new phase is not in any mixture yet, so no recompute is needed.
        self.ui.edit_objects_treeview.setCurrentIndex(
            self.objects_model.index(first_row, 0)
        )

    def _apply_fwhm_to_all(self, fwhm: float) -> None:
        """Set the calibrated FWHM on every computed non-clay phase in the
        project (instrumental width is shared), re-render each, and recompute."""
        if self.project is None:
            return
        gonio = self._project_goniometer()
        wavelength = gonio.wavelength if gonio is not None else 0.154056
        changed = False
        for phase in self.project.phases:
            if getattr(phase, "type", None) == "NonClayPhase" and phase.is_computed:
                phase.set_fwhm(fwhm)
                phase.rebuild_stored_pattern(wavelength)
                changed = True
        if changed:
            self.project.calculate()

    def _apply_caglioti_to_all(self, caglioti) -> None:
        """Set the calibrated angle-dependent width on every computed non-clay
        phase, re-render each, and recompute."""
        if self.project is None:
            return
        gonio = self._project_goniometer()
        wavelength = gonio.wavelength if gonio is not None else 0.154056
        changed = False
        for phase in self.project.phases:
            if getattr(phase, "type", None) == "NonClayPhase" and phase.is_computed:
                phase.set_caglioti(*caglioti)
                phase.rebuild_stored_pattern(wavelength)
                changed = True
        if changed:
            self.project.calculate()

    def _project_goniometer(self):
        """A goniometer to compute a CIF pattern at the project's wavelength
        (the first specimen's), or None so the dialog falls back to CuKα."""
        if self.project is None:
            return None
        for specimen in self.project.specimens:
            if specimen is not None and getattr(specimen, "goniometer", None):
                return specimen.goniometer
        return None

    # ------------------------------------------------------------------
    # Import / Export (.phs)  (old PhasesController load/save object)
    # ------------------------------------------------------------------
    def _on_import_phases(self) -> None:
        if self.project is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import phases", "", PHS_FILTERS
        )
        if not path:
            return
        try:
            imported, missing = load_phs(path, self.project)
        except Exception as exc:  # zip / json / format errors
            QMessageBox.critical(
                self, "Import phases", "Could not import:\n%s\n\n%s" % (path, exc)
            )
            return
        # Capture a PRISTINE reference copy of what was just imported, before
        # anything can refine it, so it can serve as the "default state" in the
        # composition comparison. A convenience: it never blocks the import.
        capture_imported_defaults(self.project, path, imported)
        first_row = len(self._phases)
        for phase in imported:
            self._phases.append(phase)
            self.add_object_row(*self._phase_row_values(phase))
        if missing:
            QMessageBox.warning(
                self, "Import phases",
                "Imported %d phase(s), but these atom types are not in this "
                "project - their atoms contribute nothing until the atom types "
                "are added:\n\n%s" % (len(imported), ", ".join(missing)),
            )
        if imported:
            self.ui.edit_objects_treeview.setCurrentIndex(
                self.objects_model.index(first_row, 0)
            )

    def _on_export_phases(self) -> None:
        rows = self.ui.edit_objects_treeview.selectionModel().selectedRows(0)
        selected = [
            self._phases[r.row()] for r in rows
            if 0 <= r.row() < len(self._phases)
        ]
        if not selected:
            QMessageBox.information(
                self, "Export phases", "Select one or more phases to export."
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export phases", "", PHS_FILTERS
        )
        if not path:
            return
        if not path.lower().endswith(".phs"):
            path += ".phs"
        try:
            save_phs(selected, path)
        except Exception as exc:
            QMessageBox.critical(
                self, "Export phases", "Could not export:\n%s\n\n%s" % (path, exc)
            )

    def _phase_row_values(self, phase) -> tuple:
        """(name, R, G) row for the phase list. A raw-pattern or non-clay phase
        has no stacking model, so R / G are shown as '—'."""
        if phase.type in ("RawPatternPhase", "NonClayPhase"):
            default = "Non-clay" if phase.type == "NonClayPhase" else "Raw pattern"
            return (phase.name or default, "—", "—")
        return (phase.name, str(getattr(phase.probabilities, "R", 0)), str(phase.G))

    def _on_phase_selected(self, index: QModelIndex) -> None:
        if not (0 <= index.row() < len(self._phases)):
            return
        phase = self._phases[index.row()]
        # Show the editor that matches the phase type, hide the others.
        if phase.type == "NonClayPhase":
            self.phase_widget.hide()
            self.raw_phase_widget.hide()
            self.nonclay_widget.show()
            gonio = self._project_goniometer()
            self.nonclay_widget.bind_nonclay_phase(
                phase, on_changed=lambda p=phase: self._recalculate(p),
                wavelength_nm=gonio.wavelength if gonio is not None else None,
            )
        elif phase.type == "RawPatternPhase":
            self.phase_widget.hide()
            self.nonclay_widget.hide()
            self.raw_phase_widget.show()
            self.raw_phase_widget.bind_raw_phase(
                phase, on_changed=lambda p=phase: self._recalculate(p)
            )
        else:
            self.raw_phase_widget.hide()
            self.nonclay_widget.hide()
            self.phase_widget.show()
            atom_types = self.project.atom_types if self.project is not None else []
            self.phase_widget.bind_phase(
                phase,
                on_changed=lambda p=phase: self._recalculate(p),
                atom_types=atom_types,
                link_candidates=self._link_candidates(),
                phase_candidates=self._phase_candidates(),
                project=self.project,
            )

    def _phase_candidates(self):
        """(label, phase) for every phase - the reference phases offered in the
        editor's "based on" combo (it filters to matching G)."""
        if self.project is None:
            return []
        return [(ph.name or "phase", ph) for ph in self.project.phases]

    def _link_candidates(self):
        """(label, component) for every component in the project - the linking
        templates offered in the component editor's "Linked with" combo."""
        if self.project is None:
            return []
        return [
            ("%s / %s" % (ph.name, getattr(comp, "name", "") or "component"), comp)
            for ph in self.project.phases
            for comp in ph.components
        ]

    def _recalculate(self, phase) -> None:
        """Recompute every mixture after a phase edit (any mixture may use
        this phase); the specimens' data_changed then refreshes the plot.
        Keep the list label in sync with an edited phase name."""
        if self.project is not None:
            self.project.calculate()
        rows = self.ui.edit_objects_treeview.selectionModel().selectedRows(0)
        if rows:
            item = self.objects_model.itemFromIndex(rows[0])
            if item is not None:
                item.setText(phase.name)
