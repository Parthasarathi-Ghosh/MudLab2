# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_raw_pattern_phase.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_EditRawPatternPhaseWidget(object):
    def setupUi(self, EditRawPatternPhaseWidget):
        if not EditRawPatternPhaseWidget.objectName():
            EditRawPatternPhaseWidget.setObjectName(u"EditRawPatternPhaseWidget")
        self.rawRootLayout = QVBoxLayout(EditRawPatternPhaseWidget)
        self.rawRootLayout.setObjectName(u"rawRootLayout")
        self.rawForm = QFormLayout()
        self.rawForm.setObjectName(u"rawForm")
        self.lblName = QLabel(EditRawPatternPhaseWidget)
        self.lblName.setObjectName(u"lblName")

        self.rawForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lblName)

        self.raw_phase_name = QLineEdit(EditRawPatternPhaseWidget)
        self.raw_phase_name.setObjectName(u"raw_phase_name")

        self.rawForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.raw_phase_name)


        self.rawRootLayout.addLayout(self.rawForm)

        self.grpRawPattern = QGroupBox(EditRawPatternPhaseWidget)
        self.grpRawPattern.setObjectName(u"grpRawPattern")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.grpRawPattern.sizePolicy().hasHeightForWidth())
        self.grpRawPattern.setSizePolicy(sizePolicy)
        self.grpRawLayout = QVBoxLayout(self.grpRawPattern)
        self.grpRawLayout.setObjectName(u"grpRawLayout")
        self.rawControlsRow = QHBoxLayout()
        self.rawControlsRow.setObjectName(u"rawControlsRow")
        self.button_import_pattern = QPushButton(self.grpRawPattern)
        self.button_import_pattern.setObjectName(u"button_import_pattern")

        self.rawControlsRow.addWidget(self.button_import_pattern)

        self.raw_pattern_info = QLabel(self.grpRawPattern)
        self.raw_pattern_info.setObjectName(u"raw_pattern_info")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.raw_pattern_info.sizePolicy().hasHeightForWidth())
        self.raw_pattern_info.setSizePolicy(sizePolicy1)

        self.rawControlsRow.addWidget(self.raw_pattern_info)


        self.grpRawLayout.addLayout(self.rawControlsRow)

        self.rawPlotLayout = QVBoxLayout()
        self.rawPlotLayout.setObjectName(u"rawPlotLayout")

        self.grpRawLayout.addLayout(self.rawPlotLayout)


        self.rawRootLayout.addWidget(self.grpRawPattern)


        self.retranslateUi(EditRawPatternPhaseWidget)

        QMetaObject.connectSlotsByName(EditRawPatternPhaseWidget)
    # setupUi

    def retranslateUi(self, EditRawPatternPhaseWidget):
        self.lblName.setText(QCoreApplication.translate("EditRawPatternPhaseWidget", u"Name", None))
#if QT_CONFIG(tooltip)
        self.raw_phase_name.setToolTip(QCoreApplication.translate("EditRawPatternPhaseWidget", u"The name of this raw-pattern phase.", None))
#endif // QT_CONFIG(tooltip)
        self.grpRawPattern.setTitle(QCoreApplication.translate("EditRawPatternPhaseWidget", u"Measured pattern", None))
#if QT_CONFIG(tooltip)
        self.button_import_pattern.setToolTip(QCoreApplication.translate("EditRawPatternPhaseWidget", u"Import the measured pattern from an XRD data file (ASCII .xy/.txt/.csv/.dat, Bruker .uxd/.raw, PANalytical .xrdml, Rigaku .rasx).", None))
#endif // QT_CONFIG(tooltip)
        self.button_import_pattern.setText(QCoreApplication.translate("EditRawPatternPhaseWidget", u"Import pattern\u2026", None))
        self.raw_pattern_info.setText(QCoreApplication.translate("EditRawPatternPhaseWidget", u"No pattern loaded.", None))
        pass
    # retranslateUi

