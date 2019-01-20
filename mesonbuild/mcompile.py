# Copyright 2016-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# A tool to build meson targets backend agnostic.
import argparse
from glob import glob
from . import coredata
from .environment import detect_ninja
import os
import subprocess

from enum import Enum

Backend = Enum('Backend', 'ninja vs xcode')

def add_arguments(parser):
    parser.add_argument('builddir', nargs='?', default='.')
    parser.add_argument('-t', '--targets', nargs='*', default=['all'],
                        help='Targets to build. Can include subdirectories.\n' +
                        "If omitted, the 'all' target gets built.\n" +
                        "Use 'clean' to clean the build directory.")

def guess_backend(backend):
    # Set backend arguments for Meson
    if backend.startswith('vs'):
        backend_flags = ['--backend=' + backend]
        backend = Backend.vs
    elif backend == 'xcode':
        backend_flags = ['--backend=xcode']
        backend = Backend.xcode
    elif backend == 'ninja':
        backend_flags = ['--backend=ninja']
        backend = Backend.ninja
    else:
        raise RuntimeError('Unknown backend: {!r}'.format(backend))
    return (backend, backend_flags)

def get_backend_args_for_dir(backend, builddir):
    '''
    Visual Studio backend needs to be given the solution to build
    '''
    if backend is Backend.vs:
        sln_name = glob(os.path.join(builddir, '*.sln'))[0]
        return [os.path.split(sln_name)[-1]]
    return []

def find_vcxproj_with_target(builddir, target):
    import re
    subdir, target = os.path.split(target)
    t, ext = os.path.splitext(target)
    if ext:
        p = r'<TargetName>{}</TargetName>\s*<TargetExt>\{}</TargetExt>'.format(t, ext)
    else:
        p = r'<TargetName>{}</TargetName>'.format(t)
    for f in glob(os.path.join(builddir, subdir, '*.vcxproj')):
        with open(f, 'r', encoding='utf-8') as o:
            if re.search(p, o.read(), flags=re.MULTILINE):
                return os.path.relpath(f, start=builddir)
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

def get_backend_commands(backend, ci=True, debug=False):
    install_cmd = []
    uninstall_cmd = []
    if backend is Backend.vs:
        cmd = ['msbuild']
        clean_cmd = cmd + ['/target:Clean']
        test_cmd = cmd + ['RUN_TESTS.vcxproj']
    elif backend is Backend.xcode:
        cmd = ['xcodebuild']
        # In Xcode9 new build system's clean command fails when using a custom build directory.
        # Maybe use it when CI uses Xcode10 we can remove '-UseNewBuildSystem=FALSE'
        clean_cmd = cmd + ['-alltargets', 'clean', '-UseNewBuildSystem=FALSE']
        test_cmd = cmd + ['-target', 'RUN_TESTS']
    elif backend is Backend.ninja:
        ninja_ver = '0.0'
        cmd = []
        if ci:
            # We need at least 1.6 because of -w dupbuild=err
            ninja_ver = '1.6'
            cmd = ['-w', 'dupbuild=err', '-d', 'explain']
        cmd = [detect_ninja(ninja_ver)] + cmd
        if cmd[0] is None:
            raise RuntimeError('Could not find Ninja v{} or newer'.format(ninja_ver))
        if debug:
            cmd += ['-v']
        clean_cmd = cmd + ['clean']
        test_cmd = cmd + ['test', 'benchmark']
        install_cmd = cmd + ['install']
        uninstall_cmd = cmd + ['uninstall']
    else:
        raise AssertionError('Unknown backend: {!r}'.format(backend))
    return cmd, clean_cmd, test_cmd, install_cmd, uninstall_cmd

def run(options):
    build_dir = os.path.abspath(os.path.realpath(options.builddir))
    backend, _ = guess_backend(coredata.load(build_dir).get_builtin_option('backend'))
    build_command, clean_cmd, *_ = get_backend_commands(backend, ci=False)

    failed = 0
    for target in options.targets:
        cmd = build_command
        if target == 'all':
            target = None
        elif target == 'clean':
            target = None
            cmd = clean_cmd
        args = get_builddir_target_args(backend, build_dir, target)
        failed += subprocess.run(cmd + args, cwd=build_dir).returncode
    return failed

def run_with_args(args):
    parser = argparse.ArgumentParser(prog='meson compile')
    add_arguments(parser)
    options = parser.parse_args(args)
    return run(options)
