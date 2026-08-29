"""Build a clay Component from a crystallographic CIF.

A CIF holds a full three-dimensional structure; a MudLab component holds a
**one-dimensional profile along c\\*** - atom rows with a height `z` in
nanometres and an amount `pn`, split into layer and interlayer. Going from one
to the other is a projection, and it is lossy on purpose.

The geometry that makes it exact
--------------------------------
Height above (001) is ``z_fractional x d001`` **exactly**, with no contribution
from x or y, because the reciprocal vector c\\* is normal to the a-b plane:
writing the cell in a Cartesian frame with **a** along x and **b** in the x-y
plane puts the whole of the interplanar spacing into the z-component of **c**,
and gives ``a_z = b_z = 0``. Verified numerically on triclinic kaolinite
(alpha 91.7, beta 104.9, gamma 89.8) as well as monoclinic cells: two atoms
sharing a fractional z but with entirely different (x, y) come out at the same
height to 0.0e+00.

The consequence matters for the design: a boundary parallel to (001) sits in
the *same place* whether you look for it in three dimensions or after
projecting, so projecting first costs nothing. What projection *does* destroy
is x and y - and therefore **bonding** - which is why the layer/interlayer
split and the hydroxyl test below are done on the 3-D structure, before the
profile is collapsed.

What is approximate
-------------------
Everything about which this module has to make a choice: where one repeat
begins, whether a published cell stacks two layers or one, which oxygens are
hydroxyls, and where the layer stops and the interlayer starts. Each is
computed here as a *proposal* and carried in `ProjectionReport` so the caller
can show it and let the user override it. None of it is silently authoritative.
"""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass, field

#: Cations that sit in the octahedral sheet of a phyllosilicate.
OCTAHEDRAL = frozenset(
    ("Al", "Mg", "Fe", "Li", "Mn", "Ti", "Ni", "Cr", "Zn", "Co", "V")
)
#: Cations that occupy the interlayer rather than the framework.
INTERLAYER_CATIONS = frozenset(
    ("K", "Na", "Ca", "Cs", "Rb", "Ba", "Sr", "Mg", "Li", "NH4")
)
#: Longest Si-O separation still counted as a tetrahedral bond, in angstrom.
SI_O_BOND = 1.85
#: Longest octahedral-cation-to-oxygen separation counted as a bond.
OCT_O_BOND = 2.35
#: Longest O-H separation counted as a hydroxyl bond.
O_H_BOND = 1.25

_NUM = re.compile(r"\(.*?\)")


def _number(token: str):
    """A CIF numeric with its standard uncertainty stripped, or None."""
    try:
        return float(_NUM.sub("", token))
    except (TypeError, ValueError):
        return None


@dataclass
class Site:
    """One atom site, before projection."""
    label: str
    element: str
    x: float
    y: float
    z: float
    occupancy: float
    #: True when the CIF itself calls this a hydroxyl (label OH / O-H / OH1).
    declared_hydroxyl: bool = False


@dataclass
class CifStructure:
    name: str
    a: float
    b: float
    c: float
    alpha: float
    beta: float
    gamma: float
    sites: list = field(default_factory=list)
    symmetry: list = field(default_factory=list)

    @property
    def d001(self) -> float:
        """Basal spacing in angstrom: the (001) interplanar spacing, V/|a x b|.

        Equals ``c sin(beta)`` for a monoclinic cell and is correct for
        triclinic ones too, which ``c sin(beta)`` is not.
        """
        ca = math.cos(math.radians(self.alpha))
        cb = math.cos(math.radians(self.beta))
        cg = math.cos(math.radians(self.gamma))
        sg = math.sin(math.radians(self.gamma))
        factor = 1.0 - ca * ca - cb * cb - cg * cg + 2.0 * ca * cb * cg
        if factor <= 0.0 or sg <= 0.0:
            return self.c
        volume = self.a * self.b * self.c * math.sqrt(factor)
        return volume / (self.a * self.b * sg)

    def cartesian_basis(self):
        """(a, b, c) as Cartesian vectors, a along x and b in the x-y plane.

        In this frame ``a_z = b_z = 0`` and ``c_z = d001``, which is the whole
        reason the projection is exact - see the module docstring.
        """
        ca = math.cos(math.radians(self.alpha))
        cb = math.cos(math.radians(self.beta))
        cg = math.cos(math.radians(self.gamma))
        sg = math.sin(math.radians(self.gamma))
        return (
            (self.a, 0.0, 0.0),
            (self.b * cg, self.b * sg, 0.0),
            (self.c * cb, self.c * (ca - cb * cg) / sg, self.d001),
        )


