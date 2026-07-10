# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_component.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_EditComponentWidget(object):
    def setupUi(self, EditComponentWidget):
        if not EditComponentWidget.objectName():
            EditComponentWidget.setObjectName(u"EditComponentWidget")
        self.componentRootLayout = QVBoxLayout(EditComponentWidget)
        self.componentRootLayout.setObjectName(u"componentRootLayout")
        self.componentForm = QFormLayout()
        self.componentForm.setObjectName(u"componentForm")
        self.lblComponent = QLabel(EditComponentWidget)
        self.lblComponent.setObjectName(u"lblComponent")

        self.componentForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblComponent)

        self.cmb_component = QComboBox(EditComponentWidget)
        self.cmb_component.setObjectName(u"cmb_component")

        self.componentForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.cmb_component)

        self.lblComponentName = QLabel(EditComponentWidget)
        self.lblComponentName.setObjectName(u"lblComponentName")

        self.componentForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblComponentName)

        self.component_name = QLineEdit(EditComponentWidget)
        self.component_name.setObjectName(u"component_name")

        self.componentForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.component_name)

        self.lblD001 = QLabel(EditComponentWidget)
        self.lblD001.setObjectName(u"lblD001")

        self.componentForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblD001)

        self.component_d001 = QDoubleSpinBox(EditComponentWidget)
        self.component_d001.setObjectName(u"component_d001")
        self.component_d001.setDecimals(4)
        self.component_d001.setMaximum(5.000000000000000)
        self.component_d001.setSingleStep(0.001000000000000)

        self.componentForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.component_d001)

        self.lblDefaultC = QLabel(EditComponentWidget)
        self.lblDefaultC.setObjectName(u"lblDefaultC")

        self.componentForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblDefaultC)

        self.component_default_c = QDoubleSpinBox(EditComponentWidget)
        self.component_default_c.setObjectName(u"component_default_c")
        self.component_default_c.setDecimals(4)
        self.component_default_c.setMaximum(5.000000000000000)
        self.component_default_c.setSingleStep(0.001000000000000)

        self.componentForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.component_default_c)

        self.lblDeltaC = QLabel(EditComponentWidget)
        self.lblDeltaC.setObjectName(u"lblDeltaC")

        self.componentForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lblDeltaC)

        self.component_delta_c = QDoubleSpinBox(EditComponentWidget)
        self.component_delta_c.setObjectName(u"component_delta_c")
        self.component_delta_c.setDecimals(4)
        self.component_delta_c.setMaximum(0.050000000000000)
        self.component_delta_c.setSingleStep(0.001000000000000)

        self.componentForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.component_delta_c)

        self.lblCellA = QLabel(EditComponentWidget)
        self.lblCellA.setObjectName(u"lblCellA")

        self.componentForm.setWidget(5, QFormLayout.ItemRole.LabelRole, self.lblCellA)

        self.component_cell_a = QLabel(EditComponentWidget)
        self.component_cell_a.setObjectName(u"component_cell_a")

        self.componentForm.setWidget(5, QFormLayout.ItemRole.FieldRole, self.component_cell_a)

        self.lblCellB = QLabel(EditComponentWidget)
        self.lblCellB.setObjectName(u"lblCellB")

        self.componentForm.setWidget(6, QFormLayout.ItemRole.LabelRole, self.lblCellB)

        self.component_cell_b = QLabel(EditComponentWidget)
        self.component_cell_b.setObjectName(u"component_cell_b")

        self.componentForm.setWidget(6, QFormLayout.ItemRole.FieldRole, self.component_cell_b)

        self.lblVolume = QLabel(EditComponentWidget)
        self.lblVolume.setObjectName(u"lblVolume")

        self.componentForm.setWidget(7, QFormLayout.ItemRole.LabelRole, self.lblVolume)

        self.component_volume = QLabel(EditComponentWidget)
        self.component_volume.setObjectName(u"component_volume")

        self.componentForm.setWidget(7, QFormLayout.ItemRole.FieldRole, self.component_volume)

        self.lblCharge = QLabel(EditComponentWidget)
        self.lblCharge.setObjectName(u"lblCharge")

        self.componentForm.setWidget(8, QFormLayout.ItemRole.LabelRole, self.lblCharge)

        self.component_charge = QLabel(EditComponentWidget)
        self.component_charge.setObjectName(u"component_charge")

        self.componentForm.setWidget(8, QFormLayout.ItemRole.FieldRole, self.component_charge)


        self.componentRootLayout.addLayout(self.componentForm)

        self.grpLayerAtoms = QGroupBox(EditComponentWidget)
        self.grpLayerAtoms.setObjectName(u"grpLayerAtoms")
        self.layerAtomsLayout = QVBoxLayout(self.grpLayerAtoms)
        self.layerAtomsLayout.setObjectName(u"layerAtomsLayout")

        self.componentRootLayout.addWidget(self.grpLayerAtoms)

        self.grpInterlayerAtoms = QGroupBox(EditComponentWidget)
        self.grpInterlayerAtoms.setObjectName(u"grpInterlayerAtoms")
        self.interlayerAtomsLayout = QVBoxLayout(self.grpInterlayerAtoms)
        self.interlayerAtomsLayout.setObjectName(u"interlayerAtomsLayout")

        self.componentRootLayout.addWidget(self.grpInterlayerAtoms)


        self.retranslateUi(EditComponentWidget)

        QMetaObject.connectSlotsByName(EditComponentWidget)
    # setupUi

    def retranslateUi(self, EditComponentWidget):
        self.lblComponent.setText(QCoreApplication.translate("EditComponentWidget", u"Component", None))
        self.lblComponentName.setText(QCoreApplication.translate("EditComponentWidget", u"Name", None))
        self.lblD001.setText(QCoreApplication.translate("EditComponentWidget", u"Cell length c / d001 [nm]", None))
