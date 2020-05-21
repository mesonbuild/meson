# Copyright 2012-2020 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A library of random helper functionality."""
from pathlib import Path
import sys
import stat
import time
import platform, subprocess, operator, os, shlex, shutil, re
import collections
from enum import Enum
from functools import lru_cache, wraps
from itertools import tee, filterfalse
import typing as T
import uuid
import textwrap

from mesonbuild import mlog

if T.TYPE_CHECKING:
    from .build import ConfigurationData
    from .coredata import OptionDictType, UserOption
    from .compilers.compilers import CompilerType
    from .interpreterbase import ObjectHolder

_T = T.TypeVar('_T')
_U = T.TypeVar('_U')

have_fcntl = False
have_msvcrt = False
# TODO: this is such a hack, this really should be either in coredata or in the
# interpreter
# {subproject: project_meson_version}
project_meson_versions = collections.defaultdict(str)  # type: T.DefaultDict[str, str]

try:
    import fcntl
    have_fcntl = True
except Exception:
    pass

try:
    import msvcrt
    have_msvcrt = True
except Exception:
    pass

from glob import glob

if os.path.basename(sys.executable) == 'meson.exe':
    # In Windows and using the MSI installed executable.
    python_command = [sys.executable, 'runpython']
else:
    python_command = [sys.executable]
meson_command = None

GIT = shutil.which('git')
def git(cmd: T.List[str], workingdir: str, **kwargs: T.Any) -> subprocess.CompletedProcess:
    pc = subprocess.run([GIT, '-C', workingdir] + cmd,
                        # Redirect stdin to DEVNULL otherwise git messes up the
                        # console and ANSI colors stop working on Windows.
                        stdin=subprocess.DEVNULL, **kwargs)
    # Sometimes git calls git recursively, such as `git submodule update
    # --recursive` which will be without the above workaround, so set the
    # console mode again just in case.
    mlog.setup_console()
    return pc


def set_meson_command(mainfile: str) -> None:
    global python_command
    global meson_command
    # On UNIX-like systems `meson` is a Python script
    # On Windows `meson` and `meson.exe` are wrapper exes
    if not mainfile.endswith('.py'):
        meson_command = [mainfile]
    elif os.path.isabs(mainfile) and mainfile.endswith('mesonmain.py'):
        # Can't actually run meson with an absolute path to mesonmain.py, it must be run as -m mesonbuild.mesonmain
        meson_command = python_command + ['-m', 'mesonbuild.mesonmain']
    else:
        # Either run uninstalled, or full path to meson-script.py
        meson_command = python_command + [mainfile]
    # We print this value for unit tests.
    if 'MESON_COMMAND_TESTS' in os.environ:
        mlog.log('meson_command is {!r}'.format(meson_command))


def is_ascii_string(astring: T.Union[str, bytes]) -> bool:
    try:
        if isinstance(astring, str):
            astring.encode('ascii')
        elif isinstance(astring, bytes):
            astring.decode('ascii')
    except UnicodeDecodeError:
        return False
    return True


def check_direntry_issues(direntry_array: T.Union[T.List[T.Union[str, bytes]], str, bytes]) -> None:
    import locale
    # Warn if the locale is not UTF-8. This can cause various unfixable issues
    # such as os.stat not being able to decode filenames with unicode in them.
    # There is no way to reset both the preferred encoding and the filesystem
    # encoding, so we can just warn about it.
    e = locale.getpreferredencoding()
    if e.upper() != 'UTF-8' and not is_windows():
        if not isinstance(direntry_array, list):
            direntry_array = [direntry_array]
        for de in direntry_array:
            if is_ascii_string(de):
                continue
            mlog.warning(textwrap.dedent('''
                You are using {!r} which is not a Unicode-compatible
                locale but you are trying to access a file system entry called {!r} which is
                not pure ASCII. This may cause problems.
                '''.format(e, de)), file=sys.stderr)


# Put this in objects that should not get dumped to pickle files
# by accident.
import threading
an_unpicklable_object = threading.Lock()


class MesonException(Exception):
    '''Exceptions thrown by Meson'''

    file = None    # type: T.Optional[str]
    lineno = None  # type: T.Optional[int]
    colno = None   # type: T.Optional[int]


class EnvironmentException(MesonException):
    '''Exceptions thrown while processing and creating the build environment'''


class FileMode:
    # The first triad is for owner permissions, the second for group permissions,
    # and the third for others (everyone else).
    # For the 1st character:
    #  'r' means can read
    #  '-' means not allowed
    # For the 2nd character:
    #  'w' means can write
    #  '-' means not allowed
    # For the 3rd character:
    #  'x' means can execute
    #  's' means can execute and setuid/setgid is set (owner/group triads only)
    #  'S' means cannot execute and setuid/setgid is set (owner/group triads only)
    #  't' means can execute and sticky bit is set ("others" triads only)
    #  'T' means cannot execute and sticky bit is set ("others" triads only)
    #  '-' means none of these are allowed
    #
    # The meanings of 'rwx' perms is not obvious for directories; see:
    # https://www.hackinglinuxexposed.com/articles/20030424.html
    #
    # For information on this notation such as setuid/setgid/sticky bits, see:
    # https://en.wikipedia.org/wiki/File_system_permissions#Symbolic_notation
    symbolic_perms_regex = re.compile('[r-][w-][xsS-]' # Owner perms
                                      '[r-][w-][xsS-]' # Group perms
                                      '[r-][w-][xtT-]') # Others perms

    def __init__(self, perms: T.Optional[str] = None, owner: T.Optional[str] = None,
                 group: T.Optional[str] = None):
        self.perms_s = perms
        self.perms = self.perms_s_to_bits(perms)
        self.owner = owner
        self.group = group

    def __repr__(self) -> str:
        ret = '<FileMode: {!r} owner={} group={}'
        return ret.format(self.perms_s, self.owner, self.group)

    @classmethod
    def perms_s_to_bits(cls, perms_s: T.Optional[str]) -> int:
        '''
        Does the opposite of stat.filemode(), converts strings of the form
        'rwxr-xr-x' to st_mode enums which can be passed to os.chmod()
        '''
        if perms_s is None:
            # No perms specified, we will not touch the permissions
            return -1
        eg = 'rwxr-xr-x'
        if not isinstance(perms_s, str):
            msg = 'Install perms must be a string. For example, {!r}'
            raise MesonException(msg.format(eg))
        if len(perms_s) != 9 or not cls.symbolic_perms_regex.match(perms_s):
            msg = 'File perms {!r} must be exactly 9 chars. For example, {!r}'
            raise MesonException(msg.format(perms_s, eg))
        perms = 0
        # Owner perms
        if perms_s[0] == 'r':
            perms |= stat.S_IRUSR
        if perms_s[1] == 'w':
            perms |= stat.S_IWUSR
        if perms_s[2] == 'x':
            perms |= stat.S_IXUSR
        elif perms_s[2] == 'S':
            perms |= stat.S_ISUID
        elif perms_s[2] == 's':
            perms |= stat.S_IXUSR
            perms |= stat.S_ISUID
        # Group perms
        if perms_s[3] == 'r':
            perms |= stat.S_IRGRP
        if perms_s[4] == 'w':
            perms |= stat.S_IWGRP
        if perms_s[5] == 'x':
            perms |= stat.S_IXGRP
        elif perms_s[5] == 'S':
            perms |= stat.S_ISGID
        elif perms_s[5] == 's':
            perms |= stat.S_IXGRP
            perms |= stat.S_ISGID
        # Others perms
        if perms_s[6] == 'r':
            perms |= stat.S_IROTH
        if perms_s[7] == 'w':
            perms |= stat.S_IWOTH
        if perms_s[8] == 'x':
            perms |= stat.S_IXOTH
        elif perms_s[8] == 'T':
            perms |= stat.S_ISVTX
        elif perms_s[8] == 't':
            perms |= stat.S_IXOTH
            perms |= stat.S_ISVTX
        return perms

