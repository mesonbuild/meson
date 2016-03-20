#!/usr/bin/env python3

# Copyright 2013-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os, pickle, time, shutil
from . import build, coredata, environment, mesonlib
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QHeaderView
from PyQt5.QtWidgets import QComboBox, QCheckBox
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QVariant, QTimer
import PyQt5.QtCore
import PyQt5.QtWidgets

priv_dir = os.path.split(os.path.abspath(os.path.realpath(__file__)))[0]

class PathModel(QAbstractItemModel):
    def __init__(self, coredata):
        super().__init__()
        self.coredata = coredata
        self.names = ['Prefix', 'Library dir', 'Binary dir', 'Include dir', 'Data dir',\
                      'Man dir', 'Locale dir']
        self.attr_name = ['prefix', 'libdir', 'bindir', 'includedir', 'datadir', \
                          'mandir', 'localedir']

    def args(self, index):
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
            elif isinstance(target, build.CustomTarget):
                typename = 'custom'
            else:
                typename = 'unknown'
            if target.should_install():
                installed = 'Yes'
            else:
                installed = 'No'
            self.targets.append((name, typename, installed, num_sources))

    def args(self, index):
        return PyQt5.QtCore.Qt.ItemIsSelectable | PyQt5.QtCore.Qt.ItemIsEnabled

    def rowCount(self, index):
        if index.isValid():
            return 0
        return len(self.targets)

    def columnCount(self, index):
        return 4

    def headerData(self, section, orientation, role):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return QVariant()
        if section == 3:
            return QVariant('Source files')
        if section == 2:
            return QVariant('Installed')
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

class DependencyModel(QAbstractItemModel):
    def __init__(self, coredata):
        super().__init__()
        self.deps = []
        for k in coredata.deps.keys():
            bd = coredata.deps[k]
            name = k
            found = bd.found()
            if found:
                cflags = str(bd.get_compile_args())
                libs = str(bd.get_link_args())
                found = 'yes'
            else:
                cflags = ''
                libs = ''
                found = 'no'
            self.deps.append((name, found, cflags, libs))

    def args(self, index):
        return PyQt5.QtCore.Qt.ItemIsSelectable | PyQt5.QtCore.Qt.ItemIsEnabled

    def rowCount(self, index):
        if index.isValid():
            return 0
        return len(self.deps)

    def columnCount(self, index):
        return 4

    def headerData(self, section, orientation, role):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return QVariant()
        if section == 3:
            return QVariant('Link args')
        if section == 2:
            return QVariant('Compile args')
        if section == 1:
            return QVariant('Found')
        return QVariant('Name')

    def data(self, index, role):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return QVariant()
        row = index.row()
        column = index.column()
        return self.deps[row][column]

    def index(self, row, column, parent):
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

class CoreModel(QAbstractItemModel):
    def __init__(self, core_data):
        super().__init__()
        self.elems = []
        for langname, comp in core_data.compilers.items():
            self.elems.append((langname + ' compiler', str(comp.get_exelist())))
        for langname, comp in core_data.cross_compilers.items():
            self.elems.append((langname + ' cross compiler', str(comp.get_exelist())))

    def args(self, index):
        return PyQt5.QtCore.Qt.ItemIsSelectable | PyQt5.QtCore.Qt.ItemIsEnabled

    def rowCount(self, index):
        if index.isValid():
            return 0
        return len(self.elems)

    def columnCount(self, index):
        return 2

    def headerData(self, section, orientation, role):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return QVariant()
        if section == 1:
            return QVariant('Value')
        return QVariant('Name')

    def data(self, index, role):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return QVariant()
        row = index.row()
        column = index.column()
        return self.elems[row][column]

    def index(self, row, column, parent):
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

