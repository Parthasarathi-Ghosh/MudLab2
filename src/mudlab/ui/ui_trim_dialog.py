# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'trim_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_TrimDataDialog(object):
    def setupUi(self, TrimDataDialog):
        if not TrimDataDialog.objectName():
            TrimDataDialog.setObjectName(u"TrimDataDialog")
        self.dialogLayout = QVBoxLayout(TrimDataDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.lbl_irreversible = QLabel(TrimDataDialog)
        self.lbl_irreversible.setObjectName(u"lbl_irreversible")
        self.lbl_irreversible.setWordWrap(True)

        self.dialogLayout.addWidget(self.lbl_irreversible)

        self.trimForm = QFormLayout()
        self.trimForm.setObjectName(u"trimForm")
        self.lbl_scope = QLabel(TrimDataDialog)
        self.lbl_scope.setObjectName(u"lbl_scope")

        self.trimForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_scope)

        self.cmb_scope = QComboBox(TrimDataDialog)
        self.cmb_scope.addItem("")
        self.cmb_scope.addItem("")
        self.cmb_scope.setObjectName(u"cmb_scope")

        self.trimForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.cmb_scope)

        self.lbl_min_2theta = QLabel(TrimDataDialog)
        self.lbl_min_2theta.setObjectName(u"lbl_min_2theta")

        self.trimForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_min_2theta)

        self.spin_min_2theta = QDoubleSpinBox(TrimDataDialog)
        self.spin_min_2theta.setObjectName(u"spin_min_2theta")
        self.spin_min_2theta.setDecimals(2)
        self.spin_min_2theta.setMaximum(180.000000000000000)
        self.spin_min_2theta.setSingleStep(0.100000000000000)

        self.trimForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.spin_min_2theta)

        self.lbl_max_2theta = QLabel(TrimDataDialog)
        self.lbl_max_2theta.setObjectName(u"lbl_max_2theta")

        self.trimForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_max_2theta)

        self.spin_max_2theta = QDoubleSpinBox(TrimDataDialog)
        self.spin_max_2theta.setObjectName(u"spin_max_2theta")
        self.spin_max_2theta.setDecimals(2)
        self.spin_max_2theta.setMaximum(180.000000000000000)
        self.spin_max_2theta.setSingleStep(0.100000000000000)
        self.spin_max_2theta.setValue(180.000000000000000)

        self.trimForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.spin_max_2theta)


        self.dialogLayout.addLayout(self.trimForm)

        self.lbl_removal_warning = QLabel(TrimDataDialog)
        self.lbl_removal_warning.setObjectName(u"lbl_removal_warning")
        self.lbl_removal_warning.setVisible(False)
        self.lbl_removal_warning.setWordWrap(True)

        self.dialogLayout.addWidget(self.lbl_removal_warning)

        self.buttonBox = QDialogButtonBox(TrimDataDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(TrimDataDialog)

        QMetaObject.connectSlotsByName(TrimDataDialog)
    # setupUi

    def retranslateUi(self, TrimDataDialog):
        TrimDataDialog.setWindowTitle(QCoreApplication.translate("TrimDataDialog", u"Trim Data", None))
        self.lbl_irreversible.setText(QCoreApplication.translate("TrimDataDialog", u"\u26a0 This operation permanently modifies the data and cannot be undone.", None))
        self.lbl_scope.setText(QCoreApplication.translate("TrimDataDialog", u"Apply to", None))
        self.cmb_scope.setItemText(0, QCoreApplication.translate("TrimDataDialog", u"This specimen only", None))
        self.cmb_scope.setItemText(1, QCoreApplication.translate("TrimDataDialog", u"All loaded specimens", None))

        self.lbl_min_2theta.setText(QCoreApplication.translate("TrimDataDialog", u"Min \u00b02\u03b8", None))
        self.spin_min_2theta.setSuffix(QCoreApplication.translate("TrimDataDialog", u" \u00b0", None))
        self.lbl_max_2theta.setText(QCoreApplication.translate("TrimDataDialog", u"Max \u00b02\u03b8", None))
        self.spin_max_2theta.setSuffix(QCoreApplication.translate("TrimDataDialog", u" \u00b0", None))
        self.lbl_removal_warning.setText("")
    # retranslateUi

