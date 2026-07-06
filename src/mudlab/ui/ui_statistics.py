# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'statistics.ui'
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
    QFormLayout, QLabel, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_StatisticsDialog(object):
    def setupUi(self, StatisticsDialog):
        if not StatisticsDialog.objectName():
            StatisticsDialog.setObjectName(u"StatisticsDialog")
        self.dialogLayout = QVBoxLayout(StatisticsDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.statisticsForm = QFormLayout()
        self.statisticsForm.setObjectName(u"statisticsForm")
        self.points_lbl = QLabel(StatisticsDialog)
        self.points_lbl.setObjectName(u"points_lbl")

        self.statisticsForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.points_lbl)

        self.lbl_points = QLabel(StatisticsDialog)
        self.lbl_points.setObjectName(u"lbl_points")

        self.statisticsForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.lbl_points)

        self.chi2_lbl = QLabel(StatisticsDialog)
        self.chi2_lbl.setObjectName(u"chi2_lbl")

        self.statisticsForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.chi2_lbl)

        self.lbl_chi2 = QLabel(StatisticsDialog)
        self.lbl_chi2.setObjectName(u"lbl_chi2")

        self.statisticsForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.lbl_chi2)

        self.R2_lbl = QLabel(StatisticsDialog)
        self.R2_lbl.setObjectName(u"R2_lbl")

        self.statisticsForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.R2_lbl)

        self.lbl_R2 = QLabel(StatisticsDialog)
        self.lbl_R2.setObjectName(u"lbl_R2")

        self.statisticsForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.lbl_R2)

        self.Rp_lbl = QLabel(StatisticsDialog)
        self.Rp_lbl.setObjectName(u"Rp_lbl")

        self.statisticsForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.Rp_lbl)

        self.lbl_Rp = QLabel(StatisticsDialog)
        self.lbl_Rp.setObjectName(u"lbl_Rp")

        self.statisticsForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.lbl_Rp)

        self.Rwp_lbl = QLabel(StatisticsDialog)
        self.Rwp_lbl.setObjectName(u"Rwp_lbl")

        self.statisticsForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.Rwp_lbl)

        self.lbl_Rwp = QLabel(StatisticsDialog)
        self.lbl_Rwp.setObjectName(u"lbl_Rwp")

        self.statisticsForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.lbl_Rwp)

        self.Re_lbl = QLabel(StatisticsDialog)
        self.Re_lbl.setObjectName(u"Re_lbl")

        self.statisticsForm.setWidget(5, QFormLayout.ItemRole.LabelRole, self.Re_lbl)

        self.lbl_Re = QLabel(StatisticsDialog)
        self.lbl_Re.setObjectName(u"lbl_Re")

        self.statisticsForm.setWidget(5, QFormLayout.ItemRole.FieldRole, self.lbl_Re)


        self.dialogLayout.addLayout(self.statisticsForm)

        self.buttonBox = QDialogButtonBox(StatisticsDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(StatisticsDialog)

        QMetaObject.connectSlotsByName(StatisticsDialog)
    # setupUi

    def retranslateUi(self, StatisticsDialog):
        StatisticsDialog.setWindowTitle(QCoreApplication.translate("StatisticsDialog", u"Statistics", None))
        self.points_lbl.setText(QCoreApplication.translate("StatisticsDialog", u"Data points", None))
        self.lbl_points.setText(QCoreApplication.translate("StatisticsDialog", u"0", None))
        self.chi2_lbl.setText(QCoreApplication.translate("StatisticsDialog", u"\u03c7\u00b2", None))
        self.lbl_chi2.setText(QCoreApplication.translate("StatisticsDialog", u"0", None))
        self.R2_lbl.setText(QCoreApplication.translate("StatisticsDialog", u"R\u00b2", None))
        self.lbl_R2.setText(QCoreApplication.translate("StatisticsDialog", u"0", None))
        self.Rp_lbl.setText(QCoreApplication.translate("StatisticsDialog", u"Rp [%]", None))
        self.lbl_Rp.setText(QCoreApplication.translate("StatisticsDialog", u"0", None))
        self.Rwp_lbl.setText(QCoreApplication.translate("StatisticsDialog", u"Rwp [%]", None))
        self.lbl_Rwp.setText(QCoreApplication.translate("StatisticsDialog", u"0", None))
        self.Re_lbl.setText(QCoreApplication.translate("StatisticsDialog", u"Re [%]", None))
        self.lbl_Re.setText(QCoreApplication.translate("StatisticsDialog", u"0", None))
    # retranslateUi

