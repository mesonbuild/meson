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

import json
import re
import sys
import typing as T
from collections import defaultdict
from pathlib import Path

from . import mlog
from . import mesonlib
from . import coredata
from .mesonlib import MesonException
from mesonbuild.environment import detect_ninja
from mesonbuild.coredata import UserArrayOption

if T.TYPE_CHECKING:
    import argparse

def array_arg(value: str) -> T.List[str]:
    return UserArrayOption(None, value, allow_dups=True, user_input=True).value

def validate_builddir(builddir: Path) -> None:
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

def parse_introspect_data(builddir: Path) -> T.Dict[str, T.List[dict]]:
    """
    Converts a List of name-to-dict to a dict of name-to-dicts (since names are not unique)
    """
    path_to_intro = builddir / 'meson-info' / 'intro-targets.json'
    if not path_to_intro.exists():
        raise MesonException('`{}` is missing! Directory is not configured yet?'.format(path_to_intro.name))
    with path_to_intro.open() as f:
        schema = json.load(f)

    parsed_data = defaultdict(list) # type: T.Dict[str, T.List[dict]]
    for target in schema:
        parsed_data[target['name']] += [target]
    return parsed_data

class ParsedTargetName:
    full_name = ''
    name = ''
    type = ''
    path = ''

    def __init__(self, target: str):
        self.full_name = target
        split = target.rsplit(':', 1)
        if len(split) > 1:
            self.type = split[1]
            if not self._is_valid_type(self.type):
                raise MesonException('Can\'t invoke target `{}`: unknown target type: `{}`'.format(target, self.type))

        split = split[0].rsplit('/', 1)
        if len(split) > 1:
            self.path = split[0]
            self.name = split[1]
        else:
            self.name = split[0]

    @staticmethod
    def _is_valid_type(type: str) -> bool:
        # Ammend docs in Commands.md when editing this list
        allowed_types = {
            'executable',
            'static_library',
            'shared_library',
            'shared_module',
            'custom',
            'run',
            'jar',
        }
        return type in allowed_types

def get_target_from_intro_data(target: ParsedTargetName, builddir: Path, introspect_data: dict) -> dict:
    if target.name not in introspect_data:
        raise MesonException('Can\'t invoke target `{}`: target not found'.format(target.full_name))

    intro_targets = introspect_data[target.name]
    found_targets = []

    resolved_bdir = builddir.resolve()

    if not target.type and not target.path:
        found_targets = intro_targets
    else:
        for intro_target in intro_targets:
            if (intro_target['subproject'] or
                    (target.type and target.type != intro_target['type'].replace(' ', '_')) or
                    (target.path
                         and intro_target['filename'] != 'no_name'
                         and Path(target.path) != Path(intro_target['filename'][0]).relative_to(resolved_bdir).parent)):
                continue
            found_targets += [intro_target]

    if not found_targets:
        raise MesonException('Can\'t invoke target `{}`: target not found'.format(target.full_name))
    elif len(found_targets) > 1:
        raise MesonException('Can\'t invoke target `{}`: ambigious name. Add target type and/or path: `PATH/NAME:TYPE`'.format(target.full_name))

    return found_targets[0]

def generate_target_names_ninja(target: ParsedTargetName, builddir: Path, introspect_data: dict) -> T.List[str]:
    intro_target = get_target_from_intro_data(target, builddir, introspect_data)

    if intro_target['type'] == 'run':
        return [target.name]
    else:
        return [str(Path(out_file).relative_to(builddir.resolve())) for out_file in intro_target['filename']]

def get_parsed_args_ninja(options: 'argparse.Namespace', builddir: Path) -> T.List[str]:
    runner = detect_ninja()
    if runner is None:
        raise MesonException('Cannot find ninja.')
    mlog.log('Found runner:', runner)

    cmd = [runner, '-C', builddir.as_posix()]

    if options.targets:
        intro_data = parse_introspect_data(builddir)
        for t in options.targets:
            cmd.extend(generate_target_names_ninja(ParsedTargetName(t), builddir, intro_data))
    if options.clean:
        cmd.append('clean')

    # If the value is set to < 1 then don't set anything, which let's
    # ninja/samu decide what to do.
    if options.jobs > 0:
        cmd.extend(['-j', str(options.jobs)])
    if options.load_average > 0:
        cmd.extend(['-l', str(options.load_average)])

    if options.verbose:
        cmd.append('--verbose')

    cmd += options.ninja_args

    return cmd

