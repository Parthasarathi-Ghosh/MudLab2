# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'line_properties.ui'
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
    QFormLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QWidget)

class Ui_LinePropertiesWidget(object):
    def setupUi(self, LinePropertiesWidget):
        if not LinePropertiesWidget.objectName():
            LinePropertiesWidget.setObjectName(u"LinePropertiesWidget")
        self.linePropsForm = QFormLayout(LinePropertiesWidget)
        self.linePropsForm.setObjectName(u"linePropsForm")
        self.linePropsForm.setContentsMargins(0, 0, 0, 0)
        self.lblColor = QLabel(LinePropertiesWidget)
        self.lblColor.setObjectName(u"lblColor")

        self.linePropsForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblColor)

        self.colorRow = QHBoxLayout()
        self.colorRow.setObjectName(u"colorRow")
        self.color_button = QPushButton(LinePropertiesWidget)
        self.color_button.setObjectName(u"color_button")
        self.color_button.setEnabled(False)

        self.colorRow.addWidget(self.color_button)

        self.inherit_color = QCheckBox(LinePropertiesWidget)
        self.inherit_color.setObjectName(u"inherit_color")
        self.inherit_color.setChecked(True)

        self.colorRow.addWidget(self.inherit_color)


        self.linePropsForm.setLayout(0, QFormLayout.ItemRole.FieldRole, self.colorRow)

        self.lblLinewidth = QLabel(LinePropertiesWidget)
        self.lblLinewidth.setObjectName(u"lblLinewidth")

        self.linePropsForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblLinewidth)

        self.linewidthRow = QHBoxLayout()
        self.linewidthRow.setObjectName(u"linewidthRow")
        self.linewidth = QDoubleSpinBox(LinePropertiesWidget)
        self.linewidth.setObjectName(u"linewidth")
        self.linewidth.setEnabled(False)
        self.linewidth.setDecimals(1)
        self.linewidth.setMinimum(1.000000000000000)
        self.linewidth.setMaximum(100.000000000000000)

        self.linewidthRow.addWidget(self.linewidth)

        self.inherit_lw = QCheckBox(LinePropertiesWidget)
        self.inherit_lw.setObjectName(u"inherit_lw")
        self.inherit_lw.setChecked(True)

        self.linewidthRow.addWidget(self.inherit_lw)


        self.linePropsForm.setLayout(1, QFormLayout.ItemRole.FieldRole, self.linewidthRow)

        self.lblLinestyle = QLabel(LinePropertiesWidget)
        self.lblLinestyle.setObjectName(u"lblLinestyle")

        self.linePropsForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblLinestyle)

        self.linestyleRow = QHBoxLayout()
        self.linestyleRow.setObjectName(u"linestyleRow")
        self.linestyle = QComboBox(LinePropertiesWidget)
        self.linestyle.addItem("")
        self.linestyle.addItem("")
        self.linestyle.addItem("")
        self.linestyle.addItem("")
        self.linestyle.addItem("")
        self.linestyle.setObjectName(u"linestyle")
        self.linestyle.setEnabled(False)

        self.linestyleRow.addWidget(self.linestyle)

        self.inherit_ls = QCheckBox(LinePropertiesWidget)
        self.inherit_ls.setObjectName(u"inherit_ls")
        self.inherit_ls.setChecked(True)

        self.linestyleRow.addWidget(self.inherit_ls)


        self.linePropsForm.setLayout(2, QFormLayout.ItemRole.FieldRole, self.linestyleRow)

        self.lblMarker = QLabel(LinePropertiesWidget)
        self.lblMarker.setObjectName(u"lblMarker")

        self.linePropsForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblMarker)

        self.markerRow = QHBoxLayout()
        self.markerRow.setObjectName(u"markerRow")
        self.marker = QComboBox(LinePropertiesWidget)
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.addItem("")
        self.marker.setObjectName(u"marker")
        self.marker.setEnabled(False)

        self.markerRow.addWidget(self.marker)

        self.inherit_marker = QCheckBox(LinePropertiesWidget)
        self.inherit_marker.setObjectName(u"inherit_marker")
        self.inherit_marker.setChecked(True)

        self.markerRow.addWidget(self.inherit_marker)


        self.linePropsForm.setLayout(3, QFormLayout.ItemRole.FieldRole, self.markerRow)

        self.lblCap = QLabel(LinePropertiesWidget)
        self.lblCap.setObjectName(u"lblCap")

        self.linePropsForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lblCap)

        self.cap_value = QDoubleSpinBox(LinePropertiesWidget)
        self.cap_value.setObjectName(u"cap_value")
        self.cap_value.setDecimals(0)
        self.cap_value.setMaximum(1000000000000.000000000000000)
        self.cap_value.setSingleStep(100.000000000000000)

        self.linePropsForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.cap_value)


        self.retranslateUi(LinePropertiesWidget)

        self.linestyle.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(LinePropertiesWidget)
    # setupUi

    def retranslateUi(self, LinePropertiesWidget):
        self.lblColor.setText(QCoreApplication.translate("LinePropertiesWidget", u"Color", None))
        self.color_button.setText(QCoreApplication.translate("LinePropertiesWidget", u"#000000", None))
        self.inherit_color.setText(QCoreApplication.translate("LinePropertiesWidget", u"Use default colour", None))
        self.lblLinewidth.setText(QCoreApplication.translate("LinePropertiesWidget", u"Linewidth", None))
        self.inherit_lw.setText(QCoreApplication.translate("LinePropertiesWidget", u"Use default linewidth", None))
        self.lblLinestyle.setText(QCoreApplication.translate("LinePropertiesWidget", u"Linestyle", None))
        self.linestyle.setItemText(0, QCoreApplication.translate("LinePropertiesWidget", u"Nothing", None))
        self.linestyle.setItemText(1, QCoreApplication.translate("LinePropertiesWidget", u"Solid", None))
        self.linestyle.setItemText(2, QCoreApplication.translate("LinePropertiesWidget", u"Dashed", None))
        self.linestyle.setItemText(3, QCoreApplication.translate("LinePropertiesWidget", u"Dash Dot", None))
        self.linestyle.setItemText(4, QCoreApplication.translate("LinePropertiesWidget", u"Dotted", None))

        self.inherit_ls.setText(QCoreApplication.translate("LinePropertiesWidget", u"Use default linestyle", None))
        self.lblMarker.setText(QCoreApplication.translate("LinePropertiesWidget", u"Marker", None))
        self.marker.setItemText(0, QCoreApplication.translate("LinePropertiesWidget", u"No marker", None))
        self.marker.setItemText(1, QCoreApplication.translate("LinePropertiesWidget", u"Point", None))
        self.marker.setItemText(2, QCoreApplication.translate("LinePropertiesWidget", u"Pixel", None))
        self.marker.setItemText(3, QCoreApplication.translate("LinePropertiesWidget", u"Plus", None))
        self.marker.setItemText(4, QCoreApplication.translate("LinePropertiesWidget", u"Cross", None))
        self.marker.setItemText(5, QCoreApplication.translate("LinePropertiesWidget", u"Diamond", None))
        self.marker.setItemText(6, QCoreApplication.translate("LinePropertiesWidget", u"Circle", None))
        self.marker.setItemText(7, QCoreApplication.translate("LinePropertiesWidget", u"Triangle down", None))
        self.marker.setItemText(8, QCoreApplication.translate("LinePropertiesWidget", u"Triangle up", None))
        self.marker.setItemText(9, QCoreApplication.translate("LinePropertiesWidget", u"Triangle left", None))
        self.marker.setItemText(10, QCoreApplication.translate("LinePropertiesWidget", u"Triangle right", None))
        self.marker.setItemText(11, QCoreApplication.translate("LinePropertiesWidget", u"Octagon", None))
        self.marker.setItemText(12, QCoreApplication.translate("LinePropertiesWidget", u"Square", None))
        self.marker.setItemText(13, QCoreApplication.translate("LinePropertiesWidget", u"Pentagon", None))
        self.marker.setItemText(14, QCoreApplication.translate("LinePropertiesWidget", u"Star", None))
        self.marker.setItemText(15, QCoreApplication.translate("LinePropertiesWidget", u"Hexagon", None))

        self.inherit_marker.setText(QCoreApplication.translate("LinePropertiesWidget", u"Use default marker", None))
        self.lblCap.setText(QCoreApplication.translate("LinePropertiesWidget", u"Cut-off value", None))
        self.cap_value.setSuffix(QCoreApplication.translate("LinePropertiesWidget", u" counts", None))
        pass
    # retranslateUi

