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
from contextlib import contextmanager
import typing
from typing import Any, Generator, List, Optional, Sequence, TextIO, Union

"""This is (mostly) a standalone module used to write logging
information about Meson runs. Some output goes to screen,
some to logging dir and some goes to both."""

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

if platform.system().lower() == 'windows':
    colorize_console = os.isatty(sys.stdout.fileno()) and _windows_ansi()  # type: bool
else:
    colorize_console = os.isatty(sys.stdout.fileno()) and os.environ.get('TERM') != 'dumb'
log_dir = None               # type: Optional[str]
log_file = None              # type: Optional[TextIO]
log_fname = 'meson-log.txt'  # type: str
log_depth = 0                # type: int
log_timestamp_start = None   # type: Optional[float]
log_fatal_warnings = False   # type: bool
log_disable_stdout = False   # type: bool
log_errors_only = False      # type: bool

def disable() -> None:
    global log_disable_stdout
    log_disable_stdout = True

def enable() -> None:
    global log_disable_stdout
    log_disable_stdout = False

def set_quiet() -> None:
    global log_errors_only
    log_errors_only = True

def set_verbose() -> None:
    global log_errors_only
    log_errors_only = False

def initialize(logdir: str, fatal_warnings: bool = False) -> None:
    global log_dir, log_file, log_fatal_warnings
    log_dir = logdir
    log_file = open(os.path.join(logdir, log_fname), 'w', encoding='utf8')
    log_fatal_warnings = fatal_warnings

def set_timestamp_start(start: float) -> None:
    global log_timestamp_start
    log_timestamp_start = start

def shutdown() -> Optional[str]:
    global log_file
    if log_file is not None:
        path = log_file.name
        exception_around_goer = log_file
        log_file = None
        exception_around_goer.close()
        return path
    return None

class AnsiDecorator:
    plain_code = "\033[0m"

    def __init__(self, text: str, code: str, quoted: bool = False):
        self.text = text
        self.code = code
        self.quoted = quoted

    def get_text(self, with_codes: bool) -> str:
        text = self.text
        if with_codes:
            text = self.code + self.text + AnsiDecorator.plain_code
        if self.quoted:
            text = '"{}"'.format(text)
        return text

def bold(text: str, quoted: bool = False) -> AnsiDecorator:
    return AnsiDecorator(text, "\033[1m", quoted=quoted)

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

# This really should be AnsiDecorator or anything that implements
# __str__(), but that requires protocols from typing_extensions
def process_markup(args: Sequence[Union[AnsiDecorator, str]], keep: bool) -> List[str]:
    arr = []  # type: List[str]
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

def force_print(*args: str, **kwargs: Any) -> None:
    global log_disable_stdout
    if log_disable_stdout:
        return
    iostr = io.StringIO()
    kwargs['file'] = iostr
    print(*args, **kwargs)

    raw = iostr.getvalue()
    if log_depth > 0:
        prepend = '|' * log_depth
        raw = prepend + raw.replace('\n', '\n' + prepend, raw.count('\n') - 1)

    # _Something_ is going to get printed.
    try:
        print(raw, end='')
    except UnicodeEncodeError:
        cleaned = raw.encode('ascii', 'replace').decode('ascii')
        print(cleaned, end='')

# We really want a heterogenous dict for this, but that's in typing_extensions
def debug(*args: Union[str, AnsiDecorator], **kwargs: Any) -> None:
    arr = process_markup(args, False)
    if log_file is not None:
        print(*arr, file=log_file, **kwargs)
        log_file.flush()

def log(*args: Union[str, AnsiDecorator], is_error: bool = False,
        **kwargs: Any) -> None:
    global log_errors_only
    arr = process_markup(args, False)
    if log_file is not None:
        print(*arr, file=log_file, **kwargs)
        log_file.flush()
    if colorize_console:
        arr = process_markup(args, True)
    if not log_errors_only or is_error:
        force_print(*arr, **kwargs)

def _log_error(severity: str, *rargs: Union[str, AnsiDecorator], **kwargs: Any) -> None:
    from .mesonlib import get_error_location_string
    from .environment import build_filename
    from .mesonlib import MesonException

    # The tping requirements here are non-obvious. Lists are invariant,
    # therefore List[A] and List[Union[A, B]] are not able to be joined
    if severity == 'warning':
        label = [yellow('WARNING:')]  # type: List[Union[str, AnsiDecorator]]
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
        location_file = os.path.join(location.subdir, build_filename)
        location_str = get_error_location_string(location_file, location.lineno)
        # Unions are frankly awful, and we have to cast here to get mypy
        # to understand that the list concatenation is safe
        location_list = typing.cast(List[Union[str, AnsiDecorator]], [location_str])
        args = location_list + args

    log(*args, **kwargs)

    global log_fatal_warnings
    if log_fatal_warnings:
        raise MesonException("Fatal warnings enabled, aborting")

def error(*args: Union[str, AnsiDecorator], **kwargs: Any) -> None:
    return _log_error('error', *args, **kwargs, is_error=True)

def warning(*args: Union[str, AnsiDecorator], **kwargs: Any) -> None:
    return _log_error('warning', *args, **kwargs, is_error=True)

def deprecation(*args: Union[str, AnsiDecorator], **kwargs: Any) -> None:
    return _log_error('deprecation', *args, **kwargs, is_error=True)

def exception(e: Exception, prefix: Optional[AnsiDecorator] = None) -> None:
    if prefix is None:
        prefix = red('ERROR:')
    log()
    args = []  # type: List[Union[AnsiDecorator, str]]
    if hasattr(e, 'file') and hasattr(e, 'lineno') and hasattr(e, 'colno'):
        # Mypy can't figure this out, and it's pretty easy to vidual inspect
        # that this is correct, so we'll just ignore it.
        args.append('%s:%d:%d:' % (e.file, e.lineno, e.colno))  # type: ignore
    if prefix:
        args.append(prefix)
    args.append(str(e))
    log(*args)

# Format a list for logging purposes as a string. It separates
# all but the last item with commas, and the last with 'and'.
def format_list(input_list: List[str]) -> str:
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
def nested() -> Generator[None, None, None]:
    global log_depth
    log_depth += 1
    try:
        yield
    finally:
        log_depth -= 1
