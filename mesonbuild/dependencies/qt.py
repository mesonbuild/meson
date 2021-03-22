# Copyright 2013-2017 The Meson development team
# Copyright © 2021 Intel Corporation
# SPDX-license-identifier: Apache-2.0

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Dependency finders for the Qt framework."""

import abc
import collections
import re
import os
import typing as T

from . import (
    ExtraFrameworkDependency, ExternalDependency, DependencyException, DependencyMethods,
    PkgConfigDependency,
)
from .. import mlog
from .. import mesonlib
from ..programs import NonExistingExternalProgram, find_external_program

if T.TYPE_CHECKING:
    from ..compilers import Compiler
    from ..environment import Environment
    from ..interpreter import Interpreter
    from ..programs import ExternalProgram


def _qt_get_private_includes(mod_inc_dir: str, module: str, mod_version: str) -> T.List[str]:
    # usually Qt5 puts private headers in /QT_INSTALL_HEADERS/module/VERSION/module/private
    # except for at least QtWebkit and Enginio where the module version doesn't match Qt version
    # as an example with Qt 5.10.1 on linux you would get:
    # /usr/include/qt5/QtCore/5.10.1/QtCore/private/
    # /usr/include/qt5/QtWidgets/5.10.1/QtWidgets/private/
    # /usr/include/qt5/QtWebKit/5.212.0/QtWebKit/private/

    # on Qt4 when available private folder is directly in module folder
    # like /usr/include/QtCore/private/
    if int(mod_version.split('.')[0]) < 5:
        return []

    private_dir = os.path.join(mod_inc_dir, mod_version)
    # fallback, let's try to find a directory with the latest version
    if not os.path.exists(private_dir):
        dirs = [filename for filename in os.listdir(mod_inc_dir)
                if os.path.isdir(os.path.join(mod_inc_dir, filename))]

        for dirname in sorted(dirs, reverse=True):
            if len(dirname.split('.')) == 3:
                private_dir = dirname
                break
    return [private_dir, os.path.join(private_dir, 'Qt' + module)]

class QtExtraFrameworkDependency(ExtraFrameworkDependency):
    def __init__(self, name: str, env: 'Environment', kwargs: T.Dict[str, T.Any], language: T.Optional[str] = None):
        super().__init__(name, env, kwargs, language=language)
        self.mod_name = name[2:]

    def get_compile_args(self, with_private_headers: bool = False, qt_version: str = "0") -> T.List[str]:
        if self.found():
            mod_inc_dir = os.path.join(self.framework_path, 'Headers')
            args = ['-I' + mod_inc_dir]
            if with_private_headers:
                args += ['-I' + dirname for dirname in _qt_get_private_includes(mod_inc_dir, self.mod_name, qt_version)]
            return args
        return []


class QtBaseDependency(ExternalDependency, metaclass=abc.ABCMeta):

    version: T.Optional[str]

    def __init__(self, name: str, env: 'Environment', kwargs: T.Dict[str, T.Any]):
        super().__init__(name, env, kwargs, language='cpp')
        self.qtname = name.capitalize()
        self.qtver = name[-1]
        if self.qtver == "4":
            self.qtpkgname = 'Qt'
        else:
            self.qtpkgname = self.qtname
        self.root = '/usr'
        self.bindir: T.Optional[str] = None
        self.private_headers = T.cast(bool, kwargs.get('private_headers', False))
        mods = mesonlib.stringlistify(mesonlib.extract_as_list(kwargs, 'modules'))
        self.requested_modules = mods
        if not mods:
            raise DependencyException('No ' + self.qtname + '  modules specified.')
        self.from_text = 'pkg-config'

        self.qtmain = T.cast(bool, kwargs.get('main', False))
        if not isinstance(self.qtmain, bool):
            raise DependencyException('"main" argument must be a boolean')

        # Keep track of the detection methods used, for logging purposes.
        methods: T.List[str] = []
        # Prefer pkg-config, then fallback to `qmake -query`
        if DependencyMethods.PKGCONFIG in self.methods:
            mlog.debug('Trying to find qt with pkg-config')
            self._pkgconfig_detect(mods, kwargs)
            methods.append('pkgconfig')
        if not self.is_found and DependencyMethods.QMAKE in self.methods:
            mlog.debug('Trying to find qt with qmake')
            self.from_text = self._qmake_detect(mods, kwargs)
            methods.append('qmake-' + self.name)
            methods.append('qmake')
        if not self.is_found:
            # Reset compile args and link args
            self.compile_args = []
            self.link_args = []
            self.from_text = mlog.format_list(methods)
            self.version = None

    @abc.abstractmethod
    def get_pkgconfig_host_bins(self, core: PkgConfigDependency) -> T.Optional[str]:
        pass

    def compilers_detect(self, interp_obj: 'Interpreter') -> T.Tuple['ExternalProgram', 'ExternalProgram', 'ExternalProgram', 'ExternalProgram']:
        """Detect Qt (4 or 5) moc, uic, rcc in the specified bindir or in PATH"""
        # It is important that this list does not change order as the order of
        # the returned ExternalPrograms will change as well
        bins = ['moc', 'uic', 'rcc', 'lrelease']
        found = {b: NonExistingExternalProgram(name=f'{b}-{self.name}')
                 for b in bins}
        wanted = f'== {self.version}'

        def gen_bins() -> T.Generator[T.Tuple[str, str], None, None]:
            for b in bins:
                if self.bindir:
                    yield os.path.join(self.bindir, b), b
                # prefer the <tool>-qt<version> of the tool to the plain one, as we
                # don't know what the unsuffixed one points to without calling it.
                yield f'{b}-{self.name}', b
                yield b, b

        for b, name in gen_bins():
            if found[name].found():
                continue

            if name == 'lrelease':
                arg = ['-version']
            elif mesonlib.version_compare(self.version, '>= 5'):
                arg = ['--version']
            else:
                arg = ['-v']

            # Ensure that the version of qt and each tool are the same
            def get_version(p: 'ExternalProgram') -> str:
                _, out, err = mesonlib.Popen_safe(p.get_command() + arg)
                if b.startswith('lrelease') or not self.version.startswith('4'):
                    care = out
                else:
                    care = err
                return care.split(' ')[-1].replace(')', '').strip()

            p = interp_obj.find_program_impl([b], required=False,
                                             version_func=get_version,
                                             wanted=wanted).held_object
            if p.found():
                found[name] = p

        # Since we're converting from a list (no size constraints) to a tuple
        # (size constrained), we have to cast. We can impsect the code to see
        # that obviously this is correct since `len(bins) == 4`, but static
        # type checkers can't
        return T.cast(T.Tuple['ExternalProgram', 'ExternalProgram', 'ExternalProgram', 'ExternalProgram'],
                      tuple([found[b] for b in bins]))

    def _pkgconfig_detect(self, mods: T.List[str], kwargs: T.Dict[str, T.Any]) -> None:
        # We set the value of required to False so that we can try the
        # qmake-based fallback if pkg-config fails.
        kwargs['required'] = False
        modules: T.MutableMapping[str, PkgConfigDependency] = collections.OrderedDict()
        for module in mods:
            modules[module] = PkgConfigDependency(self.qtpkgname + module, self.env,
                                                  kwargs, language=self.language)
        for m_name, m in modules.items():
            if not m.found():
                self.is_found = False
                return
            self.compile_args += m.get_compile_args()
            if self.private_headers:
                qt_inc_dir = m.get_pkgconfig_variable('includedir', dict())
                mod_private_dir = os.path.join(qt_inc_dir, 'Qt' + m_name)
                if not os.path.isdir(mod_private_dir):
                    # At least some versions of homebrew don't seem to set this
                    # up correctly. /usr/local/opt/qt/include/Qt + m_name is a
                    # symlink to /usr/local/opt/qt/include, but the pkg-config
                    # file points to /usr/local/Cellar/qt/x.y.z/Headers/, and
                    # the Qt + m_name there is not a symlink, it's a file
                    mod_private_dir = qt_inc_dir
                mod_private_inc = _qt_get_private_includes(mod_private_dir, m_name, m.version)
                for directory in mod_private_inc:
                    self.compile_args.append('-I' + directory)
            self.link_args += m.get_link_args()

        if 'Core' in modules:
            core = modules['Core']
        else:
            corekwargs = {'required': 'false', 'silent': 'true'}
            core = PkgConfigDependency(self.qtpkgname + 'Core', self.env, corekwargs,
                                       language=self.language)
            modules['Core'] = core

        if self.env.machines[self.for_machine].is_windows() and self.qtmain:
            # Check if we link with debug binaries
            debug_lib_name = self.qtpkgname + 'Core' + self._get_modules_lib_suffix(True)
            is_debug = False
            for arg in core.get_link_args():
                if arg == '-l%s' % debug_lib_name or arg.endswith('%s.lib' % debug_lib_name) or arg.endswith('%s.a' % debug_lib_name):
                    is_debug = True
                    break
            libdir = core.get_pkgconfig_variable('libdir', {})
            if not self._link_with_qtmain(is_debug, libdir):
                self.is_found = False
                return

        self.is_found = True
        self.version = m.version
        self.pcdep = list(modules.values())
        # Try to detect moc, uic, rcc
        # Used by self.compilers_detect()
        self.bindir = self.get_pkgconfig_host_bins(core)
        if not self.bindir:
            # If exec_prefix is not defined, the pkg-config file is broken
            prefix = core.get_pkgconfig_variable('exec_prefix', {})
            if prefix:
                self.bindir = os.path.join(prefix, 'bin')

    def search_qmake(self) -> T.Generator['ExternalProgram', None, None]:
        for qmake in ('qmake-' + self.name, 'qmake'):
            yield from find_external_program(self.env, self.for_machine, qmake, 'QMake', [qmake])

    def _qmake_detect(self, mods: T.List[str], kwargs: T.Dict[str, T.Any]) -> T.Optional[str]:
        for qmake in self.search_qmake():
            if not qmake.found():
                continue
            # Check that the qmake is for qt5
            pc, stdo = mesonlib.Popen_safe(qmake.get_command() + ['-v'])[0:2]
            if pc.returncode != 0:
                continue
            if not 'Qt version ' + self.qtver in stdo:
                mlog.log('QMake is not for ' + self.qtname)
                continue
            # Found qmake for Qt5!
            self.qmake = qmake
            break
        else:
            # Didn't find qmake :(
            self.is_found = False
            return None
        self.version = re.search(self.qtver + r'(\.\d+)+', stdo).group(0)
        # Query library path, header path, and binary path
        mlog.log("Found qmake:", mlog.bold(self.qmake.get_path()), '(%s)' % self.version)
        stdo = mesonlib.Popen_safe(self.qmake.get_command() + ['-query'])[1]
        qvars = {}
        for line in stdo.split('\n'):
            line = line.strip()
            if line == '':
                continue
            (k, v) = tuple(line.split(':', 1))
            qvars[k] = v
        # Qt on macOS uses a framework, but Qt for iOS/tvOS does not
        xspec = qvars.get('QMAKE_XSPEC', '')
        if self.env.machines.host.is_darwin() and not any(s in xspec for s in ['ios', 'tvos']):
            mlog.debug("Building for macOS, looking for framework")
            self._framework_detect(qvars, mods, kwargs)
            # Sometimes Qt is built not as a framework (for instance, when using conan pkg manager)
            # skip and fall back to normal procedure then
            if self.is_found:
                return self.qmake.name
            else:
                mlog.debug("Building for macOS, couldn't find framework, falling back to library search")
        incdir = qvars['QT_INSTALL_HEADERS']
        self.compile_args.append('-I' + incdir)
        libdir = qvars['QT_INSTALL_LIBS']
        # Used by self.compilers_detect()
        self.bindir = self.get_qmake_host_bins(qvars)
        self.is_found = True

        # Use the buildtype by default, but look at the b_vscrt option if the
        # compiler supports it.
        is_debug = self.env.coredata.get_option(mesonlib.OptionKey('buildtype')) == 'debug'
        if mesonlib.OptionKey('b_vscrt') in self.env.coredata.options:
            if self.env.coredata.options[mesonlib.OptionKey('b_vscrt')].value in {'mdd', 'mtd'}:
                is_debug = True
        modules_lib_suffix = self._get_modules_lib_suffix(is_debug)

        for module in mods:
            mincdir = os.path.join(incdir, 'Qt' + module)
            self.compile_args.append('-I' + mincdir)

            if module == 'QuickTest':
                define_base = 'QMLTEST'
            elif module == 'Test':
                define_base = 'TESTLIB'
            else:
                define_base = module.upper()
            self.compile_args.append('-DQT_%s_LIB' % define_base)

            if self.private_headers:
                priv_inc = self.get_private_includes(mincdir, module)
                for directory in priv_inc:
                    self.compile_args.append('-I' + directory)
            libfiles = self.clib_compiler.find_library(
                self.qtpkgname + module + modules_lib_suffix, self.env,
                mesonlib.listify(libdir)) # TODO: shouldn't be necissary
            if libfiles:
                libfile = libfiles[0]
            else:
                mlog.log("Could not find:", module,
                         self.qtpkgname + module + modules_lib_suffix,
                         'in', libdir)
                self.is_found = False
                break
            self.link_args.append(libfile)

        if self.env.machines[self.for_machine].is_windows() and self.qtmain:
            if not self._link_with_qtmain(is_debug, libdir):
                self.is_found = False

        return self.qmake.name

    def _get_modules_lib_suffix(self, is_debug: bool) -> str:
        suffix = ''
        if self.env.machines[self.for_machine].is_windows():
            if is_debug:
                suffix += 'd'
            if self.qtver == '4':
                suffix += '4'
        if self.env.machines[self.for_machine].is_darwin():
            if is_debug:
                suffix += '_debug'
        if mesonlib.version_compare(self.version, '>= 5.14.0'):
            if self.env.machines[self.for_machine].is_android():
                cpu_family = self.env.machines[self.for_machine].cpu_family
                if cpu_family == 'x86':
                    suffix += '_x86'
                elif cpu_family == 'x86_64':
                    suffix += '_x86_64'
                elif cpu_family == 'arm':
                    suffix += '_armeabi-v7a'
                elif cpu_family == 'aarch64':
                    suffix += '_arm64-v8a'
                else:
                    mlog.warning('Android target arch {!r} for Qt5 is unknown, '
                                 'module detection may not work'.format(cpu_family))
        return suffix

    def _link_with_qtmain(self, is_debug: bool, libdir: T.Union[str, T.List[str]]) -> bool:
        libdir = mesonlib.listify(libdir)  # TODO: shouldn't be necessary
        base_name = 'qtmaind' if is_debug else 'qtmain'
        qtmain = self.clib_compiler.find_library(base_name, self.env, libdir)
        if qtmain:
            self.link_args.append(qtmain[0])
            return True
        return False

    def _framework_detect(self, qvars: T.Dict[str, str], modules: T.List[str], kwargs: T.Dict[str, T.Any]) -> None:
        libdir = qvars['QT_INSTALL_LIBS']

        # ExtraFrameworkDependency doesn't support any methods
        fw_kwargs = kwargs.copy()
        fw_kwargs.pop('method', None)
        fw_kwargs['paths'] = [libdir]

        for m in modules:
            fname = 'Qt' + m
            mlog.debug('Looking for qt framework ' + fname)
            fwdep = QtExtraFrameworkDependency(fname, self.env, fw_kwargs, language=self.language)
            if fwdep.found():
                self.compile_args.append('-F' + libdir)
                self.compile_args += fwdep.get_compile_args(with_private_headers=self.private_headers,
                                                            qt_version=self.version)
                self.link_args += fwdep.get_link_args()
            else:
                break
        else:
            self.is_found = True
            # Used by self.compilers_detect()
            self.bindir = self.get_qmake_host_bins(qvars)

    @staticmethod
    def get_qmake_host_bins(qvars: T.Dict[str, str]) -> str:
        # Prefer QT_HOST_BINS (qt5, correct for cross and native compiling)
        # but fall back to QT_INSTALL_BINS (qt4)
        if 'QT_HOST_BINS' in qvars:
            return qvars['QT_HOST_BINS']
        return qvars['QT_INSTALL_BINS']

    @staticmethod
    def get_methods() -> T.List[DependencyMethods]:
        return [DependencyMethods.PKGCONFIG, DependencyMethods.QMAKE]

    @staticmethod
    def get_exe_args(compiler: 'Compiler') -> T.List[str]:
        # Originally this was -fPIE but nowadays the default
        # for upstream and distros seems to be -reduce-relocations
        # which requires -fPIC. This may cause a performance
        # penalty when using self-built Qt or on platforms
        # where -fPIC is not required. If this is an issue
        # for you, patches are welcome.
        return compiler.get_pic_args()

    def get_private_includes(self, mod_inc_dir: str, module: str) -> T.List[str]:
        return []

    def log_details(self) -> str:
        module_str = ', '.join(self.requested_modules)
        return 'modules: ' + module_str

    def log_info(self) -> str:
        return f'{self.from_text}'

    def log_tried(self) -> str:
        return self.from_text


class Qt4Dependency(QtBaseDependency):
    def __init__(self, env: 'Environment', kwargs: T.Dict[str, T.Any]):
        QtBaseDependency.__init__(self, 'qt4', env, kwargs)

    @staticmethod
    def get_pkgconfig_host_bins(core: PkgConfigDependency) -> T.Optional[str]:
        # Only return one bins dir, because the tools are generally all in one
        # directory for Qt4, in Qt5, they must all be in one directory. Return
        # the first one found among the bin variables, in case one tool is not
        # configured to be built.
        applications = ['moc', 'uic', 'rcc', 'lupdate', 'lrelease']
        for application in applications:
            try:
                return os.path.dirname(core.get_pkgconfig_variable('%s_location' % application, {}))
            except mesonlib.MesonException:
                pass
        return None


class Qt5Dependency(QtBaseDependency):
    def __init__(self, env: 'Environment', kwargs: T.Dict[str, T.Any]):
        QtBaseDependency.__init__(self, 'qt5', env, kwargs)

    @staticmethod
    def get_pkgconfig_host_bins(core: PkgConfigDependency) -> str:
        return core.get_pkgconfig_variable('host_bins', {})

    def get_private_includes(self, mod_inc_dir: str, module: str) -> T.List[str]:
        return _qt_get_private_includes(mod_inc_dir, module, self.version)


class Qt6Dependency(QtBaseDependency):
    def __init__(self, env: 'Environment', kwargs: T.Dict[str, T.Any]):
        QtBaseDependency.__init__(self, 'qt6', env, kwargs)

    @staticmethod
    def get_pkgconfig_host_bins(core: PkgConfigDependency) -> str:
        return core.get_pkgconfig_variable('host_bins', {})

    def get_private_includes(self, mod_inc_dir: str, module: str) -> T.List[str]:
        return _qt_get_private_includes(mod_inc_dir, module, self.version)
