# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_atom_type.ui'
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
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QFormLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QSizePolicy,
    QSpinBox, QVBoxLayout, QWidget)

class Ui_EditAtomTypeWidget(object):
    def setupUi(self, EditAtomTypeWidget):
        if not EditAtomTypeWidget.objectName():
            EditAtomTypeWidget.setObjectName(u"EditAtomTypeWidget")
        self.atomTypeLayout = QVBoxLayout(EditAtomTypeWidget)
        self.atomTypeLayout.setObjectName(u"atomTypeLayout")
        self.atomForm = QFormLayout()
        self.atomForm.setObjectName(u"atomForm")
        self.lblAtomName = QLabel(EditAtomTypeWidget)
        self.lblAtomName.setObjectName(u"lblAtomName")

        self.atomForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblAtomName)

        self.atom_name = QLineEdit(EditAtomTypeWidget)
        self.atom_name.setObjectName(u"atom_name")

        self.atomForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.atom_name)

        self.lblAtomNr = QLabel(EditAtomTypeWidget)
        self.lblAtomNr.setObjectName(u"lblAtomNr")

        self.atomForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblAtomNr)

        self.atom_atom_nr = QSpinBox(EditAtomTypeWidget)
        self.atom_atom_nr.setObjectName(u"atom_atom_nr")
        self.atom_atom_nr.setMaximum(118)

        self.atomForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.atom_atom_nr)

        self.lblAtomWeight = QLabel(EditAtomTypeWidget)
        self.lblAtomWeight.setObjectName(u"lblAtomWeight")

        self.atomForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblAtomWeight)

        self.atom_weight = QDoubleSpinBox(EditAtomTypeWidget)
        self.atom_weight.setObjectName(u"atom_weight")
        self.atom_weight.setDecimals(4)
        self.atom_weight.setMaximum(500.000000000000000)

        self.atomForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.atom_weight)

        self.lblAtomDebye = QLabel(EditAtomTypeWidget)
        self.lblAtomDebye.setObjectName(u"lblAtomDebye")

        self.atomForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblAtomDebye)

        self.atom_debye = QDoubleSpinBox(EditAtomTypeWidget)
        self.atom_debye.setObjectName(u"atom_debye")
        self.atom_debye.setDecimals(4)
        self.atom_debye.setMinimum(-100.000000000000000)
        self.atom_debye.setMaximum(100.000000000000000)

        self.atomForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.atom_debye)

        self.lblAtomCharge = QLabel(EditAtomTypeWidget)
        self.lblAtomCharge.setObjectName(u"lblAtomCharge")

        self.atomForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lblAtomCharge)

        self.atom_charge = QDoubleSpinBox(EditAtomTypeWidget)
        self.atom_charge.setObjectName(u"atom_charge")
        self.atom_charge.setDecimals(2)
        self.atom_charge.setMinimum(-10.000000000000000)
        self.atom_charge.setMaximum(10.000000000000000)

        self.atomForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.atom_charge)


        self.atomTypeLayout.addLayout(self.atomForm)

        self.frm_atom_type_asfs = QGroupBox(EditAtomTypeWidget)
        self.frm_atom_type_asfs.setObjectName(u"frm_atom_type_asfs")
        self.parametersGrid = QGridLayout(self.frm_atom_type_asfs)
        self.parametersGrid.setObjectName(u"parametersGrid")
        self.lbl_a1 = QLabel(self.frm_atom_type_asfs)
        self.lbl_a1.setObjectName(u"lbl_a1")
        self.lbl_a1.setAlignment(Qt.AlignCenter)

        self.parametersGrid.addWidget(self.lbl_a1, 0, 0, 1, 1)

        self.lbl_a2 = QLabel(self.frm_atom_type_asfs)
        self.lbl_a2.setObjectName(u"lbl_a2")
        self.lbl_a2.setAlignment(Qt.AlignCenter)

        self.parametersGrid.addWidget(self.lbl_a2, 0, 1, 1, 1)

        self.lbl_a3 = QLabel(self.frm_atom_type_asfs)
        self.lbl_a3.setObjectName(u"lbl_a3")
        self.lbl_a3.setAlignment(Qt.AlignCenter)

        self.parametersGrid.addWidget(self.lbl_a3, 0, 2, 1, 1)

        self.lbl_a4 = QLabel(self.frm_atom_type_asfs)
        self.lbl_a4.setObjectName(u"lbl_a4")
        self.lbl_a4.setAlignment(Qt.AlignCenter)

        self.parametersGrid.addWidget(self.lbl_a4, 0, 3, 1, 1)

        self.lbl_a5 = QLabel(self.frm_atom_type_asfs)
        self.lbl_a5.setObjectName(u"lbl_a5")
        self.lbl_a5.setAlignment(Qt.AlignCenter)

        self.parametersGrid.addWidget(self.lbl_a5, 0, 4, 1, 1)

        self.atom_par_a1 = QDoubleSpinBox(self.frm_atom_type_asfs)
        self.atom_par_a1.setObjectName(u"atom_par_a1")
        self.atom_par_a1.setDecimals(4)
        self.atom_par_a1.setMinimum(-1000.000000000000000)
        self.atom_par_a1.setMaximum(1000.000000000000000)

        self.parametersGrid.addWidget(self.atom_par_a1, 1, 0, 1, 1)

        self.atom_par_a2 = QDoubleSpinBox(self.frm_atom_type_asfs)
        self.atom_par_a2.setObjectName(u"atom_par_a2")
        self.atom_par_a2.setDecimals(4)
        self.atom_par_a2.setMinimum(-1000.000000000000000)
        self.atom_par_a2.setMaximum(1000.000000000000000)

        self.parametersGrid.addWidget(self.atom_par_a2, 1, 1, 1, 1)

        self.atom_par_a3 = QDoubleSpinBox(self.frm_atom_type_asfs)
        self.atom_par_a3.setObjectName(u"atom_par_a3")
        self.atom_par_a3.setDecimals(4)
        self.atom_par_a3.setMinimum(-1000.000000000000000)
        self.atom_par_a3.setMaximum(1000.000000000000000)

        self.parametersGrid.addWidget(self.atom_par_a3, 1, 2, 1, 1)

        self.atom_par_a4 = QDoubleSpinBox(self.frm_atom_type_asfs)
        self.atom_par_a4.setObjectName(u"atom_par_a4")
        self.atom_par_a4.setDecimals(4)
        self.atom_par_a4.setMinimum(-1000.000000000000000)
        self.atom_par_a4.setMaximum(1000.000000000000000)

        self.parametersGrid.addWidget(self.atom_par_a4, 1, 3, 1, 1)

        self.atom_par_a5 = QDoubleSpinBox(self.frm_atom_type_asfs)
        self.atom_par_a5.setObjectName(u"atom_par_a5")
        self.atom_par_a5.setDecimals(4)
        self.atom_par_a5.setMinimum(-1000.000000000000000)
        self.atom_par_a5.setMaximum(1000.000000000000000)

        self.parametersGrid.addWidget(self.atom_par_a5, 1, 4, 1, 1)

        self.lbl_b1 = QLabel(self.frm_atom_type_asfs)
        self.lbl_b1.setObjectName(u"lbl_b1")
        self.lbl_b1.setAlignment(Qt.AlignCenter)

        self.parametersGrid.addWidget(self.lbl_b1, 2, 0, 1, 1)

        self.lbl_b2 = QLabel(self.frm_atom_type_asfs)
        self.lbl_b2.setObjectName(u"lbl_b2")
        self.lbl_b2.setAlignment(Qt.AlignCenter)

        self.parametersGrid.addWidget(self.lbl_b2, 2, 1, 1, 1)

        self.lbl_b3 = QLabel(self.frm_atom_type_asfs)
        self.lbl_b3.setObjectName(u"lbl_b3")
        self.lbl_b3.setAlignment(Qt.AlignCenter)

        self.parametersGrid.addWidget(self.lbl_b3, 2, 2, 1, 1)

        self.lbl_b4 = QLabel(self.frm_atom_type_asfs)
        self.lbl_b4.setObjectName(u"lbl_b4")
        self.lbl_b4.setAlignment(Qt.AlignCenter)

        self.parametersGrid.addWidget(self.lbl_b4, 2, 3, 1, 1)

        self.lbl_b5 = QLabel(self.frm_atom_type_asfs)
        self.lbl_b5.setObjectName(u"lbl_b5")
        self.lbl_b5.setAlignment(Qt.AlignCenter)

        self.parametersGrid.addWidget(self.lbl_b5, 2, 4, 1, 1)

        self.atom_par_b1 = QDoubleSpinBox(self.frm_atom_type_asfs)
        self.atom_par_b1.setObjectName(u"atom_par_b1")
        self.atom_par_b1.setDecimals(4)
        self.atom_par_b1.setMinimum(-1000.000000000000000)
        self.atom_par_b1.setMaximum(1000.000000000000000)

        self.parametersGrid.addWidget(self.atom_par_b1, 3, 0, 1, 1)

        self.atom_par_b2 = QDoubleSpinBox(self.frm_atom_type_asfs)
        self.atom_par_b2.setObjectName(u"atom_par_b2")
        self.atom_par_b2.setDecimals(4)
        self.atom_par_b2.setMinimum(-1000.000000000000000)
        self.atom_par_b2.setMaximum(1000.000000000000000)

        self.parametersGrid.addWidget(self.atom_par_b2, 3, 1, 1, 1)

        self.atom_par_b3 = QDoubleSpinBox(self.frm_atom_type_asfs)
        self.atom_par_b3.setObjectName(u"atom_par_b3")
        self.atom_par_b3.setDecimals(4)
        self.atom_par_b3.setMinimum(-1000.000000000000000)
        self.atom_par_b3.setMaximum(1000.000000000000000)

        self.parametersGrid.addWidget(self.atom_par_b3, 3, 2, 1, 1)

        self.atom_par_b4 = QDoubleSpinBox(self.frm_atom_type_asfs)
        self.atom_par_b4.setObjectName(u"atom_par_b4")
        self.atom_par_b4.setDecimals(4)
        self.atom_par_b4.setMinimum(-1000.000000000000000)
        self.atom_par_b4.setMaximum(1000.000000000000000)

        self.parametersGrid.addWidget(self.atom_par_b4, 3, 3, 1, 1)

        self.atom_par_b5 = QDoubleSpinBox(self.frm_atom_type_asfs)
        self.atom_par_b5.setObjectName(u"atom_par_b5")
        self.atom_par_b5.setDecimals(4)
        self.atom_par_b5.setMinimum(-1000.000000000000000)
        self.atom_par_b5.setMaximum(1000.000000000000000)

        self.parametersGrid.addWidget(self.atom_par_b5, 3, 4, 1, 1)

        self.lbl_c = QLabel(self.frm_atom_type_asfs)
        self.lbl_c.setObjectName(u"lbl_c")
        self.lbl_c.setAlignment(Qt.AlignCenter)

        self.parametersGrid.addWidget(self.lbl_c, 4, 0, 1, 1)

        self.atom_par_c = QDoubleSpinBox(self.frm_atom_type_asfs)
        self.atom_par_c.setObjectName(u"atom_par_c")
        self.atom_par_c.setDecimals(4)
        self.atom_par_c.setMinimum(-1000.000000000000000)
        self.atom_par_c.setMaximum(1000.000000000000000)

        self.parametersGrid.addWidget(self.atom_par_c, 5, 0, 1, 1)


        self.atomTypeLayout.addWidget(self.frm_atom_type_asfs)

        self.grpScattering = QGroupBox(EditAtomTypeWidget)
        self.grpScattering.setObjectName(u"grpScattering")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.grpScattering.sizePolicy().hasHeightForWidth())
        self.grpScattering.setSizePolicy(sizePolicy)
        self.scatteringLayout = QVBoxLayout(self.grpScattering)
        self.scatteringLayout.setObjectName(u"scatteringLayout")

        self.atomTypeLayout.addWidget(self.grpScattering)


        self.retranslateUi(EditAtomTypeWidget)

        QMetaObject.connectSlotsByName(EditAtomTypeWidget)
    # setupUi

    def retranslateUi(self, EditAtomTypeWidget):
        self.lblAtomName.setText(QCoreApplication.translate("EditAtomTypeWidget", u"Name", None))
        self.lblAtomNr.setText(QCoreApplication.translate("EditAtomTypeWidget", u"Atom nr", None))
        self.lblAtomWeight.setText(QCoreApplication.translate("EditAtomTypeWidget", u"Atomic weight", None))
        self.lblAtomDebye.setText(QCoreApplication.translate("EditAtomTypeWidget", u"Debye-Waller factor", None))
        self.lblAtomCharge.setText(QCoreApplication.translate("EditAtomTypeWidget", u"Charge", None))
        self.frm_atom_type_asfs.setTitle(QCoreApplication.translate("EditAtomTypeWidget", u"Parameters", None))
        self.lbl_a1.setText(QCoreApplication.translate("EditAtomTypeWidget", u"a\u2081", None))
        self.lbl_a2.setText(QCoreApplication.translate("EditAtomTypeWidget", u"a\u2082", None))
        self.lbl_a3.setText(QCoreApplication.translate("EditAtomTypeWidget", u"a\u2083", None))
        self.lbl_a4.setText(QCoreApplication.translate("EditAtomTypeWidget", u"a\u2084", None))
        self.lbl_a5.setText(QCoreApplication.translate("EditAtomTypeWidget", u"a\u2085", None))
        self.lbl_b1.setText(QCoreApplication.translate("EditAtomTypeWidget", u"b\u2081", None))
        self.lbl_b2.setText(QCoreApplication.translate("EditAtomTypeWidget", u"b\u2082", None))
        self.lbl_b3.setText(QCoreApplication.translate("EditAtomTypeWidget", u"b\u2083", None))
        self.lbl_b4.setText(QCoreApplication.translate("EditAtomTypeWidget", u"b\u2084", None))
        self.lbl_b5.setText(QCoreApplication.translate("EditAtomTypeWidget", u"b\u2085", None))
        self.lbl_c.setText(QCoreApplication.translate("EditAtomTypeWidget", u"c", None))
        self.grpScattering.setTitle(QCoreApplication.translate("EditAtomTypeWidget", u"Scattering factor", None))
        pass
    # retranslateUi

