# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'calibrate_fwhm.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_CalibrateFwhmDialog(object):
    def setupUi(self, CalibrateFwhmDialog):
        if not CalibrateFwhmDialog.objectName():
            CalibrateFwhmDialog.setObjectName(u"CalibrateFwhmDialog")
        CalibrateFwhmDialog.setMinimumSize(QSize(560, 420))
        self.dialogLayout = QVBoxLayout(CalibrateFwhmDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.lbl_intro = QLabel(CalibrateFwhmDialog)
        self.lbl_intro.setObjectName(u"lbl_intro")
        self.lbl_intro.setWordWrap(True)

        self.dialogLayout.addWidget(self.lbl_intro)

        self.form = QFormLayout()
        self.form.setObjectName(u"form")
        self.lbl_standard_caption = QLabel(CalibrateFwhmDialog)
        self.lbl_standard_caption.setObjectName(u"lbl_standard_caption")

        self.form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_standard_caption)

        self.standardRow = QHBoxLayout()
        self.standardRow.setObjectName(u"standardRow")
        self.lbl_standard = QLabel(CalibrateFwhmDialog)
        self.lbl_standard.setObjectName(u"lbl_standard")

        self.standardRow.addWidget(self.lbl_standard)

        self.stdSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.standardRow.addItem(self.stdSpacer)

        self.button_standard = QPushButton(CalibrateFwhmDialog)
        self.button_standard.setObjectName(u"button_standard")

        self.standardRow.addWidget(self.button_standard)


        self.form.setLayout(0, QFormLayout.ItemRole.FieldRole, self.standardRow)

        self.lbl_measured_caption = QLabel(CalibrateFwhmDialog)
        self.lbl_measured_caption.setObjectName(u"lbl_measured_caption")

        self.form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_measured_caption)

        self.measuredRow = QHBoxLayout()
        self.measuredRow.setObjectName(u"measuredRow")
        self.lbl_measured = QLabel(CalibrateFwhmDialog)
        self.lbl_measured.setObjectName(u"lbl_measured")

        self.measuredRow.addWidget(self.lbl_measured)

        self.measSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.measuredRow.addItem(self.measSpacer)

        self.button_measured = QPushButton(CalibrateFwhmDialog)
        self.button_measured.setObjectName(u"button_measured")

        self.measuredRow.addWidget(self.button_measured)


        self.form.setLayout(1, QFormLayout.ItemRole.FieldRole, self.measuredRow)

        self.lbl_wavelength_caption = QLabel(CalibrateFwhmDialog)
        self.lbl_wavelength_caption.setObjectName(u"lbl_wavelength_caption")

        self.form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_wavelength_caption)

        self.lbl_wavelength = QLabel(CalibrateFwhmDialog)
        self.lbl_wavelength.setObjectName(u"lbl_wavelength")

        self.form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.lbl_wavelength)


        self.dialogLayout.addLayout(self.form)

        self.chk_caglioti = QCheckBox(CalibrateFwhmDialog)
        self.chk_caglioti.setObjectName(u"chk_caglioti")

        self.dialogLayout.addWidget(self.chk_caglioti)

        self.fitRow = QHBoxLayout()
        self.fitRow.setObjectName(u"fitRow")
        self.button_fit = QPushButton(CalibrateFwhmDialog)
        self.button_fit.setObjectName(u"button_fit")

        self.fitRow.addWidget(self.button_fit)

        self.lbl_result = QLabel(CalibrateFwhmDialog)
        self.lbl_result.setObjectName(u"lbl_result")

        self.fitRow.addWidget(self.lbl_result)


        self.dialogLayout.addLayout(self.fitRow)

        self.grpPreview = QGroupBox(CalibrateFwhmDialog)
        self.grpPreview.setObjectName(u"grpPreview")
        self.previewLayout = QVBoxLayout(self.grpPreview)
        self.previewLayout.setObjectName(u"previewLayout")

        self.dialogLayout.addWidget(self.grpPreview)

        self.chk_apply_all = QCheckBox(CalibrateFwhmDialog)
        self.chk_apply_all.setObjectName(u"chk_apply_all")

        self.dialogLayout.addWidget(self.chk_apply_all)

        self.buttonBox = QDialogButtonBox(CalibrateFwhmDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(CalibrateFwhmDialog)

        QMetaObject.connectSlotsByName(CalibrateFwhmDialog)
    # setupUi

    def retranslateUi(self, CalibrateFwhmDialog):
        CalibrateFwhmDialog.setWindowTitle(QCoreApplication.translate("CalibrateFwhmDialog", u"Calibrate peak FWHM", None))
        self.lbl_intro.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"Fit the instrumental peak width by matching a standard's computed pattern to a measured scan of that standard. A 2\u03b8 zero-shift is fitted too, so displacement does not inflate the width.", None))
        self.lbl_standard_caption.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"Standard", None))
        self.lbl_standard.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"Silicon (built-in)", None))
#if QT_CONFIG(tooltip)
        self.button_standard.setToolTip(QCoreApplication.translate("CalibrateFwhmDialog", u"Use a different standard's CIF instead of the built-in Silicon.", None))
#endif // QT_CONFIG(tooltip)
        self.button_standard.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"Use CIF\u2026", None))
        self.lbl_measured_caption.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"Measured pattern", None))
        self.lbl_measured.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"none loaded", None))
        self.button_measured.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"Open\u2026", None))
        self.lbl_wavelength_caption.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"Wavelength", None))
        self.lbl_wavelength.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.chk_caglioti.setToolTip(QCoreApplication.translate("CalibrateFwhmDialog", u"Fit an angle-dependent width (Caglioti U,V,W: FWHM\u00b2 = U\u00b7tan\u00b2\u03b8 + V\u00b7tan\u03b8 + W) instead of one constant FWHM. Needs a standard scan spanning a wide 2\u03b8 range.", None))
#endif // QT_CONFIG(tooltip)
        self.chk_caglioti.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"Fit angle-dependent width (Caglioti U, V, W)", None))
        self.button_fit.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"Fit", None))
        self.lbl_result.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"Open a measured pattern, then Fit.", None))
        self.grpPreview.setTitle(QCoreApplication.translate("CalibrateFwhmDialog", u"Fit preview (measured vs fitted standard)", None))
#if QT_CONFIG(tooltip)
        self.chk_apply_all.setToolTip(QCoreApplication.translate("CalibrateFwhmDialog", u"Also set this fitted width on every other CIF-derived non-clay phase in the project (instrumental width is shared across them).", None))
#endif // QT_CONFIG(tooltip)
        self.chk_apply_all.setText(QCoreApplication.translate("CalibrateFwhmDialog", u"Apply to all computed non-clay phases", None))
    # retranslateUi

