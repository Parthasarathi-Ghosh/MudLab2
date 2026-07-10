# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'probabilities.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QGroupBox, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_ProbabilitiesWidget(object):
    def setupUi(self, ProbabilitiesWidget):
        if not ProbabilitiesWidget.objectName():
            ProbabilitiesWidget.setObjectName(u"ProbabilitiesWidget")
        self.probRootLayout = QVBoxLayout(ProbabilitiesWidget)
        self.probRootLayout.setObjectName(u"probRootLayout")
        self.grpIndependents = QGroupBox(ProbabilitiesWidget)
        self.grpIndependents.setObjectName(u"grpIndependents")
        self.independentsForm = QFormLayout(self.grpIndependents)
        self.independentsForm.setObjectName(u"independentsForm")

        self.probRootLayout.addWidget(self.grpIndependents)

        self.grpWeights = QGroupBox(ProbabilitiesWidget)
        self.grpWeights.setObjectName(u"grpWeights")
        self.weightsLayout = QVBoxLayout(self.grpWeights)
        self.weightsLayout.setObjectName(u"weightsLayout")

        self.probRootLayout.addWidget(self.grpWeights)

        self.grpTransitions = QGroupBox(ProbabilitiesWidget)
        self.grpTransitions.setObjectName(u"grpTransitions")
        self.transitionsLayout = QVBoxLayout(self.grpTransitions)
        self.transitionsLayout.setObjectName(u"transitionsLayout")

        self.probRootLayout.addWidget(self.grpTransitions)


        self.retranslateUi(ProbabilitiesWidget)

        QMetaObject.connectSlotsByName(ProbabilitiesWidget)
    # setupUi

    def retranslateUi(self, ProbabilitiesWidget):
        self.grpIndependents.setTitle(QCoreApplication.translate("ProbabilitiesWidget", u"Independent parameters", None))
        self.grpWeights.setTitle(QCoreApplication.translate("ProbabilitiesWidget", u"Weight fractions (W)", None))
        self.grpTransitions.setTitle(QCoreApplication.translate("ProbabilitiesWidget", u"Junction probabilities (P)", None))
        pass
    # retranslateUi