class File:
    def __init__(self, is_built: bool, subdir: str, fname: str):
        self.is_built = is_built
        self.subdir = subdir
        self.fname = fname

    def __str__(self) -> str:
        return self.relative_name()

    def __repr__(self) -> str:
        ret = '<File: {0}'
        if not self.is_built:
            ret += ' (not built)'
        ret += '>'
        return ret.format(self.relative_name())

    @staticmethod
    @lru_cache(maxsize=None)
    def from_source_file(source_root: str, subdir: str, fname: str) -> 'File':
        if not os.path.isfile(os.path.join(source_root, subdir, fname)):
            raise MesonException('File %s does not exist.' % fname)
        return File(False, subdir, fname)

    @staticmethod
    def from_built_file(subdir: str, fname: str) -> 'File':
        return File(True, subdir, fname)

    @staticmethod
    def from_absolute_file(fname: str) -> 'File':
        return File(False, '', fname)

    @lru_cache(maxsize=None)
    def rel_to_builddir(self, build_to_src: str) -> str:
        if self.is_built:
            return self.relative_name()
        else:
            return os.path.join(build_to_src, self.subdir, self.fname)

    @lru_cache(maxsize=None)
    def absolute_path(self, srcdir: str, builddir: str) -> str:
        absdir = srcdir
        if self.is_built:
            absdir = builddir
        return os.path.join(absdir, self.relative_name())

    def endswith(self, ending: str) -> bool:
        return self.fname.endswith(ending)

    def split(self, s: str) -> T.List[str]:
        return self.fname.split(s)

    def __eq__(self, other) -> bool:
        if not isinstance(other, File):
            return NotImplemented
        return (self.fname, self.subdir, self.is_built) == (other.fname, other.subdir, other.is_built)

    def __hash__(self) -> int:
        return hash((self.fname, self.subdir, self.is_built))

    @lru_cache(maxsize=None)
    def relative_name(self) -> str:
        return os.path.join(self.subdir, self.fname)


def get_compiler_for_source(compilers: T.Iterable['CompilerType'], src: str) -> 'CompilerType':
    """Given a set of compilers and a source, find the compiler for that source type."""
    for comp in compilers:
        if comp.can_compile(src):
            return comp
    raise MesonException('No specified compiler can handle file {!s}'.format(src))


def classify_unity_sources(compilers: T.Iterable['CompilerType'], sources: T.Iterable[str]) -> T.Dict['CompilerType', T.List[str]]:
    compsrclist = {}  # type: T.Dict[CompilerType, T.List[str]]
    for src in sources:
        comp = get_compiler_for_source(compilers, src)
        if comp not in compsrclist:
            compsrclist[comp] = [src]
        else:
            compsrclist[comp].append(src)
    return compsrclist


class OrderedEnum(Enum):
    """
    An Enum which additionally offers homogeneous ordered comparison.
    """
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class MachineChoice(OrderedEnum):

    """Enum class representing one of the two abstract machine names used in
    most places: the build, and host, machines.
    """

    BUILD = 0
    HOST = 1

    def get_lower_case_name(self) -> str:
        return PerMachine('build', 'host')[self]

    def get_prefix(self) -> str:
        return PerMachine('build.', '')[self]


class PerMachine(T.Generic[_T]):
    def __init__(self, build: _T, host: _T):
        self.build = build
        self.host = host

    def __getitem__(self, machine: MachineChoice) -> _T:
        return {
            MachineChoice.BUILD:  self.build,
            MachineChoice.HOST:   self.host,
        }[machine]

    def __setitem__(self, machine: MachineChoice, val: _T) -> None:
        setattr(self, machine.get_lower_case_name(), val)

    def miss_defaulting(self) -> "PerMachineDefaultable[T.Optional[_T]]":
        """Unset definition duplicated from their previous to None

        This is the inverse of ''default_missing''. By removing defaulted
        machines, we can elaborate the original and then redefault them and thus
        avoid repeating the elaboration explicitly.
        """
        unfreeze = PerMachineDefaultable() # type: PerMachineDefaultable[T.Optional[_T]]
        unfreeze.build = self.build
        unfreeze.host = self.host
        if unfreeze.host == unfreeze.build:
            unfreeze.host = None
        return unfreeze


class PerThreeMachine(PerMachine[_T]):
    """Like `PerMachine` but includes `target` too.

    It turns out just one thing do we need track the target machine. There's no
    need to computer the `target` field so we don't bother overriding the
    `__getitem__`/`__setitem__` methods.
    """
    def __init__(self, build: _T, host: _T, target: _T):
        super().__init__(build, host)
        self.target = target

    def miss_defaulting(self) -> "PerThreeMachineDefaultable[T.Optional[_T]]":
        """Unset definition duplicated from their previous to None

        This is the inverse of ''default_missing''. By removing defaulted
        machines, we can elaborate the original and then redefault them and thus
        avoid repeating the elaboration explicitly.
        """
        unfreeze = PerThreeMachineDefaultable() # type: PerThreeMachineDefaultable[T.Optional[_T]]
        unfreeze.build = self.build
        unfreeze.host = self.host
        unfreeze.target = self.target
        if unfreeze.target == unfreeze.host:
            unfreeze.target = None
        if unfreeze.host == unfreeze.build:
            unfreeze.host = None
        return unfreeze

    def matches_build_machine(self, machine: MachineChoice) -> bool:
        return self.build == self[machine]


class PerMachineDefaultable(PerMachine[T.Optional[_T]]):
    """Extends `PerMachine` with the ability to default from `None`s.
    """
    def __init__(self):
        super().__init__(None, None)

    def default_missing(self) -> "PerMachine[T.Optional[_T]]":
        """Default host to build

        This allows just specifying nothing in the native case, and just host in the
        cross non-compiler case.
        """
        freeze = PerMachine(self.build, self.host)
        if freeze.host is None:
            freeze.host = freeze.build
        return freeze


class PerThreeMachineDefaultable(PerMachineDefaultable, PerThreeMachine[T.Optional[_T]]):
    """Extends `PerThreeMachine` with the ability to default from `None`s.
    """
    def __init__(self):
        PerThreeMachine.__init__(self, None, None, None)

    def default_missing(self) -> "PerThreeMachine[T.Optional[_T]]":
        """Default host to build and target to host.

        This allows just specifying nothing in the native case, just host in the
        cross non-compiler case, and just target in the native-built
        cross-compiler case.
        """
        freeze = PerThreeMachine(self.build, self.host, self.target)
        if freeze.host is None:
            freeze.host = freeze.build
        if freeze.target is None:
            freeze.target = freeze.host
        return freeze


