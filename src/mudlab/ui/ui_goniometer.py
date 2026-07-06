# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'goniometer.ui'
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
    QPushButton, QSizePolicy, QSpacerItem, QSpinBox,
    QVBoxLayout, QWidget)

class Ui_GoniometerWidget(object):
    def setupUi(self, GoniometerWidget):
        if not GoniometerWidget.objectName():
            GoniometerWidget.setObjectName(u"GoniometerWidget")
        self.goniometerWidgetLayout = QVBoxLayout(GoniometerWidget)
        self.goniometerWidgetLayout.setObjectName(u"goniometerWidgetLayout")
        self.columnsLayout = QHBoxLayout()
        self.columnsLayout.setObjectName(u"columnsLayout")
        self.leftColumn = QVBoxLayout()
        self.leftColumn.setObjectName(u"leftColumn")
        self.grpGeneral = QGroupBox(GoniometerWidget)
        self.grpGeneral.setObjectName(u"grpGeneral")
        self.generalForm = QFormLayout(self.grpGeneral)
        self.generalForm.setObjectName(u"generalForm")
        self.gonio_radius_lbl = QLabel(self.grpGeneral)
        self.gonio_radius_lbl.setObjectName(u"gonio_radius_lbl")

        self.generalForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.gonio_radius_lbl)

        self.gonio_radius_spb = QDoubleSpinBox(self.grpGeneral)
        self.gonio_radius_spb.setObjectName(u"gonio_radius_spb")
        self.gonio_radius_spb.setDecimals(2)
        self.gonio_radius_spb.setMaximum(200.000000000000000)
        self.gonio_radius_spb.setValue(24.000000000000000)

        self.generalForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.gonio_radius_spb)

        self.gonio_min_2theta_lbl = QLabel(self.grpGeneral)
        self.gonio_min_2theta_lbl.setObjectName(u"gonio_min_2theta_lbl")

        self.generalForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.gonio_min_2theta_lbl)

        self.gonio_min_2theta_spb = QDoubleSpinBox(self.grpGeneral)
        self.gonio_min_2theta_spb.setObjectName(u"gonio_min_2theta_spb")
        self.gonio_min_2theta_spb.setDecimals(2)
        self.gonio_min_2theta_spb.setMaximum(180.000000000000000)
        self.gonio_min_2theta_spb.setValue(3.000000000000000)

        self.generalForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.gonio_min_2theta_spb)

        self.gonio_max_2theta_lbl = QLabel(self.grpGeneral)
        self.gonio_max_2theta_lbl.setObjectName(u"gonio_max_2theta_lbl")

        self.generalForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.gonio_max_2theta_lbl)

        self.gonio_max_2theta_spb = QDoubleSpinBox(self.grpGeneral)
        self.gonio_max_2theta_spb.setObjectName(u"gonio_max_2theta_spb")
        self.gonio_max_2theta_spb.setDecimals(2)
        self.gonio_max_2theta_spb.setMaximum(180.000000000000000)
        self.gonio_max_2theta_spb.setValue(50.000000000000000)

        self.generalForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.gonio_max_2theta_spb)

        self.lbl_steps_gonio1 = QLabel(self.grpGeneral)
        self.lbl_steps_gonio1.setObjectName(u"lbl_steps_gonio1")

        self.generalForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lbl_steps_gonio1)

        self.steps_spn_btn1 = QSpinBox(self.grpGeneral)
        self.steps_spn_btn1.setObjectName(u"steps_spn_btn1")
        self.steps_spn_btn1.setMaximum(10000)
        self.steps_spn_btn1.setValue(2500)

        self.generalForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.steps_spn_btn1)


        self.leftColumn.addWidget(self.grpGeneral)

        self.grpSample = QGroupBox(GoniometerWidget)
        self.grpSample.setObjectName(u"grpSample")
        self.sampleForm = QFormLayout(self.grpSample)
        self.sampleForm.setObjectName(u"sampleForm")
        self.spec_length_lbl = QLabel(self.grpSample)
        self.spec_length_lbl.setObjectName(u"spec_length_lbl")

        self.sampleForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.spec_length_lbl)

        self.sample_length_spb = QDoubleSpinBox(self.grpSample)
        self.sample_length_spb.setObjectName(u"sample_length_spb")
        self.sample_length_spb.setDecimals(2)
        self.sample_length_spb.setMaximum(100.000000000000000)
        self.sample_length_spb.setValue(1.250000000000000)

        self.sampleForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.sample_length_spb)

        self.absorption_lbl3 = QLabel(self.grpSample)
        self.absorption_lbl3.setObjectName(u"absorption_lbl3")

        self.sampleForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.absorption_lbl3)

        self.sample_surf_density_spb = QDoubleSpinBox(self.grpSample)
        self.sample_surf_density_spb.setObjectName(u"sample_surf_density_spb")
        self.sample_surf_density_spb.setDecimals(2)
        self.sample_surf_density_spb.setMaximum(10000.000000000000000)
        self.sample_surf_density_spb.setValue(20.000000000000000)

        self.sampleForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.sample_surf_density_spb)

        self.gonio_has_absorption_correction = QCheckBox(self.grpSample)
        self.gonio_has_absorption_correction.setObjectName(u"gonio_has_absorption_correction")

        self.sampleForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.gonio_has_absorption_correction)

        self.absorption_lbl = QLabel(self.grpSample)
        self.absorption_lbl.setObjectName(u"absorption_lbl")

        self.sampleForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.absorption_lbl)

        self.absorption_spb = QDoubleSpinBox(self.grpSample)
        self.absorption_spb.setObjectName(u"absorption_spb")
        self.absorption_spb.setEnabled(False)
        self.absorption_spb.setDecimals(2)
        self.absorption_spb.setMaximum(10000.000000000000000)
        self.absorption_spb.setValue(45.000000000000000)

        self.sampleForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.absorption_spb)


        self.leftColumn.addWidget(self.grpSample)

        self.leftSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.leftColumn.addItem(self.leftSpacer)


        self.columnsLayout.addLayout(self.leftColumn)

        self.rightColumn = QVBoxLayout()
        self.rightColumn.setObjectName(u"rightColumn")
        self.grpPrimary = QGroupBox(GoniometerWidget)
        self.grpPrimary.setObjectName(u"grpPrimary")
        self.primaryForm = QFormLayout(self.grpPrimary)
        self.primaryForm.setObjectName(u"primaryForm")
        self.gonio_lambda_lbl = QLabel(self.grpPrimary)
        self.gonio_lambda_lbl.setObjectName(u"gonio_lambda_lbl")

        self.primaryForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.gonio_lambda_lbl)

        self.btn_edit_wld = QPushButton(self.grpPrimary)
        self.btn_edit_wld.setObjectName(u"btn_edit_wld")

        self.primaryForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.btn_edit_wld)

        self.gonio_divergence_lbl = QLabel(self.grpPrimary)
        self.gonio_divergence_lbl.setObjectName(u"gonio_divergence_lbl")

        self.primaryForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.gonio_divergence_lbl)

        self.gonio_divergence_mode = QComboBox(self.grpPrimary)
        self.gonio_divergence_mode.addItem("")
        self.gonio_divergence_mode.addItem("")
        self.gonio_divergence_mode.setObjectName(u"gonio_divergence_mode")

        self.primaryForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.gonio_divergence_mode)

        self.gonio_div_val_lbl = QLabel(self.grpPrimary)
        self.gonio_div_val_lbl.setObjectName(u"gonio_div_val_lbl")

        self.primaryForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.gonio_div_val_lbl)

        self.gonio_div_value_spb = QDoubleSpinBox(self.grpPrimary)
        self.gonio_div_value_spb.setObjectName(u"gonio_div_value_spb")
        self.gonio_div_value_spb.setDecimals(2)
        self.gonio_div_value_spb.setMaximum(90.000000000000000)
        self.gonio_div_value_spb.setValue(0.500000000000000)

        self.primaryForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.gonio_div_value_spb)

        self.gonio_has_soller1 = QCheckBox(self.grpPrimary)
        self.gonio_has_soller1.setObjectName(u"gonio_has_soller1")
        self.gonio_has_soller1.setChecked(True)

        self.primaryForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.gonio_has_soller1)

        self.gonio_soller1_spb = QDoubleSpinBox(self.grpPrimary)
        self.gonio_soller1_spb.setObjectName(u"gonio_soller1_spb")
        self.gonio_soller1_spb.setDecimals(2)
        self.gonio_soller1_spb.setMaximum(10.000000000000000)
        self.gonio_soller1_spb.setValue(2.300000000000000)

        self.primaryForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.gonio_soller1_spb)


        self.rightColumn.addWidget(self.grpPrimary)

        self.grpSecondary = QGroupBox(GoniometerWidget)
        self.grpSecondary.setObjectName(u"grpSecondary")
        self.secondaryForm = QFormLayout(self.grpSecondary)
        self.secondaryForm.setObjectName(u"secondaryForm")
        self.gonio_has_soller2 = QCheckBox(self.grpSecondary)
        self.gonio_has_soller2.setObjectName(u"gonio_has_soller2")
        self.gonio_has_soller2.setChecked(True)

        self.secondaryForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.gonio_has_soller2)

        self.gonio_soller2_spb = QDoubleSpinBox(self.grpSecondary)
        self.gonio_soller2_spb.setObjectName(u"gonio_soller2_spb")
        self.gonio_soller2_spb.setDecimals(2)
        self.gonio_soller2_spb.setMaximum(10.000000000000000)
        self.gonio_soller2_spb.setValue(2.300000000000000)

        self.secondaryForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.gonio_soller2_spb)

        self.gonio_mcr_2theta_lbl6 = QLabel(self.grpSecondary)
        self.gonio_mcr_2theta_lbl6.setObjectName(u"gonio_mcr_2theta_lbl6")

        self.secondaryForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.gonio_mcr_2theta_lbl6)

        self.gonio_mcr2t_spb = QDoubleSpinBox(self.grpSecondary)
        self.gonio_mcr2t_spb.setObjectName(u"gonio_mcr2t_spb")
        self.gonio_mcr2t_spb.setDecimals(2)
        self.gonio_mcr2t_spb.setMaximum(90.000000000000000)

        self.secondaryForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.gonio_mcr2t_spb)


        self.rightColumn.addWidget(self.grpSecondary)

        self.rightSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.rightColumn.addItem(self.rightSpacer)


        self.columnsLayout.addLayout(self.rightColumn)


        self.goniometerWidgetLayout.addLayout(self.columnsLayout)

        self.importExportRow = QHBoxLayout()
        self.importExportRow.setObjectName(u"importExportRow")
        self.lbl_import = QLabel(GoniometerWidget)
        self.lbl_import.setObjectName(u"lbl_import")

        self.importExportRow.addWidget(self.lbl_import)

        self.cmb_import_gonio = QComboBox(GoniometerWidget)
        self.cmb_import_gonio.setObjectName(u"cmb_import_gonio")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cmb_import_gonio.sizePolicy().hasHeightForWidth())
        self.cmb_import_gonio.setSizePolicy(sizePolicy)

        self.importExportRow.addWidget(self.cmb_import_gonio)

        self.btn_export_gonio = QPushButton(GoniometerWidget)
        self.btn_export_gonio.setObjectName(u"btn_export_gonio")

        self.importExportRow.addWidget(self.btn_export_gonio)

        self.lbl_applied_gonio = QLabel(GoniometerWidget)
        self.lbl_applied_gonio.setObjectName(u"lbl_applied_gonio")

        self.importExportRow.addWidget(self.lbl_applied_gonio)


        self.goniometerWidgetLayout.addLayout(self.importExportRow)


        self.retranslateUi(GoniometerWidget)

        self.gonio_divergence_mode.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(GoniometerWidget)
    # setupUi

    def retranslateUi(self, GoniometerWidget):
        self.grpGeneral.setTitle(QCoreApplication.translate("GoniometerWidget", u"General information", None))
        self.gonio_radius_lbl.setText(QCoreApplication.translate("GoniometerWidget", u"Radius", None))
        self.gonio_radius_spb.setSuffix(QCoreApplication.translate("GoniometerWidget", u" cm", None))
        self.gonio_min_2theta_lbl.setText(QCoreApplication.translate("GoniometerWidget", u"Minimal 2\u03b8", None))
        self.gonio_min_2theta_spb.setSuffix(QCoreApplication.translate("GoniometerWidget", u" \u00b0", None))
        self.gonio_max_2theta_lbl.setText(QCoreApplication.translate("GoniometerWidget", u"Maximal 2\u03b8", None))
        self.gonio_max_2theta_spb.setSuffix(QCoreApplication.translate("GoniometerWidget", u" \u00b0", None))
        self.lbl_steps_gonio1.setText(QCoreApplication.translate("GoniometerWidget", u"2\u03b8 Steps", None))
        self.grpSample.setTitle(QCoreApplication.translate("GoniometerWidget", u"Sample information", None))
        self.spec_length_lbl.setText(QCoreApplication.translate("GoniometerWidget", u"Sample length", None))
        self.sample_length_spb.setSuffix(QCoreApplication.translate("GoniometerWidget", u" cm", None))
        self.absorption_lbl3.setText(QCoreApplication.translate("GoniometerWidget", u"Surface density", None))
        self.sample_surf_density_spb.setSuffix(QCoreApplication.translate("GoniometerWidget", u" mg/cm\u00b2", None))
        self.gonio_has_absorption_correction.setText(QCoreApplication.translate("GoniometerWidget", u"Absorption correction", None))
        self.absorption_lbl.setText(QCoreApplication.translate("GoniometerWidget", u"Mass attenuation", None))
        self.absorption_spb.setSuffix(QCoreApplication.translate("GoniometerWidget", u" cm\u00b2/g", None))
        self.grpPrimary.setTitle(QCoreApplication.translate("GoniometerWidget", u"Primary beam information", None))
        self.gonio_lambda_lbl.setText(QCoreApplication.translate("GoniometerWidget", u"Wavelength (\u03bb)", None))
