# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_project.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSizePolicy, QSpacerItem, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget)

class Ui_EditProjectDialog(object):
    def setupUi(self, EditProjectDialog):
        if not EditProjectDialog.objectName():
            EditProjectDialog.setObjectName(u"EditProjectDialog")
        EditProjectDialog.resize(620, 560)
        self.dialogLayout = QVBoxLayout(EditProjectDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.tabWidget = QTabWidget(EditProjectDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabGeneral = QWidget()
        self.tabGeneral.setObjectName(u"tabGeneral")
        self.generalForm = QFormLayout(self.tabGeneral)
        self.generalForm.setObjectName(u"generalForm")
        self.lblName = QLabel(self.tabGeneral)
        self.lblName.setObjectName(u"lblName")

        self.generalForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblName)

        self.project_name = QLineEdit(self.tabGeneral)
        self.project_name.setObjectName(u"project_name")

        self.generalForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.project_name)

        self.lblAuthor = QLabel(self.tabGeneral)
        self.lblAuthor.setObjectName(u"lblAuthor")

        self.generalForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblAuthor)

        self.project_author = QLineEdit(self.tabGeneral)
        self.project_author.setObjectName(u"project_author")

        self.generalForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.project_author)

        self.lblDate = QLabel(self.tabGeneral)
        self.lblDate.setObjectName(u"lblDate")

        self.generalForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblDate)

        self.project_date = QLineEdit(self.tabGeneral)
        self.project_date.setObjectName(u"project_date")

        self.generalForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.project_date)

        self.lblDescription = QLabel(self.tabGeneral)
        self.lblDescription.setObjectName(u"lblDescription")

        self.generalForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblDescription)

        self.project_description = QPlainTextEdit(self.tabGeneral)
        self.project_description.setObjectName(u"project_description")

        self.generalForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.project_description)

        self.lblLayoutMode = QLabel(self.tabGeneral)
        self.lblLayoutMode.setObjectName(u"lblLayoutMode")

        self.generalForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lblLayoutMode)

        self.project_layout_mode = QComboBox(self.tabGeneral)
        self.project_layout_mode.addItem("")
        self.project_layout_mode.addItem("")
        self.project_layout_mode.setObjectName(u"project_layout_mode")

        self.generalForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.project_layout_mode)

        self.tabWidget.addTab(self.tabGeneral, "")
        self.tabPatterns = QWidget()
        self.tabPatterns.setObjectName(u"tabPatterns")
        self.patternsTabLayout = QVBoxLayout(self.tabPatterns)
        self.patternsTabLayout.setObjectName(u"patternsTabLayout")
        self.patternsForm = QFormLayout()
        self.patternsForm.setObjectName(u"patternsForm")
        self.lblYNormalize = QLabel(self.tabPatterns)
        self.lblYNormalize.setObjectName(u"lblYNormalize")

        self.patternsForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblYNormalize)

        self.project_axes_ynormalize = QComboBox(self.tabPatterns)
        self.project_axes_ynormalize.addItem("")
        self.project_axes_ynormalize.addItem("")
        self.project_axes_ynormalize.addItem("")
        self.project_axes_ynormalize.setObjectName(u"project_axes_ynormalize")

        self.patternsForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.project_axes_ynormalize)

        self.lblOffset = QLabel(self.tabPatterns)
        self.lblOffset.setObjectName(u"lblOffset")

        self.patternsForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblOffset)

        self.project_display_plot_offset = QDoubleSpinBox(self.tabPatterns)
        self.project_display_plot_offset.setObjectName(u"project_display_plot_offset")
        self.project_display_plot_offset.setDecimals(2)
        self.project_display_plot_offset.setMaximum(100.000000000000000)
        self.project_display_plot_offset.setSingleStep(0.050000000000000)
        self.project_display_plot_offset.setValue(0.750000000000000)

        self.patternsForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.project_display_plot_offset)

        self.lblGroupBy = QLabel(self.tabPatterns)
        self.lblGroupBy.setObjectName(u"lblGroupBy")

        self.patternsForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblGroupBy)

        self.spin_display_group_by = QSpinBox(self.tabPatterns)
        self.spin_display_group_by.setObjectName(u"spin_display_group_by")
        self.spin_display_group_by.setMinimum(1)
        self.spin_display_group_by.setMaximum(100)

        self.patternsForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.spin_display_group_by)

        self.lblLabelPos = QLabel(self.tabPatterns)
        self.lblLabelPos.setObjectName(u"lblLabelPos")

        self.patternsForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblLabelPos)

        self.project_display_label_pos = QDoubleSpinBox(self.tabPatterns)
        self.project_display_label_pos.setObjectName(u"project_display_label_pos")
        self.project_display_label_pos.setDecimals(2)
        self.project_display_label_pos.setMaximum(1.000000000000000)
        self.project_display_label_pos.setSingleStep(0.050000000000000)
        self.project_display_label_pos.setValue(0.350000000000000)

        self.patternsForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.project_display_label_pos)


        self.patternsTabLayout.addLayout(self.patternsForm)

        self.grpExperimental = QGroupBox(self.tabPatterns)
        self.grpExperimental.setObjectName(u"grpExperimental")
        self.experimentalForm = QFormLayout(self.grpExperimental)
        self.experimentalForm.setObjectName(u"experimentalForm")
        self.lblExpColor = QLabel(self.grpExperimental)
        self.lblExpColor.setObjectName(u"lblExpColor")

        self.experimentalForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblExpColor)

        self.project_display_exp_color = QPushButton(self.grpExperimental)
        self.project_display_exp_color.setObjectName(u"project_display_exp_color")

        self.experimentalForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.project_display_exp_color)

        self.lblExpLw = QLabel(self.grpExperimental)
        self.lblExpLw.setObjectName(u"lblExpLw")

        self.experimentalForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblExpLw)

        self.spin_display_exp_lw = QDoubleSpinBox(self.grpExperimental)
        self.spin_display_exp_lw.setObjectName(u"spin_display_exp_lw")
        self.spin_display_exp_lw.setDecimals(1)
        self.spin_display_exp_lw.setMinimum(1.000000000000000)
        self.spin_display_exp_lw.setMaximum(100.000000000000000)
        self.spin_display_exp_lw.setValue(1.000000000000000)

        self.experimentalForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.spin_display_exp_lw)

        self.lblExpLs = QLabel(self.grpExperimental)
        self.lblExpLs.setObjectName(u"lblExpLs")

        self.experimentalForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblExpLs)

        self.project_display_exp_ls = QComboBox(self.grpExperimental)
        self.project_display_exp_ls.addItem("")
        self.project_display_exp_ls.addItem("")
        self.project_display_exp_ls.addItem("")
        self.project_display_exp_ls.addItem("")
        self.project_display_exp_ls.addItem("")
        self.project_display_exp_ls.setObjectName(u"project_display_exp_ls")

        self.experimentalForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.project_display_exp_ls)

        self.lblExpMarker = QLabel(self.grpExperimental)
        self.lblExpMarker.setObjectName(u"lblExpMarker")

        self.experimentalForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblExpMarker)

        self.project_display_exp_marker = QComboBox(self.grpExperimental)
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.addItem("")
        self.project_display_exp_marker.setObjectName(u"project_display_exp_marker")

        self.experimentalForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.project_display_exp_marker)


        self.patternsTabLayout.addWidget(self.grpExperimental)

        self.grpCalculated = QGroupBox(self.tabPatterns)
        self.grpCalculated.setObjectName(u"grpCalculated")
        self.calculatedForm = QFormLayout(self.grpCalculated)
        self.calculatedForm.setObjectName(u"calculatedForm")
        self.lblCalcColor = QLabel(self.grpCalculated)
        self.lblCalcColor.setObjectName(u"lblCalcColor")

        self.calculatedForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblCalcColor)

        self.project_display_calc_color = QPushButton(self.grpCalculated)
        self.project_display_calc_color.setObjectName(u"project_display_calc_color")

        self.calculatedForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.project_display_calc_color)

        self.lblCalcLw = QLabel(self.grpCalculated)
        self.lblCalcLw.setObjectName(u"lblCalcLw")

        self.calculatedForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblCalcLw)

        self.spin_display_calc_lw = QDoubleSpinBox(self.grpCalculated)
        self.spin_display_calc_lw.setObjectName(u"spin_display_calc_lw")
        self.spin_display_calc_lw.setDecimals(1)
        self.spin_display_calc_lw.setMinimum(1.000000000000000)
        self.spin_display_calc_lw.setMaximum(100.000000000000000)
        self.spin_display_calc_lw.setValue(2.000000000000000)

        self.calculatedForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.spin_display_calc_lw)

        self.lblCalcLs = QLabel(self.grpCalculated)
        self.lblCalcLs.setObjectName(u"lblCalcLs")

        self.calculatedForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblCalcLs)

        self.project_display_calc_ls = QComboBox(self.grpCalculated)
        self.project_display_calc_ls.addItem("")
        self.project_display_calc_ls.addItem("")
        self.project_display_calc_ls.addItem("")
        self.project_display_calc_ls.addItem("")
        self.project_display_calc_ls.addItem("")
        self.project_display_calc_ls.setObjectName(u"project_display_calc_ls")

        self.calculatedForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.project_display_calc_ls)

        self.lblCalcMarker = QLabel(self.grpCalculated)
        self.lblCalcMarker.setObjectName(u"lblCalcMarker")

        self.calculatedForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblCalcMarker)

        self.project_display_calc_marker = QComboBox(self.grpCalculated)
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.addItem("")
        self.project_display_calc_marker.setObjectName(u"project_display_calc_marker")

        self.calculatedForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.project_display_calc_marker)


        self.patternsTabLayout.addWidget(self.grpCalculated)

        self.patternsSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.patternsTabLayout.addItem(self.patternsSpacer)

        self.tabWidget.addTab(self.tabPatterns, "")
        self.tabPlot = QWidget()
        self.tabPlot.setObjectName(u"tabPlot")
        self.plotTabLayout = QVBoxLayout(self.tabPlot)
        self.plotTabLayout.setObjectName(u"plotTabLayout")
        self.grpXScale = QGroupBox(self.tabPlot)
        self.grpXScale.setObjectName(u"grpXScale")
        self.xScaleForm = QFormLayout(self.grpXScale)
        self.xScaleForm.setObjectName(u"xScaleForm")
        self.lblXLimit = QLabel(self.grpXScale)
        self.lblXLimit.setObjectName(u"lblXLimit")

        self.xScaleForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblXLimit)

        self.project_axes_xlimit = QComboBox(self.grpXScale)
        self.project_axes_xlimit.addItem("")
        self.project_axes_xlimit.addItem("")
        self.project_axes_xlimit.setObjectName(u"project_axes_xlimit")

        self.xScaleForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.project_axes_xlimit)

        self.project_axes_xstretch = QCheckBox(self.grpXScale)
        self.project_axes_xstretch.setObjectName(u"project_axes_xstretch")
        self.project_axes_xstretch.setChecked(True)

        self.xScaleForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.project_axes_xstretch)

        self.lblXMin = QLabel(self.grpXScale)
        self.lblXMin.setObjectName(u"lblXMin")

        self.xScaleForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblXMin)

        self.spin_project_axes_xmin = QDoubleSpinBox(self.grpXScale)
        self.spin_project_axes_xmin.setObjectName(u"spin_project_axes_xmin")
        self.spin_project_axes_xmin.setDecimals(2)
        self.spin_project_axes_xmin.setMaximum(180.000000000000000)

        self.xScaleForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.spin_project_axes_xmin)

        self.lblXMax = QLabel(self.grpXScale)
        self.lblXMax.setObjectName(u"lblXMax")

        self.xScaleForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblXMax)

        self.spin_project_axes_xmax = QDoubleSpinBox(self.grpXScale)
        self.spin_project_axes_xmax.setObjectName(u"spin_project_axes_xmax")
        self.spin_project_axes_xmax.setDecimals(2)
        self.spin_project_axes_xmax.setMaximum(180.000000000000000)
        self.spin_project_axes_xmax.setValue(70.000000000000000)

        self.xScaleForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.spin_project_axes_xmax)


        self.plotTabLayout.addWidget(self.grpXScale)

        self.grpYScale = QGroupBox(self.tabPlot)
        self.grpYScale.setObjectName(u"grpYScale")
        self.yScaleForm = QFormLayout(self.grpYScale)
        self.yScaleForm.setObjectName(u"yScaleForm")
        self.lblYLimit = QLabel(self.grpYScale)
        self.lblYLimit.setObjectName(u"lblYLimit")

        self.yScaleForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblYLimit)

        self.project_axes_ylimit = QComboBox(self.grpYScale)
        self.project_axes_ylimit.addItem("")
        self.project_axes_ylimit.addItem("")
        self.project_axes_ylimit.setObjectName(u"project_axes_ylimit")

        self.yScaleForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.project_axes_ylimit)

        self.project_axes_yvisible = QCheckBox(self.grpYScale)
        self.project_axes_yvisible.setObjectName(u"project_axes_yvisible")

        self.yScaleForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.project_axes_yvisible)

        self.lblYMin = QLabel(self.grpYScale)
        self.lblYMin.setObjectName(u"lblYMin")

        self.yScaleForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblYMin)

        self.spin_project_axes_ymin = QDoubleSpinBox(self.grpYScale)
        self.spin_project_axes_ymin.setObjectName(u"spin_project_axes_ymin")
        self.spin_project_axes_ymin.setDecimals(0)
        self.spin_project_axes_ymin.setMaximum(1000000000000.000000000000000)
        self.spin_project_axes_ymin.setSingleStep(100.000000000000000)

        self.yScaleForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.spin_project_axes_ymin)

        self.lblYMax = QLabel(self.grpYScale)
        self.lblYMax.setObjectName(u"lblYMax")

        self.yScaleForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblYMax)

        self.spin_project_axes_ymax = QDoubleSpinBox(self.grpYScale)
        self.spin_project_axes_ymax.setObjectName(u"spin_project_axes_ymax")
        self.spin_project_axes_ymax.setDecimals(0)
        self.spin_project_axes_ymax.setMaximum(1000000000000.000000000000000)
        self.spin_project_axes_ymax.setSingleStep(100.000000000000000)

        self.yScaleForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.spin_project_axes_ymax)


        self.plotTabLayout.addWidget(self.grpYScale)

        self.project_axes_dspacing = QCheckBox(self.tabPlot)
        self.project_axes_dspacing.setObjectName(u"project_axes_dspacing")

        self.plotTabLayout.addWidget(self.project_axes_dspacing)

        self.plotSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.plotTabLayout.addItem(self.plotSpacer)

        self.tabWidget.addTab(self.tabPlot, "")
        self.tabMarkers = QWidget()
        self.tabMarkers.setObjectName(u"tabMarkers")
        self.markersForm = QFormLayout(self.tabMarkers)
        self.markersForm.setObjectName(u"markersForm")
        self.lblMarkerAngle = QLabel(self.tabMarkers)
        self.lblMarkerAngle.setObjectName(u"lblMarkerAngle")

        self.markersForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblMarkerAngle)

        self.project_display_marker_angle = QDoubleSpinBox(self.tabMarkers)
        self.project_display_marker_angle.setObjectName(u"project_display_marker_angle")
        self.project_display_marker_angle.setDecimals(2)
        self.project_display_marker_angle.setMinimum(-180.000000000000000)
        self.project_display_marker_angle.setMaximum(180.000000000000000)

        self.markersForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.project_display_marker_angle)

        self.lblMarkerTopOffset = QLabel(self.tabMarkers)
        self.lblMarkerTopOffset.setObjectName(u"lblMarkerTopOffset")

        self.markersForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblMarkerTopOffset)

        self.project_display_marker_top_offset = QDoubleSpinBox(self.tabMarkers)
        self.project_display_marker_top_offset.setObjectName(u"project_display_marker_top_offset")
        self.project_display_marker_top_offset.setDecimals(2)
        self.project_display_marker_top_offset.setMinimum(-1000000.000000000000000)
        self.project_display_marker_top_offset.setMaximum(1000000.000000000000000)

        self.markersForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.project_display_marker_top_offset)

        self.lblMarkerStyle = QLabel(self.tabMarkers)
        self.lblMarkerStyle.setObjectName(u"lblMarkerStyle")

        self.markersForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblMarkerStyle)

        self.project_display_marker_style = QComboBox(self.tabMarkers)
        self.project_display_marker_style.addItem("")
        self.project_display_marker_style.addItem("")
        self.project_display_marker_style.addItem("")
        self.project_display_marker_style.addItem("")
        self.project_display_marker_style.addItem("")
        self.project_display_marker_style.addItem("")
        self.project_display_marker_style.setObjectName(u"project_display_marker_style")

        self.markersForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.project_display_marker_style)

        self.lblMarkerColor = QLabel(self.tabMarkers)
        self.lblMarkerColor.setObjectName(u"lblMarkerColor")

        self.markersForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblMarkerColor)

        self.project_display_marker_color = QPushButton(self.tabMarkers)
        self.project_display_marker_color.setObjectName(u"project_display_marker_color")

        self.markersForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.project_display_marker_color)

        self.lblMarkerBase = QLabel(self.tabMarkers)
        self.lblMarkerBase.setObjectName(u"lblMarkerBase")

        self.markersForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lblMarkerBase)

        self.project_display_marker_base = QComboBox(self.tabMarkers)
        self.project_display_marker_base.addItem("")
        self.project_display_marker_base.addItem("")
        self.project_display_marker_base.addItem("")
        self.project_display_marker_base.addItem("")
        self.project_display_marker_base.addItem("")
        self.project_display_marker_base.setObjectName(u"project_display_marker_base")

        self.markersForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.project_display_marker_base)

        self.lblMarkerTop = QLabel(self.tabMarkers)
        self.lblMarkerTop.setObjectName(u"lblMarkerTop")

        self.markersForm.setWidget(5, QFormLayout.ItemRole.LabelRole, self.lblMarkerTop)

        self.project_display_marker_top = QComboBox(self.tabMarkers)
        self.project_display_marker_top.addItem("")
        self.project_display_marker_top.addItem("")
        self.project_display_marker_top.setObjectName(u"project_display_marker_top")

        self.markersForm.setWidget(5, QFormLayout.ItemRole.FieldRole, self.project_display_marker_top)

        self.lblMarkerAlign = QLabel(self.tabMarkers)
        self.lblMarkerAlign.setObjectName(u"lblMarkerAlign")

        self.markersForm.setWidget(6, QFormLayout.ItemRole.LabelRole, self.lblMarkerAlign)

        self.project_display_marker_align = QComboBox(self.tabMarkers)
        self.project_display_marker_align.addItem("")
        self.project_display_marker_align.addItem("")
        self.project_display_marker_align.addItem("")
        self.project_display_marker_align.setObjectName(u"project_display_marker_align")

        self.markersForm.setWidget(6, QFormLayout.ItemRole.FieldRole, self.project_display_marker_align)

        self.tabWidget.addTab(self.tabMarkers, "")

        self.dialogLayout.addWidget(self.tabWidget)

        self.buttonBox = QDialogButtonBox(EditProjectDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(EditProjectDialog)

        self.tabWidget.setCurrentIndex(0)
        self.project_display_exp_ls.setCurrentIndex(1)
        self.project_display_calc_ls.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(EditProjectDialog)
    # setupUi

    def retranslateUi(self, EditProjectDialog):
        EditProjectDialog.setWindowTitle(QCoreApplication.translate("EditProjectDialog", u"Edit Project", None))
        self.lblName.setText(QCoreApplication.translate("EditProjectDialog", u"Name", None))
        self.lblAuthor.setText(QCoreApplication.translate("EditProjectDialog", u"Author", None))
        self.lblDate.setText(QCoreApplication.translate("EditProjectDialog", u"Date", None))
        self.lblDescription.setText(QCoreApplication.translate("EditProjectDialog", u"Description", None))
        self.lblLayoutMode.setText(QCoreApplication.translate("EditProjectDialog", u"Layout mode", None))
        self.project_layout_mode.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"Full", None))
        self.project_layout_mode.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"View-mode", None))