class OptionForm:
    def __init__(self, coredata, form):
        self.coredata = coredata
        self.form = form
        form.addRow(PyQt5.QtWidgets.QLabel("Meson options"))
        combo = QComboBox()
        combo.addItem('plain')
        combo.addItem('debug')
        combo.addItem('debugoptimized')
        combo.addItem('release')
        combo.setCurrentText(self.coredata.get_builtin_option('buildtype'))
        combo.currentTextChanged.connect(self.build_type_changed)
        self.form.addRow('Build type', combo)
        strip = QCheckBox("")
        strip.setChecked(self.coredata.get_builtin_option('strip'))
        strip.stateChanged.connect(self.strip_changed)
        self.form.addRow('Strip on install', strip)
        unity = QCheckBox("")
        unity.setChecked(self.coredata.get_builtin_option('unity'))
        unity.stateChanged.connect(self.unity_changed)
        self.form.addRow('Unity build', unity)
        form.addRow(PyQt5.QtWidgets.QLabel("Project options"))
        self.set_user_options()

    def set_user_options(self):
        options = self.coredata.user_options
        keys = list(options.keys())
        keys.sort()
        self.opt_keys = keys
        self.opt_widgets = []
        for key in keys:
            opt = options[key]
            if isinstance(opt, mesonlib.UserStringOption):
                w = PyQt5.QtWidgets.QLineEdit(opt.value)
                w.textChanged.connect(self.user_option_changed)
            elif isinstance(opt, mesonlib.UserBooleanOption):
                w = QCheckBox('')
                w.setChecked(opt.value)
                w.stateChanged.connect(self.user_option_changed)
            elif isinstance(opt, mesonlib.UserComboOption):
                w = QComboBox()
                for i in opt.choices:
                    w.addItem(i)
                w.setCurrentText(opt.value)
                w.currentTextChanged.connect(self.user_option_changed)
            else:
                raise RuntimeError("Unknown option type")
            self.opt_widgets.append(w)
            self.form.addRow(opt.description, w)

    def user_option_changed(self, dummy=None):
        for i in range(len(self.opt_keys)):
            key = self.opt_keys[i]
            w = self.opt_widgets[i]
            if isinstance(w, PyQt5.QtWidgets.QLineEdit):
                newval = w.text()
            elif isinstance(w, QComboBox):
                newval = w.currentText()
            elif isinstance(w, QCheckBox):
                if w.checkState() == 0:
                    newval = False
                else:
                    newval = True
            else:
                raise RuntimeError('Unknown widget type')
            self.coredata.user_options[key].set_value(newval)

    def build_type_changed(self, newtype):
        self.coredata.buildtype = newtype

    def strip_changed(self, newState):
        if newState == 0:
            ns = False
        else:
            ns = True
        self.coredata.strip = ns

    def unity_changed(self, newState):
        if newState == 0:
            ns = False
        else:
            ns = True
        self.coredata.unity = ns

