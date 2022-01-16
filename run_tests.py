#!/usr/bin/env python3

# Copyright 2012-2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Work around some pathlib bugs...
from mesonbuild import _pathlib
import sys
sys.modules['pathlib'] = _pathlib

import collections
import os
import time
import shutil
import subprocess
import platform
import argparse
import traceback
from io import StringIO
from enum import Enum
from glob import glob
from pathlib import Path
from unittest import mock
import typing as T

from mesonbuild import compilers
from mesonbuild import dependencies
from mesonbuild import mesonlib
from mesonbuild import mesonmain
from mesonbuild import mtest
from mesonbuild import mlog
from mesonbuild.environment import Environment, detect_ninja
from mesonbuild.coredata import backendlist, version as meson_version
from mesonbuild.mesonlib import OptionKey, setup_vsenv

NINJA_1_9_OR_NEWER = False
NINJA_CMD = None
# If we're on CI, just assume we have ninja in PATH and it's new enough because
# we provide that. This avoids having to detect ninja for every subprocess unit
# test that we run.
if 'CI' in os.environ:
    NINJA_1_9_OR_NEWER = True
    NINJA_CMD = ['ninja']
else:
    # Look for 1.9 to see if https://github.com/ninja-build/ninja/issues/1219
    # is fixed
    NINJA_CMD = detect_ninja('1.9')
    if NINJA_CMD is not None:
        NINJA_1_9_OR_NEWER = True
    else:
        mlog.warning('Found ninja <1.9, tests will run slower', once=True)
        NINJA_CMD = detect_ninja()
if NINJA_CMD is None:
    raise RuntimeError('Could not find Ninja v1.7 or newer')

def guess_backend(backend_str: str, msbuild_exe: str) -> T.Tuple['Backend', T.List[str]]:
    # Auto-detect backend if unspecified
    backend_flags = []
    if backend_str is None:
        if msbuild_exe is not None and (mesonlib.is_windows() and not _using_intelcl()):
            backend_str = 'vs' # Meson will auto-detect VS version to use
        else:
            backend_str = 'ninja'

    # Set backend arguments for Meson
    if backend_str.startswith('vs'):
        backend_flags = ['--backend=' + backend_str]
        backend = Backend.vs
    elif backend_str == 'xcode':
        backend_flags = ['--backend=xcode']
        backend = Backend.xcode
    elif backend_str == 'ninja':
        backend_flags = ['--backend=ninja']
        backend = Backend.ninja
    else:
        raise RuntimeError(f'Unknown backend: {backend_str!r}')
    return (backend, backend_flags)


def _using_intelcl() -> bool:
    """
    detect if intending to using Intel-Cl compilers (Intel compilers on Windows)
    Sufficient evidence of intent is that user is working in the Intel compiler
    shell environment, otherwise this function returns False
    """
    if not mesonlib.is_windows():
        return False
    # handle where user tried to "blank" MKLROOT and left space(s)
    if not os.environ.get('MKLROOT', '').strip():
        return False
    if (os.environ.get('CC') == 'icl' or
            os.environ.get('CXX') == 'icl' or
            os.environ.get('FC') == 'ifort'):
        return True
    # Intel-Cl users might not have the CC,CXX,FC envvars set,
    # but because they're in Intel shell, the exe's below are on PATH
    if shutil.which('icl') or shutil.which('ifort'):
        return True
    mlog.warning('It appears you might be intending to use Intel compiler on Windows '
                 'since non-empty environment variable MKLROOT is set to {} '
                 'However, Meson cannot find the Intel WIndows compiler executables (icl,ifort).'
                 'Please try using the Intel shell.'.format(os.environ.get('MKLROOT')))
    return False


# Fake classes and objects for mocking
class FakeBuild:
    def __init__(self, env):
        self.environment = env

class FakeCompilerOptions:
    def __init__(self):
        self.value = []

# TODO: use a typing.Protocol here
def get_fake_options(prefix: str = '') -> argparse.Namespace:
    opts = argparse.Namespace()
    opts.native_file = []
    opts.cross_file = None
    opts.wrap_mode = None
    opts.prefix = prefix
    opts.cmd_line_options = {}
    return opts

def get_fake_env(sdir='', bdir=None, prefix='', opts=None):
    if opts is None:
        opts = get_fake_options(prefix)
    env = Environment(sdir, bdir, opts)
    env.coredata.options[OptionKey('args', lang='c')] = FakeCompilerOptions()
    env.machines.host.cpu_family = 'x86_64' # Used on macOS inside find_library
    return env


Backend = Enum('Backend', 'ninja vs xcode')

if 'MESON_EXE' in os.environ:
    meson_exe = mesonlib.split_args(os.environ['MESON_EXE'])
else:
    meson_exe = None

if mesonlib.is_windows() or mesonlib.is_cygwin():
    exe_suffix = '.exe'
else:
    exe_suffix = ''

