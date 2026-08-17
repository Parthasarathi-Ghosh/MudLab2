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
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_RefinementDialog(object):
    def setupUi(self, RefinementDialog):
        if not RefinementDialog.objectName():
            RefinementDialog.setObjectName(u"RefinementDialog")
        RefinementDialog.resize(1440, 720)
        RefinementDialog.setMinimumSize(QSize(1350, 580))
        RefinementDialog.setModal(True)
        self.refinementLayout = QVBoxLayout(RefinementDialog)
        self.refinementLayout.setObjectName(u"refinementLayout")
        self.framesRow = QHBoxLayout()
        self.framesRow.setSpacing(8)
        self.framesRow.setObjectName(u"framesRow")
        self.grpParameters = QGroupBox(RefinementDialog)
        self.grpParameters.setObjectName(u"grpParameters")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(5)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.grpParameters.sizePolicy().hasHeightForWidth())
        self.grpParameters.setSizePolicy(sizePolicy)
        self.parametersLayout = QVBoxLayout(self.grpParameters)
        self.parametersLayout.setObjectName(u"parametersLayout")
        self.lblRefinables = QLabel(self.grpParameters)
        self.lblRefinables.setObjectName(u"lblRefinables")
        self.lblRefinables.setWordWrap(True)

        self.parametersLayout.addWidget(self.lblRefinables)

        self.tbl_refinables = QTableWidget(self.grpParameters)
        self.tbl_refinables.setObjectName(u"tbl_refinables")
        self.tbl_refinables.setMinimumSize(QSize(390, 0))
        self.tbl_refinables.setAlternatingRowColors(True)
        self.tbl_refinables.setSelectionMode(QAbstractItemView.NoSelection)
        self.tbl_refinables.setTextElideMode(Qt.ElideRight)
        self.tbl_refinables.setWordWrap(False)

        self.parametersLayout.addWidget(self.tbl_refinables)

        self.paramButtonRow = QHBoxLayout()
        self.paramButtonRow.setObjectName(u"paramButtonRow")
        self.btn_auto_restrict = QPushButton(self.grpParameters)
        self.btn_auto_restrict.setObjectName(u"btn_auto_restrict")

        self.paramButtonRow.addWidget(self.btn_auto_restrict)

        self.btn_randomize = QPushButton(self.grpParameters)
        self.btn_randomize.setObjectName(u"btn_randomize")

        self.paramButtonRow.addWidget(self.btn_randomize)

        self.paramButtonSpacer = QSpacerItem(0, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.paramButtonRow.addItem(self.paramButtonSpacer)


        self.parametersLayout.addLayout(self.paramButtonRow)


        self.framesRow.addWidget(self.grpParameters)

        self.grpRefine = QGroupBox(RefinementDialog)
        self.grpRefine.setObjectName(u"grpRefine")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(4)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.grpRefine.sizePolicy().hasHeightForWidth())
        self.grpRefine.setSizePolicy(sizePolicy1)
        self.refineFrameLayout = QVBoxLayout(self.grpRefine)
        self.refineFrameLayout.setObjectName(u"refineFrameLayout")
        self.methodRow = QHBoxLayout()
        self.methodRow.setObjectName(u"methodRow")
        self.lblMethod = QLabel(self.grpRefine)
        self.lblMethod.setObjectName(u"lblMethod")

        self.methodRow.addWidget(self.lblMethod)

        self.cmb_method = QComboBox(self.grpRefine)
        self.cmb_method.setObjectName(u"cmb_method")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(1)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.cmb_method.sizePolicy().hasHeightForWidth())
        self.cmb_method.setSizePolicy(sizePolicy2)

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

        self.grpProgress = QGroupBox(self.grpRefine)
        self.grpProgress.setObjectName(u"grpProgress")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(1)
        sizePolicy3.setHeightForWidth(self.grpProgress.sizePolicy().hasHeightForWidth())
        self.grpProgress.setSizePolicy(sizePolicy3)
        self.grpProgress.setMinimumSize(QSize(300, 200))
        self.progressLayout = QVBoxLayout(self.grpProgress)
        self.progressLayout.setObjectName(u"progressLayout")

        self.refineFrameLayout.addWidget(self.grpProgress)


        self.framesRow.addWidget(self.grpRefine)

        self.grpResult = QGroupBox(RefinementDialog)
        self.grpResult.setObjectName(u"grpResult")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(3)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.grpResult.sizePolicy().hasHeightForWidth())
        self.grpResult.setSizePolicy(sizePolicy4)
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

        self.applyLayout = QVBoxLayout()
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
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(1)
        sizePolicy5.setHeightForWidth(self.txt_report.sizePolicy().hasHeightForWidth())
        self.txt_report.setSizePolicy(sizePolicy5)
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
        self.btn_auto_restrict.setToolTip(QCoreApplication.translate("RefinementDialog", u"Set Min/Max to +/-20% of each flagged parameter's current value.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_auto_restrict.setText(QCoreApplication.translate("RefinementDialog", u"Auto-restrict", None))
#if QT_CONFIG(tooltip)
        self.btn_randomize.setToolTip(QCoreApplication.translate("RefinementDialog", u"Randomize each flagged parameter within its Min/Max.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_randomize.setText(QCoreApplication.translate("RefinementDialog", u"Randomize", None))
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