class ProcessRunner():
    def __init__(self, rundir, cmdlist):
        self.cmdlist = cmdlist
        self.ui = uic.loadUi(os.path.join(priv_dir, 'mesonrunner.ui'))
        self.timer = QTimer(self.ui)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.timeout)
        self.process = PyQt5.QtCore.QProcess()
        self.process.setProcessChannelMode(PyQt5.QtCore.QProcess.MergedChannels)
        self.process.setWorkingDirectory(rundir)
        self.process.readyRead.connect(self.read_data)
        self.process.finished.connect(self.finished)
        self.ui.termbutton.clicked.connect(self.terminated)
        self.return_value = 100

    def run(self):
        self.process.start(self.cmdlist[0], self.cmdlist[1:])
        self.timer.start()
        self.start_time = time.time()
        return self.ui.exec()

    def read_data(self):
        while(self.process.canReadLine()):
            txt = bytes(self.process.readLine()).decode('utf8')
            self.ui.console.append(txt)

    def finished(self):
        self.read_data()
        self.ui.termbutton.setText('Done')
        self.timer.stop()
        self.return_value = self.process.exitCode()

    def terminated(self, foo):
        self.process.kill()
        self.timer.stop()
        self.ui.done(self.return_value)

    def timeout(self):
        now = time.time()
        duration = int(now - self.start_time)
        msg = 'Elapsed time: %d:%d' % (duration // 60, duration % 60)
        self.ui.timelabel.setText(msg)

class MesonGui():
    def __init__(self, respawner, build_dir):
        self.respawner = respawner
        uifile = os.path.join(priv_dir, 'mesonmain.ui')
        self.ui = uic.loadUi(uifile)
        self.coredata_file = os.path.join(build_dir, 'meson-private/coredata.dat')
        self.build_file = os.path.join(build_dir, 'meson-private/build.dat')
        if not os.path.exists(self.coredata_file):
            print("Argument is not build directory.")
            sys.exit(1)
        self.coredata = pickle.load(open(self.coredata_file, 'rb'))
        self.build = pickle.load(open(self.build_file, 'rb'))
        self.build_dir = self.build.environment.build_dir
        self.src_dir = self.build.environment.source_dir
        self.build_models()
        self.options = OptionForm(self.coredata, self.ui.option_form)
        self.ui.show()

    def hide(self):
        self.ui.hide()

    def geometry(self):
        return self.ui.geometry()

    def move(self, x, y):
        return self.ui.move(x, y)

    def size(self):
        return self.ui.size()

    def resize(self, s):
        return self.ui.resize(s)

    def build_models(self):
        self.path_model = PathModel(self.coredata)
        self.target_model = TargetModel(self.build)
        self.dep_model = DependencyModel(self.coredata)
        self.core_model = CoreModel(self.coredata)
        self.fill_data()
        self.ui.core_view.setModel(self.core_model)
        hv = QHeaderView(1)
        hv.setModel(self.core_model)
        self.ui.core_view.setHeader(hv)
        self.ui.path_view.setModel(self.path_model)
        hv = QHeaderView(1)
        hv.setModel(self.path_model)
        self.ui.path_view.setHeader(hv)
        self.ui.target_view.setModel(self.target_model)
        hv = QHeaderView(1)
        hv.setModel(self.target_model)
        self.ui.target_view.setHeader(hv)
        self.ui.dep_view.setModel(self.dep_model)
        hv = QHeaderView(1)
        hv.setModel(self.dep_model)
        self.ui.dep_view.setHeader(hv)
        self.ui.compile_button.clicked.connect(self.compile)
        self.ui.test_button.clicked.connect(self.run_tests)
        self.ui.install_button.clicked.connect(self.install)
        self.ui.clean_button.clicked.connect(self.clean)
        self.ui.save_button.clicked.connect(self.save)

    def fill_data(self):
        self.ui.project_label.setText(self.build.projects[''])
        self.ui.srcdir_label.setText(self.src_dir)
        self.ui.builddir_label.setText(self.build_dir)
        if self.coredata.cross_file is None:
            btype = 'Native build'
        else:
            btype = 'Cross build'
        self.ui.buildtype_label.setText(btype)

    def run_process(self, cmdlist):
        cmdlist = [shutil.which(environment.detect_ninja())] + cmdlist
        dialog = ProcessRunner(self.build.environment.build_dir, cmdlist)
        dialog.run()
        # All processes (at the moment) may change cache state
        # so reload.
        self.respawner.respawn()

    def compile(self, foo):
        self.run_process([])

    def run_tests(self, foo):
        self.run_process(['test'])

    def install(self, foo):
        self.run_process(['install'])

    def clean(self, foo):
        self.run_process(['clean'])

    def save(self, foo):
        pickle.dump(self.coredata, open(self.coredata_file, 'wb'))

class Starter():
    def __init__(self, sdir):
        uifile = os.path.join(priv_dir, 'mesonstart.ui')
        self.ui = uic.loadUi(uifile)
        self.ui.source_entry.setText(sdir)
        self.dialog = PyQt5.QtWidgets.QFileDialog()
        if len(sdir) == 0:
            self.dialog.setDirectory(os.getcwd())
        else:
            self.dialog.setDirectory(sdir)
        self.ui.source_browse_button.clicked.connect(self.src_browse_clicked)
        self.ui.build_browse_button.clicked.connect(self.build_browse_clicked)
        self.ui.cross_browse_button.clicked.connect(self.cross_browse_clicked)
        self.ui.source_entry.textChanged.connect(self.update_button)
        self.ui.build_entry.textChanged.connect(self.update_button)
        self.ui.generate_button.clicked.connect(self.generate)
        self.update_button()
        self.ui.show()

    def generate(self):
        srcdir = self.ui.source_entry.text()
        builddir = self.ui.build_entry.text()
        cross = self.ui.cross_entry.text()
        cmdlist = [os.path.join(os.path.split(__file__)[0], 'meson.py'), srcdir, builddir]
        if cross != '':
            cmdlist += ['--cross', cross]
        pr = ProcessRunner(os.getcwd(), cmdlist)
        rvalue = pr.run()
        if rvalue == 0:
            os.execl(__file__, 'dummy', builddir)

    def update_button(self):
        if self.ui.source_entry.text() == '' or self.ui.build_entry.text() == '':
            self.ui.generate_button.setEnabled(False)
        else:
            self.ui.generate_button.setEnabled(True)

    def src_browse_clicked(self):
        self.dialog.setFileMode(2)
        if self.dialog.exec():
            self.ui.source_entry.setText(self.dialog.selectedFiles()[0])

    def build_browse_clicked(self):
        self.dialog.setFileMode(2)
        if self.dialog.exec():
            self.ui.build_entry.setText(self.dialog.selectedFiles()[0])

    def cross_browse_clicked(self):
        self.dialog.setFileMode(1)
        if self.dialog.exec():
            self.ui.cross_entry.setText(self.dialog.selectedFiles()[0])

# Rather than rewrite all classes and arrays to be
# updateable, just rebuild the entire GUI from
# scratch whenever data on disk changes.

class MesonGuiRespawner():
    def __init__(self, arg):
        self.arg = arg
        self.gui = MesonGui(self, self.arg)

    def respawn(self):
        geo = self.gui.geometry()
        s = self.gui.size()
        self.gui.hide()
        self.gui = MesonGui(self, self.arg)
        self.gui.move(geo.x(), geo.y())
        self.gui.resize(s)
        # Garbage collection takes care of the old gui widget


def run(args): # SPECIAL, Qt wants all args, including command name.
    app = QApplication(sys.argv)
    if len(args) == 1:
        arg = ""
    elif len(args) == 2:
        arg = sys.argv[1]
    else:
        print(sys.argv[0], "<build or source dir>")
        return 1
    if os.path.exists(os.path.join(arg, 'meson-private/coredata.dat')):
        guirespawner = MesonGuiRespawner(arg)
    else:
        runner = Starter(arg)
    return app.exec_()

if __name__ == '__main__':
    sys.exit(run(sys.argv))
