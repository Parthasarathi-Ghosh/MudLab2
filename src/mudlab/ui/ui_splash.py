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
from PySide6.QtWidgets import (QApplication, QFrame, QLabel, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_SplashScreen(object):
    def setupUi(self, SplashScreen):
        if not SplashScreen.objectName():
            SplashScreen.setObjectName(u"SplashScreen")
        SplashScreen.resize(520, 460)
        self.outerLayout = QVBoxLayout(SplashScreen)
        self.outerLayout.setSpacing(0)
        self.outerLayout.setObjectName(u"outerLayout")
        self.outerLayout.setContentsMargins(0, 0, 0, 0)
        self.splashCard = QFrame(SplashScreen)
        self.splashCard.setObjectName(u"splashCard")
        self.splashLayout = QVBoxLayout(self.splashCard)
        self.splashLayout.setSpacing(0)
        self.splashLayout.setObjectName(u"splashLayout")
        self.splashLayout.setContentsMargins(40, 30, 40, 24)
        self.lbl_logo = QLabel(self.splashCard)
        self.lbl_logo.setObjectName(u"lbl_logo")
        self.lbl_logo.setAlignment(Qt.AlignCenter)

        self.splashLayout.addWidget(self.lbl_logo)

        self.afterLogo = QSpacerItem(20, 14, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.splashLayout.addItem(self.afterLogo)

        self.lbl_name = QLabel(self.splashCard)
        self.lbl_name.setObjectName(u"lbl_name")
        self.lbl_name.setAlignment(Qt.AlignCenter)

        self.splashLayout.addWidget(self.lbl_name)

        self.afterName = QSpacerItem(20, 2, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.splashLayout.addItem(self.afterName)

        self.lbl_tagline = QLabel(self.splashCard)
        self.lbl_tagline.setObjectName(u"lbl_tagline")
        self.lbl_tagline.setAlignment(Qt.AlignCenter)

        self.splashLayout.addWidget(self.lbl_tagline)

        self.afterTagline = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.splashLayout.addItem(self.afterTagline)

        self.lbl_version = QLabel(self.splashCard)
        self.lbl_version.setObjectName(u"lbl_version")
        self.lbl_version.setAlignment(Qt.AlignCenter)

        self.splashLayout.addWidget(self.lbl_version)

        self.afterVersion = QSpacerItem(20, 18, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.splashLayout.addItem(self.afterVersion)

        self.separator = QFrame(self.splashCard)
        self.separator.setObjectName(u"separator")
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Plain)

        self.splashLayout.addWidget(self.separator)

        self.afterSeparator = QSpacerItem(20, 14, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.splashLayout.addItem(self.afterSeparator)

        self.lbl_status = QLabel(self.splashCard)
        self.lbl_status.setObjectName(u"lbl_status")
        self.lbl_status.setAlignment(Qt.AlignCenter)

        self.splashLayout.addWidget(self.lbl_status)


        self.outerLayout.addWidget(self.splashCard)


        self.retranslateUi(SplashScreen)

        QMetaObject.connectSlotsByName(SplashScreen)
    # setupUi

    def retranslateUi(self, SplashScreen):
        self.lbl_name.setText(QCoreApplication.translate("SplashScreen", u"MudLab", None))
        self.lbl_tagline.setText(QCoreApplication.translate("SplashScreen", u"X-ray Diffraction Analysis of Disordered Layered Minerals", None))
        self.lbl_version.setText(QCoreApplication.translate("SplashScreen", u"v0.0.0", None))
        self.lbl_status.setText(QCoreApplication.translate("SplashScreen", u"Loading ...", None))
        pass
    # retranslateUi

