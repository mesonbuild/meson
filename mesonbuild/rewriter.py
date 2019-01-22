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

from .ast import IntrospectionInterpreter, build_target_functions, AstVisitor, AstIDGenerator, AstIndentationGenerator, AstPrinter
from mesonbuild.mesonlib import MesonException
from . import mlog, mparser, environment
import traceback
from functools import wraps
from pprint import pprint
import json, os

class RewriterException(MesonException):
    pass

def add_arguments(parser):
    parser.add_argument('--sourcedir', default='.',
                        help='Path to source directory.')
    parser.add_argument('-p', '--print', action='store_true', default=False, dest='print',
                        help='Print the parsed AST.')
    parser.add_argument('command', type=str)

class RequiredKeys:
    def __init__(self, keys):
        self.keys = keys

    def __call__(self, f):
        @wraps(f)
        def wrapped(*wrapped_args, **wrapped_kwargs):
            assert(len(wrapped_args) >= 2)
            cmd = wrapped_args[1]
            for key, val in self.keys.items():
                typ = val[0] # The type of the value
                default = val[1] # The default value -- None is required
                choices = val[2] # Valid choices -- None is for everything
                if key not in cmd:
                    if default is not None:
                        cmd[key] = default
                    else:
                        raise RewriterException('Key "{}" is missing in object for {}'
                                                .format(key, f.__name__))
                if not isinstance(cmd[key], typ):
                    raise RewriterException('Invalid type of "{}". Required is {} but provided was {}'
                                            .format(key, typ.__name__, type(cmd[key]).__name__))
                if choices is not None:
                    assert(isinstance(choices, list))
                    if cmd[key] not in choices:
                        raise RewriterException('Invalid value of "{}": Possible values are {} but provided was "{}"'
                                                .format(key, choices, cmd[key]))
            return f(*wrapped_args, **wrapped_kwargs)

        return wrapped

rewriter_keys = {
    'target': {
        'target': (str, None, None),
        'operation': (str, None, ['src_add', 'src_rm', 'test']),
        'sources': (list, [], None),
        'debug': (bool, False, None)
    }
}

class Rewriter:
    def __init__(self, sourcedir: str, generator: str = 'ninja'):
        self.sourcedir = sourcedir
        self.interpreter = IntrospectionInterpreter(sourcedir, '', generator)
        self.id_generator = AstIDGenerator()
        self.modefied_nodes = []
        self.functions = {
            'target': self.process_target,
        }

    def analyze_meson(self):
        mlog.log('Analyzing meson file:', mlog.bold(os.path.join(self.sourcedir, environment.build_filename)))
        self.interpreter.analyze()
        mlog.log('  -- Project:', mlog.bold(self.interpreter.project_data['descriptive_name']))
        mlog.log('  -- Version:', mlog.cyan(self.interpreter.project_data['version']))
        self.interpreter.ast.accept(AstIndentationGenerator())
        self.interpreter.ast.accept(self.id_generator)

    def find_target(self, target: str):
        for i in self.interpreter.targets:
            if target == i['name'] or target == i['id']:
                return i
        return None

    @RequiredKeys(rewriter_keys['target'])
    def process_target(self, cmd):
        mlog.log('Processing target', mlog.bold(cmd['target']), 'operation', mlog.cyan(cmd['operation']))
        target = self.find_target(cmd['target'])
        if target is None:
            mlog.error('Unknown target "{}" --> skipping'.format(cmd['target']))
            if cmd['debug']:
                pprint(self.interpreter.targets)
            return
        if cmd['debug']:
            pprint(target)

        # Utility function to get a list of the sources from a node
        def arg_list_from_node(n):
            args = []
            if isinstance(n, mparser.FunctionNode):
                args = list(n.args.arguments)
                if n.func_name in build_target_functions:
                    args.pop(0)
            elif isinstance(n, mparser.ArrayNode):
                args = n.args.arguments
            elif isinstance(n, mparser.ArgumentNode):
                args = n.arguments
            return args

        if cmd['operation'] == 'src_add':
            #################################
            ### Add sources to the target ###
            #################################
            node = None
            if target['sources']:
                node = target['sources'][0]
            else:
                node = target['node']
            assert(node is not None)

            # Generate the new String nodes
            to_append = []
            for i in cmd['sources']:
                mlog.log('  -- Adding source', mlog.green(i), 'at',
                         mlog.yellow('{}:{}'.format(os.path.join(node.subdir, environment.build_filename), node.lineno)))
                token = mparser.Token('string', node.subdir, 0, 0, 0, None, i)
                to_append += [mparser.StringNode(token)]

            # Append to the AST at the right place
            if isinstance(node, mparser.FunctionNode):
                node.args.arguments += to_append
            elif isinstance(node, mparser.ArrayNode):
                node.args.arguments += to_append
            elif isinstance(node, mparser.ArgumentNode):
                node.arguments += to_append

            # Mark the node as modified
            if node not in self.modefied_nodes:
                self.modefied_nodes += [node]
        elif cmd['operation'] == 'src_rm':
            ######################################
            ### Remove sources from the target ###
            ######################################
            # Helper to find the exact string node and its parent
            def find_node(src):
                for i in target['sources']:
                    for j in arg_list_from_node(i):
                        if isinstance(j, mparser.StringNode):
                            if j.value == src:
                                return i, j
                return None, None

            for i in cmd['sources']:
                # Try to find the node with the source string
                root, string_node = find_node(i)
                if root is None:
                    mlog.warning('  -- Unable to find source', mlog.green(i), 'in the target')
                    continue

                # Remove the found string node from the argument list
                arg_node = None
                if isinstance(root, mparser.FunctionNode):
                    arg_node = root.args
                if isinstance(root, mparser.ArrayNode):
                    arg_node = root.args
                if isinstance(root, mparser.ArgumentNode):
                    arg_node = root
                assert(arg_node is not None)
                mlog.log('  -- Removing source', mlog.green(i), 'from',
                         mlog.yellow('{}:{}'.format(os.path.join(string_node.subdir, environment.build_filename), string_node.lineno)))
                arg_node.arguments.remove(string_node)

                # Mark the node as modified
                if root not in self.modefied_nodes:
                    self.modefied_nodes += [root]
        elif cmd['operation'] == 'test':
            ######################################
            ### List all sources in the target ###
            ######################################
            src_list = []
            for i in target['sources']:
                for j in arg_list_from_node(i):
                    if isinstance(j, mparser.StringNode):
                        src_list += [j.value]
            test_data = {
                'name': target['name'],
                'sources': src_list
            }
            mlog.log('  !! target {}={}'.format(target['id'], json.dumps(test_data)))

    def process(self, cmd):
        if 'type' not in cmd:
            raise RewriterException('Command has no key "type"')
        if cmd['type'] not in self.functions:
            raise RewriterException('Unknown command "{}". Supported commands are: {}'
                                    .format(cmd['type'], list(self.functions.keys())))
        self.functions[cmd['type']](cmd)

def run(options):
    rewriter = Rewriter(options.sourcedir)
    rewriter.analyze_meson()
    if os.path.exists(options.command):
        with open(options.command, 'r') as fp:
            commands = json.load(fp)
    else:
        commands = json.loads(options.command)

    if not isinstance(commands, list):
        raise TypeError('Command is not a list')

    for i in commands:
        if not isinstance(i, object):
            raise TypeError('Command is not an object')
        rewriter.process(i)
    return 0
