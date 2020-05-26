# Copyright 2020 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Entrypoint script for backend agnostic compile."""

import sys
import typing as T
from pathlib import Path

from . import mlog
from . import mesonlib
from . import coredata
from .mesonlib import MesonException
from mesonbuild.environment import detect_ninja

if T.TYPE_CHECKING:
    import argparse
    
def validate_builddir(builddir: Path):
    if not (builddir / 'meson-private' / 'coredata.dat' ).is_file():
        raise MesonException('Current directory is not a meson build directory: `{}`.\n'
                             'Please specify a valid build dir or change the working directory to it.\n'
                             'It is also possible that the build directory was generated with an old\n'
                             'meson version. Please regenerate it in this case.'.format(builddir))

def get_backend_from_coredata(builddir: Path) -> str:
    """
    Gets `backend` option value from coredata
    """
    return coredata.load(str(builddir)).get_builtin_option('backend')

def get_parsed_args_ninja(options: 'argparse.Namespace', builddir: Path):
    runner = detect_ninja()
    if runner is None:
        raise MesonException('Cannot find ninja.')
    mlog.log('Found runner:', runner)

    cmd = [runner, '-C', builddir.as_posix()]

    # If the value is set to < 1 then don't set anything, which let's
    # ninja/samu decide what to do.
    if options.jobs > 0:
        cmd.extend(['-j', str(options.jobs)])
    if options.load_average > 0:
        cmd.extend(['-l', str(options.load_average)])
    if options.clean:
        cmd.append('clean')
    
    return cmd

def get_parsed_args_vs(options: 'argparse.Namespace', builddir: Path):
    slns = list(builddir.glob('*.sln'))
    assert len(slns) == 1, 'More than one solution in a project?'
    
    sln = slns[0]
    cmd = ['msbuild', str(sln.resolve())]
    
    # In msbuild `-m` with no number means "detect cpus", the default is `-m1`
    if options.jobs > 0:
        cmd.append('-m{}'.format(options.jobs))
    else:
        cmd.append('-m')
    
    if options.load_average:
        mlog.warning('Msbuild does not have a load-average switch, ignoring.')
    if options.clean:
        cmd.extend(['/t:Clean'])
    
    return cmd
    
def add_arguments(parser: 'argparse.ArgumentParser') -> None:
    """Add compile specific arguments."""
    parser.add_argument(
        '-j', '--jobs',
        action='store',
        default=0,
        type=int,
        help='The number of worker jobs to run (if supported). If the value is less than 1 the build program will guess.'
    )
    parser.add_argument(
        '-l', '--load-average',
        action='store',
        default=0,
        type=int,
        help='The system load average to try to maintain (if supported)'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean the build directory.'
    )
    parser.add_argument(
        '-C',
        action='store',
        dest='builddir',
        type=Path,
        default='.',
        help='The directory containing build files to be built.'
    )


def run(options: 'argparse.Namespace') -> int:
    bdir = options.builddir  # type: Path
    validate_builddir(bdir.resolve())

    cmd = []  # type: T.List[str]

    backend = get_backend_from_coredata(bdir)
    if backend == 'ninja':
        cmd = get_parsed_args_ninja(options, bdir)
    elif backend.startswith('vs'):
        cmd = get_parsed_args_vs(options, bdir)
    else:
        # TODO: xcode?
        raise MesonException(
            'Backend `{}` is not yet supported by `compile`. Use generated project files directly instead.'.format(backend))

    p, *_ = mesonlib.Popen_safe(cmd, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer)

    return p.returncode
