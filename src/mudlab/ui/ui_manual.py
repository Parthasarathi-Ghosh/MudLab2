# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'manual.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QPushButton,
    QSizePolicy, QSpacerItem, QTextBrowser, QVBoxLayout,
    QWidget)

class Ui_ManualDialog(object):
    def setupUi(self, ManualDialog):
        if not ManualDialog.objectName():
            ManualDialog.setObjectName(u"ManualDialog")
        ManualDialog.resize(860, 720)
        ManualDialog.setSizeGripEnabled(True)
        self.rootLayout = QVBoxLayout(ManualDialog)
        self.rootLayout.setObjectName(u"rootLayout")
        self.browser = QTextBrowser(ManualDialog)
        self.browser.setObjectName(u"browser")
        self.browser.setOpenExternalLinks(False)
        self.browser.setOpenLinks(False)

        self.rootLayout.addWidget(self.browser)

        self.buttonRow = QHBoxLayout()
        self.buttonRow.setObjectName(u"buttonRow")
        self.btn_back = QPushButton(ManualDialog)
        self.btn_back.setObjectName(u"btn_back")
        self.btn_back.setAutoDefault(False)

        self.buttonRow.addWidget(self.btn_back)

        self.btn_contents = QPushButton(ManualDialog)
        self.btn_contents.setObjectName(u"btn_contents")
        self.btn_contents.setAutoDefault(False)

        self.buttonRow.addWidget(self.btn_contents)

        self.btn_print = QPushButton(ManualDialog)
        self.btn_print.setObjectName(u"btn_print")
        self.btn_print.setAutoDefault(False)

        self.buttonRow.addWidget(self.btn_print)

        self.btn_export = QPushButton(ManualDialog)
        self.btn_export.setObjectName(u"btn_export")
        self.btn_export.setAutoDefault(False)

        self.buttonRow.addWidget(self.btn_export)

        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonRow.addItem(self.buttonSpacer)

        self.btn_close = QPushButton(ManualDialog)
        self.btn_close.setObjectName(u"btn_close")
        self.btn_close.setAutoDefault(False)

        self.buttonRow.addWidget(self.btn_close)


        self.rootLayout.addLayout(self.buttonRow)


        self.retranslateUi(ManualDialog)

        self.btn_back.setDefault(False)
        self.btn_contents.setDefault(False)
        self.btn_print.setDefault(False)
        self.btn_export.setDefault(False)
        self.btn_close.setDefault(False)


        QMetaObject.connectSlotsByName(ManualDialog)
    # setupUi

    def retranslateUi(self, ManualDialog):
        ManualDialog.setWindowTitle(QCoreApplication.translate("ManualDialog", u"MudLab Manual", None))
#if QT_CONFIG(tooltip)
        self.btn_back.setToolTip(QCoreApplication.translate("ManualDialog", u"Go back to the previous page", None))
#endif // QT_CONFIG(tooltip)
        self.btn_back.setText(QCoreApplication.translate("ManualDialog", u"Back", None))
#if QT_CONFIG(tooltip)
        self.btn_contents.setToolTip(QCoreApplication.translate("ManualDialog", u"Return to the start of the walkthrough", None))
#endif // QT_CONFIG(tooltip)
        self.btn_contents.setText(QCoreApplication.translate("ManualDialog", u"Contents", None))
#if QT_CONFIG(tooltip)
        self.btn_print.setToolTip(QCoreApplication.translate("ManualDialog", u"Print this page, or save it as PDF from the print dialog.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_print.setText(QCoreApplication.translate("ManualDialog", u"Print\u2026", None))
#if QT_CONFIG(tooltip)
        self.btn_export.setToolTip(QCoreApplication.translate("ManualDialog", u"Save this page as an editable document (ODT), a web page, Markdown or plain text.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_export.setText(QCoreApplication.translate("ManualDialog", u"Export\u2026", None))
        self.btn_close.setText(QCoreApplication.translate("ManualDialog", u"Close", None))
    # retranslateUi

