# Copyright 2013-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file contains the detection logic for external dependencies that
# are UI-related.

import os
import re
import shutil
import subprocess
from collections import OrderedDict

from .. import mlog
from .. import mesonlib
from ..mesonlib import (
    MesonException, Popen_safe, extract_as_list, for_windows,
    version_compare_many
)
from ..environment import detect_cpu

from .base import DependencyException, DependencyMethods
from .base import ExternalDependency, ExternalProgram
from .base import ExtraFrameworkDependency, PkgConfigDependency
from .base import ConfigToolDependency


class GLDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('gl', environment, None, kwargs)
        if DependencyMethods.PKGCONFIG in self.methods:
            try:
                pcdep = PkgConfigDependency('gl', environment, kwargs)
                if pcdep.found():
                    self.type_name = 'pkgconfig'
                    self.is_found = True
                    self.compile_args = pcdep.get_compile_args()
                    self.link_args = pcdep.get_link_args()
                    self.version = pcdep.get_version()
                    self.pcdep = pcdep
                    return
            except Exception:
                pass
        if DependencyMethods.SYSTEM in self.methods:
            if mesonlib.is_osx():
                self.is_found = True
                # FIXME: Use AppleFrameworks dependency
                self.link_args = ['-framework', 'OpenGL']
                # FIXME: Detect version using self.compiler
                self.version = '1'
                return
            if mesonlib.is_windows():
                self.is_found = True
                # FIXME: Use self.compiler.find_library()
                self.link_args = ['-lopengl32']
                # FIXME: Detect version using self.compiler
                self.version = '1'
                return

    def get_methods(self):
        if mesonlib.is_osx() or mesonlib.is_windows():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.SYSTEM]
        else:
            return [DependencyMethods.PKGCONFIG]


class GnuStepDependency(ConfigToolDependency):

    tools = ['gnustep-config']
    tool_name = 'gnustep-config'

    def __init__(self, environment, kwargs):
        super().__init__('gnustep', environment, 'objc', kwargs)
        if not self.is_found:
            return
        self.modules = kwargs.get('modules', [])
        self.compile_args = self.filter_args(
            self.get_config_value(['--objc-flags'], 'compile_args'))
        self.link_args = self.weird_filter(self.get_config_value(
            ['--gui-libs' if 'gui' in self.modules else '--base-libs'],
            'link_args'))

    def find_config(self, versions=None):
        tool = self.tools[0]
        try:
            p, out = Popen_safe([tool, '--help'])[:2]
        except (FileNotFoundError, PermissionError):
            return (None, None)
        if p.returncode != 0:
            return (None, None)
        self.config = tool
        found_version = self.detect_version()
        if versions and not version_compare_many(found_version, versions)[0]:
            return (None, found_version)

        return (tool, found_version)

    def weird_filter(self, elems):
        """When building packages, the output of the enclosing Make is
        sometimes mixed among the subprocess output. I have no idea why. As a
        hack filter out everything that is not a flag.
        """
        return [e for e in elems if e.startswith('-')]

    def filter_args(self, args):
        """gnustep-config returns a bunch of garbage args such as -O2 and so
        on. Drop everything that is not needed.
        """
        result = []
        for f in args:
            if f.startswith('-D') \
                    or f.startswith('-f') \
                    or f.startswith('-I') \
                    or f == '-pthread' \
                    or (f.startswith('-W') and not f == '-Wall'):
                result.append(f)
        return result

    def detect_version(self):
        gmake = self.get_config_value(['--variable=GNUMAKE'], 'variable')[0]
        makefile_dir = self.get_config_value(['--variable=GNUSTEP_MAKEFILES'], 'variable')[0]
        # This Makefile has the GNUStep version set
        base_make = os.path.join(makefile_dir, 'Additional', 'base.make')
        # Print the Makefile variable passed as the argument. For instance, if
        # you run the make target `print-SOME_VARIABLE`, this will print the
        # value of the variable `SOME_VARIABLE`.
        printver = "print-%:\n\t@echo '$($*)'"
        env = os.environ.copy()
        # See base.make to understand why this is set
        env['FOUNDATION_LIB'] = 'gnu'
        p, o, e = Popen_safe([gmake, '-f', '-', '-f', base_make,
                              'print-GNUSTEP_BASE_VERSION'],
                             env=env, write=printver, stdin=subprocess.PIPE)
        version = o.strip()
        if not version:
            mlog.debug("Couldn't detect GNUStep version, falling back to '1'")
            # Fallback to setting some 1.x version
            version = '1'
        return version