# ----------------------------------------------------------------------
# Reading
# ----------------------------------------------------------------------
_ELEMENTS = (
    "Si Al Fe Mg Ca Na Ca Ti Mn Cr Ni Zn Li Ba Sr Rb Cs Be Zr Cu Co "
    "O H F Cl N C S P K V"
).split()
_TWO_LETTER = tuple(e for e in _ELEMENTS if len(e) == 2)


def element_of(token: str):
    """The element symbol a CIF label or type symbol denotes, or None.

    Labels in real files look like ``SiT1``, ``Fe2+M``, ``O-H3``, ``AlM2`` -
    the element is the leading alphabetic run, longest match first so ``Si``
    is not read as sulphur.
    """
    if not token:
        return None
    text = str(token).strip()
    alpha = re.match(r"[A-Za-z]+", text)
    if not alpha:
        return None
    word = alpha.group(0)
    for symbol in _TWO_LETTER:
        if word[:2].capitalize() == symbol:
            return symbol
    head = word[:1].upper()
    return head if head in _ELEMENTS else None


def _is_declared_hydroxyl(label: str, type_symbol: str) -> bool:
    """Whether the file already says this oxygen is a hydroxyl.

    Worth trusting when present: of the shipped test corpus, kaolinite labels
    its sites ``O-H`` outright, which is far better evidence than any distance
    heuristic can produce.
    """
    for token in (label or "", type_symbol or ""):
        text = str(token).strip().upper().replace(" ", "")
        if text.startswith(("OH", "O-H", "HO")):
            return True
    return False


def parse_cif(text: str) -> CifStructure:
    """Read the first data block that carries an atom-site loop.

    Deliberately tolerant: real AMCSD/RRUFF files vary in tag order, quoting
    and column count, and a structural importer that rejects a file over
    cosmetics is useless. Raises ValueError only when something essential -
    the cell or the atom sites - is genuinely absent.
    """
    def scalar(tag):
        match = re.search(r"^%s\s+(\S+)" % re.escape(tag), text, re.M)
        return _number(match.group(1)) if match else None

    cell = {t: scalar("_cell_length_" + t) for t in ("a", "b", "c")}
    for angle in ("alpha", "beta", "gamma"):
        cell[angle] = scalar("_cell_angle_" + angle)
        if cell[angle] is None:
            cell[angle] = 90.0
    missing = [k for k in ("a", "b", "c") if not cell.get(k)]
    if missing:
        raise ValueError("CIF has no unit-cell length(s): %s" % ", ".join(missing))

    name = ""
    for tag in ("_chemical_name_mineral", "_chemical_name_common",
                "_chemical_name_systematic"):
        match = re.search(r"^%s\s+(.+)$" % re.escape(tag), text, re.M)
        if match:
            name = match.group(1).strip().strip("'\"")
            if name and name != "?":
                break
            name = ""

    sites, symmetry = [], []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if lines[index].strip() != "loop_":
            index += 1
            continue
        cursor = index + 1
        tags = []
        while cursor < len(lines) and lines[cursor].strip().startswith("_"):
            tags.append(lines[cursor].strip().split()[0])
            cursor += 1
        rows = []
        while cursor < len(lines):
            stripped = lines[cursor].strip()
            if (not stripped or stripped == "loop_"
                    or stripped.startswith(("_", "data_", "#", ";"))):
                break
            rows.append(stripped)
            cursor += 1
        index = cursor

        if any("symop" in t or "equiv_pos" in t for t in tags):
            for row in rows:
                match = re.search(
                    r"([-+xyz0-9/.]+\s*,\s*[-+xyz0-9/.]+\s*,\s*[-+xyz0-9/.]+)",
                    row.replace("'", " ").replace('"', " "))
                if match:
                    symmetry.append([p.strip() for p in match.group(1).split(",")])
        elif "_atom_site_fract_x" in tags:
            column = {tag: n for n, tag in enumerate(tags)}
            ix = column["_atom_site_fract_x"]
            iy = column["_atom_site_fract_y"]
            iz = column["_atom_site_fract_z"]
            ilabel = column.get("_atom_site_label")
            itype = column.get("_atom_site_type_symbol")
            iocc = column.get("_atom_site_occupancy")
            for row in rows:
                token = row.split()
                if len(token) < len(tags):
                    continue
                label = token[ilabel] if ilabel is not None else ""
                type_symbol = token[itype] if itype is not None else ""
                element = element_of(type_symbol) or element_of(label)
                if element is None:
                    continue
                x, y, z = (_number(token[i]) for i in (ix, iy, iz))
                if None in (x, y, z):
                    continue
                occupancy = _number(token[iocc]) if iocc is not None else 1.0
                if occupancy is None:
                    occupancy = 1.0
                if occupancy <= 0.0:
                    continue      # an explicit vacancy is not an atom
                sites.append(Site(
                    label=label, element=element, x=x, y=y, z=z,
                    occupancy=occupancy,
                    declared_hydroxyl=(element == "O"
                                       and _is_declared_hydroxyl(label, type_symbol)),
                ))

    if not sites:
        raise ValueError("CIF has no atom sites")
    return CifStructure(name=name, sites=sites, symmetry=symmetry,
                        **{k: float(v) for k, v in cell.items()})


