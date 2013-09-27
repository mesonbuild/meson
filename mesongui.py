#!/usr/bin/env python3

# Copyright 2013 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os, pickle
import build, coredata
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QHeaderView
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QVariant
import PyQt5.QtCore

class PathModel(QAbstractItemModel):
    def __init__(self, coredata):
        super().__init__()
        self.coredata = coredata
        self.names = ['Prefix', 'Library dir', 'Binary dir', 'Include dir', 'Data dir',\
                      'Man dir', 'Locale dir']
        self.attr_name = ['prefix', 'libdir', 'bindir', 'includedir', 'datadir', \
                          'mandir', 'localedir']

    def flags(self, index):
        if index.column() == 1:
            editable = PyQt5.QtCore.Qt.ItemIsEditable
        else:
            editable= 0
        return PyQt5.QtCore.Qt.ItemIsSelectable | PyQt5.QtCore.Qt.ItemIsEnabled | editable

    def rowCount(self, index):
        if index.isValid():
            return 0
        return len(self.names)
    
    def columnCount(self, index):
        return 2

    def headerData(self, section, orientation, role):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return QVariant()
        if section == 1:
            return QVariant('Path')
        return QVariant('Type')

    def index(self, row, column, parent):
        return self.createIndex(row, column)

    def index(self, row, column, parent):
        return self.createIndex(row, column)

    def data(self, index, role):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return QVariant()
        row = index.row()
        column = index.column()
        if column == 0:
            return self.names[row]
        return getattr(self.coredata, self.attr_name[row])

    def parent(self, index):
        return QModelIndex()

    def setData(self, index, value, role):
        if role != PyQt5.QtCore.Qt.EditRole:
            return False
        row = index.row()
        column = index.column()
        s = str(value)
        setattr(self.coredata, self.attr_name[row], s)
        self.dataChanged.emit(self.createIndex(row, column), self.createIndex(row, column))
        return True

class TargetModel(QAbstractItemModel):
    def __init__(self, builddata):
        super().__init__()
        self.targets = []
        for target in builddata.get_targets().values():
            name = target.get_basename()
            num_sources = len(target.get_sources()) + len(target.get_generated_sources())
            if isinstance(target, build.Executable):
                typename = 'executable'
            elif isinstance(target, build.SharedLibrary):
                typename = 'shared library'
            elif isinstance(target, build.StaticLibrary):
                typename = 'static library'
            else:
                typename = 'unknown'
            self.targets.append((name, typename, num_sources))

    def flags(self, index):
        return PyQt5.QtCore.Qt.ItemIsSelectable | PyQt5.QtCore.Qt.ItemIsEnabled

    def rowCount(self, index):
        if index.isValid():
            return 0
        return len(self.targets)
    
    def columnCount(self, index):
        return 3

    def headerData(self, section, orientation, role):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return QVariant()
        if section == 2:
            return QVariant('Source files')
        if section == 1:
            return QVariant('Type')
        return QVariant('Name')

    def data(self, index, role):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return QVariant()
        row = index.row()
        column = index.column()
        return self.targets[row][column]

    def index(self, row, column, parent):
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

class MesonGui():
    def __init__(self, build_dir):
        self.build_dir = os.path.join(os.getcwd(), build_dir)
        self.src_dir = os.path.normpath(os.path.join(self.build_dir, '..')) # HACK HACK HACK WRONG!
        uifile = 'mesonmain.ui'
        self.ui = uic.loadUi(uifile)
        self.ui.show()
        self.coredata_file = os.path.join(build_dir, 'meson-private/coredata.dat')
        self.build_file = os.path.join(build_dir, 'meson-private/build.dat')
        if not os.path.exists(self.coredata_file):
            printf("Argument is not build directory.")
            sys.exit(1)
        self.coredata = pickle.load(open(self.coredata_file, 'rb'))
        self.build = pickle.load(open(self.build_file, 'rb'))
        self.path_model = PathModel(self.coredata)
        self.target_model = TargetModel(self.build)
        self.fill_data()
        self.ui.path_view.setModel(self.path_model)
        hv = QHeaderView(1)
        hv.setModel(self.path_model)
        self.ui.path_view.setHeader(hv)
        self.ui.target_view.setModel(self.target_model)
        hv = QHeaderView(1)
        hv.setModel(self.target_model)
        self.ui.target_view.setHeader(hv)

    def fill_data(self):
        self.ui.project_label.setText(self.build.project)
        self.ui.srcdir_label.setText(self.src_dir)
        self.ui.builddir_label.setText(self.build_dir)
        if self.coredata.cross_file is None:
            btype = 'Native build'
        else:
            btype = 'Cross build'
        self.ui.buildtype_label.setText(btype)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if len(sys.argv) != 2:
        print(sys.argv[0], "<build dir>")
        sys.exit(1)
    gui = MesonGui(sys.argv[1])
    sys.exit(app.exec_())
