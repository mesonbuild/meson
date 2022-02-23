import os, subprocess
import argparse
import tempfile
import shutil
import itertools

from pathlib import Path
from . import build, minstall, dependencies
from .mesonlib import MesonException, RealPathAction, is_windows, setup_vsenv, OptionKey, quote_arg
from . import mlog

import typing as T
if T.TYPE_CHECKING:
    from .backends import InstallData

def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('-C', dest='wd', action=RealPathAction,
                        help='Directory to cd into before running')
    parser.add_argument('--dump', action='store_true',
                        help='Only print required environment (Since 0.62.0)')
    parser.add_argument('command', nargs=argparse.REMAINDER,
                        help='Command to run in developer environment (default: interactive shell)')

def get_windows_shell() -> str:
    mesonbuild = Path(__file__).parent
    script = mesonbuild / 'scripts' / 'cmd_or_ps.ps1'
    command = ['powershell.exe', '-noprofile', '-executionpolicy', 'bypass', '-file', str(script)]
    result = subprocess.check_output(command)
    return result.decode().strip()

def get_env(b: build.Build, build_dir: str) -> T.Tuple[T.Dict[str, str], T.Set[str]]:
    extra_env = build.EnvironmentVariables()
    extra_env.set('MESON_DEVENV', ['1'])
    extra_env.set('MESON_PROJECT_NAME', [b.project_name])

    meson_uninstalled = Path(build_dir) / 'meson-uninstalled'
    if meson_uninstalled.is_dir():
        extra_env.prepend('PKG_CONFIG_PATH', [str(meson_uninstalled)])

    env = os.environ.copy()
    varnames = set()
    for i in itertools.chain(b.devenv, {extra_env}):
        env = i.get_env(env)
        varnames |= i.get_names()

    return env, varnames

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

def add_gdb_auto_load(autoload_path: Path, gdb_helper: str, fname: Path) -> None:
    # Copy or symlink the GDB helper into our private directory tree
    destdir = autoload_path / fname.parent
    destdir.mkdir(parents=True, exist_ok=True)
    try:
        if is_windows():
            shutil.copy(gdb_helper, str(destdir / os.path.basename(gdb_helper)))
        else:
            os.symlink(gdb_helper, str(destdir / os.path.basename(gdb_helper)))
    except (FileExistsError, shutil.SameFileError):
        pass

def write_gdb_script(privatedir: Path, install_data: 'InstallData') -> None:
    if not shutil.which('gdb'):
        return
    bdir = privatedir.parent
    autoload_basedir = privatedir / 'gdb-auto-load'
    autoload_path = Path(autoload_basedir, *bdir.parts[1:])
    have_gdb_helpers = False
    for d in install_data.data:
        if d.path.endswith('-gdb.py') or d.path.endswith('-gdb.gdb') or d.path.endswith('-gdb.scm'):
            # This GDB helper is made for a specific shared library, search if
            # we have it in our builddir.
            libname = Path(d.path).name.rsplit('-', 1)[0]
            for t in install_data.targets:
                path = Path(t.fname)
                if path.name == libname:
                    add_gdb_auto_load(autoload_path, d.path, path)
                    have_gdb_helpers = True
    if have_gdb_helpers:
        gdbinit_line = f'add-auto-load-scripts-directory {autoload_basedir}\n'
        gdbinit_path = bdir / '.gdbinit'
        first_time = False
        try:
            with gdbinit_path.open('r+', encoding='utf-8') as f:
                if gdbinit_line not in f.readlines():
                    f.write(gdbinit_line)
                    first_time = True
        except FileNotFoundError:
            gdbinit_path.write_text(gdbinit_line, encoding='utf-8')
            first_time = True
        if first_time:
            mlog.log('Meson detected GDB helpers and added config in', mlog.bold(str(gdbinit_path)))

def run(options: argparse.Namespace) -> int:
    privatedir = Path(options.wd) / 'meson-private'
    buildfile = privatedir / 'build.dat'
    if not buildfile.is_file():
        raise MesonException(f'Directory {options.wd!r} does not seem to be a Meson build directory.')
    b = build.load(options.wd)

    devenv, varnames = get_env(b, options.wd)
    if options.dump:
        if options.command:
            raise MesonException('--dump option does not allow running other command.')
        for name in varnames:
            print(f'{name}={quote_arg(devenv[name])}')
            print(f'export {name}')
        return 0

    install_data = minstall.load_install_data(str(privatedir / 'install.dat'))
    write_gdb_script(privatedir, install_data)

    setup_vsenv(b.need_vsenv)

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