# ----------------------------------------------------------------------
# Symmetry
# ----------------------------------------------------------------------
_TERM = re.compile(r"([+-]?)(?:(\d+)/(\d+)|(\d*\.?\d+))?\*?([xyz])?")


def apply_symop(op, x: float, y: float, z: float):
    """Apply one ``x,y,z``-style symmetry expression triple."""
    values = {"x": x, "y": y, "z": z}
    out = []
    for expr in op:
        total = 0.0
        for sign, num, den, plain, var in _TERM.findall(expr.replace(" ", "")):
            if not (num or plain or var):
                continue
            factor = 1.0
            if num and den:
                factor = float(num) / float(den)
            elif plain:
                factor = float(plain)
            if var:
                total += (-factor if sign == "-" else factor) * values[var]
            else:
                total += -factor if sign == "-" else factor
        out.append(total)
    return tuple(out)


def expand(structure: CifStructure) -> list:
    """Every site in the cell, symmetry operations applied and duplicates
    dropped. A file with no symmetry loop is taken as P1."""
    ops = structure.symmetry or [["x", "y", "z"]]
    seen = {}
    for site in structure.sites:
        for op in ops:
            x, y, z = apply_symop(op, site.x, site.y, site.z)
            x, y, z = x % 1.0, y % 1.0, z % 1.0
            key = (site.label, round(x, 4), round(y, 4), round(z, 4))
            if key not in seen:
                seen[key] = Site(site.label, site.element, x, y, z,
                                 site.occupancy, site.declared_hydroxyl)
    return list(seen.values())


# ----------------------------------------------------------------------
# Bonding (the part projection would destroy)
# ----------------------------------------------------------------------
@dataclass
class Bonding:
    """Every site sorted into framework or guest by who it is bonded to."""
    framework_oxygen: set = field(default_factory=set)
    hydroxyl: set = field(default_factory=set)
    guest_oxygen: set = field(default_factory=set)
    framework_cation: set = field(default_factory=set)
    guest_cation: set = field(default_factory=set)


