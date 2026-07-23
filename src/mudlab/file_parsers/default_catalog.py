"""Bundled default-phase catalog (ported from generate_default_phases.py).

The reference clay-layer COMPONENTS ship as `.cmp` files under
`mudlab/data/default components/` (verbatim from the old app - the same ZIP-of-
Component-JSON format MudLab2's `load_cmp` reads). A default component's atoms
reference atom types by NAME; they resolve against the built-in scattering-
factor library ([atom_type_library]), so a phase built from a default component
computes a real pattern with no project atom types needed.

`build_catalog_entry` assembles named default PHASES from those components,
following the old generator's recipe: a component "code" (4-char aliases, one
per component) selects the `.cmp` files, and per-phase `based_on` / per-
component `linked_with` names wire the air-dried -> glycolated -> heated (Ca-AD /
Ca-EG / Ca-350) inheritance chains. `default_catalog_entries` lists the entries
the Add Phase dialog offers.

SCOPE: MudLab2 models only R0 (any G) and R1G2 stacking (R1G3 / R2 / R3 are not
ported), so `is_modeled` gates the catalog to those. Covered: the single-layer
clays, the expandable Ca-smectite / -vermiculite families (G=1), and the
2-component mixed-layer interstratified families (Illite- / Kaolinite- / Talc- /
Chlorite-Smectite) at R0 and R1G2 - whose treated phases inherit the AD's
stacking ratio (inherit_probabilities). The higher-order mixed-layer stacks
(SS/SSS multi-hydration, ICS/KCS, vermiculite interstratifications) need the
extra 1WAT/1GLY/Dehydr components aliased and are a later extension.
"""

from __future__ import annotations

import os

from mudlab.file_parsers.atom_type_library import atom_type_library_map
from mudlab.file_parsers.cmp_components import load_cmp
from mudlab.models.phase import Phase

_COMPONENTS_DIR = os.path.join(
    os.path.dirname(__file__), os.pardir, "data", "default components"
)


def default_components_dir() -> str:
    """Absolute path to the bundled default-component `.cmp` directory."""
    return os.path.abspath(_COMPONENTS_DIR)


def load_default_component(relpath: str, atom_type_map: dict | None = None) -> list:
    """Load the component(s) in a bundled `.cmp` (path relative to
    `default_components_dir`), resolving their atoms against the built-in
    scattering-factor library by default so the result is directly computable.
    Pass an `atom_type_map` (e.g. a project's) to resolve against that instead."""
    if atom_type_map is None:
        atom_type_map = atom_type_library_map()
    path = os.path.join(default_components_dir(), relpath)
    components, _names = load_cmp(path, atom_type_map)
    return components


# ----------------------------------------------------------------------
# The recipe (ported from generate_default_phases.run)
# ----------------------------------------------------------------------
_CODE_LEN = 4  # each component is named by a 4-character alias in the "code"


def is_modeled(reichweite: int, g: int) -> bool:
    """Whether MudLab2 models this stacking: R0 (any G) or R1G2 only."""
    return reichweite == 0 or (reichweite == 1 and g == 2)

# alias -> .cmp path (relative to the default-component dir).
_ALIASES = {
    "K   ": "Kaolinite.cmp",
    "I   ": "Illite.cmp",
    "Se  ": "Serpentine.cmp",
    "T   ": "Talc.cmp",
    "C   ": "Chlorite.cmp",
    "Ma  ": "Margarite.cmp",
    "L   ": "Leucophyllite.cmp",
    "Pa  ": "Paragonite.cmp",
    # Di-octahedral smectite: air-dried (2 water) / glycolated (2 glycol) / heated
    "dS2w": "Di-Smectite/Di-Smectite - Ca 2WAT.cmp",
    "dS2g": "Di-Smectite/Di-Smectite - Ca 2GLY.cmp",
    "dSht": "Di-Smectite/Di-Smectite - Ca Heated.cmp",
    # Tri-octahedral smectite
    "tS2w": "Tri-Smectite/Tri-Smectite - Ca 2WAT.cmp",
    "tS2g": "Tri-Smectite/Tri-Smectite - Ca 2GLY.cmp",
    "tSht": "Tri-Smectite/Tri-Smectite - Ca Heated.cmp",
    # Di-octahedral vermiculite
    "dV2w": "Di-Vermiculite/Di-Vermiculite - Ca 2WAT.cmp",
    "dV2g": "Di-Vermiculite/Di-Vermiculite - Ca 2GLY.cmp",
    "dVht": "Di-Vermiculite/Di-Vermiculite - Ca Heated.cmp",
}

