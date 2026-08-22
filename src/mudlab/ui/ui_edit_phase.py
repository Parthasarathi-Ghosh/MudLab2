# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_phase.ui'
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
    QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QTabWidget,
    QVBoxLayout, QWidget)

class Ui_EditPhaseWidget(object):
    def setupUi(self, EditPhaseWidget):
        if not EditPhaseWidget.objectName():
            EditPhaseWidget.setObjectName(u"EditPhaseWidget")
        self.phaseLayout = QVBoxLayout(EditPhaseWidget)
        self.phaseLayout.setObjectName(u"phaseLayout")
        self.phaseForm = QFormLayout()
        self.phaseForm.setObjectName(u"phaseForm")
        self.lblPhaseName = QLabel(EditPhaseWidget)
        self.lblPhaseName.setObjectName(u"lblPhaseName")

        self.phaseForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblPhaseName)

        self.nameColorRow = QHBoxLayout()
        self.nameColorRow.setObjectName(u"nameColorRow")
        self.phase_name = QLineEdit(EditPhaseWidget)
        self.phase_name.setObjectName(u"phase_name")

        self.nameColorRow.addWidget(self.phase_name)

        self.phase_display_color = QPushButton(EditPhaseWidget)
        self.phase_display_color.setObjectName(u"phase_display_color")
        self.phase_display_color.setMaximumSize(QSize(110, 16777215))

        self.nameColorRow.addWidget(self.phase_display_color)

        self.phase_inherit_display_color = QCheckBox(EditPhaseWidget)
        self.phase_inherit_display_color.setObjectName(u"phase_inherit_display_color")

        self.nameColorRow.addWidget(self.phase_inherit_display_color)


        self.phaseForm.setLayout(0, QFormLayout.ItemRole.FieldRole, self.nameColorRow)

        self.lblBasedOn = QLabel(EditPhaseWidget)
        self.lblBasedOn.setObjectName(u"lblBasedOn")

        self.phaseForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblBasedOn)

        self.phase_based_on = QComboBox(EditPhaseWidget)
        self.phase_based_on.addItem("")
        self.phase_based_on.setObjectName(u"phase_based_on")

        self.phaseForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.phase_based_on)

        self.lblG = QLabel(EditPhaseWidget)
        self.lblG.setObjectName(u"lblG")

        self.phaseForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblG)

        self.phase_G = QLineEdit(EditPhaseWidget)
        self.phase_G.setObjectName(u"phase_G")
        self.phase_G.setReadOnly(True)

        self.phaseForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.phase_G)

        self.lblR = QLabel(EditPhaseWidget)
        self.lblR.setObjectName(u"lblR")

        self.phaseForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblR)

        self.phase_R = QLineEdit(EditPhaseWidget)
        self.phase_R.setObjectName(u"phase_R")
        self.phase_R.setReadOnly(True)

        self.phaseForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.phase_R)

        self.lblSigmaStar = QLabel(EditPhaseWidget)
        self.lblSigmaStar.setObjectName(u"lblSigmaStar")

        self.phaseForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lblSigmaStar)

        self.sigmaStarRow = QHBoxLayout()
        self.sigmaStarRow.setObjectName(u"sigmaStarRow")
        self.phase_sigma_star = QDoubleSpinBox(EditPhaseWidget)
        self.phase_sigma_star.setObjectName(u"phase_sigma_star")
        self.phase_sigma_star.setDecimals(2)
        self.phase_sigma_star.setMaximum(90.000000000000000)
        self.phase_sigma_star.setSingleStep(0.100000000000000)
        self.phase_sigma_star.setValue(3.000000000000000)

        self.sigmaStarRow.addWidget(self.phase_sigma_star)

        self.phase_inherit_sigma_star = QCheckBox(EditPhaseWidget)
        self.phase_inherit_sigma_star.setObjectName(u"phase_inherit_sigma_star")

        self.sigmaStarRow.addWidget(self.phase_inherit_sigma_star)


        self.phaseForm.setLayout(4, QFormLayout.ItemRole.FieldRole, self.sigmaStarRow)


        self.phaseLayout.addLayout(self.phaseForm)

        self.baselineRow = QHBoxLayout()
        self.baselineRow.setObjectName(u"baselineRow")
        self.btn_set_baseline = QPushButton(EditPhaseWidget)
        self.btn_set_baseline.setObjectName(u"btn_set_baseline")

        self.baselineRow.addWidget(self.btn_set_baseline)

        self.lbl_baseline = QLabel(EditPhaseWidget)
        self.lbl_baseline.setObjectName(u"lbl_baseline")
        self.lbl_baseline.setWordWrap(True)

        self.baselineRow.addWidget(self.lbl_baseline)


        self.phaseLayout.addLayout(self.baselineRow)

        self.book_wrapper = QTabWidget(EditPhaseWidget)
        self.book_wrapper.setObjectName(u"book_wrapper")
        self.tabCSDS = QWidget()
        self.tabCSDS.setObjectName(u"tabCSDS")
        self.csdsTabLayout = QVBoxLayout(self.tabCSDS)
        self.csdsTabLayout.setObjectName(u"csdsTabLayout")
        self.phase_inherit_CSDS_distribution = QCheckBox(self.tabCSDS)
        self.phase_inherit_CSDS_distribution.setObjectName(u"phase_inherit_CSDS_distribution")

        self.csdsTabLayout.addWidget(self.phase_inherit_CSDS_distribution)

        self.csdsLayout = QVBoxLayout()
        self.csdsLayout.setObjectName(u"csdsLayout")

        self.csdsTabLayout.addLayout(self.csdsLayout)

        self.lblCsdsPlaceholder = QLabel(self.tabCSDS)
        self.lblCsdsPlaceholder.setObjectName(u"lblCsdsPlaceholder")
        self.lblCsdsPlaceholder.setEnabled(False)
        self.lblCsdsPlaceholder.setAlignment(Qt.AlignCenter)

        self.csdsTabLayout.addWidget(self.lblCsdsPlaceholder)

        self.csdsSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.csdsTabLayout.addItem(self.csdsSpacer)

        self.book_wrapper.addTab(self.tabCSDS, "")
        self.tabProbabilities = QWidget()
        self.tabProbabilities.setObjectName(u"tabProbabilities")
        self.probabilitiesTabLayout = QVBoxLayout(self.tabProbabilities)
        self.probabilitiesTabLayout.setObjectName(u"probabilitiesTabLayout")
        self.probabilitiesLayout = QVBoxLayout()
        self.probabilitiesLayout.setObjectName(u"probabilitiesLayout")

        self.probabilitiesTabLayout.addLayout(self.probabilitiesLayout)

        self.lblProbabilitiesPlaceholder = QLabel(self.tabProbabilities)
        self.lblProbabilitiesPlaceholder.setObjectName(u"lblProbabilitiesPlaceholder")
        self.lblProbabilitiesPlaceholder.setEnabled(False)
        self.lblProbabilitiesPlaceholder.setAlignment(Qt.AlignCenter)

        self.probabilitiesTabLayout.addWidget(self.lblProbabilitiesPlaceholder)

        self.probabilitiesSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.probabilitiesTabLayout.addItem(self.probabilitiesSpacer)

        self.book_wrapper.addTab(self.tabProbabilities, "")
        self.tabComponents = QWidget()
        self.tabComponents.setObjectName(u"tabComponents")
        self.componentsTabLayout = QVBoxLayout(self.tabComponents)
        self.componentsTabLayout.setObjectName(u"componentsTabLayout")
        self.componentsLayout = QVBoxLayout()
        self.componentsLayout.setObjectName(u"componentsLayout")

        self.componentsTabLayout.addLayout(self.componentsLayout)

        self.lblComponentsPlaceholder = QLabel(self.tabComponents)
        self.lblComponentsPlaceholder.setObjectName(u"lblComponentsPlaceholder")
        self.lblComponentsPlaceholder.setEnabled(False)
        self.lblComponentsPlaceholder.setAlignment(Qt.AlignCenter)

        self.componentsTabLayout.addWidget(self.lblComponentsPlaceholder)

        self.componentsSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.componentsTabLayout.addItem(self.componentsSpacer)

        self.book_wrapper.addTab(self.tabComponents, "")

        self.phaseLayout.addWidget(self.book_wrapper)


        self.retranslateUi(EditPhaseWidget)

        self.book_wrapper.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(EditPhaseWidget)
    # setupUi

    def retranslateUi(self, EditPhaseWidget):
        self.lblPhaseName.setText(QCoreApplication.translate("EditPhaseWidget", u"Name & colour", None))
        self.phase_display_color.setText(QCoreApplication.translate("EditPhaseWidget", u"#808080", None))
