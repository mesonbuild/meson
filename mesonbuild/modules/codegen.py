# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024-2025 Intel Corporation

from __future__ import annotations
import dataclasses
import os
import typing as T

from . import ExtensionModule, ModuleInfo
from ..build import CustomTarget, CustomTargetIndex, GeneratedList
from ..compilers.compilers import lang_suffixes
from ..interpreter.type_checking import NoneType
from ..interpreterbase import (
    ContainerTypeInfo, ObjectHolder, KwargInfo, typed_pos_args, typed_kwargs,
    noPosargs, noKwargs
)
from ..mesonlib import File, MesonException, Popen_safe, version_compare
from ..programs import ExternalProgram
from ..utils.core import HoldableObject
from .. import mlog

if T.TYPE_CHECKING:
    from typing_extensions import Literal, TypeAlias, TypedDict

    from . import ModuleState
    from ..build import Executable
    from ..interpreter import Interpreter
    from ..interpreterbase import TYPE_var, TYPE_kwargs
    from ..programs import OverrideProgram
    from .._typing import ImmutableListProtocol

    Program: TypeAlias = T.Union[Executable, ExternalProgram, OverrideProgram]
    LexImpls = Literal['lex', 'flex', 'reflex', 'win_flex']
    YaccImpls = Literal['yacc', 'byacc', 'bison', 'win_bison']

    class LexGenerateKwargs(TypedDict):

        args: T.List[str]
        source: T.Optional[str]
        header: T.Optional[str]
        table: T.Optional[str]
        plainname: bool

    class FindLexKwargs(TypedDict):

        lex_version: T.List[str]
        flex_version: T.List[str]
        reflex_version: T.List[str]
        win_flex_version: T.List[str]
        implementations: T.List[LexImpls]

    class YaccGenerateKWargs(TypedDict):

        args: T.List[str]
        source: T.Optional[str]
        header: T.Optional[str]
        locations: T.Optional[str]
        plainname: bool

    class FindYaccKwargs(TypedDict):

        yacc_version: T.List[str]
        byacc_version: T.List[str]
        bison_version: T.List[str]
        win_bison_version: T.List[str]
        implementations: T.List[YaccImpls]


def is_subset_validator(choices: T.Set[str]) -> T.Callable[[T.List[str]], T.Optional[str]]:

    def inner(check: T.List[str]) -> T.Optional[str]:
        if not set(check).issubset(choices):
            invalid = ', '.join(sorted(set(check).difference(choices)))
            valid = ', '.join(sorted(choices))
            return f"valid members are '{valid}', not '{invalid}'"
        return None

    return inner


@dataclasses.dataclass
class _CodeGenerator(HoldableObject):

    name: str
    program: Program
    arguments: ImmutableListProtocol[str] = dataclasses.field(default_factory=list)

    def command(self) -> T.List[T.Union[Program, str]]:
        return (T.cast('T.List[T.Union[Program, str]]', [self.program]) +
                T.cast('T.List[T.Union[Program, str]]', self.arguments))


@dataclasses.dataclass
class LexGenerator(_CodeGenerator):
    pass


