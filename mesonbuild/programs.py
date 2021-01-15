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

"""Representations and logic for External and Internal Programs."""

import functools
import os
import re
import shutil
import stat
import sys
import typing as T
from pathlib import Path

from . import mesonlib
from . import mlog
from .mesonlib import MachineChoice

if T.TYPE_CHECKING:
    from .build import Executable
    from .environment import Environment


class ExternalProgram:

    """A program that is found on the system."""

    windows_exts = ('exe', 'msc', 'com', 'bat', 'cmd')
    _VERSION_ARG = ['--version']

    def __init__(self, name: str, command: T.Optional[T.List[str]] = None,
                 silent: bool = False, search_dir: T.Optional[str] = None,
                 extra_search_dirs: T.Optional[T.List[str]] = None,
                 for_machine: MachineChoice = MachineChoice.BUILD,
                 version_arg: T.Optional[T.List[str]] = None):
        self.name = name
        self.path = None  # type: T.Optional[str]
        self.for_machine = for_machine
        self.version_arg = version_arg if version_arg is not None else self._VERSION_ARG
        if command is not None:
            self.command = mesonlib.listify(command)
            if mesonlib.is_windows():
                cmd = self.command[0]
                args = self.command[1:]
                # Check whether the specified cmd is a path to a script, in
                # which case we need to insert the interpreter. If not, try to
                # use it as-is.
                ret = self._shebang_to_cmd(cmd)
                if ret:
                    self.command = ret + args
                else:
                    self.command = [cmd] + args
        else:
            all_search_dirs = [search_dir]
            if extra_search_dirs:
                all_search_dirs += extra_search_dirs
            for d in all_search_dirs:
                self.command = self._search(name, d)
                if self.found():
                    break

        if self.found():
            # Set path to be the last item that is actually a file (in order to
            # skip options in something like ['python', '-u', 'file.py']. If we
            # can't find any components, default to the last component of the path.
            for arg in reversed(self.command):
                if arg is not None and os.path.isfile(arg):
                    self.path = arg
                    break
            else:
                self.path = self.command[-1]

        if not silent:
            # ignore the warning because derived classes never call this __init__
            # method, and thus only the found() method of this class is ever executed
            if self.found():  # lgtm [py/init-calls-subclass]
                mlog.log('Program', mlog.bold(name), 'found:', mlog.green('YES'),
                         '(%s)' % ' '.join(self.command))
            else:
                mlog.log('Program', mlog.bold(name), 'found:', mlog.red('NO'))

    def __repr__(self) -> str:
        r = '<{} {!r} -> {!r}>'
        return r.format(self.__class__.__name__, self.name, self.command)

    def description(self) -> str:
        '''Human friendly description of the command'''
        return ' '.join(self.command)

    @classmethod
    def from_bin_list(cls, env: 'Environment', for_machine: MachineChoice, name: str) -> 'ExternalProgram':
        # There is a static `for_machine` for this class because the binary
        # aways runs on the build platform. (It's host platform is our build
        # platform.) But some external programs have a target platform, so this
        # is what we are specifying here.
        command = env.lookup_binary_entry(for_machine, name)
        if command is None:
            return NonExistingExternalProgram()
        return cls.from_entry(name, command)

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def _windows_sanitize_path(path: str) -> str:
        # Ensure that we use USERPROFILE even when inside MSYS, MSYS2, Cygwin, etc.
        if 'USERPROFILE' not in os.environ:
            return path
        # The WindowsApps directory is a bit of a problem. It contains
        # some zero-sized .exe files which have "reparse points", that
        # might either launch an installed application, or might open
        # a page in the Windows Store to download the application.
        #
        # To handle the case where the python interpreter we're
        # running on came from the Windows Store, if we see the
        # WindowsApps path in the search path, replace it with
        # dirname(sys.executable).
        appstore_dir = Path(os.environ['USERPROFILE']) / 'AppData' / 'Local' / 'Microsoft' / 'WindowsApps'
        paths = []
        for each in path.split(os.pathsep):
            if Path(each) != appstore_dir:
                paths.append(each)
            elif 'WindowsApps' in sys.executable:
                paths.append(os.path.dirname(sys.executable))
        return os.pathsep.join(paths)

    @classmethod
    def from_entry(cls, name: str, command: T.Union[str, T.List[str]],
                   silent: bool = False) -> 'ExternalProgram':
        if isinstance(command, list):
            if len(command) == 1:
                command = command[0]
        # We cannot do any searching if the command is a list, and we don't
        # need to search if the path is an absolute path.
        if isinstance(command, list) or os.path.isabs(command):
            if isinstance(command, str):
                command = [command]
            return cls(name, command=command, silent=silent)
        assert isinstance(command, str)
        # Search for the command using the specified string!
        return cls(command, silent=silent)

    @staticmethod
    def _shebang_to_cmd(script: str) -> T.Optional[T.List[str]]:
        """
        Check if the file has a shebang and manually parse it to figure out
        the interpreter to use. This is useful if the script is not executable
        or if we're on Windows (which does not understand shebangs).
        """
        try:
            with open(script) as f:
                first_line = f.readline().strip()
            if first_line.startswith('#!'):
                # In a shebang, everything before the first space is assumed to
                # be the command to run and everything after the first space is
                # the single argument to pass to that command. So we must split
                # exactly once.
                commands = first_line[2:].split('#')[0].strip().split(maxsplit=1)
                if mesonlib.is_windows():
                    # Windows does not have UNIX paths so remove them,
                    # but don't remove Windows paths
                    if commands[0].startswith('/'):
                        commands[0] = commands[0].split('/')[-1]
                    if len(commands) > 0 and commands[0] == 'env':
                        commands = commands[1:]
                    # Windows does not ship python3.exe, but we know the path to it
                    if len(commands) > 0 and commands[0] == 'python3':
                        commands = mesonlib.python_command + commands[1:]
                elif mesonlib.is_haiku():
                    # Haiku does not have /usr, but a lot of scripts assume that
                    # /usr/bin/env always exists. Detect that case and run the
                    # script with the interpreter after it.
                    if commands[0] == '/usr/bin/env':
                        commands = commands[1:]
                    # We know what python3 is, we're running on it
                    if len(commands) > 0 and commands[0] == 'python3':
                        commands = mesonlib.python_command + commands[1:]
                else:
                    # Replace python3 with the actual python3 that we are using
                    if commands[0] == '/usr/bin/env' and commands[1] == 'python3':
                        commands = mesonlib.python_command + commands[2:]
                    elif commands[0].split('/')[-1] == 'python3':
                        commands = mesonlib.python_command + commands[1:]
                return commands + [script]
        except Exception as e:
            mlog.debug(str(e))
        mlog.debug('Unusable script {!r}'.format(script))
        return None

    def _is_executable(self, path: str) -> bool:
        suffix = os.path.splitext(path)[-1].lower()[1:]
        execmask = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if mesonlib.is_windows():
            if suffix in self.windows_exts:
                return True
        elif os.stat(path).st_mode & execmask:
            return not os.path.isdir(path)
        return False

    def _search_dir(self, name: str, search_dir: T.Optional[str]) -> T.Optional[list]:
        if search_dir is None:
            return None
        trial = os.path.join(search_dir, name)
        if os.path.exists(trial):
            if self._is_executable(trial):
                return [trial]
            # Now getting desperate. Maybe it is a script file that is
            # a) not chmodded executable, or
            # b) we are on windows so they can't be directly executed.
            return self._shebang_to_cmd(trial)
        else:
            if mesonlib.is_windows():
                for ext in self.windows_exts:
                    trial_ext = '{}.{}'.format(trial, ext)
                    if os.path.exists(trial_ext):
                        return [trial_ext]
        return None

    def _search_windows_special_cases(self, name: str, command: str) -> T.List[T.Optional[str]]:
        '''
        Lots of weird Windows quirks:
        1. PATH search for @name returns files with extensions from PATHEXT,
           but only self.windows_exts are executable without an interpreter.
        2. @name might be an absolute path to an executable, but without the
           extension. This works inside MinGW so people use it a lot.
        3. The script is specified without an extension, in which case we have
           to manually search in PATH.
        4. More special-casing for the shebang inside the script.
        '''
        if command:
            # On Windows, even if the PATH search returned a full path, we can't be
            # sure that it can be run directly if it's not a native executable.
            # For instance, interpreted scripts sometimes need to be run explicitly
            # with an interpreter if the file association is not done properly.
            name_ext = os.path.splitext(command)[1]
            if name_ext[1:].lower() in self.windows_exts:
                # Good, it can be directly executed
                return [command]
            # Try to extract the interpreter from the shebang
            commands = self._shebang_to_cmd(command)
            if commands:
                return commands
            return [None]
        # Maybe the name is an absolute path to a native Windows
        # executable, but without the extension. This is technically wrong,
        # but many people do it because it works in the MinGW shell.
        if os.path.isabs(name):
            for ext in self.windows_exts:
                command = '{}.{}'.format(name, ext)
                if os.path.exists(command):
                    return [command]
        # On Windows, interpreted scripts must have an extension otherwise they
        # cannot be found by a standard PATH search. So we do a custom search
        # where we manually search for a script with a shebang in PATH.
        search_dirs = self._windows_sanitize_path(os.environ.get('PATH', '')).split(';')
        for search_dir in search_dirs:
            commands = self._search_dir(name, search_dir)
            if commands:
                return commands
        return [None]

    def _search(self, name: str, search_dir: T.Optional[str]) -> T.List[T.Optional[str]]:
        '''
        Search in the specified dir for the specified executable by name
        and if not found search in PATH
        '''
        commands = self._search_dir(name, search_dir)
        if commands:
            return commands
        # Do a standard search in PATH
        path = os.environ.get('PATH', None)
        if mesonlib.is_windows() and path:
            path = self._windows_sanitize_path(path)
        command = shutil.which(name, path=path)
        if mesonlib.is_windows():
            return self._search_windows_special_cases(name, command)
        # On UNIX-like platforms, shutil.which() is enough to find
        # all executables whether in PATH or with an absolute path
        return [command]

    def found(self) -> bool:
        return self.command[0] is not None

    def get_command(self) -> T.List[str]:
        return self.command[:]

    def get_path(self) -> T.Optional[str]:
        return self.path

    def get_name(self) -> str:
        return self.name

    @functools.lru_cache()
    def get_version(self) -> T.Optional[str]:
        cmd = self.get_command() + self.version_arg
        p, out, err = mesonlib.Popen_safe(cmd)
        if p.returncode != 0:
            raise mesonlib.MesonException('Failed running "{}"'.format(' ' .join(cmd)))
        if not out:
            out = err
        match = re.search(r'([0-9][0-9\.]+)', out)
        if not match:
            return None
        return str(match.group(0))

    def log(self, cached: bool) -> None:
        """Function that logs that an executable was found."""
        info = []  # type: T.List[T.Union[str, mlog.AnsiDecorator]]
        if self.found():
            info.append(mlog.green('YES'))
            version = self.get_version()
            if version:
                info.append(mlog.normal_cyan(version))
                # TODO: explict?
            if isinstance(self, (OverrideProgram, InternalProgram)):
                info.append(mlog.blue('(overridden)'))
            elif cached:
                info.append(mlog.blue('(cached)'))
        else:
            info.append(mlog.red('NO'))

        mlog.log('Program', mlog.bold(self.name), 'found:', *info)


