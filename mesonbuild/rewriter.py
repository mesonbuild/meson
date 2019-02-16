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

from .ast import IntrospectionInterpreter, build_target_functions, AstIDGenerator, AstIndentationGenerator, AstPrinter
from mesonbuild.mesonlib import MesonException
from . import mlog, mparser, environment
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

class MTypeBase:
    def __init__(self, node: mparser.BaseNode):
        if node is None:
            self.node = self._new_node()
        else:
            self.node = node
        self.node_type = None
        for i in self.supported_nodes():
            if isinstance(self.node, i):
                self.node_type = i

    def _new_node(self):
        # Overwrite in derived class
        return mparser.BaseNode()

    def can_modify(self):
        return self.node_type is not None

    def get_node(self):
        return self.node

    def supported_nodes(self):
        # Overwrite in derived class
        return []

    def set_value(self, value):
        # Overwrite in derived class
        mlog.warning('Cannot set the value of type', mlog.bold(type(self).__name__), '--> skipping')

    def add_value(self, value):
        # Overwrite in derived class
        mlog.warning('Cannot add a value of type', mlog.bold(type(self).__name__), '--> skipping')

    def remove_value(self, value):
        # Overwrite in derived class
        mlog.warning('Cannot remove a value of type', mlog.bold(type(self).__name__), '--> skipping')

class MTypeStr(MTypeBase):
    def __init__(self, node: mparser.BaseNode):
        super().__init__(node)

    def _new_node(self):
        return mparser.StringNode(mparser.Token('', '', 0, 0, 0, None, ''))

    def supported_nodes(self):
        return [mparser.StringNode]

    def set_value(self, value):
        self.node.value = str(value)

class MTypeBool(MTypeBase):
    def __init__(self, node: mparser.BaseNode):
        super().__init__(node)

    def _new_node(self):
        return mparser.StringNode(mparser.Token('', '', 0, 0, 0, None, False))

    def supported_nodes(self):
        return [mparser.BooleanNode]

    def set_value(self, value):
        self.node.value = bool(value)

class MTypeID(MTypeBase):
    def __init__(self, node: mparser.BaseNode):
        super().__init__(node)

    def _new_node(self):
        return mparser.StringNode(mparser.Token('', '', 0, 0, 0, None, ''))

    def supported_nodes(self):
        return [mparser.IdNode]

    def set_value(self, value):
        self.node.value = str(value)

class MTypeList(MTypeBase):
    def __init__(self, node: mparser.BaseNode):
        super().__init__(node)

    def _new_node(self):
        return mparser.ArrayNode(mparser.ArgumentNode(mparser.Token('', '', 0, 0, 0, None, '')), 0, 0)

    def _new_element_node(self, value):
        # Overwrite in derived class
        return mparser.BaseNode()

    def _ensure_array_node(self):
        if not isinstance(self.node, mparser.ArrayNode):
            tmp = self.node
            self.node = self._new_node()
            self.node.args.arguments += [tmp]

    def _check_is_equal(self, node, value):
        # Overwrite in derived class
        return False

    def get_node(self):
        if isinstance(self.node, mparser.ArrayNode):
            if len(self.node.args.arguments) == 1:
                return self.node.args.arguments[0]
        return self.node

    def supported_element_nodes(self):
        # Overwrite in derived class
        return []

    def supported_nodes(self):
        return [mparser.ArrayNode] + self.supported_element_nodes()

    def set_value(self, value):
        if not isinstance(value, list):
            value = [value]
        self._ensure_array_node()
        self.node.args.arguments = [] # Remove all current nodes
        for i in value:
            self.node.args.arguments += [self._new_element_node(i)]

    def add_value(self, value):
        if not isinstance(value, list):
            value = [value]
        self._ensure_array_node()
        for i in value:
            self.node.args.arguments += [self._new_element_node(i)]

    def remove_value(self, value):
        def check_remove_node(node):
            for j in value:
                if self._check_is_equal(i, j):
                    return True
            return False

        if not isinstance(value, list):
            value = [value]
        self._ensure_array_node()
        removed_list = []
        for i in self.node.args.arguments:
            if not check_remove_node(i):
                removed_list += [i]
        self.node.args.arguments = removed_list

