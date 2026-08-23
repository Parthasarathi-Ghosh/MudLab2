"""Typographic cross-section diagram for a Component.

Port of the old app's `phases/models/component_diagram.py`, which backed its
component pane's **Show Structure** button. It draws the layer as text, bottom
to top: the d001 boundary, the interlayer, `lattice_d`, then the tetrahedral /
octahedral sheets with every atom's z, name, `pn` and type - and closes with the
charge balance.

Deliberate differences from the old module:

* **Line endings are "\\n", not CRLF.** The old one wrote CRLF for a GtkTextView;
  a Qt text widget shows a stray CR as a control glyph. Qt normalises on
  display, so "\\n" is the correct spelling here.
* **No "Generated" timestamp.** It made two diagrams of the same unchanged
  component differ, which is exactly what you do not want when comparing one
  against another - and it was the only thing standing between this function and
  being pure.
* Relation types are read from the model's own `type` property rather than
  `type(rel).__name__`.

Kept free of Qt so it can be tested (and diffed) without a widget.
"""

from __future__ import annotations

_SEP = "═" * 52          # major boundary line
_MID = "─" * 52          # zone separator

#: Gap between consecutive atom z-values that starts a new structural zone.
#: 0.07 nm separates the tet / oct clusters cleanly for every default component
#: without splitting one of them in two.
_GAP_NM = 0.07

_NAME_WIDTH = 14         # atom-name column width

#: Element prefixes that mark a cluster as an octahedral sheet.
_OCTAHEDRAL = ("AL", "MG", "FE", "CR", "NI", "ZN", "CU")


def _cluster_layer_atoms(atoms) -> list:
    """Layer atoms grouped into clusters separated by z-gaps > `_GAP_NM`,
    ordered bottom to top."""
    if not atoms:
        return []
    ordered = sorted(atoms, key=lambda a: a.default_z)
    clusters = [[ordered[0]]]
    for atom in ordered[1:]:
        if atom.default_z - clusters[-1][-1].default_z > _GAP_NM:
            clusters.append([])
        clusters[-1].append(atom)
    return clusters


def _zone_label(cluster) -> str:
    """"TETRAHEDRAL SHEET" / "OCTAHEDRAL SHEET", or "" for a plane of oxygens
    or hydroxyls, which is a boundary rather than a sheet."""
    names = [(a.atom_type.name if a.atom_type else "").upper() for a in cluster]
    if any(n.startswith("SI") for n in names):
        return "TETRAHEDRAL SHEET"
    if any(n.startswith(prefix) for n in names for prefix in _OCTAHEDRAL):
        return "OCTAHEDRAL SHEET"
    return ""


def _pn_str(pn) -> str:
    """Whole numbers as "6.0", anything else to three decimals - a substituted
    site's 3.500 must not round away to 4."""
    pn = float(pn)
    return "%.1f" % pn if pn == int(pn) else "%.3f" % pn


def _name(atom) -> str:
    """The atom's name, truncated so the column stays aligned."""
    name = atom.name or "?"
    return name if len(name) < _NAME_WIDTH else name[:_NAME_WIDTH - 1] + "…"


def _atom_type_name(atom) -> str:
    return atom.atom_type.name if atom.atom_type else "?"


def _interlayer_label(relations) -> str:
    """A one-line summary of what the atom relations put in the interlayer."""
    parts = []
    for relation in relations:
        kind = getattr(relation, "type", type(relation).__name__)
        if not getattr(relation, "enabled", False):
            continue
        if kind == "AtomContents":
            parts.append("%s = %s" % (relation.name, _pn_str(relation.value)))
        elif kind == "AtomRatio":
            first, second = relation.atom1, relation.atom2
            if not (first and second):
                continue
            one = getattr(first[0], "name", "?")
            two = getattr(second[0], "name", "?")
            parts.append("%s  %s:%s = %.0f:%.0f" % (
                relation.name, one, two,
                relation.value * 10, (1 - relation.value) * 10))
    return "  |  ".join(parts)