class QtBaseDependency(ExternalDependency):
    def __init__(self, name, env, kwargs):
        super().__init__(name, env, 'cpp', kwargs)
        self.qtname = name.capitalize()
        self.qtver = name[-1]
        if self.qtver == "4":
            self.qtpkgname = 'Qt'
        else:
            self.qtpkgname = self.qtname
        self.root = '/usr'
        self.bindir = None
        mods = kwargs.get('modules', [])
        if isinstance(mods, str):
            mods = [mods]
        if not mods:
            raise DependencyException('No ' + self.qtname + '  modules specified.')
        type_text = 'cross' if env.is_cross_build() else 'native'
        found_msg = '{} {} {{}} dependency (modules: {}) found:' \
                    ''.format(self.qtname, type_text, ', '.join(mods))
        from_text = 'pkg-config'

        # Keep track of the detection methods used, for logging purposes.
        methods = []
        # Prefer pkg-config, then fallback to `qmake -query`
        if DependencyMethods.PKGCONFIG in self.methods:
            self._pkgconfig_detect(mods, kwargs)
            methods.append('pkgconfig')
        if not self.is_found and DependencyMethods.QMAKE in self.methods:
            from_text = self._qmake_detect(mods, kwargs)
            methods.append('qmake-' + self.name)
            methods.append('qmake')
        if not self.is_found:
            # Reset compile args and link args
            self.compile_args = []
            self.link_args = []
            from_text = '(checked {})'.format(mlog.format_list(methods))
            self.version = 'none'
            if self.required:
                err_msg = '{} {} dependency not found {}' \
                          ''.format(self.qtname, type_text, from_text)
                raise DependencyException(err_msg)
            if not self.silent:
                mlog.log(found_msg.format(from_text), mlog.red('NO'))
            return
        from_text = '`{}`'.format(from_text)
        if not self.silent:
            mlog.log(found_msg.format(from_text), mlog.green('YES'))

    def compilers_detect(self):
        "Detect Qt (4 or 5) moc, uic, rcc in the specified bindir or in PATH"
        if self.bindir:
            moc = ExternalProgram(os.path.join(self.bindir, 'moc'), silent=True)
            uic = ExternalProgram(os.path.join(self.bindir, 'uic'), silent=True)
            rcc = ExternalProgram(os.path.join(self.bindir, 'rcc'), silent=True)
            lrelease = ExternalProgram(os.path.join(self.bindir, 'lrelease'), silent=True)
        else:
            # We don't accept unsuffixed 'moc', 'uic', and 'rcc' because they
            # are sometimes older, or newer versions.
            moc = ExternalProgram('moc-' + self.name, silent=True)
            uic = ExternalProgram('uic-' + self.name, silent=True)
            rcc = ExternalProgram('rcc-' + self.name, silent=True)
            lrelease = ExternalProgram('lrelease-' + self.name, silent=True)
        return moc, uic, rcc, lrelease

    def _pkgconfig_detect(self, mods, kwargs):
        # We set the value of required to False so that we can try the
        # qmake-based fallback if pkg-config fails.
        kwargs['required'] = False
        modules = OrderedDict()
        for module in mods:
            modules[module] = PkgConfigDependency(self.qtpkgname + module, self.env,
                                                  kwargs, language=self.language)
        for m in modules.values():
            if not m.found():
                self.is_found = False
                return
            self.compile_args += m.get_compile_args()
            self.link_args += m.get_link_args()
        self.is_found = True
        self.version = m.version
        self.pcdep = list(modules.values())
        # Try to detect moc, uic, rcc
        if 'Core' in modules:
            core = modules['Core']
        else:
            corekwargs = {'required': 'false', 'silent': 'true'}
            core = PkgConfigDependency(self.qtpkgname + 'Core', self.env, corekwargs,
                                       language=self.language)
            self.pcdep.append(core)
        # Used by self.compilers_detect()
        self.bindir = self.get_pkgconfig_host_bins(core)
        if not self.bindir:
            # If exec_prefix is not defined, the pkg-config file is broken
            prefix = core.get_pkgconfig_variable('exec_prefix', {})
            if prefix:
                self.bindir = os.path.join(prefix, 'bin')

    def _find_qmake(self, qmake):
        # Even when cross-compiling, if we don't get a cross-info qmake, we
        # fallback to using the qmake in PATH because that's what we used to do
        if self.env.is_cross_build():
            qmake = self.env.cross_info.config['binaries'].get('qmake', qmake)
        return ExternalProgram(qmake, silent=True)

    def _qmake_detect(self, mods, kwargs):
        for qmake in ('qmake-' + self.name, 'qmake'):
            self.qmake = self._find_qmake(qmake)
            if not self.qmake.found():
                continue
            # Check that the qmake is for qt5
            pc, stdo = Popen_safe(self.qmake.get_command() + ['-v'])[0:2]
            if pc.returncode != 0:
                continue
            if not 'Qt version ' + self.qtver in stdo:
                mlog.log('QMake is not for ' + self.qtname)
                continue
            # Found qmake for Qt5!
            break
        else:
            # Didn't find qmake :(
            self.is_found = False
            return
        self.version = re.search(self.qtver + '(\.\d+)+', stdo).group(0)
        # Query library path, header path, and binary path
        mlog.log("Found qmake:", mlog.bold(self.qmake.get_name()), '(%s)' % self.version)
        stdo = Popen_safe(self.qmake.get_command() + ['-query'])[1]
        qvars = {}
        for line in stdo.split('\n'):
            line = line.strip()
            if line == '':
                continue
            (k, v) = tuple(line.split(':', 1))
            qvars[k] = v
        if mesonlib.is_osx():
            return self._framework_detect(qvars, mods, kwargs)
        incdir = qvars['QT_INSTALL_HEADERS']
        self.compile_args.append('-I' + incdir)
        libdir = qvars['QT_INSTALL_LIBS']
        # Used by self.compilers_detect()
        self.bindir = self.get_qmake_host_bins(qvars)
        self.is_found = True
        for module in mods:
            mincdir = os.path.join(incdir, 'Qt' + module)
            self.compile_args.append('-I' + mincdir)
            if for_windows(self.env.is_cross_build(), self.env):
                is_debug = self.env.cmd_line_options.buildtype.startswith('debug')
                dbg = 'd' if is_debug else ''
                if self.qtver == '4':
                    base_name = 'Qt' + module + dbg + '4'
                else:
                    base_name = 'Qt5' + module + dbg
                libfile = os.path.join(libdir, base_name + '.lib')
                if not os.path.isfile(libfile):
                    # MinGW can link directly to .dll
                    libfile = os.path.join(self.bindir, base_name + '.dll')
                    if not os.path.isfile(libfile):
                        self.is_found = False
                        break
            else:
                libfile = os.path.join(libdir, 'lib{}{}.so'.format(self.qtpkgname, module))
                if not os.path.isfile(libfile):
                    self.is_found = False
                    break
            self.link_args.append(libfile)
        return qmake

    def _framework_detect(self, qvars, modules, kwargs):
        libdir = qvars['QT_INSTALL_LIBS']
        for m in modules:
            fname = 'Qt' + m
            fwdep = ExtraFrameworkDependency(fname, False, libdir, self.env,
                                             self.language, kwargs)
            self.compile_args.append('-F' + libdir)
            if fwdep.found():
                self.is_found = True
                self.compile_args += fwdep.get_compile_args()
                self.link_args += fwdep.get_link_args()
        # Used by self.compilers_detect()
        self.bindir = self.get_qmake_host_bins(qvars)

    def get_qmake_host_bins(self, qvars):
        # Prefer QT_HOST_BINS (qt5, correct for cross and native compiling)
        # but fall back to QT_INSTALL_BINS (qt4)
        if 'QT_HOST_BINS' in qvars:
            return qvars['QT_HOST_BINS']
        else:
            return qvars['QT_INSTALL_BINS']

    def get_methods(self):
        return [DependencyMethods.PKGCONFIG, DependencyMethods.QMAKE]

    def get_exe_args(self, compiler):
        # Originally this was -fPIE but nowadays the default
        # for upstream and distros seems to be -reduce-relocations
        # which requires -fPIC. This may cause a performance
        # penalty when using self-built Qt or on platforms
        # where -fPIC is not required. If this is an issue
        # for you, patches are welcome.
        return compiler.get_pic_args()


