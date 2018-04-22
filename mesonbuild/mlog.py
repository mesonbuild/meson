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

import sys, os, platform, io
from contextlib import contextmanager

"""This is (mostly) a standalone module used to write logging
information about Meson runs. Some output goes to screen,
some to logging dir and some goes to both."""

if platform.system().lower() == 'windows':
    colorize_console = os.isatty(sys.stdout.fileno()) and os.environ.get('ANSICON')
else:
    colorize_console = os.isatty(sys.stdout.fileno()) and os.environ.get('TERM') != 'dumb'
log_dir = None
log_file = None
log_fname = 'meson-log.txt'
log_depth = 0

def initialize(logdir):
    global log_dir, log_file
    log_dir = logdir
    log_file = open(os.path.join(logdir, log_fname), 'w', encoding='utf8')

def shutdown():
    global log_file
    if log_file is not None:
        exception_around_goer = log_file
        log_file = None
        exception_around_goer.close()

class AnsiDecorator:
    plain_code = "\033[0m"

    def __init__(self, text, code):
        self.text = text
        self.code = code

    def get_text(self, with_codes):
        if with_codes:
            return self.code + self.text + AnsiDecorator.plain_code
        return self.text

def bold(text):
    return AnsiDecorator(text, "\033[1m")

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
    from . import environment
    if severity == 'warning':
        args = (yellow('WARNING:'),) + args
    elif severity == 'error':
        args = (red('ERROR:'),) + args
    else:
        assert False, 'Invalid severity ' + severity

    location = kwargs.pop('location', None)
    if location is not None:
        location_str = '{}:{}:'.format(os.path.join(location.subdir,
                                                    environment.build_filename),
                                       location.lineno)
        args = (location_str,) + args

    log(*args, **kwargs)

def error(*args, **kwargs):
    return _log_error('error', *args, **kwargs)

def warning(*args, **kwargs):
    return _log_error('warning', *args, **kwargs)

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
