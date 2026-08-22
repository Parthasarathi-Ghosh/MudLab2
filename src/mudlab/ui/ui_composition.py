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

        self.chk_measured = QCheckBox(CompositionDialog)
        self.chk_measured.setObjectName(u"chk_measured")

        self.rootLayout.addWidget(self.chk_measured)

        self.defaultRow = QHBoxLayout()
        self.defaultRow.setObjectName(u"defaultRow")
        self.chk_default = QCheckBox(CompositionDialog)
        self.chk_default.setObjectName(u"chk_default")

        self.defaultRow.addWidget(self.chk_default)

        self.btn_default_phases = QPushButton(CompositionDialog)
        self.btn_default_phases.setObjectName(u"btn_default_phases")

        self.defaultRow.addWidget(self.btn_default_phases)

        self.defaultSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.defaultRow.addItem(self.defaultSpacer)


        self.rootLayout.addLayout(self.defaultRow)

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
        self.chk_measured.setToolTip(QCoreApplication.translate("CompositionDialog", u"Add a column with the measured (XRF) analysis imported through Data -> Import composition, normalised to 100% so it is directly comparable. Disabled when the project has no measured composition.", None))
#endif // QT_CONFIG(tooltip)
        self.chk_measured.setText(QCoreApplication.translate("CompositionDialog", u"Show measured (XRF) composition", None))
#if QT_CONFIG(tooltip)
        self.chk_default.setToolTip(QCoreApplication.translate("CompositionDialog", u"Add, for each specimen, the composition the mixture would have if every phase were still in its shipped default state - weighted by the fractions the fit found. Shows what refinement did to the chemistry. Needs the default phases to be stated first.", None))
#endif // QT_CONFIG(tooltip)
        self.chk_default.setText(QCoreApplication.translate("CompositionDialog", u"Show default-phase state", None))
        self.btn_default_phases.setText(QCoreApplication.translate("CompositionDialog", u"Default phases...", None))
#if QT_CONFIG(tooltip)
        self.btn_default_phases.setToolTip(QCoreApplication.translate("CompositionDialog", u"State which built-in default phase each phase started as. Required for the default-state comparison, and remembered with the project.", None))
#endif // QT_CONFIG(tooltip)
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

