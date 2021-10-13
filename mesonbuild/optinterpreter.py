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
import functools
import typing as T

from . import coredata
from . import mesonlib
from . import mparser
from . import mlog
from .interpreterbase import FeatureNew

if T.TYPE_CHECKING:
    from .interpreterbase import TV_func

class OptionException(mesonlib.MesonException):
    pass


def permitted_kwargs(permitted: T.Set[str]) -> T.Callable[..., T.Any]:
    """Function that validates kwargs for options."""
    def _wraps(func: 'TV_func') -> 'TV_func':
        @functools.wraps(func)
        def _inner(name: str, description: str, kwargs: T.Dict[str, T.Any]) -> T.Any:
            bad = [a for a in kwargs.keys() if a not in permitted]
            if bad:
                raise OptionException('Invalid kwargs for option "{}": "{}"'.format(
                    name, ' '.join(bad)))
            return func(description, kwargs)
        return T.cast('TV_func', _inner)
    return _wraps


optname_regex = re.compile('[^a-zA-Z0-9_-]')

@permitted_kwargs({'value', 'yield'})
def string_parser(description: str, kwargs: T.Dict[str, T.Any]) -> coredata.UserStringOption:
    return coredata.UserStringOption(description,
                                     kwargs.get('value', ''),
                                     kwargs.get('yield', coredata.default_yielding))

@permitted_kwargs({'value', 'yield'})
def boolean_parser(description: str, kwargs: T.Dict[str, T.Any]) -> coredata.UserBooleanOption:
    return coredata.UserBooleanOption(description,
                                      kwargs.get('value', True),
                                      kwargs.get('yield', coredata.default_yielding))

@permitted_kwargs({'value', 'yield', 'choices'})
def combo_parser(description: str, kwargs: T.Dict[str, T.Any]) -> coredata.UserComboOption:
    if 'choices' not in kwargs:
        raise OptionException('Combo option missing "choices" keyword.')
    choices = kwargs['choices']
    if not isinstance(choices, list):
        raise OptionException('Combo choices must be an array.')
    for i in choices:
        if not isinstance(i, str):
            raise OptionException('Combo choice elements must be strings.')
    return coredata.UserComboOption(description,
                                    choices,
                                    kwargs.get('value', choices[0]),
                                    kwargs.get('yield', coredata.default_yielding),)


@permitted_kwargs({'value', 'min', 'max', 'yield'})
def integer_parser(description: str, kwargs: T.Dict[str, T.Any]) -> coredata.UserIntegerOption:
    if 'value' not in kwargs:
        raise OptionException('Integer option must contain value argument.')
    inttuple = (kwargs.get('min', None), kwargs.get('max', None), kwargs['value'])
    return coredata.UserIntegerOption(description,
                                      inttuple,
                                      kwargs.get('yield', coredata.default_yielding))

# FIXME: Cannot use FeatureNew while parsing options because we parse it before
# reading options in project(). See func_project() in interpreter.py
#@FeatureNew('array type option()', '0.44.0')
@permitted_kwargs({'value', 'yield', 'choices'})
def string_array_parser(description: str, kwargs: T.Dict[str, T.Any]) -> coredata.UserArrayOption:
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
    return coredata.UserArrayOption(description,
                                    value,
                                    choices=choices,
                                    yielding=kwargs.get('yield', coredata.default_yielding))

@permitted_kwargs({'value', 'yield'})
def feature_parser(description: str, kwargs: T.Dict[str, T.Any]) -> coredata.UserFeatureOption:
    return coredata.UserFeatureOption(description,
                                      kwargs.get('value', 'auto'),
                                      yielding=kwargs.get('yield', coredata.default_yielding))

option_types = {'string': string_parser,
                'boolean': boolean_parser,
                'combo': combo_parser,
                'integer': integer_parser,
                'array': string_array_parser,
                'feature': feature_parser,
                } # type: T.Dict[str, T.Callable[[str, str, T.Dict[str, T.Any]], coredata.UserOption]]

class OptionInterpreter:
    def __init__(self, subproject: str) -> None:
        self.options: 'coredata.KeyedOptionDictType' = {}
        self.subproject = subproject

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
                self.evaluate_statement(cur)
            except mesonlib.MesonException as e:
                e.lineno = cur.lineno
                e.colno = cur.colno
                e.file = option_file
                raise e
            except Exception as e:
                raise mesonlib.MesonException(
                    str(e), lineno=cur.lineno, colno=cur.colno, file=option_file)

    def reduce_single(self, arg: T.Union[str, mparser.BaseNode]) -> T.Union[str, int, bool, T.Sequence[T.Union[str, int, bool]]]:
        if isinstance(arg, str):
            return arg
        elif isinstance(arg, (mparser.StringNode, mparser.BooleanNode,
                              mparser.NumberNode)):
            return arg.value
        elif isinstance(arg, mparser.ArrayNode):
            lr = [self.reduce_single(curarg) for curarg in arg.args.arguments]
            # mypy really struggles with recursive flattening, help it out
            return T.cast(T.Sequence[T.Union[str, int, bool]], lr)
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

    def reduce_arguments(self, args: mparser.ArgumentNode) -> T.Tuple[
            T.List[T.Union[str, int, bool, T.Sequence[T.Union[str, int, bool]]]],
            T.Dict[str, T.Union[str, int, bool, T.Sequence[T.Union[str, int, bool]]]]]:
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

        if len(posargs) != 1:
            raise OptionException('Option() must have one (and only one) positional argument')
        opt_name = posargs[0]
        if not isinstance(opt_name, str):
            raise OptionException('Positional argument must be a string.')
        if optname_regex.search(opt_name) is not None:
            raise OptionException('Option names can only contain letters, numbers or dashes.')
        key = mesonlib.OptionKey.from_string(opt_name).evolve(subproject=self.subproject)
        if not key.is_project():
            raise OptionException('Option name %s is reserved.' % opt_name)

        if 'yield' in kwargs:
            FeatureNew.single_use('option yield', '0.45.0', self.subproject)

        if 'type' not in kwargs:
            raise OptionException('Option call missing mandatory "type" keyword argument')
        opt_type = kwargs.pop('type')
        if not isinstance(opt_type, str):
            raise OptionException('option() type must be a string')
        if opt_type not in option_types:
            raise OptionException('Unknown type %s.' % opt_type)

        description = kwargs.pop('description', '')
        if not isinstance(description, str):
            raise OptionException('Option descriptions must be strings.')

        opt = option_types[opt_type](opt_name, description, kwargs)
        if opt.description == '':
            opt.description = opt_name
        self.options[key] = opt
