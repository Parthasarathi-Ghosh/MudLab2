# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'nonclay.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QSpacerItem,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_NonclayDialog(object):
    def setupUi(self, NonclayDialog):
        if not NonclayDialog.objectName():
            NonclayDialog.setObjectName(u"NonclayDialog")
        NonclayDialog.resize(640, 520)
        self.rootLayout = QVBoxLayout(NonclayDialog)
        self.rootLayout.setObjectName(u"rootLayout")
        self.lbl_title = QLabel(NonclayDialog)
        self.lbl_title.setObjectName(u"lbl_title")
        self.lbl_title.setWordWrap(True)

        self.rootLayout.addWidget(self.lbl_title)

        self.topRow = QHBoxLayout()
        self.topRow.setObjectName(u"topRow")
        self.grp_refs = QGroupBox(NonclayDialog)
        self.grp_refs.setObjectName(u"grp_refs")
        self.refsLayout = QHBoxLayout(self.grp_refs)
        self.refsLayout.setObjectName(u"refsLayout")
        self.list_refs = QListWidget(self.grp_refs)
        self.list_refs.setObjectName(u"list_refs")

        self.refsLayout.addWidget(self.list_refs)

        self.refsButtons = QVBoxLayout()
        self.refsButtons.setObjectName(u"refsButtons")
        self.btn_add_ref = QPushButton(self.grp_refs)
        self.btn_add_ref.setObjectName(u"btn_add_ref")

        self.refsButtons.addWidget(self.btn_add_ref)

        self.btn_add_cif = QPushButton(self.grp_refs)
        self.btn_add_cif.setObjectName(u"btn_add_cif")

        self.refsButtons.addWidget(self.btn_add_cif)

        self.btn_edit_comp = QPushButton(self.grp_refs)
        self.btn_edit_comp.setObjectName(u"btn_edit_comp")

        self.refsButtons.addWidget(self.btn_edit_comp)

        self.btn_remove_ref = QPushButton(self.grp_refs)
        self.btn_remove_ref.setObjectName(u"btn_remove_ref")

        self.refsButtons.addWidget(self.btn_remove_ref)

        self.refsButtonSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.refsButtons.addItem(self.refsButtonSpacer)

        self.btn_run = QPushButton(self.grp_refs)
        self.btn_run.setObjectName(u"btn_run")

        self.refsButtons.addWidget(self.btn_run)


        self.refsLayout.addLayout(self.refsButtons)


        self.topRow.addWidget(self.grp_refs)

        self.grp_xrf = QGroupBox(NonclayDialog)
        self.grp_xrf.setObjectName(u"grp_xrf")
        self.grp_xrf.setMaximumSize(QSize(190, 16777215))
        self.xrfLayout = QVBoxLayout(self.grp_xrf)
        self.xrfLayout.setObjectName(u"xrfLayout")
        self.tbl_xrf = QTableWidget(self.grp_xrf)
        self.tbl_xrf.setObjectName(u"tbl_xrf")

        self.xrfLayout.addWidget(self.tbl_xrf)

        self.lbl_xrf_hint = QLabel(self.grp_xrf)
        self.lbl_xrf_hint.setObjectName(u"lbl_xrf_hint")
        self.lbl_xrf_hint.setWordWrap(True)

        self.xrfLayout.addWidget(self.lbl_xrf_hint)


        self.topRow.addWidget(self.grp_xrf)


        self.rootLayout.addLayout(self.topRow)

        self.tbl_results = QTableWidget(NonclayDialog)
        self.tbl_results.setObjectName(u"tbl_results")
        self.tbl_results.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_results.setAlternatingRowColors(True)
        self.tbl_results.setSelectionMode(QAbstractItemView.ContiguousSelection)

        self.rootLayout.addWidget(self.tbl_results)

        self.lbl_summary = QLabel(NonclayDialog)
        self.lbl_summary.setObjectName(u"lbl_summary")
        self.lbl_summary.setWordWrap(True)

        self.rootLayout.addWidget(self.lbl_summary)

        self.buttonRow = QHBoxLayout()
        self.buttonRow.setObjectName(u"buttonRow")
        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonRow.addItem(self.buttonSpacer)

        self.btn_copy = QPushButton(NonclayDialog)
        self.btn_copy.setObjectName(u"btn_copy")

        self.buttonRow.addWidget(self.btn_copy)

        self.btn_export = QPushButton(NonclayDialog)
        self.btn_export.setObjectName(u"btn_export")

        self.buttonRow.addWidget(self.btn_export)

        self.btn_close = QPushButton(NonclayDialog)
        self.btn_close.setObjectName(u"btn_close")

        self.buttonRow.addWidget(self.btn_close)


        self.rootLayout.addLayout(self.buttonRow)


        self.retranslateUi(NonclayDialog)

        self.btn_close.setDefault(True)


        QMetaObject.connectSlotsByName(NonclayDialog)
    # setupUi

    def retranslateUi(self, NonclayDialog):
        NonclayDialog.setWindowTitle(QCoreApplication.translate("NonclayDialog", u"Non-clay decomposition", None))
        self.lbl_title.setText(QCoreApplication.translate("NonclayDialog", u"Fit non-clay reference patterns to the clay-subtracted residual (EXPERIMENTAL). The XRD share is semi-quantitative (orientation-biased); add XRF oxides for a weight %.", None))
        self.grp_refs.setTitle(QCoreApplication.translate("NonclayDialog", u"Non-clay reference patterns", None))
