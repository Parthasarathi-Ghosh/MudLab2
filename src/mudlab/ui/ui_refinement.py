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
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_RefinementDialog(object):
    def setupUi(self, RefinementDialog):
        if not RefinementDialog.objectName():
            RefinementDialog.setObjectName(u"RefinementDialog")
        RefinementDialog.resize(640, 560)
        self.refinementLayout = QVBoxLayout(RefinementDialog)
        self.refinementLayout.setObjectName(u"refinementLayout")
        self.lblRefinables = QLabel(RefinementDialog)
        self.lblRefinables.setObjectName(u"lblRefinables")

        self.refinementLayout.addWidget(self.lblRefinables)

        self.tbl_refinables = QTableWidget(RefinementDialog)
        self.tbl_refinables.setObjectName(u"tbl_refinables")
        self.tbl_refinables.setAlternatingRowColors(True)
        self.tbl_refinables.setSelectionMode(QAbstractItemView.NoSelection)

        self.refinementLayout.addWidget(self.tbl_refinables)

        self.methodRow = QHBoxLayout()
        self.methodRow.setObjectName(u"methodRow")
        self.lblMethod = QLabel(RefinementDialog)
        self.lblMethod.setObjectName(u"lblMethod")

        self.methodRow.addWidget(self.lblMethod)

        self.cmb_method = QComboBox(RefinementDialog)
        self.cmb_method.setObjectName(u"cmb_method")

        self.methodRow.addWidget(self.cmb_method)

        self.btn_auto_restrict = QPushButton(RefinementDialog)
        self.btn_auto_restrict.setObjectName(u"btn_auto_restrict")

        self.methodRow.addWidget(self.btn_auto_restrict)

        self.btn_randomize = QPushButton(RefinementDialog)
        self.btn_randomize.setObjectName(u"btn_randomize")

        self.methodRow.addWidget(self.btn_randomize)


        self.refinementLayout.addLayout(self.methodRow)

        self.optionsLayout = QVBoxLayout()
        self.optionsLayout.setObjectName(u"optionsLayout")

        self.refinementLayout.addLayout(self.optionsLayout)

        self.refineRow = QHBoxLayout()
        self.refineRow.setObjectName(u"refineRow")
        self.lbl_status = QLabel(RefinementDialog)
        self.lbl_status.setObjectName(u"lbl_status")

        self.refineRow.addWidget(self.lbl_status)

        self.refineSpacer = QSpacerItem(0, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.refineRow.addItem(self.refineSpacer)

        self.btn_refine = QPushButton(RefinementDialog)
        self.btn_refine.setObjectName(u"btn_refine")

        self.refineRow.addWidget(self.btn_refine)

        self.btn_cancel = QPushButton(RefinementDialog)
        self.btn_cancel.setObjectName(u"btn_cancel")
        self.btn_cancel.setEnabled(False)

        self.refineRow.addWidget(self.btn_cancel)


        self.refinementLayout.addLayout(self.refineRow)

        self.grpResult = QGroupBox(RefinementDialog)
        self.grpResult.setObjectName(u"grpResult")
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


        self.resultLayout.addLayout(self.residualForm)

        self.applyRow = QHBoxLayout()
        self.applyRow.setObjectName(u"applyRow")
        self.btn_apply_initial = QPushButton(self.grpResult)
        self.btn_apply_initial.setObjectName(u"btn_apply_initial")

        self.applyRow.addWidget(self.btn_apply_initial)

        self.btn_apply_best = QPushButton(self.grpResult)
        self.btn_apply_best.setObjectName(u"btn_apply_best")

        self.applyRow.addWidget(self.btn_apply_best)

        self.btn_apply_last = QPushButton(self.grpResult)
        self.btn_apply_last.setObjectName(u"btn_apply_last")

        self.applyRow.addWidget(self.btn_apply_last)


        self.resultLayout.addLayout(self.applyRow)


        self.refinementLayout.addWidget(self.grpResult)

        self.buttonBox = QDialogButtonBox(RefinementDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.refinementLayout.addWidget(self.buttonBox)


        self.retranslateUi(RefinementDialog)

        QMetaObject.connectSlotsByName(RefinementDialog)
    # setupUi

    def retranslateUi(self, RefinementDialog):
        RefinementDialog.setWindowTitle(QCoreApplication.translate("RefinementDialog", u"Refine mixture", None))
        self.lblRefinables.setText(QCoreApplication.translate("RefinementDialog", u"Tick \"Refine\" and set Min/Max for the parameters to refine:", None))
        self.lblMethod.setText(QCoreApplication.translate("RefinementDialog", u"Method", None))
#if QT_CONFIG(tooltip)
        self.btn_auto_restrict.setToolTip(QCoreApplication.translate("RefinementDialog", u"Set Min/Max to +/-20% of each flagged parameter's current value.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_auto_restrict.setText(QCoreApplication.translate("RefinementDialog", u"Auto-restrict", None))
#if QT_CONFIG(tooltip)
        self.btn_randomize.setToolTip(QCoreApplication.translate("RefinementDialog", u"Randomize each flagged parameter within its Min/Max.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_randomize.setText(QCoreApplication.translate("RefinementDialog", u"Randomize", None))
        self.lbl_status.setText("")
#if QT_CONFIG(tooltip)
        self.btn_refine.setToolTip(QCoreApplication.translate("RefinementDialog", u"Run the refinement on a background thread; the window stays responsive and Cancel keeps the best result so far.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_refine.setText(QCoreApplication.translate("RefinementDialog", u"Refine", None))
#if QT_CONFIG(tooltip)
        self.btn_cancel.setToolTip(QCoreApplication.translate("RefinementDialog", u"Stop the running refinement and keep the best solution found so far.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_cancel.setText(QCoreApplication.translate("RefinementDialog", u"Cancel", None))
        self.grpResult.setTitle(QCoreApplication.translate("RefinementDialog", u"Result - which solution do you want to keep?", None))
        self.lblInitial.setText(QCoreApplication.translate("RefinementDialog", u"Initial residual (Rp)", None))
        self.lbl_initial_residual.setText(QCoreApplication.translate("RefinementDialog", u"-", None))
        self.lblBest.setText(QCoreApplication.translate("RefinementDialog", u"Best residual (Rp)", None))
        self.lbl_best_residual.setText(QCoreApplication.translate("RefinementDialog", u"-", None))
        self.lblLast.setText(QCoreApplication.translate("RefinementDialog", u"Last residual (Rp)", None))
        self.lbl_last_residual.setText(QCoreApplication.translate("RefinementDialog", u"-", None))
        self.btn_apply_initial.setText(QCoreApplication.translate("RefinementDialog", u"Keep initial", None))
        self.btn_apply_best.setText(QCoreApplication.translate("RefinementDialog", u"Keep best", None))
        self.btn_apply_last.setText(QCoreApplication.translate("RefinementDialog", u"Keep last", None))
    # retranslateUi

