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
from mesonbuild import mesonlib
from mesonbuild import mesonmain
from mesonbuild.environment import detect_ninja
from io import StringIO
from enum import Enum
from glob import glob

Backend = Enum('Backend', 'ninja vs xcode')

if mesonlib.is_windows() or mesonlib.is_cygwin():
    exe_suffix = '.exe'
else:
    exe_suffix = ''

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
        cmd = [detect_ninja('1.6'), '-w', 'dupbuild=err']
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
    # This is needed to increase the difference between build.ninja's
    # timestamp and the timestamp of whatever you changed due to a Ninja
    # bug: https://github.com/ninja-build/ninja/issues/371
    if backend is Backend.ninja:
        time.sleep(1)

def get_fake_options(prefix):
    import argparse
    opts = argparse.Namespace()
    opts.cross_file = None
    opts.wrap_mode = None
    opts.prefix = prefix
    return opts

def should_run_linux_cross_tests():
    return shutil.which('arm-linux-gnueabihf-gcc-6') and not platform.machine().startswith('arm')

def run_configure_inprocess(commandlist):
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    old_stderr = sys.stderr
    sys.stderr = mystderr = StringIO()
    try:
        returncode = mesonmain.run(commandlist[0], commandlist[1:])
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return returncode, mystdout.getvalue(), mystderr.getvalue()

class FakeEnvironment(object):
    def __init__(self):
        self.cross_info = None
        self.coredata = lambda: None
        self.coredata.compilers = {}

    def is_cross_build(self):
        return False

if __name__ == '__main__':
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
    for arg in reversed(sys.argv[1:]):
        if arg.startswith('--backend'):
            if arg.startswith('--backend=vs'):
                backend = Backend.vs
            elif arg == '--backend=xcode':
                backend = Backend.xcode
            break
    # Running on a developer machine? Be nice!
    if not mesonlib.is_windows() and 'TRAVIS' not in os.environ:
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
    print('Running unittests.\n')
    units = ['InternalTests', 'AllPlatformTests', 'FailureTests']
    if mesonlib.is_linux():
        units += ['LinuxlikeTests']
        if should_run_linux_cross_tests():
            units += ['LinuxArmCrossCompileTests']
    elif mesonlib.is_windows():
        units += ['WindowsTests']
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

        returncode += subprocess.call([sys.executable, 'run_unittests.py', '-v'] + units, env=env)
        # Ubuntu packages do not have a binary without -6 suffix.
        if should_run_linux_cross_tests():
            print('Running cross compilation tests.\n')
            returncode += subprocess.call([sys.executable, 'run_cross_test.py', 'cross/ubuntu-armhf.txt'], env=env)
        returncode += subprocess.call([sys.executable, 'run_project_tests.py'] + sys.argv[1:], env=env)
    sys.exit(returncode)
