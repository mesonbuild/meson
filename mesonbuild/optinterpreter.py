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

import re
import typing as T

from . import coredata
from . import mesonlib
from . import mparser
from . import mlog
from .interpreterbase import FeatureNew, typed_pos_args, typed_kwargs, ContainerTypeInfo, KwargInfo, permittedKwargs
if T.TYPE_CHECKING:
    from .interpreterbase import TYPE_var, TYPE_kwargs
    from .interpreterbase import SubProject
    from typing_extensions import TypedDict
    FuncOptionArgs = TypedDict('FuncOptionArgs', {
        'type': str,
        'description': str,
        'yield': bool,
        'choices': T.Optional[T.List[str]],
        'value': object,
        'min': T.Optional[int],
        'max': T.Optional[int],
        'deprecated': T.Union[bool, T.Dict[str, str], T.List[str]],
        })
    ParserArgs = TypedDict('ParserArgs', {
        'yield': bool,
        'choices': T.Optional[T.List[str]],
        'value': object,
        'min': T.Optional[int],
        'max': T.Optional[int],
        })


class OptionException(mesonlib.MesonException):
    pass


optname_regex = re.compile('[^a-zA-Z0-9_-]')


class OptionInterpreter:
    def __init__(self, subproject: 'SubProject') -> None:
        self.options: 'coredata.KeyedOptionDictType' = {}
        self.subproject = subproject
        self.option_types = {'string': self.string_parser,
                             'boolean': self.boolean_parser,
                             'combo': self.combo_parser,
                             'integer': self.integer_parser,
                             'array': self.string_array_parser,
                             'feature': self.feature_parser,
                             }

    def process(self, option_file: str) -> None:
        try:
            with open(option_file, encoding='utf-8') as f:
                ast = mparser.Parser(f.read(), option_file).parse()
        except mesonlib.MesonException as me:
            me.file = option_file
            raise me
        if not isinstance(ast, mparser.CodeBlockNode):
            e = OptionException('Option file is malformed.')
            e.lineno = ast.lineno()
            e.file = option_file
            raise e
        for cur in ast.lines:
            try:
                self.current_node = cur
                self.evaluate_statement(cur)
            except mesonlib.MesonException as e:
                e.lineno = cur.lineno
                e.colno = cur.colno
                e.file = option_file
                raise e
            except Exception as e:
                raise mesonlib.MesonException(
                    str(e), lineno=cur.lineno, colno=cur.colno, file=option_file)

    def reduce_single(self, arg: T.Union[str, mparser.BaseNode]) -> 'TYPE_var':
        if isinstance(arg, str):
            return arg
        elif isinstance(arg, (mparser.StringNode, mparser.BooleanNode,
                              mparser.NumberNode)):
            return arg.value
        elif isinstance(arg, mparser.ArrayNode):
            return [self.reduce_single(curarg) for curarg in arg.args.arguments]
        elif isinstance(arg, mparser.DictNode):
            d = {}
            for k, v in arg.args.kwargs.items():
                if not isinstance(k, mparser.StringNode):
                    raise OptionException('Dictionary keys must be a string literal')
                d[k.value] = self.reduce_single(v)
            return d
        elif isinstance(arg, mparser.UMinusNode):
            res = self.reduce_single(arg.value)
            if not isinstance(res, (int, float)):
                raise OptionException('Token after "-" is not a number')
            FeatureNew.single_use('negative numbers in meson_options.txt', '0.54.1', self.subproject)
            return -res
        elif isinstance(arg, mparser.NotNode):
            res = self.reduce_single(arg.value)
            if not isinstance(res, bool):
                raise OptionException('Token after "not" is not a a boolean')
            FeatureNew.single_use('negation ("not") in meson_options.txt', '0.54.1', self.subproject)
            return not res
        elif isinstance(arg, mparser.ArithmeticNode):
            l = self.reduce_single(arg.left)
            r = self.reduce_single(arg.right)
            if not (arg.operation == 'add' and isinstance(l, str) and isinstance(r, str)):
                raise OptionException('Only string concatenation with the "+" operator is allowed')
            FeatureNew.single_use('string concatenation in meson_options.txt', '0.55.0', self.subproject)
            return l + r
        else:
            raise OptionException('Arguments may only be string, int, bool, or array of those.')

    def reduce_arguments(self, args: mparser.ArgumentNode) -> T.Tuple['TYPE_var', 'TYPE_kwargs']:
        if args.incorrect_order():
            raise OptionException('All keyword arguments must be after positional arguments.')
        reduced_pos = [self.reduce_single(arg) for arg in args.arguments]
        reduced_kw = {}
        for key in args.kwargs.keys():
            if not isinstance(key, mparser.IdNode):
                raise OptionException('Keyword argument name is not a string.')
            a = args.kwargs[key]
            reduced_kw[key.value] = self.reduce_single(a)
        return reduced_pos, reduced_kw

    def evaluate_statement(self, node: mparser.BaseNode) -> None:
        if not isinstance(node, mparser.FunctionNode):
            raise OptionException('Option file may only contain option definitions')
        func_name = node.func_name
        if func_name != 'option':
            raise OptionException('Only calls to option() are allowed in option files.')
        (posargs, kwargs) = self.reduce_arguments(node.args)
        self.func_option(posargs, kwargs)

    @typed_kwargs('option',
                  KwargInfo('type', str, required=True),
                  KwargInfo('description', str, default=''),
                  KwargInfo('yield', bool, default=coredata.default_yielding, since='0.45.0'),
                  KwargInfo('choices', (ContainerTypeInfo(list, str), type(None))),
                  KwargInfo('value', object),
                  KwargInfo('min', (int, type(None))),
                  KwargInfo('max', (int, type(None))),
                  KwargInfo('deprecated', (bool, ContainerTypeInfo(dict, str), ContainerTypeInfo(list, str)),
                            default=False, since='0.60.0')
                  )
    @typed_pos_args('option', str)
    def func_option(self, args: T.Tuple[str], kwargs: 'FuncOptionArgs') -> None:
        opt_name = args[0]
        if optname_regex.search(opt_name) is not None:
            raise OptionException('Option names can only contain letters, numbers or dashes.')
        key = mesonlib.OptionKey.from_string(opt_name).evolve(subproject=self.subproject)
        if not key.is_project():
            raise OptionException('Option name %s is reserved.' % opt_name)

        opt_type = kwargs['type']
        parser = self.option_types.get(opt_type)
        if not parser:
            raise OptionException(f'Unknown type {opt_type}.')
        description = kwargs['description'] or opt_name

        # Only keep in kwargs arguments that are used by option type's parser
        # because they use @permittedKwargs().
        known_parser_kwargs = {'value', 'choices', 'yield', 'min', 'max'}
        parser_kwargs = {k: v for k, v in kwargs.items() if k in known_parser_kwargs and v is not None}
        opt = parser(description, T.cast('ParserArgs', parser_kwargs))
        opt.deprecated = kwargs['deprecated']

        if key in self.options:
            mlog.deprecation(f'Option {opt_name} already exists.')
        self.options[key] = opt

    @permittedKwargs({'value', 'yield'})
    def string_parser(self, description: str, kwargs: 'ParserArgs') -> coredata.UserOption:
        value = kwargs.get('value', '')
        return coredata.UserStringOption(description, value, kwargs['yield'])

    @permittedKwargs({'value', 'yield'})
    def boolean_parser(self, description: str, kwargs: 'ParserArgs') -> coredata.UserOption:
        value = kwargs.get('value', True)
        return coredata.UserBooleanOption(description, value, kwargs['yield'])

    @permittedKwargs({'value', 'yield', 'choices'})
    def combo_parser(self, description: str, kwargs: 'ParserArgs') -> coredata.UserOption:
        choices = kwargs.get('choices')
        if not choices:
            raise OptionException('Combo option missing "choices" keyword.')
        value = kwargs.get('value', choices[0])
        return coredata.UserComboOption(description, choices, value, kwargs['yield'])

    @permittedKwargs({'value', 'min', 'max', 'yield'})
    def integer_parser(self, description: str, kwargs: 'ParserArgs') -> coredata.UserOption:
        value = kwargs.get('value')
        if value is None:
            raise OptionException('Integer option must contain value argument.')
        inttuple = (kwargs.get('min'), kwargs.get('max'), value)
        return coredata.UserIntegerOption(description, inttuple, kwargs['yield'])

    @permittedKwargs({'value', 'yield', 'choices'})
    def string_array_parser(self, description: str, kwargs: 'ParserArgs') -> coredata.UserOption:
        choices = kwargs.get('choices', [])
        value = kwargs.get('value', choices)
        if not isinstance(value, list):
            raise OptionException('Array choices must be passed as an array.')
        return coredata.UserArrayOption(description, value,
                                        choices=choices,
                                        yielding=kwargs['yield'])

    @permittedKwargs({'value', 'yield'})
    def feature_parser(self, description: str, kwargs: 'ParserArgs') -> coredata.UserOption:
        value = kwargs.get('value', 'auto')
        return coredata.UserFeatureOption(description, value, kwargs['yield'])
