# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'csv_import.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QCheckBox,
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHeaderView, QLabel, QSizePolicy, QTableView,
    QVBoxLayout, QWidget)

class Ui_CsvImportDialog(object):
    def setupUi(self, CsvImportDialog):
        if not CsvImportDialog.objectName():
            CsvImportDialog.setObjectName(u"CsvImportDialog")
        CsvImportDialog.resize(440, 420)
        self.dialogLayout = QVBoxLayout(CsvImportDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.lbl_file = QLabel(CsvImportDialog)
        self.lbl_file.setObjectName(u"lbl_file")
        self.lbl_file.setWordWrap(True)

        self.dialogLayout.addWidget(self.lbl_file)

        self.optionsForm = QFormLayout()
        self.optionsForm.setObjectName(u"optionsForm")
        self.lbl_separator = QLabel(CsvImportDialog)
        self.lbl_separator.setObjectName(u"lbl_separator")

        self.optionsForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_separator)

        self.cmb_separator = QComboBox(CsvImportDialog)
        self.cmb_separator.setObjectName(u"cmb_separator")

        self.optionsForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.cmb_separator)

        self.lbl_decimal = QLabel(CsvImportDialog)
        self.lbl_decimal.setObjectName(u"lbl_decimal")

        self.optionsForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_decimal)

        self.cmb_decimal = QComboBox(CsvImportDialog)
        self.cmb_decimal.setObjectName(u"cmb_decimal")

        self.optionsForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.cmb_decimal)


        self.dialogLayout.addLayout(self.optionsForm)

        self.chk_has_header = QCheckBox(CsvImportDialog)
        self.chk_has_header.setObjectName(u"chk_has_header")

        self.dialogLayout.addWidget(self.chk_has_header)

        self.lbl_preview = QLabel(CsvImportDialog)
        self.lbl_preview.setObjectName(u"lbl_preview")

        self.dialogLayout.addWidget(self.lbl_preview)

        self.tv_preview = QTableView(CsvImportDialog)
        self.tv_preview.setObjectName(u"tv_preview")
        self.tv_preview.setAlternatingRowColors(True)
        self.tv_preview.setSelectionMode(QAbstractItemView.NoSelection)
        self.tv_preview.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.dialogLayout.addWidget(self.tv_preview)

        self.buttonBox = QDialogButtonBox(CsvImportDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(CsvImportDialog)

        QMetaObject.connectSlotsByName(CsvImportDialog)
    # setupUi

    def retranslateUi(self, CsvImportDialog):
        CsvImportDialog.setWindowTitle(QCoreApplication.translate("CsvImportDialog", u"CSV import options", None))
        self.lbl_file.setText(QCoreApplication.translate("CsvImportDialog", u"File", None))
        self.lbl_separator.setText(QCoreApplication.translate("CsvImportDialog", u"Separator", None))
        self.lbl_decimal.setText(QCoreApplication.translate("CsvImportDialog", u"Decimal sign", None))
        self.chk_has_header.setText(QCoreApplication.translate("CsvImportDialog", u"First row contains headers", None))
        self.lbl_preview.setText(QCoreApplication.translate("CsvImportDialog", u"Preview (first rows):", None))
    # retranslateUi

