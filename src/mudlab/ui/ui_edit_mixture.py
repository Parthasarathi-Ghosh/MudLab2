# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_mixture.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_EditMixtureWidget(object):
    def setupUi(self, EditMixtureWidget):
        if not EditMixtureWidget.objectName():
            EditMixtureWidget.setObjectName(u"EditMixtureWidget")
        self.mixtureLayout = QVBoxLayout(EditMixtureWidget)
        self.mixtureLayout.setObjectName(u"mixtureLayout")
        self.mixtureForm = QFormLayout()
        self.mixtureForm.setObjectName(u"mixtureForm")
        self.lblMixtureName = QLabel(EditMixtureWidget)
        self.lblMixtureName.setObjectName(u"lblMixtureName")

        self.mixtureForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblMixtureName)

        self.mixture_name = QLineEdit(EditMixtureWidget)
        self.mixture_name.setObjectName(u"mixture_name")

        self.mixtureForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.mixture_name)


        self.mixtureLayout.addLayout(self.mixtureForm)

        self.actionsRow = QHBoxLayout()
        self.actionsRow.setObjectName(u"actionsRow")
        self.mixture_auto_run = QCheckBox(EditMixtureWidget)
        self.mixture_auto_run.setObjectName(u"mixture_auto_run")

        self.actionsRow.addWidget(self.mixture_auto_run)

        self.actionsSpacer = QSpacerItem(0, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.actionsRow.addItem(self.actionsSpacer)

        self.btn_composition = QPushButton(EditMixtureWidget)
        self.btn_composition.setObjectName(u"btn_composition")

        self.actionsRow.addWidget(self.btn_composition)

        self.btn_refine = QPushButton(EditMixtureWidget)
        self.btn_refine.setObjectName(u"btn_refine")

        self.actionsRow.addWidget(self.btn_refine)

        self.btn_optimize = QPushButton(EditMixtureWidget)
        self.btn_optimize.setObjectName(u"btn_optimize")

        self.actionsRow.addWidget(self.btn_optimize)


        self.mixtureLayout.addLayout(self.actionsRow)

        self.tbl_matrix = QTableWidget(EditMixtureWidget)
        self.tbl_matrix.setObjectName(u"tbl_matrix")
        self.tbl_matrix.setAlternatingRowColors(True)
        self.tbl_matrix.setSelectionMode(QAbstractItemView.NoSelection)

        self.mixtureLayout.addWidget(self.tbl_matrix)

        self.matrixButtons = QHBoxLayout()
        self.matrixButtons.setObjectName(u"matrixButtons")
        self.btn_add_phase = QPushButton(EditMixtureWidget)
        self.btn_add_phase.setObjectName(u"btn_add_phase")

        self.matrixButtons.addWidget(self.btn_add_phase)

        self.btn_add_specimen = QPushButton(EditMixtureWidget)
        self.btn_add_specimen.setObjectName(u"btn_add_specimen")

        self.matrixButtons.addWidget(self.btn_add_specimen)

        self.btn_add_both = QPushButton(EditMixtureWidget)
        self.btn_add_both.setObjectName(u"btn_add_both")

        self.matrixButtons.addWidget(self.btn_add_both)

        self.matrixBtnSpacer = QSpacerItem(0, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.matrixButtons.addItem(self.matrixBtnSpacer)


        self.mixtureLayout.addLayout(self.matrixButtons)

        self.mixture_auto_scales = QCheckBox(EditMixtureWidget)
        self.mixture_auto_scales.setObjectName(u"mixture_auto_scales")

        self.mixtureLayout.addWidget(self.mixture_auto_scales)

        self.mixture_auto_bg = QCheckBox(EditMixtureWidget)
        self.mixture_auto_bg.setObjectName(u"mixture_auto_bg")

        self.mixtureLayout.addWidget(self.mixture_auto_bg)


        self.retranslateUi(EditMixtureWidget)

        QMetaObject.connectSlotsByName(EditMixtureWidget)
    # setupUi

    def retranslateUi(self, EditMixtureWidget):
        self.lblMixtureName.setText(QCoreApplication.translate("EditMixtureWidget", u"Mixture name", None))
#if QT_CONFIG(tooltip)
        self.mixture_auto_run.setToolTip(QCoreApplication.translate("EditMixtureWidget", u"Run automatically when patterns have updated.", None))
#endif // QT_CONFIG(tooltip)
        self.mixture_auto_run.setText(QCoreApplication.translate("EditMixtureWidget", u"Auto run", None))
#if QT_CONFIG(tooltip)
        self.btn_composition.setToolTip(QCoreApplication.translate("EditMixtureWidget", u"Show the chemical composition of this mixture.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_composition.setText(QCoreApplication.translate("EditMixtureWidget", u"Composition", None))
#if QT_CONFIG(tooltip)
        self.btn_refine.setToolTip(QCoreApplication.translate("EditMixtureWidget", u"Refine the mixture parameters.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_refine.setText(QCoreApplication.translate("EditMixtureWidget", u"Refine", None))
#if QT_CONFIG(tooltip)
        self.btn_optimize.setToolTip(QCoreApplication.translate("EditMixtureWidget", u"Optimize fractions, scales and background shifts.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_optimize.setText(QCoreApplication.translate("EditMixtureWidget", u"Optimize", None))
#if QT_CONFIG(tooltip)
        self.btn_add_phase.setToolTip(QCoreApplication.translate("EditMixtureWidget", u"Add a phase row to this mixture", None))
#endif // QT_CONFIG(tooltip)
        self.btn_add_phase.setText(QCoreApplication.translate("EditMixtureWidget", u"Add phase", None))
#if QT_CONFIG(tooltip)
        self.btn_add_specimen.setToolTip(QCoreApplication.translate("EditMixtureWidget", u"Add a specimen column to this mixture", None))
#endif // QT_CONFIG(tooltip)
        self.btn_add_specimen.setText(QCoreApplication.translate("EditMixtureWidget", u"Add specimen", None))
#if QT_CONFIG(tooltip)
        self.btn_add_both.setToolTip(QCoreApplication.translate("EditMixtureWidget", u"Add a phase row and a specimen column to this mixture", None))
#endif // QT_CONFIG(tooltip)
        self.btn_add_both.setText(QCoreApplication.translate("EditMixtureWidget", u"Add both", None))
#if QT_CONFIG(tooltip)
        self.mixture_auto_scales.setToolTip(QCoreApplication.translate("EditMixtureWidget", u"Automatically optimize the absolute scales.", None))
#endif // QT_CONFIG(tooltip)
        self.mixture_auto_scales.setText(QCoreApplication.translate("EditMixtureWidget", u"Auto-adjust absolute scales", None))
#if QT_CONFIG(tooltip)
        self.mixture_auto_bg.setToolTip(QCoreApplication.translate("EditMixtureWidget", u"Automatically optimize the background shifts.", None))
#endif // QT_CONFIG(tooltip)
        self.mixture_auto_bg.setText(QCoreApplication.translate("EditMixtureWidget", u"Auto-adjust background shifts", None))
        pass
    # retranslateUi

