# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'find_peaks_dialog.ui'
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
    QDialogButtonBox, QDoubleSpinBox, QFormLayout, QFrame,
    QLabel, QSizePolicy, QSpinBox, QVBoxLayout,
    QWidget)

class Ui_DetectPeaksDialog(object):
    def setupUi(self, DetectPeaksDialog):
        if not DetectPeaksDialog.objectName():
            DetectPeaksDialog.setObjectName(u"DetectPeaksDialog")
        DetectPeaksDialog.resize(560, 460)
        self.dialogLayout = QVBoxLayout(DetectPeaksDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.topForm = QFormLayout()
        self.topForm.setObjectName(u"topForm")
        self.lbl_pattern = QLabel(DetectPeaksDialog)
        self.lbl_pattern.setObjectName(u"lbl_pattern")

        self.topForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_pattern)

        self.pattern = QComboBox(DetectPeaksDialog)
        self.pattern.addItem("")
        self.pattern.addItem("")
        self.pattern.setObjectName(u"pattern")

        self.topForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.pattern)

        self.lbl_algorithm = QLabel(DetectPeaksDialog)
        self.lbl_algorithm.setObjectName(u"lbl_algorithm")

        self.topForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_algorithm)

        self.algorithm = QComboBox(DetectPeaksDialog)
        self.algorithm.addItem("")
        self.algorithm.setObjectName(u"algorithm")

        self.topForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.algorithm)


        self.dialogLayout.addLayout(self.topForm)

        self.hseparator1 = QFrame(DetectPeaksDialog)
        self.hseparator1.setObjectName(u"hseparator1")
        self.hseparator1.setFrameShape(QFrame.Shape.HLine)
        self.hseparator1.setFrameShadow(QFrame.Shadow.Sunken)

        self.dialogLayout.addWidget(self.hseparator1)

        self.lbl_selection = QLabel(DetectPeaksDialog)
        self.lbl_selection.setObjectName(u"lbl_selection")

        self.dialogLayout.addWidget(self.lbl_selection)

        self.graphLayout = QVBoxLayout()
        self.graphLayout.setObjectName(u"graphLayout")

        self.dialogLayout.addLayout(self.graphLayout)

        self.bottomForm = QFormLayout()
        self.bottomForm.setObjectName(u"bottomForm")
        self.lbl_max_thold = QLabel(DetectPeaksDialog)
        self.lbl_max_thold.setObjectName(u"lbl_max_thold")

        self.bottomForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_max_thold)

        self.max_threshold = QDoubleSpinBox(DetectPeaksDialog)
        self.max_threshold.setObjectName(u"max_threshold")
        self.max_threshold.setDecimals(2)
        self.max_threshold.setMaximum(1000000.000000000000000)

        self.bottomForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.max_threshold)

        self.lbl_stps = QLabel(DetectPeaksDialog)
        self.lbl_stps.setObjectName(u"lbl_stps")

        self.bottomForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_stps)

        self.spin_steps = QSpinBox(DetectPeaksDialog)
        self.spin_steps.setObjectName(u"spin_steps")
        self.spin_steps.setMinimum(1)
        self.spin_steps.setMaximum(10000)
        self.spin_steps.setValue(100)

        self.bottomForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.spin_steps)

        self.lbl_peaks = QLabel(DetectPeaksDialog)
        self.lbl_peaks.setObjectName(u"lbl_peaks")

        self.bottomForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_peaks)

        self.spin_sel_num_peaks = QSpinBox(DetectPeaksDialog)
        self.spin_sel_num_peaks.setObjectName(u"spin_sel_num_peaks")
        self.spin_sel_num_peaks.setMaximum(10000)

        self.bottomForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.spin_sel_num_peaks)

        self.lbl_thold = QLabel(DetectPeaksDialog)
        self.lbl_thold.setObjectName(u"lbl_thold")

        self.bottomForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lbl_thold)

        self.sel_threshold = QDoubleSpinBox(DetectPeaksDialog)
        self.sel_threshold.setObjectName(u"sel_threshold")
        self.sel_threshold.setDecimals(2)
        self.sel_threshold.setMaximum(1000000.000000000000000)

        self.bottomForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.sel_threshold)

        self.lbl_min_distance = QLabel(DetectPeaksDialog)
        self.lbl_min_distance.setObjectName(u"lbl_min_distance")
        self.lbl_min_distance.setVisible(False)

        self.bottomForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lbl_min_distance)

        self.min_distance = QDoubleSpinBox(DetectPeaksDialog)
        self.min_distance.setObjectName(u"min_distance")
        self.min_distance.setVisible(False)
        self.min_distance.setDecimals(2)
        self.min_distance.setMaximum(180.000000000000000)

        self.bottomForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.min_distance)


        self.dialogLayout.addLayout(self.bottomForm)

        self.buttonBox = QDialogButtonBox(DetectPeaksDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(DetectPeaksDialog)

        QMetaObject.connectSlotsByName(DetectPeaksDialog)
    # setupUi

    def retranslateUi(self, DetectPeaksDialog):
        DetectPeaksDialog.setWindowTitle(QCoreApplication.translate("DetectPeaksDialog", u"Auto detect peaks", None))
        self.lbl_pattern.setText(QCoreApplication.translate("DetectPeaksDialog", u"Pattern", None))
        self.pattern.setItemText(0, QCoreApplication.translate("DetectPeaksDialog", u"Experimental", None))
        self.pattern.setItemText(1, QCoreApplication.translate("DetectPeaksDialog", u"Calculated", None))

        self.lbl_algorithm.setText(QCoreApplication.translate("DetectPeaksDialog", u"Algorithm", None))
        self.algorithm.setItemText(0, QCoreApplication.translate("DetectPeaksDialog", u"Threshold", None))

        self.lbl_selection.setText(QCoreApplication.translate("DetectPeaksDialog", u"Generate parameter histogram:", None))
        self.lbl_max_thold.setText(QCoreApplication.translate("DetectPeaksDialog", u"Maximum", None))
        self.lbl_stps.setText(QCoreApplication.translate("DetectPeaksDialog", u"Steps", None))
        self.lbl_peaks.setText(QCoreApplication.translate("DetectPeaksDialog", u"# of peaks", None))
        self.lbl_thold.setText(QCoreApplication.translate("DetectPeaksDialog", u"Selected threshold:", None))
        self.lbl_min_distance.setText(QCoreApplication.translate("DetectPeaksDialog", u"Min. distance (\u00b02\u03b8)", None))
    # retranslateUi

