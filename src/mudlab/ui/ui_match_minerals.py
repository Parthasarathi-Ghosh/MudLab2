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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QToolButton, QTreeView, QVBoxLayout,
    QWidget)

class Ui_MatchMineralsDialog(object):
    def setupUi(self, MatchMineralsDialog):
        if not MatchMineralsDialog.objectName():
            MatchMineralsDialog.setObjectName(u"MatchMineralsDialog")
        MatchMineralsDialog.resize(540, 400)
        self.dialogLayout = QVBoxLayout(MatchMineralsDialog)
        self.dialogLayout.setSpacing(6)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.dialogLayout.setContentsMargins(8, 8, 8, 8)
        self.box_targets = QHBoxLayout()
        self.box_targets.setObjectName(u"box_targets")
        self.lbl_targets = QLabel(MatchMineralsDialog)
        self.lbl_targets.setObjectName(u"lbl_targets")

        self.box_targets.addWidget(self.lbl_targets)

        self.cmb_targets = QComboBox(MatchMineralsDialog)
        self.cmb_targets.setObjectName(u"cmb_targets")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cmb_targets.sizePolicy().hasHeightForWidth())
        self.cmb_targets.setSizePolicy(sizePolicy)
        self.cmb_targets.setMaxVisibleItems(16)

        self.box_targets.addWidget(self.cmb_targets)

        self.chk_use_specimen_range = QCheckBox(MatchMineralsDialog)
        self.chk_use_specimen_range.setObjectName(u"chk_use_specimen_range")

        self.box_targets.addWidget(self.chk_use_specimen_range)


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

        self.edit_search = QLineEdit(MatchMineralsDialog)
        self.edit_search.setObjectName(u"edit_search")
        self.edit_search.setClearButtonEnabled(True)

        self.mineralsColumn.addWidget(self.edit_search)

        self.tv_minerals = QTreeView(MatchMineralsDialog)
        self.tv_minerals.setObjectName(u"tv_minerals")
        self.tv_minerals.setRootIsDecorated(False)
        self.tv_minerals.setAlternatingRowColors(True)

        self.mineralsColumn.addWidget(self.tv_minerals)


        self.listsRow.addLayout(self.mineralsColumn)


        self.dialogLayout.addLayout(self.listsRow)

        self.bottomRow = QHBoxLayout()
        self.bottomRow.setObjectName(u"bottomRow")
        self.btn_apply = QPushButton(MatchMineralsDialog)
        self.btn_apply.setObjectName(u"btn_apply")
        self.btn_apply.setAutoDefault(False)

        self.bottomRow.addWidget(self.btn_apply)

        self.buttonBox = QDialogButtonBox(MatchMineralsDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.bottomRow.addWidget(self.buttonBox)


        self.dialogLayout.addLayout(self.bottomRow)

#if QT_CONFIG(shortcut)
        self.lbl_targets.setBuddy(self.cmb_targets)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(MatchMineralsDialog)

        self.btn_apply.setDefault(False)


        QMetaObject.connectSlotsByName(MatchMineralsDialog)
    # setupUi

    def retranslateUi(self, MatchMineralsDialog):
        MatchMineralsDialog.setWindowTitle(QCoreApplication.translate("MatchMineralsDialog", u"Match minerals", None))
        self.lbl_targets.setText(QCoreApplication.translate("MatchMineralsDialog", u"Targets", None))
#if QT_CONFIG(tooltip)
        self.cmb_targets.setToolTip(QCoreApplication.translate("MatchMineralsDialog", u"The peaks the minerals are scored against. Tick or untick peaks to change them; the scores update at once.", None))
#endif // QT_CONFIG(tooltip)
        self.chk_use_specimen_range.setText(QCoreApplication.translate("MatchMineralsDialog", u"Specimen range", None))
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
        self.edit_search.setPlaceholderText(QCoreApplication.translate("MatchMineralsDialog", u"Search minerals\u2026", None))
#if QT_CONFIG(tooltip)
        self.edit_search.setToolTip(QCoreApplication.translate("MatchMineralsDialog", u"Filter the list by mineral name or abbreviation.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.btn_apply.setToolTip(QCoreApplication.translate("MatchMineralsDialog", u"Add the selected mineral's abbreviation to the label of every target peak.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_apply.setText(QCoreApplication.translate("MatchMineralsDialog", u"Append labels", None))
    # retranslateUi

