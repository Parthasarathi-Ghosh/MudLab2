# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'default_phases.ui'
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
    QPushButton, QSizePolicy, QSpacerItem, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_DefaultPhasesDialog(object):
    def setupUi(self, DefaultPhasesDialog):
        if not DefaultPhasesDialog.objectName():
            DefaultPhasesDialog.setObjectName(u"DefaultPhasesDialog")
        DefaultPhasesDialog.resize(620, 420)
        DefaultPhasesDialog.setMinimumSize(QSize(520, 340))
        DefaultPhasesDialog.setModal(True)
        self.defaultPhasesLayout = QVBoxLayout(DefaultPhasesDialog)
        self.defaultPhasesLayout.setObjectName(u"defaultPhasesLayout")
        self.lblIntro = QLabel(DefaultPhasesDialog)
        self.lblIntro.setObjectName(u"lblIntro")
        self.lblIntro.setWordWrap(True)

        self.defaultPhasesLayout.addWidget(self.lblIntro)

        self.tbl_phases = QTableWidget(DefaultPhasesDialog)
        self.tbl_phases.setObjectName(u"tbl_phases")
        self.tbl_phases.setAlternatingRowColors(True)
        self.tbl_phases.setSelectionMode(QAbstractItemView.NoSelection)

        self.defaultPhasesLayout.addWidget(self.tbl_phases)

        self.actionRow = QHBoxLayout()
        self.actionRow.setObjectName(u"actionRow")
        self.button_match = QPushButton(DefaultPhasesDialog)
        self.button_match.setObjectName(u"button_match")

        self.actionRow.addWidget(self.button_match)

        self.button_clear = QPushButton(DefaultPhasesDialog)
        self.button_clear.setObjectName(u"button_clear")

        self.actionRow.addWidget(self.button_clear)

        self.actionSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.actionRow.addItem(self.actionSpacer)


        self.defaultPhasesLayout.addLayout(self.actionRow)

        self.lbl_status = QLabel(DefaultPhasesDialog)
        self.lbl_status.setObjectName(u"lbl_status")
        self.lbl_status.setWordWrap(True)

        self.defaultPhasesLayout.addWidget(self.lbl_status)

        self.buttonBox = QDialogButtonBox(DefaultPhasesDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.defaultPhasesLayout.addWidget(self.buttonBox)


        self.retranslateUi(DefaultPhasesDialog)

        QMetaObject.connectSlotsByName(DefaultPhasesDialog)
    # setupUi

    def retranslateUi(self, DefaultPhasesDialog):
        DefaultPhasesDialog.setWindowTitle(QCoreApplication.translate("DefaultPhasesDialog", u"Default phases", None))
        self.lblIntro.setText(QCoreApplication.translate("DefaultPhasesDialog", u"For each phase, choose the built-in default phase it started as. This cannot be worked out automatically: adding a default phase gives it a new identity, and phases are often renamed afterwards.", None))
        self.button_match.setText(QCoreApplication.translate("DefaultPhasesDialog", u"Match by name", None))
#if QT_CONFIG(tooltip)
        self.button_match.setToolTip(QCoreApplication.translate("DefaultPhasesDialog", u"Fill in every phase whose name exactly matches a built-in default phase. Renamed phases are left for you to set.", None))
#endif // QT_CONFIG(tooltip)
        self.button_clear.setText(QCoreApplication.translate("DefaultPhasesDialog", u"Clear all", None))
        self.lbl_status.setText("")
    # retranslateUi

