"""Pattern line-operation dialogs (background, smooth, shift, noise,
strip peak, peak properties).

Ported from the GTK dialogs in generic/views/glade/lines/. Each dialog binds
to one Specimen and applies its operation on OK, through the Specimen methods
in models/specimen.py (numerics: calculations/pattern_ops.py).

Old-app parity notes:

- The operations are **destructive and have no undo**, exactly as in the old
  app. Nothing is written to the .mud until the user saves, so Cancel-without-
  saving is the only way back - the old app behaved the same way and these
  dialogs do not add a confirmation the old app never had.
- In the old app these hung off the Edit Specimen controller, so they always
  targeted the specimen being edited. Here they open from the main window's
  menu and target the **selected** specimen; the actions are disabled when the
  selection is not a single specimen with data (see main_window).
- The old app previews shift / strip live on the plot while the dialog is
  open. That needs the plot-controller port, so these apply on OK only; the
  compute_* previews are already in place for when it lands.
"""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget

from mudlab.calculations import pattern_ops
from mudlab.file_parsers.xrd_import import PATTERN_FILTERS, parse_pattern
from mudlab.ui.ui_add_noise import Ui_AddNoiseDialog
from mudlab.ui.ui_background import Ui_RemoveBackgroundDialog
from mudlab.ui.ui_peak_properties import Ui_PeakPropertiesDialog
from mudlab.ui.ui_shifting import Ui_ShiftPatternDialog
from mudlab.ui.ui_smoothing import Ui_SmoothDataDialog
from mudlab.ui.ui_strip_peak import Ui_StripPeakDialog

# Combo index -> old model value maps (old settings.PATTERN_SHIFT_POSITIONS /
# the smoothing + background combo order).
BG_TYPES = (pattern_ops.BG_LINEAR, pattern_ops.BG_PATTERN)
SMOOTH_TYPES = (0, 1, 2, 3, 4, 5)
# NOTE: the d-spacings below are the old app's *values*; its own combo labels
# print slightly different numbers for silicon (0.31355) and zincite (0.24759).
# The values are what the old app actually shifts against, so they are ported
# verbatim rather than "corrected" to match its labels.
SHIFT_POSITIONS = (0.42574, 0.3134, 0.2476, 0.2085, 0.4183, 0.48486, 0.0)
SHIFT_MANUAL_INDEX = len(SHIFT_POSITIONS) - 1  # "Manual"


class _SpecimenDialog(QDialog):
    """Common base: holds the bound specimen and the OK/Cancel wiring.

    `accept()` runs the operation and is refused (the dialog stays open) when
    there is no specimen, so a mis-wired action cannot silently do nothing.
    """

    def __init__(self, ui_class, parent: QWidget | None = None, specimen=None) -> None:
        super().__init__(parent)
        self.ui = ui_class()
        self.ui.setupUi(self)
        self._specimen = None
        self.ui.buttonBox.accepted.connect(self._on_accept)
        self.ui.buttonBox.rejected.connect(self.reject)
        if specimen is not None:
            self.bind_specimen(specimen)

    def bind_specimen(self, specimen) -> None:
        self._specimen = specimen
        self._on_specimen_bound()

    def _on_specimen_bound(self) -> None:
        """Hook: pre-fill the dialog from the specimen's data."""

    def _apply(self) -> bool:
        """Run the operation. Return False to refuse (the dialog stays open);
        an implementation that refuses must say why first."""
        raise NotImplementedError

    def _on_accept(self) -> None:
        # Only close when the operation actually ran: closing on a refusal
        # would look exactly like success, which is how these dialogs got
        # their "looks done, does nothing" reputation in the first place.
        if self._specimen is None:
            return  # nothing bound: refuse rather than pretend it worked
        if self._apply():
            self.accept()


