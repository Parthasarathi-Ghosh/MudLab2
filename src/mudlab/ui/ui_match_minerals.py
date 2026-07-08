# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'match_minerals.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QToolButton,
    QTreeView, QVBoxLayout, QWidget)

class Ui_MatchMineralsDialog(object):
    def setupUi(self, MatchMineralsDialog):
        if not MatchMineralsDialog.objectName():
            MatchMineralsDialog.setObjectName(u"MatchMineralsDialog")
        MatchMineralsDialog.resize(640, 520)
        self.dialogLayout = QVBoxLayout(MatchMineralsDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.box_targets = QHBoxLayout()
        self.box_targets.setObjectName(u"box_targets")
        self.chk_use_specimen_range = QCheckBox(MatchMineralsDialog)
        self.chk_use_specimen_range.setObjectName(u"chk_use_specimen_range")

        self.box_targets.addWidget(self.chk_use_specimen_range)

        self.targetsSpacer = QSpacerItem(0, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.box_targets.addItem(self.targetsSpacer)

        self.btn_auto_match = QPushButton(MatchMineralsDialog)
        self.btn_auto_match.setObjectName(u"btn_auto_match")

        self.box_targets.addWidget(self.btn_auto_match)

        self.btn_apply = QPushButton(MatchMineralsDialog)
        self.btn_apply.setObjectName(u"btn_apply")

        self.box_targets.addWidget(self.btn_apply)


        self.dialogLayout.addLayout(self.box_targets)

        self.listsRow = QHBoxLayout()
        self.listsRow.setObjectName(u"listsRow")
        self.matchesColumn = QVBoxLayout()
        self.matchesColumn.setObjectName(u"matchesColumn")
        self.lbl_select = QLabel(MatchMineralsDialog)
        self.lbl_select.setObjectName(u"lbl_select")

        self.matchesColumn.addWidget(self.lbl_select)

        self.tv_matches = QTreeView(MatchMineralsDialog)
        self.tv_matches.setObjectName(u"tv_matches")
        self.tv_matches.setRootIsDecorated(False)
        self.tv_matches.setAlternatingRowColors(True)

        self.matchesColumn.addWidget(self.tv_matches)


        self.listsRow.addLayout(self.matchesColumn)

        self.transferColumn = QVBoxLayout()
        self.transferColumn.setObjectName(u"transferColumn")
        self.transferTopSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.transferColumn.addItem(self.transferTopSpacer)

        self.btn_rtl = QToolButton(MatchMineralsDialog)
        self.btn_rtl.setObjectName(u"btn_rtl")

        self.transferColumn.addWidget(self.btn_rtl)

        self.btn_ltr = QToolButton(MatchMineralsDialog)
        self.btn_ltr.setObjectName(u"btn_ltr")

        self.transferColumn.addWidget(self.btn_ltr)

        self.transferBottomSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.transferColumn.addItem(self.transferBottomSpacer)


        self.listsRow.addLayout(self.transferColumn)

        self.mineralsColumn = QVBoxLayout()
        self.mineralsColumn.setObjectName(u"mineralsColumn")
        self.minerals_lbl = QLabel(MatchMineralsDialog)
        self.minerals_lbl.setObjectName(u"minerals_lbl")

        self.mineralsColumn.addWidget(self.minerals_lbl)

        self.tv_minerals = QTreeView(MatchMineralsDialog)
        self.tv_minerals.setObjectName(u"tv_minerals")
        self.tv_minerals.setRootIsDecorated(False)
        self.tv_minerals.setAlternatingRowColors(True)

        self.mineralsColumn.addWidget(self.tv_minerals)


        self.listsRow.addLayout(self.mineralsColumn)


        self.dialogLayout.addLayout(self.listsRow)

        self.buttonBox = QDialogButtonBox(MatchMineralsDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(MatchMineralsDialog)

        QMetaObject.connectSlotsByName(MatchMineralsDialog)
    # setupUi

    def retranslateUi(self, MatchMineralsDialog):
        MatchMineralsDialog.setWindowTitle(QCoreApplication.translate("MatchMineralsDialog", u"Match minerals", None))
        self.chk_use_specimen_range.setText(QCoreApplication.translate("MatchMineralsDialog", u"Specimen range", None))
        self.btn_auto_match.setText(QCoreApplication.translate("MatchMineralsDialog", u"Auto match", None))
        self.btn_apply.setText(QCoreApplication.translate("MatchMineralsDialog", u"Append labels", None))
        self.lbl_select.setText(QCoreApplication.translate("MatchMineralsDialog", u"Matched minerals:", None))
#if QT_CONFIG(tooltip)
        self.btn_rtl.setToolTip(QCoreApplication.translate("MatchMineralsDialog", u"Add the selected mineral to the matches", None))
#endif // QT_CONFIG(tooltip)
        self.btn_rtl.setText(QCoreApplication.translate("MatchMineralsDialog", u"\u25c4", None))
#if QT_CONFIG(tooltip)
        self.btn_ltr.setToolTip(QCoreApplication.translate("MatchMineralsDialog", u"Remove the selected mineral from the matches", None))
#endif // QT_CONFIG(tooltip)
        self.btn_ltr.setText(QCoreApplication.translate("MatchMineralsDialog", u"\u25ba", None))
        self.minerals_lbl.setText(QCoreApplication.translate("MatchMineralsDialog", u"All minerals:", None))
    # retranslateUi

