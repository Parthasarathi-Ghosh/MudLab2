# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'about.ui'
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
    QHBoxLayout, QLabel, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_AboutDialog(object):
    def setupUi(self, AboutDialog):
        if not AboutDialog.objectName():
            AboutDialog.setObjectName(u"AboutDialog")
        AboutDialog.resize(460, 320)
        self.dialogLayout = QVBoxLayout(AboutDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.headerRow = QHBoxLayout()
        self.headerRow.setSpacing(16)
        self.headerRow.setObjectName(u"headerRow")
        self.lbl_logo = QLabel(AboutDialog)
        self.lbl_logo.setObjectName(u"lbl_logo")
        self.lbl_logo.setAlignment(Qt.AlignHCenter|Qt.AlignTop)

        self.headerRow.addWidget(self.lbl_logo)

        self.titleColumn = QVBoxLayout()
        self.titleColumn.setObjectName(u"titleColumn")
        self.lbl_name = QLabel(AboutDialog)
        self.lbl_name.setObjectName(u"lbl_name")

        self.titleColumn.addWidget(self.lbl_name)

        self.lbl_version = QLabel(AboutDialog)
        self.lbl_version.setObjectName(u"lbl_version")

        self.titleColumn.addWidget(self.lbl_version)

        self.lbl_tagline = QLabel(AboutDialog)
        self.lbl_tagline.setObjectName(u"lbl_tagline")
        self.lbl_tagline.setWordWrap(True)

        self.titleColumn.addWidget(self.lbl_tagline)

        self.titleSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.titleColumn.addItem(self.titleSpacer)


        self.headerRow.addLayout(self.titleColumn)


        self.dialogLayout.addLayout(self.headerRow)

        self.lbl_description = QLabel(AboutDialog)
        self.lbl_description.setObjectName(u"lbl_description")
        self.lbl_description.setWordWrap(True)

        self.dialogLayout.addWidget(self.lbl_description)

        self.lbl_credit = QLabel(AboutDialog)
        self.lbl_credit.setObjectName(u"lbl_credit")
        self.lbl_credit.setWordWrap(True)

        self.dialogLayout.addWidget(self.lbl_credit)

        self.bodySpacer = QSpacerItem(20, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.dialogLayout.addItem(self.bodySpacer)

        self.lbl_libs = QLabel(AboutDialog)
        self.lbl_libs.setObjectName(u"lbl_libs")
        self.lbl_libs.setWordWrap(True)
        self.lbl_libs.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.dialogLayout.addWidget(self.lbl_libs)

        self.buttonBox = QDialogButtonBox(AboutDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(AboutDialog)

        QMetaObject.connectSlotsByName(AboutDialog)
    # setupUi

    def retranslateUi(self, AboutDialog):
        AboutDialog.setWindowTitle(QCoreApplication.translate("AboutDialog", u"About MudLab", None))
        self.lbl_name.setText(QCoreApplication.translate("AboutDialog", u"MudLab", None))
        self.lbl_version.setText(QCoreApplication.translate("AboutDialog", u"Version", None))
        self.lbl_tagline.setText(QCoreApplication.translate("AboutDialog", u"X-ray Diffraction Analysis of Disordered Layered Minerals", None))
        self.lbl_description.setText(QCoreApplication.translate("AboutDialog", u"A desktop application for modelling and analysing powder X-ray diffraction patterns of disordered, mixed-layer clay minerals.", None))
        self.lbl_credit.setText(QCoreApplication.translate("AboutDialog", u"Original MudLab by Mathijs Dumon.", None))
        self.lbl_libs.setText("")
    # retranslateUi

