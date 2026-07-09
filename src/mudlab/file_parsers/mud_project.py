"""MudLab .mud project files, compatible with the old app's format.

A .mud file is a deflated ZIP:
- 'content': {"type": "Project", "properties": {...}} where multi-part
  properties hold "file://<entry>" placeholders,
- 'version': a JSON string,
- 'specimens', 'phases', 'atom_types', 'mixtures': the referenced parts.

Loading maps the modeled subset onto the Qt models and keeps everything
else verbatim (raw passthrough on the models), so saving a project that
was created by the old app does NOT lose the parts MudLab2 does not model
yet (phases, mixtures, atom types, goniometers, markers, exclusion
ranges, line properties, uuids).
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
import zipfile

import numpy as np

from mudlab.models import Marker, Project, Specimen

# Version tag written for new files (old-app format version we are
# compatible with); round-trips preserve the loaded tag.
DEFAULT_FILE_VERSION = "0.1.10"

MULTI_PARTS = ("specimens", "phases", "atom_types", "mixtures")

# Scalar properties shared 1:1 between the file and the Qt models.
PROJECT_PROPS = (
    "name", "author", "date", "description", "layout_mode",
    "display_exp_color", "display_calc_color",
    "display_exp_lw", "display_calc_lw",
    "display_exp_ls", "display_calc_ls",
    "display_exp_marker", "display_calc_marker",
    "display_plot_offset", "display_group_by", "display_label_pos",
    "axes_xlimit", "axes_xmin", "axes_xmax", "axes_xstretch",
    "axes_ylimit", "axes_ymin", "axes_ymax", "axes_yvisible",
    "axes_ynormalize", "axes_dspacing",
    "display_marker_angle", "display_marker_top_offset",
    "display_marker_style", "display_marker_color",
    "display_marker_base", "display_marker_top", "display_marker_align",
)
SPECIMEN_PROPS = (
    "name", "sample_name",
    "display_experimental", "display_calculated", "display_phases",
    "display_derivatives", "display_residuals", "display_stats_in_lbl",
    "display_vshift", "display_vscale", "display_residual_scale",
)


def _parse_pattern_data(data_string: str) -> tuple[np.ndarray, np.ndarray]:
    """Old pattern lines store their data as a JSON string of rows; the
    calculated line may carry extra per-phase columns - take the first two."""
    rows = json.loads(data_string) if data_string else []
    if len(rows) < 2:
        return np.empty(0), np.empty(0)
    array = np.asarray(rows, dtype=float)
    return array[:, 0], array[:, 1]


def _encode_pattern_data(x: np.ndarray, y: np.ndarray) -> str:
    pairs = [[float(xi), float(yi)] for xi, yi in zip(x, y)]
    return json.dumps(pairs, separators=(",", ":"))


# ----------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------
def load_mud(path: str) -> Project:
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        if "content" not in names:
            raise ValueError(f"{path!r} is not a MudLab project file")
        content = json.loads(archive.read("content").decode("utf-8"))
        properties = dict(content.get("properties", {}))
        for name in names:
            if name not in ("content", "version"):
                properties[name] = json.loads(archive.read(name).decode("utf-8"))
        version = (
            json.loads(archive.read("version").decode("utf-8"))
            if "version" in names else None
        )

    project = Project()
    project.raw_properties = properties
    project.file_version = version
    project.filename = path
    for prop in PROJECT_PROPS:
        if prop in properties:
            setattr(project, prop, properties[prop])

    for spec_dict in properties.get("specimens") or []:
        spec_props = spec_dict.get("properties", {})
        specimen = Specimen()
        specimen.raw_properties = spec_props
        for prop in SPECIMEN_PROPS:
            if prop in spec_props:
                setattr(specimen, prop, spec_props[prop])
        for key, setter in (
            ("experimental_pattern", specimen.set_experimental_pattern),
            ("calculated_pattern", specimen.set_calculated_pattern),
        ):
            line = spec_props.get(key)
            if isinstance(line, dict):
                data = line.get("properties", {}).get("data", "")
                x, y = _parse_pattern_data(data)
                if x.size:
                    setter(x, y)
        project.add_specimen(specimen)
        # Markers are now modeled; add them after the specimen has a project
        # so inheritance resolves.
        for marker_dict in spec_props.get("markers") or []:
            if isinstance(marker_dict, dict):
                specimen.add_marker(Marker.from_dict(marker_dict))

    return project


# ----------------------------------------------------------------------
# Saving
# ----------------------------------------------------------------------
def save_mud(project: Project, path: str) -> None:
    properties = dict(getattr(project, "raw_properties", None) or {})
    for prop in PROJECT_PROPS:
        properties[prop] = getattr(project, prop)
    properties.setdefault("uuid", uuid.uuid4().hex)
    properties["specimens"] = [
        _specimen_to_dict(specimen) for specimen in project.specimens
    ]
    for part in MULTI_PARTS:
        properties.setdefault(part, [])

    content_props = {
        key: (f"file://{key}" if key in MULTI_PARTS else value)
        for key, value in properties.items()
    }
    content = {"type": "Project", "properties": content_props}
    version = getattr(project, "file_version", None) or DEFAULT_FILE_VERSION

    # Safe write, like the old app: temp file first, existing file
    # becomes a '~' backup.
    temp_path = path + ".tmp"
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("content", json.dumps(content, separators=(",", ":")))
            archive.writestr("version", json.dumps(version))
            for part in MULTI_PARTS:
                archive.writestr(
                    part, json.dumps(properties[part], separators=(",", ":"))
                )
    except BaseException:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    if os.path.exists(path):
        shutil.move(path, path + "~")
    shutil.move(temp_path, path)

    project.raw_properties = properties
    project.filename = path


def _specimen_to_dict(specimen: Specimen) -> dict:
    props = dict(getattr(specimen, "raw_properties", None) or {})
    for prop in SPECIMEN_PROPS:
        props[prop] = getattr(specimen, prop)
    props.setdefault("uuid", uuid.uuid4().hex)
    # Markers are modeled: write the live list back.
    props["markers"] = [marker.to_dict() for marker in specimen.markers]

    # Experimental pattern: update the data inside the (possibly raw) line
    # object so unmodeled line properties (color, lw, inherits, z_data)
    # survive the round-trip.
    exp = props.get("experimental_pattern")
    if not isinstance(exp, dict):
        exp = {
            "type": "ExperimentalLine",
            "properties": {"label": "Experimental Profile", "uuid": uuid.uuid4().hex},
        }
    exp_props = dict(exp.get("properties", {}))
    x, y = specimen.experimental_pattern
    exp_props["data"] = _encode_pattern_data(x, y)
    props["experimental_pattern"] = {
        "type": exp.get("type", "ExperimentalLine"),
        "properties": exp_props,
    }

    # Calculated pattern: MudLab2 never modifies it yet, and the raw data
    # may carry extra per-phase columns - keep it verbatim when present.
    if not isinstance(props.get("calculated_pattern"), dict) and specimen.has_calculated_data:
        cx, cy = specimen.calculated_pattern
        props["calculated_pattern"] = {
            "type": "CalculatedLine",
            "properties": {
                "label": "Calculated Profile",
                "uuid": uuid.uuid4().hex,
                "data": _encode_pattern_data(cx, cy),
            },
        }

    # 'source' is MudLab2-only; the old app's loader does not know it.
    props.pop("source", None)
    return {"type": "Specimen", "properties": props}
