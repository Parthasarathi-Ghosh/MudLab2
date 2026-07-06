"""Tiny property system for the Qt-signal models.

The old MudLab models used the bundled mvc framework (PropIntel
descriptors with signal names like data_changed / visuals_changed). That
framework is NOT ported: models here are plain QObjects, and `Prop` is a
descriptor that stores the value on the instance and emits the named Qt
signal when it changes.

Use Prop for scalar values (str/int/float/bool) only; array data gets
explicit setter methods on the model.
"""

from __future__ import annotations

from typing import Any


class Prop:
    """Model property that emits a named signal of its owner on change."""

    def __init__(self, default: Any, signal: str = "data_changed") -> None:
        self.default = default
        self.signal = signal
        self.attr = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr = "_prop_" + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.attr, self.default)

    def __set__(self, obj, value) -> None:
        old = getattr(obj, self.attr, self.default)
        if old != value:
            setattr(obj, self.attr, value)
            getattr(obj, self.signal).emit()
