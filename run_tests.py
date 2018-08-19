#!/usr/bin/env python3

# Copyright 2012-2017 The Meson development team

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
import sys
import time
import shutil
import subprocess
import tempfile
import platform
from io import StringIO
from enum import Enum
from glob import glob
from pathlib import Path

import mesonbuild
from mesonbuild import mesonlib
from mesonbuild import mesonmain
from mesonbuild import mtest
from mesonbuild import mlog
from mesonbuild.environment import Environment, detect_ninja


# Fake classes and objects for mocking
class FakeBuild:
    def __init__(self, env):
        self.environment = env

class FakeCompilerOptions:
    def __init__(self):
        self.value = []

def get_fake_options(prefix):
    import argparse
    opts = argparse.Namespace()
    opts.cross_file = None
    opts.wrap_mode = None
    opts.prefix = prefix
    opts.cmd_line_options = {}
    return opts

def get_fake_env(sdir, bdir, prefix):
    env = Environment(sdir, bdir, get_fake_options(prefix))
    env.coredata.compiler_options['c_args'] = FakeCompilerOptions()
    return env


Backend = Enum('Backend', 'ninja vs xcode')

if 'MESON_EXE' in os.environ:
    import shlex
    meson_exe = shlex.split(os.environ['MESON_EXE'])
else:
    meson_exe = None

if mesonlib.is_windows() or mesonlib.is_cygwin():
    exe_suffix = '.exe'
else:
    exe_suffix = ''

def get_meson_script():
    '''
    Guess the meson that corresponds to the `mesonbuild` that has been imported
    so we can run configure and other commands in-process, since mesonmain.run
    needs to know the meson_command to use.

    Also used by run_unittests.py to determine what meson to run when not
    running in-process (which is the default).
    '''
    # Is there a meson.py next to the mesonbuild currently in use?
    mesonbuild_dir = Path(mesonbuild.__file__).resolve().parent.parent
    meson_script = mesonbuild_dir / 'meson.py'
    if meson_script.is_file():
        return str(meson_script)
    # Then if mesonbuild is in PYTHONPATH, meson must be in PATH
    mlog.warning('Could not find meson.py next to the mesonbuild module. '
                 'Trying system meson...')
    meson_cmd = shutil.which('meson')
    if meson_cmd:
        return meson_cmd
    raise RuntimeError('Could not find {!r} or a meson in PATH'.format(meson_script))

def get_backend_args_for_dir(backend, builddir):
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
        p = '<TargetName>{}</TargetName>\s*<TargetExt>\{}</TargetExt>'.format(t, ext)
    else:
        p = '<TargetName>{}</TargetName>'.format(t)
    for root, dirs, files in os.walk(builddir):
        for f in fnmatch.filter(files, '*.vcxproj'):
            f = os.path.join(builddir, f)
            with open(f, 'r', encoding='utf-8') as o:
                if re.search(p, o.read(), flags=re.MULTILINE):
                    return f
    raise RuntimeError('No vcxproj matching {!r} in {!r}'.format(p, builddir))

def get_builddir_target_args(backend, builddir, target):
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
        raise AssertionError('Unknown backend: {!r}'.format(backend))
    return target_args + dir_args

def get_backend_commands(backend, debug=False):
    install_cmd = []
    uninstall_cmd = []
    if backend is Backend.vs:
        cmd = ['msbuild']
        clean_cmd = cmd + ['/target:Clean']
        test_cmd = cmd + ['RUN_TESTS.vcxproj']
    elif backend is Backend.xcode:
        cmd = ['xcodebuild']
        clean_cmd = cmd + ['-alltargets', 'clean']
        test_cmd = cmd + ['-target', 'RUN_TESTS']
    elif backend is Backend.ninja:
        # We need at least 1.6 because of -w dupbuild=err
        cmd = [detect_ninja('1.6'), '-w', 'dupbuild=err', '-d', 'explain']
        if cmd[0] is None:
            raise RuntimeError('Could not find Ninja v1.6 or newer')
        if debug:
            cmd += ['-v']
        clean_cmd = cmd + ['clean']
        test_cmd = cmd + ['test', 'benchmark']
        install_cmd = cmd + ['install']
        uninstall_cmd = cmd + ['uninstall']
    else:
        raise AssertionError('Unknown backend: {!r}'.format(backend))
    return cmd, clean_cmd, test_cmd, install_cmd, uninstall_cmd

