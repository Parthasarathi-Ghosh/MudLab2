# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'smoothing.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

class Ui_SmoothDataDialog(object):
    def setupUi(self, SmoothDataDialog):
        if not SmoothDataDialog.objectName():
            SmoothDataDialog.setObjectName(u"SmoothDataDialog")
        self.dialogLayout = QVBoxLayout(SmoothDataDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.smoothForm = QFormLayout()
        self.smoothForm.setObjectName(u"smoothForm")
        self.lbl_type = QLabel(SmoothDataDialog)
        self.lbl_type.setObjectName(u"lbl_type")

        self.smoothForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_type)

        self.smooth_type = QComboBox(SmoothDataDialog)
        self.smooth_type.addItem("")
        self.smooth_type.addItem("")
        self.smooth_type.addItem("")
        self.smooth_type.addItem("")
        self.smooth_type.addItem("")
        self.smooth_type.addItem("")
        self.smooth_type.setObjectName(u"smooth_type")

        self.smoothForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.smooth_type)

        self.lbl_degree = QLabel(SmoothDataDialog)
        self.lbl_degree.setObjectName(u"lbl_degree")

        self.smoothForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_degree)

        self.spin_degree = QSpinBox(SmoothDataDialog)
        self.spin_degree.setObjectName(u"spin_degree")
        self.spin_degree.setMinimum(1)
        self.spin_degree.setMaximum(600)
        self.spin_degree.setValue(3)

        self.smoothForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.spin_degree)

        self.smooth_show_original = QCheckBox(SmoothDataDialog)
        self.smooth_show_original.setObjectName(u"smooth_show_original")
        self.smooth_show_original.setChecked(True)

        self.smoothForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.smooth_show_original)


        self.dialogLayout.addLayout(self.smoothForm)

        self.buttonBox = QDialogButtonBox(SmoothDataDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(SmoothDataDialog)

        QMetaObject.connectSlotsByName(SmoothDataDialog)
    # setupUi

    def retranslateUi(self, SmoothDataDialog):
        SmoothDataDialog.setWindowTitle(QCoreApplication.translate("SmoothDataDialog", u"Smooth Data", None))
        self.lbl_type.setText(QCoreApplication.translate("SmoothDataDialog", u"Type", None))
        self.smooth_type.setItemText(0, QCoreApplication.translate("SmoothDataDialog", u"Moving Triangle", None))
        self.smooth_type.setItemText(1, QCoreApplication.translate("SmoothDataDialog", u"Savitzky-Golay", None))
        self.smooth_type.setItemText(2, QCoreApplication.translate("SmoothDataDialog", u"Gaussian", None))
        self.smooth_type.setItemText(3, QCoreApplication.translate("SmoothDataDialog", u"Moving Average", None))
        self.smooth_type.setItemText(4, QCoreApplication.translate("SmoothDataDialog", u"Smoothing Spline", None))
        self.smooth_type.setItemText(5, QCoreApplication.translate("SmoothDataDialog", u"Butterworth (filtfilt)", None))

        self.lbl_degree.setText(QCoreApplication.translate("SmoothDataDialog", u"Degree", None))
        self.smooth_show_original.setText(QCoreApplication.translate("SmoothDataDialog", u"Show Original", None))
    # retranslateUi

