# Copyright 2013-2014 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import io
import sys
import time
import platform
import shlex
import subprocess
import shutil
import typing as T
from contextlib import contextmanager
from pathlib import Path

if T.TYPE_CHECKING:
    from ._typing import StringProtocol, SizedStringProtocol

"""This is (mostly) a standalone module used to write logging
information about Meson runs. Some output goes to screen,
some to logging dir and some goes to both."""

def is_windows() -> bool:
    platname = platform.system().lower()
    return platname == 'windows'

def _windows_ansi() -> bool:
    # windll only exists on windows, so mypy will get mad
    from ctypes import windll, byref  # type: ignore
    from ctypes.wintypes import DWORD

    kernel = windll.kernel32
    stdout = kernel.GetStdHandle(-11)
    mode = DWORD()
    if not kernel.GetConsoleMode(stdout, byref(mode)):
        return False
    # ENABLE_VIRTUAL_TERMINAL_PROCESSING == 0x4
    # If the call to enable VT processing fails (returns 0), we fallback to
    # original behavior
    return bool(kernel.SetConsoleMode(stdout, mode.value | 0x4) or os.environ.get('ANSICON'))

def colorize_console() -> bool:
    _colorize_console = getattr(sys.stdout, 'colorize_console', None)  # type: bool
    if _colorize_console is not None:
        return _colorize_console

    try:
        if is_windows():
            _colorize_console = os.isatty(sys.stdout.fileno()) and _windows_ansi()
        else:
            _colorize_console = os.isatty(sys.stdout.fileno()) and os.environ.get('TERM', 'dumb') != 'dumb'
    except Exception:
        _colorize_console = False

    sys.stdout.colorize_console = _colorize_console  # type: ignore[attr-defined]
    return _colorize_console

def setup_console() -> None:
    # on Windows, a subprocess might call SetConsoleMode() on the console
    # connected to stdout and turn off ANSI escape processing. Call this after
    # running a subprocess to ensure we turn it on again.
    if is_windows():
        try:
            delattr(sys.stdout, 'colorize_console')
        except AttributeError:
            pass

log_dir = None               # type: T.Optional[str]
log_file = None              # type: T.Optional[T.TextIO]
log_fname = 'meson-log.txt'  # type: str
log_depth = []               # type: T.List[str]
log_timestamp_start = None   # type: T.Optional[float]
log_fatal_warnings = False   # type: bool
log_disable_stdout = False   # type: bool
log_errors_only = False      # type: bool
_in_ci = 'CI' in os.environ  # type: bool
_logged_once = set()         # type: T.Set[T.Tuple[str, ...]]
log_warnings_counter = 0     # type: int
log_pager: T.Optional['subprocess.Popen'] = None

def disable() -> None:
    global log_disable_stdout  # pylint: disable=global-statement
    log_disable_stdout = True

def enable() -> None:
    global log_disable_stdout  # pylint: disable=global-statement
    log_disable_stdout = False

def set_quiet() -> None:
    global log_errors_only  # pylint: disable=global-statement
    log_errors_only = True

def set_verbose() -> None:
    global log_errors_only  # pylint: disable=global-statement
    log_errors_only = False

def initialize(logdir: str, fatal_warnings: bool = False) -> None:
    global log_dir, log_file, log_fatal_warnings  # pylint: disable=global-statement
    log_dir = logdir
    log_file = open(os.path.join(logdir, log_fname), 'w', encoding='utf-8')
    log_fatal_warnings = fatal_warnings

def set_timestamp_start(start: float) -> None:
    global log_timestamp_start  # pylint: disable=global-statement
    log_timestamp_start = start

def shutdown() -> T.Optional[str]:
    global log_file  # pylint: disable=global-statement
    if log_file is not None:
        path = log_file.name
        exception_around_goer = log_file
        log_file = None
        exception_around_goer.close()
        return path
    stop_pager()
    return None

class AnsiDecorator:
    plain_code = "\033[0m"

    def __init__(self, text: str, code: str, quoted: bool = False):
        self.text = text
        self.code = code
        self.quoted = quoted

    def get_text(self, with_codes: bool) -> str:
        text = self.text
        if with_codes and self.code:
            text = self.code + self.text + AnsiDecorator.plain_code
        if self.quoted:
            text = f'"{text}"'
        return text

    def __len__(self) -> int:
        return len(self.text)

    def __str__(self) -> str:
        return self.get_text(colorize_console())

TV_Loggable = T.Union[str, AnsiDecorator, 'StringProtocol']
TV_LoggableList = T.List[TV_Loggable]

class AnsiText:
    def __init__(self, *args: 'SizedStringProtocol'):
        self.args = args

    def __len__(self) -> int:
        return sum(len(x) for x in self.args)

    def __str__(self) -> str:
        return ''.join(str(x) for x in self.args)


