# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'shifting.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_ShiftPatternDialog(object):
    def setupUi(self, ShiftPatternDialog):
        if not ShiftPatternDialog.objectName():
            ShiftPatternDialog.setObjectName(u"ShiftPatternDialog")
        self.dialogLayout = QVBoxLayout(ShiftPatternDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.shiftForm = QFormLayout()
        self.shiftForm.setObjectName(u"shiftForm")
        self.lbl_position = QLabel(ShiftPatternDialog)
        self.lbl_position.setObjectName(u"lbl_position")

        self.shiftForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_position)

        self.shift_position = QComboBox(ShiftPatternDialog)
        self.shift_position.addItem("")
        self.shift_position.addItem("")
        self.shift_position.addItem("")
        self.shift_position.addItem("")
        self.shift_position.addItem("")
        self.shift_position.addItem("")
        self.shift_position.addItem("")
        self.shift_position.setObjectName(u"shift_position")

        self.shiftForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.shift_position)

        self.lbl_value = QLabel(ShiftPatternDialog)
        self.lbl_value.setObjectName(u"lbl_value")

        self.shiftForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_value)

        self.spin_shift_value = QDoubleSpinBox(ShiftPatternDialog)
        self.spin_shift_value.setObjectName(u"spin_shift_value")
        self.spin_shift_value.setDecimals(5)
        self.spin_shift_value.setMinimum(-10.000000000000000)
        self.spin_shift_value.setMaximum(10.000000000000000)
        self.spin_shift_value.setSingleStep(0.010000000000000)

        self.shiftForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.spin_shift_value)


        self.dialogLayout.addLayout(self.shiftForm)

        self.buttonBox = QDialogButtonBox(ShiftPatternDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(ShiftPatternDialog)

        QMetaObject.connectSlotsByName(ShiftPatternDialog)
    # setupUi

    def retranslateUi(self, ShiftPatternDialog):
        ShiftPatternDialog.setWindowTitle(QCoreApplication.translate("ShiftPatternDialog", u"Shift Pattern", None))
        self.lbl_position.setText(QCoreApplication.translate("ShiftPatternDialog", u"Position", None))
        self.shift_position.setItemText(0, QCoreApplication.translate("ShiftPatternDialog", u"Quartz    0.42574   SiO2", None))
        self.shift_position.setItemText(1, QCoreApplication.translate("ShiftPatternDialog", u"Silicon   0.31355   Si", None))
        self.shift_position.setItemText(2, QCoreApplication.translate("ShiftPatternDialog", u"Zincite   0.24759   ZnO", None))
        self.shift_position.setItemText(3, QCoreApplication.translate("ShiftPatternDialog", u"Corundum  0.2085    Al2O3", None))
        self.shift_position.setItemText(4, QCoreApplication.translate("ShiftPatternDialog", u"Goethite  0.4183    FeO(OH)", None))
        self.shift_position.setItemText(5, QCoreApplication.translate("ShiftPatternDialog", u"Gibbsite  0.48486   Al(OH)3", None))
        self.shift_position.setItemText(6, QCoreApplication.translate("ShiftPatternDialog", u"Manual", None))

        self.lbl_value.setText(QCoreApplication.translate("ShiftPatternDialog", u"Value", None))
        self.spin_shift_value.setSuffix(QCoreApplication.translate("ShiftPatternDialog", u" nm", None))
    # retranslateUi

