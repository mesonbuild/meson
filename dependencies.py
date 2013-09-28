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

# This file contains the detection logic for external
# dependencies. Mostly just uses pkg-config but also contains
# custom logic for packages that don't provide them.

# Currently one file, should probably be split into a
# package before this gets too big.

import os, stat, glob, subprocess, shutil
from coredata import MesonException
import environment
import mlog

class DependencyException(MesonException):
    def __init__(self, *args, **kwargs):
        MesonException.__init__(self, *args, **kwargs)

class CustomRule:
    def __init__(self, cmd_list, name_templ, src_keyword, name, description):
        self.cmd_list = cmd_list
        self.name_templ = name_templ
        self.src_keyword = src_keyword
        self.name = name
        self.description = description

class Dependency():
    def __init__(self):
        self.name = "null"

    def get_compile_flags(self):
        return []

    def get_link_flags(self):
        return []

    def found(self):
        return False

    def get_sources(self):
        """Source files that need to be added to the target.
        As an example, gtest-all.cc when using GTest."""
        return []

    def get_name(self):
        return self.name

    # Rules for commands to execute before compilation
    # such as Qt's moc preprocessor.
    def get_generate_rules(self):
        return []

    def get_exe_flags(self):
        return []

class PkgConfigDependency(Dependency):
    pkgconfig_found = False

    def __init__(self, name, required):
        Dependency.__init__(self)
        self.name = name
        if not PkgConfigDependency.pkgconfig_found:
            self.check_pkgconfig()

        self.is_found = False
        p = subprocess.Popen(['pkg-config', '--modversion', name], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        out = p.communicate()[0]
        if p.returncode != 0:
            mlog.log('Dependency', name, 'found:', mlog.red('NO'))
            if required:
                raise DependencyException('Required dependency %s not found.' % name)
            self.modversion = 'none'
            self.cflags = []
            self.libs = []
        else:
            mlog.log('Dependency', name, 'found:', mlog.green('YES'))
            self.is_found = True
            self.modversion = out.decode().strip()
            p = subprocess.Popen(['pkg-config', '--cflags', name], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out = p.communicate()[0]
            if p.returncode != 0:
                raise RuntimeError('Could not generate cflags for %s.' % name)
            self.cflags = out.decode().split()

            p = subprocess.Popen(['pkg-config', '--libs', name], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out = p.communicate()[0]
            if p.returncode != 0:
                raise RuntimeError('Could not generate libs for %s.' % name)
            self.libs = out.decode().split()

    def get_modversion(self):
        return self.modversion

    def get_compile_flags(self):
        return self.cflags

    def get_link_flags(self):
        return self.libs

    def check_pkgconfig(self):
        p = subprocess.Popen(['pkg-config', '--version'], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out = p.communicate()[0]
        if p.returncode != 0:
            raise RuntimeError('Pkg-config executable not found.')
        mlog.log('Found pkg-config version %s.' % out.decode().strip())
        PkgConfigDependency.pkgconfig_found = True

    def found(self):
        return self.is_found

class ExternalProgram():
    def __init__(self, name, fullpath=None):
        self.name = name
        if fullpath is not None:
            self.fullpath = fullpath
        else:
            self.fullpath = shutil.which(name)
        if self.found():
            mlog.log('Program', name, 'found:', mlog.green('YES'), '(%s)' % self.fullpath)
        else:
            mlog.log('Program', name, 'found:,', mlog.red('NO'))

    def found(self):
        return self.fullpath is not None

    def get_command(self):
        return self.fullpath

    def get_name(self):
        return self.name

class ExternalLibrary(Dependency):
    def __init__(self, name, fullpath=None):
        super().__init__(self)
        self.name = name
        self.fullpath = fullpath

    def found(self):
        return self.fullpath is not None

    def get_link_flags(self):
        if self.found():
            return [self.fullpath]
        return []

def find_external_dependency(name, kwargs):
    required = kwargs.get('required', True)
    if not isinstance(required, bool):
        raise DependencyException('Keyword "required" must be a boolean.')
    if name in packages:
        dep = packages[name](kwargs)
        if required and not dep.found():
            raise DependencyException('Dependency "%s" not found' % name)
        return dep
    return PkgConfigDependency(name, required)

class BoostDependency(Dependency):
    def __init__(self, kwargs):
        Dependency.__init__(self)
        self.name = 'boost'
        self.incdir = '/usr/include/boost'
        self.src_modules = {}
        self.lib_modules = {}
        self.lib_modules_mt = {}
        self.detect_version()
        self.requested_modules = self.get_requested(kwargs)
        module_str = ', '.join(self.requested_modules)
        if self.version is not None:
            self.detect_src_modules()
            self.detect_lib_modules()
            self.validate_requested()
            mlog.log('Dependency Boost (%s) found:' % module_str, mlog.green('YES'), '(' + self.version + ')')
        else:
            mlog.log("Dependency Boost (%s) found:" % module_str, mlog.red('NO'))

    def get_compile_flags(self):
        return []

    def get_requested(self, kwargs):
        modules = 'modules'
        if not modules in kwargs:
            raise DependencyException('Boost dependency must specify "%s" keyword.' % modules)
        candidates = kwargs[modules]
        if isinstance(candidates, str):
            return [candidates]
        for c in candidates:
            if not isinstance(c, str):
                raise DependencyException('Boost module argument is not a string.')
        return candidates

    def validate_requested(self):
        for m in self.requested_modules:
            if m not in self.src_modules:
                raise DependencyException('Requested Boost module "%s" not found.' % m)

    def found(self):
        return self.version is not None

    def get_version(self):
        return self.version

    def detect_version(self):
        try:
            ifile = open(os.path.join(self.incdir, 'version.hpp'))
        except FileNotFoundError:
            self.version = None
            return
        for line in ifile:
            if line.startswith("#define") and 'BOOST_LIB_VERSION' in line:
                ver = line.split()[-1]
                ver = ver[1:-1]
                self.version = ver.replace('_', '.')
                return
        self.version = None

    def detect_src_modules(self):
        for entry in os.listdir(self.incdir):
            entry = os.path.join(self.incdir, entry)
            if stat.S_ISDIR(os.stat(entry).st_mode):
                self.src_modules[os.path.split(entry)[-1]] = True

    def detect_lib_modules(self):
        globber = 'libboost_*.so' # FIXME, make platform independent.
        libdirs = environment.get_library_dirs()
        for libdir in libdirs:
            for entry in glob.glob(os.path.join(libdir, globber)):
                lib = os.path.basename(entry)
                name = lib.split('.')[0].split('_', 1)[-1]
                # I'm not 100% sure what to do here. Some distros
                # have modules such as thread only as -mt versions.
                if entry.endswith('-mt.so'):
                    self.lib_modules_mt[name] = True
                else:
                    self.lib_modules[name] = True

    def get_link_flags(self):
        flags = [] # Fixme, add -L if necessary.
        for module in self.requested_modules:
            if module in self.lib_modules or module in self.lib_modules_mt:
                linkcmd = '-lboost_' + module
                flags.append(linkcmd)
            elif module + '-mt' in self.lib_modules_mt:
                linkcmd = '-lboost_' + module + '-mt'
                flags.append(linkcmd)
        return flags

    def get_sources(self):
        return []

class GTestDependency(Dependency):
    def __init__(self, kwargs):
        Dependency.__init__(self)
        self.main = kwargs.get('main', False)
        self.name = 'gtest'
        self.libdir = '/usr/lib'
        self.libname = 'libgtest.so'
        self.libmain_name = 'libgtest_main.so'
        self.include_dir = '/usr/include'
        self.src_include_dir = '/usr/src/gtest'
        self.src_dir = '/usr/src/gtest/src'
        self.all_src = os.path.join(self.src_dir, 'gtest-all.cc')
        self.main_src = os.path.join(self.src_dir, 'gtest_main.cc')
        self.detect()

    def found(self):
        return self.is_found

    def detect(self):
        libname = os.path.join(self.libdir, self.libname)
        mainname = os.path.join(self.libdir, self.libmain_name)
        if os.path.exists(libname) and os.path.exists(mainname):
            self.is_found = True
            self.compile_flags = []
            self.link_flags = ['-lgtest']
            if self.main:
                self.link_flags.append('-lgtest_main')
            self.sources = []
            mlog.log('Dependency GTest found:', mlog.green('YES'), '(prebuilt)')
        elif os.path.exists(self.src_dir):
            self.is_found = True
            self.compile_flags = ['-I' + self.src_include_dir]
            self.link_flags = []
            if self.main:
                self.sources = [self.all_src, self.main_src]
            else:
                self.sources = [self.all_src]
            mlog.log('Dependency GTest found:', mlog.green('YES'), '(building self)')
        else:
            mlog.log('Dependency GTest found:', mlog.red('NO'))
            self.is_found = False
        self.link_flags.append('-lpthread')
        return self.is_found

    def get_compile_flags(self):
        arr = []
        if self.include_dir != '/usr/include':
            arr.append('-I' + self.include_dir)
        arr.append('-I' + self.src_include_dir)
        return arr

    def get_link_flags(self):
        return self.link_flags
    def get_version(self):
        return '1.something_maybe'
    def get_sources(self):
        return self.sources

class GMockDependency(Dependency):
    def __init__(self, kwargs):
        Dependency.__init__(self)
        # GMock may be a library or just source.
        # Work with both.
        self.name = 'gmock'
        self.libdir = '/usr/lib'
        self.libname = 'libgmock.so'
        self.src_include_dir = '/usr/src/gmock'
        self.src_dir = '/usr/src/gmock/src'
        self.all_src = os.path.join(self.src_dir, 'gmock-all.cc')
        self.main_src = os.path.join(self.src_dir, 'gmock_main.cc')
        fname = os.path.join(self.libdir, self.libname)
        if os.path.exists(fname):
            self.is_found = True
            self.compile_flags = []
            self.link_flags = ['-lgmock']
            self.sources = []
            mlog.log('Dependency GMock found:', mlog.green('YES'), '(prebuilt)')
        elif os.path.exists(self.src_dir):
            self.is_found = True
            self.compile_flags = ['-I' + self.src_include_dir]
            self.link_flags = []
            if kwargs.get('main', False):
                self.sources = [self.all_src, self.main_src]
            else:
                self.sources = [self.all_src]
            mlog.log('Dependency GMock found:', mlog.green('YES'), '(building self)')
            
        else:
            mlog.log('Dependency GMock found:', mlog.red('NO'))
            self.is_found = False

    def get_version(self):
        return '1.something_maybe'

    def get_compile_flags(self):
        return self.compile_flags

    def get_sources(self):
        return self.sources

    def get_link_flags(self):
        return self.link_flags

    def found(self):
        return self.is_found

class Qt5Dependency(Dependency):
    def __init__(self, kwargs):
        Dependency.__init__(self)
        self.name = 'qt5'
        self.root = '/usr'
        self.modules = []
        mods = kwargs.get('modules', [])
        if isinstance(mods, str):
            mods = [mods]
        for module in mods:
            self.modules.append(PkgConfigDependency('Qt5' + module, False))
        if len(self.modules) == 0:
            raise DependencyException('No Qt5 modules specified.')
        mlog.log('Dependency Qt5 tools:')
        self.find_exes()
    
    def find_exes(self):
        self.moc = ExternalProgram('moc')
        self.uic = ExternalProgram('uic')
        # Moc and uic write their version strings to stderr.
        # Moc returns a non-zero result when doing so.
        # What kind of an idiot thought that was a good idea?
        if self.moc.found():
            mp = subprocess.Popen([self.moc.get_command(), '-v'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            moc_ver = mp.communicate()[1].decode().strip()
            if 'Qt 5' not in moc_ver:
                raise DependencyException('Moc preprocessor is not for Qt 5. Output: %s' % moc_ver)
            mlog.log(' moc:', mlog.green('YES'), '(%s)' % moc_ver)
        else:
            mlog.log(' moc:', mlog.red('NO'))
        if self.uic.found():
            up = subprocess.Popen([self.uic.get_command(), '-v'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            uic_ver = up.communicate()[1].decode().strip()
            if 'version 5.' not in uic_ver:
                raise DependencyException('Uic compiler is not for Qt 5. Output: %s' % uic_ver)
            mlog.log(' uic:', mlog.green('YES'), '(%s)' % uic_ver)
        else:
            mlog.log(' uic:', mlog.red('NO'))

    def get_version(self):
        return self.modules[0].get_version()

    def get_compile_flags(self):
        flags = []
        for m in self.modules:
            flags += m.get_compile_flags()
        return flags

    def get_sources(self):
        return []

    def get_link_flags(self):
        flags = []
        for module in self.modules:
            flags += module.get_link_flags()
        return flags

    def found(self):
        if not self.moc.found():
            return False
        if not self.uic.found():
            return False
        for i in self.modules:
            if not i.found():
                return False
        return True

    def get_generate_rules(self):
        moc_rule = CustomRule([self.moc.get_command(), '@INFILE@', '-o', '@OUTFILE@'],
                              'moc_@BASENAME@.cpp', 'moc_headers', 'moc_compile',
                              'Compiling @INFILE@ with the moc preprocessor')
        ui_rule = CustomRule([self.uic.get_command(), '@INFILE@', '-o', '@OUTFILE@'],
                              'ui_@BASENAME@.h', 'ui_files', 'ui_compile',
                              'Compiling @INFILE@ with the ui compiler')
        return [moc_rule, ui_rule]

    def get_exe_flags(self):
        # Qt5 seems to require this always.
        # Fix this to be more portable, especially to MSVC.
        return ['-fPIE']

class GnuStepDependency(Dependency):
    def __init__(self, kwargs):
        Dependency.__init__(self)
        self.modules = kwargs.get('modules', [])
        self.detect()

    def detect(self):
        confprog = 'gnustep-config'
        gp = subprocess.Popen([confprog, '--help'],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        gp.communicate()
        if gp.returncode != 0:
            self.flags = None
            mlog.log('Dependency GnuStep found:', mlog.red('NO'))
            return
        if 'gui' in self.modules:
            arg = '--gui-libs'
        else:
            arg = '--base-libs'
        fp = subprocess.Popen([confprog, '--objc-flags'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (flagtxt, flagerr) = fp.communicate()
        flagtxt = flagtxt.decode()
        flagerr = flagerr.decode()
        if fp.returncode != 0:
            raise DependencyException('Error getting objc-flags: %s %s' % (flagtxt, flagerr))
        flags = flagtxt.split()
        self.flags = self.filter_flags(flags)
        fp = subprocess.Popen([confprog, arg],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (libtxt, liberr) = fp.communicate()
        libtxt = libtxt.decode()
        liberr = liberr.decode()
        if fp.returncode != 0:
            raise DependencyException('Error getting objc-lib flags: %s %s' % (libtxt, liberr))
        self.libs = self.weird_filter(libtxt.split())
        mlog.log('Dependency GnuStep found:', mlog.green('YES'))

    def weird_filter(self, elems):
        """When building packages, the output of the enclosing Make
is sometimes mixed among the subprocess output. I have no idea
why. As a hack filter out everything that is not a flag."""
        return [e for e in elems if e.startswith('-')]


    def filter_flags(self, flags):
        """gnustep-config returns a bunch of garbage flags such
        as -O2 and so on. Drop everything that is not needed."""
        result = []
        for f in flags:
            if f.startswith('-D') or f.startswith('-f') or \
            f.startswith('-I') or f == '-pthread' or\
            (f.startswith('-W') and not f == '-Wall'):
                result.append(f)
        return result

    def found(self):
        return self.flags is not None
    
    def get_compile_flags(self):
        if self.flags is None:
            return []
        return self.flags
    
    def get_link_flags(self):
        return self.libs

class AppleFrameworks(Dependency):
    def __init__(self, kwargs):
        Dependency.__init__(self)
        modules = kwargs.get('modules', [])
        if isinstance(modules, str):
            modules = [modules]
        if len(modules) == 0:
            raise DependencyException("AppleFrameworks dependency requires at least one module.")
        self.frameworks = modules
    
    def get_link_flags(self):
        flags = []
        for f in self.frameworks:
            flags.append('-framework')
            flags.append(f)
        return flags

    def found(self):
        return environment.is_osx()

def get_dep_identifier(name, kwargs):
    elements = [name]
    modlist = kwargs.get('modules', [])
    if isinstance(modlist, str):
        modlist = [modlist]
    for module in modlist:
        elements.append(module)
    return '/'.join(elements)

# This has to be at the end so the classes it references
# are defined.
packages = {'boost': BoostDependency,
            'gtest': GTestDependency,
            'gmock': GMockDependency,
            'qt5': Qt5Dependency,
            'Qt5': Qt5Dependency, # Qt people sure do love their upper case.
            'gnustep': GnuStepDependency,
            'appleframeworks': AppleFrameworks,
            }
