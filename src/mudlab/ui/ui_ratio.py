# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ratio.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QFormLayout, QLabel, QLineEdit, QSizePolicy,
    QWidget)

class Ui_AtomRatioWidget(object):
    def setupUi(self, AtomRatioWidget):
        if not AtomRatioWidget.objectName():
            AtomRatioWidget.setObjectName(u"AtomRatioWidget")
        self.ratioForm = QFormLayout(AtomRatioWidget)
        self.ratioForm.setObjectName(u"ratioForm")
        self.ratioForm.setContentsMargins(0, 0, 0, 0)
        self.lblRatioName = QLabel(AtomRatioWidget)
        self.lblRatioName.setObjectName(u"lblRatioName")

        self.ratioForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblRatioName)

        self.ratio_name = QLineEdit(AtomRatioWidget)
        self.ratio_name.setObjectName(u"ratio_name")

        self.ratioForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.ratio_name)

        self.ratio_enabled = QCheckBox(AtomRatioWidget)
        self.ratio_enabled.setObjectName(u"ratio_enabled")

        self.ratioForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.ratio_enabled)

        self.lblRatioAtom1 = QLabel(AtomRatioWidget)
        self.lblRatioAtom1.setObjectName(u"lblRatioAtom1")

        self.ratioForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblRatioAtom1)

        self.ratio_atom1 = QComboBox(AtomRatioWidget)
        self.ratio_atom1.setObjectName(u"ratio_atom1")

        self.ratioForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.ratio_atom1)

        self.lblRatioAtom2 = QLabel(AtomRatioWidget)
        self.lblRatioAtom2.setObjectName(u"lblRatioAtom2")

        self.ratioForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblRatioAtom2)

        self.ratio_atom2 = QComboBox(AtomRatioWidget)
        self.ratio_atom2.setObjectName(u"ratio_atom2")

        self.ratioForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.ratio_atom2)

        self.lblRatioValue = QLabel(AtomRatioWidget)
        self.lblRatioValue.setObjectName(u"lblRatioValue")

        self.ratioForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lblRatioValue)

        self.ratio_value = QDoubleSpinBox(AtomRatioWidget)
        self.ratio_value.setObjectName(u"ratio_value")
        self.ratio_value.setDecimals(4)
        self.ratio_value.setMaximum(1.000000000000000)
        self.ratio_value.setSingleStep(0.010000000000000)

        self.ratioForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.ratio_value)

        self.lblRatioSum = QLabel(AtomRatioWidget)
        self.lblRatioSum.setObjectName(u"lblRatioSum")

        self.ratioForm.setWidget(5, QFormLayout.ItemRole.LabelRole, self.lblRatioSum)

        self.ratio_sum = QDoubleSpinBox(AtomRatioWidget)
        self.ratio_sum.setObjectName(u"ratio_sum")
        self.ratio_sum.setDecimals(4)
        self.ratio_sum.setMaximum(100.000000000000000)
        self.ratio_sum.setSingleStep(0.100000000000000)

        self.ratioForm.setWidget(5, QFormLayout.ItemRole.FieldRole, self.ratio_sum)

        self.lblRatioFormula = QLabel(AtomRatioWidget)
        self.lblRatioFormula.setObjectName(u"lblRatioFormula")
        self.lblRatioFormula.setEnabled(False)

        self.ratioForm.setWidget(6, QFormLayout.ItemRole.FieldRole, self.lblRatioFormula)


        self.retranslateUi(AtomRatioWidget)

        QMetaObject.connectSlotsByName(AtomRatioWidget)
    # setupUi

    def retranslateUi(self, AtomRatioWidget):
        self.lblRatioName.setText(QCoreApplication.translate("AtomRatioWidget", u"Name", None))
        self.ratio_enabled.setText(QCoreApplication.translate("AtomRatioWidget", u"Enabled", None))
        self.lblRatioAtom1.setText(QCoreApplication.translate("AtomRatioWidget", u"Substituting atom", None))
#if QT_CONFIG(tooltip)
        self.ratio_atom1.setToolTip(QCoreApplication.translate("AtomRatioWidget", u"This atom's occupancy becomes ratio \u00d7 sum.", None))
#endif // QT_CONFIG(tooltip)
        self.lblRatioAtom2.setText(QCoreApplication.translate("AtomRatioWidget", u"Original atom", None))
#if QT_CONFIG(tooltip)
        self.ratio_atom2.setToolTip(QCoreApplication.translate("AtomRatioWidget", u"This atom's occupancy becomes (1 \u2212 ratio) \u00d7 sum.", None))
#endif // QT_CONFIG(tooltip)
        self.lblRatioValue.setText(QCoreApplication.translate("AtomRatioWidget", u"Ratio (0\u20131)", None))
        self.lblRatioSum.setText(QCoreApplication.translate("AtomRatioWidget", u"Sum", None))
        self.lblRatioFormula.setText(QCoreApplication.translate("AtomRatioWidget", u"substituting.pn = ratio \u00d7 sum, original.pn = (1 \u2212 ratio) \u00d7 sum", None))
        pass
    # retranslateUi