class MtypeStrList(MTypeList):
    def __init__(self, node: mparser.BaseNode):
        super().__init__(node)

    def _new_element_node(self, value):
        return mparser.StringNode(mparser.Token('', '', 0, 0, 0, None, str(value)))

    def _check_is_equal(self, node, value):
        if isinstance(node, mparser.StringNode):
            return node.value == value
        return False

    def supported_element_nodes(self):
        return [mparser.StringNode]

class MTypeIDList(MTypeList):
    def __init__(self, node: mparser.BaseNode):
        super().__init__(node)

    def _new_element_node(self, value):
        return mparser.IdNode(mparser.Token('', '', 0, 0, 0, None, str(value)))

    def _check_is_equal(self, node, value):
        if isinstance(node, mparser.IdNode):
            return node.value == value
        return False

    def supported_element_nodes(self):
        return [mparser.IdNode]

rewriter_keys = {
    'kwargs': {
        'function': (str, None, None),
        'id': (str, None, None),
        'operation': (str, None, ['set', 'delete', 'add', 'remove', 'info']),
        'kwargs': (dict, {}, None)
    },
    'target': {
        'target': (str, None, None),
        'operation': (str, None, ['src_add', 'src_rm', 'info']),
        'sources': (list, [], None),
        'debug': (bool, False, None)
    }
}

rewriter_func_kwargs = {
    'dependency': {
        'language': MTypeStr,
        'method': MTypeStr,
        'native': MTypeBool,
        'not_found_message': MTypeStr,
        'required': MTypeBool,
        'static': MTypeBool,
        'version': MtypeStrList,
        'modules': MtypeStrList
    },
    'target': {
        'build_by_default': MTypeBool,
        'build_rpath': MTypeStr,
        'dependencies': MTypeIDList,
        'gui_app': MTypeBool,
        'link_with': MTypeIDList,
        'export_dynamic': MTypeBool,
        'implib': MTypeBool,
        'install': MTypeBool,
        'install_dir': MTypeStr,
        'install_rpath': MTypeStr,
        'pie': MTypeBool
    },
    'project': {
        'meson_version': MTypeStr,
        'license': MtypeStrList,
        'subproject_dir': MTypeStr,
        'version': MTypeStr
    }
}

