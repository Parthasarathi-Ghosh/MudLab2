# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'structure_diagram.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QHBoxLayout, QPlainTextEdit, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_StructureDiagramDialog(object):
    def setupUi(self, StructureDiagramDialog):
        if not StructureDiagramDialog.objectName():
            StructureDiagramDialog.setObjectName(u"StructureDiagramDialog")
        StructureDiagramDialog.resize(740, 540)
        self.dialogLayout = QVBoxLayout(StructureDiagramDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.txt_diagram = QPlainTextEdit(StructureDiagramDialog)
        self.txt_diagram.setObjectName(u"txt_diagram")
        self.txt_diagram.setReadOnly(True)
        self.txt_diagram.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.txt_diagram.setTabChangesFocus(True)

        self.dialogLayout.addWidget(self.txt_diagram)

        self.buttonRow = QHBoxLayout()
        self.buttonRow.setObjectName(u"buttonRow")
        self.button_copy = QPushButton(StructureDiagramDialog)
        self.button_copy.setObjectName(u"button_copy")

        self.buttonRow.addWidget(self.button_copy)

        self.button_save = QPushButton(StructureDiagramDialog)
        self.button_save.setObjectName(u"button_save")

        self.buttonRow.addWidget(self.button_save)

        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonRow.addItem(self.buttonSpacer)

        self.buttonBox = QDialogButtonBox(StructureDiagramDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.buttonRow.addWidget(self.buttonBox)


        self.dialogLayout.addLayout(self.buttonRow)


        self.retranslateUi(StructureDiagramDialog)

        QMetaObject.connectSlotsByName(StructureDiagramDialog)
    # setupUi

    def retranslateUi(self, StructureDiagramDialog):
        StructureDiagramDialog.setWindowTitle(QCoreApplication.translate("StructureDiagramDialog", u"Structure", None))
        self.button_copy.setText(QCoreApplication.translate("StructureDiagramDialog", u"Copy", None))
#if QT_CONFIG(tooltip)
        self.button_copy.setToolTip(QCoreApplication.translate("StructureDiagramDialog", u"Copy the diagram to the clipboard as text.", None))
#endif // QT_CONFIG(tooltip)
        self.button_save.setText(QCoreApplication.translate("StructureDiagramDialog", u"Save as text...", None))
#if QT_CONFIG(tooltip)
        self.button_save.setToolTip(QCoreApplication.translate("StructureDiagramDialog", u"Write the diagram to a .txt file.", None))
#endif // QT_CONFIG(tooltip)
    # retranslateUi