def bold(text: str, quoted: bool = False) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[1m", quoted=quoted)

def italic(text: str, quoted: bool = False) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[3m", quoted=quoted)

def plain(text: str) -> AnsiDecorator:
    return AnsiDecorator(text, "")

def red(text: str) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[1;31m")

def green(text: str) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[1;32m")

def yellow(text: str) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[1;33m")

def blue(text: str) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[1;34m")

def cyan(text: str) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[1;36m")

def normal_red(text: str) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[31m")

def normal_green(text: str) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[32m")

def normal_yellow(text: str) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[33m")

def normal_blue(text: str) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[34m")

def normal_cyan(text: str) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[36m")

# This really should be AnsiDecorator or anything that implements
# __str__(), but that requires protocols from typing_extensions
def process_markup(args: T.Sequence[TV_Loggable], keep: bool) -> T.List[str]:
    arr = []  # type: T.List[str]
    if log_timestamp_start is not None:
        arr = ['[{:.3f}]'.format(time.monotonic() - log_timestamp_start)]
    for arg in args:
        if arg is None:
            continue
        if isinstance(arg, str):
            arr.append(arg)
        elif isinstance(arg, AnsiDecorator):
            arr.append(arg.get_text(keep))
        else:
            arr.append(str(arg))
    return arr

def force_print(*args: str, nested: bool, **kwargs: T.Any) -> None:
    if log_disable_stdout:
        return
    iostr = io.StringIO()
    kwargs['file'] = iostr
    print(*args, **kwargs)

    raw = iostr.getvalue()
    if log_depth:
        prepend = log_depth[-1] + '| ' if nested else ''
        lines = []
        for l in raw.split('\n'):
            l = l.strip()
            lines.append(prepend + l if l else '')
        raw = '\n'.join(lines)

    # _Something_ is going to get printed.
    try:
        output = log_pager.stdin if log_pager else None
        print(raw, end='', file=output)
    except UnicodeEncodeError:
        cleaned = raw.encode('ascii', 'replace').decode('ascii')
        print(cleaned, end='')

# We really want a heterogeneous dict for this, but that's in typing_extensions
def debug(*args: TV_Loggable, **kwargs: T.Any) -> None:
    arr = process_markup(args, False)
    if log_file is not None:
        print(*arr, file=log_file, **kwargs)
        log_file.flush()

def _debug_log_cmd(cmd: str, args: T.List[str]) -> None:
    if not _in_ci:
        return
    args = [f'"{x}"' for x in args]  # Quote all args, just in case
    debug('!meson_ci!/{} {}'.format(cmd, ' '.join(args)))

def cmd_ci_include(file: str) -> None:
    _debug_log_cmd('ci_include', [file])


def log(*args: TV_Loggable, is_error: bool = False,
        once: bool = False, **kwargs: T.Any) -> None:
    if once:
        log_once(*args, is_error=is_error, **kwargs)
    else:
        _log(*args, is_error=is_error, **kwargs)


def _log(*args: TV_Loggable, is_error: bool = False,
         **kwargs: T.Any) -> None:
    nested = kwargs.pop('nested', True)
    arr = process_markup(args, False)
    if log_file is not None:
        print(*arr, file=log_file, **kwargs)
        log_file.flush()
    if colorize_console():
        arr = process_markup(args, True)
    if not log_errors_only or is_error:
        force_print(*arr, nested=nested, **kwargs)

def log_once(*args: TV_Loggable, is_error: bool = False,
             **kwargs: T.Any) -> None:
    """Log variant that only prints a given message one time per meson invocation.

    This considers ansi decorated values by the values they wrap without
    regard for the AnsiDecorator itself.
    """
    def to_str(x: TV_Loggable) -> str:
        if isinstance(x, str):
            return x
        if isinstance(x, AnsiDecorator):
            return x.text
        return str(x)
    t = tuple(to_str(a) for a in args)
    if t in _logged_once:
        return
    _logged_once.add(t)
    _log(*args, is_error=is_error, **kwargs)

# This isn't strictly correct. What we really want here is something like:
# class StringProtocol(typing_extensions.Protocol):
#
#      def __str__(self) -> str: ...
#
# This would more accurately embody what this function can handle, but we
# don't have that yet, so instead we'll do some casting to work around it
def get_error_location_string(fname: str, lineno: int) -> str:
    return f'{fname}:{lineno}:'

def _log_error(severity: str, *rargs: TV_Loggable,
               once: bool = False, fatal: bool = True, **kwargs: T.Any) -> None:
    from .mesonlib import MesonException, relpath

    # The typing requirements here are non-obvious. Lists are invariant,
    # therefore T.List[A] and T.List[T.Union[A, B]] are not able to be joined
    if severity == 'notice':
        label = [bold('NOTICE:')]  # type: TV_LoggableList
    elif severity == 'warning':
        label = [yellow('WARNING:')]
    elif severity == 'error':
        label = [red('ERROR:')]
    elif severity == 'deprecation':
        label = [red('DEPRECATION:')]
    else:
        raise MesonException('Invalid severity ' + severity)
    # rargs is a tuple, not a list
    args = label + list(rargs)

    location = kwargs.pop('location', None)
    if location is not None:
        location_file = relpath(location.filename, os.getcwd())
        location_str = get_error_location_string(location_file, location.lineno)
        # Unions are frankly awful, and we have to T.cast here to get mypy
        # to understand that the list concatenation is safe
        location_list = T.cast('TV_LoggableList', [location_str])
        args = location_list + args

    log(*args, once=once, **kwargs)

    global log_warnings_counter  # pylint: disable=global-statement
    log_warnings_counter += 1

    if log_fatal_warnings and fatal:
        raise MesonException("Fatal warnings enabled, aborting")

def error(*args: TV_Loggable, **kwargs: T.Any) -> None:
    return _log_error('error', *args, **kwargs, is_error=True)

def warning(*args: TV_Loggable, **kwargs: T.Any) -> None:
    return _log_error('warning', *args, **kwargs, is_error=True)

def deprecation(*args: TV_Loggable, **kwargs: T.Any) -> None:
    return _log_error('deprecation', *args, **kwargs, is_error=True)

def notice(*args: TV_Loggable, **kwargs: T.Any) -> None:
    return _log_error('notice', *args, **kwargs, is_error=False)

def get_relative_path(target: Path, current: Path) -> Path:
    """Get the path to target from current"""
    # Go up "current" until we find a common ancestor to target
    acc = ['.']
    for part in [current, *current.parents]:
        try:
            path = target.relative_to(part)
            return Path(*acc, path)
        except ValueError:
            pass
        acc += ['..']

    # we failed, should not get here
    return target

def exception(e: Exception, prefix: T.Optional[AnsiDecorator] = None) -> None:
    if prefix is None:
        prefix = red('ERROR:')
    log()
    args = []  # type: T.List[T.Union[AnsiDecorator, str]]
    if all(getattr(e, a, None) is not None for a in ['file', 'lineno', 'colno']):
        # Mypy doesn't follow hasattr, and it's pretty easy to visually inspect
        # that this is correct, so we'll just ignore it.
        path = get_relative_path(Path(e.file), Path(os.getcwd()))  # type: ignore
        args.append(f'{path}:{e.lineno}:{e.colno}:')  # type: ignore
    if prefix:
        args.append(prefix)
    args.append(str(e))
    log(*args)

# Format a list for logging purposes as a string. It separates
# all but the last item with commas, and the last with 'and'.
def format_list(input_list: T.List[str]) -> str:
    l = len(input_list)
    if l > 2:
        return ' and '.join([', '.join(input_list[:-1]), input_list[-1]])
    elif l == 2:
        return ' and '.join(input_list)
    elif l == 1:
        return input_list[0]
    else:
        return ''

@contextmanager
def nested(name: str = '') -> T.Generator[None, None, None]:
    log_depth.append(name)
    try:
        yield
    finally:
        log_depth.pop()

def start_pager() -> None:
    if not colorize_console():
        return
    pager_cmd = []
    if 'PAGER' in os.environ:
        pager_cmd = shlex.split(os.environ['PAGER'])
    else:
        less = shutil.which('less')
        if not less and is_windows():
            git = shutil.which('git')
            if git:
                path = Path(git).parents[1] / 'usr' / 'bin'
                less = shutil.which('less', path=str(path))
        if less:
            pager_cmd = [less]
    if not pager_cmd:
        return
    global log_pager # pylint: disable=global-statement
    assert log_pager is None
    try:
        # Set 'LESS' environment variable, rather than arguments in
        # pager_cmd, to also support the case where the user has 'PAGER'
        # set to 'less'. Arguments set are:
        # "R" : support color
        # "X" : do not clear the screen when leaving the pager
        # "F" : skip the pager if content fits into the screen
        env = os.environ.copy()
        if 'LESS' not in env:
            env['LESS'] = 'RXF'
        # Set "-c" for lv to support color
        if 'LV' not in env:
            env['LV'] = '-c'
        log_pager = subprocess.Popen(pager_cmd, stdin=subprocess.PIPE,
                                     text=True, encoding='utf-8', env=env)
    except Exception as e:
        # Ignore errors, unless it is a user defined pager.
        if 'PAGER' in os.environ:
            from .mesonlib import MesonException
            raise MesonException(f'Failed to start pager: {str(e)}')

def stop_pager() -> None:
    global log_pager # pylint: disable=global-statement
    if log_pager:
        try:
            log_pager.stdin.flush()
            log_pager.stdin.close()
        except BrokenPipeError:
            pass
        log_pager.wait()
        log_pager = None
