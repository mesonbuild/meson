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

from .ast import AstInterpreter, AstVisitor, AstIDGenerator, AstIndentationGenerator, AstPrinter
from mesonbuild.mesonlib import MesonException
from mesonbuild import mlog
import traceback

def add_arguments(parser):
    parser.add_argument('--sourcedir', default='.',
                        help='Path to source directory.')
    parser.add_argument('-p', '--print', action='store_true', default=False, dest='print',
                        help='Print the parsed AST.')

def run(options):
    rewriter = AstInterpreter(options.sourcedir, '')
    try:
        rewriter.load_root_meson_file()
        rewriter.sanity_check_ast()
        rewriter.parse_project()
        rewriter.run()

        indentor = AstIndentationGenerator()
        idgen = AstIDGenerator()
        printer = AstPrinter()
        rewriter.ast.accept(indentor)
        rewriter.ast.accept(idgen)
        rewriter.ast.accept(printer)
        print(printer.result)
    except Exception as e:
        if isinstance(e, MesonException):
            mlog.exception(e)
        else:
            traceback.print_exc()
        return 1
    return 0
