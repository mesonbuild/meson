import os, subprocess
import argparse
import tempfile

from pathlib import Path
from . import build
from .mesonlib import MesonException, is_windows

import typing as T

def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('-C', default='.', dest='wd',
                        help='directory to cd into before running')
    parser.add_argument('command', nargs=argparse.REMAINDER,
                        help='Command to run in developer environment (default: interactive shell)')

def get_windows_shell() -> str:
    mesonbuild = Path(__file__).parent
    script = mesonbuild / 'scripts' / 'cmd_or_ps.ps1'
    command = ['powershell.exe', '-noprofile', '-executionpolicy', 'bypass', '-file', str(script)]
    result = subprocess.check_output(command)
    return result.decode().strip()

def get_env(b: build.Build, build_dir: str) -> T.Dict[str, str]:
    env = os.environ.copy()
    for i in b.devenv:
        env = i.get_env(env)

    extra_env = build.EnvironmentVariables()
    extra_env.set('MESON_DEVENV', ['1'])
    extra_env.set('MESON_PROJECT_NAME', [b.project_name])

    meson_uninstalled = Path(build_dir) / 'meson-uninstalled'
    if meson_uninstalled.is_dir():
        extra_env.prepend('PKG_CONFIG_PATH', [str(meson_uninstalled)])

    return extra_env.get_env(env)

def run(options: argparse.Namespace) -> int:
    options.wd = os.path.abspath(options.wd)
    buildfile = Path(options.wd) / 'meson-private' / 'build.dat'
    if not buildfile.is_file():
        raise MesonException(f'Directory {options.wd!r} does not seem to be a Meson build directory.')
    b = build.load(options.wd)

    devenv = get_env(b, options.wd)

    args = options.command
    if not args:
        prompt_prefix = f'[{b.project_name}]'
        if is_windows():
            shell = get_windows_shell()
            if shell == 'powershell.exe':
                args = ['powershell.exe']
                args += ['-NoLogo', '-NoExit']
                prompt = f'function global:prompt {{  "{prompt_prefix} PS " + $PWD + "> "}}'
                args += ['-Command', prompt]
            else:
                args = [os.environ.get("COMSPEC", r"C:\WINDOWS\system32\cmd.exe")]
                args += ['/k', f'prompt {prompt_prefix} $P$G']
        else:
            args = [os.environ.get("SHELL", os.path.realpath("/bin/sh"))]
        if "bash" in args[0] and not os.environ.get("MESON_DISABLE_PS1_OVERRIDE"):
            tmprc = tempfile.NamedTemporaryFile(mode='w')
            bashrc = os.path.expanduser('~/.bashrc')
            if os.path.exists(bashrc):
                tmprc.write(f'. {bashrc}\n')
            tmprc.write(f'export PS1="{prompt_prefix} $PS1"')
            tmprc.flush()
            # Let the GC remove the tmp file
            args.append("--rcfile")
            args.append(tmprc.name)

    try:
        return subprocess.call(args, close_fds=False,
                               env=devenv,
                               cwd=options.wd)
    except subprocess.CalledProcessError as e:
        return e.returncode
