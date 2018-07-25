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

import os, re
import functools

from . import mparser
from . import coredata
from . import mesonlib
from . import compilers

forbidden_option_names = coredata.get_builtin_options()
forbidden_prefixes = [lang + '_' for lang in compilers.all_languages] + ['b_', 'backend_']

def is_invalid_name(name):
    if name in forbidden_option_names:
        return True
    pref = name.split('_')[0] + '_'
    if pref in forbidden_prefixes:
        return True
    return False

class OptionException(mesonlib.MesonException):
    pass


def permitted_kwargs(permitted):
    """Function that validates kwargs for options."""
    def _wraps(func):
        @functools.wraps(func)
        def _inner(name, description, kwargs):
            bad = [a for a in kwargs.keys() if a not in permitted]
            if bad:
                raise OptionException('Invalid kwargs for option "{}": "{}"'.format(
                    name, ' '.join(bad)))
            return func(name, description, kwargs)
        return _inner
    return _wraps


optname_regex = re.compile('[^a-zA-Z0-9_-]')

@permitted_kwargs({'value', 'yield'})
def StringParser(name, description, kwargs):
    return coredata.UserStringOption(name,
                                     description,
                                     kwargs.get('value', ''),
                                     kwargs.get('choices', []),
                                     kwargs.get('yield', coredata.default_yielding))

@permitted_kwargs({'value', 'yield'})
def BooleanParser(name, description, kwargs):
    return coredata.UserBooleanOption(name, description,
                                      kwargs.get('value', True),
                                      kwargs.get('yield', coredata.default_yielding))

@permitted_kwargs({'value', 'yield', 'choices'})
def ComboParser(name, description, kwargs):
    if 'choices' not in kwargs:
        raise OptionException('Combo option missing "choices" keyword.')
    choices = kwargs['choices']
    if not isinstance(choices, list):
        raise OptionException('Combo choices must be an array.')
    for i in choices:
        if not isinstance(i, str):
            raise OptionException('Combo choice elements must be strings.')
    return coredata.UserComboOption(name,
                                    description,
                                    choices,
                                    kwargs.get('value', choices[0]),
                                    kwargs.get('yield', coredata.default_yielding),)


@permitted_kwargs({'value', 'min', 'max', 'yield'})
def IntegerParser(name, description, kwargs):
    if 'value' not in kwargs:
        raise OptionException('Integer option must contain value argument.')
    return coredata.UserIntegerOption(name,
                                      description,
                                      kwargs.get('min', None),
                                      kwargs.get('max', None),
                                      kwargs['value'],
                                      kwargs.get('yield', coredata.default_yielding))

# FIXME: Cannot use FeatureNew while parsing options because we parse it before
# reading options in project(). See func_project() in interpreter.py
#@FeatureNew('array type option()', '0.44.0')
@permitted_kwargs({'value', 'yield', 'choices'})
def string_array_parser(name, description, kwargs):
    if 'choices' in kwargs:
        choices = kwargs['choices']
        if not isinstance(choices, list):
            raise OptionException('Array choices must be an array.')
        for i in choices:
            if not isinstance(i, str):
                raise OptionException('Array choice elements must be strings.')
            value = kwargs.get('value', choices)
    else:
        choices = None
        value = kwargs.get('value', [])
    if not isinstance(value, list):
        raise OptionException('Array choices must be passed as an array.')
    return coredata.UserArrayOption(name,
                                    description,
                                    value,
                                    choices=choices,
                                    yielding=kwargs.get('yield', coredata.default_yielding))

@permitted_kwargs({'value', 'yield'})
def FeatureParser(name, description, kwargs):
    return coredata.UserFeatureOption(name,
                                      description,
                                      kwargs.get('value', 'auto'),
                                      yielding=kwargs.get('yield', coredata.default_yielding))

option_types = {'string': StringParser,
                'boolean': BooleanParser,
                'combo': ComboParser,
                'integer': IntegerParser,
                'array': string_array_parser,
                'feature': FeatureParser,
                }

class OptionInterpreter:
    def __init__(self, subproject):
        self.options = {}
        self.subproject = subproject

    def process(self, option_file):
        try:
            with open(option_file, 'r', encoding='utf8') as f:
                ast = mparser.Parser(f.read(), '').parse()
        except mesonlib.MesonException as me:
            me.file = option_file
            raise me
        if not isinstance(ast, mparser.CodeBlockNode):
            e = OptionException('Option file is malformed.')
            e.lineno = ast.lineno()
            raise e
        for cur in ast.lines:
            try:
                self.evaluate_statement(cur)
            except Exception as e:
                e.lineno = cur.lineno
                e.colno = cur.colno
                e.file = os.path.join('meson_options.txt')
                raise e

    def reduce_single(self, arg):
        if isinstance(arg, str):
            return arg
        elif isinstance(arg, (mparser.StringNode, mparser.BooleanNode,
                              mparser.NumberNode)):
            return arg.value
        elif isinstance(arg, mparser.ArrayNode):
            return [self.reduce_single(curarg) for curarg in arg.args.arguments]
        else:
            raise OptionException('Arguments may only be string, int, bool, or array of those.')

    def reduce_arguments(self, args):
        assert(isinstance(args, mparser.ArgumentNode))
        if args.incorrect_order():
            raise OptionException('All keyword arguments must be after positional arguments.')
        reduced_pos = [self.reduce_single(arg) for arg in args.arguments]
        reduced_kw = {}
        for key in args.kwargs.keys():
            if not isinstance(key, str):
                raise OptionException('Keyword argument name is not a string.')
            a = args.kwargs[key]
            reduced_kw[key] = self.reduce_single(a)
        return reduced_pos, reduced_kw

    def evaluate_statement(self, node):
        if not isinstance(node, mparser.FunctionNode):
            raise OptionException('Option file may only contain option definitions')
        func_name = node.func_name
        if func_name != 'option':
            raise OptionException('Only calls to option() are allowed in option files.')
        (posargs, kwargs) = self.reduce_arguments(node.args)

        # FIXME: Cannot use FeatureNew while parsing options because we parse
        # it before reading options in project(). See func_project() in
        # interpreter.py
        #if 'yield' in kwargs:
        #    FeatureNew('option yield', '0.45.0').use(self.subproject)

        if 'type' not in kwargs:
            raise OptionException('Option call missing mandatory "type" keyword argument')
        opt_type = kwargs.pop('type')
        if opt_type not in option_types:
            raise OptionException('Unknown type %s.' % opt_type)
        if len(posargs) != 1:
            raise OptionException('Option() must have one (and only one) positional argument')
        opt_name = posargs[0]
        if not isinstance(opt_name, str):
            raise OptionException('Positional argument must be a string.')
        if optname_regex.search(opt_name) is not None:
            raise OptionException('Option names can only contain letters, numbers or dashes.')
        if is_invalid_name(opt_name):
            raise OptionException('Option name %s is reserved.' % opt_name)
        if self.subproject != '':
            opt_name = self.subproject + ':' + opt_name
        opt = option_types[opt_type](opt_name, kwargs.pop('description', ''), kwargs)
        if opt.description == '':
            opt.description = opt_name
        self.options[opt_name] = opt
