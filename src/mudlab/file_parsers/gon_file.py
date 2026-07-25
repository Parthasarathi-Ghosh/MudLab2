"""Stored goniometer setup (`.gon`) reader/writer + discovery.

A `.gon` is a JSON goniometer file: ``{"type": "Goniometer", "properties":
{...}}`` - the same structure ``Goniometer.to_dict()`` produces, so storing a
setup is just dumping ``to_dict()`` and loading is applying the ``properties``
back onto a goniometer. A handful of very old files use the legacy
``goniometer.models/Goniometer`` type with a single ``lambda`` wavelength; the
model's loader tolerates that.

Kept Qt-free (pure paths) so it is head-less testable; the widget resolves the
user directory (via QStandardPaths) and passes concrete paths here.
"""

from __future__ import annotations

import json
import os

#: Bundled factory presets (shipped read-only under the package data).
DEFAULT_GONIO_DIR = os.path.join(
    os.path.dirname(__file__), os.pardir, "data", "default goniometers"
)


def load_gon(path: str) -> dict:
    """Read a `.gon` file and return its ``properties`` dict. Raises ValueError
    if the file is not a goniometer setup."""
    with open(path, "r", encoding="utf-8") as stream:
        data = json.load(stream)
    props = data.get("properties") if isinstance(data, dict) else None
    if not isinstance(props, dict):
        raise ValueError("Not a goniometer setup file: %s" % path)
    return props


def save_gon(path: str, gonio_dict: dict) -> None:
    """Write a goniometer's ``to_dict()`` (``{"type", "properties"}``) as a
    `.gon` JSON file."""
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(gonio_dict, stream, indent=4)


def list_setups_in(directory: str) -> list[tuple[str, str]]:
    """``[(display_name, full_path), ...]`` for every `.gon` in `directory`
    (name = filename without extension), sorted by name. Empty if the
    directory does not exist."""
    if not os.path.isdir(directory):
        return []
    out = []
    for name in os.listdir(directory):
        if name.lower().endswith(".gon"):
            out.append((os.path.splitext(name)[0], os.path.join(directory, name)))
    return sorted(out, key=lambda item: item[0].lower())
