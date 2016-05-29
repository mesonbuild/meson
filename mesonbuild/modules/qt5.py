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

from .. import dependencies, mlog
import os, subprocess
from .. import build
from ..mesonlib import MesonException
import xml.etree.ElementTree as ET

class Qt5Module():

    def __init__(self):
        mlog.log('Detecting Qt tools.')
        # The binaries have different names on different
        # distros. Joy.
        self.moc = dependencies.ExternalProgram('moc-qt5', silent=True)
        if not self.moc.found():
            self.moc = dependencies.ExternalProgram('moc', silent=True)
        self.uic = dependencies.ExternalProgram('uic-qt5', silent=True)
        if not self.uic.found():
            self.uic = dependencies.ExternalProgram('uic', silent=True)
        self.rcc = dependencies.ExternalProgram('rcc-qt5', silent=True)
        if not self.rcc.found():
            self.rcc = dependencies.ExternalProgram('rcc', silent=True)
        # Moc, uic and rcc write their version strings to stderr.
        # Moc and rcc return a non-zero result when doing so.
        # What kind of an idiot thought that was a good idea?
        if self.moc.found():
            mp = subprocess.Popen(self.moc.get_command() + ['-v'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = mp.communicate()
            stdout = stdout.decode().strip()
            stderr = stderr.decode().strip()
            if 'Qt 5' in stderr:
                moc_ver = stderr
            elif '5.' in stdout:
                moc_ver = stdout
            else:
                raise MesonException('Moc preprocessor is not for Qt 5. Output:\n%s\n%s' %
                                          (stdout, stderr))
            mlog.log(' moc:', mlog.green('YES'), '(%s, %s)' % \
                     (' '.join(self.moc.fullpath), moc_ver.split()[-1]))
        else:
            mlog.log(' moc:', mlog.red('NO'))
        if self.uic.found():
            up = subprocess.Popen(self.uic.get_command() + ['-v'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = up.communicate()
            stdout = stdout.decode().strip()
            stderr = stderr.decode().strip()
            if 'version 5.' in stderr:
                uic_ver = stderr
            elif '5.' in stdout:
                uic_ver = stdout
            else:
                raise MesonException('Uic compiler is not for Qt 5. Output:\n%s\n%s' %
                                          (stdout, stderr))
            mlog.log(' uic:', mlog.green('YES'), '(%s, %s)' % \
                     (' '.join(self.uic.fullpath), uic_ver.split()[-1]))
        else:
            mlog.log(' uic:', mlog.red('NO'))
        if self.rcc.found():
            rp = subprocess.Popen(self.rcc.get_command() + ['-v'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = rp.communicate()
            stdout = stdout.decode().strip()
            stderr = stderr.decode().strip()
            if 'version 5.' in stderr:
                rcc_ver = stderr
            elif '5.' in stdout:
                rcc_ver = stdout
            else:
                raise MesonException('Rcc compiler is not for Qt 5. Output:\n%s\n%s' %
                                          (stdout, stderr))
            mlog.log(' rcc:', mlog.green('YES'), '(%s, %s)'\
                     % (' '.join(self.rcc.fullpath), rcc_ver.split()[-1]))
        else:
            mlog.log(' rcc:', mlog.red('NO'))

    def parse_qrc(self, state, fname):
        abspath = os.path.join(state.environment.source_dir, state.subdir, fname)
        relative_part = os.path.split(fname)[0]
        try:
            tree = ET.parse(abspath)
            root = tree.getroot()
            result = []
            for child in root[0]:
                if child.tag != 'file':
                    mlog.log("Warning, malformed rcc file: ", os.path.join(state.subdir, fname))
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
        srctmp = kwargs.pop('sources', [])
        if not isinstance(srctmp, list):
            srctmp = [srctmp]
        sources = args[1:] + srctmp
        if len(rcc_files) > 0:
            qrc_deps = []
            for i in rcc_files:
                qrc_deps += self.parse_qrc(state, i)
            basename = os.path.split(rcc_files[0])[1]
            rcc_kwargs = {'input' : rcc_files,
                    'output' : basename + '.cpp',
                    'command' : [self.rcc, '-o', '@OUTPUT@', '@INPUT@'],
                    'depend_files' : qrc_deps,
                    }
            res_target = build.CustomTarget(basename.replace('.', '_'),
                                            state.subdir,
                                            rcc_kwargs)
            sources.append(res_target)
        if len(ui_files) > 0:
            ui_kwargs = {'output' : 'ui_@BASENAME@.h',
                         'arguments' : ['-o', '@OUTPUT@', '@INPUT@']}
            ui_gen = build.Generator([self.uic], ui_kwargs)
            ui_output = build.GeneratedList(ui_gen)
            [ui_output.add_file(os.path.join(state.subdir, a)) for a in ui_files]
            sources.append(ui_output)
        if len(moc_headers) > 0:
            moc_kwargs = {'output' : 'moc_@BASENAME@.cpp',
                          'arguments' : ['@INPUT@', '-o', '@OUTPUT@']}
            moc_gen = build.Generator([self.moc], moc_kwargs)
            moc_output = build.GeneratedList(moc_gen)
            [moc_output.add_file(os.path.join(state.subdir, a)) for a in moc_headers]
            sources.append(moc_output)
        if len(moc_sources) > 0:
            moc_kwargs = {'output' : '@BASENAME@.moc',
                          'arguments' : ['@INPUT@', '-o', '@OUTPUT@']}
            moc_gen = build.Generator([self.moc], moc_kwargs)
            moc_output = build.GeneratedList(moc_gen)
            [moc_output.add_file(os.path.join(state.subdir, a)) for a in moc_sources]
            sources.append(moc_output)
        return sources

def initialize():
    mlog.log('Warning, rcc dependencies will not work reliably until this upstream issue is fixed:',
             mlog.bold('https://bugreports.qt.io/browse/QTBUG-45460'))
    return Qt5Module()