#if QT_CONFIG(tooltip)
        self.btn_edit_wld.setToolTip(QCoreApplication.translate("GoniometerWidget", u"Edit the X-ray emission spectrum (wavelength distribution).", None))
#endif // QT_CONFIG(tooltip)
        self.btn_edit_wld.setText(QCoreApplication.translate("GoniometerWidget", u"Edit emission spectrum", None))
        self.gonio_divergence_lbl.setText(QCoreApplication.translate("GoniometerWidget", u"Divergence mode", None))
        self.gonio_divergence_mode.setItemText(0, QCoreApplication.translate("GoniometerWidget", u"Automatic divergence", None))
        self.gonio_divergence_mode.setItemText(1, QCoreApplication.translate("GoniometerWidget", u"Fixed divergence", None))

        self.gonio_div_val_lbl.setText(QCoreApplication.translate("GoniometerWidget", u"Value", None))
        self.gonio_div_value_spb.setSuffix(QCoreApplication.translate("GoniometerWidget", u" \u00b0", None))
        self.gonio_has_soller1.setText(QCoreApplication.translate("GoniometerWidget", u"Soller 1", None))
        self.gonio_soller1_spb.setSuffix(QCoreApplication.translate("GoniometerWidget", u" \u00b0", None))
        self.grpSecondary.setTitle(QCoreApplication.translate("GoniometerWidget", u"Secondary beam information", None))
        self.gonio_has_soller2.setText(QCoreApplication.translate("GoniometerWidget", u"Soller 2", None))
        self.gonio_soller2_spb.setSuffix(QCoreApplication.translate("GoniometerWidget", u" \u00b0", None))
