import os, subprocess
import argparse
import tempfile

from pathlib import Path
from . import build, minstall, dependencies
from .mesonlib import MesonException, RealPathAction, is_windows, setup_vsenv, OptionKey

import typing as T
if T.TYPE_CHECKING:
    from .backends import InstallData

def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('-C', dest='wd', action=RealPathAction,
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

def bash_completion_files(b: build.Build, install_data: 'InstallData') -> T.List[str]:
    result = []
    dep = dependencies.PkgConfigDependency('bash-completion', b.environment,
                                           {'silent': True, 'version': '>=2.10'})
    if dep.found():
        prefix = b.environment.coredata.get_option(OptionKey('prefix'))
        assert isinstance(prefix, str), 'for mypy'
        datadir = b.environment.coredata.get_option(OptionKey('datadir'))
        assert isinstance(datadir, str), 'for mypy'
        datadir_abs = os.path.join(prefix, datadir)
        completionsdir = dep.get_variable(pkgconfig='completionsdir', pkgconfig_define=['datadir', datadir_abs])
        assert isinstance(completionsdir, str), 'for mypy'
        completionsdir_path = Path(completionsdir)
        for f in install_data.data:
            if completionsdir_path in Path(f.install_path).parents:
                result.append(f.path)
    return result

def run(options: argparse.Namespace) -> int:
    buildfile = Path(options.wd) / 'meson-private' / 'build.dat'
    if not buildfile.is_file():
        raise MesonException(f'Directory {options.wd!r} does not seem to be a Meson build directory.')
    b = build.load(options.wd)
    install_data = minstall.load_install_data(str(buildfile.parent / 'install.dat'))
    setup_vsenv(b.need_vsenv)

    devenv = get_env(b, options.wd)

    args = options.command
    if not args:
        prompt_prefix = f'[{b.project_name}]'
        shell_env = os.environ.get("SHELL")
        # Prefer $SHELL in a MSYS2 bash despite it being Windows
        if shell_env and os.path.exists(shell_env):
            args = [shell_env]
        elif is_windows():
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
        if "bash" in args[0]:
            # Let the GC remove the tmp file
            tmprc = tempfile.NamedTemporaryFile(mode='w')
            tmprc.write('[ -e ~/.bashrc ] && . ~/.bashrc\n')
            if not os.environ.get("MESON_DISABLE_PS1_OVERRIDE"):
                tmprc.write(f'export PS1="{prompt_prefix} $PS1"\n')
            for f in bash_completion_files(b, install_data):
                tmprc.write(f'. "{f}"\n')
            tmprc.flush()
            args.append("--rcfile")
            args.append(tmprc.name)

    try:
        return subprocess.call(args, close_fds=False,
                               env=devenv,
                               cwd=options.wd)
    except subprocess.CalledProcessError as e:
        return e.returncode
