# -*- coding: utf-8 -*-

from PySide import QtCore, QtGui
from widgets import *


class LoginScreen(CenteredWidget):

    def __init__(self):
        super(LoginScreen, self).__init__()
        self.initUI()

    def initUI(self):
        self.resize(400, 200)
        self.setMinimumSize(QtCore.QSize(400, 200))
        self.setMaximumSize(QtCore.QSize(400, 200))
        self.new_profile = QtGui.QPushButton(self)
        self.new_profile.setGeometry(QtCore.QRect(20, 150, 171, 27))
        self.new_profile.clicked.connect(self.create_profile)
        self.label = QtGui.QLabel(self)
        self.label.setGeometry(QtCore.QRect(20, 70, 101, 17))
        self.new_name = QtGui.QPlainTextEdit(self)
        self.new_name.setGeometry(QtCore.QRect(20, 100, 171, 31))
        self.load_profile = QtGui.QPushButton(self)
        self.load_profile.setGeometry(QtCore.QRect(220, 150, 161, 27))
        self.load_profile.clicked.connect(self.load_ex_profile)
        self.default = QtGui.QCheckBox(self)
        self.default.setGeometry(QtCore.QRect(220, 110, 131, 22))
        self.groupBox = QtGui.QGroupBox(self)
        self.groupBox.setGeometry(QtCore.QRect(210, 40, 181, 151))
        self.comboBox = QtGui.QComboBox(self.groupBox)
        self.comboBox.setGeometry(QtCore.QRect(10, 30, 161, 27))
        self.groupBox_2 = QtGui.QGroupBox(self)
        self.groupBox_2.setGeometry(QtCore.QRect(10, 40, 191, 151))
        self.toxygen = QtGui.QLabel(self)
        self.groupBox.raise_()
        self.groupBox_2.raise_()
        self.comboBox.raise_()
        self.default.raise_()
        self.load_profile.raise_()
        self.new_name.raise_()
        self.new_profile.raise_()
        self.toxygen.setGeometry(QtCore.QRect(160, 10, 90, 21))
        font = QtGui.QFont()
        font.setFamily("Impact")
        font.setPointSize(16)
        self.toxygen.setFont(font)
        self.toxygen.setObjectName("toxygen")
        self.type = 0
        self.number = -1
        self.load_as_default = False
        self.name = None
        self.retranslateUi()
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslateUi(self):
        self.setWindowTitle(QtGui.QApplication.translate("login", "Log in", None, QtGui.QApplication.UnicodeUTF8))
        self.new_profile.setText(QtGui.QApplication.translate("login", "Create", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("login", "Profile name:", None, QtGui.QApplication.UnicodeUTF8))
        self.load_profile.setText(QtGui.QApplication.translate("login", "Load profile", None, QtGui.QApplication.UnicodeUTF8))
        self.default.setText(QtGui.QApplication.translate("login", "Use as default", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox.setTitle(QtGui.QApplication.translate("login", "Load existing profile", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox_2.setTitle(QtGui.QApplication.translate("login", "Create new profile", None, QtGui.QApplication.UnicodeUTF8))
        self.toxygen.setText(QtGui.QApplication.translate("login", "toxygen", None, QtGui.QApplication.UnicodeUTF8))

    def create_profile(self):
        self.type = 1
        self.name = self.new_name.toPlainText()
        self.close()

    def load_ex_profile(self):
        if not self.create_only:
            self.type = 2
            self.number = self.comboBox.currentIndex()
            self.load_as_default = self.default.isChecked()
            self.close()

    def update_select(self, data):
        list_of_profiles = []
        for elem in data:
            list_of_profiles.append(self.tr(elem))
        self.comboBox.addItems(list_of_profiles)
        self.create_only = not list_of_profiles

    def update_on_close(self, func):
        self.onclose = func

    def closeEvent(self, event):
        self.onclose(self.type, self.number, self.load_as_default, self.name)
        event.accept()


if __name__ == '__main__':
    pass