#if QT_CONFIG(tooltip)
        self.gonio_mcr_2theta_lbl6.setToolTip(QCoreApplication.translate("GoniometerWidget", u"The Bragg angle of the monochromator crystal. Set to zero if there is none.", None))
#endif // QT_CONFIG(tooltip)
        self.gonio_mcr_2theta_lbl6.setText(QCoreApplication.translate("GoniometerWidget", u"Monochromator 2\u03b8", None))
#if QT_CONFIG(tooltip)
        self.gonio_mcr2t_spb.setToolTip(QCoreApplication.translate("GoniometerWidget", u"The Bragg angle of the monochromator crystal. Set to zero if there is none.", None))
#endif // QT_CONFIG(tooltip)
        self.gonio_mcr2t_spb.setSuffix(QCoreApplication.translate("GoniometerWidget", u" \u00b0", None))
        self.lbl_import.setText(QCoreApplication.translate("GoniometerWidget", u"Load setup:", None))
#if QT_CONFIG(tooltip)
        self.btn_export_gonio.setToolTip(QCoreApplication.translate("GoniometerWidget", u"Stores the current goniometer setup as a default.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_export_gonio.setText(QCoreApplication.translate("GoniometerWidget", u"Store setup", None))
        self.lbl_applied_gonio.setText("")
        pass
    # retranslateUi

