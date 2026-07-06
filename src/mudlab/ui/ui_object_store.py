# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'object_store.ui'
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
    QDialogButtonBox, QFrame, QGridLayout, QGroupBox,
    QHeaderView, QPushButton, QScrollArea, QSizePolicy,
    QSplitter, QTreeView, QVBoxLayout, QWidget)

class Ui_ObjectStoreDialog(object):
    def setupUi(self, ObjectStoreDialog):
        if not ObjectStoreDialog.objectName():
            ObjectStoreDialog.setObjectName(u"ObjectStoreDialog")
        ObjectStoreDialog.resize(920, 620)
        self.dialogLayout = QVBoxLayout(ObjectStoreDialog)
        self.dialogLayout.setObjectName(u"dialogLayout")
        self.edit_object_store = QSplitter(ObjectStoreDialog)
        self.edit_object_store.setObjectName(u"edit_object_store")
        self.edit_object_store.setOrientation(Qt.Horizontal)
        self.edit_object_store.setChildrenCollapsible(False)
        self.objectsPanel = QWidget(self.edit_object_store)
        self.objectsPanel.setObjectName(u"objectsPanel")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.objectsPanel.sizePolicy().hasHeightForWidth())
        self.objectsPanel.setSizePolicy(sizePolicy)
        self.objectsPanel.setMinimumSize(QSize(220, 0))
        self.objectsPanelLayout = QVBoxLayout(self.objectsPanel)
        self.objectsPanelLayout.setObjectName(u"objectsPanelLayout")
        self.objectsPanelLayout.setContentsMargins(0, 0, 0, 0)
        self.frm_objects_tv = QGroupBox(self.objectsPanel)
        self.frm_objects_tv.setObjectName(u"frm_objects_tv")
        self.objectsGroupLayout = QVBoxLayout(self.frm_objects_tv)
        self.objectsGroupLayout.setObjectName(u"objectsGroupLayout")
        self.edit_objects_treeview = QTreeView(self.frm_objects_tv)
        self.edit_objects_treeview.setObjectName(u"edit_objects_treeview")
        self.edit_objects_treeview.setRootIsDecorated(False)
        self.edit_objects_treeview.setAlternatingRowColors(True)
        self.edit_objects_treeview.setUniformRowHeights(True)
        self.edit_objects_treeview.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.objectsGroupLayout.addWidget(self.edit_objects_treeview)

        self.objectButtons = QGridLayout()
        self.objectButtons.setObjectName(u"objectButtons")
        self.button_add_object = QPushButton(self.frm_objects_tv)
        self.button_add_object.setObjectName(u"button_add_object")

        self.objectButtons.addWidget(self.button_add_object, 0, 0, 1, 1)

        self.button_del_object = QPushButton(self.frm_objects_tv)
        self.button_del_object.setObjectName(u"button_del_object")

        self.objectButtons.addWidget(self.button_del_object, 0, 1, 1, 1)

        self.button_load_object = QPushButton(self.frm_objects_tv)
        self.button_load_object.setObjectName(u"button_load_object")

        self.objectButtons.addWidget(self.button_load_object, 1, 0, 1, 1)

        self.button_save_object = QPushButton(self.frm_objects_tv)
        self.button_save_object.setObjectName(u"button_save_object")

        self.objectButtons.addWidget(self.button_save_object, 1, 1, 1, 1)


        self.objectsGroupLayout.addLayout(self.objectButtons)

        self.extraLayout = QVBoxLayout()
        self.extraLayout.setObjectName(u"extraLayout")

        self.objectsGroupLayout.addLayout(self.extraLayout)


        self.objectsPanelLayout.addWidget(self.frm_objects_tv)

        self.edit_object_store.addWidget(self.objectsPanel)
        self.frame_object_param = QGroupBox(self.edit_object_store)
        self.frame_object_param.setObjectName(u"frame_object_param")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_object_param.sizePolicy().hasHeightForWidth())
        self.frame_object_param.setSizePolicy(sizePolicy1)
        self.propertiesGroupLayout = QVBoxLayout(self.frame_object_param)
        self.propertiesGroupLayout.setObjectName(u"propertiesGroupLayout")
        self.vwp_edit_object = QScrollArea(self.frame_object_param)
        self.vwp_edit_object.setObjectName(u"vwp_edit_object")
        self.vwp_edit_object.setFrameShape(QFrame.NoFrame)
        self.vwp_edit_object.setWidgetResizable(True)
        self.propertiesContainer = QWidget()
        self.propertiesContainer.setObjectName(u"propertiesContainer")
        self.propertiesLayout = QVBoxLayout(self.propertiesContainer)
        self.propertiesLayout.setObjectName(u"propertiesLayout")
        self.propertiesLayout.setContentsMargins(0, 0, 0, 0)
        self.vwp_edit_object.setWidget(self.propertiesContainer)

        self.propertiesGroupLayout.addWidget(self.vwp_edit_object)

        self.edit_object_store.addWidget(self.frame_object_param)

        self.dialogLayout.addWidget(self.edit_object_store)

        self.buttonBox = QDialogButtonBox(ObjectStoreDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)

        self.dialogLayout.addWidget(self.buttonBox)


        self.retranslateUi(ObjectStoreDialog)

        QMetaObject.connectSlotsByName(ObjectStoreDialog)
    # setupUi

    def retranslateUi(self, ObjectStoreDialog):
        ObjectStoreDialog.setWindowTitle(QCoreApplication.translate("ObjectStoreDialog", u"Edit Objects", None))
        self.frm_objects_tv.setTitle(QCoreApplication.translate("ObjectStoreDialog", u"Objects", None))
        self.button_add_object.setText(QCoreApplication.translate("ObjectStoreDialog", u"Add", None))
        self.button_del_object.setText(QCoreApplication.translate("ObjectStoreDialog", u"Remove", None))
        self.button_load_object.setText(QCoreApplication.translate("ObjectStoreDialog", u"Import", None))
        self.button_save_object.setText(QCoreApplication.translate("ObjectStoreDialog", u"Export", None))
        self.frame_object_param.setTitle(QCoreApplication.translate("ObjectStoreDialog", u"Properties", None))
    # retranslateUi

