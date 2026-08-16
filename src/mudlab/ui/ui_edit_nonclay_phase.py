# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_nonclay_phase.ui'
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
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_EditNonClayPhaseWidget(object):
    def setupUi(self, EditNonClayPhaseWidget):
        if not EditNonClayPhaseWidget.objectName():
            EditNonClayPhaseWidget.setObjectName(u"EditNonClayPhaseWidget")
        self.rootLayout = QVBoxLayout(EditNonClayPhaseWidget)
        self.rootLayout.setObjectName(u"rootLayout")
        self.topForm = QFormLayout()
        self.topForm.setObjectName(u"topForm")
        self.lbl_name = QLabel(EditNonClayPhaseWidget)
        self.lbl_name.setObjectName(u"lbl_name")

        self.topForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_name)

        self.nonclay_name = QLineEdit(EditNonClayPhaseWidget)
        self.nonclay_name.setObjectName(u"nonclay_name")

        self.topForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.nonclay_name)

        self.lbl_color = QLabel(EditNonClayPhaseWidget)
        self.lbl_color.setObjectName(u"lbl_color")

        self.topForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_color)

        self.button_color = QPushButton(EditNonClayPhaseWidget)
        self.button_color.setObjectName(u"button_color")

        self.topForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.button_color)

        self.lbl_info_caption = QLabel(EditNonClayPhaseWidget)
        self.lbl_info_caption.setObjectName(u"lbl_info_caption")

        self.topForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_info_caption)

        self.nonclay_pattern_info = QLabel(EditNonClayPhaseWidget)
        self.nonclay_pattern_info.setObjectName(u"nonclay_pattern_info")

        self.topForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.nonclay_pattern_info)

        self.lbl_fwhm = QLabel(EditNonClayPhaseWidget)
        self.lbl_fwhm.setObjectName(u"lbl_fwhm")

        self.topForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lbl_fwhm)

        self.fwhmRow = QHBoxLayout()
        self.fwhmRow.setObjectName(u"fwhmRow")
        self.spin_fwhm = QDoubleSpinBox(EditNonClayPhaseWidget)
        self.spin_fwhm.setObjectName(u"spin_fwhm")
        self.spin_fwhm.setDecimals(2)
        self.spin_fwhm.setMinimum(0.010000000000000)
        self.spin_fwhm.setMaximum(5.000000000000000)
        self.spin_fwhm.setSingleStep(0.050000000000000)
        self.spin_fwhm.setValue(0.100000000000000)

        self.fwhmRow.addWidget(self.spin_fwhm)

        self.button_calibrate = QPushButton(EditNonClayPhaseWidget)
        self.button_calibrate.setObjectName(u"button_calibrate")

        self.fwhmRow.addWidget(self.button_calibrate)


        self.topForm.setLayout(3, QFormLayout.ItemRole.FieldRole, self.fwhmRow)


        self.rootLayout.addLayout(self.topForm)

        self.grpComposition = QGroupBox(EditNonClayPhaseWidget)
        self.grpComposition.setObjectName(u"grpComposition")
        self.compositionLayout = QVBoxLayout(self.grpComposition)
        self.compositionLayout.setObjectName(u"compositionLayout")
        self.formulaRow = QHBoxLayout()
        self.formulaRow.setObjectName(u"formulaRow")
        self.edit_formula = QLineEdit(self.grpComposition)
        self.edit_formula.setObjectName(u"edit_formula")

        self.formulaRow.addWidget(self.edit_formula)

        self.button_formula = QPushButton(self.grpComposition)
        self.button_formula.setObjectName(u"button_formula")

        self.formulaRow.addWidget(self.button_formula)


        self.compositionLayout.addLayout(self.formulaRow)

        self.oxide_grid = QTableWidget(self.grpComposition)
        self.oxide_grid.setObjectName(u"oxide_grid")
        self.oxide_grid.setAlternatingRowColors(True)

        self.compositionLayout.addWidget(self.oxide_grid)

        self.sumRow = QHBoxLayout()
        self.sumRow.setObjectName(u"sumRow")
        self.lbl_sum = QLabel(self.grpComposition)
        self.lbl_sum.setObjectName(u"lbl_sum")

        self.sumRow.addWidget(self.lbl_sum)

        self.sumSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.sumRow.addItem(self.sumSpacer)

        self.button_normalize = QPushButton(self.grpComposition)
        self.button_normalize.setObjectName(u"button_normalize")

        self.sumRow.addWidget(self.button_normalize)


        self.compositionLayout.addLayout(self.sumRow)


        self.rootLayout.addWidget(self.grpComposition)

        self.grpPreview = QGroupBox(EditNonClayPhaseWidget)
        self.grpPreview.setObjectName(u"grpPreview")
        self.previewLayout = QVBoxLayout(self.grpPreview)
        self.previewLayout.setObjectName(u"previewLayout")

        self.rootLayout.addWidget(self.grpPreview)


        self.retranslateUi(EditNonClayPhaseWidget)

        QMetaObject.connectSlotsByName(EditNonClayPhaseWidget)
    # setupUi

    def retranslateUi(self, EditNonClayPhaseWidget):
        self.lbl_name.setText(QCoreApplication.translate("EditNonClayPhaseWidget", u"Name", None))
