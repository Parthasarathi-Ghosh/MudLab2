# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'cif_import.ui'
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
    QDialogButtonBox, QDoubleSpinBox, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QTableView,
    QVBoxLayout, QWidget)

class Ui_CifImportDialog(object):
    def setupUi(self, CifImportDialog):
        if not CifImportDialog.objectName():
            CifImportDialog.setObjectName(u"CifImportDialog")
        CifImportDialog.resize(900, 680)
        CifImportDialog.setSizeGripEnabled(True)
        self.rootLayout = QVBoxLayout(CifImportDialog)
        self.rootLayout.setObjectName(u"rootLayout")
        self.lbl_source = QLabel(CifImportDialog)
        self.lbl_source.setObjectName(u"lbl_source")
        self.lbl_source.setWordWrap(True)

        self.rootLayout.addWidget(self.lbl_source)

        self.grpDecisions = QGroupBox(CifImportDialog)
        self.grpDecisions.setObjectName(u"grpDecisions")
        self.decisionLayout = QGridLayout(self.grpDecisions)
        self.decisionLayout.setObjectName(u"decisionLayout")
        self.lbl_divisor_caption = QLabel(self.grpDecisions)
        self.lbl_divisor_caption.setObjectName(u"lbl_divisor_caption")

        self.decisionLayout.addWidget(self.lbl_divisor_caption, 0, 0, 1, 1)

        self.spin_divisor = QSpinBox(self.grpDecisions)
        self.spin_divisor.setObjectName(u"spin_divisor")
        self.spin_divisor.setMinimum(1)
        self.spin_divisor.setMaximum(8)

        self.decisionLayout.addWidget(self.spin_divisor, 0, 1, 1, 1)

        self.lbl_divisor_note = QLabel(self.grpDecisions)
        self.lbl_divisor_note.setObjectName(u"lbl_divisor_note")

        self.decisionLayout.addWidget(self.lbl_divisor_note, 0, 2, 1, 1)

        self.lbl_d001_caption = QLabel(self.grpDecisions)
        self.lbl_d001_caption.setObjectName(u"lbl_d001_caption")

        self.decisionLayout.addWidget(self.lbl_d001_caption, 1, 0, 1, 1)

        self.spin_d001 = QDoubleSpinBox(self.grpDecisions)
        self.spin_d001.setObjectName(u"spin_d001")
        self.spin_d001.setDecimals(4)
        self.spin_d001.setMinimum(0.100000000000000)
        self.spin_d001.setMaximum(10.000000000000000)
        self.spin_d001.setSingleStep(0.010000000000000)

        self.decisionLayout.addWidget(self.spin_d001, 1, 1, 1, 1)

        self.lbl_cell = QLabel(self.grpDecisions)
        self.lbl_cell.setObjectName(u"lbl_cell")

        self.decisionLayout.addWidget(self.lbl_cell, 1, 2, 1, 1)

        self.lbl_warning = QLabel(self.grpDecisions)
        self.lbl_warning.setObjectName(u"lbl_warning")
        self.lbl_warning.setWordWrap(True)

        self.decisionLayout.addWidget(self.lbl_warning, 2, 0, 1, 3)


        self.rootLayout.addWidget(self.grpDecisions)

        self.grpRows = QGroupBox(CifImportDialog)
        self.grpRows.setObjectName(u"grpRows")
        self.rowsLayout = QVBoxLayout(self.grpRows)
        self.rowsLayout.setObjectName(u"rowsLayout")
        self.lbl_rows_hint = QLabel(self.grpRows)
        self.lbl_rows_hint.setObjectName(u"lbl_rows_hint")
        self.lbl_rows_hint.setWordWrap(True)

        self.rowsLayout.addWidget(self.lbl_rows_hint)

        self.tbl_rows = QTableView(self.grpRows)
        self.tbl_rows.setObjectName(u"tbl_rows")
        self.tbl_rows.setAlternatingRowColors(True)
        self.tbl_rows.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.rowsLayout.addWidget(self.tbl_rows)

        self.lbl_totals = QLabel(self.grpRows)
        self.lbl_totals.setObjectName(u"lbl_totals")

        self.rowsLayout.addWidget(self.lbl_totals)


        self.rootLayout.addWidget(self.grpRows)

        self.buttonRow = QHBoxLayout()
        self.buttonRow.setObjectName(u"buttonRow")
        self.btn_reset = QPushButton(CifImportDialog)
        self.btn_reset.setObjectName(u"btn_reset")
        self.btn_reset.setAutoDefault(False)

        self.buttonRow.addWidget(self.btn_reset)

        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonRow.addItem(self.buttonSpacer)

        self.buttonBox = QDialogButtonBox(CifImportDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.buttonRow.addWidget(self.buttonBox)


        self.rootLayout.addLayout(self.buttonRow)


        self.retranslateUi(CifImportDialog)

        self.btn_reset.setDefault(False)


        QMetaObject.connectSlotsByName(CifImportDialog)
    # setupUi

    def retranslateUi(self, CifImportDialog):
        CifImportDialog.setWindowTitle(QCoreApplication.translate("CifImportDialog", u"Import component from CIF", None))
        self.lbl_source.setText(QCoreApplication.translate("CifImportDialog", u"No file loaded.", None))
        self.grpDecisions.setTitle(QCoreApplication.translate("CifImportDialog", u"1. What the projection had to decide", None))
        self.lbl_divisor_caption.setText(QCoreApplication.translate("CifImportDialog", u"Layers stacked in the published cell", None))
#if QT_CONFIG(tooltip)
        self.spin_divisor.setToolTip(QCoreApplication.translate("CifImportDialog", u"How many identical layers the published cell stacks along c. Detected automatically; change it if the basal spacing below is a multiple of what you expect.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_divisor_note.setText("")
        self.lbl_d001_caption.setText(QCoreApplication.translate("CifImportDialog", u"Basal spacing d001", None))
#if QT_CONFIG(tooltip)
        self.spin_d001.setToolTip(QCoreApplication.translate("CifImportDialog", u"The repeat distance of one layer, taken from the cell. Editing it rescales nothing: it states what this component's repeat is.", None))
#endif // QT_CONFIG(tooltip)
        self.spin_d001.setSuffix(QCoreApplication.translate("CifImportDialog", u" nm", None))
        self.lbl_cell.setText("")
        self.lbl_warning.setText("")
        self.grpRows.setTitle(QCoreApplication.translate("CifImportDialog", u"2. Projected atoms \u2014 correct anything the projection got wrong", None))
        self.lbl_rows_hint.setText(QCoreApplication.translate("CifImportDialog", u"Kind tells an oxygen from a hydroxyl; Sheet says whether the row belongs to the layer or the interlayer.", None))
        self.lbl_totals.setText("")
#if QT_CONFIG(tooltip)
        self.btn_reset.setToolTip(QCoreApplication.translate("CifImportDialog", u"Discard your edits and go back to what the projection proposed.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_reset.setText(QCoreApplication.translate("CifImportDialog", u"Reset to proposal", None))
    # retranslateUi