#if QT_CONFIG(tooltip)
        self.project_layout_mode.setToolTip(QCoreApplication.translate("EditProjectDialog", u"Temporary: only Full mode will be used; kept for wiring parity with the old app.", None))
#endif // QT_CONFIG(tooltip)
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabGeneral), QCoreApplication.translate("EditProjectDialog", u"General", None))
        self.lblYNormalize.setText(QCoreApplication.translate("EditProjectDialog", u"Y-scale normalization", None))
        self.project_axes_ynormalize.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"Multi normalised", None))
        self.project_axes_ynormalize.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"Single normalised", None))
        self.project_axes_ynormalize.setItemText(2, QCoreApplication.translate("EditProjectDialog", u"Unchanged raw counts", None))

        self.lblOffset.setText(QCoreApplication.translate("EditProjectDialog", u"Pattern offset", None))
        self.lblGroupBy.setText(QCoreApplication.translate("EditProjectDialog", u"Group patterns by", None))
        self.lblLabelPos.setText(QCoreApplication.translate("EditProjectDialog", u"Default label position [0-1]", None))
        self.grpExperimental.setTitle(QCoreApplication.translate("EditProjectDialog", u"Experimental pattern", None))
        self.lblExpColor.setText(QCoreApplication.translate("EditProjectDialog", u"Color", None))
        self.project_display_exp_color.setText(QCoreApplication.translate("EditProjectDialog", u"#000000", None))
        self.lblExpLw.setText(QCoreApplication.translate("EditProjectDialog", u"Linewidth", None))
        self.lblExpLs.setText(QCoreApplication.translate("EditProjectDialog", u"Linestyle", None))
        self.project_display_exp_ls.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"Nothing", None))
        self.project_display_exp_ls.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"Solid", None))
        self.project_display_exp_ls.setItemText(2, QCoreApplication.translate("EditProjectDialog", u"Dashed", None))
        self.project_display_exp_ls.setItemText(3, QCoreApplication.translate("EditProjectDialog", u"Dash Dot", None))
        self.project_display_exp_ls.setItemText(4, QCoreApplication.translate("EditProjectDialog", u"Dotted", None))

        self.lblExpMarker.setText(QCoreApplication.translate("EditProjectDialog", u"Marker", None))
        self.project_display_exp_marker.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"No marker", None))
        self.project_display_exp_marker.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"Point", None))
        self.project_display_exp_marker.setItemText(2, QCoreApplication.translate("EditProjectDialog", u"Pixel", None))
        self.project_display_exp_marker.setItemText(3, QCoreApplication.translate("EditProjectDialog", u"Plus", None))
        self.project_display_exp_marker.setItemText(4, QCoreApplication.translate("EditProjectDialog", u"Cross", None))
        self.project_display_exp_marker.setItemText(5, QCoreApplication.translate("EditProjectDialog", u"Diamond", None))
        self.project_display_exp_marker.setItemText(6, QCoreApplication.translate("EditProjectDialog", u"Circle", None))
        self.project_display_exp_marker.setItemText(7, QCoreApplication.translate("EditProjectDialog", u"Triangle down", None))
        self.project_display_exp_marker.setItemText(8, QCoreApplication.translate("EditProjectDialog", u"Triangle up", None))
        self.project_display_exp_marker.setItemText(9, QCoreApplication.translate("EditProjectDialog", u"Triangle left", None))
        self.project_display_exp_marker.setItemText(10, QCoreApplication.translate("EditProjectDialog", u"Triangle right", None))
        self.project_display_exp_marker.setItemText(11, QCoreApplication.translate("EditProjectDialog", u"Octagon", None))
        self.project_display_exp_marker.setItemText(12, QCoreApplication.translate("EditProjectDialog", u"Square", None))
        self.project_display_exp_marker.setItemText(13, QCoreApplication.translate("EditProjectDialog", u"Pentagon", None))
        self.project_display_exp_marker.setItemText(14, QCoreApplication.translate("EditProjectDialog", u"Star", None))
        self.project_display_exp_marker.setItemText(15, QCoreApplication.translate("EditProjectDialog", u"Hexagon", None))

        self.grpCalculated.setTitle(QCoreApplication.translate("EditProjectDialog", u"Calculated pattern", None))
        self.lblCalcColor.setText(QCoreApplication.translate("EditProjectDialog", u"Color", None))
        self.project_display_calc_color.setText(QCoreApplication.translate("EditProjectDialog", u"#FF0000", None))
        self.lblCalcLw.setText(QCoreApplication.translate("EditProjectDialog", u"Linewidth", None))
        self.lblCalcLs.setText(QCoreApplication.translate("EditProjectDialog", u"Linestyle", None))
        self.project_display_calc_ls.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"Nothing", None))
        self.project_display_calc_ls.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"Solid", None))
        self.project_display_calc_ls.setItemText(2, QCoreApplication.translate("EditProjectDialog", u"Dashed", None))
        self.project_display_calc_ls.setItemText(3, QCoreApplication.translate("EditProjectDialog", u"Dash Dot", None))
        self.project_display_calc_ls.setItemText(4, QCoreApplication.translate("EditProjectDialog", u"Dotted", None))

        self.lblCalcMarker.setText(QCoreApplication.translate("EditProjectDialog", u"Marker", None))
        self.project_display_calc_marker.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"No marker", None))
        self.project_display_calc_marker.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"Point", None))
        self.project_display_calc_marker.setItemText(2, QCoreApplication.translate("EditProjectDialog", u"Pixel", None))
        self.project_display_calc_marker.setItemText(3, QCoreApplication.translate("EditProjectDialog", u"Plus", None))
        self.project_display_calc_marker.setItemText(4, QCoreApplication.translate("EditProjectDialog", u"Cross", None))
        self.project_display_calc_marker.setItemText(5, QCoreApplication.translate("EditProjectDialog", u"Diamond", None))
        self.project_display_calc_marker.setItemText(6, QCoreApplication.translate("EditProjectDialog", u"Circle", None))
        self.project_display_calc_marker.setItemText(7, QCoreApplication.translate("EditProjectDialog", u"Triangle down", None))
        self.project_display_calc_marker.setItemText(8, QCoreApplication.translate("EditProjectDialog", u"Triangle up", None))
        self.project_display_calc_marker.setItemText(9, QCoreApplication.translate("EditProjectDialog", u"Triangle left", None))
        self.project_display_calc_marker.setItemText(10, QCoreApplication.translate("EditProjectDialog", u"Triangle right", None))
        self.project_display_calc_marker.setItemText(11, QCoreApplication.translate("EditProjectDialog", u"Octagon", None))
        self.project_display_calc_marker.setItemText(12, QCoreApplication.translate("EditProjectDialog", u"Square", None))
        self.project_display_calc_marker.setItemText(13, QCoreApplication.translate("EditProjectDialog", u"Pentagon", None))
        self.project_display_calc_marker.setItemText(14, QCoreApplication.translate("EditProjectDialog", u"Star", None))
        self.project_display_calc_marker.setItemText(15, QCoreApplication.translate("EditProjectDialog", u"Hexagon", None))

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabPatterns), QCoreApplication.translate("EditProjectDialog", u"Patterns", None))
        self.grpXScale.setTitle(QCoreApplication.translate("EditProjectDialog", u"X scale", None))
        self.lblXLimit.setText(QCoreApplication.translate("EditProjectDialog", u"Scale", None))
        self.project_axes_xlimit.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"Automatic", None))
        self.project_axes_xlimit.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"Manual", None))

        self.project_axes_xstretch.setText(QCoreApplication.translate("EditProjectDialog", u"Stretch X-axis to fit window", None))
        self.lblXMin.setText(QCoreApplication.translate("EditProjectDialog", u"min.", None))
        self.spin_project_axes_xmin.setSuffix(QCoreApplication.translate("EditProjectDialog", u" \u00b02\u03b8", None))
        self.lblXMax.setText(QCoreApplication.translate("EditProjectDialog", u"max.", None))
        self.spin_project_axes_xmax.setSuffix(QCoreApplication.translate("EditProjectDialog", u" \u00b02\u03b8", None))
        self.grpYScale.setTitle(QCoreApplication.translate("EditProjectDialog", u"Y scale", None))
        self.lblYLimit.setText(QCoreApplication.translate("EditProjectDialog", u"Scale", None))
        self.project_axes_ylimit.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"Automatic", None))
        self.project_axes_ylimit.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"Manual", None))

        self.project_axes_yvisible.setText(QCoreApplication.translate("EditProjectDialog", u"Y-axis visible", None))
        self.lblYMin.setText(QCoreApplication.translate("EditProjectDialog", u"min.", None))
        self.spin_project_axes_ymin.setSuffix(QCoreApplication.translate("EditProjectDialog", u" counts", None))
        self.lblYMax.setText(QCoreApplication.translate("EditProjectDialog", u"max.", None))
        self.spin_project_axes_ymax.setSuffix(QCoreApplication.translate("EditProjectDialog", u" counts", None))
