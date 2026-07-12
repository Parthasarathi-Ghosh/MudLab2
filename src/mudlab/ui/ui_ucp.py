# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ucp.ui'
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
    QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_UnitCellPropWidget(object):
    def setupUi(self, UnitCellPropWidget):
        if not UnitCellPropWidget.objectName():
            UnitCellPropWidget.setObjectName(u"UnitCellPropWidget")
        self.ucpRootLayout = QVBoxLayout(UnitCellPropWidget)
        self.ucpRootLayout.setSpacing(2)
        self.ucpRootLayout.setObjectName(u"ucpRootLayout")
        self.ucpRootLayout.setContentsMargins(0, 0, 0, 0)
        self.ucp_enabled = QCheckBox(UnitCellPropWidget)
        self.ucp_enabled.setObjectName(u"ucp_enabled")

        self.ucpRootLayout.addWidget(self.ucp_enabled)

        self.ucp_value = QDoubleSpinBox(UnitCellPropWidget)
        self.ucp_value.setObjectName(u"ucp_value")
        self.ucp_value.setDecimals(5)
        self.ucp_value.setMaximum(5.000000000000000)
        self.ucp_value.setSingleStep(0.001000000000000)

        self.ucpRootLayout.addWidget(self.ucp_value)

        self.box_enabled = QWidget(UnitCellPropWidget)
        self.box_enabled.setObjectName(u"box_enabled")
        self.box_enabled_layout = QHBoxLayout(self.box_enabled)
        self.box_enabled_layout.setSpacing(2)
        self.box_enabled_layout.setObjectName(u"box_enabled_layout")
        self.box_enabled_layout.setContentsMargins(0, 0, 0, 0)
        self.ucp_factor = QDoubleSpinBox(self.box_enabled)
        self.ucp_factor.setObjectName(u"ucp_factor")
        self.ucp_factor.setDecimals(5)
        self.ucp_factor.setMinimum(-1000.000000000000000)
        self.ucp_factor.setMaximum(1000.000000000000000)
        self.ucp_factor.setSingleStep(0.001000000000000)

        self.box_enabled_layout.addWidget(self.ucp_factor)

        self.lbl_mult = QLabel(self.box_enabled)
        self.lbl_mult.setObjectName(u"lbl_mult")

        self.box_enabled_layout.addWidget(self.lbl_mult)

        self.ucp_prop = QComboBox(self.box_enabled)
        self.ucp_prop.setObjectName(u"ucp_prop")

        self.box_enabled_layout.addWidget(self.ucp_prop)

        self.lbl_plus = QLabel(self.box_enabled)
        self.lbl_plus.setObjectName(u"lbl_plus")

        self.box_enabled_layout.addWidget(self.lbl_plus)

        self.ucp_constant = QDoubleSpinBox(self.box_enabled)
        self.ucp_constant.setObjectName(u"ucp_constant")
        self.ucp_constant.setDecimals(5)
        self.ucp_constant.setMinimum(-1000.000000000000000)
        self.ucp_constant.setMaximum(1000.000000000000000)
        self.ucp_constant.setSingleStep(0.001000000000000)

        self.box_enabled_layout.addWidget(self.ucp_constant)


        self.ucpRootLayout.addWidget(self.box_enabled)


        self.retranslateUi(UnitCellPropWidget)

        QMetaObject.connectSlotsByName(UnitCellPropWidget)
    # setupUi

    def retranslateUi(self, UnitCellPropWidget):
#if QT_CONFIG(tooltip)
        self.ucp_enabled.setToolTip(QCoreApplication.translate("UnitCellPropWidget", u"Compute this cell length from another property instead of typing it.", None))
#endif // QT_CONFIG(tooltip)
        self.ucp_enabled.setText(QCoreApplication.translate("UnitCellPropWidget", u"Derived (factor \u00d7 property + constant)", None))
#if QT_CONFIG(tooltip)
        self.ucp_value.setToolTip(QCoreApplication.translate("UnitCellPropWidget", u"Fixed cell length [nm]. When derived, shows the computed value.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_mult.setText(QCoreApplication.translate("UnitCellPropWidget", u" \u00d7 ", None))
#if QT_CONFIG(tooltip)
        self.ucp_prop.setToolTip(QCoreApplication.translate("UnitCellPropWidget", u"The property this cell length is derived from (an atom pn, or the other cell length).", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_plus.setText(QCoreApplication.translate("UnitCellPropWidget", u" + ", None))
        pass
    # retranslateUi

