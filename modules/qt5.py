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

import dependencies, mlog, subprocess
import build
from coredata import MesonException

class Qt5Module():
    
    def __init__(self):

        mlog.log('Detecting Qt tools.')
        # The binaries have different names on different
        # distros. Joy.
        self.moc = dependencies.ExternalProgram('moc', silent=True)
        if not self.moc.found():
            self.moc = dependencies.ExternalProgram('moc-qt5', silent=True)
        self.uic = dependencies.ExternalProgram('uic', silent=True)
        if not self.uic.found():
            self.uic = dependencies.ExternalProgram('uic-qt5', silent=True)
        self.rcc = dependencies.ExternalProgram('rcc', silent=True)
        if not self.rcc.found():
            self.rcc = dependencies.ExternalProgram('rcc-qt5', silent=True)
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

    def get_rules(self):
        global moc, uic, rcc
        moc_rule = dependencies.CustomRule(self.moc.get_command() + ['$mocargs', '@INFILE@', '-o', '@OUTFILE@'],
                              'moc_@BASENAME@.cpp', 'moc_headers', 'moc_hdr_compile',
                              'Compiling header @INFILE@ with the moc preprocessor')
        mocsrc_rule = dependencies.CustomRule(self.moc.get_command() + ['$mocargs', '@INFILE@', '-o', '@OUTFILE@'],
                              '@BASENAME@.moc', 'moc_sources', 'moc_src_compile',
                              'Compiling source @INFILE@ with the moc preprocessor')
        ui_rule = dependencies.CustomRule(self.uic.get_command() + ['@INFILE@', '-o', '@OUTFILE@'],
                              'ui_@BASENAME@.h', 'ui_files', 'ui_compile',
                              'Compiling @INFILE@ with the ui compiler')
        rrc_rule = dependencies.CustomRule(self.rcc.get_command() + ['@INFILE@', '-o', '@OUTFILE@',
                               '${rcc_args}'], '@BASENAME@.cpp','qresources',
                              'rc_compile', 'Compiling @INFILE@ with the rrc compiler')
        return [moc_rule, mocsrc_rule, ui_rule, rrc_rule]

    def executable(self, state, args, kwargs):
        rcc_files = kwargs.pop('qresources', [])
        uic_files = kwargs.pop('ui_files', [])
        moc_headers = kwargs.pop('moc_headers', [])
        moc_sources = kwargs.pop('moc_sources', [])
        name = args[0]
        srctmp = kwargs.pop('sources', [])
        if not isinstance(srctmp, list):
            srctmp = [srctmp]
        sources = args[1:] + srctmp
        objects = []
        return build.Executable(name, state.subdir, state.environment.is_cross_build(), sources, objects,
                                state.environment, kwargs)

def initialize():
    return Qt5Module()
