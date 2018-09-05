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

"""This is (mostly) a standalone module used to write logging
information about Meson runs. Some output goes to screen,
some to logging dir and some goes to both."""

def _windows_ansi():
    from ctypes import windll, byref
    from ctypes.wintypes import DWORD

    kernel = windll.kernel32
    stdout = kernel.GetStdHandle(-11)
    mode = DWORD()
    if not kernel.GetConsoleMode(stdout, byref(mode)):
        return False
    # ENABLE_VIRTUAL_TERMINAL_PROCESSING == 0x4
    # If the call to enable VT processing fails (returns 0), we fallback to
    # original behavior
    return kernel.SetConsoleMode(stdout, mode.value | 0x4) or os.environ.get('ANSICON')

if platform.system().lower() == 'windows':
    colorize_console = os.isatty(sys.stdout.fileno()) and _windows_ansi()
else:
    colorize_console = os.isatty(sys.stdout.fileno()) and os.environ.get('TERM') != 'dumb'
log_dir = None
log_file = None
log_fname = 'meson-log.txt'
log_depth = 0
log_timestamp_start = None
log_fatal_warnings = False

def initialize(logdir, fatal_warnings=False):
    global log_dir, log_file, log_fatal_warnings
    log_dir = logdir
    log_file = open(os.path.join(logdir, log_fname), 'w', encoding='utf8')
    log_fatal_warnings = fatal_warnings

def set_timestamp_start(start):
    global log_timestamp_start
    log_timestamp_start = start

def shutdown():
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

    def __init__(self, text, code, quoted=False):
        self.text = text
        self.code = code
        self.quoted = quoted

    def get_text(self, with_codes):
        text = self.text
        if with_codes:
            text = self.code + self.text + AnsiDecorator.plain_code
        if self.quoted:
            text = '"{}"'.format(text)
        return text

def bold(text, quoted=False):
    return AnsiDecorator(text, "\033[1m", quoted=quoted)

def red(text):
    return AnsiDecorator(text, "\033[1;31m")

def green(text):
    return AnsiDecorator(text, "\033[1;32m")

def yellow(text):
    return AnsiDecorator(text, "\033[1;33m")

def cyan(text):
    return AnsiDecorator(text, "\033[1;36m")

def process_markup(args, keep):
    arr = []
    if log_timestamp_start is not None:
        arr = ['[{:.3f}]'.format(time.monotonic() - log_timestamp_start)]
    for arg in args:
        if isinstance(arg, str):
            arr.append(arg)
        elif isinstance(arg, AnsiDecorator):
            arr.append(arg.get_text(keep))
        else:
            arr.append(str(arg))
    return arr

def force_print(*args, **kwargs):
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

def debug(*args, **kwargs):
    arr = process_markup(args, False)
    if log_file is not None:
        print(*arr, file=log_file, **kwargs) # Log file never gets ANSI codes.
        log_file.flush()

def log(*args, **kwargs):
    arr = process_markup(args, False)
    if log_file is not None:
        print(*arr, file=log_file, **kwargs) # Log file never gets ANSI codes.
        log_file.flush()
    if colorize_console:
        arr = process_markup(args, True)
    force_print(*arr, **kwargs)

def _log_error(severity, *args, **kwargs):
    from .mesonlib import get_error_location_string
    from .environment import build_filename
    from .mesonlib import MesonException
    if severity == 'warning':
        args = (yellow('WARNING:'),) + args
    elif severity == 'error':
        args = (red('ERROR:'),) + args
    elif severity == 'deprecation':
        args = (red('DEPRECATION:'),) + args
    else:
        assert False, 'Invalid severity ' + severity

    location = kwargs.pop('location', None)
    if location is not None:
        location_file = os.path.join(location.subdir, build_filename)
        location_str = get_error_location_string(location_file, location.lineno)
        args = (location_str,) + args

    log(*args, **kwargs)

    global log_fatal_warnings
    if log_fatal_warnings:
        raise MesonException("Fatal warnings enabled, aborting")

def error(*args, **kwargs):
    return _log_error('error', *args, **kwargs)

def warning(*args, **kwargs):
    return _log_error('warning', *args, **kwargs)

def deprecation(*args, **kwargs):
    return _log_error('deprecation', *args, **kwargs)

def exception(e):
    log()
    if hasattr(e, 'file') and hasattr(e, 'lineno') and hasattr(e, 'colno'):
        log('%s:%d:%d:' % (e.file, e.lineno, e.colno), red('ERROR: '), e)
    else:
        log(red('ERROR:'), e)

# Format a list for logging purposes as a string. It separates
# all but the last item with commas, and the last with 'and'.
def format_list(list):
    l = len(list)
    if l > 2:
        return ' and '.join([', '.join(list[:-1]), list[-1]])
    elif l == 2:
        return ' and '.join(list)
    elif l == 1:
        return list[0]
    else:
        return ''

@contextmanager
def nested():
    global log_depth
    log_depth += 1
    try:
        yield
    finally:
        log_depth -= 1
