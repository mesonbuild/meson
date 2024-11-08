# SPDX-License-Identifier: Apache-2.0
# Copyright 2020 The Meson development team

from __future__ import annotations

"""Entrypoint script for backend agnostic compile."""

import os
import json
import re
import sys
import shutil
import typing as T
from collections import defaultdict
from pathlib import Path
from functools import lru_cache

from . import mlog
from . import mesonlib
from .options import OptionKey
from .mesonlib import MesonException, RealPathAction, join_args, listify_array_value, setup_vsenv
from mesonbuild.environment import detect_ninja
from mesonbuild import build

if T.TYPE_CHECKING:
    import argparse
    from .environment import Environment
    IntroTarget = T.Dict[str, T.Any]


def array_arg(value: str) -> T.List[str]:
    return listify_array_value(value)

def validate_builddir(builddir: Path) -> None:
    if not (builddir / 'meson-private' / 'coredata.dat').is_file():
        raise MesonException(f'Current directory is not a meson build directory: `{builddir}`.\n'
                             'Please specify a valid build dir or change the working directory to it.\n'
                             'It is also possible that the build directory was generated with an old\n'
                             'meson version. Please regenerate it in this case.')

@lru_cache(maxsize=None)
def parse_introspect_data(builddir: Path) -> T.Dict[str, T.List[IntroTarget]]:
    """
    Converts a List of name-to-dict to a dict of name-to-dicts (since names are not unique)
    """
    path_to_intro = builddir / 'meson-info' / 'intro-targets.json'
    if not path_to_intro.exists():
        raise MesonException(f'`{path_to_intro.name}` is missing! Directory is not configured yet?')
    with path_to_intro.open(encoding='utf-8') as f:
        schema = json.load(f)

    parsed_data: T.Dict[str, T.List[dict]] = defaultdict(list)
    for target in schema:
        parsed_data[target['name']] += [target]
    return parsed_data

class ParsedTargetName:
    full_name = ''
    base_name = ''
    name = ''
    type = ''
    path = ''
    suffix = ''

    def __init__(self, target: str):
        self.full_name = target
        split = target.rsplit(':', 1)
        if len(split) > 1:
            self.type = split[1]
            if not self._is_valid_type(self.type):
                raise MesonException(f'Can\'t invoke target `{target}`: unknown target type: `{self.type}`')

        split = split[0].rsplit('/', 1)
        if len(split) > 1:
            self.path = split[0]
            self.name = split[1]
        else:
            self.name = split[0]

        split = self.name.rsplit('.', 1)
        if len(split) > 1:
            self.base_name = split[0]
            self.suffix = split[1]
        else:
            self.base_name = split[0]

    @staticmethod
    def _is_valid_type(type: str) -> bool:
        # Amend docs in Commands.md when editing this list
        allowed_types = {
            'executable',
            'static_library',
            'shared_library',
            'shared_module',
            'custom',
            'alias',
            'run',
            'jar',
        }
        return type in allowed_types

def get_suggestions(builddir: Path, found_targets: T.List[IntroTarget]) -> str:
    resolved_bdir = builddir.resolve()
    suggestions: T.List[str] = []
    for i in found_targets:
        i_name = i['name']
        split = i['id'].rsplit('@', 1)
        if len(split) > 1:
            split = split[0].split('@@', 1)
            if len(split) > 1:
                i_name = split[1]
            else:
                i_name = split[0]
        p = Path(i['filename'][0]).relative_to(resolved_bdir).parent / i_name
        t = i['type'].replace(' ', '_')
        suggestions.append(f'- ./{p}:{t}')
    return '\n'.join(suggestions)

def get_target_from_intro_data(full_name: str, builddir: Path, introspect_data: IntroTarget) -> IntroTarget:
    target = ParsedTargetName(full_name)
    if target.name not in introspect_data and target.base_name not in introspect_data:
        raise MesonException(f'Can\'t invoke target `{target.full_name}`: target not found')

    intro_targets = introspect_data[target.name]
    # if target.name doesn't find anything, try just the base name
    if not intro_targets:
        intro_targets = introspect_data[target.base_name]
    found_targets: T.List[IntroTarget] = []

    resolved_bdir = builddir.resolve()

    if not target.type and not target.path and not target.suffix:
        found_targets = intro_targets
    else:
        for intro_target in intro_targets:
            # Parse out the name from the id if needed
            intro_target_name = intro_target['name']
            split = intro_target['id'].rsplit('@', 1)
            if len(split) > 1:
                split = split[0].split('@@', 1)
                if len(split) > 1:
                    intro_target_name = split[1]
                else:
                    intro_target_name = split[0]
            if ((target.type and target.type != intro_target['type'].replace(' ', '_')) or
                (target.name != intro_target_name) or
                (target.path and intro_target['filename'] != 'no_name' and
                 Path(target.path) != Path(intro_target['filename'][0]).relative_to(resolved_bdir).parent)):
                continue
            found_targets.append(intro_target)

    if not found_targets:
        raise MesonException(f'Can\'t invoke target `{target.full_name}`: target not found')
    elif len(found_targets) > 1:
        suggestions_str = get_suggestions(builddir, found_targets)
        raise MesonException(f'Can\'t invoke target `{target.full_name}`: ambiguous name.'
                             f' Add target type and/or path:\n{suggestions_str}')
    return found_targets[0]