class Rewriter:
    def __init__(self, sourcedir: str, generator: str = 'ninja'):
        self.sourcedir = sourcedir
        self.interpreter = IntrospectionInterpreter(sourcedir, '', generator)
        self.id_generator = AstIDGenerator()
        self.modefied_nodes = []
        self.functions = {
            'kwargs': self.process_kwargs,
            'target': self.process_target,
        }
        self.info_dump = None

    def analyze_meson(self):
        mlog.log('Analyzing meson file:', mlog.bold(os.path.join(self.sourcedir, environment.build_filename)))
        self.interpreter.analyze()
        mlog.log('  -- Project:', mlog.bold(self.interpreter.project_data['descriptive_name']))
        mlog.log('  -- Version:', mlog.cyan(self.interpreter.project_data['version']))
        self.interpreter.ast.accept(AstIndentationGenerator())
        self.interpreter.ast.accept(self.id_generator)

    def add_info(self, cmd_type: str, cmd_id: str, data: dict):
        if self.info_dump is None:
            self.info_dump = {}
        if cmd_type not in self.info_dump:
            self.info_dump[cmd_type] = {}
        self.info_dump[cmd_type][cmd_id] = data

    def print_info(self):
        if self.info_dump is None:
            return
        # Wrap the dump in magic strings
        print('!!==JSON DUMP: BEGIN==!!')
        print(json.dumps(self.info_dump, indent=2))
        print('!!==JSON DUMP: END==!!')

    def find_target(self, target: str):
        def check_list(name: str):
            for i in self.interpreter.targets:
                if name == i['name'] or name == i['id']:
                    return i
            return None

        tgt = check_list(target)
        if tgt is not None:
            return tgt

        # Check the assignments
        if target in self.interpreter.assignments:
            node = self.interpreter.assignments[target][0]
            if isinstance(node, mparser.FunctionNode):
                if node.func_name in ['executable', 'jar', 'library', 'shared_library', 'shared_module', 'static_library', 'both_libraries']:
                    name = self.interpreter.flatten_args(node.args)[0]
                    tgt = check_list(name)

        return tgt

    def find_dependency(self, dependency: str):
        def check_list(name: str):
            for i in self.interpreter.dependencies:
                if name == i['name']:
                    return i
            return None

        dep = check_list(dependency)
        if dep is not None:
            return dep

        # Check the assignments
        if dependency in self.interpreter.assignments:
            node = self.interpreter.assignments[dependency][0]
            if isinstance(node, mparser.FunctionNode):
                if node.func_name in ['dependency']:
                    name = self.interpreter.flatten_args(node.args)[0]
                    dep = check_list(name)

        return dep

    @RequiredKeys(rewriter_keys['kwargs'])
    def process_kwargs(self, cmd):
        mlog.log('Processing function type', mlog.bold(cmd['function']), 'with id', mlog.cyan("'" + cmd['id'] + "'"))
        if cmd['function'] not in rewriter_func_kwargs:
            mlog.error('Unknown function type {} --> skipping'.format(cmd['function']))
            return
        kwargs_def = rewriter_func_kwargs[cmd['function']]

        # Find the function node to modify
        node = None
        arg_node = None
        if cmd['function'] == 'project':
            node = self.interpreter.project_node
            arg_node = node.args
        elif cmd['function'] == 'target':
            tmp = self.find_target(cmd['id'])
            if tmp:
                node = tmp['node']
                arg_node = node.args
        elif cmd['function'] == 'dependency':
            tmp = self.find_dependency(cmd['id'])
            if tmp:
                node = tmp['node']
                arg_node = node.args
        if not node:
            mlog.error('Unable to find the function node')
        assert(isinstance(node, mparser.FunctionNode))
        assert(isinstance(arg_node, mparser.ArgumentNode))

        # Print kwargs info
        if cmd['operation'] == 'info':
            info_data = {}
            for key, val in arg_node.kwargs.items():
                info_data[key] = None
                if isinstance(val, mparser.ElementaryNode):
                    info_data[key] = val.value
                elif isinstance(val, mparser.ArrayNode):
                    data_list = []
                    for i in val.args.arguments:
                        element = None
                        if isinstance(i, mparser.ElementaryNode):
                            element = i.value
                        data_list += [element]
                    info_data[key] = data_list

            self.add_info('kwargs', '{}#{}'.format(cmd['function'], cmd['id']), info_data)
            return # Nothing else to do

        # Modify the kwargs
        num_changed = 0
        for key, val in cmd['kwargs'].items():
            if key not in kwargs_def:
                mlog.error('Cannot modify unknown kwarg --> skipping', mlog.bold(key))
                continue

            # Remove the key from the kwargs
            if cmd['operation'] == 'delete':
                if key in arg_node.kwargs:
                    mlog.log('  -- Deleting', mlog.bold(key), 'from the kwargs')
                    del arg_node.kwargs[key]
                    num_changed += 1
                else:
                    mlog.log('  -- Key', mlog.bold(key), 'is already deleted')
                continue

            if key not in arg_node.kwargs:
                arg_node.kwargs[key] = None
            modifyer = kwargs_def[key](arg_node.kwargs[key])
            if not modifyer.can_modify():
                mlog.log('  -- Skipping', mlog.bold(key), 'because it is to complex to modify')

            # Apply the operation
            val_str = str(val)
            if cmd['operation'] == 'set':
                mlog.log('  -- Setting', mlog.bold(key), 'to', mlog.yellow(val_str))
                modifyer.set_value(val)
            elif cmd['operation'] == 'add':
                mlog.log('  -- Adding', mlog.yellow(val_str), 'to', mlog.bold(key))
                modifyer.add_value(val)
            elif cmd['operation'] == 'remove':
                mlog.log('  -- Removing', mlog.yellow(val_str), 'from', mlog.bold(key))
                modifyer.remove_value(val)

            # Write back the result
            arg_node.kwargs[key] = modifyer.get_node()
            num_changed += 1

        if num_changed > 0 and node not in self.modefied_nodes:
            self.modefied_nodes += [node]

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

        elif cmd['operation'] == 'info':
            # List all sources in the target
            src_list = []
            for i in target['sources']:
                for j in arg_list_from_node(i):
                    if isinstance(j, mparser.StringNode):
                        src_list += [j.value]
            test_data = {
                'name': target['name'],
                'sources': src_list
            }
            self.add_info('target', target['id'], test_data)

    def process(self, cmd):
        if 'type' not in cmd:
            raise RewriterException('Command has no key "type"')
        if cmd['type'] not in self.functions:
            raise RewriterException('Unknown command "{}". Supported commands are: {}'
                                    .format(cmd['type'], list(self.functions.keys())))
        self.functions[cmd['type']](cmd)

    def apply_changes(self):
        assert(all(hasattr(x, 'lineno') and hasattr(x, 'colno') and hasattr(x, 'subdir') for x in self.modefied_nodes))
        assert(all(isinstance(x, (mparser.ArrayNode, mparser.FunctionNode)) for x in self.modefied_nodes))
        # Sort based on line and column in reversed order
        work_nodes = list(sorted(self.modefied_nodes, key=lambda x: x.lineno * 1000 + x.colno, reverse=True))

        # Generating the new replacement string
        str_list = []
        for i in work_nodes:
            printer = AstPrinter()
            i.accept(printer)
            printer.post_process()
            data = {
                'file': os.path.join(i.subdir, environment.build_filename),
                'str': printer.result.strip(),
                'node': i
            }
            str_list += [data]

        # Load build files
        files = {}
        for i in str_list:
            if i['file'] in files:
                continue
            fpath = os.path.realpath(os.path.join(self.sourcedir, i['file']))
            fdata = ''
            with open(fpath, 'r') as fp:
                fdata = fp.read()

            # Generate line offsets numbers
            m_lines = fdata.splitlines(True)
            offset = 0
            line_offsets = []
            for j in m_lines:
                line_offsets += [offset]
                offset += len(j)

            files[i['file']] = {
                'path': fpath,
                'raw': fdata,
                'offsets': line_offsets
            }

        # Replace in source code
        for i in str_list:
            offsets = files[i['file']]['offsets']
            raw = files[i['file']]['raw']
            node = i['node']
            line = node.lineno - 1
            col = node.colno
            start = offsets[line] + col
            end = start
            if isinstance(node, mparser.ArrayNode):
                if raw[end] != '[':
                    mlog.warning('Internal error: expected "[" at {}:{} but got "{}"'.format(line, col, raw[end]))
                    continue
                counter = 1
                while counter > 0:
                    end += 1
                    if raw[end] == '[':
                        counter += 1
                    elif raw[end] == ']':
                        counter -= 1
                end += 1
            elif isinstance(node, mparser.FunctionNode):
                while raw[end] != '(':
                    end += 1
                end += 1
                counter = 1
                while counter > 0:
                    end += 1
                    if raw[end] == '(':
                        counter += 1
                    elif raw[end] == ')':
                        counter -= 1
                end += 1
            raw = files[i['file']]['raw'] = raw[:start] + i['str'] + raw[end:]

        # Write the files back
        for key, val in files.items():
            mlog.log('Rewriting', mlog.yellow(key))
            with open(val['path'], 'w') as fp:
                fp.write(val['raw'])

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

    rewriter.apply_changes()
    rewriter.print_info()
    return 0
