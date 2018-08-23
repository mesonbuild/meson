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
from ..mesonlib import MesonException, Popen_safe, extract_as_list, File
from ..dependencies import Dependency, Qt4Dependency, Qt5Dependency
import xml.etree.ElementTree as ET
from . import ModuleReturnValue, get_include_args
from ..interpreterbase import permittedKwargs, FeatureNewKwargs

_QT_DEPS_LUT = {
    4: Qt4Dependency,
    5: Qt5Dependency
}


class QtBaseModule:
    tools_detected = False

    def __init__(self, qt_version=5):
        self.qt_version = qt_version

    def _detect_tools(self, env, method):
        if self.tools_detected:
            return
        mlog.log('Detecting Qt{version} tools'.format(version=self.qt_version))
        # FIXME: We currently require QtX to exist while importing the module.
        # We should make it gracefully degrade and not create any targets if
        # the import is marked as 'optional' (not implemented yet)
        kwargs = {'required': 'true', 'modules': 'Core', 'silent': 'true', 'method': method}
        qt = _QT_DEPS_LUT[self.qt_version](env, kwargs)
        # Get all tools and then make sure that they are the right version
        self.moc, self.uic, self.rcc, self.lrelease = qt.compilers_detect()
        # Moc, uic and rcc write their version strings to stderr.
        # Moc and rcc return a non-zero result when doing so.
        # What kind of an idiot thought that was a good idea?
        for compiler, compiler_name in ((self.moc, "Moc"), (self.uic, "Uic"), (self.rcc, "Rcc"), (self.lrelease, "lrelease")):
            if compiler.found():
                # Workaround since there is no easy way to know which tool/version support which flag
                for flag in ['-v', '-version']:
                    p, stdout, stderr = Popen_safe(compiler.get_command() + [flag])[0:3]
                    if p.returncode == 0:
                        break
                stdout = stdout.strip()
                stderr = stderr.strip()
                if 'Qt {}'.format(self.qt_version) in stderr:
                    compiler_ver = stderr
                elif 'version {}.'.format(self.qt_version) in stderr:
                    compiler_ver = stderr
                elif ' {}.'.format(self.qt_version) in stdout:
                    compiler_ver = stdout
                else:
                    raise MesonException('{name} preprocessor is not for Qt {version}. Output:\n{stdo}\n{stderr}'.format(
                        name=compiler_name, version=self.qt_version, stdo=stdout, stderr=stderr))
                mlog.log(' {}:'.format(compiler_name.lower()), mlog.green('YES'), '({path}, {version})'.format(
                    path=compiler.get_path(), version=compiler_ver.split()[-1]))
            else:
                mlog.log(' {}:'.format(compiler_name.lower()), mlog.red('NO'))
        self.tools_detected = True

    def parse_qrc(self, state, rcc_file):
        if type(rcc_file) is str:
            abspath = os.path.join(state.environment.source_dir, state.subdir, rcc_file)
            rcc_dirname = os.path.dirname(abspath)
        elif type(rcc_file) is File:
            abspath = rcc_file.absolute_path(state.environment.source_dir, state.environment.build_dir)
            rcc_dirname = os.path.dirname(abspath)

        try:
            tree = ET.parse(abspath)
            root = tree.getroot()
            result = []
            for child in root[0]:
                if child.tag != 'file':
                    mlog.warning("malformed rcc file: ", os.path.join(state.subdir, rcc_file))
                    break
                else:
                    resource_path = child.text
                    # We need to guess if the pointed resource is:
                    #   a) in build directory -> implies a generated file
                    #   b) in source directory
                    #   c) somewhere else external dependency file to bundle
                    #
                    # Also from qrc documentation: relative path are always from qrc file
                    # So relative path must always be computed from qrc file !
                    if os.path.isabs(resource_path):
                        # a)
                        if resource_path.startswith(os.path.abspath(state.environment.build_dir)):
                            resource_relpath = os.path.relpath(resource_path, state.environment.build_dir)
                            result.append(File(is_built=True, subdir='', fname=resource_relpath))
                        # either b) or c)
                        else:
                            result.append(File(is_built=False, subdir=state.subdir, fname=resource_path))
                    else:
                        path_from_rcc = os.path.normpath(os.path.join(rcc_dirname, resource_path))
                        # a)
                        if path_from_rcc.startswith(state.environment.build_dir):
                            result.append(File(is_built=True, subdir=state.subdir, fname=resource_path))
                        # b)
                        else:
                            result.append(File(is_built=False, subdir=state.subdir, fname=path_from_rcc))
            return result
        except Exception:
            return []

    @FeatureNewKwargs('qt.preprocess', '0.44.0', ['moc_extra_arguments'])
    @permittedKwargs({'moc_headers', 'moc_sources', 'moc_extra_arguments', 'include_directories', 'dependencies', 'ui_files', 'qresources', 'method'})
    def preprocess(self, state, args, kwargs):
        rcc_files, ui_files, moc_headers, moc_sources, moc_extra_arguments, sources, include_directories, dependencies \
            = extract_as_list(kwargs, 'qresources', 'ui_files', 'moc_headers', 'moc_sources', 'moc_extra_arguments', 'sources', 'include_directories', 'dependencies', pop = True)
        sources += args[1:]
        method = kwargs.get('method', 'auto')
        self._detect_tools(state.environment, method)
        err_msg = "{0} sources specified and couldn't find {1}, " \
                  "please check your qt{2} installation"
        if len(moc_headers) + len(moc_sources) > 0 and not self.moc.found():
            raise MesonException(err_msg.format('MOC', 'moc-qt{}'.format(self.qt_version), self.qt_version))
        if len(rcc_files) > 0:
            if not self.rcc.found():
                raise MesonException(err_msg.format('RCC', 'rcc-qt{}'.format(self.qt_version), self.qt_version))
            # custom output name set? -> one output file, multiple otherwise
            if len(args) > 0:
                qrc_deps = []
                for i in rcc_files:
                    qrc_deps += self.parse_qrc(state, i)
                name = args[0]
                rcc_kwargs = {'input': rcc_files,
                              'output': name + '.cpp',
                              'command': [self.rcc, '-name', name, '-o', '@OUTPUT@', '@INPUT@'],
                              'depend_files': qrc_deps}
                res_target = build.CustomTarget(name, state.subdir, state.subproject, rcc_kwargs)
                sources.append(res_target)
            else:
                for rcc_file in rcc_files:
                    qrc_deps = self.parse_qrc(state, rcc_file)
                    if type(rcc_file) is str:
                        basename = os.path.basename(rcc_file)
                    elif type(rcc_file) is File:
                        basename = os.path.basename(rcc_file.fname)
                    name = 'qt' + str(self.qt_version) + '-' + basename.replace('.', '_')
                    rcc_kwargs = {'input': rcc_file,
                                  'output': name + '.cpp',
                                  'command': [self.rcc, '-name', '@BASENAME@', '-o', '@OUTPUT@', '@INPUT@'],
                                  'depend_files': qrc_deps}
                    res_target = build.CustomTarget(name, state.subdir, state.subproject, rcc_kwargs)
                    sources.append(res_target)
        if len(ui_files) > 0:
            if not self.uic.found():
                raise MesonException(err_msg.format('UIC', 'uic-qt' + self.qt_version))
            ui_kwargs = {'output': 'ui_@BASENAME@.h',
                         'arguments': ['-o', '@OUTPUT@', '@INPUT@']}
            ui_gen = build.Generator([self.uic], ui_kwargs)
            ui_output = ui_gen.process_files('Qt{} ui'.format(self.qt_version), ui_files, state)
            sources.append(ui_output)
        inc = get_include_args(include_dirs=include_directories)
        compile_args = []
        for dep in dependencies:
            if hasattr(dep, 'held_object'):
                dep = dep.held_object
            if isinstance(dep, Dependency):
                for arg in dep.get_compile_args():
                    if arg.startswith('-I') or arg.startswith('-D'):
                        compile_args.append(arg)
            else:
                raise MesonException('Argument is of an unacceptable type {!r}.\nMust be '
                                     'either an external dependency (returned by find_library() or '
                                     'dependency()) or an internal dependency (returned by '
                                     'declare_dependency()).'.format(type(dep).__name__))
        if len(moc_headers) > 0:
            arguments = moc_extra_arguments + inc + compile_args + ['@INPUT@', '-o', '@OUTPUT@']
            moc_kwargs = {'output': 'moc_@BASENAME@.cpp',
                          'arguments': arguments}
            moc_gen = build.Generator([self.moc], moc_kwargs)
            moc_output = moc_gen.process_files('Qt{} moc header'.format(self.qt_version), moc_headers, state)
            sources.append(moc_output)
        if len(moc_sources) > 0:
            arguments = moc_extra_arguments + inc + compile_args + ['@INPUT@', '-o', '@OUTPUT@']
            moc_kwargs = {'output': '@BASENAME@.moc',
                          'arguments': arguments}
            moc_gen = build.Generator([self.moc], moc_kwargs)
            moc_output = moc_gen.process_files('Qt{} moc source'.format(self.qt_version), moc_sources, state)
            sources.append(moc_output)
        return ModuleReturnValue(sources, sources)

    @FeatureNewKwargs('build target', '0.40.0', ['build_by_default'])
    @permittedKwargs({'ts_files', 'install', 'install_dir', 'build_by_default', 'method'})
    def compile_translations(self, state, args, kwargs):
        ts_files, install_dir = extract_as_list(kwargs, 'ts_files', 'install_dir', pop=True)
        self._detect_tools(state.environment, kwargs.get('method', 'auto'))
        translations = []
        for ts in ts_files:
            cmd = [self.lrelease, '@INPUT@', '-qm', '@OUTPUT@']
            lrelease_kwargs = {'output': '@BASENAME@.qm',
                               'input': ts,
                               'install': kwargs.get('install', False),
                               'build_by_default': kwargs.get('build_by_default', False),
                               'command': cmd}
            if install_dir is not None:
                lrelease_kwargs['install_dir'] = install_dir
            lrelease_target = build.CustomTarget('qt{}-compile-{}'.format(self.qt_version, ts), state.subdir, state.subproject, lrelease_kwargs)
            translations.append(lrelease_target)
        return ModuleReturnValue(translations, translations)
