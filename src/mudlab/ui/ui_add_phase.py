# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_phase.ui'
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
    QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QSizePolicy, QSpacerItem,
    QSpinBox, QVBoxLayout, QWidget)

class Ui_AddPhaseDialog(object):
    def setupUi(self, AddPhaseDialog):
        if not AddPhaseDialog.objectName():
            AddPhaseDialog.setObjectName(u"AddPhaseDialog")
        AddPhaseDialog.resize(420, 320)
        self.dialogLayout = QVBoxLayout(AddPhaseDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.rdb_empty_phase = QRadioButton(AddPhaseDialog)
        self.rdb_empty_phase.setObjectName(u"rdb_empty_phase")
        self.rdb_empty_phase.setChecked(True)

        self.dialogLayout.addWidget(self.rdb_empty_phase)

        self.cont_empty_phase = QWidget(AddPhaseDialog)
        self.cont_empty_phase.setObjectName(u"cont_empty_phase")
        self.emptyPhaseForm = QFormLayout(self.cont_empty_phase)
        self.emptyPhaseForm.setObjectName(u"emptyPhaseForm")
        self.emptyPhaseForm.setContentsMargins(24, -1, -1, -1)
        self.lbl_N = QLabel(self.cont_empty_phase)
        self.lbl_N.setObjectName(u"lbl_N")

        self.emptyPhaseForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_N)

        self.G = QSpinBox(self.cont_empty_phase)
        self.G.setObjectName(u"G")
        self.G.setMinimum(1)
        self.G.setMaximum(6)

        self.emptyPhaseForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.G)

        self.lbl_reichweite = QLabel(self.cont_empty_phase)
        self.lbl_reichweite.setObjectName(u"lbl_reichweite")

        self.emptyPhaseForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_reichweite)

        self.R = QSpinBox(self.cont_empty_phase)
        self.R.setObjectName(u"R")
        self.R.setMaximum(4)

        self.emptyPhaseForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.R)


        self.dialogLayout.addWidget(self.cont_empty_phase)

        self.rdb_default_phase = QRadioButton(AddPhaseDialog)
        self.rdb_default_phase.setObjectName(u"rdb_default_phase")

        self.dialogLayout.addWidget(self.rdb_default_phase)

        self.cont_default_phase = QWidget(AddPhaseDialog)
        self.cont_default_phase.setObjectName(u"cont_default_phase")
        self.cont_default_phase.setEnabled(False)
        self.defaultPhaseRow = QHBoxLayout(self.cont_default_phase)
        self.defaultPhaseRow.setObjectName(u"defaultPhaseRow")
        self.defaultPhaseRow.setContentsMargins(24, -1, -1, -1)
        self.cmb_default_phases = QComboBox(self.cont_default_phase)
        self.cmb_default_phases.setObjectName(u"cmb_default_phases")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cmb_default_phases.sizePolicy().hasHeightForWidth())
        self.cmb_default_phases.setSizePolicy(sizePolicy)

        self.defaultPhaseRow.addWidget(self.cmb_default_phases)

        self.btn_generate_phases = QPushButton(self.cont_default_phase)
        self.btn_generate_phases.setObjectName(u"btn_generate_phases")

        self.defaultPhaseRow.addWidget(self.btn_generate_phases)


        self.dialogLayout.addWidget(self.cont_default_phase)

        self.rdb_raw_pattern = QRadioButton(AddPhaseDialog)
        self.rdb_raw_pattern.setObjectName(u"rdb_raw_pattern")

        self.dialogLayout.addWidget(self.rdb_raw_pattern)

        self.dialogSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.dialogLayout.addItem(self.dialogSpacer)

        self.buttonBox = QDialogButtonBox(AddPhaseDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(AddPhaseDialog)

        QMetaObject.connectSlotsByName(AddPhaseDialog)
    # setupUi

    def retranslateUi(self, AddPhaseDialog):
        AddPhaseDialog.setWindowTitle(QCoreApplication.translate("AddPhaseDialog", u"Add Phase", None))
        self.rdb_empty_phase.setText(QCoreApplication.translate("AddPhaseDialog", u"Create a new phase:", None))
        self.lbl_N.setText(QCoreApplication.translate("AddPhaseDialog", u"# of components", None))
        self.lbl_reichweite.setText(QCoreApplication.translate("AddPhaseDialog", u"Reichweite", None))
        self.rdb_default_phase.setText(QCoreApplication.translate("AddPhaseDialog", u"Choose a default phase:", None))
#if QT_CONFIG(tooltip)
        self.btn_generate_phases.setToolTip(QCoreApplication.translate("AddPhaseDialog", u"Regenerate the default phases catalog.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_generate_phases.setText(QCoreApplication.translate("AddPhaseDialog", u"Generate", None))
        self.rdb_raw_pattern.setText(QCoreApplication.translate("AddPhaseDialog", u"Add a raw pattern", None))
    # retranslateUi