def is_sunos() -> bool:
    return platform.system().lower() == 'sunos'


def is_osx() -> bool:
    return platform.system().lower() == 'darwin'


def is_linux() -> bool:
    return platform.system().lower() == 'linux'


def is_android() -> bool:
    return platform.system().lower() == 'android'


def is_haiku() -> bool:
    return platform.system().lower() == 'haiku'


def is_openbsd() -> bool:
    return platform.system().lower() == 'openbsd'


def is_windows() -> bool:
    platname = platform.system().lower()
    return platname == 'windows' or 'mingw' in platname


def is_cygwin() -> bool:
    return platform.system().lower().startswith('cygwin')


def is_debianlike() -> bool:
    return os.path.isfile('/etc/debian_version')


def is_dragonflybsd() -> bool:
    return platform.system().lower() == 'dragonfly'


def is_netbsd() -> bool:
    return platform.system().lower() == 'netbsd'


def is_freebsd() -> bool:
    return platform.system().lower() == 'freebsd'

def is_irix() -> bool:
    return platform.system().startswith('irix')

def is_hurd() -> bool:
    return platform.system().lower() == 'gnu'


def exe_exists(arglist: T.List[str]) -> bool:
    try:
        if subprocess.run(arglist, timeout=10).returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


@lru_cache(maxsize=None)
def darwin_get_object_archs(objpath: str) -> T.List[str]:
    '''
    For a specific object (executable, static library, dylib, etc), run `lipo`
    to fetch the list of archs supported by it. Supports both thin objects and
    'fat' objects.
    '''
    _, stdo, stderr = Popen_safe(['lipo', '-info', objpath])
    if not stdo:
        mlog.debug('lipo {}: {}'.format(objpath, stderr))
        return None
    stdo = stdo.rsplit(': ', 1)[1]
    # Convert from lipo-style archs to meson-style CPUs
    stdo = stdo.replace('i386', 'x86')
    stdo = stdo.replace('arm64', 'aarch64')
    # Add generic name for armv7 and armv7s
    if 'armv7' in stdo:
        stdo += ' arm'
    return stdo.split()


def detect_vcs(source_dir: T.Union[str, Path]) -> T.Optional[T.Dict[str, str]]:
    vcs_systems = [
        dict(name = 'git',        cmd = 'git', repo_dir = '.git', get_rev = 'git describe --dirty=+', rev_regex = '(.*)', dep = '.git/logs/HEAD'),
        dict(name = 'mercurial',  cmd = 'hg',  repo_dir = '.hg',  get_rev = 'hg id -i',               rev_regex = '(.*)', dep = '.hg/dirstate'),
        dict(name = 'subversion', cmd = 'svn', repo_dir = '.svn', get_rev = 'svn info',               rev_regex = 'Revision: (.*)', dep = '.svn/wc.db'),
        dict(name = 'bazaar',     cmd = 'bzr', repo_dir = '.bzr', get_rev = 'bzr revno',              rev_regex = '(.*)', dep = '.bzr'),
    ]
    if isinstance(source_dir, str):
        source_dir = Path(source_dir)

    parent_paths_and_self = collections.deque(source_dir.parents)
    # Prepend the source directory to the front so we can check it;
    # source_dir.parents doesn't include source_dir
    parent_paths_and_self.appendleft(source_dir)
    for curdir in parent_paths_and_self:
        for vcs in vcs_systems:
            if Path.is_dir(curdir.joinpath(vcs['repo_dir'])) and shutil.which(vcs['cmd']):
                vcs['wc_dir'] = str(curdir)
                return vcs
    return None

# a helper class which implements the same version ordering as RPM
class Version:
    def __init__(self, s: str):
        self._s = s

        # split into numeric, alphabetic and non-alphanumeric sequences
        sequences1 = re.finditer(r'(\d+|[a-zA-Z]+|[^a-zA-Z\d]+)', s)

        # non-alphanumeric separators are discarded
        sequences2 = [m for m in sequences1 if not re.match(r'[^a-zA-Z\d]+', m.group(1))]

        # numeric sequences are converted from strings to ints
        sequences3 = [int(m.group(1)) if m.group(1).isdigit() else m.group(1) for m in sequences2]

        self._v = sequences3

    def __str__(self):
        return '%s (V=%s)' % (self._s, str(self._v))

    def __repr__(self):
        return '<Version: {}>'.format(self._s)

    def __lt__(self, other):
        if isinstance(other, Version):
            return self.__cmp(other, operator.lt)
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Version):
            return self.__cmp(other, operator.gt)
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Version):
            return self.__cmp(other, operator.le)
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Version):
            return self.__cmp(other, operator.ge)
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Version):
            return self._v == other._v
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Version):
            return self._v != other._v
        return NotImplemented

    def __cmp(self, other: 'Version', comparator: T.Callable[[T.Any, T.Any], bool]) -> bool:
        # compare each sequence in order
        for ours, theirs in zip(self._v, other._v):
            # sort a non-digit sequence before a digit sequence
            ours_is_int = isinstance(ours, int)
            theirs_is_int = isinstance(theirs, int)
            if ours_is_int != theirs_is_int:
                return comparator(ours_is_int, theirs_is_int)

            if ours != theirs:
                return comparator(ours, theirs)

        # if equal length, all components have matched, so equal
        # otherwise, the version with a suffix remaining is greater
        return comparator(len(self._v), len(other._v))


def _version_extract_cmpop(vstr2: str) -> T.Tuple[T.Callable[[T.Any, T.Any], bool], str]:
    if vstr2.startswith('>='):
        cmpop = operator.ge
        vstr2 = vstr2[2:]
    elif vstr2.startswith('<='):
        cmpop = operator.le
        vstr2 = vstr2[2:]
    elif vstr2.startswith('!='):
        cmpop = operator.ne
        vstr2 = vstr2[2:]
    elif vstr2.startswith('=='):
        cmpop = operator.eq
        vstr2 = vstr2[2:]
    elif vstr2.startswith('='):
        cmpop = operator.eq
        vstr2 = vstr2[1:]
    elif vstr2.startswith('>'):
        cmpop = operator.gt
        vstr2 = vstr2[1:]
    elif vstr2.startswith('<'):
        cmpop = operator.lt
        vstr2 = vstr2[1:]
    else:
        cmpop = operator.eq

    return (cmpop, vstr2)


def version_compare(vstr1: str, vstr2: str) -> bool:
    (cmpop, vstr2) = _version_extract_cmpop(vstr2)
    return cmpop(Version(vstr1), Version(vstr2))


def version_compare_many(vstr1: str, conditions: T.Union[str, T.Iterable[str]]) -> T.Tuple[bool, T.List[str], T.List[str]]:
    if isinstance(conditions, str):
        conditions = [conditions]
    found = []
    not_found = []
    for req in conditions:
        if not version_compare(vstr1, req):
            not_found.append(req)
        else:
            found.append(req)
    return not_found == [], not_found, found


