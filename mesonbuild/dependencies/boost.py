# Copyright 2013-2020 The Meson development team

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
import re
import functools
import typing as T
from pathlib import Path

from .. import mlog
from .. import mesonlib
from ..environment import Environment

from .base import (DependencyException, ExternalDependency)
from .misc import threads_factory

# On windows 3 directory layouts are supported:
# * The default layout (versioned) installed:
#   - $BOOST_ROOT/include/boost-x_x/boost/*.hpp
#   - $BOOST_ROOT/lib/*.lib
# * The non-default layout (system) installed:
#   - $BOOST_ROOT/include/boost/*.hpp
#   - $BOOST_ROOT/lib/*.lib
# * The pre-built binaries from sf.net:
#   - $BOOST_ROOT/boost/*.hpp
#   - $BOOST_ROOT/lib<arch>-<compiler>/*.lib where arch=32/64 and compiler=msvc-14.1
#
# Note that we should also try to support:
# mingw-w64 / Windows : libboost_<module>-mt.a            (location = <prefix>/mingw64/lib/)
#                       libboost_<module>-mt.dll.a
#
# The `modules` argument accept library names. This is because every module that
# has libraries to link against also has multiple options regarding how to
# link. See for example:
# * http://www.boost.org/doc/libs/1_65_1/libs/test/doc/html/boost_test/usage_variants.html
# * http://www.boost.org/doc/libs/1_65_1/doc/html/stacktrace/configuration_and_build.html
# * http://www.boost.org/doc/libs/1_65_1/libs/math/doc/html/math_toolkit/main_tr1.html

# **On Unix**, official packaged versions of boost libraries follow the following schemes:
#
# Linux / Debian:   libboost_<module>.so -> libboost_<module>.so.1.66.0
# Linux / Red Hat:  libboost_<module>.so -> libboost_<module>.so.1.66.0
# Linux / OpenSuse: libboost_<module>.so -> libboost_<module>.so.1.66.0
# Win   / Cygwin:   libboost_<module>.dll.a                                 (location = /usr/lib)
#                   libboost_<module>.a
#                   cygboost_<module>_1_64.dll                              (location = /usr/bin)
# Win   / VS:       boost_<module>-vc<ver>-mt[-gd]-<arch>-1_67.dll          (location = C:/local/boost_1_67_0)
# Mac   / homebrew: libboost_<module>.dylib + libboost_<module>-mt.dylib    (location = /usr/local/lib)
# Mac   / macports: libboost_<module>.dylib + libboost_<module>-mt.dylib    (location = /opt/local/lib)
#
# Its not clear that any other abi tags (e.g. -gd) are used in official packages.
#
# On Linux systems, boost libs have multithreading support enabled, but without the -mt tag.
#
# Boost documentation recommends using complex abi tags like "-lboost_regex-gcc34-mt-d-1_36".
# (See http://www.boost.org/doc/libs/1_66_0/more/getting_started/unix-variants.html#library-naming)
# However, its not clear that any Unix distribution follows this scheme.
# Furthermore, the boost documentation for unix above uses examples from windows like
#   "libboost_regex-vc71-mt-d-x86-1_34.lib", so apparently the abi tags may be more aimed at windows.
#
# We follow the following strategy for finding modules:
# A) Detect potential boost root directories (uses also BOOST_ROOT env var)
# B) Foreach candidate
#   1. Look for the boost headers (boost/version.pp)
#   2. Find all boost libraries
#     2.1 Add all libraries in lib*
#     2.2 Filter out non boost libraries
#     2.3 Filter the renaining libraries based on the meson requirements (static/shared, etc.)
#     2.4 Ensure that all libraries have the same boost tag (and are thus compatible)
#   3. Select the libraries matching the requested modules

@functools.total_ordering
class BoostIncludeDir():
    def __init__(self, path: Path, version_int: int):
        self.path = path
        self.version_int = version_int
        major = int(self.version_int / 100000)
        minor = int((self.version_int / 100) % 1000)
        patch = int(self.version_int % 100)
        self.version = '{}.{}.{}'.format(major, minor, patch)
        self.version_lib = '{}_{}'.format(major, minor)

    def __repr__(self) -> str:
        return '<BoostIncludeDir: {} -- {}>'.format(self.version, self.path)

    def __lt__(self, other: T.Any) -> bool:
        if isinstance(other, BoostIncludeDir):
            return (self.version_int, self.path) < (other.version_int, other.path)
        return NotImplemented

