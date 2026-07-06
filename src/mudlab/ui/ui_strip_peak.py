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
    QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_StripPeakDialog(object):
    def setupUi(self, StripPeakDialog):
        if not StripPeakDialog.objectName():
            StripPeakDialog.setObjectName(u"StripPeakDialog")
        self.dialogLayout = QVBoxLayout(StripPeakDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.stripForm = QFormLayout()
        self.stripForm.setObjectName(u"stripForm")
        self.lbl_startpos = QLabel(StripPeakDialog)
        self.lbl_startpos.setObjectName(u"lbl_startpos")

        self.stripForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_startpos)

        self.startRow = QHBoxLayout()
        self.startRow.setObjectName(u"startRow")
        self.strip_startx = QDoubleSpinBox(StripPeakDialog)
        self.strip_startx.setObjectName(u"strip_startx")
        self.strip_startx.setDecimals(2)
        self.strip_startx.setMaximum(180.000000000000000)

        self.startRow.addWidget(self.strip_startx)

        self.cmd_sample_start = QPushButton(StripPeakDialog)
        self.cmd_sample_start.setObjectName(u"cmd_sample_start")

        self.startRow.addWidget(self.cmd_sample_start)


        self.stripForm.setLayout(0, QFormLayout.ItemRole.FieldRole, self.startRow)

        self.lbl_endpos = QLabel(StripPeakDialog)
        self.lbl_endpos.setObjectName(u"lbl_endpos")

        self.stripForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_endpos)

        self.endRow = QHBoxLayout()
        self.endRow.setObjectName(u"endRow")
        self.strip_endx = QDoubleSpinBox(StripPeakDialog)
        self.strip_endx.setObjectName(u"strip_endx")
        self.strip_endx.setDecimals(2)
        self.strip_endx.setMaximum(180.000000000000000)

        self.endRow.addWidget(self.strip_endx)

        self.cmd_sample_end = QPushButton(StripPeakDialog)
        self.cmd_sample_end.setObjectName(u"cmd_sample_end")

        self.endRow.addWidget(self.cmd_sample_end)


        self.stripForm.setLayout(1, QFormLayout.ItemRole.FieldRole, self.endRow)

        self.lbl_noise = QLabel(StripPeakDialog)
        self.lbl_noise.setObjectName(u"lbl_noise")

        self.stripForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_noise)

        self.noise_level = QDoubleSpinBox(StripPeakDialog)
        self.noise_level.setObjectName(u"noise_level")
        self.noise_level.setDecimals(2)
        self.noise_level.setMaximum(1000000.000000000000000)

        self.stripForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.noise_level)


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
        self.lbl_startpos.setText(QCoreApplication.translate("StripPeakDialog", u"Start position", None))
        self.strip_startx.setSuffix(QCoreApplication.translate("StripPeakDialog", u" \u00b02\u03b8", None))
#if QT_CONFIG(tooltip)
        self.cmd_sample_start.setToolTip(QCoreApplication.translate("StripPeakDialog", u"Select the position directly on the pattern", None))
#endif // QT_CONFIG(tooltip)
        self.cmd_sample_start.setText(QCoreApplication.translate("StripPeakDialog", u"Sample", None))
        self.lbl_endpos.setText(QCoreApplication.translate("StripPeakDialog", u"End position", None))
        self.strip_endx.setSuffix(QCoreApplication.translate("StripPeakDialog", u" \u00b02\u03b8", None))
#if QT_CONFIG(tooltip)
        self.cmd_sample_end.setToolTip(QCoreApplication.translate("StripPeakDialog", u"Select the position directly on the pattern", None))
#endif // QT_CONFIG(tooltip)
        self.cmd_sample_end.setText(QCoreApplication.translate("StripPeakDialog", u"Sample", None))
        self.lbl_noise.setText(QCoreApplication.translate("StripPeakDialog", u"Noise level", None))
    # retranslateUi