# determine if the minimum version satisfying the condition |condition| exceeds
# the minimum version for a feature |minimum|
def version_compare_condition_with_min(condition: str, minimum: str) -> bool:
    if condition.startswith('>='):
        cmpop = operator.le
        condition = condition[2:]
    elif condition.startswith('<='):
        return False
    elif condition.startswith('!='):
        return False
    elif condition.startswith('=='):
        cmpop = operator.le
        condition = condition[2:]
    elif condition.startswith('='):
        cmpop = operator.le
        condition = condition[1:]
    elif condition.startswith('>'):
        cmpop = operator.lt
        condition = condition[1:]
    elif condition.startswith('<'):
        return False
    else:
        cmpop = operator.le

    # Declaring a project(meson_version: '>=0.46') and then using features in
    # 0.46.0 is valid, because (knowing the meson versioning scheme) '0.46.0' is
    # the lowest version which satisfies the constraint '>=0.46'.
    #
    # But this will fail here, because the minimum version required by the
    # version constraint ('0.46') is strictly less (in our version comparison)
    # than the minimum version needed for the feature ('0.46.0').
    #
    # Map versions in the constraint of the form '0.46' to '0.46.0', to embed
    # this knowledge of the meson versioning scheme.
    condition = condition.strip()
    if re.match(r'^\d+.\d+$', condition):
        condition += '.0'

    return cmpop(Version(minimum), Version(condition))


