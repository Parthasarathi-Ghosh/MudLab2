"""Marker model (Qt signals).

Property names follow the old mudlab.specimen.models.markers.Marker. Each
marker belongs to a specimen; the inheritable properties (color, angle,
style, align, base, top, top_offset) fall back to the project's
display_marker_* settings when their inherit_* flag is set - the old
InheritableMixin behavior, resolved by the effective_* accessors.
"""

from __future__ import annotations

import uuid

from PySide6.QtCore import QObject, Signal

from mudlab.calculations import get_2t_from_nm, get_nm_from_2t
from mudlab.models.properties import Prop

# Persistent marker keys as they appear in the .mud file.
MARKER_KEYS = (
    "label", "anno_label", "visible", "position", "x_offset", "y_offset",
    "top_offset", "color", "base", "angle", "align", "style", "top",
    "inherit_color", "inherit_angle", "inherit_top_offset", "inherit_align",
    "inherit_base", "inherit_top", "inherit_style",
)


class Marker(QObject):
    visuals_changed = Signal()

    label = Prop("New Marker", "visuals_changed")
    anno_label = Prop("", "visuals_changed")
    visible = Prop(True, "visuals_changed")
    position = Prop(0.0, "visuals_changed")
    x_offset = Prop(0.0, "visuals_changed")
    y_offset = Prop(0.05, "visuals_changed")
    top_offset = Prop(0.0, "visuals_changed")
    color = Prop("#000000", "visuals_changed")
    angle = Prop(0.0, "visuals_changed")
    style = Prop("none", "visuals_changed")
    align = Prop("left", "visuals_changed")
    base = Prop(1, "visuals_changed")
    top = Prop(0, "visuals_changed")

    inherit_color = Prop(True, "visuals_changed")
    inherit_angle = Prop(True, "visuals_changed")
    inherit_top_offset = Prop(True, "visuals_changed")
    inherit_align = Prop(True, "visuals_changed")
    inherit_base = Prop(True, "visuals_changed")
    inherit_top = Prop(True, "visuals_changed")
    inherit_style = Prop(True, "visuals_changed")

    def __init__(self, label: str = "", position: float = 0.0, parent=None) -> None:
        super().__init__(parent)
        if label:
            self.label = label
        if position:
            self.position = position
        self.uuid = uuid.uuid4().hex
        self.raw_properties: dict = {}
        self._specimen = None

    @property
    def specimen(self):
        return self._specimen

    # ------------------------------------------------------------------
    # Inheritable effective values (old InheritableMixin)
    # ------------------------------------------------------------------
    def _effective(self, prop: str, project_prop: str):
        project = self._specimen.project if self._specimen is not None else None
        if getattr(self, "inherit_" + prop) and project is not None:
            return getattr(project, project_prop)
        return getattr(self, prop)

    @property
    def effective_color(self) -> str:
        return self._effective("color", "display_marker_color")

    @property
    def effective_angle(self) -> float:
        return self._effective("angle", "display_marker_angle")

    @property
    def effective_style(self) -> str:
        return self._effective("style", "display_marker_style")

    @property
    def effective_align(self) -> str:
        return self._effective("align", "display_marker_align")

    @property
    def effective_base(self) -> int:
        return self._effective("base", "display_marker_base")

    @property
    def effective_top(self) -> int:
        return self._effective("top", "display_marker_top")

    @property
    def effective_top_offset(self) -> float:
        return self._effective("top_offset", "display_marker_top_offset")

    # ------------------------------------------------------------------
    # Position in nm (old get/set_nm_position via the goniometer)
    # ------------------------------------------------------------------
    @property
    def wavelength(self) -> float:
        return self._specimen.wavelength if self._specimen is not None else 0.154056

    def get_nm_position(self) -> float:
        return get_nm_from_2t(self.position, self.wavelength)

    def set_nm_position(self, nm: float) -> None:
        self.position = get_2t_from_nm(nm, self.wavelength)

    # ------------------------------------------------------------------
    # Serialization (.mud)
    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict) -> "Marker":
        props = data.get("properties", {})
        marker = cls()
        marker.raw_properties = dict(props)
        for key in MARKER_KEYS:
            if key in props:
                setattr(marker, key, props[key])
        if "uuid" in props:
            marker.uuid = props["uuid"]
        return marker

    def to_dict(self) -> dict:
        props = dict(self.raw_properties)
        for key in MARKER_KEYS:
            props[key] = getattr(self, key)
        props["uuid"] = self.uuid
        return {"type": "Marker", "properties": props}
