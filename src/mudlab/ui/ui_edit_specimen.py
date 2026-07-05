# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_specimen.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QCheckBox,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTabWidget, QTableView, QVBoxLayout,
    QWidget)

class Ui_EditSpecimenDialog(object):
    def setupUi(self, EditSpecimenDialog):
        if not EditSpecimenDialog.objectName():
            EditSpecimenDialog.setObjectName(u"EditSpecimenDialog")
        EditSpecimenDialog.resize(640, 600)
        self.dialogLayout = QVBoxLayout(EditSpecimenDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.tabWidget = QTabWidget(EditSpecimenDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabGeneral = QWidget()
        self.tabGeneral.setObjectName(u"tabGeneral")
        self.generalForm = QFormLayout(self.tabGeneral)
        self.generalForm.setObjectName(u"generalForm")
        self.lblName = QLabel(self.tabGeneral)
        self.lblName.setObjectName(u"lblName")

        self.generalForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblName)

        self.specimen_name = QLineEdit(self.tabGeneral)
        self.specimen_name.setObjectName(u"specimen_name")

        self.generalForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.specimen_name)

        self.lblSample = QLabel(self.tabGeneral)
        self.lblSample.setObjectName(u"lblSample")

        self.generalForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblSample)

        self.specimen_sample_name = QLineEdit(self.tabGeneral)
        self.specimen_sample_name.setObjectName(u"specimen_sample_name")

        self.generalForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.specimen_sample_name)

        self.lblSource = QLabel(self.tabGeneral)
        self.lblSource.setObjectName(u"lblSource")

        self.generalForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblSource)

        self.specimen_source = QPlainTextEdit(self.tabGeneral)
        self.specimen_source.setObjectName(u"specimen_source")

        self.generalForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.specimen_source)

        self.tabWidget.addTab(self.tabGeneral, "")
        self.tabDisplay = QWidget()
        self.tabDisplay.setObjectName(u"tabDisplay")
        self.displayTabLayout = QVBoxLayout(self.tabDisplay)
        self.displayTabLayout.setObjectName(u"displayTabLayout")
        self.displayForm = QFormLayout()
        self.displayForm.setObjectName(u"displayForm")
        self.specimen_display_experimental = QCheckBox(self.tabDisplay)
        self.specimen_display_experimental.setObjectName(u"specimen_display_experimental")
        self.specimen_display_experimental.setChecked(True)

        self.displayForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.specimen_display_experimental)

        self.specimen_display_calculated = QCheckBox(self.tabDisplay)
        self.specimen_display_calculated.setObjectName(u"specimen_display_calculated")
        self.specimen_display_calculated.setChecked(True)

        self.displayForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.specimen_display_calculated)

        self.specimen_display_phases = QCheckBox(self.tabDisplay)
        self.specimen_display_phases.setObjectName(u"specimen_display_phases")

        self.displayForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.specimen_display_phases)

        self.specimen_display_derivatives = QCheckBox(self.tabDisplay)
        self.specimen_display_derivatives.setObjectName(u"specimen_display_derivatives")

        self.displayForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.specimen_display_derivatives)

        self.specimen_display_residuals = QCheckBox(self.tabDisplay)
        self.specimen_display_residuals.setObjectName(u"specimen_display_residuals")

        self.displayForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.specimen_display_residuals)

        self.specimen_display_stats_in_lbl = QCheckBox(self.tabDisplay)
        self.specimen_display_stats_in_lbl.setObjectName(u"specimen_display_stats_in_lbl")

        self.displayForm.setWidget(5, QFormLayout.ItemRole.FieldRole, self.specimen_display_stats_in_lbl)

        self.lblVshift = QLabel(self.tabDisplay)
        self.lblVshift.setObjectName(u"lblVshift")

        self.displayForm.setWidget(6, QFormLayout.ItemRole.LabelRole, self.lblVshift)

        self.display_vshift_spb = QDoubleSpinBox(self.tabDisplay)
        self.display_vshift_spb.setObjectName(u"display_vshift_spb")
        self.display_vshift_spb.setDecimals(2)
        self.display_vshift_spb.setMinimum(-10.000000000000000)
        self.display_vshift_spb.setMaximum(10.000000000000000)
        self.display_vshift_spb.setSingleStep(0.050000000000000)

        self.displayForm.setWidget(6, QFormLayout.ItemRole.FieldRole, self.display_vshift_spb)

        self.lblVscale = QLabel(self.tabDisplay)
        self.lblVscale.setObjectName(u"lblVscale")

        self.displayForm.setWidget(7, QFormLayout.ItemRole.LabelRole, self.lblVscale)

        self.display_vscale_spb = QDoubleSpinBox(self.tabDisplay)
        self.display_vscale_spb.setObjectName(u"display_vscale_spb")
        self.display_vscale_spb.setDecimals(2)
        self.display_vscale_spb.setMaximum(1000000000.000000000000000)
        self.display_vscale_spb.setSingleStep(0.100000000000000)
        self.display_vscale_spb.setValue(1.000000000000000)

        self.displayForm.setWidget(7, QFormLayout.ItemRole.FieldRole, self.display_vscale_spb)

        self.lblResidualScale = QLabel(self.tabDisplay)
        self.lblResidualScale.setObjectName(u"lblResidualScale")

        self.displayForm.setWidget(8, QFormLayout.ItemRole.LabelRole, self.lblResidualScale)

        self.display_residual_scale_spb = QDoubleSpinBox(self.tabDisplay)
        self.display_residual_scale_spb.setObjectName(u"display_residual_scale_spb")
        self.display_residual_scale_spb.setDecimals(2)
        self.display_residual_scale_spb.setMaximum(1000000000.000000000000000)
        self.display_residual_scale_spb.setSingleStep(0.100000000000000)
        self.display_residual_scale_spb.setValue(1.000000000000000)

        self.displayForm.setWidget(8, QFormLayout.ItemRole.FieldRole, self.display_residual_scale_spb)


        self.displayTabLayout.addLayout(self.displayForm)

        self.grpExpLine = QGroupBox(self.tabDisplay)
        self.grpExpLine.setObjectName(u"grpExpLine")
        self.expLineLayout = QVBoxLayout(self.grpExpLine)
        self.expLineLayout.setObjectName(u"expLineLayout")

        self.displayTabLayout.addWidget(self.grpExpLine)

        self.grpCalcLine = QGroupBox(self.tabDisplay)
        self.grpCalcLine.setObjectName(u"grpCalcLine")
        self.calcLineLayout = QVBoxLayout(self.grpCalcLine)
        self.calcLineLayout.setObjectName(u"calcLineLayout")

        self.displayTabLayout.addWidget(self.grpCalcLine)

        self.displaySpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.displayTabLayout.addItem(self.displaySpacer)

        self.tabWidget.addTab(self.tabDisplay, "")
        self.tabExperimental = QWidget()
        self.tabExperimental.setObjectName(u"tabExperimental")
        self.experimentalTabLayout = QVBoxLayout(self.tabExperimental)
        self.experimentalTabLayout.setObjectName(u"experimentalTabLayout")
        self.specimen_experimental_pattern = QTableView(self.tabExperimental)
        self.specimen_experimental_pattern.setObjectName(u"specimen_experimental_pattern")
        self.specimen_experimental_pattern.setAlternatingRowColors(True)
        self.specimen_experimental_pattern.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.experimentalTabLayout.addWidget(self.specimen_experimental_pattern)

        self.experimentalButtons = QHBoxLayout()
        self.experimentalButtons.setObjectName(u"experimentalButtons")
        self.btn_add_experimental_data = QPushButton(self.tabExperimental)
        self.btn_add_experimental_data.setObjectName(u"btn_add_experimental_data")

        self.experimentalButtons.addWidget(self.btn_add_experimental_data)

        self.btn_del_experimental_data = QPushButton(self.tabExperimental)
        self.btn_del_experimental_data.setObjectName(u"btn_del_experimental_data")

        self.experimentalButtons.addWidget(self.btn_del_experimental_data)

        self.expBtnSpacer = QSpacerItem(0, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.experimentalButtons.addItem(self.expBtnSpacer)

        self.btn_import_experimental_data = QPushButton(self.tabExperimental)
        self.btn_import_experimental_data.setObjectName(u"btn_import_experimental_data")

        self.experimentalButtons.addWidget(self.btn_import_experimental_data)

        self.btn_export_experimental_data = QPushButton(self.tabExperimental)
        self.btn_export_experimental_data.setObjectName(u"btn_export_experimental_data")

        self.experimentalButtons.addWidget(self.btn_export_experimental_data)


        self.experimentalTabLayout.addLayout(self.experimentalButtons)

        self.tabWidget.addTab(self.tabExperimental, "")
        self.tabCalculated = QWidget()
        self.tabCalculated.setObjectName(u"tabCalculated")
        self.calculatedTabLayout = QVBoxLayout(self.tabCalculated)
        self.calculatedTabLayout.setObjectName(u"calculatedTabLayout")
        self.specimen_calculated_pattern = QTableView(self.tabCalculated)
        self.specimen_calculated_pattern.setObjectName(u"specimen_calculated_pattern")
        self.specimen_calculated_pattern.setAlternatingRowColors(True)
        self.specimen_calculated_pattern.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.calculatedTabLayout.addWidget(self.specimen_calculated_pattern)

        self.calculatedButtons = QHBoxLayout()
        self.calculatedButtons.setObjectName(u"calculatedButtons")
        self.calcBtnSpacer = QSpacerItem(0, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.calculatedButtons.addItem(self.calcBtnSpacer)

        self.btn_export_calculated_data = QPushButton(self.tabCalculated)
        self.btn_export_calculated_data.setObjectName(u"btn_export_calculated_data")

        self.calculatedButtons.addWidget(self.btn_export_calculated_data)


        self.calculatedTabLayout.addLayout(self.calculatedButtons)

        self.tabWidget.addTab(self.tabCalculated, "")
        self.tabExclusions = QWidget()
        self.tabExclusions.setObjectName(u"tabExclusions")
        self.exclusionsTabLayout = QVBoxLayout(self.tabExclusions)
        self.exclusionsTabLayout.setObjectName(u"exclusionsTabLayout")
        self.specimen_exclusion_ranges = QTableView(self.tabExclusions)
        self.specimen_exclusion_ranges.setObjectName(u"specimen_exclusion_ranges")
        self.specimen_exclusion_ranges.setAlternatingRowColors(True)
        self.specimen_exclusion_ranges.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.exclusionsTabLayout.addWidget(self.specimen_exclusion_ranges)

        self.exclusionButtons = QHBoxLayout()
        self.exclusionButtons.setObjectName(u"exclusionButtons")
        self.btn_add_exclusion_range = QPushButton(self.tabExclusions)
        self.btn_add_exclusion_range.setObjectName(u"btn_add_exclusion_range")

        self.exclusionButtons.addWidget(self.btn_add_exclusion_range)

        self.btn_del_exclusion_ranges = QPushButton(self.tabExclusions)
        self.btn_del_exclusion_ranges.setObjectName(u"btn_del_exclusion_ranges")

        self.exclusionButtons.addWidget(self.btn_del_exclusion_ranges)

        self.exclBtnSpacer = QSpacerItem(0, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.exclusionButtons.addItem(self.exclBtnSpacer)

        self.btn_import_exclusion_ranges = QPushButton(self.tabExclusions)
        self.btn_import_exclusion_ranges.setObjectName(u"btn_import_exclusion_ranges")

        self.exclusionButtons.addWidget(self.btn_import_exclusion_ranges)

        self.btn_export_exclusion_ranges = QPushButton(self.tabExclusions)
        self.btn_export_exclusion_ranges.setObjectName(u"btn_export_exclusion_ranges")

        self.exclusionButtons.addWidget(self.btn_export_exclusion_ranges)


        self.exclusionsTabLayout.addLayout(self.exclusionButtons)

        self.tabWidget.addTab(self.tabExclusions, "")
        self.tabGoniometer = QWidget()
        self.tabGoniometer.setObjectName(u"tabGoniometer")
        self.goniometerTabLayout = QVBoxLayout(self.tabGoniometer)
        self.goniometerTabLayout.setObjectName(u"goniometerTabLayout")
        self.goniometerLayout = QVBoxLayout()
        self.goniometerLayout.setObjectName(u"goniometerLayout")

        self.goniometerTabLayout.addLayout(self.goniometerLayout)

        self.lblGonioPlaceholder = QLabel(self.tabGoniometer)
        self.lblGonioPlaceholder.setObjectName(u"lblGonioPlaceholder")
        self.lblGonioPlaceholder.setEnabled(False)
        self.lblGonioPlaceholder.setAlignment(Qt.AlignCenter)

        self.goniometerTabLayout.addWidget(self.lblGonioPlaceholder)

        self.gonioSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.goniometerTabLayout.addItem(self.gonioSpacer)

        self.tabWidget.addTab(self.tabGoniometer, "")

        self.dialogLayout.addWidget(self.tabWidget)

        self.buttonBox = QDialogButtonBox(EditSpecimenDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(EditSpecimenDialog)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(EditSpecimenDialog)
    # setupUi

    def retranslateUi(self, EditSpecimenDialog):
        EditSpecimenDialog.setWindowTitle(QCoreApplication.translate("EditSpecimenDialog", u"Edit Specimen", None))
        self.lblName.setText(QCoreApplication.translate("EditSpecimenDialog", u"Name", None))
        self.lblSample.setText(QCoreApplication.translate("EditSpecimenDialog", u"Sample", None))
        self.lblSource.setText(QCoreApplication.translate("EditSpecimenDialog", u"Source", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabGeneral), QCoreApplication.translate("EditSpecimenDialog", u"General", None))
        self.specimen_display_experimental.setText(QCoreApplication.translate("EditSpecimenDialog", u"Display experimental diffractogram", None))
        self.specimen_display_calculated.setText(QCoreApplication.translate("EditSpecimenDialog", u"Display calculated diffractogram", None))
        self.specimen_display_phases.setText(QCoreApplication.translate("EditSpecimenDialog", u"Display phases separately", None))
        self.specimen_display_derivatives.setText(QCoreApplication.translate("EditSpecimenDialog", u"Display derivative patterns", None))
        self.specimen_display_residuals.setText(QCoreApplication.translate("EditSpecimenDialog", u"Display residual patterns", None))
        self.specimen_display_stats_in_lbl.setText(QCoreApplication.translate("EditSpecimenDialog", u"Add R\u209a value to the specimen label", None))
        self.lblVshift.setText(QCoreApplication.translate("EditSpecimenDialog", u"Vertical shift of the plot", None))
        self.lblVscale.setText(QCoreApplication.translate("EditSpecimenDialog", u"Experimental scale factor", None))
        self.lblResidualScale.setText(QCoreApplication.translate("EditSpecimenDialog", u"Residuals scale factor", None))
        self.grpExpLine.setTitle(QCoreApplication.translate("EditSpecimenDialog", u"Experimental line", None))
        self.grpCalcLine.setTitle(QCoreApplication.translate("EditSpecimenDialog", u"Calculated line", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabDisplay), QCoreApplication.translate("EditSpecimenDialog", u"Display", None))
        self.btn_add_experimental_data.setText(QCoreApplication.translate("EditSpecimenDialog", u"Add", None))
        self.btn_del_experimental_data.setText(QCoreApplication.translate("EditSpecimenDialog", u"Remove", None))
        self.btn_import_experimental_data.setText(QCoreApplication.translate("EditSpecimenDialog", u"Import", None))
        self.btn_export_experimental_data.setText(QCoreApplication.translate("EditSpecimenDialog", u"Export", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabExperimental), QCoreApplication.translate("EditSpecimenDialog", u"Experimental", None))
        self.btn_export_calculated_data.setText(QCoreApplication.translate("EditSpecimenDialog", u"Export", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabCalculated), QCoreApplication.translate("EditSpecimenDialog", u"Calculated", None))
        self.btn_add_exclusion_range.setText(QCoreApplication.translate("EditSpecimenDialog", u"Add", None))
        self.btn_del_exclusion_ranges.setText(QCoreApplication.translate("EditSpecimenDialog", u"Remove", None))
        self.btn_import_exclusion_ranges.setText(QCoreApplication.translate("EditSpecimenDialog", u"Import", None))
        self.btn_export_exclusion_ranges.setText(QCoreApplication.translate("EditSpecimenDialog", u"Export", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabExclusions), QCoreApplication.translate("EditSpecimenDialog", u"Exclusion ranges", None))
        self.lblGonioPlaceholder.setText(QCoreApplication.translate("EditSpecimenDialog", u"The goniometer setup component (goniometer.ui) will be inserted here.", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabGoniometer), QCoreApplication.translate("EditSpecimenDialog", u"Goniometer", None))
    # retranslateUi

