# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'strip_peak.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QLabel, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_StripPeakDialog(object):
    def setupUi(self, StripPeakDialog):
        if not StripPeakDialog.objectName():
            StripPeakDialog.setObjectName(u"StripPeakDialog")
        self.dialogLayout = QVBoxLayout(StripPeakDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.lbl_hint = QLabel(StripPeakDialog)
        self.lbl_hint.setObjectName(u"lbl_hint")
        self.lbl_hint.setWordWrap(True)

        self.dialogLayout.addWidget(self.lbl_hint)

        self.stripForm = QFormLayout()
        self.stripForm.setObjectName(u"stripForm")
        self.lbl_startpos = QLabel(StripPeakDialog)
        self.lbl_startpos.setObjectName(u"lbl_startpos")

        self.stripForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_startpos)

        self.strip_startx = QDoubleSpinBox(StripPeakDialog)
        self.strip_startx.setObjectName(u"strip_startx")
        self.strip_startx.setDecimals(2)
        self.strip_startx.setMaximum(180.000000000000000)

        self.stripForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.strip_startx)

        self.lbl_endpos = QLabel(StripPeakDialog)
        self.lbl_endpos.setObjectName(u"lbl_endpos")

        self.stripForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_endpos)

        self.strip_endx = QDoubleSpinBox(StripPeakDialog)
        self.strip_endx.setObjectName(u"strip_endx")
        self.strip_endx.setDecimals(2)
        self.strip_endx.setMaximum(180.000000000000000)

        self.stripForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.strip_endx)

        self.lbl_keep = QLabel(StripPeakDialog)
        self.lbl_keep.setObjectName(u"lbl_keep")

        self.stripForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_keep)

        self.keep_percent = QDoubleSpinBox(StripPeakDialog)
        self.keep_percent.setObjectName(u"keep_percent")
        self.keep_percent.setDecimals(1)
        self.keep_percent.setMinimum(0.000000000000000)
        self.keep_percent.setMaximum(100.000000000000000)
        self.keep_percent.setSingleStep(1.000000000000000)
        self.keep_percent.setValue(0.000000000000000)

        self.stripForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.keep_percent)

        self.lbl_noise = QLabel(StripPeakDialog)
        self.lbl_noise.setObjectName(u"lbl_noise")

        self.stripForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lbl_noise)

        self.noise_level = QDoubleSpinBox(StripPeakDialog)
        self.noise_level.setObjectName(u"noise_level")
        self.noise_level.setDecimals(2)
        self.noise_level.setMinimum(0.000000000000000)
        self.noise_level.setMaximum(1000000.000000000000000)

        self.stripForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.noise_level)


        self.dialogLayout.addLayout(self.stripForm)

        self.buttonBox = QDialogButtonBox(StripPeakDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(StripPeakDialog)

        QMetaObject.connectSlotsByName(StripPeakDialog)
    # setupUi

    def retranslateUi(self, StripPeakDialog):
        StripPeakDialog.setWindowTitle(QCoreApplication.translate("StripPeakDialog", u"Strip Peak", None))
        self.lbl_hint.setText(QCoreApplication.translate("StripPeakDialog", u"Drag across the pattern to select the peak, or type the start/end below.", None))
        self.lbl_startpos.setText(QCoreApplication.translate("StripPeakDialog", u"Start position", None))
#if QT_CONFIG(tooltip)
        self.strip_startx.setToolTip(QCoreApplication.translate("StripPeakDialog", u"Start of the range - set by dragging on the pattern, or type a value.", None))
#endif // QT_CONFIG(tooltip)
        self.strip_startx.setSuffix(QCoreApplication.translate("StripPeakDialog", u" \u00b02\u03b8", None))
        self.lbl_endpos.setText(QCoreApplication.translate("StripPeakDialog", u"End position", None))
#if QT_CONFIG(tooltip)
        self.strip_endx.setToolTip(QCoreApplication.translate("StripPeakDialog", u"End of the range - set by dragging on the pattern, or type a value.", None))
#endif // QT_CONFIG(tooltip)
        self.strip_endx.setSuffix(QCoreApplication.translate("StripPeakDialog", u" \u00b02\u03b8", None))
        self.lbl_keep.setText(QCoreApplication.translate("StripPeakDialog", u"Keep peak", None))
#if QT_CONFIG(tooltip)
        self.keep_percent.setToolTip(QCoreApplication.translate("StripPeakDialog", u"How much of the peak's height above the background line to keep: 0% flattens it onto the line (a strip), 100% leaves it unchanged. Fractions are allowed; the value cannot go below 0.", None))
#endif // QT_CONFIG(tooltip)
        self.keep_percent.setSuffix(QCoreApplication.translate("StripPeakDialog", u" %", None))
        self.lbl_noise.setText(QCoreApplication.translate("StripPeakDialog", u"Noise level", None))
#if QT_CONFIG(tooltip)
        self.noise_level.setToolTip(QCoreApplication.translate("StripPeakDialog", u"Random scatter added to the patched range so it does not look artificially clean (auto-estimated from the endpoints; set to 0 for a clean result).", None))
#endif // QT_CONFIG(tooltip)
    # retranslateUi

