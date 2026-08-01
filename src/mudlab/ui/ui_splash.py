# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'splash.ui'
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
from PySide6.QtWidgets import (QApplication, QLabel, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_SplashScreen(object):
    def setupUi(self, SplashScreen):
        if not SplashScreen.objectName():
            SplashScreen.setObjectName(u"SplashScreen")
        SplashScreen.resize(480, 300)
        SplashScreen.setMinimumSize(QSize(480, 300))
        SplashScreen.setMaximumSize(QSize(480, 300))
        self.splashLayout = QVBoxLayout(SplashScreen)
        self.splashLayout.setSpacing(6)
        self.splashLayout.setObjectName(u"splashLayout")
        self.splashLayout.setContentsMargins(32, 26, 32, 20)
        self.topSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.splashLayout.addItem(self.topSpacer)

        self.lbl_logo = QLabel(SplashScreen)
        self.lbl_logo.setObjectName(u"lbl_logo")
        self.lbl_logo.setAlignment(Qt.AlignCenter)

        self.splashLayout.addWidget(self.lbl_logo)

        self.lbl_name = QLabel(SplashScreen)
        self.lbl_name.setObjectName(u"lbl_name")
        self.lbl_name.setAlignment(Qt.AlignCenter)

        self.splashLayout.addWidget(self.lbl_name)

        self.lbl_version = QLabel(SplashScreen)
        self.lbl_version.setObjectName(u"lbl_version")
        self.lbl_version.setAlignment(Qt.AlignCenter)

        self.splashLayout.addWidget(self.lbl_version)

        self.lbl_tagline = QLabel(SplashScreen)
        self.lbl_tagline.setObjectName(u"lbl_tagline")
        self.lbl_tagline.setAlignment(Qt.AlignCenter)
        self.lbl_tagline.setWordWrap(True)

        self.splashLayout.addWidget(self.lbl_tagline)

        self.bottomSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.splashLayout.addItem(self.bottomSpacer)

        self.lbl_status = QLabel(SplashScreen)
        self.lbl_status.setObjectName(u"lbl_status")
        self.lbl_status.setAlignment(Qt.AlignCenter)

        self.splashLayout.addWidget(self.lbl_status)


        self.retranslateUi(SplashScreen)

        QMetaObject.connectSlotsByName(SplashScreen)
    # setupUi

    def retranslateUi(self, SplashScreen):
        self.lbl_name.setText(QCoreApplication.translate("SplashScreen", u"MudLab", None))
        self.lbl_version.setText(QCoreApplication.translate("SplashScreen", u"version", None))
        self.lbl_tagline.setText(QCoreApplication.translate("SplashScreen", u"X-ray Diffraction Analysis of Disordered Layered Minerals", None))
        self.lbl_status.setText(QCoreApplication.translate("SplashScreen", u"Starting...", None))
        pass
    # retranslateUi

