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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
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

        self.ucpAContainer = QWidget(EditComponentWidget)
        self.ucpAContainer.setObjectName(u"ucpAContainer")
        self.ucpALayout = QVBoxLayout(self.ucpAContainer)
        self.ucpALayout.setObjectName(u"ucpALayout")
        self.ucpALayout.setContentsMargins(0, 0, 0, 0)

        self.componentForm.setWidget(5, QFormLayout.ItemRole.FieldRole, self.ucpAContainer)

        self.lblCellB = QLabel(EditComponentWidget)
        self.lblCellB.setObjectName(u"lblCellB")

        self.componentForm.setWidget(6, QFormLayout.ItemRole.LabelRole, self.lblCellB)

        self.ucpBContainer = QWidget(EditComponentWidget)
        self.ucpBContainer.setObjectName(u"ucpBContainer")
        self.ucpBLayout = QVBoxLayout(self.ucpBContainer)
        self.ucpBLayout.setObjectName(u"ucpBLayout")
        self.ucpBLayout.setContentsMargins(0, 0, 0, 0)

        self.componentForm.setWidget(6, QFormLayout.ItemRole.FieldRole, self.ucpBContainer)

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

        self.grpLinking = QGroupBox(EditComponentWidget)
        self.grpLinking.setObjectName(u"grpLinking")
        self.linkingLayout = QVBoxLayout(self.grpLinking)
        self.linkingLayout.setObjectName(u"linkingLayout")
        self.linkingForm = QFormLayout()
        self.linkingForm.setObjectName(u"linkingForm")
        self.lblLinkedWith = QLabel(self.grpLinking)
        self.lblLinkedWith.setObjectName(u"lblLinkedWith")

        self.linkingForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblLinkedWith)

        self.component_linked_with = QComboBox(self.grpLinking)
        self.component_linked_with.setObjectName(u"component_linked_with")

        self.linkingForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.component_linked_with)


        self.linkingLayout.addLayout(self.linkingForm)

        self.inheritGrid = QGridLayout()
        self.inheritGrid.setObjectName(u"inheritGrid")
        self.component_inherit_ucp_a = QCheckBox(self.grpLinking)
        self.component_inherit_ucp_a.setObjectName(u"component_inherit_ucp_a")

        self.inheritGrid.addWidget(self.component_inherit_ucp_a, 0, 0, 1, 1)

        self.component_inherit_ucp_b = QCheckBox(self.grpLinking)
        self.component_inherit_ucp_b.setObjectName(u"component_inherit_ucp_b")

        self.inheritGrid.addWidget(self.component_inherit_ucp_b, 0, 1, 1, 1)

        self.component_inherit_default_c = QCheckBox(self.grpLinking)
        self.component_inherit_default_c.setObjectName(u"component_inherit_default_c")

        self.inheritGrid.addWidget(self.component_inherit_default_c, 1, 0, 1, 1)

        self.component_inherit_delta_c = QCheckBox(self.grpLinking)
        self.component_inherit_delta_c.setObjectName(u"component_inherit_delta_c")

        self.inheritGrid.addWidget(self.component_inherit_delta_c, 1, 1, 1, 1)

        self.component_inherit_layer_atoms = QCheckBox(self.grpLinking)
        self.component_inherit_layer_atoms.setObjectName(u"component_inherit_layer_atoms")

        self.inheritGrid.addWidget(self.component_inherit_layer_atoms, 2, 0, 1, 1)

        self.component_inherit_interlayer_atoms = QCheckBox(self.grpLinking)
        self.component_inherit_interlayer_atoms.setObjectName(u"component_inherit_interlayer_atoms")

        self.inheritGrid.addWidget(self.component_inherit_interlayer_atoms, 2, 1, 1, 1)

        self.component_inherit_d001 = QCheckBox(self.grpLinking)
        self.component_inherit_d001.setObjectName(u"component_inherit_d001")

        self.inheritGrid.addWidget(self.component_inherit_d001, 3, 0, 1, 1)

        self.component_inherit_atom_relations = QCheckBox(self.grpLinking)
        self.component_inherit_atom_relations.setObjectName(u"component_inherit_atom_relations")

        self.inheritGrid.addWidget(self.component_inherit_atom_relations, 3, 1, 1, 1)


        self.linkingLayout.addLayout(self.inheritGrid)


        self.componentRootLayout.addWidget(self.grpLinking)

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

        self.grpRelations = QGroupBox(EditComponentWidget)
        self.grpRelations.setObjectName(u"grpRelations")
        self.relationsRootLayout = QVBoxLayout(self.grpRelations)
        self.relationsRootLayout.setObjectName(u"relationsRootLayout")
        self.relationsBar = QHBoxLayout()
        self.relationsBar.setObjectName(u"relationsBar")
        self.cmb_relation = QComboBox(self.grpRelations)
        self.cmb_relation.setObjectName(u"cmb_relation")

        self.relationsBar.addWidget(self.cmb_relation)

        self.btn_add_ratio = QPushButton(self.grpRelations)
        self.btn_add_ratio.setObjectName(u"btn_add_ratio")

        self.relationsBar.addWidget(self.btn_add_ratio)

        self.btn_add_contents = QPushButton(self.grpRelations)
        self.btn_add_contents.setObjectName(u"btn_add_contents")

        self.relationsBar.addWidget(self.btn_add_contents)

        self.btn_del_relation = QPushButton(self.grpRelations)
        self.btn_del_relation.setObjectName(u"btn_del_relation")

        self.relationsBar.addWidget(self.btn_del_relation)


        self.relationsRootLayout.addLayout(self.relationsBar)

        self.ratioLayout = QVBoxLayout()
        self.ratioLayout.setObjectName(u"ratioLayout")

        self.relationsRootLayout.addLayout(self.ratioLayout)

        self.lblRelationInfo = QLabel(self.grpRelations)
        self.lblRelationInfo.setObjectName(u"lblRelationInfo")
        self.lblRelationInfo.setEnabled(False)
        self.lblRelationInfo.setWordWrap(True)

        self.relationsRootLayout.addWidget(self.lblRelationInfo)


        self.componentRootLayout.addWidget(self.grpRelations)


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
        self.lblCellB.setText(QCoreApplication.translate("EditComponentWidget", u"Cell length b [nm]", None))
        self.lblVolume.setText(QCoreApplication.translate("EditComponentWidget", u"Cell volume [nm\u00b3]", None))
        self.component_volume.setText(QCoreApplication.translate("EditComponentWidget", u"-", None))
        self.lblCharge.setText(QCoreApplication.translate("EditComponentWidget", u"Charge balance", None))
        self.component_charge.setText(QCoreApplication.translate("EditComponentWidget", u"-", None))
        self.grpLinking.setTitle(QCoreApplication.translate("EditComponentWidget", u"Component linking (inherit from linked layer)", None))
        self.lblLinkedWith.setText(QCoreApplication.translate("EditComponentWidget", u"Linked with", None))
