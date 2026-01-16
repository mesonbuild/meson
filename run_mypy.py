#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

from pathlib import Path
import argparse
import concurrent.futures
import os
import subprocess
import sys
import typing as T

from mesonbuild.mesonlib import version_compare

modules = [
    # fully typed submodules
    'mesonbuild/ast/',
    'mesonbuild/cargo/',
    'mesonbuild/cmake/',
    'mesonbuild/compilers/',
    'mesonbuild/dependencies/',
    'mesonbuild/interpreter/primitives/',
    'mesonbuild/interpreterbase/',
    'mesonbuild/linkers/',
    'mesonbuild/scripts/',
    'mesonbuild/templates/',
    'mesonbuild/utils/',
    'mesonbuild/wrap/',

    # specific files
    'mesonbuild/arglist.py',
    'mesonbuild/backend/backends.py',
    'mesonbuild/backend/nonebackend.py',
    'mesonbuild/cmdline.py',
    'mesonbuild/coredata.py',
    'mesonbuild/depfile.py',
    'mesonbuild/envconfig.py',
    'mesonbuild/environment.py',
    'mesonbuild/interpreter/compiler.py',
    'mesonbuild/interpreter/dependencyfallbacks.py',
    'mesonbuild/interpreter/mesonmain.py',
    'mesonbuild/interpreter/interpreterobjects.py',
    'mesonbuild/interpreter/type_checking.py',
    'mesonbuild/machinefile.py',
    'mesonbuild/mesondata.py',
    'mesonbuild/mcompile.py',
    'mesonbuild/mdevenv.py',
    'mesonbuild/mconf.py',
    'mesonbuild/mdist.py',
    'mesonbuild/mformat.py',
    'mesonbuild/minit.py',
    'mesonbuild/minstall.py',
    'mesonbuild/mintro.py',
    'mesonbuild/mlog.py',
    'mesonbuild/msubprojects.py',
    'mesonbuild/modules/__init__.py',
    'mesonbuild/modules/cmake.py',
    'mesonbuild/modules/codegen.py',
    'mesonbuild/modules/cuda.py',
    'mesonbuild/modules/dlang.py',
    'mesonbuild/modules/external_project.py',
    'mesonbuild/modules/fs.py',
    'mesonbuild/modules/gnome.py',
    'mesonbuild/modules/i18n.py',
    'mesonbuild/modules/icestorm.py',
    'mesonbuild/modules/java.py',
    'mesonbuild/modules/keyval.py',
    'mesonbuild/modules/modtest.py',
    'mesonbuild/modules/pkgconfig.py',
    'mesonbuild/modules/_qt.py',
    'mesonbuild/modules/qt4.py',
    'mesonbuild/modules/qt5.py',
    'mesonbuild/modules/qt6.py',
    'mesonbuild/modules/rust.py',
    'mesonbuild/modules/simd.py',
    'mesonbuild/modules/snippets.py',
    'mesonbuild/modules/sourceset.py',
    'mesonbuild/modules/wayland.py',
    'mesonbuild/modules/windows.py',
    'mesonbuild/mparser.py',
    'mesonbuild/msetup.py',
    'mesonbuild/mtest.py',
    'mesonbuild/optinterpreter.py',
    'mesonbuild/options.py',
    'mesonbuild/programs.py',
    'mesonbuild/rewriter.py',
    'mesonbuild/tooldetect.py',
]
additional = [
    'run_mypy.py',
    'run_project_tests.py',
    'run_single_test.py',
    'tools',
    'docs/genrefman.py',
    'docs/refman',
    'unittests/helpers.py',
]

def check_mypy() -> None:
    try:
        import mypy
    except ImportError:
        print('Failed import mypy')
        sys.exit(1)
    from mypy.version import __version__ as mypy_version
    if not version_compare(mypy_version, '>=0.812'):
        print('mypy >=0.812 is required, older versions report spurious errors')
        sys.exit(1)

def main() -> int:
    root = Path(__file__).absolute().parent

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('files', nargs='*')
    parser.add_argument('--mypy', help='path to mypy executable')
    parser.add_argument('-q', '--quiet', action='store_true', help='do not print informational messages')
    parser.add_argument('-p', '--pretty', action='store_true', help='pretty print mypy errors')
    parser.add_argument('-C', '--clear', action='store_true', help='clear the terminal before running mypy')
    parser.add_argument('--allver', action='store_true', help='Check all supported versions of python')

    opts, args = parser.parse_known_args()
    if not opts.mypy:
        check_mypy()

    if opts.pretty:
        args.append('--pretty')

    if opts.clear:
        print('\x1bc', end='', flush=True)

    to_check = [] # type: T.List[str]
    additional_to_check = [] # type: T.List[str]
    if opts.files:
        for f in opts.files:
            if f in modules:
                to_check.append(f)
            elif any(f.startswith(i) for i in modules):
                to_check.append(f)
            elif f in additional:
                additional_to_check.append(f)
            elif any(f.startswith(i) for i in additional):
                additional_to_check.append(f)
            else:
                if not opts.quiet:
                    print(f'skipping {f!r} because it is not yet typed')
    else:
        to_check.extend(modules)
        additional_to_check.extend(additional)

    if not to_check:
        if not opts.quiet:
            print('nothing to do...')
        return 0

    command = [opts.mypy] if opts.mypy else [sys.executable, '-m', 'mypy']
    if not opts.quiet:
        print('Running mypy (this can take some time) ...')

    if opts.allver:
        versions = ['default'] + [f'3.{minor}' for minor in range(7, sys.version_info[1])]
    else:
        versions = ['default']

    def run_mypy_version(version: str) -> T.Tuple[int, str, str]:
        if version == 'default':
            cmd = command + args + to_check + additional_to_check
        else:
            cmd = command + args + to_check + [f'--python-version={version}']

        env = os.environ.copy()
        if sys.stdout.isatty():
            env['MYPY_FORCE_COLOR'] = "1"

        result = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            env=env
        )

        return (result.returncode, version, result.stdout + result.stderr)

    if not opts.quiet and opts.allver:
        for version in versions:
            print(f'Starting mypy check for python version: {version}')

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_mypy_version, version) for version in versions]

        retcode = 0
        for future in concurrent.futures.as_completed(futures):
            exit_code, version, output = future.result()

            if not opts.allver:
                print(output, end='')
            else:
                if not opts.quiet:
                    print(f'Results for python version: {version} (exit code: {exit_code})')
                print(output, end='')

            retcode = max(retcode, exit_code)

    return retcode

if __name__ == '__main__':
    sys.exit(main())
