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
import shutil
from .. import mlog
from .. import build
from ..mesonlib import MesonException, extract_as_list, File, unholder, version_compare
from ..dependencies import Dependency, Qt4Dependency, Qt5Dependency, NonExistingExternalProgram
import xml.etree.ElementTree as ET
from . import ModuleReturnValue, get_include_args, ExtensionModule
from ..interpreterbase import noPosargs, permittedKwargs, FeatureNew, FeatureNewKwargs
from ..interpreter import extract_required_kwarg

_QT_DEPS_LUT = {
    4: Qt4Dependency,
    5: Qt5Dependency
}


class QtBaseModule(ExtensionModule):
    tools_detected = False
    rcc_supports_depfiles = False

    def __init__(self, interpreter, qt_version=5):
        ExtensionModule.__init__(self, interpreter)
        self.snippets.add('has_tools')
        self.qt_version = qt_version

    def _detect_tools(self, env, method, required=True):
        if self.tools_detected:
            return
        self.tools_detected = True
        mlog.log('Detecting Qt{version} tools'.format(version=self.qt_version))
        kwargs = {'required': required, 'modules': 'Core', 'method': method}
        qt = _QT_DEPS_LUT[self.qt_version](env, kwargs)
        if qt.found():
            # Get all tools and then make sure that they are the right version
            self.moc, self.uic, self.rcc, self.lrelease = qt.compilers_detect(self.interpreter)
            if version_compare(qt.version, '>=5.14.0'):
                self.rcc_supports_depfiles = True
            else:
                mlog.warning('rcc dependencies will not work properly until you move to Qt >= 5.14:',
                    mlog.bold('https://bugreports.qt.io/browse/QTBUG-45460'), fatal=False)
        else:
            suffix = '-qt{}'.format(self.qt_version)
            self.moc = NonExistingExternalProgram(name='moc' + suffix)
            self.uic = NonExistingExternalProgram(name='uic' + suffix)
            self.rcc = NonExistingExternalProgram(name='rcc' + suffix)
            self.lrelease = NonExistingExternalProgram(name='lrelease' + suffix)

    def qrc_nodes(self, state, rcc_file):
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
                    result.append(child.text)

            return rcc_dirname, result
        except Exception:
            return []

    def parse_qrc_deps(self, state, rcc_file):
        rcc_dirname, nodes = self.qrc_nodes(state, rcc_file)
        result = []
        for resource_path in nodes:
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

    @noPosargs
    @permittedKwargs({'method', 'required'})
    @FeatureNew('qt.has_tools', '0.54.0')
    def has_tools(self, interpreter, state, args, kwargs):
        method = kwargs.get('method', 'auto')
        disabled, required, feature = extract_required_kwarg(kwargs, state.subproject, default=False)
        if disabled:
            mlog.log('qt.has_tools skipped: feature', mlog.bold(feature), 'disabled')
            return False
        self._detect_tools(state.environment, method, required=False)
        for tool in (self.moc, self.uic, self.rcc, self.lrelease):
            if not tool.found():
                if required:
                    raise MesonException('Qt tools not found')
                return False
        return True

    @FeatureNewKwargs('qt.preprocess', '0.49.0', ['uic_extra_arguments'])
    @FeatureNewKwargs('qt.preprocess', '0.44.0', ['moc_extra_arguments'])
    @FeatureNewKwargs('qt.preprocess', '0.49.0', ['rcc_extra_arguments'])
    @permittedKwargs({'moc_headers', 'moc_sources', 'uic_extra_arguments', 'moc_extra_arguments', 'rcc_extra_arguments', 'include_directories', 'dependencies', 'ui_files', 'qresources', 'method'})
    def preprocess(self, state, args, kwargs):
        rcc_files, ui_files, moc_headers, moc_sources, uic_extra_arguments, moc_extra_arguments, rcc_extra_arguments, sources, include_directories, dependencies \
            = [extract_as_list(kwargs, c, pop=True) for c in ['qresources', 'ui_files', 'moc_headers', 'moc_sources', 'uic_extra_arguments', 'moc_extra_arguments', 'rcc_extra_arguments', 'sources', 'include_directories', 'dependencies']]
        sources += args[1:]
        method = kwargs.get('method', 'auto')
        self._detect_tools(state.environment, method)
        err_msg = "{0} sources specified and couldn't find {1}, " \
                  "please check your qt{2} installation"
        if (moc_headers or moc_sources) and not self.moc.found():
            raise MesonException(err_msg.format('MOC', 'moc-qt{}'.format(self.qt_version), self.qt_version))
        if rcc_files:
            if not self.rcc.found():
                raise MesonException(err_msg.format('RCC', 'rcc-qt{}'.format(self.qt_version), self.qt_version))
            # custom output name set? -> one output file, multiple otherwise
            if args:
                qrc_deps = []
                for i in rcc_files:
                    qrc_deps += self.parse_qrc_deps(state, i)
                name = args[0]
                rcc_kwargs = {'input': rcc_files,
                              'output': name + '.cpp',
                              'command': [self.rcc, '-name', name, '-o', '@OUTPUT@', rcc_extra_arguments, '@INPUT@'],
                              'depend_files': qrc_deps}
                res_target = build.CustomTarget(name, state.subdir, state.subproject, rcc_kwargs)
                sources.append(res_target)
            else:
                for rcc_file in rcc_files:
                    qrc_deps = self.parse_qrc_deps(state, rcc_file)
                    if type(rcc_file) is str:
                        basename = os.path.basename(rcc_file)
                    elif type(rcc_file) is File:
                        basename = os.path.basename(rcc_file.fname)
                    name = 'qt' + str(self.qt_version) + '-' + basename.replace('.', '_')
                    rcc_kwargs = {'input': rcc_file,
                                  'output': name + '.cpp',
                                  'command': [self.rcc, '-name', '@BASENAME@', '-o', '@OUTPUT@', rcc_extra_arguments, '@INPUT@'],
                                  'depend_files': qrc_deps}
                    if self.rcc_supports_depfiles:
                        rcc_kwargs['depfile'] = name + '.d'
                        rcc_kwargs['command'] += ['--depfile', '@DEPFILE@']
                    res_target = build.CustomTarget(name, state.subdir, state.subproject, rcc_kwargs)
                    sources.append(res_target)
        if ui_files:
            if not self.uic.found():
                raise MesonException(err_msg.format('UIC', 'uic-qt{}'.format(self.qt_version), self.qt_version))
            arguments = uic_extra_arguments + ['-o', '@OUTPUT@', '@INPUT@']
            ui_kwargs = {'output': 'ui_@BASENAME@.h',
                         'arguments': arguments}
            ui_gen = build.Generator([self.uic], ui_kwargs)
            ui_output = ui_gen.process_files('Qt{} ui'.format(self.qt_version), ui_files, state)
            sources.append(ui_output)
        inc = get_include_args(include_dirs=include_directories)
        compile_args = []
        for dep in unholder(dependencies):
            if isinstance(dep, Dependency):
                for arg in dep.get_compile_args():
                    if arg.startswith('-I') or arg.startswith('-D'):
                        compile_args.append(arg)
            else:
                raise MesonException('Argument is of an unacceptable type {!r}.\nMust be '
                                     'either an external dependency (returned by find_library() or '
                                     'dependency()) or an internal dependency (returned by '
                                     'declare_dependency()).'.format(type(dep).__name__))
        if moc_headers:
            arguments = moc_extra_arguments + inc + compile_args + ['@INPUT@', '-o', '@OUTPUT@']
            moc_kwargs = {'output': 'moc_@BASENAME@.cpp',
                          'arguments': arguments}
            moc_gen = build.Generator([self.moc], moc_kwargs)
            moc_output = moc_gen.process_files('Qt{} moc header'.format(self.qt_version), moc_headers, state)
            sources.append(moc_output)
        if moc_sources:
            arguments = moc_extra_arguments + inc + compile_args + ['@INPUT@', '-o', '@OUTPUT@']
            moc_kwargs = {'output': '@BASENAME@.moc',
                          'arguments': arguments}
            moc_gen = build.Generator([self.moc], moc_kwargs)
            moc_output = moc_gen.process_files('Qt{} moc source'.format(self.qt_version), moc_sources, state)
            sources.append(moc_output)
        return ModuleReturnValue(sources, sources)

    @FeatureNew('qt.compile_translations', '0.44.0')
    @FeatureNewKwargs('qt.compile_translations', '0.56.0', ['qresource'])
    @FeatureNewKwargs('qt.compile_translations', '0.56.0', ['rcc_extra_arguments'])
    @permittedKwargs({'ts_files', 'qresource', 'rcc_extra_arguments', 'install', 'install_dir', 'build_by_default', 'method'})
    def compile_translations(self, state, args, kwargs):
        ts_files, install_dir = [extract_as_list(kwargs, c, pop=True) for c in ['ts_files', 'install_dir']]
        qresource = kwargs.get('qresource')
        if qresource:
            if ts_files:
                raise MesonException('qt.compile_translations: Cannot specify both ts_files and qresource')
            if os.path.dirname(qresource) != '':
                raise MesonException('qt.compile_translations: qresource file name must not contain a subdirectory.')
            qresource = File.from_built_file(state.subdir, qresource)
            infile_abs = os.path.join(state.environment.source_dir, qresource.relative_name())
            outfile_abs = os.path.join(state.environment.build_dir, qresource.relative_name())
            os.makedirs(os.path.dirname(outfile_abs), exist_ok=True)
            shutil.copy2(infile_abs, outfile_abs)
            self.interpreter.add_build_def_file(infile_abs)

            rcc_file, nodes = self.qrc_nodes(state, qresource)
            for c in nodes:
                if c.endswith('.qm'):
                    ts_files.append(c.rstrip('.qm')+'.ts')
                else:
                    raise MesonException('qt.compile_translations: qresource can only contain ts files, found {}'.format(c))
            results = self.preprocess(state, [], {'qresources': qresource, 'rcc_extra_arguments': kwargs.get('rcc_extra_arguments', [])})
        self._detect_tools(state.environment, kwargs.get('method', 'auto'))
        translations = []
        for ts in ts_files:
            if not self.lrelease.found():
                raise MesonException('qt.compile_translations: ' +
                                     self.lrelease.name + ' not found')
            if qresource:
                outdir = os.path.dirname(os.path.normpath(os.path.join(state.subdir, ts)))
                ts = os.path.basename(ts)
            else:
                outdir = state.subdir
            cmd = [self.lrelease, '@INPUT@', '-qm', '@OUTPUT@']
            lrelease_kwargs = {'output': '@BASENAME@.qm',
                               'input': ts,
                               'install': kwargs.get('install', False),
                               'build_by_default': kwargs.get('build_by_default', False),
                               'command': cmd}
            if install_dir is not None:
                lrelease_kwargs['install_dir'] = install_dir
            lrelease_target = build.CustomTarget('qt{}-compile-{}'.format(self.qt_version, ts), outdir, state.subproject, lrelease_kwargs)
            translations.append(lrelease_target)
        if qresource:
            return ModuleReturnValue(results.return_value[0], [results.new_objects, translations])
        else:
            return ModuleReturnValue(translations, translations)
