# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'import_nonclay.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_ImportNonClayDialog(object):
    def setupUi(self, ImportNonClayDialog):
        if not ImportNonClayDialog.objectName():
            ImportNonClayDialog.setObjectName(u"ImportNonClayDialog")
        ImportNonClayDialog.setMinimumSize(QSize(620, 460))
        self.dialogLayout = QVBoxLayout(ImportNonClayDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.topForm = QFormLayout()
        self.topForm.setObjectName(u"topForm")
        self.lbl_name = QLabel(ImportNonClayDialog)
        self.lbl_name.setObjectName(u"lbl_name")

        self.topForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_name)

        self.edit_name = QLineEdit(ImportNonClayDialog)
        self.edit_name.setObjectName(u"edit_name")

        self.topForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.edit_name)

        self.lbl_color = QLabel(ImportNonClayDialog)
        self.lbl_color.setObjectName(u"lbl_color")

        self.topForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_color)

        self.button_color = QPushButton(ImportNonClayDialog)
        self.button_color.setObjectName(u"button_color")

        self.topForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.button_color)

        self.lbl_file = QLabel(ImportNonClayDialog)
        self.lbl_file.setObjectName(u"lbl_file")

        self.topForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_file)

        self.button_open_file = QPushButton(ImportNonClayDialog)
        self.button_open_file.setObjectName(u"button_open_file")

        self.topForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.button_open_file)

        self.lbl_source_caption = QLabel(ImportNonClayDialog)
        self.lbl_source_caption.setObjectName(u"lbl_source_caption")

        self.topForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lbl_source_caption)

        self.lbl_source = QLabel(ImportNonClayDialog)
        self.lbl_source.setObjectName(u"lbl_source")
        self.lbl_source.setWordWrap(True)

        self.topForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.lbl_source)

        self.lbl_fwhm = QLabel(ImportNonClayDialog)
        self.lbl_fwhm.setObjectName(u"lbl_fwhm")

        self.topForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lbl_fwhm)

        self.spin_fwhm = QDoubleSpinBox(ImportNonClayDialog)
        self.spin_fwhm.setObjectName(u"spin_fwhm")
        self.spin_fwhm.setDecimals(2)
        self.spin_fwhm.setMinimum(0.010000000000000)
        self.spin_fwhm.setMaximum(5.000000000000000)
        self.spin_fwhm.setSingleStep(0.050000000000000)
        self.spin_fwhm.setValue(0.100000000000000)

        self.topForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.spin_fwhm)


        self.dialogLayout.addLayout(self.topForm)

        self.grpBody = QGroupBox(ImportNonClayDialog)
        self.grpBody.setObjectName(u"grpBody")
        self.bodyLayout = QHBoxLayout(self.grpBody)
        self.bodyLayout.setObjectName(u"bodyLayout")
        self.gridColumn = QVBoxLayout()
        self.gridColumn.setObjectName(u"gridColumn")
        self.formulaRow = QHBoxLayout()
        self.formulaRow.setObjectName(u"formulaRow")
        self.edit_formula = QLineEdit(self.grpBody)
        self.edit_formula.setObjectName(u"edit_formula")

        self.formulaRow.addWidget(self.edit_formula)

        self.button_formula = QPushButton(self.grpBody)
        self.button_formula.setObjectName(u"button_formula")

        self.formulaRow.addWidget(self.button_formula)


        self.gridColumn.addLayout(self.formulaRow)

        self.oxide_grid = QTableWidget(self.grpBody)
        self.oxide_grid.setObjectName(u"oxide_grid")
        self.oxide_grid.setAlternatingRowColors(True)

        self.gridColumn.addWidget(self.oxide_grid)

        self.sumRow = QHBoxLayout()
        self.sumRow.setObjectName(u"sumRow")
        self.lbl_sum = QLabel(self.grpBody)
        self.lbl_sum.setObjectName(u"lbl_sum")

        self.sumRow.addWidget(self.lbl_sum)

        self.sumSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.sumRow.addItem(self.sumSpacer)

        self.button_normalize = QPushButton(self.grpBody)
        self.button_normalize.setObjectName(u"button_normalize")

        self.sumRow.addWidget(self.button_normalize)


        self.gridColumn.addLayout(self.sumRow)


        self.bodyLayout.addLayout(self.gridColumn)

        self.previewColumn = QVBoxLayout()
        self.previewColumn.setObjectName(u"previewColumn")
        self.lbl_preview = QLabel(self.grpBody)
        self.lbl_preview.setObjectName(u"lbl_preview")

        self.previewColumn.addWidget(self.lbl_preview)

        self.previewLayout = QVBoxLayout()
        self.previewLayout.setObjectName(u"previewLayout")

        self.previewColumn.addLayout(self.previewLayout)


        self.bodyLayout.addLayout(self.previewColumn)


        self.dialogLayout.addWidget(self.grpBody)

        self.buttonBox = QDialogButtonBox(ImportNonClayDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(ImportNonClayDialog)

        QMetaObject.connectSlotsByName(ImportNonClayDialog)
    # setupUi

    def retranslateUi(self, ImportNonClayDialog):
        ImportNonClayDialog.setWindowTitle(QCoreApplication.translate("ImportNonClayDialog", u"Import non-clay phase", None))
        self.lbl_name.setText(QCoreApplication.translate("ImportNonClayDialog", u"Phase name", None))
        self.edit_name.setPlaceholderText(QCoreApplication.translate("ImportNonClayDialog", u"e.g. Quartz", None))
        self.lbl_color.setText(QCoreApplication.translate("ImportNonClayDialog", u"Display colour", None))
#if QT_CONFIG(tooltip)
        self.button_color.setToolTip(QCoreApplication.translate("ImportNonClayDialog", u"Colour used for this phase's curve on the plot.", None))
#endif // QT_CONFIG(tooltip)
        self.button_color.setText(QCoreApplication.translate("ImportNonClayDialog", u"#1f77b4", None))
        self.lbl_file.setText(QCoreApplication.translate("ImportNonClayDialog", u"Pattern / structure", None))
#if QT_CONFIG(tooltip)
        self.button_open_file.setToolTip(QCoreApplication.translate("ImportNonClayDialog", u"A measured pattern (.xy/.txt/.csv/.xrdml/.uxd/.raw/.rasx) - enter oxides by hand; or a CIF with atoms - the pattern and oxides are computed for you.", None))
#endif // QT_CONFIG(tooltip)
        self.button_open_file.setText(QCoreApplication.translate("ImportNonClayDialog", u"Open file\u2026", None))
        self.lbl_source_caption.setText(QCoreApplication.translate("ImportNonClayDialog", u"Source", None))
        self.lbl_source.setText(QCoreApplication.translate("ImportNonClayDialog", u"No file loaded.", None))
        self.lbl_fwhm.setText(QCoreApplication.translate("ImportNonClayDialog", u"CIF peak FWHM", None))
#if QT_CONFIG(tooltip)
        self.spin_fwhm.setToolTip(QCoreApplication.translate("ImportNonClayDialog", u"Peak width used when a pattern is computed from a CIF (ignored for a measured pattern).", None))
#endif // QT_CONFIG(tooltip)
        self.spin_fwhm.setSuffix(QCoreApplication.translate("ImportNonClayDialog", u" \u00b02\u03b8", None))
        self.grpBody.setTitle(QCoreApplication.translate("ImportNonClayDialog", u"Oxide composition (wt %) and pattern preview", None))
#if QT_CONFIG(tooltip)
        self.edit_formula.setToolTip(QCoreApplication.translate("ImportNonClayDialog", u"Type a chemical formula (e.g. NaAlSi3O8, CaCO3, CaMg(CO3)2) to fill the oxides. Only Si/Al/Fe/Ca/Mg/Na/K map to the reported oxides. Use \u00b7 or * between segments (CaSO4\u00b72H2O, K2O\u00b7Al2O3\u00b76SiO2); a '.' between digits is read as a decimal point (Fe0.5), and you are asked when that changes the result.", None))
#endif // QT_CONFIG(tooltip)
        self.edit_formula.setPlaceholderText(QCoreApplication.translate("ImportNonClayDialog", u"Formula, e.g. NaAlSi3O8", None))
        self.button_formula.setText(QCoreApplication.translate("ImportNonClayDialog", u"Fill from formula", None))
        self.lbl_sum.setText(QCoreApplication.translate("ImportNonClayDialog", u"Sum: 0.00 %", None))
#if QT_CONFIG(tooltip)
        self.button_normalize.setToolTip(QCoreApplication.translate("ImportNonClayDialog", u"Scale the entered oxides so they sum to 100 %.", None))
#endif // QT_CONFIG(tooltip)
        self.button_normalize.setText(QCoreApplication.translate("ImportNonClayDialog", u"Normalize to 100 %", None))
        self.lbl_preview.setText(QCoreApplication.translate("ImportNonClayDialog", u"Pattern preview", None))
    # retranslateUi

