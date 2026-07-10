# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'csds.ui'
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
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QFormLayout, QGroupBox,
    QLabel, QSizePolicy, QVBoxLayout, QWidget)

class Ui_CSDSWidget(object):
    def setupUi(self, CSDSWidget):
        if not CSDSWidget.objectName():
            CSDSWidget.setObjectName(u"CSDSWidget")
        self.csdsRootLayout = QVBoxLayout(CSDSWidget)
        self.csdsRootLayout.setObjectName(u"csdsRootLayout")
        self.csdsForm = QFormLayout()
        self.csdsForm.setObjectName(u"csdsForm")
        self.lblAverage = QLabel(CSDSWidget)
        self.lblAverage.setObjectName(u"lblAverage")

        self.csdsForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblAverage)

        self.csds_average = QDoubleSpinBox(CSDSWidget)
        self.csds_average.setObjectName(u"csds_average")
        self.csds_average.setDecimals(2)
        self.csds_average.setMinimum(1.000000000000000)
        self.csds_average.setMaximum(1000.000000000000000)
        self.csds_average.setSingleStep(1.000000000000000)
        self.csds_average.setValue(10.000000000000000)

        self.csdsForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.csds_average)

        self.lblRange = QLabel(CSDSWidget)
        self.lblRange.setObjectName(u"lblRange")

        self.csdsForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblRange)

        self.csds_range = QLabel(CSDSWidget)
        self.csds_range.setObjectName(u"csds_range")

        self.csdsForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.csds_range)


        self.csdsRootLayout.addLayout(self.csdsForm)

        self.grpCsdsHist = QGroupBox(CSDSWidget)
        self.grpCsdsHist.setObjectName(u"grpCsdsHist")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.grpCsdsHist.sizePolicy().hasHeightForWidth())
        self.grpCsdsHist.setSizePolicy(sizePolicy)
        self.csdsHistLayout = QVBoxLayout(self.grpCsdsHist)
        self.csdsHistLayout.setObjectName(u"csdsHistLayout")

        self.csdsRootLayout.addWidget(self.grpCsdsHist)


        self.retranslateUi(CSDSWidget)

        QMetaObject.connectSlotsByName(CSDSWidget)
    # setupUi

    def retranslateUi(self, CSDSWidget):
        self.lblAverage.setText(QCoreApplication.translate("CSDSWidget", u"Mean CSDS [layers]", None))
#if QT_CONFIG(tooltip)
        self.csds_average.setToolTip(QCoreApplication.translate("CSDSWidget", u"The mean coherent-scattering-domain size (average number of stacked layers).", None))
#endif // QT_CONFIG(tooltip)
        self.lblRange.setText(QCoreApplication.translate("CSDSWidget", u"Range [layers]", None))
        self.csds_range.setText(QCoreApplication.translate("CSDSWidget", u"1 - 25", None))
        self.grpCsdsHist.setTitle(QCoreApplication.translate("CSDSWidget", u"Size distribution", None))
        pass
    # retranslateUi

