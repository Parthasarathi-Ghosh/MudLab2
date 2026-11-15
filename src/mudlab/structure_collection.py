"""The shipped collection of published crystal structures (``structures/``).

65 published CIFs, split into ``Clays`` (layer silicates, for Import CIF...) and
``Non-clays`` (for Import Non-Clay and Calibrate FWHM), with README.md,
CREDITS.md and manifest.csv beside them. See docs/structure-collection-plan.md.

Two layouts, as for the manual (`manual_dialog.docs_dir`):

- **Frozen build:** ``package.cmd`` copies the repository's ``structures`` to a
  visible ``Structures`` folder BESIDE ``MudLab.exe``. It does not go through
  the spec's ``datas``: PyInstaller 6 puts those in the internal folder, where
  no user would find them.
- **Source checkout:** the repository's own ``structures`` folder, two levels
  above this package.

The frozen location is checked first, so a build never reaches outside itself.

The file dialogs start in the collection the first time each one is used in a
session, and after that in the folder the user last picked from. The app keeps
no settings between runs, so that memory lasts one session.
"""

from __future__ import annotations

import csv
import os
import sys

#: Folder name beside the executable in a frozen build.
FROZEN_NAME = "Structures"
#: Folder name in a source checkout (the repository root).
SOURCE_NAME = "structures"
CLAYS = "Clays"
NONCLAYS = "Non-clays"

#: Start-folder keys, one per file dialog that opens a CIF.
IMPORT_CIF = "import_cif"
IMPORT_NONCLAY = "import_nonclay"
CALIBRATE_FWHM = "calibrate_fwhm"
NONCLAY_REFERENCE = "nonclay_reference"

#: Which subfolder each dialog starts in.
_SUBFOLDER = {
    IMPORT_CIF: CLAYS,
    IMPORT_NONCLAY: NONCLAYS,
    CALIBRATE_FWHM: NONCLAYS,
    NONCLAY_REFERENCE: NONCLAYS,
}

#: Last folder picked from, per dialog, for this session only.
_last_dir: dict[str, str] = {}


def _candidates() -> list[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    found = []
    if getattr(sys, "frozen", False):
        found.append(os.path.join(os.path.dirname(sys.executable), FROZEN_NAME))
    found.append(os.path.normpath(os.path.join(here, os.pardir, os.pardir, SOURCE_NAME)))
    return found


def collection_dir() -> str | None:
    """The collection folder, or None when this installation has none."""
    for path in _candidates():
        if os.path.isdir(path):
            return path
    return None


def _subdir(name: str) -> str | None:
    root = collection_dir()
    if root is None:
        return None
    path = os.path.join(root, name)
    return path if os.path.isdir(path) else None


def clays_dir() -> str | None:
    return _subdir(CLAYS)


def nonclays_dir() -> str | None:
    return _subdir(NONCLAYS)


def start_dir(key: str) -> str:
    """Where the file dialog `key` should open.

    The folder last picked from in this session if it still exists, otherwise
    the collection subfolder for that dialog, otherwise "" (no start folder:
    the platform dialog's own behaviour, as before the collection shipped).
    """
    last = _last_dir.get(key)
    if last and os.path.isdir(last):
        return last
    return _subdir(_SUBFOLDER[key]) or ""


def remember(key: str, path: str) -> None:
    """Record the folder of a file the user picked in dialog `key`."""
    if path:
        _last_dir[key] = os.path.dirname(os.path.abspath(path))


def forget_all() -> None:
    """Clear the session memory (tests)."""
    _last_dir.clear()


# ----------------------------------------------------------------------
# The manifest (the Structure Library reads it)
# ----------------------------------------------------------------------
MANIFEST = "manifest.csv"
#: The manifest's `kind` values.
KIND_CLAY = "clay"
KIND_NONCLAY = "non-clay"


def load_manifest(root: str | None = None) -> list[dict]:
    """One dict per structure, in the manifest's order (grouped by mineral
    family), with the manifest's columns plus ``path``: the CIF on disk.
    [] when there is no collection or no manifest."""
    root = root or collection_dir()
    if root is None:
        return []
    manifest = os.path.join(root, MANIFEST)
    if not os.path.isfile(manifest):
        return []
    with open(manifest, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["path"] = os.path.join(root, *row["file"].split("/"))
    return rows


def source_ids(row: dict) -> str:
    """The database numbers, as CREDITS.md gives them: "COD 9009233, AMCSD
    0012235"."""
    parts = []
    if row.get("cod"):
        parts.append("COD %s" % row["cod"])
    if row.get("amcsd"):
        parts.append("AMCSD %s" % row["amcsd"])
    return ", ".join(parts)


def citation(row: dict) -> str:
    """The full citation as plain text, in CREDITS.md's form: "Authors (year).
    Title. Journal volume, pages. https://doi.org/... [COD n, AMCSD n]"."""
    text = "%s (%s)." % (row["authors"], row["year"])
    # A few CIFs give no title the reader can keep (marcasite); CREDITS.md
    # then goes straight to the journal, and so does this.
    if row.get("title"):
        text += " %s." % row["title"].rstrip(".")
    text += " %s" % row["journal"]
    if row.get("volume"):
        text += " %s" % row["volume"]
    if row.get("pages"):
        text += ", %s" % row["pages"]
    text += "."
    if row.get("doi"):
        text += " https://doi.org/%s" % row["doi"]
    ids = source_ids(row)
    if ids:
        text += " [%s]" % ids
    return text