#if QT_CONFIG(tooltip)
        self.nonclay_name.setToolTip(QCoreApplication.translate("EditNonClayPhaseWidget", u"The name of this non-clay phase.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_color.setText(QCoreApplication.translate("EditNonClayPhaseWidget", u"Display colour", None))
        self.button_color.setText(QCoreApplication.translate("EditNonClayPhaseWidget", u"#1f77b4", None))
        self.lbl_info_caption.setText(QCoreApplication.translate("EditNonClayPhaseWidget", u"Pattern", None))
        self.nonclay_pattern_info.setText(QCoreApplication.translate("EditNonClayPhaseWidget", u"No pattern loaded.", None))
        self.lbl_fwhm.setText(QCoreApplication.translate("EditNonClayPhaseWidget", u"Peak FWHM", None))
#if QT_CONFIG(tooltip)
        self.spin_fwhm.setToolTip(QCoreApplication.translate("EditNonClayPhaseWidget", u"Peak width for the pattern computed from the structure (only for CIF-derived phases). Change it to match your instrument's real peak width; the pattern re-renders live.", None))
#endif // QT_CONFIG(tooltip)
        self.spin_fwhm.setSuffix(QCoreApplication.translate("EditNonClayPhaseWidget", u" \u00b02\u03b8", None))
#if QT_CONFIG(tooltip)
        self.button_calibrate.setToolTip(QCoreApplication.translate("EditNonClayPhaseWidget", u"Fit the FWHM from a measured standard (e.g. Silicon).", None))
#endif // QT_CONFIG(tooltip)
        self.button_calibrate.setText(QCoreApplication.translate("EditNonClayPhaseWidget", u"Calibrate\u2026", None))
        self.grpComposition.setTitle(QCoreApplication.translate("EditNonClayPhaseWidget", u"Oxide composition (wt %)", None))
#if QT_CONFIG(tooltip)
        self.edit_formula.setToolTip(QCoreApplication.translate("EditNonClayPhaseWidget", u"Type a chemical formula (e.g. NaAlSi3O8, CaCO3) to fill the oxides. Only Si/Al/Fe/Ca/Mg/Na/K map to the reported oxides.", None))
#endif // QT_CONFIG(tooltip)
        self.edit_formula.setPlaceholderText(QCoreApplication.translate("EditNonClayPhaseWidget", u"Formula, e.g. NaAlSi3O8", None))
        self.button_formula.setText(QCoreApplication.translate("EditNonClayPhaseWidget", u"Fill from formula", None))
        self.lbl_sum.setText(QCoreApplication.translate("EditNonClayPhaseWidget", u"Sum: 0.00 %", None))
        self.button_normalize.setText(QCoreApplication.translate("EditNonClayPhaseWidget", u"Normalize to 100 %", None))
        self.grpPreview.setTitle(QCoreApplication.translate("EditNonClayPhaseWidget", u"Pattern preview", None))
        pass
    # retranslateUi

