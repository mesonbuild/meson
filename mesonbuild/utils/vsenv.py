# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2025 The Meson development team

from __future__ import annotations

import os
import subprocess
import json
import pathlib
import shutil

from .. import mlog
from .core import MesonException
from .universal import is_windows, windows_detect_native_arch


__all__ = [
    'setup_vsenv',
]


def get_vsenv(force: bool) -> dict[str, str] | None:
    """
    This function locates a Visual Studio installation, executes its environment
    setup script (vcvars*.bat), and returns the environment variables that were
    modified or added by the script.
    Returns:
        dict[str, str] | None: A dictionary containing environment variables
        that were added or modified by the Visual Studio setup script or None.
    """
    if not is_windows():
        return None
    if os.environ.get('OSTYPE') == 'cygwin':
        return None
    if 'MESON_FORCE_VSENV_FOR_UNITTEST' not in os.environ:
        # VSINSTALL is set when running setvars from a Visual Studio installation
        # Tested with Visual Studio 2012 and 2017
        if 'VSINSTALLDIR' in os.environ:
            return None
        # Check explicitly for cl when on Windows
        if shutil.which('cl.exe'):
            return None
    if not force:
        if shutil.which('cc'):
            return None
        if shutil.which('gcc'):
            return None
        if shutil.which('clang'):
            return None
        if shutil.which('clang-cl'):
            return None

    root = os.environ.get("ProgramFiles(x86)") or os.environ.get("ProgramFiles")
    bat_locator_bin = pathlib.Path(root, 'Microsoft Visual Studio/Installer/vswhere.exe')
    if not bat_locator_bin.exists():
        raise MesonException(f'Could not find {bat_locator_bin}')
    bat_json = subprocess.check_output(
        [
            str(bat_locator_bin),
            '-latest',
            '-prerelease',
            '-requiresAny',
            '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
            '-requires', 'Microsoft.VisualStudio.Workload.WDExpress',
            '-products', '*',
            '-utf8',
            '-format',
            'json'
        ]
    )
    bat_info = json.loads(bat_json)
    if not bat_info:
        # VS installer installed but not VS itself maybe?
        raise MesonException('Could not parse vswhere.exe output')
    bat_root = pathlib.Path(bat_info[0]['installationPath'])
    if windows_detect_native_arch() == 'arm64':
        bat_path = bat_root / 'VC/Auxiliary/Build/vcvarsarm64.bat'
        if not bat_path.exists():
            bat_path = bat_root / 'VC/Auxiliary/Build/vcvarsx86_arm64.bat'
    else:
        bat_path = bat_root / 'VC/Auxiliary/Build/vcvars64.bat'
        # if VS is not found try VS Express
        if not bat_path.exists():
            bat_path = bat_root / 'VC/Auxiliary/Build/vcvarsx86_amd64.bat'
    if not bat_path.exists():
        raise MesonException(f'Could not find {bat_path}')

    mlog.log('Activating VS', bat_info[0]['catalog']['productDisplayVersion'])

    before_separator = '---BEFORE---'
    after_separator = '---AFTER---'
    # This will print to stdout the env variables set before the VS
    # activation and after VS activation so that we can process only
    # newly created environment variables. This is required to correctly parse
    # environment variables taking into account that some variables
    # can have multiple lines. (https://github.com/mesonbuild/meson/pull/13682)
    cmd = f'set&& echo {before_separator}&&"{bat_path.absolute()}" && echo {after_separator}&& set'
    process = subprocess.Popen(
        f'cmd.exe /c "{cmd}"',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f'Script failed with error: {stderr.decode()}')
    lines = stdout.decode().splitlines()

    # Remove the output from the vcvars script
    try:
        lines_before = set(lines[: lines.index(before_separator)])
        lines_after = set(lines[lines.index(after_separator) + 1:])
    except ValueError:
        raise MesonException('Could not find separators in environment variables output')

    # Filter out duplicated lines to remove env variables that haven't changed
    new_lines = lines_after - lines_before
    vsenv = {}
    for line in new_lines:
        parts = line.split('=', 1)
        if len(parts) != 2:
            continue
        k, v = parts
        if k is None or v is None:
            continue
        vsenv[k] = v
    return vsenv


def setup_vsenv(force: bool = False) -> bool:
    """
    Setup the VS environment if we are on Windows and VS is installed but not
    set up in the environment. In this way Meson can be directly invoked
    from any shell, VS Code etc...
    """
    try:
        vsenv = get_vsenv(force)
        if vsenv is None:
            return False
        for k, v in vsenv.items():
            try:
                os.environ[k] = v
            except ValueError:
                # Ignore errors from junk data returning invalid environment variable names
                pass
        return True
    except MesonException as e:
        if force:
            raise
        mlog.warning('Failed to activate VS environment:', str(e))
        return False
