# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'contents.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_AtomContentsWidget(object):
    def setupUi(self, AtomContentsWidget):
        if not AtomContentsWidget.objectName():
            AtomContentsWidget.setObjectName(u"AtomContentsWidget")
        self.contentsRoot = QVBoxLayout(AtomContentsWidget)
        self.contentsRoot.setObjectName(u"contentsRoot")
        self.contentsRoot.setContentsMargins(0, 0, 0, 0)
        self.contentsForm = QFormLayout()
        self.contentsForm.setObjectName(u"contentsForm")
        self.lblContentsName = QLabel(AtomContentsWidget)
        self.lblContentsName.setObjectName(u"lblContentsName")

        self.contentsForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblContentsName)

        self.contents_name = QLineEdit(AtomContentsWidget)
        self.contents_name.setObjectName(u"contents_name")

        self.contentsForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.contents_name)

        self.contents_enabled = QCheckBox(AtomContentsWidget)
        self.contents_enabled.setObjectName(u"contents_enabled")

        self.contentsForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.contents_enabled)

        self.lblContentsValue = QLabel(AtomContentsWidget)
        self.lblContentsValue.setObjectName(u"lblContentsValue")

        self.contentsForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblContentsValue)

        self.contents_value = QDoubleSpinBox(AtomContentsWidget)
        self.contents_value.setObjectName(u"contents_value")
        self.contents_value.setDecimals(4)
        self.contents_value.setMaximum(100.000000000000000)
        self.contents_value.setSingleStep(0.100000000000000)

        self.contentsForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.contents_value)


        self.contentsRoot.addLayout(self.contentsForm)

        self.lblContentsAtoms = QLabel(AtomContentsWidget)
        self.lblContentsAtoms.setObjectName(u"lblContentsAtoms")
        self.lblContentsAtoms.setEnabled(False)

        self.contentsRoot.addWidget(self.lblContentsAtoms)

        self.contentsTableLayout = QVBoxLayout()
        self.contentsTableLayout.setObjectName(u"contentsTableLayout")

        self.contentsRoot.addLayout(self.contentsTableLayout)

        self.contentsButtons = QHBoxLayout()
        self.contentsButtons.setObjectName(u"contentsButtons")
        self.btn_add_content_row = QPushButton(AtomContentsWidget)
        self.btn_add_content_row.setObjectName(u"btn_add_content_row")

        self.contentsButtons.addWidget(self.btn_add_content_row)

        self.btn_del_content_row = QPushButton(AtomContentsWidget)
        self.btn_del_content_row.setObjectName(u"btn_del_content_row")

        self.contentsButtons.addWidget(self.btn_del_content_row)


        self.contentsRoot.addLayout(self.contentsButtons)


        self.retranslateUi(AtomContentsWidget)

        QMetaObject.connectSlotsByName(AtomContentsWidget)
    # setupUi

    def retranslateUi(self, AtomContentsWidget):
        self.lblContentsName.setText(QCoreApplication.translate("AtomContentsWidget", u"Name", None))
        self.contents_enabled.setText(QCoreApplication.translate("AtomContentsWidget", u"Enabled", None))
        self.lblContentsValue.setText(QCoreApplication.translate("AtomContentsWidget", u"Value", None))
        self.lblContentsAtoms.setText(QCoreApplication.translate("AtomContentsWidget", u"Atoms  (pn = amount \u00d7 value)", None))
        self.btn_add_content_row.setText(QCoreApplication.translate("AtomContentsWidget", u"Add atom", None))
        self.btn_del_content_row.setText(QCoreApplication.translate("AtomContentsWidget", u"Remove atom", None))
        pass
    # retranslateUi

