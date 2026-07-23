"""Atom type editor form. Design: ui/edit_atom_type.ui.

Ported from the GTK EditAtomTypeView (atoms/glade/atoms.glade). Plugged
into the Properties pane of the Edit Atom Types window and bound live to
an AtomType model. The scattering-factor plot uses the real formula
(ASF = [c + Σ aᵢ·e^(−bᵢ·s²)]·e^(−debye·s²), s = sin(θ)/λ in Å⁻¹).
"""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget

from mudlab.chart_style import INK_SECONDARY, SERIES_BLUE, SURFACE, style_axes
from mudlab.file_parsers.atom_type_library import load_atom_type_library
from mudlab.models import AtomType
from mudlab.ui.ui_edit_atom_type import Ui_EditAtomTypeWidget


class EditAtomTypeWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditAtomTypeWidget()
        self.ui.setupUi(self)

        self._atom_type: AtomType | None = None
        self._updating = False

        self.figure = Figure(facecolor=SURFACE, layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(220)
        self.ui.scatteringLayout.addWidget(self.canvas)
        self.axes = self.figure.add_subplot(111)

        self._a_spins = (
            self.ui.atom_par_a1, self.ui.atom_par_a2, self.ui.atom_par_a3,
            self.ui.atom_par_a4, self.ui.atom_par_a5,
        )
        self._b_spins = (
            self.ui.atom_par_b1, self.ui.atom_par_b2, self.ui.atom_par_b3,
            self.ui.atom_par_b4, self.ui.atom_par_b5,
        )

        # "Fill from element": the built-in scattering-factor library. Loaded
        # once; picking an entry copies its weight + coefficients onto the bound
        # atom type (leaving its name/uuid, so existing references still resolve).
        self._library = load_atom_type_library()
        self.ui.atom_element_picker.addItem("(pick an element…)", None)
        for lib_type in self._library:
            self.ui.atom_element_picker.addItem(lib_type.name, lib_type)
        self.ui.atom_element_picker.currentIndexChanged.connect(self._on_element_picked)

        self.ui.atom_name.textChanged.connect(lambda t: self._write("name", t))
        self.ui.atom_atom_nr.valueChanged.connect(lambda v: self._write("atom_nr", v))
        self.ui.atom_weight.valueChanged.connect(lambda v: self._write("weight", v))
        self.ui.atom_debye.valueChanged.connect(lambda v: self._write("debye", v))
        self.ui.atom_charge.valueChanged.connect(lambda v: self._write("charge", v))
        self.ui.atom_par_c.valueChanged.connect(lambda v: self._write("par_c", v))
        for i, spin in enumerate(self._a_spins):
            spin.valueChanged.connect(lambda v, i=i: self._write_array("par_a", i, v))
        for i, spin in enumerate(self._b_spins):
            spin.valueChanged.connect(lambda v, i=i: self._write_array("par_b", i, v))

        self.setEnabled(False)
        self._update_figure()

    def bind_atom_type(self, atom_type: AtomType | None) -> None:
        self._atom_type = atom_type
        self.setEnabled(atom_type is not None)
        if atom_type is None:
            return
        self._updating = True
        try:
            self.ui.atom_element_picker.setCurrentIndex(0)  # a momentary action
            self.ui.atom_name.setText(atom_type.name)
            self.ui.atom_atom_nr.setValue(int(atom_type.atom_nr))
            self.ui.atom_weight.setValue(atom_type.weight)
            self.ui.atom_debye.setValue(atom_type.debye)
            self.ui.atom_charge.setValue(atom_type.charge)
            self.ui.atom_par_c.setValue(atom_type.par_c)
            for spin, value in zip(self._a_spins, atom_type.par_a):
                spin.setValue(float(value))
            for spin, value in zip(self._b_spins, atom_type.par_b):
                spin.setValue(float(value))
        finally:
            self._updating = False
        self._update_figure()

    def _on_element_picked(self, _index: int) -> None:
        """Copy the picked element's physical + scattering-factor fields onto the
        bound atom type. Its name and uuid are left untouched, so atoms that
        reference it keep resolving - the user names the atom type, the library
        supplies the physics."""
        if self._updating or self._atom_type is None:
            return
        source = self.ui.atom_element_picker.currentData()
        if source is None:
            return
        self._atom_type.atom_nr = int(source.atom_nr)
        self._atom_type.weight = source.weight
        self._atom_type.debye = source.debye
        self._atom_type.charge = source.charge
        self._atom_type.par_c = source.par_c
        self._atom_type.par_a = np.array(source.par_a, dtype=float)
        self._atom_type.par_b = np.array(source.par_b, dtype=float)
        self._atom_type.data_changed.emit()  # one refresh, with the full new state
        self.bind_atom_type(self._atom_type)  # resync the spins + plot (+ picker)

    def _write(self, prop: str, value) -> None:
        if self._atom_type is not None and not self._updating:
            setattr(self._atom_type, prop, value)
            self._update_figure()

    def _write_array(self, prop: str, index: int, value: float) -> None:
        if self._atom_type is not None and not self._updating:
            getattr(self._atom_type, prop)[index] = value
            self._update_figure()

    def _update_figure(self) -> None:
        s = np.linspace(0.0, 1.5, 300)  # sin(θ)/λ in Å⁻¹
        s2 = s ** 2
        factor = np.full_like(s, self.ui.atom_par_c.value())
        for a_spin, b_spin in zip(self._a_spins, self._b_spins):
            factor += a_spin.value() * np.exp(-b_spin.value() * s2)
        factor *= np.exp(-self.ui.atom_debye.value() * s2)

        self.axes.clear()
        self.axes.plot(s, factor, color=SERIES_BLUE, linewidth=1.6)
        style_axes(self.axes)
        self.axes.set_xlabel("sin(θ)/λ [Å⁻¹]", color=INK_SECONDARY)
        self.axes.set_ylabel("Scattering factor", color=INK_SECONDARY)
        self.canvas.draw_idle()
