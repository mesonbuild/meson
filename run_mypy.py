#!/usr/bin/env python3

from collections import UserDict
from pathlib import Path
import argparse
import subprocess
import sys
import typing as T

from mesonbuild.mesonlib import version_compare

modules = {
    # fully typed submodules
    # 'mesonbuild/ast/': None,
    'mesonbuild/cargo/': None,
    'mesonbuild/cmake/': None,
    'mesonbuild/compilers/': None,
    'mesonbuild/dependencies/': None,
    'mesonbuild/interpreter/primitives/': None,
    'mesonbuild/interpreterbase/': None,
    'mesonbuild/linkers/': None,
    'mesonbuild/scripts/': None,
    'mesonbuild/templates/': None,
    'mesonbuild/wrap/': None,

    # specific files
    'mesonbuild/arglist.py': None,
    'mesonbuild/backend/backends.py': None,
    # 'mesonbuild/coredata.py': None,
    'mesonbuild/depfile.py': None,
    'mesonbuild/envconfig.py': None,
    'mesonbuild/interpreter/compiler.py': None,
    'mesonbuild/interpreter/mesonmain.py': None,
    'mesonbuild/interpreter/interpreterobjects.py': None,
    'mesonbuild/interpreter/type_checking.py': None,
    'mesonbuild/mcompile.py': None,
    'mesonbuild/mdevenv.py': None,
    'mesonbuild/utils/core.py': None,
    'mesonbuild/utils/platform.py': None,
    'mesonbuild/utils/universal.py': None,
    'mesonbuild/mconf.py': None,
    'mesonbuild/mdist.py': None,
    'mesonbuild/minit.py': None,
    'mesonbuild/minstall.py': 'linux',
    'mesonbuild/mintro.py': None,
    'mesonbuild/mlog.py': 'linux',
    'mesonbuild/msubprojects.py': None,
    'mesonbuild/modules/__init__.py': None,
    'mesonbuild/modules/external_project.py': None,
    'mesonbuild/modules/fs.py': None,
    'mesonbuild/modules/gnome.py': None,
    'mesonbuild/modules/i18n.py': None,
    'mesonbuild/modules/icestorm.py': None,
    'mesonbuild/modules/java.py': None,
    'mesonbuild/modules/keyval.py': None,
    'mesonbuild/modules/modtest.py': None,
    'mesonbuild/modules/pkgconfig.py': None,
    'mesonbuild/modules/qt.py': None,
    'mesonbuild/modules/qt4.py': None,
    'mesonbuild/modules/qt5.py': None,
    'mesonbuild/modules/qt6.py': None,
    'mesonbuild/modules/rust.py': None,
    'mesonbuild/modules/sourceset.py': None,
    'mesonbuild/modules/wayland.py': None,
    'mesonbuild/modules/windows.py': None,
    'mesonbuild/mparser.py': None,
    'mesonbuild/msetup.py': None,
    'mesonbuild/mtest.py': 'linux',
    'mesonbuild/optinterpreter.py': None,
    'mesonbuild/programs.py': None,
    'mesonbuild/utils/posix.py': 'linux',
    'mesonbuild/utils/win32.py': 'win32',

    'run_mypy.py': None,
    'run_project_tests.py': None,
    'run_single_test.py': None,
    'tools': None,
    'docs/genrefman.py': None,
    'docs/refman': None,
}

def check_mypy() -> None:
    try:
        import mypy  # noqa
    except ImportError:
        print('Failed import mypy')
        sys.exit(1)
    from mypy.version import __version__ as mypy_version
    if not version_compare(mypy_version, '>=0.812'):
        print('mypy >=0.812 is required, older versions report spurious errors')
        sys.exit(1)

class PlatformDict(UserDict):

    def __init__(self, platform: T.Optional[str] = None):
        super().__init__()
        self.platform = platform

    def append(self, module: str, platform: T.Optional[str]) -> None:
        p = self.platform or platform or sys.platform
        d = self.data.setdefault(p, [])
        d.append(module)

    def extend(self, modules: T.Dict[str, T.Optional[str]], platform: T.Optional[str]) -> None:
        for m, t in modules.items():
            self.append(m, platform or t)

    def run_mypy(self, command: T.List[str], python_minor_version: T.Optional[int], quiet: bool, root: Path) -> int:
        retcode = 0

        if python_minor_version is not None and not quiet:
            print(f'Checking mypy with python version: 3.{python_minor_version}')
        for platform, modules_to_check in self.data.items():
            if not quiet:
                print(f'{platform}:', end=' ')
            parg = [f'--platform={platform}']
            if python_minor_version is not None:
                parg.append(f'--python-version=3.{python_minor_version}')
            retcode = subprocess.run(command + parg + modules_to_check, cwd=root).returncode
            if retcode != 0:
                break
        return retcode


def main() -> int:
    check_mypy()

    root = Path(__file__).absolute().parent

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('files', nargs='*')
    parser.add_argument('--mypy', help='path to mypy executable')
    parser.add_argument('-q', '--quiet', action='store_true', help='do not print informational messages')
    parser.add_argument('-p', '--pretty', action='store_true', help='pretty print mypy errors')
    parser.add_argument('-C', '--clear', action='store_true', help='clear the terminal before running mypy')
    parser.add_argument('--allver', action='store_true', help='Check all supported versions of python')
    parser.add_argument('--platform', help='Type check special-cased code for the given OS platform')

    opts, args = parser.parse_known_args()
    if opts.pretty:
        args.append('--pretty')

    if opts.clear:
        print('\x1bc', end='', flush=True)

    to_check = PlatformDict()
    if opts.files:
        for f in opts.files:
            if sys.platform == 'win32':
                f = f.replace('\\', '/')
            if f in modules:
                to_check.append(f, opts.platform or modules[f])
            else:
                for i, p in modules.items():
                    if f.startswith(i):
                        to_check.append(f, opts.platform or p)
                        break
                else:
                    if not opts.quiet:
                        print(f'skipping {f!r} because it is not yet typed')
    else:
        to_check.extend(modules, opts.platform)

    if to_check:
        command = [opts.mypy] if opts.mypy else [sys.executable, '-m', 'mypy']
        if not opts.quiet:
            print('Running mypy (this can take some time) ...')

        retcode = to_check.run_mypy(command + args, None, opts.quiet, root)

        if opts.allver and retcode == 0:
            for minor in range(7, sys.version_info[1]):
                retcode = to_check.run_mypy(command + args, minor, opts.quiet, root)
                if retcode != 0:
                    break
        return retcode
    else:
        if not opts.quiet:
            print('nothing to do...')
        return 0

if __name__ == '__main__':
    sys.exit(main())