def generate_target_names_ninja(intro_target: IntroTarget, builddir: Path) -> T.List[str]:
    if intro_target['type'] in {'alias', 'run'}:
        return [intro_target["name"]]
    else:
        return [str(Path(out_file).relative_to(builddir.resolve())) for out_file in intro_target['filename']]

def get_parsed_args_ninja(builddir: Path, targets: T.List[IntroTarget],
                          jobs: int = 0, load_average: int = 0,
                          verbose: bool = False, clean: bool = False,
                          ninja_args: T.Optional[T.List[str]] = None) -> T.Tuple[T.List[str], T.Optional[T.Dict[str, str]]]:
    runner = detect_ninja()
    if runner is None:
        raise MesonException('Cannot find ninja.')

    cmd = runner
    if not builddir.samefile('.'):
        cmd.extend(['-C', builddir.as_posix()])

    # If the value is set to < 1 then don't set anything, which let's
    # ninja/samu decide what to do.
    if jobs > 0:
        cmd.extend(['-j', str(jobs)])
    if load_average > 0:
        cmd.extend(['-l', str(load_average)])

    if verbose:
        cmd.append('-v')

    cmd += ninja_args or []

    # operands must be processed after options/option-arguments
    for t in targets:
        cmd.extend(generate_target_names_ninja(t, builddir))
    if clean:
        cmd.append('clean')

    return cmd, None

def generate_target_name_vs(intro_target: IntroTarget, builddir: Path) -> str:
    assert intro_target['type'] not in {'alias', 'run'}, 'Should not reach here: `run` targets must be handle above'

    # Normalize project name
    # Source: https://docs.microsoft.com/en-us/visualstudio/msbuild/how-to-build-specific-targets-in-solutions-by-using-msbuild-exe
    target_name = re.sub(r"[\%\$\@\;\.\(\)']", '_', intro_target['id'])
    rel_path = Path(intro_target['filename'][0]).relative_to(builddir.resolve()).parent
    if rel_path != Path('.'):
        target_name = str(rel_path / target_name)
    return target_name

def get_parsed_args_vs(builddir: Path, targets: T.List[IntroTarget],
                       jobs: int = 0, load_average: int = 0,
                       verbose: bool = False, clean: bool = False,
                       vs_args: T.Optional[T.List[str]] = None) -> T.Tuple[T.List[str], T.Optional[T.Dict[str, str]]]:
    slns = list(builddir.glob('*.sln'))
    assert len(slns) == 1, 'More than one solution in a project?'
    sln = slns[0]

    cmd = ['msbuild']

    if targets:
        has_run_target = any(t['type'] in {'alias', 'run'} for t in targets)
        if has_run_target:
            # `run` target can't be used the same way as other targets on `vs` backend.
            # They are defined as disabled projects, which can't be invoked as `.sln`
            # target and have to be invoked directly as project instead.
            # Issue: https://github.com/microsoft/msbuild/issues/4772

            if len(targets) > 1:
                raise MesonException('Only one target may be specified when `run` target type is used on this backend.')
            intro_target = targets[0]
            proj_dir = Path(intro_target['filename'][0]).parent
            proj = proj_dir/'{}.vcxproj'.format(intro_target['id'])
            cmd += [str(proj.resolve())]
        else:
            cmd += [str(sln.resolve())]
            cmd.extend(['-target:{}'.format(generate_target_name_vs(t, builddir)) for t in targets])
    else:
        cmd += [str(sln.resolve())]

    if clean:
        cmd.extend(['-target:Clean'])

    # In msbuild `-maxCpuCount` with no number means "detect cpus", the default is `-maxCpuCount:1`
    if jobs > 0:
        cmd.append(f'-maxCpuCount:{jobs}')
    else:
        cmd.append('-maxCpuCount')

    if load_average:
        mlog.warning('Msbuild does not have a load-average switch, ignoring.')

    if not verbose:
        cmd.append('-verbosity:minimal')

    cmd += vs_args

    # Remove platform from env if set so that msbuild does not
    # pick x86 platform when solution platform is Win32
    env = os.environ.copy()
    env.pop('PLATFORM', None)

    return cmd, env

