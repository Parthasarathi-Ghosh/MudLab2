# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'import_composition.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QDialog,
    QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_ImportCompositionDialog(object):
    def setupUi(self, ImportCompositionDialog):
        if not ImportCompositionDialog.objectName():
            ImportCompositionDialog.setObjectName(u"ImportCompositionDialog")
        ImportCompositionDialog.resize(420, 470)
        ImportCompositionDialog.setMinimumSize(QSize(380, 430))
        ImportCompositionDialog.setModal(True)
        self.compositionLayout = QVBoxLayout(ImportCompositionDialog)
        self.compositionLayout.setObjectName(u"compositionLayout")
        self.lblIntro = QLabel(ImportCompositionDialog)
        self.lblIntro.setObjectName(u"lblIntro")
        self.lblIntro.setWordWrap(True)

        self.compositionLayout.addWidget(self.lblIntro)

        self.detailsLayout = QFormLayout()
        self.detailsLayout.setObjectName(u"detailsLayout")
        self.lblName = QLabel(ImportCompositionDialog)
        self.lblName.setObjectName(u"lblName")

        self.detailsLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblName)

        self.edit_name = QLineEdit(ImportCompositionDialog)
        self.edit_name.setObjectName(u"edit_name")

        self.detailsLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.edit_name)

        self.lblSource = QLabel(ImportCompositionDialog)
        self.lblSource.setObjectName(u"lblSource")

        self.detailsLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lblSource)

        self.edit_source = QLineEdit(ImportCompositionDialog)
        self.edit_source.setObjectName(u"edit_source")

        self.detailsLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.edit_source)


        self.compositionLayout.addLayout(self.detailsLayout)

        self.oxide_grid = QTableWidget(ImportCompositionDialog)
        self.oxide_grid.setObjectName(u"oxide_grid")
        self.oxide_grid.setAlternatingRowColors(True)
        self.oxide_grid.setSelectionMode(QAbstractItemView.NoSelection)

        self.compositionLayout.addWidget(self.oxide_grid)

        self.totalRow = QHBoxLayout()
        self.totalRow.setObjectName(u"totalRow")
        self.lbl_sum = QLabel(ImportCompositionDialog)
        self.lbl_sum.setObjectName(u"lbl_sum")

        self.totalRow.addWidget(self.lbl_sum)

        self.totalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.totalRow.addItem(self.totalSpacer)

        self.button_normalize = QPushButton(ImportCompositionDialog)
        self.button_normalize.setObjectName(u"button_normalize")

        self.totalRow.addWidget(self.button_normalize)


        self.compositionLayout.addLayout(self.totalRow)

        self.lbl_warning = QLabel(ImportCompositionDialog)
        self.lbl_warning.setObjectName(u"lbl_warning")
        self.lbl_warning.setWordWrap(True)

        self.compositionLayout.addWidget(self.lbl_warning)

        self.buttonBox = QDialogButtonBox(ImportCompositionDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.compositionLayout.addWidget(self.buttonBox)


        self.retranslateUi(ImportCompositionDialog)

        QMetaObject.connectSlotsByName(ImportCompositionDialog)
    # setupUi

    def retranslateUi(self, ImportCompositionDialog):
        ImportCompositionDialog.setWindowTitle(QCoreApplication.translate("ImportCompositionDialog", u"Import composition", None))
        self.lblIntro.setText(QCoreApplication.translate("ImportCompositionDialog", u"Enter the measured (XRF) oxide analysis for this sample, in weight percent.", None))
        self.lblName.setText(QCoreApplication.translate("ImportCompositionDialog", u"Name:", None))
#if QT_CONFIG(tooltip)
        self.edit_name.setToolTip(QCoreApplication.translate("ImportCompositionDialog", u"A short label for this analysis, shown wherever it is compared with the modelled composition.", None))
#endif // QT_CONFIG(tooltip)
        self.lblSource.setText(QCoreApplication.translate("ImportCompositionDialog", u"Source:", None))
#if QT_CONFIG(tooltip)
        self.edit_source.setToolTip(QCoreApplication.translate("ImportCompositionDialog", u"Optional note on where the analysis came from - laboratory, method, date. Kept with the project; never interpreted.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.oxide_grid.setToolTip(QCoreApplication.translate("ImportCompositionDialog", u"Only these oxides can be entered: they are the same set the modelled composition reports, so the two can be compared row by row. Leave an oxide at 0 if it was not measured.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_sum.setText(QCoreApplication.translate("ImportCompositionDialog", u"Total: 0.00 %", None))
        self.button_normalize.setText(QCoreApplication.translate("ImportCompositionDialog", u"Recompute to 100 %", None))
#if QT_CONFIG(tooltip)
        self.button_normalize.setToolTip(QCoreApplication.translate("ImportCompositionDialog", u"Scale every entered value so they total 100 %. The modelled composition is always normalised to 100, so an analysis totalling 97 or 101 would otherwise read as a difference that is not there.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_warning.setText("")
    # retranslateUi