@functools.total_ordering
class BoostLibraryFile():
    # Python libraries are special because of the included
    # minor version in the module name.
    boost_python_libs = ['boost_python', 'boost_numpy']
    reg_python_mod_split = re.compile(r'(boost_[a-zA-Z]+)([0-9]*)')

    reg_abi_tag = re.compile(r'^s?g?y?d?p?n?$')
    reg_ver_tag = re.compile(r'^[0-9_]+$')

    def __init__(self, path: Path):
        self.path = path
        self.name = self.path.name

        # Initialize default properties
        self.static = False
        self.toolset = ''
        self.arch = ''
        self.version_lib = ''
        self.mt = True

        self.runtime_static = False
        self.runtime_debug = False
        self.python_debug = False
        self.debug = False
        self.stlport = False
        self.deprecated_iostreams = False

        # Post process the library name
        name_parts = self.name.split('.')
        self.basename = name_parts[0]
        self.suffixes = name_parts[1:]
        self.suffixes = [x for x in self.suffixes if not x.isdigit()]
        self.nvsuffix = '.'.join(self.suffixes)  # Used for detecting the library type
        self.nametags = self.basename.split('-')
        self.mod_name = self.nametags[0]
        if self.mod_name.startswith('lib'):
            self.mod_name = self.mod_name[3:]

        # Detecting library type
        if self.nvsuffix in ['so', 'dll', 'dll.a', 'dll.lib', 'dylib']:
            self.static = False
        elif self.nvsuffix in ['a', 'lib']:
            self.static = True
        else:
            raise DependencyException('Unable to process library extension "{}" ({})'.format(self.nvsuffix, self.path))

        # boost_.lib is the dll import library
        if self.basename.startswith('boost_') and self.nvsuffix == 'lib':
            self.static = False

        # Process tags
        tags = self.nametags[1:]
        if not tags:
            return

        # Without any tags mt is assumed, however, an absents of mt in the name
        # with tags present indicates that the lib was build without mt support
        self.mt = False
        for i in tags:
            if i == 'mt':
                self.mt = True
            elif len(i) == 3 and i[1:] in ['32', '64']:
                self.arch = i
            elif BoostLibraryFile.reg_abi_tag.match(i):
                self.runtime_static = 's' in i
                self.runtime_debug = 'g' in i
                self.python_debug = 'y' in i
                self.debug = 'd' in i
                self.stlport = 'p' in i
                self.deprecated_iostreams = 'n' in i
            elif BoostLibraryFile.reg_ver_tag.match(i):
                self.version_lib = i
            else:
                self.toolset = i

    def __repr__(self) -> str:
        return '<LIB: {} {:<32} {}>'.format(self.abitag, self.mod_name, self.path)

    def __lt__(self, other: T.Any) -> bool:
        if isinstance(other, BoostLibraryFile):
            return (
                self.mod_name, self.version_lib, self.arch, self.static,
                not self.mt, not self.runtime_static,
                not self.debug, self.runtime_debug, self.python_debug,
                self.stlport, self.deprecated_iostreams,
                self.name,
            ) < (
                other.mod_name, other.version_lib, other.arch, other.static,
                not other.mt, not other.runtime_static,
                not other.debug, other.runtime_debug, other.python_debug,
                other.stlport, other.deprecated_iostreams,
                other.name,
            )
        return NotImplemented

    def __eq__(self, other: T.Any) -> bool:
        if isinstance(other, BoostLibraryFile):
            return self.name == other.name
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.name)

    @property
    def abitag(self) -> str:
        abitag = ''
        abitag += 'S' if self.static else '-'
        abitag += 'M' if self.mt else '-'
        abitag += ' '
        abitag += 's' if self.runtime_static else '-'
        abitag += 'g' if self.runtime_debug else '-'
        abitag += 'y' if self.python_debug else '-'
        abitag += 'd' if self.debug else '-'
        abitag += 'p' if self.stlport else '-'
        abitag += 'n' if self.deprecated_iostreams else '-'
        abitag += ' ' + (self.arch or '???')
        abitag += ' ' + (self.toolset or '?')
        abitag += ' ' + (self.version_lib or 'x_xx')
        return abitag

    def is_boost(self) -> bool:
        return any([self.name.startswith(x) for x in ['libboost_', 'boost_']])

    def is_python_lib(self) -> bool:
        return any([self.mod_name.startswith(x) for x in BoostLibraryFile.boost_python_libs])

    def mod_name_matches(self, mod_name: str) -> bool:
        if self.mod_name == mod_name:
            return True
        if not self.is_python_lib():
            return False

        m_cur = BoostLibraryFile.reg_python_mod_split.match(self.mod_name)
        m_arg = BoostLibraryFile.reg_python_mod_split.match(mod_name)

        if not m_cur or not m_arg:
            return False

        if m_cur.group(1) != m_arg.group(1):
            return False

        cur_vers = m_cur.group(2)
        arg_vers = m_arg.group(2)

        # Always assume python 2 if nothing is specified
        if not arg_vers:
            arg_vers = '2'

        return cur_vers.startswith(arg_vers)

    def version_matches(self, version_lib: str) -> bool:
        # If no version tag is present, assume that it fits
        if not self.version_lib or not version_lib:
            return True
        return self.version_lib == version_lib

    def arch_matches(self, arch: str) -> bool:
        # If no version tag is present, assume that it fits
        if not self.arch or not arch:
            return True
        return self.arch == arch

    def vscrt_matches(self, vscrt: str) -> bool:
        # If no vscrt tag present, assume that it fits  ['/MD', '/MDd', '/MT', '/MTd']
        if not vscrt:
            return True
        if vscrt in ['/MD', '-MD']:
            return not self.runtime_static and not self.runtime_debug
        elif vscrt in ['/MDd', '-MDd']:
            return not self.runtime_static and self.runtime_debug
        elif vscrt in ['/MT', '-MT']:
            return (self.runtime_static or not self.static) and not self.runtime_debug
        elif vscrt in ['/MTd', '-MTd']:
            return (self.runtime_static or not self.static) and self.runtime_debug

        mlog.warning('Boost: unknow vscrt tag {}. This may cause the compilation to fail. Please consider reporting this as a bug.'.format(vscrt), once=True)
        return True

    def get_compiler_args(self) -> T.List[str]:
        args = []  # type: T.List[str]
        if self.mod_name in boost_libraries:
            libdef = boost_libraries[self.mod_name]  # type: BoostLibrary
            if self.static:
                args += libdef.static
            else:
                args += libdef.shared
            if self.mt:
                args += libdef.multi
            else:
                args += libdef.single
        return args

    def get_link_args(self) -> T.List[str]:
        return [self.path.as_posix()]