#if QT_CONFIG(tooltip)
        self.phase_inherit_display_color.setToolTip(QCoreApplication.translate("EditPhaseWidget", u"Inherit the colour from the \"based on\" phase.", None))
#endif // QT_CONFIG(tooltip)
        self.phase_inherit_display_color.setText(QCoreApplication.translate("EditPhaseWidget", u"Inherit", None))
        self.lblBasedOn.setText(QCoreApplication.translate("EditPhaseWidget", u"Based on phase", None))
        self.phase_based_on.setItemText(0, QCoreApplication.translate("EditPhaseWidget", u"None", None))

        self.lblG.setText(QCoreApplication.translate("EditPhaseWidget", u"Nr. of components", None))
#if QT_CONFIG(tooltip)
        self.phase_G.setToolTip(QCoreApplication.translate("EditPhaseWidget", u"Fixed when the phase is created.", None))
#endif // QT_CONFIG(tooltip)
        self.lblR.setText(QCoreApplication.translate("EditPhaseWidget", u"Reichweite", None))
#if QT_CONFIG(tooltip)
        self.phase_R.setToolTip(QCoreApplication.translate("EditPhaseWidget", u"Fixed when the phase is created.", None))
#endif // QT_CONFIG(tooltip)
        self.lblSigmaStar.setText(QCoreApplication.translate("EditPhaseWidget", u"\u03c3* [\u00b0]", None))