def default_libdir() -> str:
    if is_debianlike():
        try:
            pc = subprocess.Popen(['dpkg-architecture', '-qDEB_HOST_MULTIARCH'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL)
            (stdo, _) = pc.communicate()
            if pc.returncode == 0:
                archpath = stdo.decode().strip()
                return 'lib/' + archpath
        except Exception:
            pass
    if is_freebsd() or is_irix():
        return 'lib'
    if os.path.isdir('/usr/lib64') and not os.path.islink('/usr/lib64'):
        return 'lib64'
    return 'lib'


def default_libexecdir() -> str:
    # There is no way to auto-detect this, so it must be set at build time
    return 'libexec'


def default_prefix() -> str:
    return 'c:/' if is_windows() else '/usr/local'


def get_library_dirs() -> T.List[str]:
    if is_windows():
        return ['C:/mingw/lib'] # TODO: get programmatically
    if is_osx():
        return ['/usr/lib'] # TODO: get programmatically
    # The following is probably Debian/Ubuntu specific.
    # /usr/local/lib is first because it contains stuff
    # installed by the sysadmin and is probably more up-to-date
    # than /usr/lib. If you feel that this search order is
    # problematic, please raise the issue on the mailing list.
    unixdirs = ['/usr/local/lib', '/usr/lib', '/lib']

    if is_freebsd():
        return unixdirs
    # FIXME: this needs to be further genericized for aarch64 etc.
    machine = platform.machine()
    if machine in ('i386', 'i486', 'i586', 'i686'):
        plat = 'i386'
    elif machine.startswith('arm'):
        plat = 'arm'
    else:
        plat = ''

    # Solaris puts 32-bit libraries in the main /lib & /usr/lib directories
    # and 64-bit libraries in platform specific subdirectories.
    if is_sunos():
        if machine == 'i86pc':
            plat = 'amd64'
        elif machine.startswith('sun4'):
            plat = 'sparcv9'

    usr_platdir = Path('/usr/lib/') / plat
    if usr_platdir.is_dir():
        unixdirs += [str(x) for x in (usr_platdir).iterdir() if x.is_dir()]
    if os.path.exists('/usr/lib64'):
        unixdirs.append('/usr/lib64')

    lib_platdir = Path('/lib/') / plat
    if lib_platdir.is_dir():
        unixdirs += [str(x) for x in (lib_platdir).iterdir() if x.is_dir()]
    if os.path.exists('/lib64'):
        unixdirs.append('/lib64')

    return unixdirs


def has_path_sep(name: str, sep: str = '/\\') -> bool:
    'Checks if any of the specified @sep path separators are in @name'
    for each in sep:
        if each in name:
            return True
    return False


if is_windows():
    # shlex.split is not suitable for splitting command line on Window (https://bugs.python.org/issue1724822);
    # shlex.quote is similarly problematic. Below are "proper" implementations of these functions according to
    # https://docs.microsoft.com/en-us/cpp/c-language/parsing-c-command-line-arguments and
    # https://blogs.msdn.microsoft.com/twistylittlepassagesallalike/2011/04/23/everyone-quotes-command-line-arguments-the-wrong-way/

    _whitespace = ' \t\n\r'
    _find_unsafe_char = re.compile(r'[{}"]'.format(_whitespace)).search

    def quote_arg(arg: str) -> str:
        if arg and not _find_unsafe_char(arg):
            return arg

        result = '"'
        num_backslashes = 0
        for c in arg:
            if c == '\\':
                num_backslashes += 1
            else:
                if c == '"':
                    # Escape all backslashes and the following double quotation mark
                    num_backslashes = num_backslashes * 2 + 1

                result += num_backslashes * '\\' + c
                num_backslashes = 0

        # Escape all backslashes, but let the terminating double quotation
        # mark we add below be interpreted as a metacharacter
        result += (num_backslashes * 2) * '\\' + '"'
        return result

    def split_args(cmd: str) -> T.List[str]:
        result = []
        arg = ''
        num_backslashes = 0
        num_quotes = 0
        in_quotes = False
        for c in cmd:
            if c == '\\':
                num_backslashes += 1
            else:
                if c == '"' and not (num_backslashes % 2):
                    # unescaped quote, eat it
                    arg += (num_backslashes // 2) * '\\'
                    num_quotes += 1
                    in_quotes = not in_quotes
                elif c in _whitespace and not in_quotes:
                    if arg or num_quotes:
                        # reached the end of the argument
                        result.append(arg)
                        arg = ''
                        num_quotes = 0
                else:
                    if c == '"':
                        # escaped quote
                        num_backslashes = (num_backslashes - 1) // 2

                    arg += num_backslashes * '\\' + c

                num_backslashes = 0

        if arg or num_quotes:
            result.append(arg)

        return result
else:
    def quote_arg(arg: str) -> str:
        return shlex.quote(arg)

    def split_args(cmd: str) -> T.List[str]:
        return shlex.split(cmd)


def join_args(args: T.Iterable[str]) -> str:
    return ' '.join([quote_arg(x) for x in args])


def do_replacement(regex: T.Pattern[str], line: str, variable_format: str,
                   confdata: 'ConfigurationData') -> T.Tuple[str, T.Set[str]]:
    missing_variables = set()  # type: T.Set[str]
    if variable_format == 'cmake':
        start_tag = '${'
        backslash_tag = '\\${'
    else:
        assert variable_format in ['meson', 'cmake@']
        start_tag = '@'
        backslash_tag = '\\@'

    def variable_replace(match: T.Match[str]) -> str:
        # Pairs of escape characters before '@' or '\@'
        if match.group(0).endswith('\\'):
            num_escapes = match.end(0) - match.start(0)
            return '\\' * (num_escapes // 2)
        # Single escape character and '@'
        elif match.group(0) == backslash_tag:
            return start_tag
        # Template variable to be replaced
        else:
            varname = match.group(1)
            if varname in confdata:
                (var, desc) = confdata.get(varname)
                if isinstance(var, str):
                    pass
                elif isinstance(var, int):
                    var = str(var)
                else:
                    msg = 'Tried to replace variable {!r} value with ' \
                          'something other than a string or int: {!r}'
                    raise MesonException(msg.format(varname, var))
            else:
                missing_variables.add(varname)
                var = ''
            return var
    return re.sub(regex, variable_replace, line), missing_variables

def do_define(regex: T.Pattern[str], line: str, confdata: 'ConfigurationData', variable_format: str) -> str:
    def get_cmake_define(line: str, confdata: 'ConfigurationData') -> str:
        arr = line.split()
        define_value=[]
        for token in arr[2:]:
            try:
                (v, desc) = confdata.get(token)
                define_value += [v]
            except KeyError:
                define_value += [token]
        return ' '.join(define_value)

    arr = line.split()
    if variable_format == 'meson' and len(arr) != 2:
      raise MesonException('#mesondefine does not contain exactly two tokens: %s' % line.strip())

    varname = arr[1]
    try:
        (v, desc) = confdata.get(varname)
    except KeyError:
        return '/* #undef %s */\n' % varname
    if isinstance(v, bool):
        if v:
            return '#define %s\n' % varname
        else:
            return '#undef %s\n' % varname
    elif isinstance(v, int):
        return '#define %s %d\n' % (varname, v)
    elif isinstance(v, str):
        if variable_format == 'meson':
            result = v
        else:
            result = get_cmake_define(line, confdata)
        result = '#define %s %s\n' % (varname, result)
        (result, missing_variable) = do_replacement(regex, result, variable_format, confdata)
        return result
    else:
        raise MesonException('#mesondefine argument "%s" is of unknown type.' % varname)

def do_conf_str (data: list, confdata: 'ConfigurationData', variable_format: str,
                 encoding: str = 'utf-8') -> T.Tuple[T.List[str],T.Set[str], bool]:
    def line_is_valid(line : str, variable_format: str):
      if variable_format == 'meson':
          if '#cmakedefine' in line:
              return False
      else: #cmake format
         if '#mesondefine' in line:
            return False
      return True

    # Only allow (a-z, A-Z, 0-9, _, -) as valid characters for a define
    # Also allow escaping '@' with '\@'
    if variable_format in ['meson', 'cmake@']:
        regex = re.compile(r'(?:\\\\)+(?=\\?@)|\\@|@([-a-zA-Z0-9_]+)@')
    elif variable_format == 'cmake':
        regex = re.compile(r'(?:\\\\)+(?=\\?\$)|\\\${|\${([-a-zA-Z0-9_]+)}')
    else:
        raise MesonException('Format "{}" not handled'.format(variable_format))

    search_token = '#mesondefine'
    if variable_format != 'meson':
        search_token = '#cmakedefine'

    result = []
    missing_variables = set()
    # Detect when the configuration data is empty and no tokens were found
    # during substitution so we can warn the user to use the `copy:` kwarg.
    confdata_useless = not confdata.keys()
    for line in data:
        if line.startswith(search_token):
            confdata_useless = False
            line = do_define(regex, line, confdata, variable_format)
        else:
            if not line_is_valid(line,variable_format):
                raise MesonException('Format "{}" mismatched'.format(variable_format))
            line, missing = do_replacement(regex, line, variable_format, confdata)
            missing_variables.update(missing)
            if missing:
                confdata_useless = False
        result.append(line)

    return result, missing_variables, confdata_useless

def do_conf_file(src: str, dst: str, confdata: 'ConfigurationData', variable_format: str,
                 encoding: str = 'utf-8') -> T.Tuple[T.Set[str], bool]:
    try:
        with open(src, encoding=encoding, newline='') as f:
            data = f.readlines()
    except Exception as e:
        raise MesonException('Could not read input file %s: %s' % (src, str(e)))

    (result, missing_variables, confdata_useless) = do_conf_str(data, confdata, variable_format, encoding)
    dst_tmp = dst + '~'
    try:
        with open(dst_tmp, 'w', encoding=encoding, newline='') as f:
            f.writelines(result)
    except Exception as e:
        raise MesonException('Could not write output file %s: %s' % (dst, str(e)))
    shutil.copymode(src, dst_tmp)
    replace_if_different(dst, dst_tmp)
    return missing_variables, confdata_useless

CONF_C_PRELUDE = '''/*
 * Autogenerated by the Meson build system.
 * Do not edit, your changes will be lost.
 */

#pragma once

'''

CONF_NASM_PRELUDE = '''; Autogenerated by the Meson build system.
; Do not edit, your changes will be lost.

'''

def dump_conf_header(ofilename: str, cdata: 'ConfigurationData', output_format: str) -> None:
    if output_format == 'c':
        prelude = CONF_C_PRELUDE
        prefix = '#'
    elif output_format == 'nasm':
        prelude = CONF_NASM_PRELUDE
        prefix = '%'

    ofilename_tmp = ofilename + '~'
    with open(ofilename_tmp, 'w', encoding='utf-8') as ofile:
        ofile.write(prelude)
        for k in sorted(cdata.keys()):
            (v, desc) = cdata.get(k)
            if desc:
                if output_format == 'c':
                    ofile.write('/* %s */\n' % desc)
                elif output_format == 'nasm':
                    for line in desc.split('\n'):
                        ofile.write('; %s\n' % line)
            if isinstance(v, bool):
                if v:
                    ofile.write('%sdefine %s\n\n' % (prefix, k))
                else:
                    ofile.write('%sundef %s\n\n' % (prefix, k))
            elif isinstance(v, (int, str)):
                ofile.write('%sdefine %s %s\n\n' % (prefix, k, v))
            else:
                raise MesonException('Unknown data type in configuration file entry: ' + k)
    replace_if_different(ofilename, ofilename_tmp)


def replace_if_different(dst: str, dst_tmp: str) -> None:
    # If contents are identical, don't touch the file to prevent
    # unnecessary rebuilds.
    different = True
    try:
        with open(dst, 'rb') as f1, open(dst_tmp, 'rb') as f2:
            if f1.read() == f2.read():
                different = False
    except FileNotFoundError:
        pass
    if different:
        os.replace(dst_tmp, dst)
    else:
        os.unlink(dst_tmp)


@T.overload
def unholder(item: 'ObjectHolder[_T]') -> _T: ...

@T.overload
def unholder(item: T.List['ObjectHolder[_T]']) -> T.List[_T]: ...

@T.overload
def unholder(item: T.List[_T]) -> T.List[_T]: ...

@T.overload
def unholder(item: T.List[T.Union[_T, 'ObjectHolder[_T]']]) -> T.List[_T]: ...

def unholder(item):
    """Get the held item of an object holder or list of object holders."""
    if isinstance(item, list):
        return [i.held_object if hasattr(i, 'held_object') else i for i in item]
    if hasattr(item, 'held_object'):
        return item.held_object
    return item


def listify(item: T.Any, flatten: bool = True) -> T.List[T.Any]:
    '''
    Returns a list with all args embedded in a list if they are not a list.
    This function preserves order.
    @flatten: Convert lists of lists to a flat list
    '''
    if not isinstance(item, list):
        return [item]
    result = []  # type: T.List[T.Any]
    for i in item:
        if flatten and isinstance(i, list):
            result += listify(i, flatten=True)
        else:
            result.append(i)
    return result


def extract_as_list(dict_object: T.Dict[_T, _U], key: _T, pop: bool = False) -> T.List[_U]:
    '''
    Extracts all values from given dict_object and listifies them.
    '''
    fetch = dict_object.get
    if pop:
        fetch = dict_object.pop
    # If there's only one key, we don't return a list with one element
    return listify(fetch(key, []), flatten=True)


def typeslistify(item: 'T.Union[_T, T.Sequence[_T]]',
                 types: 'T.Union[T.Type[_T], T.Tuple[T.Type[_T]]]') -> T.List[_T]:
    '''
    Ensure that type(@item) is one of @types or a
    list of items all of which are of type @types
    '''
    if isinstance(item, types):
        item = T.cast(T.List[_T], [item])
    if not isinstance(item, list):
        raise MesonException('Item must be a list or one of {!r}'.format(types))
    for i in item:
        if i is not None and not isinstance(i, types):
            raise MesonException('List item must be one of {!r}'.format(types))
    return item


def stringlistify(item: T.Union[T.Any, T.Sequence[T.Any]]) -> T.List[str]:
    return typeslistify(item, str)


def expand_arguments(args: T.Iterable[str]) -> T.Optional[T.List[str]]:
    expended_args = []  # type: T.List[str]
    for arg in args:
        if not arg.startswith('@'):
            expended_args.append(arg)
            continue

        args_file = arg[1:]
        try:
            with open(args_file) as f:
                extended_args = f.read().split()
            expended_args += extended_args
        except Exception as e:
            mlog.error('Expanding command line arguments:',  args_file, 'not found')
            mlog.exception(e)
            return None
    return expended_args


def partition(pred: T.Callable[[_T], object], iterable: T.Iterator[_T]) -> T.Tuple[T.Iterator[_T], T.Iterator[_T]]:
    """Use a predicate to partition entries into false entries and true
    entries.

    >>> x, y = partition(is_odd, range(10))
    >>> (list(x), list(y))
    ([0, 2, 4, 6, 8], [1, 3, 5, 7, 9])
    """
    t1, t2 = tee(iterable)
    return filterfalse(pred, t1), filter(pred, t2)


def Popen_safe(args: T.List[str], write: T.Optional[str] = None,
               stdout: T.Union[T.BinaryIO, int] = subprocess.PIPE,
               stderr: T.Union[T.BinaryIO, int] = subprocess.PIPE,
               **kwargs: T.Any) -> T.Tuple[subprocess.Popen, str, str]:
    import locale
    encoding = locale.getpreferredencoding()
    # Redirect stdin to DEVNULL otherwise the command run by us here might mess
    # up the console and ANSI colors will stop working on Windows.
    if 'stdin' not in kwargs:
        kwargs['stdin'] = subprocess.DEVNULL
    if sys.version_info < (3, 6) or not sys.stdout.encoding or encoding.upper() != 'UTF-8':
        p, o, e = Popen_safe_legacy(args, write=write, stdout=stdout, stderr=stderr, **kwargs)
    else:
        p = subprocess.Popen(args, universal_newlines=True, close_fds=False,
                             stdout=stdout, stderr=stderr, **kwargs)
        o, e = p.communicate(write)
    # Sometimes the command that we run will call another command which will be
    # without the above stdin workaround, so set the console mode again just in
    # case.
    mlog.setup_console()
    return p, o, e


def Popen_safe_legacy(args: T.List[str], write: T.Optional[str] = None,
                      stdout: T.Union[T.BinaryIO, int] = subprocess.PIPE,
                      stderr: T.Union[T.BinaryIO, int] = subprocess.PIPE,
                      **kwargs: T.Any) -> T.Tuple[subprocess.Popen, str, str]:
    p = subprocess.Popen(args, universal_newlines=False, close_fds=False,
                         stdout=stdout, stderr=stderr, **kwargs)
    input_ = None  # type: T.Optional[bytes]
    if write is not None:
        input_ = write.encode('utf-8')
    o, e = p.communicate(input_)
    if o is not None:
        if sys.stdout.encoding:
            o = o.decode(encoding=sys.stdout.encoding, errors='replace').replace('\r\n', '\n')
        else:
            o = o.decode(errors='replace').replace('\r\n', '\n')
    if e is not None:
        if sys.stderr.encoding:
            e = e.decode(encoding=sys.stderr.encoding, errors='replace').replace('\r\n', '\n')
        else:
            e = e.decode(errors='replace').replace('\r\n', '\n')
    return p, o, e


def iter_regexin_iter(regexiter: T.Iterable[str], initer: T.Iterable[str]) -> T.Optional[str]:
    '''
    Takes each regular expression in @regexiter and tries to search for it in
    every item in @initer. If there is a match, returns that match.
    Else returns False.
    '''
    for regex in regexiter:
        for ii in initer:
            if not isinstance(ii, str):
                continue
            match = re.search(regex, ii)
            if match:
                return match.group()
    return None


def _substitute_values_check_errors(command: T.List[str], values: T.Dict[str, str]) -> None:
    # Error checking
    inregex = ['@INPUT([0-9]+)?@', '@PLAINNAME@', '@BASENAME@']  # type: T.List[str]
    outregex = ['@OUTPUT([0-9]+)?@', '@OUTDIR@']                 # type: T.List[str]
    if '@INPUT@' not in values:
        # Error out if any input-derived templates are present in the command
        match = iter_regexin_iter(inregex, command)
        if match:
            m = 'Command cannot have {!r}, since no input files were specified'
            raise MesonException(m.format(match))
    else:
        if len(values['@INPUT@']) > 1:
            # Error out if @PLAINNAME@ or @BASENAME@ is present in the command
            match = iter_regexin_iter(inregex[1:], command)
            if match:
                raise MesonException('Command cannot have {!r} when there is '
                                     'more than one input file'.format(match))
        # Error out if an invalid @INPUTnn@ template was specified
        for each in command:
            if not isinstance(each, str):
                continue
            match2 = re.search(inregex[0], each)
            if match2 and match2.group() not in values:
                m = 'Command cannot have {!r} since there are only {!r} inputs'
                raise MesonException(m.format(match2.group(), len(values['@INPUT@'])))
    if '@OUTPUT@' not in values:
        # Error out if any output-derived templates are present in the command
        match = iter_regexin_iter(outregex, command)
        if match:
            m = 'Command cannot have {!r} since there are no outputs'
            raise MesonException(m.format(match))
    else:
        # Error out if an invalid @OUTPUTnn@ template was specified
        for each in command:
            if not isinstance(each, str):
                continue
            match2 = re.search(outregex[0], each)
            if match2 and match2.group() not in values:
                m = 'Command cannot have {!r} since there are only {!r} outputs'
                raise MesonException(m.format(match2.group(), len(values['@OUTPUT@'])))


def substitute_values(command: T.List[str], values: T.Dict[str, str]) -> T.List[str]:
    '''
    Substitute the template strings in the @values dict into the list of
    strings @command and return a new list. For a full list of the templates,
    see get_filenames_templates_dict()

    If multiple inputs/outputs are given in the @values dictionary, we
    substitute @INPUT@ and @OUTPUT@ only if they are the entire string, not
    just a part of it, and in that case we substitute *all* of them.
    '''
    # Error checking
    _substitute_values_check_errors(command, values)
    # Substitution
    outcmd = []  # type: T.List[str]
    rx_keys = [re.escape(key) for key in values if key not in ('@INPUT@', '@OUTPUT@')]
    value_rx = re.compile('|'.join(rx_keys)) if rx_keys else None
    for vv in command:
        if not isinstance(vv, str):
            outcmd.append(vv)
        elif '@INPUT@' in vv:
            inputs = values['@INPUT@']
            if vv == '@INPUT@':
                outcmd += inputs
            elif len(inputs) == 1:
                outcmd.append(vv.replace('@INPUT@', inputs[0]))
            else:
                raise MesonException("Command has '@INPUT@' as part of a "
                                     "string and more than one input file")
        elif '@OUTPUT@' in vv:
            outputs = values['@OUTPUT@']
            if vv == '@OUTPUT@':
                outcmd += outputs
            elif len(outputs) == 1:
                outcmd.append(vv.replace('@OUTPUT@', outputs[0]))
            else:
                raise MesonException("Command has '@OUTPUT@' as part of a "
                                     "string and more than one output file")
        # Append values that are exactly a template string.
        # This is faster than a string replace.
        elif vv in values:
            outcmd.append(values[vv])
        # Substitute everything else with replacement
        elif value_rx:
            outcmd.append(value_rx.sub(lambda m: values[m.group(0)], vv))
        else:
            outcmd.append(vv)
    return outcmd


def get_filenames_templates_dict(inputs: T.List[str], outputs: T.List[str]) -> T.Dict[str, T.Union[str, T.List[str]]]:
    '''
    Create a dictionary with template strings as keys and values as values for
    the following templates:

    @INPUT@  - the full path to one or more input files, from @inputs
    @OUTPUT@ - the full path to one or more output files, from @outputs
    @OUTDIR@ - the full path to the directory containing the output files

    If there is only one input file, the following keys are also created:

    @PLAINNAME@ - the filename of the input file
    @BASENAME@ - the filename of the input file with the extension removed

    If there is more than one input file, the following keys are also created:

    @INPUT0@, @INPUT1@, ... one for each input file

    If there is more than one output file, the following keys are also created:

    @OUTPUT0@, @OUTPUT1@, ... one for each output file
    '''
    values = {}  # type: T.Dict[str, T.Union[str, T.List[str]]]
    # Gather values derived from the input
    if inputs:
        # We want to substitute all the inputs.
        values['@INPUT@'] = inputs
        for (ii, vv) in enumerate(inputs):
            # Write out @INPUT0@, @INPUT1@, ...
            values['@INPUT{}@'.format(ii)] = vv
        if len(inputs) == 1:
            # Just one value, substitute @PLAINNAME@ and @BASENAME@
            values['@PLAINNAME@'] = plain = os.path.basename(inputs[0])
            values['@BASENAME@'] = os.path.splitext(plain)[0]
    if outputs:
        # Gather values derived from the outputs, similar to above.
        values['@OUTPUT@'] = outputs
        for (ii, vv) in enumerate(outputs):
            values['@OUTPUT{}@'.format(ii)] = vv
        # Outdir should be the same for all outputs
        values['@OUTDIR@'] = os.path.dirname(outputs[0])
        # Many external programs fail on empty arguments.
        if values['@OUTDIR@'] == '':
            values['@OUTDIR@'] = '.'
    return values


def _make_tree_writable(topdir: str) -> None:
    # Ensure all files and directories under topdir are writable
    # (and readable) by owner.
    for d, _, files in os.walk(topdir):
        os.chmod(d, os.stat(d).st_mode | stat.S_IWRITE | stat.S_IREAD)
        for fname in files:
            fpath = os.path.join(d, fname)
            if os.path.isfile(fpath):
                os.chmod(fpath, os.stat(fpath).st_mode | stat.S_IWRITE | stat.S_IREAD)


def windows_proof_rmtree(f: str) -> None:
    # On Windows if anyone is holding a file open you can't
    # delete it. As an example an anti virus scanner might
    # be scanning files you are trying to delete. The only
    # way to fix this is to try again and again.
    delays = [0.1, 0.1, 0.2, 0.2, 0.2, 0.5, 0.5, 1, 1, 1, 1, 2]
    # Start by making the tree wriable.
    _make_tree_writable(f)
    for d in delays:
        try:
            shutil.rmtree(f)
            return
        except FileNotFoundError:
            return
        except OSError:
            time.sleep(d)
    # Try one last time and throw if it fails.
    shutil.rmtree(f)


def windows_proof_rm(fpath: str) -> None:
    """Like windows_proof_rmtree, but for a single file."""
    if os.path.isfile(fpath):
        os.chmod(fpath, os.stat(fpath).st_mode | stat.S_IWRITE | stat.S_IREAD)
    delays = [0.1, 0.1, 0.2, 0.2, 0.2, 0.5, 0.5, 1, 1, 1, 1, 2]
    for d in delays:
        try:
            os.unlink(fpath)
            return
        except FileNotFoundError:
            return
        except OSError:
            time.sleep(d)
    os.unlink(fpath)


def detect_subprojects(spdir_name: str, current_dir: str = '',
                       result: T.Optional[T.Dict[str, T.List[str]]] = None) -> T.Optional[T.Dict[str, T.List[str]]]:
    if result is None:
        result = {}
    spdir = os.path.join(current_dir, spdir_name)
    if not os.path.exists(spdir):
        return result
    for trial in glob(os.path.join(spdir, '*')):
        basename = os.path.basename(trial)
        if trial == 'packagecache':
            continue
        append_this = True
        if os.path.isdir(trial):
            detect_subprojects(spdir_name, trial, result)
        elif trial.endswith('.wrap') and os.path.isfile(trial):
            basename = os.path.splitext(basename)[0]
        else:
            append_this = False
        if append_this:
            if basename in result:
                result[basename].append(trial)
            else:
                result[basename] = [trial]
    return result


def substring_is_in_list(substr: str, strlist: T.List[str]) -> bool:
    for s in strlist:
        if substr in s:
            return True
    return False


class OrderedSet(T.MutableSet[_T]):
    """A set that preserves the order in which items are added, by first
    insertion.
    """
    def __init__(self, iterable: T.Optional[T.Iterable[_T]] = None):
        # typing.OrderedDict is new in 3.7.2, so we can't use that, but we can
        # use MutableMapping, which is fine in this case.
        self.__container = collections.OrderedDict()  # type: T.MutableMapping[_T, None]
        if iterable:
            self.update(iterable)

    def __contains__(self, value: object) -> bool:
        return value in self.__container

    def __iter__(self) -> T.Iterator[_T]:
        return iter(self.__container.keys())

    def __len__(self) -> int:
        return len(self.__container)

    def __repr__(self) -> str:
        # Don't print 'OrderedSet("")' for an empty set.
        if self.__container:
            return 'OrderedSet("{}")'.format(
                '", "'.join(repr(e) for e in self.__container.keys()))
        return 'OrderedSet()'

    def __reversed__(self) -> T.Iterator[_T]:
        # Mypy is complaining that sets cant be reversed, which is true for
        # unordered sets, but this is an ordered, set so reverse() makes sense.
        return reversed(self.__container.keys())  # type: ignore

    def add(self, value: _T) -> None:
        self.__container[value] = None

    def discard(self, value: _T) -> None:
        if value in self.__container:
            del self.__container[value]

    def update(self, iterable: T.Iterable[_T]) -> None:
        for item in iterable:
            self.__container[item] = None

    def difference(self, set_: T.Union[T.Set[_T], 'OrderedSet[_T]']) -> 'OrderedSet[_T]':
        return type(self)(e for e in self if e not in set_)

class BuildDirLock:

    def __init__(self, builddir: str):
        self.lockfilename = os.path.join(builddir, 'meson-private/meson.lock')

    def __enter__(self):
        self.lockfile = open(self.lockfilename, 'w')
        try:
            if have_fcntl:
                fcntl.flock(self.lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
            elif have_msvcrt:
                msvcrt.locking(self.lockfile.fileno(), msvcrt.LK_NBLCK, 1)
        except (BlockingIOError, PermissionError):
            self.lockfile.close()
            raise MesonException('Some other Meson process is already using this build directory. Exiting.')

    def __exit__(self, *args):
        if have_fcntl:
            fcntl.flock(self.lockfile, fcntl.LOCK_UN)
        elif have_msvcrt:
            msvcrt.locking(self.lockfile.fileno(), msvcrt.LK_UNLCK, 1)
        self.lockfile.close()

def relpath(path: str, start: str) -> str:
    # On Windows a relative path can't be evaluated for paths on two different
    # drives (i.e. c:\foo and f:\bar).  The only thing left to do is to use the
    # original absolute path.
    try:
        return os.path.relpath(path, start)
    except (TypeError, ValueError):
        return path

def path_is_in_root(path: Path, root: Path, resolve: bool = False) -> bool:
    # Check wheter a path is within the root directory root
    try:
        if resolve:
            path.resolve().relative_to(root.resolve())
        else:
            path.relative_to(root)
    except ValueError:
        return False
    return True

class LibType(Enum):

    """Enumeration for library types."""

    SHARED = 0
    STATIC = 1
    PREFER_SHARED = 2
    PREFER_STATIC = 3


class ProgressBarFallback:  # lgtm [py/iter-returns-non-self]
    '''
    Fallback progress bar implementation when tqdm is not found

    Since this class is not an actual iterator, but only provides a minimal
    fallback, it is safe to ignore the 'Iterator does not return self from
    __iter__ method' warning.
    '''
    def __init__(self, iterable: T.Optional[T.Iterable[str]] = None, total: T.Optional[int] = None,
                 bar_type: T.Optional[str] = None, desc: T.Optional[str] = None):
        if iterable is not None:
            self.iterable = iter(iterable)
            return
        self.total = total
        self.done = 0
        self.printed_dots = 0
        if self.total and bar_type == 'download':
            print('Download size:', self.total)
        if desc:
            print('{}: '.format(desc), end='')

    # Pretend to be an iterator when called as one and don't print any
    # progress
    def __iter__(self) -> T.Iterator[str]:
        return self.iterable

    def __next__(self) -> str:
        return next(self.iterable)

    def print_dot(self) -> None:
        print('.', end='')
        sys.stdout.flush()
        self.printed_dots += 1

    def update(self, progress: int) -> None:
        self.done += progress
        if not self.total:
            # Just print one dot per call if we don't have a total length
            self.print_dot()
            return
        ratio = int(self.done / self.total * 10)
        while self.printed_dots < ratio:
            self.print_dot()

    def close(self) -> None:
        print('')

try:
    from tqdm import tqdm
except ImportError:
    # ideally we would use a typing.Protocol here, but it's part of typing_extensions until 3.8
    ProgressBar = ProgressBarFallback  # type: T.Union[T.Type[ProgressBarFallback], T.Type[ProgressBarTqdm]]
else:
    class ProgressBarTqdm(tqdm):
        def __init__(self, *args, bar_type: T.Optional[str] = None, **kwargs):
            if bar_type == 'download':
                kwargs.update({'unit': 'bytes', 'leave': True})
            else:
                kwargs.update({'leave': False})
            kwargs['ncols'] = 100
            super().__init__(*args, **kwargs)

    ProgressBar = ProgressBarTqdm


def get_wine_shortpath(winecmd: T.List[str], wine_paths: T.Sequence[str]) -> str:
    """Get A short version of @wine_paths to avoid reaching WINEPATH number
    of char limit.
    """

    wine_paths = list(OrderedSet(wine_paths))

    getShortPathScript = '%s.bat' % str(uuid.uuid4()).lower()[:5]
    with open(getShortPathScript, mode='w') as f:
        f.write("@ECHO OFF\nfor %%x in (%*) do (\n echo|set /p=;%~sx\n)\n")
        f.flush()
    try:
        with open(os.devnull, 'w') as stderr:
            wine_path = subprocess.check_output(
                winecmd +
                ['cmd', '/C', getShortPathScript] + wine_paths,
                stderr=stderr).decode('utf-8')
    except subprocess.CalledProcessError as e:
        print("Could not get short paths: %s" % e)
        wine_path = ';'.join(wine_paths)
    finally:
        os.remove(getShortPathScript)
    if len(wine_path) > 2048:
        raise MesonException(
            'WINEPATH size {} > 2048'
            ' this will cause random failure.'.format(
                len(wine_path)))

    return wine_path.strip(';')


def run_once(func: T.Callable[..., _T]) -> T.Callable[..., _T]:
    ret = []  # type: T.List[_T]

    @wraps(func)
    def wrapper(*args: T.Any, **kwargs: T.Any) -> _T:
        if ret:
            return ret[0]

        val = func(*args, **kwargs)
        ret.append(val)
        return val

    return wrapper


class OptionProxy(T.Generic[_T]):
    def __init__(self, value: _T):
        self.value = value


class OptionOverrideProxy:

    '''Mimic an option list but transparently override selected option
    values.
    '''

    # TODO: the typing here could be made more explicit using a TypeDict from
    # python 3.8 or typing_extensions

    def __init__(self, overrides: T.Dict[str, T.Any], *options: 'OptionDictType'):
        self.overrides = overrides
        self.options = options

    def __getitem__(self, option_name: str) -> T.Any:
        for opts in self.options:
            if option_name in opts:
                return self._get_override(option_name, opts[option_name])
        raise KeyError('Option not found', option_name)

    def _get_override(self, option_name: str, base_opt: 'UserOption[T.Any]') -> T.Union[OptionProxy[T.Any], 'UserOption[T.Any]']:
        if option_name in self.overrides:
            return OptionProxy(base_opt.validate_value(self.overrides[option_name]))
        return base_opt

    def copy(self) -> T.Dict[str, T.Any]:
        result = {}  # type: T.Dict[str, T.Any]
        for opts in self.options:
            for option_name in opts:
                result[option_name] = self._get_override(option_name, opts[option_name])
        return result