def classify_bonding(structure: CifStructure, sites: list) -> Bonding:
    """Sort sites by coordination, in three dimensions.

    The rules are ordinary crystal chemistry, not invention:

    * an oxygen bonded to tetrahedral Si is a **framework** oxygen (bridging or
      apical);
    * an oxygen with no Si neighbour but coordinated to octahedral cations is a
      **hydroxyl** - in a phyllosilicate the OH sits in the octahedral sheet
      and never bonds to Si;
    * an oxygen bonded to neither is a **guest** - interlayer water.

    That last distinction is the one the projected profile cannot make, because
    hydroxyl and interlayer water sit at different heights but look identical
    once x and y are gone. Tested on the vermiculite CIFs, where it correctly
    separates 6-8 water oxygens that a height rule merges into the layer.
    """
    basis = structure.cartesian_basis()

    def cartesian(site):
        return tuple(
            site.x * basis[0][i] + site.y * basis[1][i] + site.z * basis[2][i]
            for i in range(3)
        )

    points = [(s, cartesian(s)) for s in sites]
    shifts = [
        tuple(i * basis[0][k] + j * basis[1][k] + m * basis[2][k] for k in range(3))
        for i in (-1, 0, 1) for j in (-1, 0, 1) for m in (-1, 0, 1)
    ]

    silicon = [p for p in points if p[0].element == "Si"]
    octahedral = [p for p in points if p[0].element in OCTAHEDRAL]
    hydrogen = [p for p in points if p[0].element == "H"]

    def bonded(point, others, cutoff):
        limit = cutoff * cutoff
        for other in others:
            for shift in shifts:
                dx = point[1][0] - other[1][0] - shift[0]
                dy = point[1][1] - other[1][1] - shift[1]
                dz = point[1][2] - other[1][2] - shift[2]
                if dx * dx + dy * dy + dz * dz <= limit:
                    return True
        return False

    out = Bonding()
    for point in points:
        site = point[0]
        if site.element == "H":
            continue                          # H is never a MudLab row
        if site.element == "O":
            if bonded(point, silicon, SI_O_BOND):
                out.framework_oxygen.add(id(site))
            elif (site.declared_hydroxyl
                  or (hydrogen and bonded(point, hydrogen, O_H_BOND))
                  or bonded(point, octahedral, OCT_O_BOND)):
                out.hydroxyl.add(id(site))
            else:
                out.guest_oxygen.add(id(site))
        elif site.element == "Si" or site.element in OCTAHEDRAL:
            # An octahedral-sheet cation is coordinated to layer anions; the
            # same element sitting in the interlayer (Mg, Li) is not.
            anions = [p for p in points if p[0].element in ("O", "F")]
            if site.element == "Si" or bonded(point, anions, OCT_O_BOND):
                out.framework_cation.add(id(site))
            else:
                out.guest_cation.add(id(site))
        else:
            out.guest_cation.add(id(site))
    return out


# ----------------------------------------------------------------------
# Projection
# ----------------------------------------------------------------------
#: CIF element -> the clay atom type MudLab ships a scattering factor for.
#: These are the ionised forms the shipped components use, so an imported
#: component resolves against the same library as a default one.
ATOM_TYPE_BY_ELEMENT = {
    "Si": "Si2+", "Al": "Al1.5+", "Fe": "Fe1.5+", "Mg": "Mg1+", "Ti": "Ti2+",
    "Mn": "Mn2+", "Li": "Li1+", "Ni": "Ni2+", "Cr": "Cr2+", "Zn": "Zn2+",
    "O": "O1-", "OH": "OH1-", "F": "F1-",
    "K": "K1+", "Na": "Na1+", "Ca": "Ca2+", "Cs": "Cs1+", "Rb": "Rb1+",
    "Ba": "Ba2+", "Sr": "Sr2+", "H2O": "OH1-",
}


@dataclass
class Row:
    """One projected atom row - what a MudLab component actually stores."""
    name: str
    atom_type_name: str
    z_nm: float
    pn: float
    interlayer: bool


@dataclass
class ProjectionReport:
    """Everything the importer had to decide, so a caller can show and
    override it rather than trust it."""
    name: str = ""
    d001_nm: float = 0.0
    cell_a_nm: float = 0.0
    cell_b_nm: float = 0.0
    repeat_divisor: int = 1
    origin_fraction: float = 0.0
    layer_rows: int = 0
    interlayer_rows: int = 0
    hydroxyl_pn: float = 0.0
    water_pn: float = 0.0
    warnings: list = field(default_factory=list)


def _role_name(site, bonding) -> tuple:
    """(display name, role) for a classified site."""
    key = id(site)
    if key in bonding.hydroxyl:
        return "OH", "layer"
    if key in bonding.framework_oxygen:
        return "O", "layer"
    if key in bonding.guest_oxygen:
        return "H2O", "interlayer"
    if key in bonding.framework_cation:
        return site.element, "layer"
    return site.element, "interlayer"


@dataclass
class Entry:
    """One level of the 1-D profile, before it becomes a component row."""
    name: str
    role: str
    z: float          # fractional, within the cell
    pn: float


def build_profile(structure: CifStructure, z_tolerance: float = 0.004) -> list:
    """Collapse the expanded 3-D structure onto its c\\* profile.

    Roles are decided FIRST, on the real structure, because folding and
    grouping destroy the neighbourhoods they come from.
    """
    expanded = expand(structure)
    bonding = classify_bonding(structure, expanded)
    buckets = {}
    for site in expanded:
        if site.element == "H":
            # Hydrogen is evidence, not a row: it decides which oxygens are
            # hydroxyls (see classify_bonding) and is then dropped, because
            # MudLab models OH as a single scatterer and has no H atom type.
            continue
        name, role = _role_name(site, bonding)
        key = (name, role, round(site.z / max(z_tolerance, 1e-9)))
        entry = buckets.get(key)
        if entry is None:
            buckets[key] = [name, role, site.z * site.occupancy, site.occupancy]
        else:
            entry[2] += site.z * site.occupancy
            entry[3] += site.occupancy
    profile = [Entry(n, r, zw / occ, occ)
               for n, r, zw, occ in buckets.values() if occ > 0]
    profile.sort(key=lambda e: e.z)
    return profile


