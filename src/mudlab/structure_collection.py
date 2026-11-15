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
