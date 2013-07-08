# Copyright 2012 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os, platform

"""This is (mostly) a standalone module used to write logging
information about Meson runs. Some output goes to screen,
some to logging dir and some goes to both."""

colorize_console = platform.system().lower() != 'windows' and os.isatty(sys.stdout.fileno())

class AnsiDecorator():
    plain_code = "\033[0m"
    
    def __init__(self, text, code):
        self.text = text
        self.code = code
    
    def get_text(self, with_codes):
        if with_codes:
            return self.code + self.text + AnsiDecorator.plain_code

def bold(text):
    return AnsiDecorator(text, "\033[1m")

def red(text):
    return AnsiDecorator(text, "\033[1;31m")

def green(text):
    return AnsiDecorator(text, "\033[1;32m")

def cyan(text):
    return AnsiDecorator(text, "\033[1;36m")

def log(*args):
    arr = []
    for arg in args:
        if isinstance(arg, str):
            arr.append(arg)
        elif isinstance(arg, AnsiDecorator):
            arr.append(arg.get_text(colorize_console))
        else:
            arr.append(str(arg))
    print(*arr)