#if QT_CONFIG(tooltip)
        self.component_d001.setToolTip(QCoreApplication.translate("EditComponentWidget", u"The basal spacing (d001) of this layer.", None))
#endif // QT_CONFIG(tooltip)
        self.lblDefaultC.setText(QCoreApplication.translate("EditComponentWidget", u"Default length c [nm]", None))
#if QT_CONFIG(tooltip)
        self.component_default_c.setToolTip(QCoreApplication.translate("EditComponentWidget", u"The default basal spacing (used to rescale interlayer atom z-coordinates).", None))
#endif // QT_CONFIG(tooltip)
        self.lblDeltaC.setText(QCoreApplication.translate("EditComponentWidget", u"\u0394c spacing [nm]", None))
#if QT_CONFIG(tooltip)
        self.component_delta_c.setToolTip(QCoreApplication.translate("EditComponentWidget", u"The variation in basal spacing due to defects.", None))
#endif // QT_CONFIG(tooltip)
        self.lblCellA.setText(QCoreApplication.translate("EditComponentWidget", u"Cell length a [nm]", None))
        self.component_cell_a.setText(QCoreApplication.translate("EditComponentWidget", u"-", None))
        self.lblCellB.setText(QCoreApplication.translate("EditComponentWidget", u"Cell length b [nm]", None))
        self.component_cell_b.setText(QCoreApplication.translate("EditComponentWidget", u"-", None))
        self.lblVolume.setText(QCoreApplication.translate("EditComponentWidget", u"Cell volume [nm\u00b3]", None))
        self.component_volume.setText(QCoreApplication.translate("EditComponentWidget", u"-", None))
        self.lblCharge.setText(QCoreApplication.translate("EditComponentWidget", u"Charge balance", None))
        self.component_charge.setText(QCoreApplication.translate("EditComponentWidget", u"-", None))
        self.grpLayerAtoms.setTitle(QCoreApplication.translate("EditComponentWidget", u"Layer atoms", None))
        self.grpInterlayerAtoms.setTitle(QCoreApplication.translate("EditComponentWidget", u"Interlayer atoms", None))
        pass
    # retranslateUi

