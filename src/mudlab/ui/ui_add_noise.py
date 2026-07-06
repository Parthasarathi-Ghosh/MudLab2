# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_noise.ui'
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

class Ui_AddNoiseDialog(object):
    def setupUi(self, AddNoiseDialog):
        if not AddNoiseDialog.objectName():
            AddNoiseDialog.setObjectName(u"AddNoiseDialog")
        self.dialogLayout = QVBoxLayout(AddNoiseDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.noiseForm = QFormLayout()
        self.noiseForm.setObjectName(u"noiseForm")
        self.lbl_value = QLabel(AddNoiseDialog)
        self.lbl_value.setObjectName(u"lbl_value")

        self.noiseForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_value)

        self.spin_fraction = QDoubleSpinBox(AddNoiseDialog)
        self.spin_fraction.setObjectName(u"spin_fraction")
        self.spin_fraction.setDecimals(2)
        self.spin_fraction.setMaximum(1.000000000000000)
        self.spin_fraction.setSingleStep(0.050000000000000)
        self.spin_fraction.setValue(0.100000000000000)

        self.noiseForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.spin_fraction)


        self.dialogLayout.addLayout(self.noiseForm)

        self.buttonBox = QDialogButtonBox(AddNoiseDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(AddNoiseDialog)

        QMetaObject.connectSlotsByName(AddNoiseDialog)
    # setupUi

    def retranslateUi(self, AddNoiseDialog):
        AddNoiseDialog.setWindowTitle(QCoreApplication.translate("AddNoiseDialog", u"Add Noise", None))
        self.lbl_value.setText(QCoreApplication.translate("AddNoiseDialog", u"Fraction", None))
    # retranslateUi

