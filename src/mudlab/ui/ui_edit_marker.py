# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_marker.ui'
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
    QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_EditMarkerWidget(object):
    def setupUi(self, EditMarkerWidget):
        if not EditMarkerWidget.objectName():
            EditMarkerWidget.setObjectName(u"EditMarkerWidget")
        self.markerLayout = QVBoxLayout(EditMarkerWidget)
        self.markerLayout.setObjectName(u"markerLayout")
        self.markerForm = QFormLayout()
        self.markerForm.setObjectName(u"markerForm")
        self.label_lbl = QLabel(EditMarkerWidget)
        self.label_lbl.setObjectName(u"label_lbl")

        self.markerForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_lbl)

        self.marker_label = QLineEdit(EditMarkerWidget)
        self.marker_label.setObjectName(u"marker_label")

        self.markerForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.marker_label)

        self.position_lbl = QLabel(EditMarkerWidget)
        self.position_lbl.setObjectName(u"position_lbl")

        self.markerForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.position_lbl)

        self.positionRow = QHBoxLayout()
        self.positionRow.setObjectName(u"positionRow")
        self.spb_position = QDoubleSpinBox(EditMarkerWidget)
        self.spb_position.setObjectName(u"spb_position")
        self.spb_position.setDecimals(4)
        self.spb_position.setMaximum(180.000000000000000)

        self.positionRow.addWidget(self.spb_position)

        self.spb_nanometer = QDoubleSpinBox(EditMarkerWidget)
        self.spb_nanometer.setObjectName(u"spb_nanometer")
        self.spb_nanometer.setDecimals(5)
        self.spb_nanometer.setMaximum(1000.000000000000000)

        self.positionRow.addWidget(self.spb_nanometer)

        self.cmd_sample = QPushButton(EditMarkerWidget)
        self.cmd_sample.setObjectName(u"cmd_sample")

        self.positionRow.addWidget(self.cmd_sample)


        self.markerForm.setLayout(1, QFormLayout.ItemRole.FieldRole, self.positionRow)

        self.marker_visible = QCheckBox(EditMarkerWidget)
        self.marker_visible.setObjectName(u"marker_visible")
        self.marker_visible.setChecked(True)

        self.markerForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.marker_visible)


        self.markerLayout.addLayout(self.markerForm)

        self.grpAppearance = QGroupBox(EditMarkerWidget)
        self.grpAppearance.setObjectName(u"grpAppearance")
        self.appearanceForm = QFormLayout(self.grpAppearance)
        self.appearanceForm.setObjectName(u"appearanceForm")
        self.colour_lbl = QLabel(self.grpAppearance)
        self.colour_lbl.setObjectName(u"colour_lbl")

        self.appearanceForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.colour_lbl)

        self.colorRow = QHBoxLayout()
        self.colorRow.setObjectName(u"colorRow")
        self.marker_color = QPushButton(self.grpAppearance)
        self.marker_color.setObjectName(u"marker_color")

        self.colorRow.addWidget(self.marker_color)

        self.marker_inherit_color = QCheckBox(self.grpAppearance)
        self.marker_inherit_color.setObjectName(u"marker_inherit_color")

        self.colorRow.addWidget(self.marker_inherit_color)


        self.appearanceForm.setLayout(0, QFormLayout.ItemRole.FieldRole, self.colorRow)

        self.line_lbl = QLabel(self.grpAppearance)
        self.line_lbl.setObjectName(u"line_lbl")

        self.appearanceForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.line_lbl)

        self.styleRow = QHBoxLayout()
        self.styleRow.setObjectName(u"styleRow")
        self.marker_style = QComboBox(self.grpAppearance)
        self.marker_style.addItem("")
        self.marker_style.addItem("")
        self.marker_style.addItem("")
        self.marker_style.addItem("")
        self.marker_style.addItem("")
        self.marker_style.addItem("")
        self.marker_style.setObjectName(u"marker_style")

        self.styleRow.addWidget(self.marker_style)

        self.marker_inherit_style = QCheckBox(self.grpAppearance)
        self.marker_inherit_style.setObjectName(u"marker_inherit_style")

        self.styleRow.addWidget(self.marker_inherit_style)


        self.appearanceForm.setLayout(1, QFormLayout.ItemRole.FieldRole, self.styleRow)

        self.angle_lbl = QLabel(self.grpAppearance)
        self.angle_lbl.setObjectName(u"angle_lbl")

        self.appearanceForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.angle_lbl)

        self.angleRow = QHBoxLayout()
        self.angleRow.setObjectName(u"angleRow")
        self.spb_angle = QDoubleSpinBox(self.grpAppearance)
        self.spb_angle.setObjectName(u"spb_angle")
        self.spb_angle.setDecimals(2)
        self.spb_angle.setMinimum(-360.000000000000000)
        self.spb_angle.setMaximum(360.000000000000000)

        self.angleRow.addWidget(self.spb_angle)

        self.marker_inherit_angle = QCheckBox(self.grpAppearance)
        self.marker_inherit_angle.setObjectName(u"marker_inherit_angle")

        self.angleRow.addWidget(self.marker_inherit_angle)


        self.appearanceForm.setLayout(2, QFormLayout.ItemRole.FieldRole, self.angleRow)

        self.align_lbl = QLabel(self.grpAppearance)
        self.align_lbl.setObjectName(u"align_lbl")

        self.appearanceForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.align_lbl)

        self.alignRow = QHBoxLayout()
        self.alignRow.setObjectName(u"alignRow")
        self.marker_align = QComboBox(self.grpAppearance)
        self.marker_align.addItem("")
        self.marker_align.addItem("")
        self.marker_align.addItem("")
        self.marker_align.setObjectName(u"marker_align")

        self.alignRow.addWidget(self.marker_align)

        self.marker_inherit_align = QCheckBox(self.grpAppearance)
        self.marker_inherit_align.setObjectName(u"marker_inherit_align")

        self.alignRow.addWidget(self.marker_inherit_align)


        self.appearanceForm.setLayout(3, QFormLayout.ItemRole.FieldRole, self.alignRow)


        self.markerLayout.addWidget(self.grpAppearance)

        self.grpConnector = QGroupBox(EditMarkerWidget)
        self.grpConnector.setObjectName(u"grpConnector")
        self.connectorForm = QFormLayout(self.grpConnector)
        self.connectorForm.setObjectName(u"connectorForm")
        self.base_lbl = QLabel(self.grpConnector)
        self.base_lbl.setObjectName(u"base_lbl")

        self.connectorForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.base_lbl)

        self.baseRow = QHBoxLayout()
        self.baseRow.setObjectName(u"baseRow")
        self.marker_base = QComboBox(self.grpConnector)
        self.marker_base.addItem("")
        self.marker_base.addItem("")
        self.marker_base.addItem("")
        self.marker_base.addItem("")
        self.marker_base.addItem("")
        self.marker_base.setObjectName(u"marker_base")

        self.baseRow.addWidget(self.marker_base)

        self.marker_inherit_base = QCheckBox(self.grpConnector)
        self.marker_inherit_base.setObjectName(u"marker_inherit_base")

        self.baseRow.addWidget(self.marker_inherit_base)


        self.connectorForm.setLayout(0, QFormLayout.ItemRole.FieldRole, self.baseRow)

        self.top_lbl = QLabel(self.grpConnector)
        self.top_lbl.setObjectName(u"top_lbl")

        self.connectorForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.top_lbl)

        self.topRow = QHBoxLayout()
        self.topRow.setObjectName(u"topRow")
        self.marker_top = QComboBox(self.grpConnector)
        self.marker_top.addItem("")
        self.marker_top.addItem("")
        self.marker_top.setObjectName(u"marker_top")

        self.topRow.addWidget(self.marker_top)

        self.marker_inherit_top = QCheckBox(self.grpConnector)
        self.marker_inherit_top.setObjectName(u"marker_inherit_top")

        self.topRow.addWidget(self.marker_inherit_top)


        self.connectorForm.setLayout(1, QFormLayout.ItemRole.FieldRole, self.topRow)

        self.offset_lbl = QLabel(self.grpConnector)
        self.offset_lbl.setObjectName(u"offset_lbl")

        self.connectorForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.offset_lbl)

        self.topOffsetRow = QHBoxLayout()
        self.topOffsetRow.setObjectName(u"topOffsetRow")
        self.spb_top_offset = QDoubleSpinBox(self.grpConnector)
        self.spb_top_offset.setObjectName(u"spb_top_offset")
        self.spb_top_offset.setDecimals(4)
        self.spb_top_offset.setMinimum(-1000000.000000000000000)
        self.spb_top_offset.setMaximum(1000000.000000000000000)

        self.topOffsetRow.addWidget(self.spb_top_offset)

        self.marker_inherit_top_offset = QCheckBox(self.grpConnector)
        self.marker_inherit_top_offset.setObjectName(u"marker_inherit_top_offset")

        self.topOffsetRow.addWidget(self.marker_inherit_top_offset)


        self.connectorForm.setLayout(2, QFormLayout.ItemRole.FieldRole, self.topOffsetRow)


        self.markerLayout.addWidget(self.grpConnector)

        self.grpOffsets = QGroupBox(EditMarkerWidget)
        self.grpOffsets.setObjectName(u"grpOffsets")
        self.offsetsForm = QFormLayout(self.grpOffsets)
        self.offsetsForm.setObjectName(u"offsetsForm")
        self.lbl_offset_x = QLabel(self.grpOffsets)
        self.lbl_offset_x.setObjectName(u"lbl_offset_x")

        self.offsetsForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_offset_x)

        self.spb_x_offset = QDoubleSpinBox(self.grpOffsets)
        self.spb_x_offset.setObjectName(u"spb_x_offset")
        self.spb_x_offset.setDecimals(4)
        self.spb_x_offset.setMinimum(-1000.000000000000000)
        self.spb_x_offset.setMaximum(1000.000000000000000)

        self.offsetsForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.spb_x_offset)

        self.lbl_offset_y = QLabel(self.grpOffsets)
        self.lbl_offset_y.setObjectName(u"lbl_offset_y")

        self.offsetsForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_offset_y)

        self.spb_y_offset = QDoubleSpinBox(self.grpOffsets)
        self.spb_y_offset.setObjectName(u"spb_y_offset")
        self.spb_y_offset.setDecimals(4)
        self.spb_y_offset.setMinimum(-1000.000000000000000)
        self.spb_y_offset.setMaximum(1000.000000000000000)
        self.spb_y_offset.setValue(0.050000000000000)

        self.offsetsForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.spb_y_offset)


        self.markerLayout.addWidget(self.grpOffsets)


        self.retranslateUi(EditMarkerWidget)

        QMetaObject.connectSlotsByName(EditMarkerWidget)
    # setupUi

    def retranslateUi(self, EditMarkerWidget):
        self.label_lbl.setText(QCoreApplication.translate("EditMarkerWidget", u"Label", None))
        self.position_lbl.setText(QCoreApplication.translate("EditMarkerWidget", u"Position", None))
        self.spb_position.setSuffix(QCoreApplication.translate("EditMarkerWidget", u" \u00b02\u03b8", None))
        self.spb_nanometer.setSuffix(QCoreApplication.translate("EditMarkerWidget", u" nm", None))
