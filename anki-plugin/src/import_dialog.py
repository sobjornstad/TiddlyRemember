# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'designer/import_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(313, 92)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.text = QtWidgets.QLabel(Dialog)
        self.text.setObjectName("text")
        self.verticalLayout.addWidget(self.text)
        self.progressBar = QtWidgets.QProgressBar(Dialog)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)
        self.progressBar.setProperty("value", -1)
        self.progressBar.setObjectName("progressBar")
        self.verticalLayout.addWidget(self.progressBar)
        self.wikiProgressBar = QtWidgets.QProgressBar(Dialog)
        self.wikiProgressBar.setMinimum(0)
        self.wikiProgressBar.setMaximum(100)
        self.wikiProgressBar.setProperty("value", 1)
        self.wikiProgressBar.setObjectName("wikiProgressBar")
        self.verticalLayout.addWidget(self.wikiProgressBar)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Sync from TiddlyWiki"))
        self.text.setText(_translate("Dialog", "Exporting tiddlers..."))
        self.progressBar.setFormat(_translate("Dialog", "%p%"))
        self.wikiProgressBar.setFormat(_translate("Dialog", "Wiki %v/%m"))