def generate_target_name_vs(target: ParsedTargetName, builddir: Path, introspect_data: dict) -> str:
    intro_target = get_target_from_intro_data(target, builddir, introspect_data)

    assert intro_target['type'] != 'run', 'Should not reach here: `run` targets must be handle above'

    # Normalize project name
    # Source: https://docs.microsoft.com/en-us/visualstudio/msbuild/how-to-build-specific-targets-in-solutions-by-using-msbuild-exe
    target_name = re.sub('[\%\$\@\;\.\(\)\']', '_', intro_target['id'])
    rel_path = Path(intro_target['filename'][0]).relative_to(builddir.resolve()).parent
    if rel_path != '.':
        target_name = str(rel_path / target_name)
    return target_name

def get_parsed_args_vs(options: 'argparse.Namespace', builddir: Path) -> T.List[str]:
    slns = list(builddir.glob('*.sln'))
    assert len(slns) == 1, 'More than one solution in a project?'
    sln = slns[0]

    cmd = ['msbuild']

    if options.targets:
        intro_data = parse_introspect_data(builddir)
        has_run_target = any(map(
            lambda t:
                get_target_from_intro_data(ParsedTargetName(t), builddir, intro_data)['type'] == 'run',
            options.targets
        ))

        if has_run_target:
            # `run` target can't be used the same way as other targets on `vs` backend.
            # They are defined as disabled projects, which can't be invoked as `.sln`
            # target and have to be invoked directly as project instead.
            # Issue: https://github.com/microsoft/msbuild/issues/4772

            if len(options.targets) > 1:
                raise MesonException('Only one target may be specified when `run` target type is used on this backend.')
            intro_target = get_target_from_intro_data(ParsedTargetName(options.targets[0]), builddir, intro_data)
            proj_dir = Path(intro_target['filename'][0]).parent
            proj = proj_dir/'{}.vcxproj'.format(intro_target['id'])
            cmd += [str(proj.resolve())]
        else:
            cmd += [str(sln.resolve())]
            cmd.extend(['-target:{}'.format(generate_target_name_vs(ParsedTargetName(t), builddir, intro_data)) for t in options.targets])
    else:
        cmd += [str(sln.resolve())]

    if options.clean:
        cmd.extend(['-target:Clean'])

    # In msbuild `-maxCpuCount` with no number means "detect cpus", the default is `-maxCpuCount:1`
    if options.jobs > 0:
        cmd.append('-maxCpuCount:{}'.format(options.jobs))
    else:
        cmd.append('-maxCpuCount')

    if options.load_average:
        mlog.warning('Msbuild does not have a load-average switch, ignoring.')

    if not options.verbose:
        cmd.append('-verbosity:minimal')

    cmd += options.vs_args

    return cmd

def add_arguments(parser: 'argparse.ArgumentParser') -> None:
    """Add compile specific arguments."""
    parser.add_argument(
        'targets',
        metavar='TARGET',
        nargs='*',
        default=None,
        help='Targets to build. Target has the following format: [PATH_TO_TARGET/]TARGET_NAME[:TARGET_TYPE].')
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
        help='The system load average to try to maintain (if supported).'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show more verbose output.'
    )
    parser.add_argument(
        '--ninja-args',
        type=array_arg,
        default=[],
        help='Arguments to pass to `ninja` (applied only on `ninja` backend).'
    )
    parser.add_argument(
        '--vs-args',
        type=array_arg,
        default=[],
        help='Arguments to pass to `msbuild` (applied only on `vs` backend).'
    )

def run(options: 'argparse.Namespace') -> int:
    bdir = options.builddir  # type: Path
    validate_builddir(bdir.resolve())

    cmd = []  # type: T.List[str]

    if options.targets and options.clean:
        raise MesonException('`TARGET` and `--clean` can\'t be used simultaneously')

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