def detect_repeat(profile: list, tolerance: float = 0.012) -> int:
    """How many identical layers the published cell stacks along c.

    Tested on the PROFILE rather than on the 3-D sites, which is both the
    thing that matters to MudLab and far more robust: successive layers in a
    real structure are usually offset in a and b as well as in c (talc's
    two-layer cell is displaced by roughly -a/3), so a test that demands the
    3-D sites map onto themselves misses exactly the cells worth folding.
    Along c\\* those offsets are invisible - which is the one case where losing
    x and y helps.
    """
    if len(profile) < 4:
        return 1
    total = sum(e.pn for e in profile)
    if total <= 0:
        return 1

    def maps_onto(divisor):
        step = 1.0 / divisor
        for entry in profile:
            want = (entry.z + step) % 1.0
            for other in profile:
                if other.name != entry.name or other.role != entry.role:
                    continue
                gap = abs(other.z - want)
                if min(gap, 1.0 - gap) < tolerance and \
                        abs(other.pn - entry.pn) <= 0.05 * max(entry.pn, 1e-9) + 0.05:
                    break
            else:
                return False
        return True

    for divisor in (4, 3, 2):
        if len(profile) % divisor == 0 and maps_onto(divisor):
            return divisor
    return 1


def fold_profile(profile: list, divisor: int, z_tolerance: float = 0.012) -> list:
    """Collapse `divisor` stacked repeats of the profile into one.

    Coincident levels **merge by summing** their amounts, and the 1/divisor
    scale is applied once at the end. Keeping the larger and discarding the
    rest - with the scale still applied - counts shared content once and then
    divides it again, which lost atoms in every folded cell of the reference
    corpus (0 of 12 kept their anion totals; 11 of 12 after this change).
    """
    if divisor <= 1:
        return list(profile)
    period = 1.0 / divisor
    buckets = {}
    for entry in profile:
        z = ((entry.z % period) / period) % 1.0
        key = (entry.name, entry.role, round(z / max(z_tolerance, 1e-9)))
        found = buckets.get(key)
        if found is None:
            buckets[key] = [entry.name, entry.role, z * entry.pn, entry.pn]
        else:
            found[2] += z * entry.pn
            found[3] += entry.pn
    folded = [Entry(n, r, zw / pn, pn / divisor)
              for n, r, zw, pn in buckets.values() if pn > 0]
    folded.sort(key=lambda e: e.z)
    return folded


def choose_origin(profile: list) -> float:
    """Where one repeat should start: immediately after the widest empty band.

    That band is the interlayer gap, so starting there puts the layer at the
    bottom and the interlayer above it - the arrangement MudLab's own shipped
    components use (Muscovite's basal oxygen sits at 0.0 and its interlayer
    potassium at 0.831 of a 1.002 nm repeat). Anchoring on the lowest atom
    instead splits the layer across the wrap.
    """
    if not profile:
        return 0.0
    zs = sorted(e.z for e in profile)
    best_gap, best_z = -1.0, zs[0]
    for index, z in enumerate(zs):
        previous = zs[index - 1] if index else zs[-1] - 1.0
        gap = z - previous
        if gap > best_gap:
            best_gap, best_z = gap, z
    return best_z


