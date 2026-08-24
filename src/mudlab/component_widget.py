"""Component (clay layer) editor. Design: ui/edit_component.ui.

Ported from the GTK EditComponentView (phases/glade/component.glade). A
phase has G components (clay layers); a selector picks one, and its c-axis
scalars (name, basal spacing d001 / cell length c, default c length, delta-c
defect spread) and layer/interlayer atom lists are editable, with cell
volume + charge balance shown read-only.

Cell lengths a/b are edited by embedded UnitCellPropWidgets (Batch 1b): each
is fixed (a typed value) or derived (factor x property + constant); editing
recomputes the derived values (cell_b can feed cell_a) and the pattern.

The Atom relations group lists the component's relations; an AtomRatio
(substitution between two atoms, Batch 2b) or an AtomContents (scale a set of
atoms by one value, Batch 3b) is edited by its embedded widget - editing
re-applies the relation (setting the atoms' pn) and cascades to the derived
cell lengths + pattern. Chained (relation-to-relation) entries are listed but
edited later; inherited relations are read-only.

Plugged into the Edit Phases > Components tab and bound to the phase's
Component models; editing a scalar recomputes the structure factor and,
via the phase editor's callback, the calculated pattern.

Batch L2/L3 surfaces component linking (shared clay layers): a "Linked with"
combo listing the project's components + per-property inherit checkboxes.
Picking a template links this component (Component.set_linked_with, self-link/
cycle guarded); "(not linked)" unlinks and clears the inherit flags. On a
linked component, ticking an inherit box greys that field (it reads through to
the template's value) and recomputes; the checkboxes are enabled only when the
component is linked.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from mudlab.atom_list_widget import AtomListWidget
from mudlab.contents_widget import AtomContentsWidget
from mudlab.file_parsers.cmp_components import CMP_FILTERS, load_cmp, save_cmp
from mudlab.inheritance_detach import ask_detach_choice
from mudlab.models.atom_relations import AtomContents, AtomRatio
from mudlab.ratio_widget import AtomRatioWidget
from mudlab.ucp_widget import UnitCellPropWidget
from mudlab.ui.ui_edit_component import Ui_EditComponentWidget


class EditComponentWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditComponentWidget()
        self.ui.setupUi(self)

        self._components: list = []
        self._component = None
        self._structure_dialog = None
        self._phase_name = ""
        self._atom_types: list = []
        self._link_candidates: list = []
        self._on_changed: Callable[[], None] | None = None
        self._updating = False

        # Cell a/b unit-cell property editors (fixed or derived) fill the two
        # form placeholders that used to be read-only labels.
        self.ucp_a_widget = UnitCellPropWidget(self)
        self.ui.ucpALayout.addWidget(self.ucp_a_widget)
        self.ucp_b_widget = UnitCellPropWidget(self)
        self.ui.ucpBLayout.addWidget(self.ucp_b_widget)

        # Layer and interlayer atom lists fill the two group-box placeholders.
        self.layer_atoms_widget = AtomListWidget(self)
        self.ui.layerAtomsLayout.addWidget(self.layer_atoms_widget)
        self.interlayer_atoms_widget = AtomListWidget(self)
        self.ui.interlayerAtomsLayout.addWidget(self.interlayer_atoms_widget)

        # The Atom relations group: a relation selector + the AtomRatio /
        # AtomContents editors (one shown at a time for the selected relation).
        self.ratio_widget = AtomRatioWidget(self)
        self.ui.ratioLayout.addWidget(self.ratio_widget)
        self.contents_widget = AtomContentsWidget(self)
        self.ui.ratioLayout.addWidget(self.contents_widget)
        self.contents_widget.setVisible(False)
        self.ui.cmb_relation.currentIndexChanged.connect(self._on_relation_selected)
        self.ui.btn_add_ratio.clicked.connect(self._on_add_ratio)
        self.ui.btn_add_contents.clicked.connect(self._on_add_contents)
        self.ui.btn_del_relation.clicked.connect(self._on_del_relation)

        self.ui.cmb_component.currentIndexChanged.connect(self._on_component_selected)
        self.ui.btn_import_component.clicked.connect(self._on_import_component)
        self.ui.btn_export_component.clicked.connect(self._on_export_component)
        self.ui.btn_show_structure.clicked.connect(self._on_show_structure)
        # AUTODEFAULT: Qt hands autoDefault to every QPushButton with a QDialog
        # ancestor, and re-grants it on REPARENTING - so the flag set in the
        # .ui is not enough once this widget is placed inside Edit Phases. The
        # app-wide policy (qt_utils.install_enter_policy) clears it on every
        # dialog show, which is the real guarantee; this is belt-and-braces for
        # the case where the widget is used outside a shown dialog.
        self.ui.btn_show_structure.setAutoDefault(False)
        self.ui.btn_show_structure.setDefault(False)
        self.ui.component_name.editingFinished.connect(self._on_name_edited)
        self.ui.component_d001.valueChanged.connect(
            lambda v: self._on_scalar_changed("d001", v)
        )
        self.ui.component_default_c.valueChanged.connect(
            lambda v: self._on_scalar_changed("default_c", v)
        )
        self.ui.component_delta_c.valueChanged.connect(
            lambda v: self._on_scalar_changed("delta_c", v)
        )

        # Component-linking controls (Batch L2). The six editable inherit
        # checkboxes toggle per-property inheritance on a linked child. The
        # linked_with combo is display-only (creating/changing a link needs
        # phase "based on", ported later), and the d001 / atom_relations
        # checkboxes are read-only reflections of the model (d001 follows the
        # "cell c" gate; the atom-relations editor is a later batch).
        self._inherit_checks = (
            ("ucp_a", self.ui.component_inherit_ucp_a),
            ("ucp_b", self.ui.component_inherit_ucp_b),
            ("default_c", self.ui.component_inherit_default_c),
            ("delta_c", self.ui.component_inherit_delta_c),
            ("layer_atoms", self.ui.component_inherit_layer_atoms),
            ("interlayer_atoms", self.ui.component_inherit_interlayer_atoms),
        )
        for name, box in self._inherit_checks:
            box.toggled.connect(
                lambda checked, n=name: self._on_inherit_toggled(n, checked)
            )
        self.ui.component_linked_with.currentIndexChanged.connect(
            self._on_linked_with_changed
        )
        self.ui.component_inherit_d001.setEnabled(False)
        self.ui.component_inherit_atom_relations.setEnabled(False)

        self.setEnabled(False)

    # ------------------------------------------------------------------
    def bind_components(
        self,
        components,
        atom_types=None,
        on_changed: Callable[[], None] | None = None,
        link_candidates=None,
        phase_name: str = "",
    ) -> None:
        """Show and edit a phase's Component list. `atom_types` fills the atom
        element combos; `link_candidates` are (label, component) pairs offered
        as linking templates (the whole project's components); `on_changed`
        runs after an accepted edit (used to recompute + redraw the pattern)."""
        self._phase_name = phase_name   # labels the structure diagram
        # Keep the phase's ACTUAL component list (not a copy) so an import
        # can replace a component in place (Component import = replace).
        self._components = components if components is not None else []
        self._atom_types = list(atom_types or [])
        self._link_candidates = list(link_candidates or [])
        self._on_changed = on_changed
        self.setEnabled(bool(self._components))

        self._updating = True
        try:
            self.ui.cmb_component.clear()
            for i, comp in enumerate(self._components):
                self.ui.cmb_component.addItem(
                    getattr(comp, "name", "") or "Component %d" % (i + 1)
                )
        finally:
            self._updating = False

        if self._components:
            self._bind_one(0)
        else:
            self._component = None

    def _bind_one(self, index: int) -> None:
        if not (0 <= index < len(self._components)):
            return
        self._component = self._components[index]
        comp = self._component
        self._updating = True
        try:
            self.ui.component_name.setText(comp.name)
            self.ui.component_d001.setValue(float(comp.d001))
            self.ui.component_default_c.setValue(float(comp.default_c))
            self.ui.component_delta_c.setValue(float(comp.delta_c))
        finally:
            self._updating = False
        self.ucp_a_widget.bind_ucp(
            comp._ucp_a, comp, "cell_b", "B cell length", on_changed=self._on_ucp_changed
        )
        self.ucp_b_widget.bind_ucp(
            comp._ucp_b, comp, "cell_a", "A cell length", on_changed=self._on_ucp_changed
        )
        self.layer_atoms_widget.bind_atoms(
            comp.layer_atoms, self._atom_types, on_changed=self._on_atoms_changed
        )
        self.interlayer_atoms_widget.bind_atoms(
            comp.interlayer_atoms, self._atom_types, on_changed=self._on_atoms_changed
        )
        self._bind_linking(comp)
        self._bind_relations(comp)
        self._refresh_derived()

    def _on_ucp_changed(self) -> None:
        # A cell a/b edit recomputes the derived cell lengths (cell_b may feed
        # cell_a), refreshes both value displays + the derived panel, and
        # redraws the pattern.
        if self._component is None:
            return
        self._component.update_ucp_values()
        self.ucp_a_widget.refresh_value()
        self.ucp_b_widget.refresh_value()
        self._refresh_derived()
        self._notify()

    def _on_atoms_changed(self) -> None:
        # An atom edit changes weight / charge balance; a pn edit may also drive
        # a derived cell length (cell_b = k*pn), so recompute the UCPs too.
        if self._component is not None:
            self._component.update_ucp_values()
            self.ucp_a_widget.refresh_value()
            self.ucp_b_widget.refresh_value()
        self._refresh_derived()
        self._notify()

    # ------------------------------------------------------------------
    # Atom relations (AtomRatio) - drive atom occupancies
    # ------------------------------------------------------------------
    def _bind_relations(self, comp) -> None:
        """Fill the relation selector and bind the editor for the current one.
        Ratios drive atom pn; AtomContents drive atom pn and/or chain to sibling
        relations (both editable). Any unmodeled relation type is shown but not
        editable; inherited relations are read-only."""
        inherited = comp.is_inherited("atom_relations")
        self._updating = True
        try:
            combo = self.ui.cmb_relation
            combo.clear()
            for r in comp.atom_relations:  # read-through (template's when inherited)
                name = getattr(r, "name", None)
                if name is None and isinstance(r, dict):
                    name = r.get("properties", {}).get("name")
                rtype = getattr(r, "type", None) or (
                    r.get("type") if isinstance(r, dict) else "?"
                )
                combo.addItem("%s  [%s]" % (name or "relation", rtype), r)
        finally:
            self._updating = False
        self.ui.btn_add_ratio.setEnabled(not inherited)
        self.ui.btn_add_contents.setEnabled(not inherited)
        self.ui.btn_del_relation.setEnabled(not inherited and combo.count() > 0)
        self._bind_selected_relation()

    def _bind_selected_relation(self) -> None:
        comp = self._component
        if comp is None:
            return
        inherited = comp.is_inherited("atom_relations")
        relation = self.ui.cmb_relation.currentData()
        atoms = list(comp.layer_atoms) + list(comp.interlayer_atoms)
        is_ratio = isinstance(relation, AtomRatio)
        is_contents = isinstance(relation, AtomContents)
        self.ratio_widget.setVisible(is_ratio)
        self.contents_widget.setVisible(is_contents)
        if is_ratio:
            self.ratio_widget.bind_ratio(relation, atoms, on_changed=self._on_relation_edited)
            self.ratio_widget.setEnabled(not inherited)
        else:
            self.ratio_widget.bind_ratio(None, [])
        if is_contents:
            siblings = [r for r in comp.atom_relations if r is not relation]
            self.contents_widget.bind_contents(
                relation, atoms, relations=siblings,
                on_changed=self._on_relation_edited)
            self.contents_widget.setEnabled(not inherited)
        else:
            self.contents_widget.bind_contents(None, [])
        if inherited and (is_ratio or is_contents):
            self.ui.lblRelationInfo.setText("Inherited from the linked component (read-only).")
        elif not (is_ratio or is_contents):
            rtype = relation.get("type") if isinstance(relation, dict) else None
            self.ui.lblRelationInfo.setText(
                "%s is edited in a later batch." % rtype if rtype else ""
            )
        else:
            self.ui.lblRelationInfo.setText("")

    def _on_relation_selected(self, _index: int) -> None:
        if not self._updating:
            self._bind_selected_relation()

    def _on_add_ratio(self) -> None:
        self._add_relation(AtomRatio(name="New ratio", value=0.5, sum=1.0, enabled=True))

    def _on_add_contents(self) -> None:
        self._add_relation(AtomContents(name="New contents", value=1.0, enabled=True))

    def _add_relation(self, relation) -> None:
        comp = self._component
        if comp is None or comp.is_inherited("atom_relations"):
            return
        comp._atom_relations.append(relation)
        self._bind_relations(comp)
        self.ui.cmb_relation.setCurrentIndex(self.ui.cmb_relation.count() - 1)

    def _on_del_relation(self) -> None:
        comp = self._component
        if comp is None or comp.is_inherited("atom_relations"):
            return
        relation = self.ui.cmb_relation.currentData()
        if relation in comp._atom_relations:
            comp._atom_relations.remove(relation)
            comp.apply_atom_relations()
            self._bind_relations(comp)
            self._refresh_after_relation_edit()

    def _on_relation_edited(self) -> None:
        comp = self._component
        if comp is None:
            return
        comp.apply_atom_relations()  # set the atoms' pn + cascade to cell_b/cell_a
        # keep the selector label in step with a renamed relation
        relation = self.ui.cmb_relation.currentData()
        rtype = getattr(relation, "type", None)
        if rtype:
            self._updating = True
            try:
                self.ui.cmb_relation.setItemText(
                    self.ui.cmb_relation.currentIndex(),
                    "%s  [%s]" % (getattr(relation, "name", "") or "relation", rtype),
                )
            finally:
                self._updating = False
        self._refresh_after_relation_edit()

    def _refresh_after_relation_edit(self) -> None:
        comp = self._component
        if comp is None:
            return
        # atom pn changed -> refresh the atom lists; the cell may have moved.
        self.layer_atoms_widget.bind_atoms(
            comp.layer_atoms, self._atom_types, on_changed=self._on_atoms_changed
        )
        self.interlayer_atoms_widget.bind_atoms(
            comp.interlayer_atoms, self._atom_types, on_changed=self._on_atoms_changed
        )
        self.ucp_a_widget.refresh_value()
        self.ucp_b_widget.refresh_value()
        self._refresh_derived()
        self._notify()

    # ------------------------------------------------------------------
    # Component linking (inherit from a linked template layer)
    # ------------------------------------------------------------------
    def _bind_linking(self, comp) -> None:
        """Fill the linking controls: the linked_with combo (project components
        as templates), the inherit checkbox states, and the greying of the
        fields that read through to the linked template."""
        self._updating = True
        try:
            combo = self.ui.component_linked_with
            combo.clear()
            combo.addItem("(not linked)", None)
            current = 0
            for label, cand in self._link_candidates:
                if cand is comp:
                    continue  # a component cannot link to itself
                combo.addItem(label, cand)
                if cand is comp.linked_with:
                    current = combo.count() - 1
            combo.setCurrentIndex(current)
            linked = comp.linked_with is not None
            for name, box in self._inherit_checks:
                box.setChecked(getattr(comp, "inherit_%s" % name))
                box.setEnabled(linked)  # a property can only inherit when linked
            # Read-only reflections of the model (not user-editable here).
            self.ui.component_inherit_d001.setChecked(comp.inherit_d001)
            self.ui.component_inherit_atom_relations.setChecked(comp.inherit_atom_relations)
        finally:
            self._updating = False
        self._apply_inheritance_ui(comp)

    def _on_linked_with_changed(self, _index: int) -> None:
        if self._component is None or self._updating:
            return
        target = self.ui.component_linked_with.currentData()
        if target is self._component.linked_with:
            return
        # Unlinking would snap inherited values back to this component's own
        # stored ones; offer to keep them (snapshot) instead.
        if target is None and self._component.has_inherited_values():
            source = (self._component.linked_with.name
                      if self._component.linked_with else "")
            choice = ask_detach_choice(self, "component", source)
            if choice == "cancel":
                self._bind_linking(self._component)  # restore the combo
                return
            if choice == "keep":
                self._component.snapshot_inherited()
        if not self._component.set_linked_with(target):
            # Rejected (self-link / cycle): revert the combo to the current link.
            self._bind_linking(self._component)
            return
        # Rebind to refresh the greying, the inherit checkboxes (now en/disabled)
        # and any newly inherited values, then recompute the pattern.
        self._bind_one(self.ui.cmb_component.currentIndex())
        self._notify()

    def _apply_inheritance_ui(self, comp) -> None:
        """Disable (grey) each field that currently reads through to the linked
        template, so the shown value is understood as the template's."""
        self.ucp_a_widget.setEnabled(not comp.is_inherited("cell_a"))
        self.ucp_b_widget.setEnabled(not comp.is_inherited("cell_b"))
        # d001 and default_c share the "cell c" gate (inherit_default_c).
        c_inherited = comp.is_inherited("d001")
        self.ui.component_d001.setDisabled(c_inherited)
        self.ui.component_default_c.setDisabled(c_inherited)
        self.ui.component_delta_c.setDisabled(comp.is_inherited("delta_c"))
        self.layer_atoms_widget.setDisabled(comp.is_inherited("layer_atoms"))
        self.interlayer_atoms_widget.setDisabled(comp.is_inherited("interlayer_atoms"))

    def _on_inherit_toggled(self, name: str, checked: bool) -> None:
        if self._component is None or self._updating:
            return
        setattr(self._component, "inherit_%s" % name, checked)
        # d001 shares the "default_c" gate in the model; keep the paired flag
        # (and its read-only checkbox) consistent, as real projects store them.
        if name == "default_c":
            self._component.inherit_d001 = checked
        # Rebind to refresh the read-through values, the greying and the atom
        # lists (own vs template), then recompute the pattern.
        self._bind_one(self.ui.cmb_component.currentIndex())
        self._notify()

    # ------------------------------------------------------------------
    # Component import / export (.cmp)  (old ComponentsController load/save)
    # ------------------------------------------------------------------
    def _atom_type_map(self) -> dict:
        table = {}
        for at in self._atom_types:
            table[at.uuid] = at
            table[at.name] = at
        return table

    def _on_export_component(self) -> None:
        if self._component is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export component", "", CMP_FILTERS
        )
        if not path:
            return
        if not path.lower().endswith(".cmp"):
            path += ".cmp"
        try:
            save_cmp([self._component], path)
        except Exception as exc:
            QMessageBox.critical(
                self, "Export component", "Could not export:\n%s\n\n%s" % (path, exc)
            )

    def _refresh_structure_dialog(self) -> None:
        """Keep an open structure diagram pointing at the CURRENT component.

        The window is modeless precisely so it can be read while the component
        is edited; left alone it kept showing whichever component was selected
        when it opened, with nothing on screen to say so - the one failure a
        reference window must not have.
        """
        dialog = getattr(self, "_structure_dialog", None)
        if dialog is not None and dialog.isVisible():
            dialog.set_component(self._component, self._phase_name)

    def _on_show_structure(self) -> None:
        """Open (or re-use) the cross-section diagram for the bound component.

        One tracked instance, re-pointed rather than stacked: clicking twice
        should not leave two windows describing the same thing. It is MODELESS,
        so the diagram can be read while the component that it describes is
        edited - `refresh()` brings it up to date.
        """
        if self._component is None:
            return
        from mudlab.structure_diagram_dialog import StructureDiagramDialog

        dialog = getattr(self, "_structure_dialog", None)
        if dialog is None:
            dialog = StructureDiagramDialog(
                self, component=self._component, phase_name=self._phase_name)
            self._structure_dialog = dialog
        else:
            dialog.set_component(self._component, self._phase_name)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _on_import_component(self) -> None:
        """Replace the selected component with one imported from a .cmp (the
        component count is unchanged, so the stacking model is untouched)."""
        idx = self.ui.cmb_component.currentIndex()
        if self._component is None or not (0 <= idx < len(self._components)):
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import component", "", CMP_FILTERS
        )
        if not path:
            return
        try:
            imported, missing = load_cmp(path, self._atom_type_map())
        except Exception as exc:
            QMessageBox.warning(
                self, "Import component", "Could not read:\n%s\n\n%s" % (path, exc)
            )
            return
        if len(imported) != 1:
            QMessageBox.information(
                self, "Import component",
                "This file has %d components; import a single-component .cmp to "
                "replace the selected component." % len(imported),
            )
            return
        new = imported[0]
        self._components[idx] = new        # replaces in the phase's live list
        self._updating = True
        try:
            self.ui.cmb_component.setItemText(
                idx, new.name or "Component %d" % (idx + 1))
        finally:
            self._updating = False
        self._bind_one(idx)
        if missing:
            QMessageBox.warning(
                self, "Import component",
                "Imported, but these atom types are not in this project - the "
                "atoms contribute nothing until they are added:\n\n%s"
                % ", ".join(missing),
            )
        self._notify()

    def _on_component_selected(self, index: int) -> None:
        if not self._updating:
            self._bind_one(index)
            self._refresh_structure_dialog()

    def _on_name_edited(self) -> None:
        if self._component is not None and not self._updating:
            self._component.name = self.ui.component_name.text()
            # Keep the selector label in step with the edited name.
            self._updating = True
            try:
                self.ui.cmb_component.setItemText(
                    self.ui.cmb_component.currentIndex(), self._component.name
                )
            finally:
                self._updating = False
            self._notify()

    def _on_scalar_changed(self, prop: str, value: float) -> None:
        if self._component is not None and not self._updating:
            setattr(self._component, prop, value)
            self._refresh_derived()
            self._notify()

    def _refresh_derived(self) -> None:
        comp = self._component
        if comp is None:
            return
        # cell a/b are shown by their UCP editors now; only volume + charge
        # (which depend on a·b·c) are derived read-outs here.
        self.ui.component_volume.setText("%.5f" % comp.volume)
        layer, interlayer, net = comp.compute_charge_balance()
        self.ui.component_charge.setText(
            "layer %+.2f / interlayer %+.2f / net %+.2f" % (layer, interlayer, net)
        )

    def _notify(self) -> None:
        # An open structure diagram is a view of this component; every accepted
        # edit already funnels through here, so this is the one place that
        # keeps it true without sprinkling refresh calls through the editor.
        self._refresh_structure_dialog()
        if self._on_changed is not None:
            self._on_changed()
