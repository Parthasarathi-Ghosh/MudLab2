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
        NonclayDialog.resize(560, 460)
        self.rootLayout = QVBoxLayout(NonclayDialog)
        self.rootLayout.setObjectName(u"rootLayout")
        self.lbl_title = QLabel(NonclayDialog)
        self.lbl_title.setObjectName(u"lbl_title")
        self.lbl_title.setWordWrap(True)

        self.rootLayout.addWidget(self.lbl_title)

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

        self.btn_remove_ref = QPushButton(self.grp_refs)
        self.btn_remove_ref.setObjectName(u"btn_remove_ref")

        self.refsButtons.addWidget(self.btn_remove_ref)

        self.refsButtonSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.refsButtons.addItem(self.refsButtonSpacer)

        self.btn_run = QPushButton(self.grp_refs)
        self.btn_run.setObjectName(u"btn_run")

        self.refsButtons.addWidget(self.btn_run)


        self.refsLayout.addLayout(self.refsButtons)


        self.rootLayout.addWidget(self.grp_refs)

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
        self.lbl_title.setText(QCoreApplication.translate("NonclayDialog", u"Fit non-clay reference patterns to the clay-subtracted residual (EXPERIMENTAL). Values are a semi-quantitative intensity share, not weight %.", None))
        self.grp_refs.setTitle(QCoreApplication.translate("NonclayDialog", u"Non-clay reference patterns", None))
#if QT_CONFIG(tooltip)
        self.btn_add_ref.setToolTip(QCoreApplication.translate("NonclayDialog", u"Add a measured non-clay reference curve (e.g. quartz).", None))
#endif // QT_CONFIG(tooltip)
        self.btn_add_ref.setText(QCoreApplication.translate("NonclayDialog", u"Add measured\u2026", None))
        self.btn_remove_ref.setText(QCoreApplication.translate("NonclayDialog", u"Remove", None))
#if QT_CONFIG(tooltip)
        self.btn_run.setToolTip(QCoreApplication.translate("NonclayDialog", u"Decompose every specimen against the loaded references.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_run.setText(QCoreApplication.translate("NonclayDialog", u"Run", None))
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

