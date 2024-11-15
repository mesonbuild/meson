from __future__ import annotations

import argparse
import typing as T

from pathlib import Path
from . import build
from .mesonlib import setup_vsenv, MesonException
from .options import OptionKey
from .mcompile import compile_single_executable
from .mdevenv import run_cmd


# Note: when adding arguments, please also add them to the completion
# scripts in $MESONSRC/data/shell-completions/
def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('-C', dest='builddir', type=Path, default='.',
                        help='Path to build directory')
    parser.add_argument('--bin', default=None,
                        help='Executable target to build and run')
    parser.add_argument('arguments', nargs=argparse.REMAINDER,
                        help='Arguments to pass to the executable')


def run(options: argparse.Namespace) -> int:
    buildfile = Path(options.builddir, 'meson-private', 'build.dat')
    if not buildfile.is_file():
        raise MesonException(f'Directory {options.builddir!r} does not seem to be a Meson build directory.')
    b = build.load(options.builddir)

    need_vsenv = T.cast('bool', b.environment.coredata.get_option(OptionKey('vsenv')))
    setup_vsenv(need_vsenv)

    path, returncode = compile_single_executable(b.environment, options.bin)
    if returncode != 0:
        return returncode

    cmd = [path] + options.arguments
    return run_cmd(b, cmd)
