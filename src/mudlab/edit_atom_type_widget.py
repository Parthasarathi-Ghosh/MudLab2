"""Atom type editor form. Design: ui/edit_atom_type.ui.

Ported from the GTK EditAtomTypeView (atoms/glade/atoms.glade). Plugged
into the Properties pane of the Edit Atom Types window. The scattering
factor plot updates live from the a/b/c coefficients; the old app plotted
against 2θ via the goniometer conversion - that arrives with the model
port, until then the x-axis is sin(θ)/λ directly.
"""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget

from mudlab.chart_style import INK_SECONDARY, SERIES_BLUE, SURFACE, style_axes
from mudlab.ui.ui_edit_atom_type import Ui_EditAtomTypeWidget


class EditAtomTypeWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = Ui_EditAtomTypeWidget()
        self.ui.setupUi(self)

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
        for spin in (*self._a_spins, *self._b_spins, self.ui.atom_par_c):
            spin.valueChanged.connect(self._update_figure)

        self._update_figure()

    def set_atom_placeholder(
        self,
        name: str,
        atom_nr: int,
        weight: float,
        debye: float,
        charge: float,
        a: tuple[float, ...],
        b: tuple[float, ...],
        c: float,
    ) -> None:
        """Show placeholder values until the atom type model (Qt signals) exists."""
        self.ui.atom_name.setText(name)
        self.ui.atom_atom_nr.setValue(atom_nr)
        self.ui.atom_weight.setValue(weight)
        self.ui.atom_debye.setValue(debye)
        self.ui.atom_charge.setValue(charge)
        for spin, value in zip((*self._a_spins, *self._b_spins), (*a, *b)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
        self.ui.atom_par_c.blockSignals(True)
        self.ui.atom_par_c.setValue(c)
        self.ui.atom_par_c.blockSignals(False)
        self._update_figure()

    def _update_figure(self) -> None:
        s = np.linspace(0.0, 1.5, 300)
        factor = np.full_like(s, self.ui.atom_par_c.value())
        for a_spin, b_spin in zip(self._a_spins, self._b_spins):
            factor += a_spin.value() * np.exp(-b_spin.value() * s**2)

        self.axes.clear()
        self.axes.plot(s, factor, color=SERIES_BLUE, linewidth=1.6)
        style_axes(self.axes)
        self.axes.set_xlabel("sin(θ)/λ [Å⁻¹]", color=INK_SECONDARY)
        self.axes.set_ylabel("Scattering factor", color=INK_SECONDARY)
        self.canvas.draw_idle()