class BoostDependency(ExternalDependency):
    def __init__(self, environment: Environment, kwargs):
        super().__init__('boost', environment, kwargs, language='cpp')
        self.debug = environment.coredata.get_builtin_option('buildtype').startswith('debug')
        self.multithreading = kwargs.get('threading', 'multi') == 'multi'

        self.boost_root = None

        # Extract and validate modules
        self.modules = mesonlib.extract_as_list(kwargs, 'modules')  # type: T.List[str]
        for i in self.modules:
            if not isinstance(i, str):
                raise DependencyException('Boost module argument is not a string.')
            if i.startswith('boost_'):
                raise DependencyException('Boost modules must be passed without the boost_ prefix')

        self.modules_found = []    # type: T.List[str]
        self.modules_missing = []  # type: T.List[str]

        # Do we need threads?
        if 'thread' in self.modules:
            if not self._add_sub_dependency(threads_factory(environment, self.for_machine, {})):
                self.is_found = False
                return

        # Try figuring out the architecture tag
        self.arch = environment.machines[self.for_machine].cpu_family
        self.arch = boost_arch_map.get(self.arch, None)

        # Prefere BOOST_INCLUDEDIR and BOOST_LIBRARYDIR if preset
        boost_manual_env = [x in os.environ for x in ['BOOST_INCLUDEDIR', 'BOOST_LIBRARYDIR']]
        if all(boost_manual_env):
            inc_dir = Path(os.environ['BOOST_INCLUDEDIR'])
            lib_dir = Path(os.environ['BOOST_LIBRARYDIR'])
            mlog.debug('Trying to find boost with:')
            mlog.debug('  - BOOST_INCLUDEDIR = {}'.format(inc_dir))
            mlog.debug('  - BOOST_LIBRARYDIR = {}'.format(lib_dir))

            boost_inc_dir = None
            for j in [inc_dir / 'version.hpp', inc_dir / 'boost' / 'version.hpp']:
                if j.is_file():
                    boost_inc_dir = self._include_dir_from_version_header(j)
                    break
            if not boost_inc_dir:
                self.is_found = False
                return

            self.is_found = self.run_check([boost_inc_dir], [lib_dir])
            return
        elif any(boost_manual_env):
            mlog.warning('Both BOOST_INCLUDEDIR *and* BOOST_LIBRARYDIR have to be set (one is not enough). Ignoring.')

        # A) Detect potential boost root directories (uses also BOOST_ROOT env var)
        roots = self.detect_roots()
        roots = list(mesonlib.OrderedSet(roots))

        # B) Foreach candidate
        for j in roots:
            #   1. Look for the boost headers (boost/version.pp)
            mlog.debug('Checking potential boost root {}'.format(j.as_posix()))
            inc_dirs = self.detect_inc_dirs(j)
            inc_dirs = sorted(inc_dirs, reverse=True)  # Prefer the newer versions

            # Early abort when boost is not found
            if not inc_dirs:
                continue

            lib_dirs = self.detect_lib_dirs(j)
            self.is_found = self.run_check(inc_dirs, lib_dirs)
            if self.is_found:
                self.boost_root = j
                break

    def run_check(self, inc_dirs: T.List[BoostIncludeDir], lib_dirs: T.List[Path]) -> bool:
        #   2. Find all boost libraries
        libs = []  # type: T.List[BoostLibraryFile]
        for i in lib_dirs:
            libs += self.detect_libraries(i)
        libs = sorted(set(libs))

        modules = ['boost_' + x for x in self.modules]
        for inc in inc_dirs:
            mlog.debug('  - found boost {} include dir: {}'.format(inc.version, inc.path))
            f_libs = self.filter_libraries(libs, inc.version_lib)

            # mlog.debug('  - raw library list:')
            # for j in libs:
            #     mlog.debug('    - {}'.format(j))
            mlog.debug('  - filtered library list:')
            for j in f_libs:
                mlog.debug('    - {}'.format(j))

            #   3. Select the libraries matching the requested modules
            not_found = []  # type: T.List[str]
            selected_modules = []  # type: T.List[BoostLibraryFile]
            for mod in modules:
                found = False
                for l in f_libs:
                    if l.mod_name_matches(mod):
                        selected_modules += [l]
                        found = True
                        break
                if not found:
                    not_found += [mod]

            # log the result
            mlog.debug('  - found:')
            comp_args = []  # type: T.List[str]
            link_args = []  # type: T.List[str]
            for j in selected_modules:
                c_args = j.get_compiler_args()
                l_args = j.get_link_args()
                mlog.debug('    - {:<24} link={} comp={}'.format(j.mod_name, str(l_args), str(c_args)))
                comp_args += c_args
                link_args += l_args

            comp_args = list(set(comp_args))
            link_args = list(set(link_args))

            self.modules_found = [x.mod_name for x in selected_modules]
            self.modules_found = [x[6:] for x in self.modules_found]
            self.modules_found = sorted(set(self.modules_found))
            self.modules_missing = not_found
            self.modules_missing = [x[6:] for x in self.modules_missing]
            self.modules_missing = sorted(set(self.modules_missing))

            # if we found all modules we are done
            if not not_found:
                self.version = inc.version
                self.compile_args = ['-I' + inc.path.as_posix()]
                self.compile_args += comp_args
                self.compile_args += self._extra_compile_args()
                self.compile_args = list(mesonlib.OrderedSet(self.compile_args))
                self.link_args = link_args
                mlog.debug('  - final compile args: {}'.format(self.compile_args))
                mlog.debug('  - final link args:    {}'.format(self.link_args))
                return True

            # in case we missed something log it and try again
            mlog.debug('  - NOT found:')
            for mod in not_found:
                mlog.debug('    - {}'.format(mod))

        return False

    def detect_inc_dirs(self, root: Path) -> T.List[BoostIncludeDir]:
        candidates = []  # type: T.List[Path]
        inc_root = root / 'include'

        candidates += [root / 'boost']
        candidates += [inc_root / 'boost']
        if inc_root.is_dir():
            for i in inc_root.iterdir():
                if not i.is_dir() or not i.name.startswith('boost-'):
                    continue
                candidates += [i / 'boost']
        candidates = [x for x in candidates if x.is_dir()]
        candidates = [x / 'version.hpp' for x in candidates]
        candidates = [x for x in candidates if x.exists()]
        return [self._include_dir_from_version_header(x) for x in candidates]

    def detect_lib_dirs(self, root: Path) -> T.List[Path]:
        dirs = []     # type: T.List[Path]
        subdirs = []  # type: T.List[Path]
        for i in root.iterdir():
            if i.is_dir() and i.name.startswith('lib'):
                dirs += [i]

        # Some distros put libraries not directly inside /usr/lib but in /usr/lib/x86_64-linux-gnu
        for i in dirs:
            for j in i.iterdir():
                if j.is_dir() and j.name.endswith('-linux-gnu'):
                    subdirs += [j]
        return dirs + subdirs

    def filter_libraries(self, libs: T.List[BoostLibraryFile], lib_vers: str) -> T.List[BoostLibraryFile]:
        # MSVC is very picky with the library tags
        vscrt = ''
        try:
            crt_val = self.env.coredata.base_options['b_vscrt'].value
            buildtype = self.env.coredata.builtins['buildtype'].value
            vscrt = self.clib_compiler.get_crt_compile_args(crt_val, buildtype)[0]
        except (KeyError, IndexError, AttributeError):
            pass

        libs = [x for x in libs if x.static == self.static]
        libs = [x for x in libs if x.mt == self.multithreading]
        libs = [x for x in libs if x.version_matches(lib_vers)]
        libs = [x for x in libs if x.arch_matches(self.arch)]
        libs = [x for x in libs if x.vscrt_matches(vscrt)]
        libs = [x for x in libs if x.nvsuffix != 'dll']  # Only link to import libraries

        # Only filter by debug when we are building in release mode. Debug
        # libraries are automatically prefered through sorting otherwise.
        if not self.debug:
            libs = [x for x in libs if not x.debug]

        # Take the abitag from the first library and filter by it. This
        # ensures that we have a set of libraries that are always compatible.
        if not libs:
            return []
        abitag = libs[0].abitag
        libs = [x for x in libs if x.abitag == abitag]

        return libs

    def detect_libraries(self, libdir: Path) -> T.List[BoostLibraryFile]:
        libs = []  # type: T.List[BoostLibraryFile]
        for i in libdir.iterdir():
            if not i.is_file() or i.is_symlink():
                continue
            if not any([i.name.startswith(x) for x in ['libboost_', 'boost_']]):
                continue

            libs += [BoostLibraryFile(i)]
        return [x for x in libs if x.is_boost()]  # Filter out no boost libraries

    def detect_roots(self) -> T.List[Path]:
        roots = []  # type: T.List[Path]

        # Add roots from the environment
        for i in ['BOOST_ROOT', 'BOOSTROOT']:
            if i in os.environ:
                raw_paths = os.environ[i].split(os.pathsep)
                paths = [Path(x) for x in raw_paths]
                if paths and any([not x.is_absolute() for x in paths]):
                    raise DependencyException('Paths in {} must be absolute'.format(i))
                roots += paths
                return roots  # Do not add system paths if BOOST_ROOT is present

        # Add system paths
        if self.env.machines[self.for_machine].is_windows():
            # Where boost built from source actually installs it
            c_root = Path('C:/Boost')
            if c_root.is_dir():
                roots += [c_root]

            # Where boost documentation says it should be
            prog_files = Path('C:/Program Files/boost')
            # Where boost prebuilt binaries are
            local_boost = Path('C:/local')

            candidates = []  # type: T.List[Path]
            if prog_files.is_dir():
                candidates += [*prog_files.iterdir()]
            if local_boost.is_dir():
                candidates += [*local_boost.iterdir()]

            roots += [x for x in candidates if x.name.lower().startswith('boost') and x.is_dir()]
        else:
            tmp = []  # type: T.List[Path]
            # Add unix paths
            tmp += [Path(x).parent for x in self.clib_compiler.get_default_include_dirs()]

            # Homebrew
            brew_boost = Path('/usr/local/Cellar/boost')
            if brew_boost.is_dir():
                tmp += [x for x in brew_boost.iterdir()]

            # Add some default system paths
            tmp += [Path('/opt/local')]
            tmp += [Path('/usr/local/opt/boost')]
            tmp += [Path('/usr/local')]
            tmp += [Path('/usr')]

            # Cleanup paths
            tmp = [x for x in tmp if x.is_dir()]
            tmp = [x.resolve() for x in tmp]
            roots += tmp

        return roots

    def log_details(self) -> str:
        res = ''
        if self.modules_found:
            res += 'found: ' + ', '.join(self.modules_found)
        if self.modules_missing:
            if res:
                res += ' | '
            res += 'missing: ' + ', '.join(self.modules_missing)
        return res

    def log_info(self) -> str:
        if self.boost_root:
            return self.boost_root.as_posix()
        return ''

    def _include_dir_from_version_header(self, hfile: Path) -> BoostIncludeDir:
        # Extract the version with a regex. Using clib_compiler.get_define would
        # also work, however, this is slower (since it the compiler has to be
        # invoked) and overkill since the layout of the header is always the same.
        assert hfile.exists()
        raw = hfile.read_text()
        m = re.search(r'#define\s+BOOST_VERSION\s+([0-9]+)', raw)
        if not m:
            mlog.debug('Failed to extract version information from {}'.format(hfile))
            return BoostIncludeDir(hfile.parents[1], 0)
        return BoostIncludeDir(hfile.parents[1], int(m.group(1)))

    def _extra_compile_args(self) -> T.List[str]:
        args = []  # type: T.List[str]
        args += ['-DBOOST_ALL_NO_LIB']  # Disable automatic linking
        if not self.static:
            args += ['-DBOOST_ALL_DYN_LINK']
        return args


