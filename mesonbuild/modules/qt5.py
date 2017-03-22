# Copyright 2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from .. import mlog
from .. import build
from ..mesonlib import MesonException, Popen_safe
from ..dependencies import Qt5Dependency
from . import ExtensionModule
import xml.etree.ElementTree as ET
from . import ModuleReturnValue

class Qt5Module(ExtensionModule):
    tools_detected = False

    def _detect_tools(self, env, method):
        if self.tools_detected:
            return
        mlog.log('Detecting Qt5 tools')
        # FIXME: We currently require Qt5 to exist while importing the module.
        # We should make it gracefully degrade and not create any targets if
        # the import is marked as 'optional' (not implemented yet)
        kwargs = {'required': 'true', 'modules': 'Core', 'silent': 'true', 'method': method}
        qt5 = Qt5Dependency(env, kwargs)
        # Get all tools and then make sure that they are the right version
        self.moc, self.uic, self.rcc = qt5.compilers_detect()
        # Moc, uic and rcc write their version strings to stderr.
        # Moc and rcc return a non-zero result when doing so.
        # What kind of an idiot thought that was a good idea?
        if self.moc.found():
            stdout, stderr = Popen_safe(self.moc.get_command() + ['-v'])[1:3]
            stdout = stdout.strip()
            stderr = stderr.strip()
            if 'Qt 5' in stderr:
                moc_ver = stderr
            elif '5.' in stdout:
                moc_ver = stdout
            else:
                raise MesonException('Moc preprocessor is not for Qt 5. Output:\n%s\n%s' %
                                     (stdout, stderr))
            mlog.log(' moc:', mlog.green('YES'), '(%s, %s)' %
                     (self.moc.get_path(), moc_ver.split()[-1]))
        else:
            mlog.log(' moc:', mlog.red('NO'))
        if self.uic.found():
            stdout, stderr = Popen_safe(self.uic.get_command() + ['-v'])[1:3]
            stdout = stdout.strip()
            stderr = stderr.strip()
            if 'version 5.' in stderr:
                uic_ver = stderr
            elif '5.' in stdout:
                uic_ver = stdout
            else:
                raise MesonException('Uic compiler is not for Qt 5. Output:\n%s\n%s' %
                                     (stdout, stderr))
            mlog.log(' uic:', mlog.green('YES'), '(%s, %s)' %
                     (self.uic.get_path(), uic_ver.split()[-1]))
        else:
            mlog.log(' uic:', mlog.red('NO'))
        if self.rcc.found():
            stdout, stderr = Popen_safe(self.rcc.get_command() + ['-v'])[1:3]
            stdout = stdout.strip()
            stderr = stderr.strip()
            if 'version 5.' in stderr:
                rcc_ver = stderr
            elif '5.' in stdout:
                rcc_ver = stdout
            else:
                raise MesonException('Rcc compiler is not for Qt 5. Output:\n%s\n%s' %
                                     (stdout, stderr))
            mlog.log(' rcc:', mlog.green('YES'), '(%s, %s)'
                     % (self.rcc.get_path(), rcc_ver.split()[-1]))
        else:
            mlog.log(' rcc:', mlog.red('NO'))
        self.tools_detected = True

    def parse_qrc(self, state, fname):
        abspath = os.path.join(state.environment.source_dir, state.subdir, fname)
        relative_part = os.path.split(fname)[0]
        try:
            tree = ET.parse(abspath)
            root = tree.getroot()
            result = []
            for child in root[0]:
                if child.tag != 'file':
                    mlog.warning("malformed rcc file: ", os.path.join(state.subdir, fname))
                    break
                else:
                    result.append(os.path.join(state.subdir, relative_part, child.text))
            return result
        except Exception:
            return []

    def preprocess(self, state, args, kwargs):
        rcc_files = kwargs.pop('qresources', [])
        if not isinstance(rcc_files, list):
            rcc_files = [rcc_files]
        ui_files = kwargs.pop('ui_files', [])
        if not isinstance(ui_files, list):
            ui_files = [ui_files]
        moc_headers = kwargs.pop('moc_headers', [])
        if not isinstance(moc_headers, list):
            moc_headers = [moc_headers]
        moc_sources = kwargs.pop('moc_sources', [])
        if not isinstance(moc_sources, list):
            moc_sources = [moc_sources]
        sources = kwargs.pop('sources', [])
        if not isinstance(sources, list):
            sources = [sources]
        sources += args[1:]
        method = kwargs.get('method', 'auto')
        self._detect_tools(state.environment, method)
        err_msg = "{0} sources specified and couldn't find {1}, " \
                  "please check your qt5 installation"
        if len(moc_headers) + len(moc_sources) > 0 and not self.moc.found():
            raise MesonException(err_msg.format('MOC', 'moc-qt5'))
        if len(rcc_files) > 0:
            if not self.rcc.found():
                raise MesonException(err_msg.format('RCC', 'rcc-qt5'))
            qrc_deps = []
            for i in rcc_files:
                qrc_deps += self.parse_qrc(state, i)
            if len(args) > 0:
                name = args[0]
            else:
                basename = os.path.split(rcc_files[0])[1]
                name = 'qt5-' + basename.replace('.', '_')
            rcc_kwargs = {'input': rcc_files,
                          'output': name + '.cpp',
                          'command': [self.rcc, '-o', '@OUTPUT@', '@INPUT@'],
                          'depend_files': qrc_deps}
            res_target = build.CustomTarget(name, state.subdir, rcc_kwargs)
            sources.append(res_target)
        if len(ui_files) > 0:
            if not self.uic.found():
                raise MesonException(err_msg.format('UIC', 'uic-qt5'))
            ui_kwargs = {'output': 'ui_@BASENAME@.h',
                         'arguments': ['-o', '@OUTPUT@', '@INPUT@']}
            ui_gen = build.Generator([self.uic], ui_kwargs)
            ui_output = ui_gen.process_files('Qt5 ui', ui_files, state)
            sources.append(ui_output)
        if len(moc_headers) > 0:
            moc_kwargs = {'output': 'moc_@BASENAME@.cpp',
                          'arguments': ['@INPUT@', '-o', '@OUTPUT@']}
            moc_gen = build.Generator([self.moc], moc_kwargs)
            moc_output = moc_gen.process_files('Qt5 moc header', moc_headers, state)
            sources.append(moc_output)
        if len(moc_sources) > 0:
            moc_kwargs = {'output': '@BASENAME@.moc',
                          'arguments': ['@INPUT@', '-o', '@OUTPUT@']}
            moc_gen = build.Generator([self.moc], moc_kwargs)
            moc_output = moc_gen.process_files('Qt5 moc source', moc_sources, state)
            sources.append(moc_output)
        return ModuleReturnValue(sources, sources)

def initialize():
    mlog.warning('rcc dependencies will not work reliably until this upstream issue is fixed:',
                 mlog.bold('https://bugreports.qt.io/browse/QTBUG-45460'))
    return Qt5Module()
