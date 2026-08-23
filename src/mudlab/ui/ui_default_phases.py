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
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QCheckBox,
    QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

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

        self.chk_show_unused = QCheckBox(DefaultPhasesDialog)
        self.chk_show_unused.setObjectName(u"chk_show_unused")

        self.actionRow.addWidget(self.chk_show_unused)

        self.button_import = QPushButton(DefaultPhasesDialog)
        self.button_import.setObjectName(u"button_import")

        self.actionRow.addWidget(self.button_import)

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
        self.lblIntro.setText(QCoreApplication.translate("DefaultPhasesDialog", u"Choose the default phase each phase started as - it cannot be worked out automatically. Import .phs... adds your own reference phases.", None))
        self.button_match.setText(QCoreApplication.translate("DefaultPhasesDialog", u"Match by name", None))
#if QT_CONFIG(tooltip)
        self.button_match.setToolTip(QCoreApplication.translate("DefaultPhasesDialog", u"Fill in every phase whose name exactly matches a built-in default phase. Renamed phases are left for you to set.", None))
#endif // QT_CONFIG(tooltip)
        self.button_clear.setText(QCoreApplication.translate("DefaultPhasesDialog", u"Clear all", None))
        self.chk_show_unused.setText(QCoreApplication.translate("DefaultPhasesDialog", u"Show unused phases", None))
#if QT_CONFIG(tooltip)
        self.chk_show_unused.setToolTip(QCoreApplication.translate("DefaultPhasesDialog", u"Also list phases that are in the project but not in any mixture. They cannot affect a composition, so they are hidden by default. Anything you have already stated for them is kept either way.", None))
#endif // QT_CONFIG(tooltip)
        self.button_import.setText(QCoreApplication.translate("DefaultPhasesDialog", u"Import .phs...", None))
#if QT_CONFIG(tooltip)
        self.button_import.setToolTip(QCoreApplication.translate("DefaultPhasesDialog", u"Import your own reference phase from a .phs file, so it can be chosen as a default. It is saved with the project, and does NOT become a phase of the model.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_status.setText("")
    # retranslateUi

