# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'composition.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog,
    QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_CompositionDialog(object):
    def setupUi(self, CompositionDialog):
        if not CompositionDialog.objectName():
            CompositionDialog.setObjectName(u"CompositionDialog")
        CompositionDialog.resize(440, 320)
        self.rootLayout = QVBoxLayout(CompositionDialog)
        self.rootLayout.setObjectName(u"rootLayout")
        self.lbl_title = QLabel(CompositionDialog)
        self.lbl_title.setObjectName(u"lbl_title")
        self.lbl_title.setWordWrap(True)

        self.rootLayout.addWidget(self.lbl_title)

        self.chk_bulk = QCheckBox(CompositionDialog)
        self.chk_bulk.setObjectName(u"chk_bulk")

        self.rootLayout.addWidget(self.chk_bulk)

        self.tbl_composition = QTableWidget(CompositionDialog)
        self.tbl_composition.setObjectName(u"tbl_composition")
        self.tbl_composition.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_composition.setAlternatingRowColors(True)
        self.tbl_composition.setSelectionMode(QAbstractItemView.ContiguousSelection)

        self.rootLayout.addWidget(self.tbl_composition)

        self.buttonRow = QHBoxLayout()
        self.buttonRow.setObjectName(u"buttonRow")
        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonRow.addItem(self.buttonSpacer)

        self.btn_copy = QPushButton(CompositionDialog)
        self.btn_copy.setObjectName(u"btn_copy")

        self.buttonRow.addWidget(self.btn_copy)

        self.btn_export = QPushButton(CompositionDialog)
        self.btn_export.setObjectName(u"btn_export")

        self.buttonRow.addWidget(self.btn_export)

        self.btn_close = QPushButton(CompositionDialog)
        self.btn_close.setObjectName(u"btn_close")

        self.buttonRow.addWidget(self.btn_close)


        self.rootLayout.addLayout(self.buttonRow)


        self.retranslateUi(CompositionDialog)

        self.btn_close.setDefault(True)


        QMetaObject.connectSlotsByName(CompositionDialog)
    # setupUi

    def retranslateUi(self, CompositionDialog):
        CompositionDialog.setWindowTitle(QCoreApplication.translate("CompositionDialog", u"Composition", None))
        self.lbl_title.setText(QCoreApplication.translate("CompositionDialog", u"Oxide composition of the specimens in this mixture (wt%):", None))
#if QT_CONFIG(tooltip)
        self.chk_bulk.setToolTip(QCoreApplication.translate("CompositionDialog", u"Include non-clay phases: a bulk composition = each phase's own composition (normalised to 100%) weighted by its fraction. Unchecked shows the clay-only composition, which instead weights each clay by fraction x formula mass - so the clay oxides themselves shift a little (~1 wt%) between the two views. Enabled only when the mixture has a non-clay phase.", None))
#endif // QT_CONFIG(tooltip)
        self.chk_bulk.setText(QCoreApplication.translate("CompositionDialog", u"Include non-clay phases (bulk composition)", None))
#if QT_CONFIG(tooltip)
        self.btn_copy.setToolTip(QCoreApplication.translate("CompositionDialog", u"Copy the composition to the clipboard as CSV.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_copy.setText(QCoreApplication.translate("CompositionDialog", u"Copy", None))
#if QT_CONFIG(tooltip)
        self.btn_export.setToolTip(QCoreApplication.translate("CompositionDialog", u"Save the composition to a CSV file.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_export.setText(QCoreApplication.translate("CompositionDialog", u"Export CSV\u2026", None))
        self.btn_close.setText(QCoreApplication.translate("CompositionDialog", u"Close", None))
    # retranslateUi