class NonExistingExternalProgram(ExternalProgram):  # lgtm [py/missing-call-to-init]
    "A program that will never exist"

    def __init__(self, name: str = 'nonexistingprogram') -> None:
        self.name = name
        self.command = [None]
        self.path = None

    def __repr__(self) -> str:
        r = '<{} {!r} -> {!r}>'
        return r.format(self.__class__.__name__, self.name, self.command)

    def found(self) -> bool:
        return False

    @functools.lru_cache()
    def get_version(self) -> T.Optional[str]:
        return None


class EmptyExternalProgram(ExternalProgram):  # lgtm [py/missing-call-to-init]
    '''
    A program object that returns an empty list of commands. Used for cases
    such as a cross file exe_wrapper to represent that it's not required.
    '''

    def __init__(self) -> None:
        self.name = None
        self.command = []
        self.path = None

    def __repr__(self) -> str:
        r = '<{} {!r} -> {!r}>'
        return r.format(self.__class__.__name__, self.name, self.command)

    def found(self) -> bool:
        return True

    @functools.lru_cache()
    def get_version(self) -> T.Optional[str]:
        return None


class ScriptProgram(ExternalProgram):

    """A wrapper around a local script.

    Needs to konw what subproject it is from, as we don't want to return
    scripts from one subprojct in another.
    """

    def __init__(self, name: str, command: T.Optional[T.List[str]] = None,
                 silent: bool = False, search_dir: T.Optional[str] = None,
                 extra_search_dirs: T.Optional[T.List[str]] = None,
                 for_machine: MachineChoice = MachineChoice.BUILD,
                 version_arg: T.Optional[T.List[str]] = None,
                 subproject: str = ''):
        super().__init__(name, command=command, silent=silent, search_dir=search_dir,
                         extra_search_dirs=extra_search_dirs, for_machine=for_machine,
                         version_arg=version_arg)
        self.subproject = subproject

    @functools.lru_cache()
    def get_version(self) -> T.Optional[str]:
        try:
            return super().get_version()
        except mesonlib.MesonException:
            # Scripts may not implement --version, that's fine
            return None


