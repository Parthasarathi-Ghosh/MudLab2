# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'peak_properties.ui'
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
    QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_PeakPropertiesDialog(object):
    def setupUi(self, PeakPropertiesDialog):
        if not PeakPropertiesDialog.objectName():
            PeakPropertiesDialog.setObjectName(u"PeakPropertiesDialog")
        self.dialogLayout = QVBoxLayout(PeakPropertiesDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.lbl_hint = QLabel(PeakPropertiesDialog)
        self.lbl_hint.setObjectName(u"lbl_hint")
        self.lbl_hint.setWordWrap(True)

        self.dialogLayout.addWidget(self.lbl_hint)

        self.peakForm = QFormLayout()
        self.peakForm.setObjectName(u"peakForm")
        self.lbl_startpos = QLabel(PeakPropertiesDialog)
        self.lbl_startpos.setObjectName(u"lbl_startpos")

        self.peakForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_startpos)

        self.peak_startx = QDoubleSpinBox(PeakPropertiesDialog)
        self.peak_startx.setObjectName(u"peak_startx")
        self.peak_startx.setDecimals(2)
        self.peak_startx.setMaximum(180.000000000000000)

        self.peakForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.peak_startx)

        self.lbl_endpos = QLabel(PeakPropertiesDialog)
        self.lbl_endpos.setObjectName(u"lbl_endpos")

        self.peakForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_endpos)

        self.peak_endx = QDoubleSpinBox(PeakPropertiesDialog)
        self.peak_endx.setObjectName(u"peak_endx")
        self.peak_endx.setDecimals(2)
        self.peak_endx.setMaximum(180.000000000000000)

        self.peakForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.peak_endx)

        self.lbl_result = QLabel(PeakPropertiesDialog)
        self.lbl_result.setObjectName(u"lbl_result")

        self.peakForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_result)

        self.peak_area_result = QLabel(PeakPropertiesDialog)
        self.peak_area_result.setObjectName(u"peak_area_result")

        self.peakForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.peak_area_result)

        self.lbl_fwhm = QLabel(PeakPropertiesDialog)
        self.lbl_fwhm.setObjectName(u"lbl_fwhm")

        self.peakForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lbl_fwhm)

        self.peak_fwhm_result = QLabel(PeakPropertiesDialog)
        self.peak_fwhm_result.setObjectName(u"peak_fwhm_result")

        self.peakForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.peak_fwhm_result)


        self.dialogLayout.addLayout(self.peakForm)

        self.buttonsRow = QHBoxLayout()
        self.buttonsRow.setObjectName(u"buttonsRow")
        self.btn_copy_results = QPushButton(PeakPropertiesDialog)
        self.btn_copy_results.setObjectName(u"btn_copy_results")

        self.buttonsRow.addWidget(self.btn_copy_results)

        self.buttonBox = QDialogButtonBox(PeakPropertiesDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.buttonsRow.addWidget(self.buttonBox)


        self.dialogLayout.addLayout(self.buttonsRow)


        self.retranslateUi(PeakPropertiesDialog)

        QMetaObject.connectSlotsByName(PeakPropertiesDialog)
    # setupUi

    def retranslateUi(self, PeakPropertiesDialog):
        PeakPropertiesDialog.setWindowTitle(QCoreApplication.translate("PeakPropertiesDialog", u"Peak Properties", None))
        self.lbl_hint.setText(QCoreApplication.translate("PeakPropertiesDialog", u"Drag across the pattern to select the peak, or type the start/end below.", None))
        self.lbl_startpos.setText(QCoreApplication.translate("PeakPropertiesDialog", u"Start position", None))
#if QT_CONFIG(tooltip)
        self.peak_startx.setToolTip(QCoreApplication.translate("PeakPropertiesDialog", u"Start of the range - set by dragging on the pattern, or type a value.", None))
#endif // QT_CONFIG(tooltip)
        self.peak_startx.setSuffix(QCoreApplication.translate("PeakPropertiesDialog", u" \u00b02\u03b8", None))
        self.lbl_endpos.setText(QCoreApplication.translate("PeakPropertiesDialog", u"End position", None))
#if QT_CONFIG(tooltip)
        self.peak_endx.setToolTip(QCoreApplication.translate("PeakPropertiesDialog", u"End of the range - set by dragging on the pattern, or type a value.", None))
#endif // QT_CONFIG(tooltip)
        self.peak_endx.setSuffix(QCoreApplication.translate("PeakPropertiesDialog", u" \u00b02\u03b8", None))
        self.lbl_result.setText(QCoreApplication.translate("PeakPropertiesDialog", u"Peak area:", None))
        self.peak_area_result.setText(QCoreApplication.translate("PeakPropertiesDialog", u"0.0", None))
        self.lbl_fwhm.setText(QCoreApplication.translate("PeakPropertiesDialog", u"FWHM [\u00b02\u03b8]:", None))
        self.peak_fwhm_result.setText(QCoreApplication.translate("PeakPropertiesDialog", u"0.0", None))
#if QT_CONFIG(tooltip)
        self.btn_copy_results.setToolTip(QCoreApplication.translate("PeakPropertiesDialog", u"Copy Peak Area and FWHM to clipboard", None))
#endif // QT_CONFIG(tooltip)
        self.btn_copy_results.setText(QCoreApplication.translate("PeakPropertiesDialog", u"Copy Results", None))
    # retranslateUi

