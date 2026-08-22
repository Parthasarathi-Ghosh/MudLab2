# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'refinement.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QPlainTextEdit, QPushButton, QSizePolicy, QSpacerItem,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

class Ui_RefinementDialog(object):
    def setupUi(self, RefinementDialog):
        if not RefinementDialog.objectName():
            RefinementDialog.setObjectName(u"RefinementDialog")
        RefinementDialog.resize(1430, 720)
        RefinementDialog.setMinimumSize(QSize(1385, 580))
        RefinementDialog.setModal(True)
        self.refinementLayout = QVBoxLayout(RefinementDialog)
        self.refinementLayout.setObjectName(u"refinementLayout")
        self.framesRow = QHBoxLayout()
        self.framesRow.setSpacing(8)
        self.framesRow.setObjectName(u"framesRow")
        self.grpParameters = QGroupBox(RefinementDialog)
        self.grpParameters.setObjectName(u"grpParameters")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(4)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.grpParameters.sizePolicy().hasHeightForWidth())
        self.grpParameters.setSizePolicy(sizePolicy)
        self.parametersLayout = QVBoxLayout(self.grpParameters)
        self.parametersLayout.setObjectName(u"parametersLayout")
        self.refinablesHeaderRow = QHBoxLayout()
        self.refinablesHeaderRow.setObjectName(u"refinablesHeaderRow")
        self.lblRefinables = QLabel(self.grpParameters)
        self.lblRefinables.setObjectName(u"lblRefinables")
        self.lblRefinables.setWordWrap(True)

        self.refinablesHeaderRow.addWidget(self.lblRefinables)

        self.lbl_selected = QLabel(self.grpParameters)
        self.lbl_selected.setObjectName(u"lbl_selected")
        self.lbl_selected.setAlignment(Qt.AlignRight|Qt.AlignTop|Qt.AlignTrailing)

        self.refinablesHeaderRow.addWidget(self.lbl_selected)


        self.parametersLayout.addLayout(self.refinablesHeaderRow)

        self.tree_refinables = QTreeWidget(self.grpParameters)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1")
        self.tree_refinables.setHeaderItem(__qtreewidgetitem)
        self.tree_refinables.setObjectName(u"tree_refinables")
        self.tree_refinables.setMinimumSize(QSize(425, 0))
        self.tree_refinables.setAlternatingRowColors(True)
        self.tree_refinables.setSelectionMode(QAbstractItemView.NoSelection)
        self.tree_refinables.setTextElideMode(Qt.ElideRight)
        self.tree_refinables.setWordWrap(False)
        self.tree_refinables.setUniformRowHeights(True)
        self.tree_refinables.setAnimated(True)

        self.parametersLayout.addWidget(self.tree_refinables)

        self.lbl_param_warning = QLabel(self.grpParameters)
        self.lbl_param_warning.setObjectName(u"lbl_param_warning")
        self.lbl_param_warning.setWordWrap(True)

        self.parametersLayout.addWidget(self.lbl_param_warning)


        self.framesRow.addWidget(self.grpParameters)

        self.grpRefine = QGroupBox(RefinementDialog)
        self.grpRefine.setObjectName(u"grpRefine")
        sizePolicy.setHeightForWidth(self.grpRefine.sizePolicy().hasHeightForWidth())
        self.grpRefine.setSizePolicy(sizePolicy)
        self.refineFrameLayout = QVBoxLayout(self.grpRefine)
        self.refineFrameLayout.setObjectName(u"refineFrameLayout")
        self.methodRow = QHBoxLayout()
        self.methodRow.setObjectName(u"methodRow")
        self.lblMethod = QLabel(self.grpRefine)
        self.lblMethod.setObjectName(u"lblMethod")

        self.methodRow.addWidget(self.lblMethod)

        self.cmb_method = QComboBox(self.grpRefine)
        self.cmb_method.setObjectName(u"cmb_method")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.cmb_method.sizePolicy().hasHeightForWidth())
        self.cmb_method.setSizePolicy(sizePolicy1)

        self.methodRow.addWidget(self.cmb_method)

        self.btn_refine = QPushButton(self.grpRefine)
        self.btn_refine.setObjectName(u"btn_refine")

        self.methodRow.addWidget(self.btn_refine)

        self.btn_cancel = QPushButton(self.grpRefine)
        self.btn_cancel.setObjectName(u"btn_cancel")
        self.btn_cancel.setEnabled(False)

        self.methodRow.addWidget(self.btn_cancel)


        self.refineFrameLayout.addLayout(self.methodRow)

        self.optionsLayout = QVBoxLayout()
        self.optionsLayout.setObjectName(u"optionsLayout")

        self.refineFrameLayout.addLayout(self.optionsLayout)

        self.lbl_budget = QLabel(self.grpRefine)
        self.lbl_budget.setObjectName(u"lbl_budget")
        self.lbl_budget.setWordWrap(True)

        self.refineFrameLayout.addWidget(self.lbl_budget)

        self.grpProgress = QGroupBox(self.grpRefine)
        self.grpProgress.setObjectName(u"grpProgress")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(1)
        sizePolicy2.setHeightForWidth(self.grpProgress.sizePolicy().hasHeightForWidth())
        self.grpProgress.setSizePolicy(sizePolicy2)
        self.grpProgress.setMinimumSize(QSize(300, 200))
        self.progressLayout = QVBoxLayout(self.grpProgress)
        self.progressLayout.setObjectName(u"progressLayout")

        self.refineFrameLayout.addWidget(self.grpProgress)


        self.framesRow.addWidget(self.grpRefine)

        self.grpResult = QGroupBox(RefinementDialog)
        self.grpResult.setObjectName(u"grpResult")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(3)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.grpResult.sizePolicy().hasHeightForWidth())
        self.grpResult.setSizePolicy(sizePolicy3)
        self.grpResult.setMinimumSize(QSize(300, 0))
        self.resultLayout = QVBoxLayout(self.grpResult)
        self.resultLayout.setObjectName(u"resultLayout")
        self.residualForm = QFormLayout()
        self.residualForm.setObjectName(u"residualForm")
        self.lblInitial = QLabel(self.grpResult)
        self.lblInitial.setObjectName(u"lblInitial")

        self.residualForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblInitial)

        self.lbl_initial_residual = QLabel(self.grpResult)
        self.lbl_initial_residual.setObjectName(u"lbl_initial_residual")

        self.residualForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.lbl_initial_residual)

        self.lblBest = QLabel(self.grpResult)
        self.lblBest.setObjectName(u"lblBest")

        self.residualForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblBest)

        self.lbl_best_residual = QLabel(self.grpResult)
        self.lbl_best_residual.setObjectName(u"lbl_best_residual")

        self.residualForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.lbl_best_residual)

        self.lblLast = QLabel(self.grpResult)
        self.lblLast.setObjectName(u"lblLast")

        self.residualForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lblLast)

        self.lbl_last_residual = QLabel(self.grpResult)
        self.lbl_last_residual.setObjectName(u"lbl_last_residual")

        self.residualForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.lbl_last_residual)

        self.lblGoF = QLabel(self.grpResult)
        self.lblGoF.setObjectName(u"lblGoF")

        self.residualForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lblGoF)

        self.lbl_gof = QLabel(self.grpResult)
        self.lbl_gof.setObjectName(u"lbl_gof")

        self.residualForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.lbl_gof)


        self.resultLayout.addLayout(self.residualForm)

        self.resultSeparator = QFrame(self.grpResult)
        self.resultSeparator.setObjectName(u"resultSeparator")
        self.resultSeparator.setFrameShape(QFrame.Shape.HLine)
        self.resultSeparator.setFrameShadow(QFrame.Shadow.Sunken)

        self.resultLayout.addWidget(self.resultSeparator)

        self.lblKeepWhich = QLabel(self.grpResult)
        self.lblKeepWhich.setObjectName(u"lblKeepWhich")
        self.lblKeepWhich.setWordWrap(True)

        self.resultLayout.addWidget(self.lblKeepWhich)

        self.applyLayout = QHBoxLayout()
        self.applyLayout.setObjectName(u"applyLayout")
        self.btn_apply_initial = QPushButton(self.grpResult)
        self.btn_apply_initial.setObjectName(u"btn_apply_initial")

        self.applyLayout.addWidget(self.btn_apply_initial)

        self.btn_apply_best = QPushButton(self.grpResult)
        self.btn_apply_best.setObjectName(u"btn_apply_best")

        self.applyLayout.addWidget(self.btn_apply_best)

        self.btn_apply_last = QPushButton(self.grpResult)
        self.btn_apply_last.setObjectName(u"btn_apply_last")

        self.applyLayout.addWidget(self.btn_apply_last)


        self.resultLayout.addLayout(self.applyLayout)

        self.txt_report = QPlainTextEdit(self.grpResult)
        self.txt_report.setObjectName(u"txt_report")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(1)
        sizePolicy4.setHeightForWidth(self.txt_report.sizePolicy().hasHeightForWidth())
        self.txt_report.setSizePolicy(sizePolicy4)
        self.txt_report.setMinimumSize(QSize(0, 120))
        self.txt_report.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.txt_report.setReadOnly(True)

        self.resultLayout.addWidget(self.txt_report)


        self.framesRow.addWidget(self.grpResult)


        self.refinementLayout.addLayout(self.framesRow)

        self.bottomRow = QHBoxLayout()
        self.bottomRow.setObjectName(u"bottomRow")
        self.lbl_status = QLabel(RefinementDialog)
        self.lbl_status.setObjectName(u"lbl_status")

        self.bottomRow.addWidget(self.lbl_status)

        self.bottomSpacer = QSpacerItem(0, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.bottomRow.addItem(self.bottomSpacer)

        self.buttonBox = QDialogButtonBox(RefinementDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.bottomRow.addWidget(self.buttonBox)


        self.refinementLayout.addLayout(self.bottomRow)


        self.retranslateUi(RefinementDialog)

        self.btn_refine.setDefault(True)


        QMetaObject.connectSlotsByName(RefinementDialog)
    # setupUi

    def retranslateUi(self, RefinementDialog):
        RefinementDialog.setWindowTitle(QCoreApplication.translate("RefinementDialog", u"Refine mixture", None))
        self.grpParameters.setTitle(QCoreApplication.translate("RefinementDialog", u"1. Parameters to refine", None))
        self.lblRefinables.setText(QCoreApplication.translate("RefinementDialog", u"Tick \"Refine\" and set Min/Max for the parameters to refine:", None))
#if QT_CONFIG(tooltip)
        self.lbl_selected.setToolTip(QCoreApplication.translate("RefinementDialog", u"How many parameters are flagged for refinement. Every flagged parameter adds a dimension to the search, so this is what decides how long a run takes.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_selected.setText(QCoreApplication.translate("RefinementDialog", u"0 of 0 selected", None))
#if QT_CONFIG(tooltip)
        self.lbl_param_warning.setToolTip(QCoreApplication.translate("RefinementDialog", u"Problems with the current selection: parameters that will not be refined, values outside their own Min/Max, and values you have typed in by hand. It disappears when there is nothing to report.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_param_warning.setText("")
        self.grpRefine.setTitle(QCoreApplication.translate("RefinementDialog", u"2. Refinement", None))
        self.lblMethod.setText(QCoreApplication.translate("RefinementDialog", u"Method", None))
#if QT_CONFIG(tooltip)
        self.btn_refine.setToolTip(QCoreApplication.translate("RefinementDialog", u"Run the refinement on a background thread; Cancel keeps the best result so far.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_refine.setText(QCoreApplication.translate("RefinementDialog", u"Refine", None))
#if QT_CONFIG(tooltip)
        self.btn_cancel.setToolTip(QCoreApplication.translate("RefinementDialog", u"Stop the running refinement and keep the best solution found so far.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_cancel.setText(QCoreApplication.translate("RefinementDialog", u"Cancel", None))
#if QT_CONFIG(tooltip)
        self.lbl_budget.setToolTip(QCoreApplication.translate("RefinementDialog", u"How much work this run may do, for the current method, options and selection. L-BFGS-B has a hard cap; Basin Hopping runs that many LOCAL minimisations and does not cap each one.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_budget.setText("")
        self.grpProgress.setTitle(QCoreApplication.translate("RefinementDialog", u"Progress", None))
        self.grpResult.setTitle(QCoreApplication.translate("RefinementDialog", u"3. Result", None))
        self.lblInitial.setText(QCoreApplication.translate("RefinementDialog", u"Initial residual (Rp)", None))
        self.lbl_initial_residual.setText(QCoreApplication.translate("RefinementDialog", u"-", None))
        self.lblBest.setText(QCoreApplication.translate("RefinementDialog", u"Best residual (Rp)", None))
        self.lbl_best_residual.setText(QCoreApplication.translate("RefinementDialog", u"-", None))
        self.lblLast.setText(QCoreApplication.translate("RefinementDialog", u"Last residual (Rp)", None))
        self.lbl_last_residual.setText(QCoreApplication.translate("RefinementDialog", u"-", None))
#if QT_CONFIG(tooltip)
        self.lblGoF.setToolTip(QCoreApplication.translate("RefinementDialog", u"Goodness of fit of the best solution, averaged over the mixture's specimens.", None))
#endif // QT_CONFIG(tooltip)
        self.lblGoF.setText(QCoreApplication.translate("RefinementDialog", u"GoF (best solution)", None))
        self.lbl_gof.setText(QCoreApplication.translate("RefinementDialog", u"-", None))
        self.lblKeepWhich.setText(QCoreApplication.translate("RefinementDialog", u"Which solution do you want to keep?", None))
        self.btn_apply_initial.setText(QCoreApplication.translate("RefinementDialog", u"Initial", None))
        self.btn_apply_best.setText(QCoreApplication.translate("RefinementDialog", u"Best", None))
        self.btn_apply_last.setText(QCoreApplication.translate("RefinementDialog", u"Last", None))
#if QT_CONFIG(tooltip)
        self.txt_report.setToolTip(QCoreApplication.translate("RefinementDialog", u"Detailed report of the finished refinement. Rewritten when you keep a solution, so it always describes the one currently applied.", None))
#endif // QT_CONFIG(tooltip)
        self.txt_report.setPlaceholderText(QCoreApplication.translate("RefinementDialog", u"The refinement report appears here when a run finishes.", None))
        self.lbl_status.setText("")
    # retranslateUi