class RemoveBackgroundDialog(_SpecimenDialog):
    """Subtract a flat value, or a measured background pattern, from the
    experimental data (old BackgroundController)."""

    def __init__(self, parent: QWidget | None = None, specimen=None) -> None:
        self._bg_pattern = None  # interpolated onto the specimen's x-grid
        super().__init__(Ui_RemoveBackgroundDialog, parent, specimen)
        self.ui.bg_type.currentIndexChanged.connect(
            self.ui.bg_view_stack.setCurrentIndex
        )
        self.ui.btn_browse_bg.clicked.connect(self._browse_pattern)

    def _on_specimen_bound(self) -> None:
        # Old find_bg_position: start from the pattern minimum, the best
        # first guess for a flat background.
        _, y = self._specimen.experimental_pattern
        self.ui.bg_position.setValue(pattern_ops.find_bg_position(y))

    def _browse_pattern(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select background pattern file", "", PATTERN_FILTERS
        )
        if not filename:
            return
        try:
            bg_x, bg_y = parse_pattern(filename)
        except (OSError, ValueError) as err:
            QMessageBox.warning(self, "Background pattern", str(err))
            return
        if self._specimen is None or len(bg_x) < 2:
            QMessageBox.warning(
                self, "Background pattern", "The file contains no usable data."
            )
            return
        # The background is measured on its own grid, so interpolate it onto
        # the specimen's 2-theta values; outside its range it contributes
        # nothing (fill_value=0), as in the old app.
        from scipy.interpolate import interp1d

        x, _ = self._specimen.experimental_pattern
        self._bg_pattern = interp1d(bg_x, bg_y, bounds_error=False, fill_value=0)(x)
        self.ui.bg_pattern_file.setText(filename)

    def _apply(self) -> bool:
        bg_type = BG_TYPES[self.ui.bg_type.currentIndex()]
        if bg_type == pattern_ops.BG_PATTERN:
            if self._bg_pattern is None:
                QMessageBox.warning(
                    self, "Remove background", "Select a background pattern file first."
                )
                return False
            self._specimen.remove_background(
                bg_type,
                self.ui.bg_offset.value(),
                self._bg_pattern,
                self.ui.bg_scale.value(),
            )
        else:
            self._specimen.remove_background(bg_type, self.ui.bg_position.value())
        return True


class SmoothDataDialog(_SpecimenDialog):
    """Reduce point-to-point scatter (old SmoothDataController)."""

    def __init__(self, parent: QWidget | None = None, specimen=None) -> None:
        super().__init__(Ui_SmoothDataDialog, parent, specimen)
        self.ui.smooth_type.currentIndexChanged.connect(self._on_type_changed)
        self._on_type_changed(self.ui.smooth_type.currentIndex())
        # Old smooth_show_original toggled a live overlay of the unsmoothed
        # pattern; that needs the plot-controller port.
        self.ui.smooth_show_original.setEnabled(False)
        self.ui.smooth_show_original.setToolTip(
            "The live original-pattern overlay is not ported yet."
        )

    def _on_type_changed(self, index: int) -> None:
        # Old setup_smooth_variables: each method has its own sensible degree.
        self.ui.spin_degree.setValue(
            int(pattern_ops.default_smooth_degree(SMOOTH_TYPES[index]))
        )

    def _apply(self) -> bool:
        try:
            self._specimen.smooth_data(
                SMOOTH_TYPES[self.ui.smooth_type.currentIndex()],
                self.ui.spin_degree.value(),
            )
        except ValueError as err:
            # Moving Triangle and Savitzky-Golay need the smoothing window to
            # fit inside the pattern; the degree spin allows up to 600, which a
            # trimmed pattern may not accommodate. The old app let this escape
            # as a traceback - report it instead and stay open so the degree
            # can be lowered.
            QMessageBox.warning(
                self, "Smooth data",
                "That degree is too large for this pattern (%d points).\n\n%s"
                % (len(self._specimen.experimental_pattern[0]), err),
            )
            return False
        return True


class ShiftPatternDialog(_SpecimenDialog):
    """Correct a 2-theta offset against a reference mineral's reflection (old
    ShiftDataController).

    Picking a reference auto-detects the offset from the data; Manual lets the
    user type one. The value is a 2-theta offset, NOT the reference d-spacing.
    """

    def __init__(self, parent: QWidget | None = None, specimen=None) -> None:
        super().__init__(Ui_ShiftPatternDialog, parent, specimen)
        self.ui.shift_position.currentIndexChanged.connect(self._on_position_changed)

    def _on_specimen_bound(self) -> None:
        self._on_position_changed(self.ui.shift_position.currentIndex())

    def _on_position_changed(self, index: int) -> None:
        manual = index == SHIFT_MANUAL_INDEX
        self.ui.spin_shift_value.setEnabled(manual)
        if manual:
            # Old setup_shift_variables resets to 0 in manual mode, so the
            # previous reference's detected offset is not silently reused.
            self.ui.spin_shift_value.setValue(0.0)
        elif self._specimen is not None:
            # Find where the reference reflection actually sits and offer that
            # offset. A reference outside the scanned range detects 0.0 (the
            # old app's guard) - it simply has nothing to measure against.
            self.ui.spin_shift_value.setValue(
                self._specimen.detect_shift(SHIFT_POSITIONS[index])
            )

    def _apply(self) -> bool:
        index = self.ui.shift_position.currentIndex()
        self._specimen.apply_shift(
            self.ui.spin_shift_value.value(), SHIFT_POSITIONS[index]
        )
        return True


