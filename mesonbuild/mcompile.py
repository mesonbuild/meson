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

import os
import pathlib
import shutil
import sys
import typing as T

from . import mlog
from . import mesonlib
from .mesonlib import MesonException

if T.TYPE_CHECKING:
    import argparse


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
        type=pathlib.Path,
        required=True,
        default='.',
        help='The directory containing build files to be built.'
    )


def run(options: 'argparse.Namespace') -> int:
    bdir = options.builddir  # type: pathlib.Path
    if not bdir.exists():
        raise MesonException('Path to builddir {} does not exist!'.format(str(bdir.resolve())))
    if not bdir.is_dir():
        raise MesonException('builddir path should be a directory.')

    cmd = []  # type: T.List[str]
    runner = None  # type T.Optional[str]
    slns = list(bdir.glob('*.sln'))

    if (bdir / 'build.ninja').exists():
        runner = os.environ.get('NINJA')
        if not runner:
            if shutil.which('ninja'):
                runner = 'ninja'
            elif shutil.which('samu'):
                runner = 'samu'

        if runner is None:
            raise MesonException('Cannot find either ninja or samu.')

        cmd = [runner, '-C', bdir.as_posix()]

        # If the value is set to < 1 then don't set anything, which let's
        # ninja/samu decide what to do.
        if options.jobs > 0:
            cmd.extend(['-j', str(options.jobs)])
        if options.load_average > 0:
            cmd.extend(['-l', str(options.load_average)])
        if options.clean:
            cmd.append('clean')

    # TODO: with python 3.8 this could be `elif slns := bdir.glob('*.sln'):`
    elif slns:
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

    # TODO: xcode?
    else:
        raise MesonException(
            'Could not find any runner or backend for directory {}'.format(bdir.resolve().as_posix()))

    mlog.log('Found runner:', runner)

    p, *_ = mesonlib.Popen_safe(cmd, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer)

    return p.returncode
