# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'structure_library.ui'
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
    QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QSplitter, QTableView, QTextBrowser,
    QVBoxLayout, QWidget)

class Ui_StructureLibraryDialog(object):
    def setupUi(self, StructureLibraryDialog):
        if not StructureLibraryDialog.objectName():
            StructureLibraryDialog.setObjectName(u"StructureLibraryDialog")
        StructureLibraryDialog.resize(980, 660)
        StructureLibraryDialog.setSizeGripEnabled(True)
        self.rootLayout = QVBoxLayout(StructureLibraryDialog)
        self.rootLayout.setObjectName(u"rootLayout")
        self.lbl_intro = QLabel(StructureLibraryDialog)
        self.lbl_intro.setObjectName(u"lbl_intro")
        self.lbl_intro.setWordWrap(True)

        self.rootLayout.addWidget(self.lbl_intro)

        self.filterRow = QHBoxLayout()
        self.filterRow.setObjectName(u"filterRow")
        self.lbl_search_caption = QLabel(StructureLibraryDialog)
        self.lbl_search_caption.setObjectName(u"lbl_search_caption")

        self.filterRow.addWidget(self.lbl_search_caption)

        self.edit_search = QLineEdit(StructureLibraryDialog)
        self.edit_search.setObjectName(u"edit_search")
        self.edit_search.setClearButtonEnabled(True)

        self.filterRow.addWidget(self.edit_search)

        self.lbl_group_caption = QLabel(StructureLibraryDialog)
        self.lbl_group_caption.setObjectName(u"lbl_group_caption")

        self.filterRow.addWidget(self.lbl_group_caption)

        self.cmb_group = QComboBox(StructureLibraryDialog)
        self.cmb_group.setObjectName(u"cmb_group")
        self.cmb_group.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        self.filterRow.addWidget(self.cmb_group)

        self.lbl_count = QLabel(StructureLibraryDialog)
        self.lbl_count.setObjectName(u"lbl_count")

        self.filterRow.addWidget(self.lbl_count)


        self.rootLayout.addLayout(self.filterRow)

        self.splitter = QSplitter(StructureLibraryDialog)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.tbl_structures = QTableView(self.splitter)
        self.tbl_structures.setObjectName(u"tbl_structures")
        self.tbl_structures.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_structures.setAlternatingRowColors(True)
        self.tbl_structures.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_structures.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_structures.setSortingEnabled(True)
        self.tbl_structures.setWordWrap(False)
        self.splitter.addWidget(self.tbl_structures)
        self.tbl_structures.verticalHeader().setVisible(False)
        self.txt_details = QTextBrowser(self.splitter)
        self.txt_details.setObjectName(u"txt_details")
        self.txt_details.setOpenExternalLinks(True)
        self.splitter.addWidget(self.txt_details)

        self.rootLayout.addWidget(self.splitter)

        self.actionRow = QHBoxLayout()
        self.actionRow.setObjectName(u"actionRow")
        self.btn_new_clay = QPushButton(StructureLibraryDialog)
        self.btn_new_clay.setObjectName(u"btn_new_clay")
        self.btn_new_clay.setAutoDefault(False)

        self.actionRow.addWidget(self.btn_new_clay)

        self.btn_add_nonclay = QPushButton(StructureLibraryDialog)
        self.btn_add_nonclay.setObjectName(u"btn_add_nonclay")
        self.btn_add_nonclay.setAutoDefault(False)

        self.actionRow.addWidget(self.btn_add_nonclay)

        self.actionSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.actionRow.addItem(self.actionSpacer)

        self.btn_copy_citation = QPushButton(StructureLibraryDialog)
        self.btn_copy_citation.setObjectName(u"btn_copy_citation")
        self.btn_copy_citation.setAutoDefault(False)

        self.actionRow.addWidget(self.btn_copy_citation)

        self.btn_open_folder = QPushButton(StructureLibraryDialog)
        self.btn_open_folder.setObjectName(u"btn_open_folder")
        self.btn_open_folder.setAutoDefault(False)

        self.actionRow.addWidget(self.btn_open_folder)


        self.rootLayout.addLayout(self.actionRow)

        self.lbl_status = QLabel(StructureLibraryDialog)
        self.lbl_status.setObjectName(u"lbl_status")
        self.lbl_status.setWordWrap(True)

        self.rootLayout.addWidget(self.lbl_status)

        self.buttonBox = QDialogButtonBox(StructureLibraryDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.rootLayout.addWidget(self.buttonBox)

#if QT_CONFIG(shortcut)
        self.lbl_search_caption.setBuddy(self.edit_search)
        self.lbl_group_caption.setBuddy(self.cmb_group)
#endif // QT_CONFIG(shortcut)
        QWidget.setTabOrder(self.edit_search, self.cmb_group)
        QWidget.setTabOrder(self.cmb_group, self.tbl_structures)
        QWidget.setTabOrder(self.tbl_structures, self.txt_details)
        QWidget.setTabOrder(self.txt_details, self.btn_new_clay)
        QWidget.setTabOrder(self.btn_new_clay, self.btn_add_nonclay)
        QWidget.setTabOrder(self.btn_add_nonclay, self.btn_copy_citation)
        QWidget.setTabOrder(self.btn_copy_citation, self.btn_open_folder)

        self.retranslateUi(StructureLibraryDialog)

        self.btn_new_clay.setDefault(False)
        self.btn_add_nonclay.setDefault(False)
        self.btn_copy_citation.setDefault(False)
        self.btn_open_folder.setDefault(False)


        QMetaObject.connectSlotsByName(StructureLibraryDialog)
    # setupUi

    def retranslateUi(self, StructureLibraryDialog):
        StructureLibraryDialog.setWindowTitle(QCoreApplication.translate("StructureLibraryDialog", u"Structure Library", None))
        self.lbl_intro.setText(QCoreApplication.translate("StructureLibraryDialog", u"Published crystal structures that ship with MudLab. Cite the article for any structure you use.", None))
        self.lbl_search_caption.setText(QCoreApplication.translate("StructureLibraryDialog", u"Search", None))
#if QT_CONFIG(tooltip)
        self.edit_search.setToolTip(QCoreApplication.translate("StructureLibraryDialog", u"Show only the structures whose mineral, formula, group, authors, journal, year or database number contain every word you type.", None))
#endif // QT_CONFIG(tooltip)
        self.edit_search.setPlaceholderText(QCoreApplication.translate("StructureLibraryDialog", u"Mineral, formula, author, journal\u2026", None))
        self.lbl_group_caption.setText(QCoreApplication.translate("StructureLibraryDialog", u"Group", None))
#if QT_CONFIG(tooltip)
        self.cmb_group.setToolTip(QCoreApplication.translate("StructureLibraryDialog", u"Show one mineral family.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_count.setText("")
#if QT_CONFIG(tooltip)
        self.btn_new_clay.setToolTip(QCoreApplication.translate("StructureLibraryDialog", u"Build a new one-component clay phase from this structure. The import review shows how the structure was projected onto c*, and anything it got wrong can be corrected there before OK.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_new_clay.setText(QCoreApplication.translate("StructureLibraryDialog", u"New clay phase\u2026", None))
#if QT_CONFIG(tooltip)
        self.btn_add_nonclay.setToolTip(QCoreApplication.translate("StructureLibraryDialog", u"Open Import Non-Clay with this structure loaded, to add it as a non-clay phase. Its peaks and its oxide composition come from the structure; check the name and the peak width before OK.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_add_nonclay.setText(QCoreApplication.translate("StructureLibraryDialog", u"Add as non-clay phase\u2026", None))
#if QT_CONFIG(tooltip)
        self.btn_copy_citation.setToolTip(QCoreApplication.translate("StructureLibraryDialog", u"Copy the article to cite for this structure.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_copy_citation.setText(QCoreApplication.translate("StructureLibraryDialog", u"Copy citation", None))
#if QT_CONFIG(tooltip)
        self.btn_open_folder.setToolTip(QCoreApplication.translate("StructureLibraryDialog", u"Open the Structures folder in Explorer. README.md and CREDITS.md are in it.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_open_folder.setText(QCoreApplication.translate("StructureLibraryDialog", u"Open folder", None))
        self.lbl_status.setText("")
    # retranslateUi