class LexHolder(ObjectHolder[LexGenerator]):

    def __init__(self, obj: LexGenerator, interpreter: Interpreter):
        super().__init__(obj, interpreter)
        self.methods.update({
            'generate': self.generate_method,
            'implementation': self.implementation_method,
        })

    @noPosargs
    @noKwargs
    def implementation_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.held_object.name

    @typed_pos_args('codegen.lex.generate', (str, File, GeneratedList, CustomTarget, CustomTargetIndex))
    @typed_kwargs(
        'codegen.lex.generate',
        KwargInfo('args', ContainerTypeInfo(list, str), default=[], listify=True),
        KwargInfo('source', (str, NoneType)),
        KwargInfo('header', (str, NoneType)),
        KwargInfo('table', (str, NoneType)),
        KwargInfo('plainname', bool, default=False),
    )
    def generate_method(self, args: T.Tuple[T.Union[str, File, GeneratedList, CustomTarget, CustomTargetIndex]], kwargs: LexGenerateKwargs) -> CustomTarget:
        input = self.interpreter.source_strings_to_files([args[0]])[0]
        if isinstance(input, File):
            is_cpp = input.endswith(".ll")
            name = os.path.splitext(input.fname)[0]
        else:
            gen_input = input.get_outputs()
            if len(gen_input) != 1:
                raise MesonException('codegen.lex.generate: generated type inputs must have exactly one output, index into them to select the correct input')
            is_cpp = gen_input[0].endswith('.ll')
            name = os.path.splitext(gen_input[0])[0]
        name = os.path.basename(name)

        # If an explicit source was given, use that to determine whether the
        # user expects this to be a C or C++ source.
        if kwargs['source'] is not None:
            ext = kwargs['source'].rsplit('.', 1)[1]
            is_cpp = ext in lang_suffixes['cpp']

        # Flex uses FlexLexer.h for C++ code
        if is_cpp and self.held_object.name in {'flex', 'win_flex'}:
            try:
                found = self.interpreter.environment.coredata.compilers.host['cpp'].has_header('FlexLexer.h', '', self.interpreter.environment)
                if not found[0]:
                    raise MesonException('Could not find FlexLexer.h, which is required for Flex with C++')
            except KeyError:
                raise MesonException("Could not find a C++ compiler to search for FlexLexer.h")

        if kwargs['source'] is None:
            outputs = ['@{}@.{}'.format(
                'PLAINNAME' if kwargs['plainname'] else 'BASENAME',
                'cpp' if is_cpp else 'c')]
        else:
            outputs = [kwargs['source']]

        command = self.held_object.command()
        if kwargs['header'] is not None:
            outputs.append(kwargs['header'])
            command.append(f'--header-file=@OUTPUT{len(outputs) - 1}@')
        if kwargs['table'] is not None:
            outputs.append(kwargs['table'])
            command.append(f'--tables-file=@OUTPUT{len(outputs) - 1}@')
        command.extend(kwargs['args'])
        # Flex, at least, seems to require that input be the last argument given
        command.append('@INPUT@')

        target = CustomTarget(
            f'codegen-lex-{name}',
            self.interpreter.subdir,
            self.interpreter.subproject,
            self.interpreter.environment,
            command,
            [input],
            outputs,
            backend=self.interpreter.backend,
            description='Generating lexer {{}} with {}'.format(self.held_object.name),
        )
        self.interpreter.add_target(target.name, target)

        return target


@dataclasses.dataclass
class YaccGenerator(_CodeGenerator):
    pass


class YaccHolder(ObjectHolder[YaccGenerator]):

    def __init__(self, obj: YaccGenerator, interpreter: Interpreter):
        super().__init__(obj, interpreter)
        self.methods.update({
            'generate': self.generate_method,
            'implementation': self.implementation_method,
        })

    @noPosargs
    @noKwargs
    def implementation_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.held_object.name

    @typed_pos_args('codegen.yacc.generate', (str, File, GeneratedList, CustomTarget, CustomTargetIndex))
    @typed_kwargs(
        'codegen.yacc.generate',
        KwargInfo('args', ContainerTypeInfo(list, str), default=[], listify=True),
        KwargInfo('source', (str, NoneType)),
        KwargInfo('header', (str, NoneType)),
        KwargInfo('locations', (str, NoneType)),
        KwargInfo('plainname', bool, default=False),
    )
    def generate_method(self, args: T.Tuple[T.Union[str, File, CustomTarget, CustomTargetIndex, GeneratedList]], kwargs: YaccGenerateKWargs) -> CustomTarget:
        input = self.interpreter.source_strings_to_files([args[0]])[0]
        if isinstance(input, File):
            is_cpp = input.endswith(".yy")
            name = os.path.splitext(input.fname)[0]
        else:
            gen_input = input.get_outputs()
            if len(gen_input) != 1:
                raise MesonException('codegen.lex.generate: generated type inputs must have exactly one output, index into them to select the correct input')
            is_cpp = gen_input[0].endswith('.yy')
            name = os.path.splitext(gen_input[0])[0]
        name = os.path.basename(name)

        command = self.held_object.command()
        command.extend(kwargs['args'])

        source_ext = 'cpp' if is_cpp else 'c'
        header_ext = 'hpp' if is_cpp else 'h'

        base = '@PLAINNAME@' if kwargs['plainname'] else '@BASENAME@'
        outputs: T.List[str] = []
        outputs.append(f'{base}.{source_ext}' if kwargs['source'] is None else kwargs['source'])
        outputs.append(f'{base}.{header_ext}' if kwargs['header'] is None else kwargs['header'])
        if kwargs['locations'] is not None:
            outputs.append(kwargs['locations'])

        target = CustomTarget(
            f'codegen-yacc-{name}',
            self.interpreter.subdir,
            self.interpreter.subproject,
            self.interpreter.environment,
            command,
            [input],
            outputs,
            backend=self.interpreter.backend,
            description='Generating parser {{}} with {}'.format(self.held_object.name),
        )
        self.interpreter.add_target(target.name, target)
        return target


