"""CIF atom-site labels that do not begin with their element symbol.

Both CIF readers - the clay-component importer (`cif_component`) and the
non-clay reference builder (`nonclay.structure`) - take an atom's element from
the leading letters of its type symbol or label. That works for the labels
real files mostly use (``SiT1``, ``Fe2+M``, ``O-H3``, ``AlM2``), and fails
badly for two conventions common in AMCSD and COD files:

* **Water oxygens labelled ``Wat1``, ``WAT2``, ``H2O3``.** The leading letters
  read as ``W`` - tungsten, Z = 74 - and ``H``. Measured on the curated
  structure set (2026-11-15): the non-clay reader computed the channel and
  interlayer water of vermiculite and sepiolite as TUNGSTEN, and the clay
  importer dropped those sites altogether, so an imported vermiculite lost its
  interlayer water.
* **Deuterium labelled ``D1``, ``DZW1*1``** (neutron studies of deuterated
  samples). ``D`` is not an element symbol, so the sites were dropped.
  Deuterium has one electron, exactly as hydrogen does, and X-rays see the two
  identically.

`label_element` recognises these and answers ``"O"`` or ``"H"``; for anything
else it answers None and the reader's own rule applies. A label that really
does begin with tungsten (``W1`` in a tungstate) is untouched: only ``Wat`` is
water. Likewise the real elements beginning with D (Db, Ds, Dy) stay
themselves.
"""

from __future__ import annotations

import re

_WATER = re.compile(r"^(?:wat|h2o)", re.IGNORECASE)
_D_ELEMENTS = frozenset(("Db", "Ds", "Dy"))

#: Every element symbol, in order of atomic number.
_BY_Z = (
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni "
    "Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I "
    "Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt "
    "Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr "
    "Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og"
).split()
ELEMENT_SYMBOLS = frozenset(_BY_Z)

#: Two-letter elements a mineral CIF may really contain (Z <= 92). A reader
#: that supports only some elements uses this to tell "an element I do not
#: handle" (Pb, Ce, Sn) from a label it can still read by its first letter -
#: without it ``Pb1`` was read as P, phosphorus. Synthetic elements are left
#: out so an ammonium ``NH4`` stays nitrogen rather than becoming nihonium, and
#: so is ``Ho``: a hydroxyl hydrogen is sometimes labelled ``HO1``, while
#: holmium in a clay structure is not plausible.
MINERAL_TWO_LETTER = frozenset(s for s in _BY_Z[:92] if len(s) == 2) - {"Ho"}


def label_element(token) -> "str | None":
    """``"O"`` for a water-oxygen label, ``"H"`` for a deuterium label, else
    None (the caller's own element rule then applies)."""
    if not token:
        return None
    text = str(token).strip()
    if _WATER.match(text):
        return "O"
    letters = re.match(r"[A-Za-z]+", text)
    if not letters:
        return None
    word = letters.group(0)
    if word[0] in "Dd" and word[:2].capitalize() not in _D_ELEMENTS:
        return "H"
    return None
