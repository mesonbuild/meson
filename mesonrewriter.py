#!/usr/bin/env python3
# Copyright 2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This class contains the basic functionality needed to run any interpreter
# or an interpreter-based tool.

# This tool is used to manipulate an existing Meson build definition.
#
# - add a file to a target
# - remove files from a target
# - move targets
# - reindent?

import mesonbuild.astinterpreter
from mesonbuild.mesonlib import MesonException
from mesonbuild import mlog
import sys, traceback
import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--sourcedir', default='.',
                    help='Path to source directory.')
parser.add_argument('--target', default=None,
                    help='Name of target to edit.')
parser.add_argument('--filename', default=None,
                    help='Name of source file to add or remove to target.')
parser.add_argument('commands', nargs='+')

if __name__ == '__main__':
    options = parser.parse_args()
    if options.target is None or options.filename is None:
        sys.exit("Must specify both target and filename.")
    print('This tool is highly experimental, use with care.')
    rewriter = mesonbuild.astinterpreter.AstInterpreter(options.sourcedir, '')
    try:
        if options.commands[0] == 'add':
            rewriter.add_source(options.target, options.filename)
        elif options.commands[0] == 'remove':
            rewriter.remove_source(options.target, options.filename)
        else:
            sys.exit('Unknown command: ' + options.commands[0])
    except Exception as e:
        if isinstance(e, MesonException):
            if hasattr(e, 'file') and hasattr(e, 'lineno') and hasattr(e, 'colno'):
                mlog.log(mlog.red('\nMeson encountered an error in file %s, line %d, column %d:' % (e.file, e.lineno, e.colno)))
            else:
                mlog.log(mlog.red('\nMeson encountered an error:'))
            mlog.log(e)
        else:
            traceback.print_exc()
        sys.exit(1)
