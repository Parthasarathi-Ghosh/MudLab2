# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'background.ui'
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
    QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget)

class Ui_RemoveBackgroundDialog(object):
    def setupUi(self, RemoveBackgroundDialog):
        if not RemoveBackgroundDialog.objectName():
            RemoveBackgroundDialog.setObjectName(u"RemoveBackgroundDialog")
        self.dialogLayout = QVBoxLayout(RemoveBackgroundDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.typeForm = QFormLayout()
        self.typeForm.setObjectName(u"typeForm")
        self.lbl_type = QLabel(RemoveBackgroundDialog)
        self.lbl_type.setObjectName(u"lbl_type")

        self.typeForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_type)

        self.bg_type = QComboBox(RemoveBackgroundDialog)
        self.bg_type.addItem("")
        self.bg_type.addItem("")
        self.bg_type.setObjectName(u"bg_type")

        self.typeForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.bg_type)


        self.dialogLayout.addLayout(self.typeForm)

        self.bg_view_stack = QStackedWidget(RemoveBackgroundDialog)
        self.bg_view_stack.setObjectName(u"bg_view_stack")
        self.bg_linear = QWidget()
        self.bg_linear.setObjectName(u"bg_linear")
        self.linearForm = QFormLayout(self.bg_linear)
        self.linearForm.setObjectName(u"linearForm")
        self.lbl_position = QLabel(self.bg_linear)
        self.lbl_position.setObjectName(u"lbl_position")

        self.linearForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_position)

        self.bg_position = QDoubleSpinBox(self.bg_linear)
        self.bg_position.setObjectName(u"bg_position")
        self.bg_position.setDecimals(2)
        self.bg_position.setMinimum(-1000000000.000000000000000)
        self.bg_position.setMaximum(1000000000.000000000000000)

        self.linearForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.bg_position)

        self.bg_view_stack.addWidget(self.bg_linear)
        self.bg_pattern = QWidget()
        self.bg_pattern.setObjectName(u"bg_pattern")
        self.patternForm = QFormLayout(self.bg_pattern)
        self.patternForm.setObjectName(u"patternForm")
        self.lbl_file = QLabel(self.bg_pattern)
        self.lbl_file.setObjectName(u"lbl_file")

        self.patternForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_file)

        self.fileRow = QHBoxLayout()
        self.fileRow.setObjectName(u"fileRow")
        self.bg_pattern_file = QLineEdit(self.bg_pattern)
        self.bg_pattern_file.setObjectName(u"bg_pattern_file")
        self.bg_pattern_file.setReadOnly(True)

        self.fileRow.addWidget(self.bg_pattern_file)

        self.btn_browse_bg = QPushButton(self.bg_pattern)
        self.btn_browse_bg.setObjectName(u"btn_browse_bg")

        self.fileRow.addWidget(self.btn_browse_bg)


        self.patternForm.setLayout(0, QFormLayout.ItemRole.FieldRole, self.fileRow)

        self.lbl_scale = QLabel(self.bg_pattern)
        self.lbl_scale.setObjectName(u"lbl_scale")

        self.patternForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_scale)

        self.bg_scale = QDoubleSpinBox(self.bg_pattern)
        self.bg_scale.setObjectName(u"bg_scale")
        self.bg_scale.setDecimals(4)
        self.bg_scale.setMaximum(1000000.000000000000000)
        self.bg_scale.setValue(1.000000000000000)

        self.patternForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.bg_scale)

        self.lbl_offset = QLabel(self.bg_pattern)
        self.lbl_offset.setObjectName(u"lbl_offset")

        self.patternForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_offset)

        self.bg_offset = QDoubleSpinBox(self.bg_pattern)
        self.bg_offset.setObjectName(u"bg_offset")
        self.bg_offset.setDecimals(2)
        self.bg_offset.setMinimum(-1000000000.000000000000000)
        self.bg_offset.setMaximum(1000000000.000000000000000)

        self.patternForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.bg_offset)

        self.bg_view_stack.addWidget(self.bg_pattern)

        self.dialogLayout.addWidget(self.bg_view_stack)

        self.buttonBox = QDialogButtonBox(RemoveBackgroundDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(RemoveBackgroundDialog)

        self.bg_view_stack.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(RemoveBackgroundDialog)
    # setupUi

    def retranslateUi(self, RemoveBackgroundDialog):
        RemoveBackgroundDialog.setWindowTitle(QCoreApplication.translate("RemoveBackgroundDialog", u"Remove Background", None))
        self.lbl_type.setText(QCoreApplication.translate("RemoveBackgroundDialog", u"Type", None))
        self.bg_type.setItemText(0, QCoreApplication.translate("RemoveBackgroundDialog", u"Linear", None))
        self.bg_type.setItemText(1, QCoreApplication.translate("RemoveBackgroundDialog", u"Pattern", None))

        self.lbl_position.setText(QCoreApplication.translate("RemoveBackgroundDialog", u"Background value", None))
        self.lbl_file.setText(QCoreApplication.translate("RemoveBackgroundDialog", u"Pattern file", None))
        self.btn_browse_bg.setText(QCoreApplication.translate("RemoveBackgroundDialog", u"Browse...", None))
        self.lbl_scale.setText(QCoreApplication.translate("RemoveBackgroundDialog", u"Scale factor", None))
        self.lbl_offset.setText(QCoreApplication.translate("RemoveBackgroundDialog", u"Offset value", None))
    # retranslateUi