def get_meson_script() -> str:
    '''
    Guess the meson that corresponds to the `mesonbuild` that has been imported
    so we can run configure and other commands in-process, since mesonmain.run
    needs to know the meson_command to use.

    Also used by run_unittests.py to determine what meson to run when not
    running in-process (which is the default).
    '''
    # Is there a meson.py next to the mesonbuild currently in use?
    mesonbuild_dir = Path(mesonmain.__file__).resolve().parent.parent
    meson_script = mesonbuild_dir / 'meson.py'
    if meson_script.is_file():
        return str(meson_script)
    # Then if mesonbuild is in PYTHONPATH, meson must be in PATH
    mlog.warning('Could not find meson.py next to the mesonbuild module. '
                 'Trying system meson...')
    meson_cmd = shutil.which('meson')
    if meson_cmd:
        return meson_cmd
    raise RuntimeError(f'Could not find {meson_script!r} or a meson in PATH')

def get_backend_args_for_dir(backend: Backend, builddir: str) -> T.List[str]:
    '''
    Visual Studio backend needs to be given the solution to build
    '''
    if backend is Backend.vs:
        sln_name = glob(os.path.join(builddir, '*.sln'))[0]
        return [os.path.split(sln_name)[-1]]
    return []

def find_vcxproj_with_target(builddir, target):
    import re, fnmatch
    t, ext = os.path.splitext(target)
    if ext:
        p = fr'<TargetName>{t}</TargetName>\s*<TargetExt>\{ext}</TargetExt>'
    else:
        p = fr'<TargetName>{t}</TargetName>'
    for _, _, files in os.walk(builddir):
        for f in fnmatch.filter(files, '*.vcxproj'):
            f = os.path.join(builddir, f)
            with open(f, encoding='utf-8') as o:
                if re.search(p, o.read(), flags=re.MULTILINE):
                    return f
    raise RuntimeError(f'No vcxproj matching {p!r} in {builddir!r}')

def get_builddir_target_args(backend: Backend, builddir, target):
    dir_args = []
    if not target:
        dir_args = get_backend_args_for_dir(backend, builddir)
    if target is None:
        return dir_args
    if backend is Backend.vs:
        vcxproj = find_vcxproj_with_target(builddir, target)
        target_args = [vcxproj]
    elif backend is Backend.xcode:
        target_args = ['-target', target]
    elif backend is Backend.ninja:
        target_args = [target]
    else:
        raise AssertionError(f'Unknown backend: {backend!r}')
    return target_args + dir_args

def get_backend_commands(backend: Backend, debug: bool = False) -> \
        T.Tuple[T.List[str], T.List[str], T.List[str], T.List[str], T.List[str]]:
    install_cmd: T.List[str] = []
    uninstall_cmd: T.List[str] = []
    clean_cmd: T.List[str]
    cmd: T.List[str]
    test_cmd: T.List[str]
    if backend is Backend.vs:
        cmd = ['msbuild']
        clean_cmd = cmd + ['/target:Clean']
        test_cmd = cmd + ['RUN_TESTS.vcxproj']
    elif backend is Backend.xcode:
        cmd = ['xcodebuild']
        clean_cmd = cmd + ['-alltargets', 'clean']
        test_cmd = cmd + ['-target', 'RUN_TESTS']
    elif backend is Backend.ninja:
        global NINJA_CMD
        cmd = NINJA_CMD + ['-w', 'dupbuild=err', '-d', 'explain']
        if debug:
            cmd += ['-v']
        clean_cmd = cmd + ['clean']
        test_cmd = cmd + ['test', 'benchmark']
        install_cmd = cmd + ['install']
        uninstall_cmd = cmd + ['uninstall']
    else:
        raise AssertionError(f'Unknown backend: {backend!r}')
    return cmd, clean_cmd, test_cmd, install_cmd, uninstall_cmd

def ensure_backend_detects_changes(backend: Backend) -> None:
    global NINJA_1_9_OR_NEWER
    if backend is not Backend.ninja:
        return
    need_workaround = False
    # We're using ninja >= 1.9 which has QuLogic's patch for sub-1s resolution
    # timestamps
    if not NINJA_1_9_OR_NEWER:
        mlog.warning('Don\'t have ninja >= 1.9, enabling timestamp resolution workaround', once=True)
        need_workaround = True
    # Increase the difference between build.ninja's timestamp and the timestamp
    # of whatever you changed: https://github.com/ninja-build/ninja/issues/371
    if need_workaround:
        time.sleep(1)

def run_mtest_inprocess(commandlist: T.List[str]) -> T.Tuple[int, str, str]:
    out = StringIO()
    with mock.patch.object(sys, 'stdout', out), mock.patch.object(sys, 'stderr', out):
        returncode = mtest.run_with_args(commandlist)
    return returncode, stdout.getvalue()