def ensure_backend_detects_changes(backend):
    # We're using a ninja with QuLogic's patch for sub-1s resolution timestamps
    # and not running on HFS+ which only stores dates in seconds:
    # https://developer.apple.com/legacy/library/technotes/tn/tn1150.html#HFSPlusDates
    # FIXME: Upgrade Travis image to Apple FS when that becomes available
    if 'MESON_FIXED_NINJA' in os.environ and not mesonlib.is_osx():
        return
    # This is needed to increase the difference between build.ninja's
    # timestamp and the timestamp of whatever you changed due to a Ninja
    # bug: https://github.com/ninja-build/ninja/issues/371
    if backend is Backend.ninja:
        time.sleep(1)

def run_mtest_inprocess(commandlist):
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    old_stderr = sys.stderr
    sys.stderr = mystderr = StringIO()
    try:
        returncode = mtest.run(commandlist)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return returncode, mystdout.getvalue(), mystderr.getvalue()

def run_configure_inprocess(commandlist):
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    old_stderr = sys.stderr
    sys.stderr = mystderr = StringIO()
    try:
        returncode = mesonmain.run(commandlist, get_meson_script())
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return returncode, mystdout.getvalue(), mystderr.getvalue()

def run_configure_external(full_command):
    pc, o, e = mesonlib.Popen_safe(full_command)
    return pc.returncode, o, e

def run_configure(commandlist):
    global meson_exe
    if meson_exe:
        return run_configure_external(meson_exe + commandlist)
    return run_configure_inprocess(commandlist)

def print_system_info():
    print(mlog.bold('System information.').get_text(mlog.colorize_console))
    print('Architecture:', platform.architecture())
    print('Machine:', platform.machine())
    print('Platform:', platform.system())
    print('Processor:', platform.processor())
    print('System:', platform.system())
    print('')

if __name__ == '__main__':
    print_system_info()
    # Enable coverage early...
    enable_coverage = '--cov' in sys.argv
    if enable_coverage:
        os.makedirs('.coverage', exist_ok=True)
        sys.argv.remove('--cov')
        import coverage
        coverage.process_startup()
    returncode = 0
    # Iterate over list in reverse order to find the last --backend arg
    backend = Backend.ninja
    cross = False
    # FIXME: PLEASE convert to argparse
    for arg in reversed(sys.argv[1:]):
        if arg.startswith('--backend'):
            if arg.startswith('--backend=vs'):
                backend = Backend.vs
            elif arg == '--backend=xcode':
                backend = Backend.xcode
        if arg.startswith('--cross'):
            cross = True
            if arg == '--cross=mingw':
                cross = 'mingw'
            elif arg == '--cross=arm':
                cross = 'arm'
    # Running on a developer machine? Be nice!
    if not mesonlib.is_windows() and not mesonlib.is_haiku() and 'TRAVIS' not in os.environ:
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
    print(mlog.bold('Running unittests.').get_text(mlog.colorize_console))
    print()
    # Can't pass arguments to unit tests, so set the backend to use in the environment
    env = os.environ.copy()
    env['MESON_UNIT_TEST_BACKEND'] = backend.name
    with tempfile.TemporaryDirectory() as td:
        # Enable coverage on all subsequent processes.
        if enable_coverage:
            with open(os.path.join(td, 'usercustomize.py'), 'w') as f:
                f.write('import coverage\n'
                        'coverage.process_startup()\n')
            env['COVERAGE_PROCESS_START'] = '.coveragerc'
            env['PYTHONPATH'] = os.pathsep.join([td] + env.get('PYTHONPATH', []))
        if not cross:
            returncode += subprocess.call(mesonlib.python_command + ['run_meson_command_tests.py', '-v'], env=env)
            returncode += subprocess.call(mesonlib.python_command + ['run_unittests.py', '-v'], env=env)
            returncode += subprocess.call(mesonlib.python_command + ['run_project_tests.py'] + sys.argv[1:], env=env)
        else:
            cross_test_args = mesonlib.python_command + ['run_cross_test.py']
            if cross is True or cross == 'arm':
                print(mlog.bold('Running armhf cross tests.').get_text(mlog.colorize_console))
                print()
                returncode += subprocess.call(cross_test_args + ['cross/ubuntu-armhf.txt'], env=env)
            if cross is True or cross == 'mingw':
                print(mlog.bold('Running mingw-w64 64-bit cross tests.').get_text(mlog.colorize_console))
                print()
                returncode += subprocess.call(cross_test_args + ['cross/linux-mingw-w64-64bit.txt'], env=env)
    sys.exit(returncode)