class Qt4Dependency(QtBaseDependency):
    def __init__(self, env, kwargs):
        QtBaseDependency.__init__(self, 'qt4', env, kwargs)

    def get_pkgconfig_host_bins(self, core):
        # Only return one bins dir, because the tools are generally all in one
        # directory for Qt4, in Qt5, they must all be in one directory. Return
        # the first one found among the bin variables, in case one tool is not
        # configured to be built.
        applications = ['moc', 'uic', 'rcc', 'lupdate', 'lrelease']
        for application in applications:
            try:
                return os.path.dirname(core.get_pkgconfig_variable('%s_location' % application, {}))
            except MesonException:
                pass


class Qt5Dependency(QtBaseDependency):
    def __init__(self, env, kwargs):
        QtBaseDependency.__init__(self, 'qt5', env, kwargs)

    def get_pkgconfig_host_bins(self, core):
        return core.get_pkgconfig_variable('host_bins', {})


# There are three different ways of depending on SDL2:
# sdl2-config, pkg-config and OSX framework
class SDL2Dependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('sdl2', environment, None, kwargs)
        kwargs['required'] = False
        if DependencyMethods.PKGCONFIG in self.methods:
            try:
                pcdep = PkgConfigDependency('sdl2', environment, kwargs)
                if pcdep.found():
                    self.type_name = 'pkgconfig'
                    self.is_found = True
                    self.compile_args = pcdep.get_compile_args()
                    self.link_args = pcdep.get_link_args()
                    self.version = pcdep.get_version()
                    self.pcdep = pcdep
                    return
            except Exception as e:
                mlog.debug('SDL 2 not found via pkgconfig. Trying next, error was:', str(e))
        if DependencyMethods.CONFIG_TOOL in self.methods:
            try:
                ctdep = ConfigToolDependency.factory(
                    'sdl2', environment, None, kwargs, ['sdl2-config'], 'sdl2-config')
                if ctdep.found():
                    self.type_name = 'config-tool'
                    self.config = ctdep.config
                    self.version = ctdep.version
                    self.compile_args = ctdep.get_config_value(['--cflags'], 'compile_args')
                    self.links_args = ctdep.get_config_value(['--libs'], 'link_args')
                    self.is_found = True
                    return
            except Exception as e:
                mlog.debug('SDL 2 not found via sdl2-config. Trying next, error was:', str(e))
        if DependencyMethods.EXTRAFRAMEWORK in self.methods:
            if mesonlib.is_osx():
                fwdep = ExtraFrameworkDependency('sdl2', False, None, self.env,
                                                 self.language, kwargs)
                if fwdep.found():
                    self.is_found = True
                    self.compile_args = fwdep.get_compile_args()
                    self.link_args = fwdep.get_link_args()
                    self.version = '2'  # FIXME
                    return
            mlog.log('Dependency', mlog.bold('sdl2'), 'found:', mlog.red('NO'))

    def get_methods(self):
        if mesonlib.is_osx():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL, DependencyMethods.EXTRAFRAMEWORK]
        else:
            return [DependencyMethods.PKGCONFIG, DependencyMethods.CONFIG_TOOL]