#if QT_CONFIG(tooltip)
        self.phase_inherit_sigma_star.setToolTip(QCoreApplication.translate("EditPhaseWidget", u"Inherit the value from the \"based on\" phase.", None))
#endif // QT_CONFIG(tooltip)
        self.phase_inherit_sigma_star.setText(QCoreApplication.translate("EditPhaseWidget", u"Inherit", None))
        self.btn_set_baseline.setText(QCoreApplication.translate("EditPhaseWidget", u"Set as baseline", None))
#if QT_CONFIG(tooltip)
        self.btn_set_baseline.setToolTip(QCoreApplication.translate("EditPhaseWidget", u"Record this phase's CURRENT state as the baseline it is compared against in the Composition view. Everything already done to the phase becomes part of that baseline, so use it when the phase is as you want to start from - typically just after building it, before refining.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_baseline.setText("")
#if QT_CONFIG(tooltip)
        self.phase_inherit_CSDS_distribution.setToolTip(QCoreApplication.translate("EditPhaseWidget", u"Inherit the CSDS distribution from the \"based on\" phase.", None))
#endif // QT_CONFIG(tooltip)
        self.phase_inherit_CSDS_distribution.setText(QCoreApplication.translate("EditPhaseWidget", u"Inherit from the \"based on\" phase", None))
        self.lblCsdsPlaceholder.setText(QCoreApplication.translate("EditPhaseWidget", u"The CSDS distribution component (csds.ui) will be inserted here.", None))
        self.book_wrapper.setTabText(self.book_wrapper.indexOf(self.tabCSDS), QCoreApplication.translate("EditPhaseWidget", u"CSDS Distribution", None))
        self.lblProbabilitiesPlaceholder.setText(QCoreApplication.translate("EditPhaseWidget", u"The probabilities component (probabilities.ui) will be inserted here.", None))
        self.book_wrapper.setTabText(self.book_wrapper.indexOf(self.tabProbabilities), QCoreApplication.translate("EditPhaseWidget", u"Probabilities && weight fractions", None))
        self.lblComponentsPlaceholder.setText(QCoreApplication.translate("EditPhaseWidget", u"The component editor (edit_component.ui) will be inserted here.", None))
        self.book_wrapper.setTabText(self.book_wrapper.indexOf(self.tabComponents), QCoreApplication.translate("EditPhaseWidget", u"Components", None))
        pass
    # retranslateUi