#if QT_CONFIG(tooltip)
        self.btn_add_ref.setToolTip(QCoreApplication.translate("NonclayDialog", u"Add a measured non-clay reference curve (e.g. quartz).", None))
#endif // QT_CONFIG(tooltip)
        self.btn_add_ref.setText(QCoreApplication.translate("NonclayDialog", u"Add measured\u2026", None))
#if QT_CONFIG(tooltip)
        self.btn_add_cif.setToolTip(QCoreApplication.translate("NonclayDialog", u"Build a reference from a crystal structure (CIF with explicit symmetry ops, e.g. from COD/AMCSD), using this specimen's goniometer.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_add_cif.setText(QCoreApplication.translate("NonclayDialog", u"Add from CIF\u2026", None))
#if QT_CONFIG(tooltip)
        self.btn_edit_comp.setToolTip(QCoreApplication.translate("NonclayDialog", u"Set the oxide composition (wt %) of the selected reference by hand, for the XRF mass balance.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_edit_comp.setText(QCoreApplication.translate("NonclayDialog", u"Composition\u2026", None))
        self.btn_remove_ref.setText(QCoreApplication.translate("NonclayDialog", u"Remove", None))
#if QT_CONFIG(tooltip)
        self.btn_run.setToolTip(QCoreApplication.translate("NonclayDialog", u"Decompose every specimen against the loaded references.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_run.setText(QCoreApplication.translate("NonclayDialog", u"Run", None))
        self.grp_xrf.setTitle(QCoreApplication.translate("NonclayDialog", u"XRF oxides (wt %, optional)", None))
        self.lbl_xrf_hint.setText(QCoreApplication.translate("NonclayDialog", u"Enter the sample's bulk oxide wt % for a weight-% (quartz vs clay) result.", None))
        self.lbl_summary.setText("")
#if QT_CONFIG(tooltip)
        self.btn_copy.setToolTip(QCoreApplication.translate("NonclayDialog", u"Copy the results to the clipboard as CSV.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_copy.setText(QCoreApplication.translate("NonclayDialog", u"Copy", None))
#if QT_CONFIG(tooltip)
        self.btn_export.setToolTip(QCoreApplication.translate("NonclayDialog", u"Save the results to a CSV file.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_export.setText(QCoreApplication.translate("NonclayDialog", u"Export CSV\u2026", None))
        self.btn_close.setText(QCoreApplication.translate("NonclayDialog", u"Close", None))
    # retranslateUi

