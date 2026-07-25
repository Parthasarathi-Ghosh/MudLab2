# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'wavelength_distribution.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QDialog,
    QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QTableView,
    QVBoxLayout, QWidget)

class Ui_WavelengthDistributionDialog(object):
    def setupUi(self, WavelengthDistributionDialog):
        if not WavelengthDistributionDialog.objectName():
            WavelengthDistributionDialog.setObjectName(u"WavelengthDistributionDialog")
        WavelengthDistributionDialog.resize(420, 380)
        self.dialogLayout = QVBoxLayout(WavelengthDistributionDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.lbl_heading = QLabel(WavelengthDistributionDialog)
        self.lbl_heading.setObjectName(u"lbl_heading")

        self.dialogLayout.addWidget(self.lbl_heading)

        self.tv_wld = QTableView(WavelengthDistributionDialog)
        self.tv_wld.setObjectName(u"tv_wld")
        self.tv_wld.setAlternatingRowColors(True)
        self.tv_wld.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.dialogLayout.addWidget(self.tv_wld)

        self.buttonsRow = QHBoxLayout()
        self.buttonsRow.setObjectName(u"buttonsRow")
        self.btn_add = QPushButton(WavelengthDistributionDialog)
        self.btn_add.setObjectName(u"btn_add")

        self.buttonsRow.addWidget(self.btn_add)

        self.btn_del = QPushButton(WavelengthDistributionDialog)
        self.btn_del.setObjectName(u"btn_del")

        self.buttonsRow.addWidget(self.btn_del)

        self.buttonsSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonsRow.addItem(self.buttonsSpacer)

        self.btn_import = QPushButton(WavelengthDistributionDialog)
        self.btn_import.setObjectName(u"btn_import")

        self.buttonsRow.addWidget(self.btn_import)

        self.btn_export = QPushButton(WavelengthDistributionDialog)
        self.btn_export.setObjectName(u"btn_export")

        self.buttonsRow.addWidget(self.btn_export)


        self.dialogLayout.addLayout(self.buttonsRow)

        self.buttonBox = QDialogButtonBox(WavelengthDistributionDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(WavelengthDistributionDialog)

        QMetaObject.connectSlotsByName(WavelengthDistributionDialog)
    # setupUi

    def retranslateUi(self, WavelengthDistributionDialog):
        WavelengthDistributionDialog.setWindowTitle(QCoreApplication.translate("WavelengthDistributionDialog", u"Edit emission spectrum", None))
        self.lbl_heading.setText(QCoreApplication.translate("WavelengthDistributionDialog", u"Emission spectrum (wavelength distribution):", None))
#if QT_CONFIG(tooltip)
        self.btn_add.setToolTip(QCoreApplication.translate("WavelengthDistributionDialog", u"Add a wavelength row", None))
#endif // QT_CONFIG(tooltip)
        self.btn_add.setText(QCoreApplication.translate("WavelengthDistributionDialog", u"Add", None))
#if QT_CONFIG(tooltip)
        self.btn_del.setToolTip(QCoreApplication.translate("WavelengthDistributionDialog", u"Remove the selected wavelength row(s)", None))
#endif // QT_CONFIG(tooltip)
        self.btn_del.setText(QCoreApplication.translate("WavelengthDistributionDialog", u"Remove", None))
#if QT_CONFIG(tooltip)
        self.btn_import.setToolTip(QCoreApplication.translate("WavelengthDistributionDialog", u"Replace the spectrum with one loaded from a .wld file", None))
#endif // QT_CONFIG(tooltip)
        self.btn_import.setText(QCoreApplication.translate("WavelengthDistributionDialog", u"Import\u2026", None))
#if QT_CONFIG(tooltip)
        self.btn_export.setToolTip(QCoreApplication.translate("WavelengthDistributionDialog", u"Save the current spectrum to a .wld file", None))
#endif // QT_CONFIG(tooltip)
        self.btn_export.setText(QCoreApplication.translate("WavelengthDistributionDialog", u"Export\u2026", None))
    # retranslateUi