def build_structure_diagram(component, phase_name: str = "") -> str:
    """The cross-section of `component` as text.

    Reads the LIVE model, so it reflects whatever the atom relations have
    already applied - call it after they have run, which is any time the editor
    is showing settled values.

    `phase_name` is passed IN rather than read off the component: the old app's
    Component had a `.phase` back-reference and MudLab2's does not, and adding
    one just to label a diagram would put a cycle into the object graph that
    the serialiser and the snapshot-on-detach code would both have to know
    about. The editor knows which phase it is showing, so it says so.
    """
    d001 = component.d001
    default_c = component.default_c
    layer_atoms = list(component.layer_atoms)
    inter_atoms = list(component.interlayer_atoms)
    relations = list(component.atom_relations)

    # lattice_d is the runtime top of the layer, not a stored field.
    lattice_d = max((a.default_z for a in layer_atoms), default=0.0)
    denominator = default_c - lattice_d
    z_factor = ((d001 - lattice_d) / denominator
                if abs(denominator) > 1e-9 else 1.0)

    def calc_z(atom):
        """Where an interlayer atom actually sits once the layer is stretched
        from its default c to the current d001."""
        return lattice_d + (atom.default_z - lattice_d) * z_factor

    # A back-reference is still honoured if one ever appears.
    phase_name = (phase_name
                  or getattr(getattr(component, "phase", None), "name", "")
                  or "—")

    lines = [
        _SEP,
        "  MudLab — Component Structure Diagram",
        _SEP,
        "  Component : %s" % (component.name or "(unnamed)"),
        "  Phase     : %s" % phase_name,
        "  d001      : %.4f nm      default c : %.4f nm" % (d001, default_c),
        _SEP,
        "",
        "           ← bottom of adjacent layer",
        "",
        "z = %.4f nm  %s  d001" % (d001, _SEP[:22]),
        "",
    ]

    # ---------------------------------------------------------- interlayer
    if inter_atoms:
        summary = _interlayer_label(relations)
        lines.append("  ·  INTERLAYER")
        if summary:
            lines.append("  ·  %s" % summary)
        lines.append("  ·")
        for atom in sorted(inter_atoms, key=calc_z, reverse=True):
            lines.append("z = %.4f nm  ·  %-14s  pn = %-7s  %s" % (
                calc_z(atom), _name(atom), _pn_str(atom.pn),
                _atom_type_name(atom)))
        lines.append("")
    else:
        lines.append("  │  (no interlayer — charge-neutral or structural)")
        lines.append("")

    lines.append("z = %.4f nm  %s  lattice_d" % (lattice_d, _SEP[:22]))

    # --------------------------------------------------- the layer itself
    clusters = _cluster_layer_atoms(layer_atoms)
    tetrahedral = [c for c in clusters if _zone_label(c) == "TETRAHEDRAL SHEET"]
    # Two tetrahedral sheets means a 2:1 clay, and then they are worth naming
    # lower and upper; one means a 1:1 clay, where the distinction is empty.
    if len(tetrahedral) >= 2:
        tet_labels = ["LOWER TETRAHEDRAL SHEET", "UPPER TETRAHEDRAL SHEET"]
    elif len(tetrahedral) == 1:
        tet_labels = ["TETRAHEDRAL SHEET"]
    else:
        tet_labels = []
    tet_index = 0

    for cluster in reversed(clusters):   # drawn top-down
        label = _zone_label(cluster)
        if label == "TETRAHEDRAL SHEET":
            # Counting down from the top, so the FIRST one drawn is the upper.
            actual = tet_labels[-(tet_index + 1)] if tet_labels else label
            tet_index += 1
            lines.append("  │  %s  %s" % (_MID[:4], actual))
        elif label == "OCTAHEDRAL SHEET":
            lines.append("  │  %s  OCTAHEDRAL SHEET  —  %s"
                         % (_MID[:4], _octahedral_summary(cluster)))
        else:
            lines.append("  │")
        for atom in sorted(cluster, key=lambda a: a.default_z, reverse=True):
            lines.append("z = %.4f nm  │  %-14s  pn = %-7s  %s" % (
                atom.default_z, _name(atom), _pn_str(atom.pn),
                _atom_type_name(atom)))

    lines += [
        "",
        "z = 0.0000 nm  %s  z = 0" % _SEP[:22],
        "",
        "           ← top of adjacent layer below",
        "",
    ]

    # ------------------------------------------------------ charge balance
    try:
        layer_q, inter_q, net = component.compute_charge_balance()
    except Exception:  # noqa: BLE001 - a diagram must not fail on arithmetic
        pass
    else:
        lines += [
            _SEP,
            "  Charge balance (per unit cell):",
            "    Layer:       %+.3f" % layer_q,
            "    Interlayer:  %+.3f" % inter_q,
            "    Net:         %+.3f   %s" % (
                net, "[ok] balanced" if abs(net) <= 0.05 else "[!] imbalanced"),
            _SEP,
            "  NB atom_type.charge is the SCATTERING ion, not a formal charge,",
            "  so a stock clay can read imbalanced by construction.",
            _SEP,
        ]

    return "\n".join(lines)


def _octahedral_summary(cluster) -> str:
    """"Al pn=4.0  +  Mg pn=0.5   (dioctahedral, 4 sites/uc)" - the cations
    only; the oxygens and hydroxyls are listed atom by atom below."""
    parts = []
    occupancy = 0.0
    for atom in sorted(cluster, key=lambda a: a.default_z):
        type_name = _atom_type_name(atom)
        if not type_name.upper().startswith(("O", "H")):
            parts.append("%s pn=%s" % (atom.name, _pn_str(atom.pn)))
            occupancy += float(atom.pn)
    summary = "  +  ".join(parts)
    if occupancy > 0:
        sites = int(round(occupancy))
        kind = "dioctahedral" if sites <= 4 else "trioctahedral"
        summary += "   (%s, %d sites/uc)" % (kind, sites)
    return summary