class AddNoiseDialog(_SpecimenDialog):
    """Add synthetic noise (old AddNoiseController) - used to test how robust
    a refinement is against counting statistics."""

    def __init__(self, parent: QWidget | None = None, specimen=None) -> None:
        super().__init__(Ui_AddNoiseDialog, parent, specimen)

    def _apply(self) -> bool:
        self._specimen.add_noise(self.ui.spin_fraction.value())
        return True


def _arm_sample(dialog: QDialog, spinbox) -> None:
    """Arm the main window's eye-dropper so the next plot click fills the
    given spinbox with the picked 2-theta position."""
    main_window = dialog.parent()
    if main_window is not None and hasattr(main_window, "arm_position_pick"):
        main_window.arm_position_pick(
            lambda plot, x: spinbox.setValue(x),
            "Click the position on the pattern...",
        )


class StripPeakDialog(_SpecimenDialog):
    """Replace a contaminant peak with the background line under it (old
    StripPeakController).

    Modeless: the Sample buttons pick the start/end positions on the plot, so
    the plot must stay clickable.
    """

    def __init__(self, parent: QWidget | None = None, specimen=None) -> None:
        super().__init__(Ui_StripPeakDialog, parent, specimen)
        self.ui.cmd_sample_start.clicked.connect(
            lambda: _arm_sample(self, self.ui.strip_startx)
        )
        self.ui.cmd_sample_end.clicked.connect(
            lambda: _arm_sample(self, self.ui.strip_endx)
        )
        # Old update_strip_pattern re-estimated the noise level whenever an
        # endpoint moved; the user can still override it afterwards.
        self.ui.strip_startx.valueChanged.connect(self._on_range_changed)
        self.ui.strip_endx.valueChanged.connect(self._on_range_changed)

    def _on_range_changed(self, *_args) -> None:
        if self._specimen is None:
            return
        strip = self._specimen.compute_strip_pattern(
            self.ui.strip_startx.value(), self.ui.strip_endx.value()
        )
        if strip is not None:
            self.ui.noise_level.setValue(strip.noise_level)

    def _apply(self) -> bool:
        strip = self._specimen.compute_strip_pattern(
            self.ui.strip_startx.value(),
            self.ui.strip_endx.value(),
            self.ui.noise_level.value(),
        )
        if strip is None:
            QMessageBox.warning(
                self, "Strip peak",
                "Set a start and end position at least two data points apart.",
            )
            return False
        self._specimen.apply_strip(strip)
        return True


class PeakPropertiesDialog(_SpecimenDialog):
    """Measure a peak's integrated area and FWHM (old
    CalculatePeakPropertiesController).

    Read-only: it never changes the pattern, so it has no OK button - results
    update live as the positions change.
    """

    def __init__(self, parent: QWidget | None = None, specimen=None) -> None:
        super().__init__(Ui_PeakPropertiesDialog, parent, specimen)
        self.ui.cmd_sample_start.clicked.connect(
            lambda: _arm_sample(self, self.ui.peak_startx)
        )
        self.ui.cmd_sample_end.clicked.connect(
            lambda: _arm_sample(self, self.ui.peak_endx)
        )
        self.ui.btn_copy_results.clicked.connect(self._copy_results)
        self.ui.peak_startx.valueChanged.connect(self._recalculate)
        self.ui.peak_endx.valueChanged.connect(self._recalculate)

    def _apply(self) -> bool:
        """A measurement: nothing to apply."""
        return True

    def _recalculate(self, *_args) -> None:
        if self._specimen is None:
            return
        props = self._specimen.compute_peak_properties(
            self.ui.peak_startx.value(), self.ui.peak_endx.value()
        )
        if props is None:
            self.set_results(0.0, 0.0)
        else:
            self.set_results(props.area, props.fwhm)

    def set_results(self, area: float, fwhm: float) -> None:
        self.ui.peak_area_result.setText(f"{area:.4f}")
        self.ui.peak_fwhm_result.setText(f"{fwhm:.4f}")

    def _copy_results(self) -> None:
        QGuiApplication.clipboard().setText(
            f"Peak area:\t{self.ui.peak_area_result.text()}\n"
            f"FWHM [°2θ]:\t{self.ui.peak_fwhm_result.text()}"
        )