# A treated (EG / 350) SMECTITE component reuses the air-dried layer structure -
# it links to the AD component and inherits its cell a/b, delta_c and layer atoms,
# keeping only its own interlayer (old inherit_S).
_INHERIT_S = dict(
    inherit_ucp_a=True, inherit_ucp_b=True,
    inherit_delta_c=True, inherit_layer_atoms=True,
)
# A treated FIXED component (illite / kaolinite / ...) is identical between
# treatments, so it inherits everything from the AD copy (old inherit_all).
_INHERIT_ALL = dict(
    inherit_d001=True, inherit_default_c=True,
    inherit_interlayer_atoms=True, inherit_atom_relations=True, **_INHERIT_S,
)
# A treated phase inherits its parent's visuals + orientation + CSDS (old
# inherit_phase; its inherit_probabilities is a no-op at G=1 - no free
# probabilities - so it is omitted here).
_INHERIT_PHASE = dict(
    inherit_display_color=True, inherit_sigma_star=True,
    inherit_CSDS_distribution=True,
)


def _expandable(family: str, ad: str, eg: str, ht: str) -> tuple:
    """One expandable-clay catalog entry: the Ca-AD / Ca-EG / Ca-350 triple,
    the EG + 350 phases based on AD and their components linked to AD's."""
    name = "%s R0 Ca" % family
    inh = {eg: dict(linked_with=ad, **_INHERIT_S),
           ht: dict(linked_with=ad, **_INHERIT_S)}
    return (name, [
        (dict(R=0, name="%s R0 Ca-AD" % family), ad, {}),
        (dict(R=0, name="%s R0 Ca-EG" % family, based_on="%s R0 Ca-AD" % family,
              **_INHERIT_PHASE), eg, inh),
        (dict(R=0, name="%s R0 Ca-350" % family, based_on="%s R0 Ca-AD" % family,
              **_INHERIT_PHASE), ht, inh),
    ])


def _interstratified(family: str, fixed: str, s_ad: str, s_eg: str, s_ht: str,
                     max_r: int = 2) -> list:
    """Mixed-layer entries (Illite-Smectite etc.): a fixed component (`fixed`)
    interstratified with a smectite, as Ca-AD / Ca-EG / Ca-350 at each modeled
    Reichweite (R0, and R1 which is G2 here). The treated phases inherit the
    AD's stacking ratio (inherit_probabilities); the fixed component inherits the
    AD's copy entirely, the smectite component only its layer structure."""
    entries = []
    for reichweite in range(max_r):
        if not is_modeled(reichweite, 2):  # G = 2 (fixed + one smectite)
            continue
        stem = "%s R%d Ca" % (family, reichweite)
        inh_eg = {fixed: dict(linked_with=fixed, **_INHERIT_ALL),
                  s_eg: dict(linked_with=s_ad, **_INHERIT_S)}
        inh_ht = {fixed: dict(linked_with=fixed, **_INHERIT_ALL),
                  s_ht: dict(linked_with=s_ad, **_INHERIT_S)}
        treated = dict(inherit_probabilities=True, **_INHERIT_PHASE)
        entries.append((stem, [
            (dict(R=reichweite, name="%s-AD" % stem), fixed + s_ad, {}),
            (dict(R=reichweite, name="%s-EG" % stem, based_on="%s-AD" % stem,
                  **treated), fixed + s_eg, inh_eg),
            (dict(R=reichweite, name="%s-350" % stem, based_on="%s-AD" % stem,
                  **treated), fixed + s_ht, inh_ht),
        ]))
    return entries


# (display name, [ (phase_kwargs, component-code, {part: component-overrides}) ])
_CATALOG: list = [
    ("Kaolinite", [(dict(R=0, name="Kaolinite"), "K   ", {})]),
    ("Illite", [(dict(R=0, name="Illite"), "I   ", {})]),
    ("Serpentine", [(dict(R=0, name="Serpentine"), "Se  ", {})]),
    ("Talc", [(dict(R=0, name="Talc"), "T   ", {})]),
    ("Chlorite", [(dict(R=0, name="Chlorite"), "C   ", {})]),
    ("Margarite", [(dict(R=0, name="Margarite"), "Ma  ", {})]),
    ("Leucophyllite", [(dict(R=0, name="Leucophyllite"), "L   ", {})]),
    ("Paragonite", [(dict(R=0, name="Paragonite"), "Pa  ", {})]),
    _expandable("Di-Smectite", "dS2w", "dS2g", "dSht"),
    _expandable("Tri-Smectite", "tS2w", "tS2g", "tSht"),
    _expandable("Di-Vermiculite", "dV2w", "dV2g", "dVht"),
    # Mixed-layer (interstratified) families: a fixed clay + a smectite, at R0
    # and R1(G2). Illite/Kaolinite/Talc pair with the di-smectite; Chlorite with
    # the tri-smectite (old CS uses tri-smectite).
    *_interstratified("Illite-Smectite", "I   ", "dS2w", "dS2g", "dSht"),
    *_interstratified("Kaolinite-Smectite", "K   ", "dS2w", "dS2g", "dSht"),
    *_interstratified("Talc-Smectite", "T   ", "dS2w", "dS2g", "dSht"),
    *_interstratified("Chlorite-Smectite", "C   ", "tS2w", "tS2g", "tSht"),
]