class CodeGenModule(ExtensionModule):

    """Module with helpers for codegen wrappers."""

    INFO = ModuleInfo('codegen', '1.9.0', unstable=True)

    def __init__(self, interpreter: Interpreter) -> None:
        super().__init__(interpreter)
        self.methods.update({
            'lex': self.lex_method,
            'yacc': self.yacc_method,
        })

    def __find_lex(self, state: ModuleState,
                   lex_version: T.Optional[T.List[str]] = None,
                   flex_version: T.Optional[T.List[str]] = None,
                   reflex_version: T.Optional[T.List[str]] = None,
                   win_flex_version: T.Optional[T.List[str]] = None,
                   implementations: T.Optional[T.List[LexImpls]] = None) -> LexGenerator:
        names: T.List[LexImpls] = []
        if implementations:
            names = implementations
        else:
            assert state.environment.machines.host is not None, 'for mypy'
            if state.environment.machines.host.system == 'windows':
                names.append('win_flex')
            names.extend(['flex', 'reflex', 'lex'])

        versions: T.Mapping[str, T.List[str]] = {
            'lex': lex_version or [],
            'flex': flex_version or [],
            'reflex': reflex_version or [],
            'win_flex': win_flex_version or [],
        }

        for name in names:
            bin = state.find_program(name, wanted=versions[name], required=name == names[-1])
            if bin.found():
                # If you're building reflex as a subproject, we consider that you
                # know what you're doing.
                if name == 'reflex' and isinstance(bin, ExternalProgram):
                    # there are potentially 3 programs called "reflex":
                    # 1. https://invisible-island.net/reflex/, an alternate fork
                    #    of the original flex, this is supported
                    # 2. https://www.genivia.com/doc/reflex/html/, an
                    #    alternative implementation for generating C++ scanners.
                    #    Not supported
                    # 3. https://github.com/cespare/reflex, which is not a lex
                    #    implementation at all, but a file watcher
                    _, out, err = Popen_safe(bin.get_command() + ['--version'])
                    if 'unknown flag: --version' in err:
                        mlog.debug('Skipping cespare/reflex, which is not a lexer and is not supported')
                        continue
                    if 'Written by Robert van Engelen' in out:
                        mlog.debug('Skipping RE/flex, which is not compatible with POSIX lex.')
                        continue
                break
        else:
            raise MesonException.from_node(
                'Could not find a lex implementation. Tried: ', ", ".join(names),
                node=state.current_node)

        args: T.List[str] = []
        if bin.name == 'win_flex':
            args.append('--wincompat')
        args.extend(['-o', '@OUTPUT0@'])
        return LexGenerator(name, bin, T.cast('ImmutableListProtocol[str]', args))

    @noPosargs
    @typed_kwargs(
        'codegen.lex',
        KwargInfo('lex_version', ContainerTypeInfo(list, str), default=[], listify=True),
        KwargInfo('flex_version', ContainerTypeInfo(list, str), default=[], listify=True),
        KwargInfo('reflex_version', ContainerTypeInfo(list, str), default=[], listify=True),
        KwargInfo('win_flex_version', ContainerTypeInfo(list, str), default=[], listify=True),
        KwargInfo(
            'implementations',
            ContainerTypeInfo(list, str),
            default=[],
            listify=True,
            validator=is_subset_validator({'lex', 'flex', 'reflex', 'win_flex'})
        ),
    )
    def lex_method(self, state: ModuleState, args: T.Tuple, kwargs: FindLexKwargs) -> LexGenerator:
        return self.__find_lex(state, **kwargs)

    def __find_yacc(self, state: ModuleState,
                    yacc_version: T.Optional[T.List[str]] = None,
                    byacc_version: T.Optional[T.List[str]] = None,
                    bison_version: T.Optional[T.List[str]] = None,
                    win_bison_version: T.Optional[T.List[str]] = None,
                    implementations: T.Optional[T.List[YaccImpls]] = None) -> YaccGenerator:
        names: T.List[YaccImpls]
        if implementations:
            names = implementations
        else:
            assert state.environment.machines.host is not None, 'for mypy'
            if state.environment.machines.host.system == 'windows':
                names = ['win_bison', 'bison', 'yacc']
            else:
                names = ['bison', 'byacc', 'yacc']

        versions: T.Mapping[YaccImpls, T.List[str]] = {
            'yacc': yacc_version or [],
            'byacc': byacc_version or [],
            'bison': bison_version or [],
            'win_bison': win_bison_version or [],
        }

        for name in names:
            bin = state.find_program(name, wanted=versions[name], required=name == names[-1])
            if bin.found():
                break
        else:
            raise MesonException.from_node(
                'Could not find a yacc implementation. Tried: ', ", ".join(names),
                node=state.current_node)

        args: T.List[str] = ['@INPUT@', '-o', '@OUTPUT0@']
        # TODO: Determine if "yacc" is "bison" or "byacc"

        impl = T.cast('YaccImpls', bin.name)
        if impl == 'yacc' and isinstance(bin, ExternalProgram):
            _, out, _ = Popen_safe(bin.get_command() + ['--version'])
            if 'GNU Bison' in out:
                impl = 'bison'
            elif out.startswith('yacc - 2'):
                impl = 'byacc'

        if impl in {'bison', 'win_bison'}:
            args.append('--defines=@OUTPUT1@')
            if isinstance(bin, ExternalProgram) and version_compare(bin.get_version(), '>= 3.4'):
                args.append('--color=always')
        elif impl == 'byacc':
            args.extend(['-H', '@OUTPUT1@'])
        else:
            mlog.warning('This yacc does not appear to be bison or byacc, the '
                         'POSIX specification does not require that header '
                         'output location be configurable, and may not work.',
                         fatal=False)
            args.append('-H')
        return YaccGenerator(name, bin, T.cast('ImmutableListProtocol[str]', args))

    @noPosargs
    @typed_kwargs(
        'codegen.yacc',
        KwargInfo('yacc_version', ContainerTypeInfo(list, str), default=[], listify=True),
        KwargInfo('byacc_version', ContainerTypeInfo(list, str), default=[], listify=True),
        KwargInfo('bison_version', ContainerTypeInfo(list, str), default=[], listify=True),
        KwargInfo('win_bison_version', ContainerTypeInfo(list, str), default=[], listify=True),
        KwargInfo(
            'implementations',
            ContainerTypeInfo(list, str),
            default=[],
            listify=True,
            validator=is_subset_validator({'yacc', 'byacc', 'bison', 'win_bison'})
        ),
    )
    def yacc_method(self, state: ModuleState, args: T.Tuple, kwargs: FindYaccKwargs) -> YaccGenerator:
        return self.__find_yacc(state, **kwargs)


def initialize(interpreter: Interpreter) -> CodeGenModule:
    interpreter.append_holder_map(LexGenerator, LexHolder)
    interpreter.append_holder_map(YaccGenerator, YaccHolder)
    return CodeGenModule(interpreter)