#if QT_CONFIG(tooltip)
        self.cmd_sample.setToolTip(QCoreApplication.translate("EditMarkerWidget", u"Select the position directly on the pattern", None))
#endif // QT_CONFIG(tooltip)
        self.cmd_sample.setText(QCoreApplication.translate("EditMarkerWidget", u"Sample", None))
        self.marker_visible.setText(QCoreApplication.translate("EditMarkerWidget", u"Visible", None))
        self.grpAppearance.setTitle(QCoreApplication.translate("EditMarkerWidget", u"Appearance", None))
        self.colour_lbl.setText(QCoreApplication.translate("EditMarkerWidget", u"Colour", None))
        self.marker_color.setText(QCoreApplication.translate("EditMarkerWidget", u"#000000", None))
        self.marker_inherit_color.setText(QCoreApplication.translate("EditMarkerWidget", u"default", None))
        self.line_lbl.setText(QCoreApplication.translate("EditMarkerWidget", u"Line style", None))
        self.marker_style.setItemText(0, QCoreApplication.translate("EditMarkerWidget", u"None", None))
        self.marker_style.setItemText(1, QCoreApplication.translate("EditMarkerWidget", u"Solid", None))
        self.marker_style.setItemText(2, QCoreApplication.translate("EditMarkerWidget", u"Dash", None))
        self.marker_style.setItemText(3, QCoreApplication.translate("EditMarkerWidget", u"Dotted", None))
        self.marker_style.setItemText(4, QCoreApplication.translate("EditMarkerWidget", u"Dash-Dotted", None))
        self.marker_style.setItemText(5, QCoreApplication.translate("EditMarkerWidget", u"Display at Y-offset", None))

        self.marker_inherit_style.setText(QCoreApplication.translate("EditMarkerWidget", u"default", None))
        self.angle_lbl.setText(QCoreApplication.translate("EditMarkerWidget", u"Label Angle", None))
        self.spb_angle.setSuffix(QCoreApplication.translate("EditMarkerWidget", u" \u00b0", None))
        self.marker_inherit_angle.setText(QCoreApplication.translate("EditMarkerWidget", u"default", None))
        self.align_lbl.setText(QCoreApplication.translate("EditMarkerWidget", u"Label alignment", None))
        self.marker_align.setItemText(0, QCoreApplication.translate("EditMarkerWidget", u"Left align", None))
        self.marker_align.setItemText(1, QCoreApplication.translate("EditMarkerWidget", u"Centered", None))
        self.marker_align.setItemText(2, QCoreApplication.translate("EditMarkerWidget", u"Right align", None))

        self.marker_inherit_align.setText(QCoreApplication.translate("EditMarkerWidget", u"default", None))
        self.grpConnector.setTitle(QCoreApplication.translate("EditMarkerWidget", u"Connector line", None))
        self.base_lbl.setText(QCoreApplication.translate("EditMarkerWidget", u"Line base", None))
        self.marker_base.setItemText(0, QCoreApplication.translate("EditMarkerWidget", u"X-axis", None))
        self.marker_base.setItemText(1, QCoreApplication.translate("EditMarkerWidget", u"Experimental profile", None))
        self.marker_base.setItemText(2, QCoreApplication.translate("EditMarkerWidget", u"Calculated profile", None))
        self.marker_base.setItemText(3, QCoreApplication.translate("EditMarkerWidget", u"Lowest of both", None))
        self.marker_base.setItemText(4, QCoreApplication.translate("EditMarkerWidget", u"Highest of both", None))

        self.marker_inherit_base.setText(QCoreApplication.translate("EditMarkerWidget", u"default", None))
        self.top_lbl.setText(QCoreApplication.translate("EditMarkerWidget", u"Line top", None))
        self.marker_top.setItemText(0, QCoreApplication.translate("EditMarkerWidget", u"Relative to base", None))
        self.marker_top.setItemText(1, QCoreApplication.translate("EditMarkerWidget", u"Top of plot", None))

        self.marker_inherit_top.setText(QCoreApplication.translate("EditMarkerWidget", u"default", None))
        self.offset_lbl.setText(QCoreApplication.translate("EditMarkerWidget", u"Offset from base", None))
        self.marker_inherit_top_offset.setText(QCoreApplication.translate("EditMarkerWidget", u"default", None))
        self.grpOffsets.setTitle(QCoreApplication.translate("EditMarkerWidget", u"Label offset", None))
        self.lbl_offset_x.setText(QCoreApplication.translate("EditMarkerWidget", u"X Offset", None))
        self.spb_x_offset.setSuffix(QCoreApplication.translate("EditMarkerWidget", u" \u00b02\u03b8", None))
        self.lbl_offset_y.setText(QCoreApplication.translate("EditMarkerWidget", u"Y Offset", None))
        pass
    # retranslateUi

