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

from __future__ import annotations
import re
import typing as T

from . import coredata
from . import mesonlib
from . import mparser
from . import mlog
from .interpreterbase import FeatureNew, typed_pos_args, typed_kwargs, ContainerTypeInfo, KwargInfo
from .interpreter.type_checking import NoneType, in_set_validator
if T.TYPE_CHECKING:
    from .interpreterbase import TYPE_var, TYPE_kwargs
    from .interpreterbase import SubProject
    from typing_extensions import TypedDict, Literal

    FuncOptionArgs = TypedDict('FuncOptionArgs', {
        'type': str,
        'description': str,
        'yield': bool,
        'choices': T.Optional[T.List[str]],
        'value': object,
        'min': T.Optional[int],
        'max': T.Optional[int],
        'deprecated': T.Union[bool, str, T.Dict[str, str], T.List[str]],
        })

    _YieldArgs = TypedDict('_YieldArgs', {
        'yield': T.Optional[bool],
    })

    class StringArgs(_YieldArgs):
        value: str

    class BooleanArgs(_YieldArgs):
        value: bool

    class ComboArgs(_YieldArgs):
        value: str
        choices: T.List[str]

    class IntegerArgs(_YieldArgs):
        value: int
        min: T.Optional[int]
        max: T.Optional[int]

    class StringArrayArgs(_YieldArgs):
        value: str
        choices: T.List[str]

    class FeatureArgs(_YieldArgs):
        value: Literal['enabled', 'disabled', 'auto']
        choices: T.List[str]


class OptionException(mesonlib.MesonException):
    pass


optname_regex = re.compile('[^a-zA-Z0-9_-]')


class OptionInterpreter:
    def __init__(self, subproject: 'SubProject') -> None:
        self.options: 'coredata.MutableKeyedOptionDictType' = {}
        self.subproject = subproject
        self.option_types: T.Dict[str, T.Callable[..., coredata.UserOption]] = {
            'string': self.string_parser,
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
                  KwargInfo('type', str, required=True,
                            validator=in_set_validator({'string', 'boolean', 'integer', 'combo', 'array', 'feature'})),
                  KwargInfo('description', str, default=''),
                  KwargInfo('yield', bool, default=coredata.default_yielding, since='0.45.0'),
                  KwargInfo('choices', (ContainerTypeInfo(list, str), NoneType)),
                  KwargInfo('value', object),
                  KwargInfo('min', (int, NoneType)),
                  KwargInfo('max', (int, NoneType)),
                  KwargInfo('deprecated', (bool, str, ContainerTypeInfo(dict, str), ContainerTypeInfo(list, str)),
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
        parser = self.option_types[opt_type]
        description = kwargs['description'] or opt_name

        # Only keep in kwargs arguments that are used by option type's parser
        # because they use @permittedKwargs().
        opt = parser(description, kwargs)
        opt.deprecated = kwargs['deprecated']
        if isinstance(opt.deprecated, str):
            FeatureNew.single_use('String value to "deprecated" keyword argument', '0.63.0', self.subproject)
        if key in self.options:
            mlog.deprecation(f'Option {opt_name} already exists.')
        self.options[key] = opt

    @typed_kwargs(
        'string option',
        KwargInfo('value', str, default=''),
        allow_unknown=True,
    )
    def string_parser(self, description: str, kwargs: StringArgs) -> coredata.UserOption:
        return coredata.UserStringOption(description, kwargs['value'], kwargs['yield'])

    @typed_kwargs(
        'boolean option',
        KwargInfo('value', bool, default=True),
        allow_unknown=True,
    )
    def boolean_parser(self, description: str, kwargs: BooleanArgs) -> coredata.UserOption:
        return coredata.UserBooleanOption(description, kwargs['value'], kwargs['yield'])

    @typed_kwargs(
        'combo option',
        KwargInfo('value', (str, NoneType)),
        KwargInfo('choices', ContainerTypeInfo(list, str, allow_empty=False), required=True),
        allow_unknown=True,
    )
    def combo_parser(self, description: str, kwargs: ComboArgs) -> coredata.UserOption:
        choices = kwargs['choices']
        value = kwargs['value']
        if value is None:
            value = kwargs['choices'][0]
        return coredata.UserComboOption(description, choices, value, kwargs['yield'])

    @typed_kwargs(
        'integer option',
        KwargInfo('value', int),
        allow_unknown=True,
    )
    def integer_parser(self, description: str, kwargs: IntegerArgs) -> coredata.UserOption:
        value = kwargs['value']
        inttuple = (kwargs['min'], kwargs['max'], value)
        return coredata.UserIntegerOption(description, inttuple, kwargs['yield'])

    @typed_kwargs(
        'string array option',
        KwargInfo('value', ContainerTypeInfo(list, str), default=[]),
        KwargInfo('choices', ContainerTypeInfo(list, str), default=[]),
        allow_unknown=True,
    )
    def string_array_parser(self, description: str, kwargs: StringArrayArgs) -> coredata.UserOption:
        choices = kwargs['choices']
        value = kwargs['value'] or choices
        return coredata.UserArrayOption(description, value,
                                        choices=choices,
                                        yielding=kwargs['yield'])

    @typed_kwargs(
        'feature option',
        KwargInfo(
            'value',
            str,
            default='auto',
            validator=in_set_validator({'auto', 'enabled', 'disabled', 'true', 'false'}),
            since_values={'true': '1.1.0', 'false': '1.1.0'},
            convertor=lambda x: {'true': 'enabled', 'false': 'disabled'}.get(x, x),  # convert true and false, return other values unchanged
        ),
        allow_unknown=True,
    )
    def feature_parser(self, description: str, kwargs: FeatureArgs) -> coredata.UserOption:
        return coredata.UserFeatureOption(description, kwargs['value'], kwargs['yield'])