# See https://www.boost.org/doc/libs/1_72_0/more/getting_started/unix-variants.html#library-naming
# See https://mesonbuild.com/Reference-tables.html#cpu-families
boost_arch_map = {
    'aarch64': 'a64',
    'arc': 'a32',
    'arm': 'a32',
    'ia64': 'i64',
    'mips': 'm32',
    'mips64': 'm64',
    'ppc': 'p32',
    'ppc64': 'p64',
    'sparc': 's32',
    'sparc64': 's64',
    'x86': 'x32',
    'x86_64': 'x64',
}


####      ---- BEGIN GENERATED ----      ####
#                                           #
# Generated with tools/boost_names.py:
#  - boost version:   1.72.0
#  - modules found:   158
#  - libraries found: 42
#

class BoostLibrary():
    def __init__(self, name: str, shared: T.List[str], static: T.List[str], single: T.List[str], multi: T.List[str]):
        self.name = name
        self.shared = shared
        self.static = static
        self.single = single
        self.multi = multi

class BoostModule():
    def __init__(self, name: str, key: str, desc: str, libs: T.List[str]):
        self.name = name
        self.key = key
        self.desc = desc
        self.libs = libs


# dict of all know libraries with additional compile options
boost_libraries = {
    'boost_atomic': BoostLibrary(
        name='boost_atomic',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_chrono': BoostLibrary(
        name='boost_chrono',
        shared=['-DBOOST_ALL_DYN_LINK=1'],
        static=['-DBOOST_All_STATIC_LINK=1'],
        single=[],
        multi=[],
    ),
    'boost_container': BoostLibrary(
        name='boost_container',
        shared=['-DBOOST_CONTAINER_DYN_LINK=1'],
        static=['-DBOOST_CONTAINER_STATIC_LINK=1'],
        single=[],
        multi=[],
    ),
    'boost_context': BoostLibrary(
        name='boost_context',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_contract': BoostLibrary(
        name='boost_contract',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_coroutine': BoostLibrary(
        name='boost_coroutine',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_date_time': BoostLibrary(
        name='boost_date_time',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_exception': BoostLibrary(
        name='boost_exception',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_fiber': BoostLibrary(
        name='boost_fiber',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_fiber_numa': BoostLibrary(
        name='boost_fiber_numa',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_filesystem': BoostLibrary(
        name='boost_filesystem',
        shared=['-DBOOST_FILESYSTEM_DYN_LINK=1'],
        static=['-DBOOST_FILESYSTEM_STATIC_LINK=1'],
        single=[],
        multi=[],
    ),
    'boost_graph': BoostLibrary(
        name='boost_graph',
        shared=['-DBOOST_GRAPH_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_iostreams': BoostLibrary(
        name='boost_iostreams',
        shared=['-DBOOST_IOSTREAMS_DYN_LINK=1', '-DBOOST_IOSTREAMS_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_locale': BoostLibrary(
        name='boost_locale',
        shared=['-DBOOST_LOCALE_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_log': BoostLibrary(
        name='boost_log',
        shared=['-DBOOST_LOG_DLL', '-DBOOST_LOG_DYN_LINK=1'],
        static=[],
        single=['BOOST_LOG_NO_THREADS'],
        multi=[],
    ),
    'boost_log_setup': BoostLibrary(
        name='boost_log_setup',
        shared=['-DBOOST_LOG_DYN_LINK=1', '-DBOOST_LOG_SETUP_DLL', '-DBOOST_LOG_SETUP_DYN_LINK=1'],
        static=[],
        single=['BOOST_LOG_NO_THREADS'],
        multi=[],
    ),
    'boost_math_c99': BoostLibrary(
        name='boost_math_c99',
        shared=['-DBOOST_MATH_TR1_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_math_c99f': BoostLibrary(
        name='boost_math_c99f',
        shared=['-DBOOST_MATH_TR1_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_math_c99l': BoostLibrary(
        name='boost_math_c99l',
        shared=['-DBOOST_MATH_TR1_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_math_tr1': BoostLibrary(
        name='boost_math_tr1',
        shared=['-DBOOST_MATH_TR1_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_math_tr1f': BoostLibrary(
        name='boost_math_tr1f',
        shared=['-DBOOST_MATH_TR1_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_math_tr1l': BoostLibrary(
        name='boost_math_tr1l',
        shared=['-DBOOST_MATH_TR1_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_mpi': BoostLibrary(
        name='boost_mpi',
        shared=['-DBOOST_MPI_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_prg_exec_monitor': BoostLibrary(
        name='boost_prg_exec_monitor',
        shared=['-DBOOST_TEST_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_program_options': BoostLibrary(
        name='boost_program_options',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_random': BoostLibrary(
        name='boost_random',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_regex': BoostLibrary(
        name='boost_regex',
        shared=['-DBOOST_REGEX_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_serialization': BoostLibrary(
        name='boost_serialization',
        shared=['-DBOOST_SERIALIZATION_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_stacktrace_addr2line': BoostLibrary(
        name='boost_stacktrace_addr2line',
        shared=['-DBOOST_STACKTRACE_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_stacktrace_backtrace': BoostLibrary(
        name='boost_stacktrace_backtrace',
        shared=['-DBOOST_STACKTRACE_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_stacktrace_basic': BoostLibrary(
        name='boost_stacktrace_basic',
        shared=['-DBOOST_STACKTRACE_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_stacktrace_noop': BoostLibrary(
        name='boost_stacktrace_noop',
        shared=['-DBOOST_STACKTRACE_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_stacktrace_windbg': BoostLibrary(
        name='boost_stacktrace_windbg',
        shared=['-DBOOST_STACKTRACE_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_stacktrace_windbg_cached': BoostLibrary(
        name='boost_stacktrace_windbg_cached',
        shared=['-DBOOST_STACKTRACE_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_system': BoostLibrary(
        name='boost_system',
        shared=['-DBOOST_SYSTEM_DYN_LINK=1'],
        static=['-DBOOST_SYSTEM_STATIC_LINK=1'],
        single=[],
        multi=[],
    ),
    'boost_test_exec_monitor': BoostLibrary(
        name='boost_test_exec_monitor',
        shared=['-DBOOST_TEST_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_thread': BoostLibrary(
        name='boost_thread',
        shared=['-DBOOST_THREAD_USE_DLL=1'],
        static=['-DBOOST_THREAD_USE_LIB=1'],
        single=[],
        multi=[],
    ),
    'boost_timer': BoostLibrary(
        name='boost_timer',
        shared=['-DBOOST_TIMER_DYN_LINK=1'],
        static=['-DBOOST_TIMER_STATIC_LINK=1'],
        single=[],
        multi=[],
    ),
    'boost_type_erasure': BoostLibrary(
        name='boost_type_erasure',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_unit_test_framework': BoostLibrary(
        name='boost_unit_test_framework',
        shared=['-DBOOST_TEST_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_wave': BoostLibrary(
        name='boost_wave',
        shared=[],
        static=[],
        single=[],
        multi=[],
    ),
    'boost_wserialization': BoostLibrary(
        name='boost_wserialization',
        shared=['-DBOOST_SERIALIZATION_DYN_LINK=1'],
        static=[],
        single=[],
        multi=[],
    ),
}

#                                           #
####       ---- END GENERATED ----       ####