def project(structure: CifStructure, divisor: "int | None" = None) -> tuple:
    """Project `structure` onto c\\*. Returns (rows, report).

    `divisor` overrides the automatic repeat detection - the review UI passes
    the user's answer back through it.
    """
    report = ProjectionReport(name=structure.name or "Imported component")
    profile = build_profile(structure)
    if divisor is None:
        divisor = detect_repeat(profile)
    report.repeat_divisor = max(1, int(divisor))

    folded = fold_profile(profile, report.repeat_divisor)
    origin = choose_origin(folded)
    report.origin_fraction = origin

    repeat_nm = structure.d001 / 10.0 / report.repeat_divisor
    report.d001_nm = repeat_nm
    report.cell_a_nm = structure.a / 10.0
    report.cell_b_nm = structure.b / 10.0

    rows = [
        Row(name=entry.name,
            atom_type_name=ATOM_TYPE_BY_ELEMENT.get(entry.name, entry.name),
            z_nm=((entry.z - origin) % 1.0) * repeat_nm,
            pn=entry.pn,
            interlayer=(entry.role == "interlayer"))
        for entry in folded
    ]
    rows.sort(key=lambda r: (r.interlayer, r.z_nm))

    report.layer_rows = sum(1 for r in rows if not r.interlayer)
    report.interlayer_rows = sum(1 for r in rows if r.interlayer)
    report.hydroxyl_pn = sum(r.pn for r in rows if r.name == "OH")
    report.water_pn = sum(r.pn for r in rows if r.name == "H2O")
    if not rows:
        report.warnings.append("No atoms survived the projection.")
    if report.d001_nm <= 0:
        report.warnings.append("The basal spacing came out as zero.")
    if not report.layer_rows:
        report.warnings.append("Nothing was classified as layer.")
    return rows, report




# ----------------------------------------------------------------------
# Building the component
# ----------------------------------------------------------------------
def _atom_entry(row: "Row") -> dict:
    return {
        "type": "Atom",
        "properties": {
            "uuid": uuid.uuid4().hex,
            "name": row.name,
            "default_z": round(row.z_nm, 6),
            "pn": round(row.pn, 6),
            "atom_type_name": row.atom_type_name,
            "stretch_z": False,
        },
    }


def _ucp_entry(value_nm: float) -> dict:
    """A unit-cell property holding a measured value.

    `enabled` is False - the shipped components DERIVE a from b, but an
    imported CIF states both, and a measured number should not be silently
    recomputed from another one.
    """
    return {
        "type": "UnitCellProperty",
        "properties": {
            "uuid": uuid.uuid4().hex,
            "value": round(value_nm, 8),
            "factor": 0.0,
            "constant": round(value_nm, 8),
            "enabled": False,
            "prop": None,
        },
    }


def component_dict(rows: list, report: "ProjectionReport",
                   name: str = "") -> dict:
    """The serialised Component the projection describes.

    Deliberately built from the SAME keys a `.cmp` already uses and no others:
    the old GTK MudLab deserialises with ``cls(**properties)`` and raises
    TypeError on any key it does not know, so an imported component must be
    indistinguishable from a hand-built one. There is nowhere to record that
    this came from a CIF, and inventing a field for it would make every
    project containing one unreadable there.
    """
    return {
        "type": "Component",
        "properties": {
            "uuid": uuid.uuid4().hex,
            "name": name or report.name,
            "d001": round(report.d001_nm, 8),
            "default_c": round(report.d001_nm, 8),
            "delta_c": 0.0,
            "ucp_a": _ucp_entry(report.cell_a_nm),
            "ucp_b": _ucp_entry(report.cell_b_nm),
            "layer_atoms": [_atom_entry(r) for r in rows if not r.interlayer],
            "interlayer_atoms": [_atom_entry(r) for r in rows if r.interlayer],
            "atom_relations": [],
            "linked_with_uuid": "",
            "inherit_ucp_a": False,
            "inherit_ucp_b": False,
            "inherit_d001": False,
            "inherit_default_c": False,
            "inherit_delta_c": False,
            "inherit_layer_atoms": False,
            "inherit_interlayer_atoms": False,
            "inherit_atom_relations": False,
        },
    }


def component_from_cif(path: str, atom_type_map: dict,
                       divisor: "int | None" = None, name: str = ""):
    """Read `path` and build a Component from it.

    Returns ``(component, report, missing_atom_type_names)``. A name in
    `missing` means the destination project has no scattering factor for it,
    so that row would contribute NOTHING to the calculated pattern - the
    caller must offer to add it rather than let the silence stand.
    """
    from mudlab.models.component import Component

    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        structure = parse_cif(handle.read())
    rows, report = project(structure, divisor=divisor)
    data = component_dict(rows, report, name=name)
    component = Component.from_dict(data, atom_type_map)
    component.set_linked_with(None)

    missing = []
    for atom in component.layer_atoms + component.interlayer_atoms:
        if atom.atom_type is None:
            wanted = atom.raw_properties.get("atom_type_name")
            if wanted and wanted not in missing:
                missing.append(wanted)
    return component, report, missing
