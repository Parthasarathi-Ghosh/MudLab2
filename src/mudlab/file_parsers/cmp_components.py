"""Component file (*.cmp) import / export.

A .cmp is a ZIP whose members are ``<uuid>`` -> a Component JSON dict (the same
serialisation a .mud phase uses for its `components`). A clay-layer component
(its cell, layer / interlayer atoms and atom relations) is saved on its own so
it can be reused in another phase. Atoms reference atom types by NAME, so a
.cmp resolves against whatever atom types the importing project already holds.

Ported from old mudlab (Component.save_components / load_components) minus its
ObjectPool. IMPORT is a REPLACE, not an add: the caller swaps the imported
component in for a selected one, so the phase's component count (and its
stacking model) is unchanged - matching the old app. On export a component is
written standalone (linked_with dropped, inherit flags cleared, atom types by
name). On import every uuid is made fresh (component + atoms, with internal
references remapped consistently) so the imported component can never alias an
existing object.
"""

from __future__ import annotations

import json
import zipfile

from mudlab.file_parsers.uuid_remap import UUID_RE, remap_uuids
from mudlab.models.component import Component

# Qt getOpenFileName / getSaveFileName filter for component files.
CMP_FILTERS = "Component files (*.cmp);;All files (*.*)"

_INHERIT_FLAGS = (
    "inherit_ucp_a", "inherit_ucp_b", "inherit_d001", "inherit_default_c",
    "inherit_delta_c", "inherit_layer_atoms", "inherit_interlayer_atoms",
    "inherit_atom_relations",
)


def _make_standalone_portable(entry: dict, component) -> None:
    """Drop the component's link (linked_with + inherit flags) and stamp each
    atom's resolved atom_type NAME, so the .cmp is self-contained and imports
    by name into any project. Mutates only the freshly built export dict."""
    props = entry.get("properties", {})
    props["linked_with_uuid"] = ""
    for flag in _INHERIT_FLAGS:
        if flag in props:
            props[flag] = False
    for key, atoms in (("layer_atoms", component._layer_atoms),
                       ("interlayer_atoms", component._interlayer_atoms)):
        adicts = props.get(key)
        if not isinstance(adicts, list):
            continue
        for adict, amodel in zip(adicts, atoms):
            if getattr(amodel, "atom_type", None) is not None:
                adict.setdefault("properties", {})["atom_type_name"] = \
                    amodel.atom_type.name


def save_cmp(components, path: str) -> None:
    """Export `components` (Component models) to a .cmp file, each standalone."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for component in components:
            entry = component.to_dict()
            _make_standalone_portable(entry, component)
            archive.writestr(
                component.uuid, json.dumps(entry, separators=(",", ":"))
            )


def load_cmp(path: str, atom_type_map: dict) -> tuple[list, list]:
    """Import components from a .cmp. `atom_type_map` (a project's uuid+name ->
    AtomType map) resolves the atoms' types by name. Every uuid is made fresh so
    the imported components can never alias existing objects. Each component's
    UCP sources / atom relations are resolved against its OWN atoms, and its
    (dropped) link is cleared. Returns (components, missing_atom_type_names)."""
    with zipfile.ZipFile(path) as archive:
        texts = [archive.read(m).decode("utf-8") for m in archive.namelist()]

    # Force every uuid fresh: pass the import's own uuids as the blocked set.
    own = set()
    for text in texts:
        own.update(UUID_RE.findall(text))
    texts, _ = remap_uuids(texts, own)

    components: list = []
    missing: list = []
    for text in texts:
        comp = Component.from_dict(json.loads(text), atom_type_map)
        comp.set_linked_with(None)
        atom_map = {a.uuid: a
                    for a in comp._layer_atoms + comp._interlayer_atoms}
        comp.resolve_ucp_props(atom_map)
        comp.resolve_relations(atom_map)
        components.append(comp)
        for atom in comp._layer_atoms + comp._interlayer_atoms:
            if atom.atom_type is None:
                name = atom.raw_properties.get("atom_type_name")
                if name and name not in missing:
                    missing.append(name)
    return components, missing
