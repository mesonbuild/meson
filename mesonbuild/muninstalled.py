import os, subprocess
import argparse
import tempfile
import shutil

from pathlib import Path
from . import build
from .mesonlib import MesonException

def get_windows_shell():
    command = ['powershell.exe', '-noprofile', '-executionpolicy', 'bypass', '-file', 'cmd_or_ps.ps1']
    result = subprocess.check_output(command)
    return result.decode().strip()

def add_arguments(parser):
    parser.add_argument('-C', default='.', dest='wd',
                        help='directory to cd into before running')
    parser.add_argument('command', nargs=argparse.REMAINDER,
                        help='Command to run in uninstalled environment (default: interactive shell)')

def run(options):
    options.wd = os.path.abspath(options.wd)
    buildfile = Path(options.wd) / 'meson-private' / 'build.dat'
    if not buildfile.is_file():
        raise MesonException('Directory {!r} does not seem to be a Meson build directory.'.format(options.wd))
    b = build.load(options.wd)
    uninstalled_env = os.environ.copy()
    for env in b.uninstalled_envs:
        uninstalled_env = env.get_env(uninstalled_env)

    args = options.command
    if not args:
        prompt_prefix = '[{}]'.format(b.project_name)
        if os.name == 'nt':
            shell = get_windows_shell()
            if shell == 'powershell.exe':
                args = ['powershell.exe']
                args += ['-NoLogo', '-NoExit']
                prompt = 'function global:prompt {  "{} PS " + $PWD + "> "}'.format(prompt_prefix)
                args += ['-Command', prompt]
            else:
                args = [os.environ.get("COMSPEC", r"C:\WINDOWS\system32\cmd.exe")]
                args += ['/k', 'prompt {} $P$G'.format(prompt_prefix)]
        else:
            args = [os.environ.get("SHELL", os.path.realpath("/bin/sh"))]
        if "bash" in args[0] and not os.environ.get("MESON_DISABLE_PS1_OVERRIDE"):
            tmprc = tempfile.NamedTemporaryFile(mode='w')
            bashrc = os.path.expanduser('~/.bashrc')
            if os.path.exists(bashrc):
                with open(bashrc, 'r') as src:
                    shutil.copyfileobj(src, tmprc)
            tmprc.write('\nexport PS1="{} $PS1"'.format(prompt_prefix))
            tmprc.flush()
            # Let the GC remove the tmp file
            args.append("--rcfile")
            args.append(tmprc.name)

    try:
        return subprocess.call(args, close_fds=False,
                               env=uninstalled_env,
                               cwd=options.wd)
    except subprocess.CalledProcessError as e:
        return e.returncode