class OverrideProgram(ExternalProgram):

    """A script overriding a program."""

    @functools.lru_cache()
    def get_version(self) -> T.Optional[str]:
        try:
            return super().get_version()
        except mesonlib.MesonException:
            # Scripts may not implement --version, that's fine
            return None

    def found(self) -> bool:
        return True


class InternalProgram(ExternalProgram):

    """A Program that is actually being built by us."""

    def __init__(self, exe: 'Executable', version: T.Optional[str] = None) -> None:
        self.name = exe.name
        self.path = exe.filename
        self.command = exe.outputs
        self.version = version

    def found(self) -> bool:
        return True

    @functools.lru_cache()
    def get_version(self) -> T.Optional[str]:
        return self.version


class ExternalProgramConfigTool(ExternalProgram):

    """A special case of ExternalProgram for config tools."""

    __strip_version = re.compile(r'^[0-9][0-9.]+')

    @functools.lru_cache()
    def get_version(self) -> T.Optional[str]:
        out = super().get_version()
        m = self.__strip_version.match(out)
        if m:
            # Ensure that there isn't a trailing '.', such as an input like
            # `1.2.3.git-1234`
            return m.group(0).rstrip('.')
        return out


class ExternalProgramCMake(ExternalProgram):

    """Special external program for cmake.
    """

    @functools.lru_cache()
    def get_version(self) -> T.Optional[str]:
        cmd = self.get_command() + ['--version']
        p, out, err = mesonlib.Popen_safe(cmd)
        if p.returncode != 0:
            raise mesonlib.MesonException('Failed running "{}"'.format(' ' .join(cmd)))
        if not out:
            out = err
        match = re.search(r'(cmake|cmake3)\s*version\s*([\d.]+)', out)
        if not match:
            return None
        return match.group(2)


class ExternalProgramPkgConfig(ExternalProgram):

    """Special external program for PkgConfig.
    """


class ExternalProgramQMake(ExternalProgram):

    """Special program for qmake."""

    @functools.lru_cache()
    def get_version(self) -> T.Optional[str]:
        cmd = self.get_command() + ['-v']
        p, out, err = mesonlib.Popen_safe(cmd)
        if p.returncode != 0:
            raise mesonlib.MesonException('Failed running "{}"'.format(' ' .join(cmd)))
        if not out:
            out = err
        match = re.search(r'Using Qt version ([\d+.]+)', out)
        if not match:
            return None
        return match.group(1)


SPECIAL_PROGRAMS = {
    'cmake': ExternalProgramCMake,
    'pkg-config': ExternalProgramPkgConfig,
    'qmake': ExternalProgramQMake,
}  # type: T.Dict[str, T.Type[ExternalProgram]]
