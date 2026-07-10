# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'atom_list.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QHeaderView, QPushButton,
    QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_AtomListWidget(object):
    def setupUi(self, AtomListWidget):
        if not AtomListWidget.objectName():
            AtomListWidget.setObjectName(u"AtomListWidget")
        self.atomListLayout = QVBoxLayout(AtomListWidget)
        self.atomListLayout.setObjectName(u"atomListLayout")
        self.atomListLayout.setContentsMargins(0, 0, 0, 0)
        self.tbl_atoms = QTableWidget(AtomListWidget)
        self.tbl_atoms.setObjectName(u"tbl_atoms")
        self.tbl_atoms.setAlternatingRowColors(True)

        self.atomListLayout.addWidget(self.tbl_atoms)

        self.atomActionsRow = QHBoxLayout()
        self.atomActionsRow.setObjectName(u"atomActionsRow")
        self.btn_add_atom = QPushButton(AtomListWidget)
        self.btn_add_atom.setObjectName(u"btn_add_atom")

        self.atomActionsRow.addWidget(self.btn_add_atom)

        self.btn_del_atom = QPushButton(AtomListWidget)
        self.btn_del_atom.setObjectName(u"btn_del_atom")

        self.atomActionsRow.addWidget(self.btn_del_atom)

        self.atomActionsSpacer = QSpacerItem(0, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.atomActionsRow.addItem(self.atomActionsSpacer)


        self.atomListLayout.addLayout(self.atomActionsRow)


        self.retranslateUi(AtomListWidget)

        QMetaObject.connectSlotsByName(AtomListWidget)
    # setupUi

    def retranslateUi(self, AtomListWidget):
        self.btn_add_atom.setText(QCoreApplication.translate("AtomListWidget", u"Add", None))
        self.btn_del_atom.setText(QCoreApplication.translate("AtomListWidget", u"Remove", None))
        pass
    # retranslateUi