def clear_meson_configure_class_caches() -> None:
    compilers.CCompiler.find_library_cache = {}
    compilers.CCompiler.find_framework_cache = {}
    dependencies.PkgConfigDependency.pkgbin_cache = {}
    dependencies.PkgConfigDependency.class_pkgbin = mesonlib.PerMachine(None, None)
    mesonlib.project_meson_versions = collections.defaultdict(str)

def run_configure_inprocess(commandlist: T.List[str], env: T.Optional[T.Dict[str, str]] = None, catch_exception: bool = False) -> T.Tuple[int, str, str]:
    stderr = StringIO()
    stdout = StringIO()
    returncode = 0
    with mock.patch.dict(os.environ, env or {}), mock.patch.object(sys, 'stdout', stdout), mock.patch.object(sys, 'stderr', stderr):
        try:
            returncode = mesonmain.run(commandlist, get_meson_script())
        except Exception:
            if catch_exception:
                returncode = 1
                traceback.print_exc()
            else:
                raise
        finally:
            clear_meson_configure_class_caches()
    return returncode, stdout.getvalue(), stderr.getvalue()

def run_configure_external(full_command: T.List[str], env: T.Optional[T.Dict[str, str]] = None) -> T.Tuple[int, str, str]:
    pc, o, e = mesonlib.Popen_safe(full_command, env=env)
    return pc.returncode, o, e

def run_configure(commandlist: T.List[str], env: T.Optional[T.Dict[str, str]] = None, catch_exception: bool = False) -> T.Tuple[int, str, str]:
    global meson_exe
    if meson_exe:
        return run_configure_external(meson_exe + commandlist, env=env)
    return run_configure_inprocess(commandlist, env=env, catch_exception=catch_exception)

def print_system_info():
    print(mlog.bold('System information.'))
    print('Architecture:', platform.architecture())
    print('Machine:', platform.machine())
    print('Platform:', platform.system())
    print('Processor:', platform.processor())
    print('System:', platform.system())
    print('')
    print(flush=True)

def main():
    print_system_info()
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', default=None, dest='backend',
                        choices=backendlist)
    parser.add_argument('--cross', default=[], dest='cross', action='append')
    parser.add_argument('--cross-only', action='store_true')
    parser.add_argument('--failfast', action='store_true')
    parser.add_argument('--no-unittests', action='store_true', default=False)
    (options, _) = parser.parse_known_args()
    returncode = 0
    backend, _ = guess_backend(options.backend, shutil.which('msbuild'))
    no_unittests = options.no_unittests
    # Running on a developer machine? Be nice!
    if not mesonlib.is_windows() and not mesonlib.is_haiku() and 'CI' not in os.environ:
        os.nice(20)
    # Appveyor sets the `platform` environment variable which completely messes
    # up building with the vs2010 and vs2015 backends.
    #
    # Specifically, MSBuild reads the `platform` environment variable to set
    # the configured value for the platform (Win32/x64/arm), which breaks x86
    # builds.
    #
    # Appveyor setting this also breaks our 'native build arch' detection for
    # Windows in environment.py:detect_windows_arch() by overwriting the value
    # of `platform` set by vcvarsall.bat.
    #
    # While building for x86, `platform` should be unset.
    if 'APPVEYOR' in os.environ and os.environ['arch'] == 'x86':
        os.environ.pop('platform')
    # Run tests
    # Can't pass arguments to unit tests, so set the backend to use in the environment
    env = os.environ.copy()
    if not options.cross:
        cmd = mesonlib.python_command + ['run_meson_command_tests.py', '-v']
        if options.failfast:
            cmd += ['--failfast']
        returncode += subprocess.call(cmd, env=env)
        if options.failfast and returncode != 0:
            return returncode
        if no_unittests:
            print('Skipping all unit tests.')
            print(flush=True)
            returncode = 0
        else:
            print(mlog.bold('Running unittests.'))
            print(flush=True)
            cmd = mesonlib.python_command + ['run_unittests.py', '--backend=' + backend.name, '-v']
            if options.failfast:
                cmd += ['--failfast']
            returncode += subprocess.call(cmd, env=env)
            if options.failfast and returncode != 0:
                return returncode
        cmd = mesonlib.python_command + ['run_project_tests.py'] + sys.argv[1:]
        returncode += subprocess.call(cmd, env=env)
    else:
        cross_test_args = mesonlib.python_command + ['run_cross_test.py']
        for cf in options.cross:
            print(mlog.bold(f'Running {cf} cross tests.'))
            print(flush=True)
            cmd = cross_test_args + ['cross/' + cf]
            if options.failfast:
                cmd += ['--failfast']
            if options.cross_only:
                cmd += ['--cross-only']
            returncode += subprocess.call(cmd, env=env)
            if options.failfast and returncode != 0:
                return returncode
    return returncode

if __name__ == '__main__':
    setup_vsenv()
    print('Meson build system', meson_version, 'Project and Unit Tests')
    raise SystemExit(main())
