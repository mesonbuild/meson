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

"""This is (mostly) a standalone module used to write logging
information about Meson runs. Some output goes to screen,
some to logging dir and some goes to both."""

colorize_console = platform.system().lower() != 'windows' and os.isatty(sys.stdout.fileno()) and \
    os.environ.get('TERM') != 'dumb'
log_dir = None
log_file = None

def initialize(logdir):
    global log_dir, log_file
    log_dir = logdir
    log_file = open(os.path.join(logdir, 'meson-log.txt'), 'w', encoding='utf8')

def shutdown():
    global log_file
    if log_file is not None:
        log_file.close()

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
    # _Something_ is going to get printed.
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        iostr = io.StringIO()
        kwargs['file'] = iostr
        print(*args, **kwargs)
        cleaned = iostr.getvalue().encode('ascii', 'replace').decode('ascii')
        print(cleaned)

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

def warning(*args, **kwargs):
    log(yellow('WARNING:'), *args, **kwargs)

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
