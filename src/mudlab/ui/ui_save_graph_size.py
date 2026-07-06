# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'save_graph_size.ui'
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
    QDialogButtonBox, QFormLayout, QLabel, QSizePolicy,
    QSpinBox, QVBoxLayout, QWidget)

class Ui_SaveGraphSizeDialog(object):
    def setupUi(self, SaveGraphSizeDialog):
        if not SaveGraphSizeDialog.objectName():
            SaveGraphSizeDialog.setObjectName(u"SaveGraphSizeDialog")
        self.dialogLayout = QVBoxLayout(SaveGraphSizeDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.sizeForm = QFormLayout()
        self.sizeForm.setObjectName(u"sizeForm")
        self.lbl_preset = QLabel(SaveGraphSizeDialog)
        self.lbl_preset.setObjectName(u"lbl_preset")

        self.sizeForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_preset)

        self.cmb_presets = QComboBox(SaveGraphSizeDialog)
        self.cmb_presets.setObjectName(u"cmb_presets")

        self.sizeForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.cmb_presets)

        self.lbl_width = QLabel(SaveGraphSizeDialog)
        self.lbl_width.setObjectName(u"lbl_width")

        self.sizeForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_width)

        self.entry_width = QSpinBox(SaveGraphSizeDialog)
        self.entry_width.setObjectName(u"entry_width")
        self.entry_width.setMinimum(1)
        self.entry_width.setMaximum(20000)
        self.entry_width.setValue(1600)

        self.sizeForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.entry_width)

        self.lbl_height = QLabel(SaveGraphSizeDialog)
        self.lbl_height.setObjectName(u"lbl_height")

        self.sizeForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_height)

        self.entry_height = QSpinBox(SaveGraphSizeDialog)
        self.entry_height.setObjectName(u"entry_height")
        self.entry_height.setMinimum(1)
        self.entry_height.setMaximum(20000)
        self.entry_height.setValue(1200)

        self.sizeForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.entry_height)

        self.lbl_dpi = QLabel(SaveGraphSizeDialog)
        self.lbl_dpi.setObjectName(u"lbl_dpi")

        self.sizeForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lbl_dpi)

        self.entry_dpi = QSpinBox(SaveGraphSizeDialog)
        self.entry_dpi.setObjectName(u"entry_dpi")
        self.entry_dpi.setMinimum(30)
        self.entry_dpi.setMaximum(1200)
        self.entry_dpi.setValue(300)

        self.sizeForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.entry_dpi)


        self.dialogLayout.addLayout(self.sizeForm)

        self.buttonBox = QDialogButtonBox(SaveGraphSizeDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(SaveGraphSizeDialog)

        QMetaObject.connectSlotsByName(SaveGraphSizeDialog)
    # setupUi

    def retranslateUi(self, SaveGraphSizeDialog):
        SaveGraphSizeDialog.setWindowTitle(QCoreApplication.translate("SaveGraphSizeDialog", u"Save Graph", None))
        self.lbl_preset.setText(QCoreApplication.translate("SaveGraphSizeDialog", u"Load preset:", None))
        self.lbl_width.setText(QCoreApplication.translate("SaveGraphSizeDialog", u"Width", None))
        self.entry_width.setSuffix(QCoreApplication.translate("SaveGraphSizeDialog", u" px", None))
        self.lbl_height.setText(QCoreApplication.translate("SaveGraphSizeDialog", u"Height", None))
        self.entry_height.setSuffix(QCoreApplication.translate("SaveGraphSizeDialog", u" px", None))
        self.lbl_dpi.setText(QCoreApplication.translate("SaveGraphSizeDialog", u"DPI", None))
    # retranslateUi