#if QT_CONFIG(tooltip)
        self.project_axes_dspacing.setToolTip(QCoreApplication.translate("EditProjectDialog", u"Will use the wavelength of the first specimen's goniometer setup", None))
#endif // QT_CONFIG(tooltip)
        self.project_axes_dspacing.setText(QCoreApplication.translate("EditProjectDialog", u"Show d-spacing (in nm)", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabPlot), QCoreApplication.translate("EditProjectDialog", u"Plot", None))
        self.lblMarkerAngle.setText(QCoreApplication.translate("EditProjectDialog", u"Angle", None))
        self.project_display_marker_angle.setSuffix(QCoreApplication.translate("EditProjectDialog", u" \u00b0", None))
        self.lblMarkerTopOffset.setText(QCoreApplication.translate("EditProjectDialog", u"Offset from base", None))
        self.lblMarkerStyle.setText(QCoreApplication.translate("EditProjectDialog", u"Line style", None))
        self.project_display_marker_style.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"None", None))
        self.project_display_marker_style.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"Solid", None))
        self.project_display_marker_style.setItemText(2, QCoreApplication.translate("EditProjectDialog", u"Dash", None))
        self.project_display_marker_style.setItemText(3, QCoreApplication.translate("EditProjectDialog", u"Dotted", None))
        self.project_display_marker_style.setItemText(4, QCoreApplication.translate("EditProjectDialog", u"Dash-Dotted", None))
        self.project_display_marker_style.setItemText(5, QCoreApplication.translate("EditProjectDialog", u"Display at Y-offset", None))

        self.lblMarkerColor.setText(QCoreApplication.translate("EditProjectDialog", u"Colour", None))
        self.project_display_marker_color.setText(QCoreApplication.translate("EditProjectDialog", u"#000000", None))
        self.lblMarkerBase.setText(QCoreApplication.translate("EditProjectDialog", u"Base connection", None))
        self.project_display_marker_base.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"X-axis", None))
        self.project_display_marker_base.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"Experimental profile", None))
        self.project_display_marker_base.setItemText(2, QCoreApplication.translate("EditProjectDialog", u"Calculated profile", None))
        self.project_display_marker_base.setItemText(3, QCoreApplication.translate("EditProjectDialog", u"Lowest of both", None))
        self.project_display_marker_base.setItemText(4, QCoreApplication.translate("EditProjectDialog", u"Highest of both", None))

        self.lblMarkerTop.setText(QCoreApplication.translate("EditProjectDialog", u"Top connection", None))
        self.project_display_marker_top.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"Relative to base", None))
        self.project_display_marker_top.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"Top of plot", None))

        self.lblMarkerAlign.setText(QCoreApplication.translate("EditProjectDialog", u"Label alignment", None))
        self.project_display_marker_align.setItemText(0, QCoreApplication.translate("EditProjectDialog", u"Left align", None))
        self.project_display_marker_align.setItemText(1, QCoreApplication.translate("EditProjectDialog", u"Centered", None))
        self.project_display_marker_align.setItemText(2, QCoreApplication.translate("EditProjectDialog", u"Right align", None))

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabMarkers), QCoreApplication.translate("EditProjectDialog", u"Markers", None))
    # retranslateUi