#if QT_CONFIG(tooltip)
        self.component_linked_with.setToolTip(QCoreApplication.translate("EditComponentWidget", u"The template component this layer inherits from (a shared clay layer). Creating/changing links needs phase \"based on\", ported later.", None))
#endif // QT_CONFIG(tooltip)
        self.component_inherit_ucp_a.setText(QCoreApplication.translate("EditComponentWidget", u"Cell a", None))
        self.component_inherit_ucp_b.setText(QCoreApplication.translate("EditComponentWidget", u"Cell b", None))
        self.component_inherit_default_c.setText(QCoreApplication.translate("EditComponentWidget", u"Cell c / default c", None))
        self.component_inherit_delta_c.setText(QCoreApplication.translate("EditComponentWidget", u"\u0394c spacing", None))
        self.component_inherit_layer_atoms.setText(QCoreApplication.translate("EditComponentWidget", u"Layer atoms", None))
        self.component_inherit_interlayer_atoms.setText(QCoreApplication.translate("EditComponentWidget", u"Interlayer atoms", None))
#if QT_CONFIG(tooltip)
        self.component_inherit_d001.setToolTip(QCoreApplication.translate("EditComponentWidget", u"In the model, d001 inheritance follows \"Cell c / default c\" (old-app behaviour); shown for reference.", None))
#endif // QT_CONFIG(tooltip)
        self.component_inherit_d001.setText(QCoreApplication.translate("EditComponentWidget", u"d001 (follows cell c)", None))
#if QT_CONFIG(tooltip)
        self.component_inherit_atom_relations.setToolTip(QCoreApplication.translate("EditComponentWidget", u"Enabled once the atom-relations editor is ported.", None))
#endif // QT_CONFIG(tooltip)
        self.component_inherit_atom_relations.setText(QCoreApplication.translate("EditComponentWidget", u"Atom relations", None))
        self.grpLayerAtoms.setTitle(QCoreApplication.translate("EditComponentWidget", u"Layer atoms", None))
        self.grpInterlayerAtoms.setTitle(QCoreApplication.translate("EditComponentWidget", u"Interlayer atoms", None))
        self.grpRelations.setTitle(QCoreApplication.translate("EditComponentWidget", u"Atom relations", None))
#if QT_CONFIG(tooltip)
        self.cmb_relation.setToolTip(QCoreApplication.translate("EditComponentWidget", u"The atom relations of this component (ratios drive atom occupancies).", None))
#endif // QT_CONFIG(tooltip)
        self.btn_add_ratio.setText(QCoreApplication.translate("EditComponentWidget", u"Add ratio", None))
        self.btn_add_contents.setText(QCoreApplication.translate("EditComponentWidget", u"Add contents", None))
        self.btn_del_relation.setText(QCoreApplication.translate("EditComponentWidget", u"Remove", None))
        self.lblRelationInfo.setText("")
        pass
    # retranslateUi