def _entry_is_modeled(descr: list) -> bool:
    return all(
        is_modeled(int(kw.get("R", 0)), max(len(code) // _CODE_LEN, 1))
        for kw, code, _props in descr
    )


def default_catalog_entries() -> list:
    """`[(display_name, descr)]` for every catalog entry MudLab2 can build."""
    return [(name, descr) for name, descr in _CATALOG if _entry_is_modeled(descr)]


def build_catalog_entry(descr: list, atom_type_map: dict | None = None) -> list:
    """Build the Phase objects for one catalog entry (old phaseworker). Loads the
    coded components, wires per-component `linked_with` and per-phase `based_on`
    within the entry, and applies the inherit flags. Returns [] if any phase in
    the entry is unmodeled. Atom types resolve against `atom_type_map` (the
    built-in library by default), shared across the entry so its phases reference
    one consistent set."""
    if not _entry_is_modeled(descr):
        return []
    if atom_type_map is None:
        atom_type_map = atom_type_library_map()

    phase_lookup: dict = {}
    component_lookup: dict = {}
    phases: list = []
    for phase_kwargs, code, comp_props in descr:
        kwargs = dict(phase_kwargs)
        reichweite = int(kwargs.pop("R", 0))
        name = kwargs.pop("name", "")
        based_on_name = kwargs.pop("based_on", None)
        inherit_probabilities = bool(kwargs.pop("inherit_probabilities", False))
        parts = [code[i:i + _CODE_LEN] for i in range(0, len(code), _CODE_LEN)]
        g = max(len(parts), 1)

        phase = Phase.create_empty(G=g, R=reichweite, name=name)
        phase.components = []
        for part in parts:
            for component in load_default_component(_ALIASES[part], atom_type_map):
                phase.components.append(component)
                for prop, value in comp_props.get(part, {}).items():
                    if prop == "linked_with":
                        target = component_lookup.get(value)
                        component.linked_with = target
                        component._linked_with_uuid = target.uuid if target else ""
                    else:
                        setattr(component, prop, value)
                component_lookup[part] = component
        phase.G = len(phase.components)

        if based_on_name and based_on_name in phase_lookup:
            phase.set_based_on(phase_lookup[based_on_name])
            # inherit the parent's stacking ratio (a no-op at G=1 - no free
            # probabilities). Must follow set_based_on, which links the models.
            if inherit_probabilities:
                phase.probabilities.inherit_all()
        for flag, value in kwargs.items():  # remaining kwargs are phase inherit_*
            if hasattr(phase, flag):
                setattr(phase, flag, value)

        phase_lookup[name] = phase
        phases.append(phase)
    return phases


def build_catalog_entry_by_name(display_name: str,
                                atom_type_map: dict | None = None) -> list:
    """Build the entry whose Add-Phase display name is `display_name`."""
    for name, descr in _CATALOG:
        if name == display_name:
            return build_catalog_entry(descr, atom_type_map)
    return []


def add_catalog_entry_to_project(project, display_name: str) -> list:
    """Build the named catalog entry and add its phases to `project`, merging
    their atom types in BY NAME: an atom type the project already has is reused
    (the built atoms re-point to it), one it lacks is adopted from the library.
    So a default phase computes immediately and never duplicates an existing
    atom type. Returns the added phases ([] if the entry is unknown/unmodeled)."""
    phases = build_catalog_entry_by_name(display_name)
    if not phases:
        return []
    by_name = {atom_type.name: atom_type for atom_type in project.atom_types}
    for phase in phases:
        for component in phase.components:
            for atom in list(component._layer_atoms) + list(component._interlayer_atoms):
                atom_type = atom.atom_type
                if atom_type is None:
                    continue
                existing = by_name.get(atom_type.name)
                if existing is None:
                    project.add_atom_type(atom_type)  # adopt the library type
                    by_name[atom_type.name] = atom_type
                elif existing is not atom_type:
                    atom.atom_type = existing  # dedup onto the project's own
        project.add_phase(phase)
    return phases