class WxDependency(ConfigToolDependency):

    tools = ['wx-config-3.0', 'wx-config']
    tool_name = 'wx-config'

    def __init__(self, environment, kwargs):
        super().__init__('WxWidgets', environment, None, kwargs)
        if not self.is_found:
            return
        self.requested_modules = self.get_requested(kwargs)
        # wx-config seems to have a cflags as well but since it requires C++,
        # this should be good, at least for now.
        self.compile_args = self.get_config_value(['--cxxflags'], 'compile_args')
        self.link_args = self.get_config_value(['--libs'], 'link_args')

    def get_requested(self, kwargs):
        if 'modules' not in kwargs:
            return []
        candidates = extract_as_list(kwargs, 'modules')
        for c in candidates:
            if not isinstance(c, str):
                raise DependencyException('wxwidgets module argument is not a string')
        return candidates


class VulkanDependency(ExternalDependency):
    def __init__(self, environment, kwargs):
        super().__init__('vulkan', environment, None, kwargs)

        if DependencyMethods.PKGCONFIG in self.methods:
            try:
                pcdep = PkgConfigDependency('vulkan', environment, kwargs)
                if pcdep.found():
                    self.type_name = 'pkgconfig'
                    self.is_found = True
                    self.compile_args = pcdep.get_compile_args()
                    self.link_args = pcdep.get_link_args()
                    self.version = pcdep.get_version()
                    self.pcdep = pcdep
                    return
            except Exception:
                pass

        if DependencyMethods.SYSTEM in self.methods:
            try:
                self.vulkan_sdk = os.environ['VULKAN_SDK']
                if not os.path.isabs(self.vulkan_sdk):
                    raise DependencyException('VULKAN_SDK must be an absolute path.')
            except KeyError:
                self.vulkan_sdk = None

            if self.vulkan_sdk:
                # TODO: this config might not work on some platforms, fix bugs as reported
                # we should at least detect other 64-bit platforms (e.g. armv8)
                lib_name = 'vulkan'
                if mesonlib.is_windows():
                    lib_name = 'vulkan-1'
                    lib_dir = 'Lib32'
                    inc_dir = 'Include'
                    if detect_cpu({}) == 'x86_64':
                        lib_dir = 'Lib'
                else:
                    lib_name = 'vulkan'
                    lib_dir = 'lib'
                    inc_dir = 'include'

                # make sure header and lib are valid
                inc_path = os.path.join(self.vulkan_sdk, inc_dir)
                header = os.path.join(inc_path, 'vulkan', 'vulkan.h')
                lib_path = os.path.join(self.vulkan_sdk, lib_dir)
                find_lib = self.compiler.find_library(lib_name, environment, lib_path)

                if not find_lib:
                    raise DependencyException('VULKAN_SDK point to invalid directory (no lib)')

                if not os.path.isfile(header):
                    raise DependencyException('VULKAN_SDK point to invalid directory (no include)')

                self.type_name = 'vulkan_sdk'
                self.is_found = True
                self.compile_args.append('-I' + inc_path)
                self.link_args.append('-L' + lib_path)
                self.link_args.append('-l' + lib_name)

                # TODO: find a way to retrieve the version from the sdk?
                # Usually it is a part of the path to it (but does not have to be)
                self.version = '1'
                return
            else:
                # simply try to guess it, usually works on linux
                libs = self.compiler.find_library('vulkan', environment, [])
                if libs is not None and self.compiler.has_header('vulkan/vulkan.h', '', environment):
                    self.type_name = 'system'
                    self.is_found = True
                    self.version = 1 # TODO
                    for lib in libs:
                        self.link_args.append(lib)
                    return

    def get_methods(self):
        return [DependencyMethods.PKGCONFIG, DependencyMethods.SYSTEM]