def get_parsed_args_xcode(builddir: Path, targets: T.List[IntroTarget],
                          jobs: int = 0, load_average: int = 0,
                          verbose: bool = False, clean: bool = False,
                          xcode_args: T.Optional[T.List[str]] = None) -> T.Tuple[T.List[str], T.Optional[T.Dict[str, str]]]:
    runner = 'xcodebuild'
    if not shutil.which(runner):
        raise MesonException('Cannot find xcodebuild, did you install XCode?')

    # No argument to switch directory
    os.chdir(str(builddir))

    cmd = [runner, '-parallelizeTargets']

    if targets:
        for t in targets:
            # FIXME: How does it work to disambiguate?
            cmd += ['-target', t['name']]

    if clean:
        if targets:
            cmd += ['clean']
        else:
            cmd += ['-alltargets', 'clean']
        # Otherwise xcodebuild tries to delete the builddir and fails
        cmd += ['-UseNewBuildSystem=FALSE']

    if jobs > 0:
        cmd.extend(['-jobs', str(jobs)])

    if load_average > 0:
        mlog.warning('xcodebuild does not have a load-average switch, ignoring')

    if verbose:
        # xcodebuild is already quite verbose, and -quiet doesn't print any
        # status messages
        pass

    cmd += xcode_args
    return cmd, None

# Note: when adding arguments, please also add them to the completion
# scripts in $MESONSRC/data/shell-completions/
def add_arguments(parser: 'argparse.ArgumentParser') -> None:
    """Add compile specific arguments."""
    parser.add_argument(
        'targets',
        metavar='TARGET',
        nargs='*',
        default=None,
        help='Targets to build. Target has the following format: [PATH_TO_TARGET/]TARGET_NAME.TARGET_SUFFIX[:TARGET_TYPE].')
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean the build directory.'
    )
    parser.add_argument('-C', dest='wd', action=RealPathAction,
                        help='directory to cd into before running')

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
        type=float,
        help='The system load average to try to maintain (if supported).'
    )
    parser.add_argument(
        '-v', '--verbose',
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
    parser.add_argument(
        '--xcode-args',
        type=array_arg,
        default=[],
        help='Arguments to pass to `xcodebuild` (applied only on `xcode` backend).'
    )

def run_compile(environment: Environment, targets: T.List[IntroTarget],
                jobs: int = 0, load_average: int = 0, verbose: bool = False,
                clean: bool = False, ninja_args: T.Optional[T.List[str]] = None,
                vs_args: T.Optional[T.List[str]] = None,
                xcode_args: T.Optional[T.List[str]] = None) -> int:
    bdir = Path(environment.build_dir)

    backend = environment.coredata.get_option(OptionKey('backend'))
    assert isinstance(backend, str)

    cmd: T.List[str] = []
    env: T.Optional[T.Dict[str, str]] = None
    if backend == 'ninja':
        cmd, env = get_parsed_args_ninja(bdir, targets, jobs, load_average, verbose, clean, ninja_args)
    elif backend.startswith('vs'):
        cmd, env = get_parsed_args_vs(bdir, targets, jobs, load_average, verbose, clean, vs_args)
    elif backend == 'xcode':
        cmd, env = get_parsed_args_xcode(bdir, targets, jobs, load_average, verbose, clean, xcode_args)
    else:
        raise MesonException(
            f'Backend `{backend}` is not yet supported by `compile`. Use generated project files directly instead.')

    mlog.log(mlog.green('INFO:'), 'calculating backend command to run:', join_args(cmd))
    p, *_ = mesonlib.Popen_safe(cmd, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer, env=env)
    return p.returncode

def run(options: 'argparse.Namespace') -> int:
    bdir = Path(options.wd)
    validate_builddir(bdir)
    if options.targets and options.clean:
        raise MesonException('`TARGET` and `--clean` can\'t be used simultaneously')

    b = build.load(options.wd)
    cdata = b.environment.coredata
    need_vsenv = T.cast('bool', cdata.get_option(OptionKey('vsenv')))
    if setup_vsenv(need_vsenv):
        mlog.log(mlog.green('INFO:'), 'automatically activated MSVC compiler environment')

    intro_targets: T.List[IntroTarget] = []
    if options.targets:
        intro_data = parse_introspect_data(bdir)
        intro_targets = [get_target_from_intro_data(t, bdir, intro_data) for t in options.targets]

    return run_compile(b.environment, intro_targets, options.jobs, options.load_average,
                       options.verbose, options.clean, options.ninja_args, options.vs_args, options.xcode_args)
