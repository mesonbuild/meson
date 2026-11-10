# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024-2025 Intel Corporation

from __future__ import annotations
import dataclasses
import itertools
import os
import typing as T

from . import ExtensionModule, ModuleInfo, ModuleState
from ..build import CustomTarget, CustomTargetIndex, GeneratedList, IncludeDirs, LocalProgram
from ..compilers.compilers import lang_suffixes
from ..dependencies import Dependency, InternalDependency
from ..interpreter.decorators import apply_machine_map
from ..interpreter.interpreterobjects import extract_required_kwarg
from ..interpreter.type_checking import (
    NoneType, REQUIRED_KW, DISABLER_KW, NATIVE_KW, INCLUDE_DIRECTORIES, INSTALL_KW, INSTALL_DIR_KW,
    in_set_validator,
)
from ..interpreterbase import (
    ContainerTypeInfo, ObjectHolder, KwargInfo, TypedArgs,
    disablerIfNotFound, InterpreterObject, PosArgInfo, VarArgInfo,
    FeatureNew,
)
from ..mesonlib import (
    File, OrderedSet, MachineChoice, MesonException, MesonBugException, Popen_safe,
    is_parent_path, relpath, version_compare,
)
from ..programs import Program, ExternalProgram, NonExistingExternalProgram
from ..utils.core import HoldableObject
from .. import mlog

if T.TYPE_CHECKING:
    from typing_extensions import Literal, TypedDict

    from .._typing import ImmutableListProtocol
    from ..interpreter import Interpreter
    from ..interpreter.kwargs import ExtractRequired, TargetDepends
    from ..interpreterbase import TYPE_var, TYPE_kwargs
    from ..programs import CommandList

    LexImpls = Literal['lex', 'flex', 'reflex', 'win_flex']
    YaccImpls = Literal['yacc', 'byacc', 'bison', 'win_bison']

    class LexGenerateKwargs(TypedDict):

        args: T.List[str]
        source: T.Optional[str]
        header: T.Optional[str]
        table: T.Optional[str]
        plainname: bool

    class FindLexKwargs(ExtractRequired):

        lex_version: T.List[str]
        flex_version: T.List[str]
        reflex_version: T.List[str]
        win_flex_version: T.List[str]
        implementations: T.List[LexImpls]
        native: MachineChoice

    class YaccGenerateKWargs(TypedDict):

        args: T.List[str]
        source: T.Optional[str]
        header: T.Optional[str]
        locations: T.Optional[str]
        plainname: bool

    class FindYaccKwargs(ExtractRequired):

        yacc_version: T.List[str]
        byacc_version: T.List[str]
        bison_version: T.List[str]
        win_bison_version: T.List[str]
        implementations: T.List[YaccImpls]
        native: MachineChoice

    class ProtocGenerateKwargs(TypedDict):

        language: str
        import_dirs: list[IncludeDirs | str]
        imports: list[ProtocOutput]
        args: list[str]
        install: bool
        install_dir: str | None
        grpc: bool | None

    class FindProtocKwargs(ExtractRequired):

        dependency: Dependency | None
        grpc_dependency: Dependency | None
        import_dirs: list[IncludeDirs | str]
        version: list[str]
        args: list[str]
        native: MachineChoice


_IMPORT_DIRS_KW = INCLUDE_DIRECTORIES.evolve(name='import_dirs')
_SRC_PARG = PosArgInfo((str, File, GeneratedList, CustomTarget, CustomTargetIndex))

def _describe_proto_file(f: File | CustomTargetIndex) -> str:
    if isinstance(f, CustomTargetIndex):
        kind = 'custom target'
        name = f.get_filename()
    else:
        kind = 'generated' if f.is_built else 'source'
        name = f.relative_name()
    return f'{kind} file {name!r}'


def _validate_protoc_source(value: str | File | CustomTarget | CustomTargetIndex) -> str | None:
    if isinstance(value, CustomTargetIndex):
        if not isinstance(value.target, CustomTarget):
            return 'comes from a CompileTarget. It cannot be used as protoc source.'
    return None


def _protoc_plugin_path(plugin: Program) -> str:
    """Path of a protoc plugin, for use inside a `--plugin=NAME=PATH` argument.

    The path is embedded in a larger argument, so the program cannot be given
    to the command as is; the caller must also add the plugin to the target
    dependencies.
    """
    if isinstance(plugin, LocalProgram) and not isinstance(plugin.program, ExternalProgram):
        target = plugin.program
        return os.path.join('@BUILD_ROOT@', target.get_builddir(), target.get_filename())
    command = plugin.get_command()
    if len(command) != 1:
        raise MesonException(
            f'protoc plugin {plugin.name!r} must be a single executable, '
            f'but its command is {" ".join(command)!r}.')
    return command[0]


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
    for_machine: MachineChoice
    arguments: ImmutableListProtocol[str] = dataclasses.field(default_factory=list)

    def command(self) -> CommandList:
        return T.cast('CommandList', [self.program]) + T.cast('CommandList', self.arguments)

    def found(self) -> bool:
        return self.program.found()


@dataclasses.dataclass
class LexGenerator(_CodeGenerator):
    pass


class LexHolder(ObjectHolder[LexGenerator]):

    @TypedArgs('codegen.lex.implementation')
    @InterpreterObject.method('implementation')
    def implementation_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.held_object.name

    @TypedArgs('codegen.lex.found')
    @InterpreterObject.method('found')
    def found_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> bool:
        return self.held_object.found()

    @TypedArgs(
        'codegen.lex.generate',
        pos_types=[_SRC_PARG],
        kw_types=[
            KwargInfo('args', ContainerTypeInfo(list, str), default=[], listify=True),
            KwargInfo('source', (str, NoneType)),
            KwargInfo('header', (str, NoneType)),
            KwargInfo('table', (str, NoneType)),
            KwargInfo('plainname', bool, default=False),
        ],
    )
    @InterpreterObject.method('generate')
    def generate_method(self, args: T.Tuple[T.Union[str, File, GeneratedList, CustomTarget, CustomTargetIndex]], kwargs: LexGenerateKwargs) -> CustomTarget:
        if not self.held_object.found():
            raise MesonException('Attempted to call generate without finding a lex implementation')

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
        for_machine = self.held_object.for_machine
        if is_cpp and self.held_object.name in {'flex', 'win_flex'}:
            try:
                comp = self.interpreter.environment.coredata.compilers[for_machine]['cpp']
            except KeyError:
                raise MesonException(f"Could not find a C++ compiler for {for_machine} to search for FlexLexer.h")
            found, _ = comp.has_header('FlexLexer.h', '')
            if not found:
                raise MesonException('Could not find FlexLexer.h, which is required for Flex with C++')

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
            f'codegen-lex-{name}-{for_machine.get_lower_case_name()}',
            self.interpreter.subdir,
            self.interpreter.environment,
            command,
            [input],
            outputs,
            self.interpreter.current_build_project(),
            backend=self.interpreter.backend,
            description='Generating lexer {{}} with {}'.format(self.held_object.name),
        )
        self.interpreter.add_target(target.name, target)

        return target


@dataclasses.dataclass
class YaccGenerator(_CodeGenerator):
    pass


class YaccHolder(ObjectHolder[YaccGenerator]):

    @TypedArgs('codegen.yacc.implementation')
    @InterpreterObject.method('implementation')
    def implementation_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.held_object.name

    @TypedArgs('codegen.yacc.found')
    @InterpreterObject.method('found')
    def found_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> bool:
        return self.held_object.found()

    @TypedArgs(
        'codegen.yacc.generate',
        pos_types=[_SRC_PARG],
        kw_types=[
            KwargInfo('args', ContainerTypeInfo(list, str), default=[], listify=True),
            KwargInfo('source', (str, NoneType)),
            KwargInfo('header', (str, NoneType)),
            KwargInfo('locations', (str, NoneType)),
            KwargInfo('plainname', bool, default=False),
        ],
    )
    @InterpreterObject.method('generate')
    def generate_method(self, args: T.Tuple[T.Union[str, File, CustomTarget, CustomTargetIndex, GeneratedList]], kwargs: YaccGenerateKWargs) -> CustomTarget:
        if not self.held_object.found():
            raise MesonException('Attempted to call generate without finding a yacc implementation')

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

        for_machine = self.held_object.for_machine
        target = CustomTarget(
            f'codegen-yacc-{name}-{for_machine.get_lower_case_name()}',
            self.interpreter.subdir,
            self.interpreter.environment,
            command,
            [input],
            outputs,
            self.interpreter.current_build_project(),
            backend=self.interpreter.backend,
            description='Generating parser {{}} with {}'.format(self.held_object.name),
        )
        self.interpreter.add_target(target.name, target)
        return target


@dataclasses.dataclass
class ProtocOutput(HoldableObject):

    language: str
    import_dir: IncludeDirs
    sources: list[CustomTargetIndex] = dataclasses.field(default_factory=list)
    headers: list[CustomTargetIndex] = dataclasses.field(default_factory=list)
    dependency: InternalDependency | None = None
    extra_depends: OrderedSet[CustomTarget] = dataclasses.field(default_factory=OrderedSet)


class ProtocOutputHolder(ObjectHolder[ProtocOutput]):

    @TypedArgs('codegen.protoc.output.sources')
    @InterpreterObject.method('sources')
    def sources_method(self, args: list[TYPE_var], kwargs: TYPE_kwargs) -> list[CustomTargetIndex]:
        return self.held_object.sources

    @TypedArgs('codegen.protoc.output.headers')
    @InterpreterObject.method('headers')
    def headers_method(self, args: list[TYPE_var], kwargs: TYPE_kwargs) -> list[CustomTargetIndex]:
        return self.held_object.headers

    @TypedArgs('codegen.protoc.output.dependency')
    @InterpreterObject.method('dependency')
    def dependency_method(self, args: list[TYPE_var], kwargs: TYPE_kwargs) -> InternalDependency:
        if self.held_object.language != 'cpp':
            raise MesonException(f'`dependency` method is not available for {self.held_object.language!r} language.')
        if self.held_object.dependency is None:
            raise MesonBugException('`generate` did not return the dependency')
        return self.held_object.dependency


@dataclasses.dataclass
class ProtocGenerator(_CodeGenerator):

    dependency: Dependency | None = None
    import_dirs: list[IncludeDirs] = dataclasses.field(default_factory=list)
    grpc_dependency: Dependency | None = None
    grpc_plugin: Program | None = None


class ProtocHolder(ObjectHolder[ProtocGenerator]):

    @TypedArgs('codegen.protoc.found')
    @InterpreterObject.method('found')
    def found_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> bool:
        return self.held_object.found()

    @TypedArgs('codegen.protoc.version')
    @InterpreterObject.method('version')
    def version_method(self, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        if not self.held_object.found():
            raise MesonException('Unable to get the version of a not-found external program')
        try:
            return self.held_object.program.get_version(self.interpreter)
        except MesonException:
            return 'unknown'

    @TypedArgs(
        'codegen.protoc.generate',
        var_types=VarArgInfo((str, File, CustomTarget, CustomTargetIndex), min_args=1, validator=_validate_protoc_source),
        kw_types=[
            KwargInfo('language', str, default='cpp', validator=in_set_validator({'cpp'})),
            _IMPORT_DIRS_KW,
            KwargInfo('imports', ContainerTypeInfo(list, ProtocOutput), default=[], listify=True),
            KwargInfo('args', ContainerTypeInfo(list, str), default=[], listify=True),
            INSTALL_KW,
            INSTALL_DIR_KW,
            KwargInfo('grpc', (bool, NoneType)),
        ],
    )
    @InterpreterObject.method('generate')
    def generate_method(self, args: tuple[list[str | File | CustomTarget | CustomTargetIndex]], kwargs: ProtocGenerateKwargs) -> ProtocOutput:
        if not self.held_object.found():
            raise MesonException('Attempted to call generate without finding a protoc implementation')

        arguments: list[str] = []
        language = kwargs['language']
        build_project = self.interpreter.current_build_project()
        state = ModuleState(self.interpreter)
        native = self.held_object.for_machine is MachineChoice.BUILD

        arguments.append('--proto_path=@CURRENT_SOURCE_DIR@')
        arguments.append('--proto_path=' + os.path.join('@BUILD_ROOT@', self.interpreter.current_build_dir()))  # for generated files
        arguments.append('--dependency_out=@DEPFILE@')

        if language == 'cpp':
            protobuf_dep = self.held_object.dependency
            if protobuf_dep is None:
                protobuf_dep = state.dependency('protobuf', native=native, required=False)
                self.held_object.dependency = protobuf_dep
            if not protobuf_dep.found():
                raise MesonException('protobuf dependency not found; install it or pass `dependency:` to codegen.protoc()')

            arguments.append('--cpp_out=' + os.path.join('@BUILD_ROOT@', self.interpreter.current_build_dir(), 'meson-protoc'))

        grpc_dep = self.held_object.grpc_dependency
        grpc_plugin = self.held_object.grpc_plugin
        grpc = kwargs['grpc']
        if grpc is None:
            grpc = grpc_dep is not None and grpc_dep.found()
        if grpc:
            if language != 'cpp':
                raise MesonException(f'protoc.generate: gRPC generation is not supported for {language!r} language.')
            if grpc_dep is None:
                grpc_dep = state.dependency('grpc++', native=native, required=False)
            if not grpc_dep.found():
                raise MesonException('grpc dependency not found; install it or pass `grpc_dependency:` to codegen.protoc()')
            if grpc_plugin is None:
                grpc_plugin = state.find_program('grpc_cpp_plugin', required=False, for_machine=self.held_object.for_machine)
                self.held_object.grpc_plugin = grpc_plugin
            if not grpc_plugin.found():
                raise MesonException('protoc.generate: gRPC generation requires the grpc_cpp_plugin program, which was not found.')

            arguments.append('--grpc_out=' + os.path.join('@BUILD_ROOT@', self.interpreter.current_build_dir(), 'meson-protoc'))
            arguments.append('--plugin=protoc-gen-grpc=' + _protoc_plugin_path(grpc_plugin))

        extra_deps: OrderedSet[CustomTarget] = OrderedSet()

        for imp_gen in kwargs['imports']:
            extra_deps.update(imp_gen.extra_depends)
        for import_dir in itertools.chain(
                self.held_object.import_dirs,
                self.interpreter.extract_incdirs(kwargs['import_dirs']),
                (imp_gen.import_dir for imp_gen in kwargs['imports'])):
            arguments.extend('-I' + path for path in import_dir.abs_string_list('@SOURCE_ROOT@', '@BUILD_ROOT@'))

        arguments.extend(kwargs['args'])
        arguments.append('@INPUT@')

        command = self.held_object.command() + arguments

        if language == 'cpp':
            includedir = self.interpreter.environment.get_includedir()
            install_dirs: list[str | Literal[False]] = [False, kwargs['install_dir'] or includedir]
            if grpc:
                install_dirs *= 2

        proto_paths: dict[str, File | CustomTargetIndex] = {}

        def _verify_proto_file(proto_file: File | CustomTargetIndex) -> None:
            if isinstance(proto_file, CustomTargetIndex):
                is_built = True
                relative_name = os.path.join(proto_file.get_builddir(), proto_file.get_filename())
            else:
                is_built = proto_file.is_built
                relative_name = proto_file.relative_name()
            parent_dir = self.interpreter.current_build_dir() if is_built else self.interpreter.subdir

            if not is_parent_path(parent_dir, relative_name):
                raise MesonException(f'{proto_file!s} file must reside inside {parent_dir!r}')
            proto_rel_path = relpath(relative_name, parent_dir)

            if old_file := proto_paths.get(proto_rel_path):
                if old_file == proto_file:
                    return
                raise MesonException(
                    f'protoc.generate: {_describe_proto_file(old_file)} and {_describe_proto_file(proto_file)} '
                    f'have the same import name {proto_rel_path!r}. Rename one of them.')
            if is_built:
                src_path = os.path.join(self.interpreter.subdir, proto_rel_path)
                if os.path.isfile(os.path.join(self.interpreter.source_root, src_path)):
                    raise MesonException(
                        f'protoc.generate: {_describe_proto_file(proto_file)} shadows source file {src_path!r}: '
                        f'both have the import name {proto_rel_path!r}. Rename one of them.')
            proto_paths[proto_rel_path] = proto_file

        for proto_source in self.interpreter.source_strings_to_files(args[0]):
            if isinstance(proto_source, File):
                _verify_proto_file(proto_source)

            elif isinstance(proto_source, CustomTargetIndex):
                extra_deps.add(T.cast(CustomTarget, proto_source.target))
                _verify_proto_file(proto_source)

            elif isinstance(proto_source, CustomTarget):
                extra_deps.add(proto_source)
                for proto_source_index in proto_source:
                    _verify_proto_file(proto_source_index)

            else:
                raise MesonBugException(f'Unsupported source type {type(proto_source)} in protoc.generate()')

        target_depends: list[TargetDepends] = list(extra_deps)
        if grpc and grpc_plugin is not None:
            # The plugin path is embedded in an argument, so the dependency
            # on the plugin must be explicit.
            target_depends.append(grpc_plugin)

        targets: list[CustomTarget] = []
        for proto_rel_path, proto_file in proto_paths.items():
            name, _ = os.path.splitext(f'codegen-protoc-{proto_rel_path}'.replace('/', '@').replace(os.path.sep, '@'))

            if language == 'cpp':
                rel_output = os.path.join('meson-protoc', os.path.dirname(proto_rel_path))
                outputs = [os.path.join(rel_output, '@BASENAME@.pb.cc'), os.path.join(rel_output, '@BASENAME@.pb.h')]
                if grpc:
                    # grpc_cpp_plugin always writes both files, even for a
                    # .proto without any service.
                    outputs += [os.path.join(rel_output, '@BASENAME@.grpc.pb.cc'),
                                os.path.join(rel_output, '@BASENAME@.grpc.pb.h')]

            ct = CustomTarget(
                name,
                self.interpreter.subdir,
                self.interpreter.environment,
                command,
                [proto_file],
                outputs,
                build_project,

                depfile=f'{name}.dep',
                extra_depends=target_depends,
                install=kwargs['install'],
                install_dir=install_dirs,
                description=f'Generating protobuf for {proto_rel_path}',
                output_install_root='meson-protoc',
            )

            self.interpreter.add_target(ct.name, ct)
            targets.append(ct)

        if language == 'cpp':
            sources = [ct[0] for ct in targets]
            headers = [ct[1] for ct in targets]
            if grpc:
                sources += [ct[2] for ct in targets]
                headers += [ct[3] for ct in targets]
            ext_deps: list[Dependency] = [d for i in kwargs['imports'] if (d := i.dependency) is not None]
            ext_deps.append(protobuf_dep)
            if grpc and grpc_dep is not None:
                ext_deps.append(grpc_dep)
            dependency = InternalDependency(
                protobuf_dep.get_version(),
                ext_deps = ext_deps,
                incdirs = [IncludeDirs(self.interpreter.subdir, [], False, build_project, extra_build_dirs=['meson-protoc'])],
                sources = targets,
            )

        else:
            sources = []
            headers = []
            dependency = None

        return ProtocOutput(language, IncludeDirs(self.interpreter.subdir, ['.'], False, build_project),
                            sources, headers, dependency, extra_deps)


class CodeGenModule(ExtensionModule):

    """Module with helpers for codegen wrappers."""

    INFO = ModuleInfo('codegen', '1.10.0', unstable=True)

    def __init__(self, interpreter: Interpreter) -> None:
        super().__init__(interpreter)
        self.methods.update({
            'lex': self.lex_method,
            'yacc': self.yacc_method,
            'protoc': self.protoc_method,
        })

    @TypedArgs(
        'codegen.lex',
        kw_types=[
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
            REQUIRED_KW,
            DISABLER_KW,
            NATIVE_KW
        ],
    )
    @apply_machine_map
    @disablerIfNotFound
    def lex_method(self, state: ModuleState, args: T.Tuple, kwargs: FindLexKwargs) -> LexGenerator:
        disabled, required, feature = extract_required_kwarg(kwargs, state.subproject)
        if disabled:
            mlog.log('generator lex skipped: feature', mlog.bold(feature), 'disabled')
            return LexGenerator('lex', NonExistingExternalProgram('lex'), kwargs['native'])

        names: T.List[LexImpls] = []
        if kwargs['implementations']:
            names = kwargs['implementations']
        else:
            if state.environment.machines[kwargs['native']].system == 'windows':
                names.append('win_flex')
            names.extend(['flex', 'reflex', 'lex'])

        versions: T.Mapping[str, T.List[str]] = {
            'lex': kwargs['lex_version'],
            'flex': kwargs['flex_version'],
            'reflex': kwargs['reflex_version'],
            'win_flex': kwargs['win_flex_version']
        }

        for name in names:
            bin = state.find_program(
                name, wanted=versions[name], for_machine=kwargs['native'], required=False)
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
            if required:
                raise MesonException.from_node(
                    'Could not find a lex implementation. Tried: ', ", ".join(names),
                    node=state.current_node)
            return LexGenerator(name, bin, kwargs['native'])

        lex_args: T.List[str] = []
        # This option allows compiling with MSVC
        # https://github.com/lexxmark/winflexbison/blob/master/UNISTD_ERROR.readme
        if bin.name == 'win_flex' and state.environment.machines[kwargs['native']].is_windows():
            lex_args.append('--wincompat')
        lex_args.extend(['-o', '@OUTPUT0@'])
        return LexGenerator(name, bin, kwargs['native'], T.cast('ImmutableListProtocol[str]', lex_args))

    @TypedArgs(
        'codegen.yacc',
        kw_types=[
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
            REQUIRED_KW,
            DISABLER_KW,
            NATIVE_KW,
        ],
    )
    @apply_machine_map
    @disablerIfNotFound
    def yacc_method(self, state: ModuleState, args: T.Tuple, kwargs: FindYaccKwargs) -> YaccGenerator:
        disabled, required, feature = extract_required_kwarg(kwargs, state.subproject)
        if disabled:
            mlog.log('generator yacc skipped: feature', mlog.bold(feature), 'disabled')
            return YaccGenerator('yacc', NonExistingExternalProgram('yacc'), kwargs['native'])
        names: T.List[YaccImpls]
        if kwargs['implementations']:
            names = kwargs['implementations']
        else:
            if state.environment.machines[kwargs['native']].system == 'windows':
                names = ['win_bison', 'bison', 'yacc']
            else:
                names = ['bison', 'byacc', 'yacc']

        versions: T.Mapping[YaccImpls, T.List[str]] = {
            'yacc': kwargs['yacc_version'],
            'byacc': kwargs['byacc_version'],
            'bison': kwargs['bison_version'],
            'win_bison': kwargs['win_bison_version'],
        }

        for name in names:
            bin = state.find_program(
                name, wanted=versions[name], for_machine=kwargs['native'], required=False)
            if bin.found():
                break
        else:
            if required:
                raise MesonException.from_node(
                    'Could not find a yacc implementation. Tried: ', ", ".join(names),
                    node=state.current_node)
            return YaccGenerator(name, bin, kwargs['native'])

        yacc_args: T.List[str] = []

        impl = T.cast('YaccImpls', bin.name)
        if impl == 'yacc' and isinstance(bin, ExternalProgram):
            _, out, _ = Popen_safe(bin.get_command() + ['--version'])
            if 'GNU Bison' in out:
                impl = 'bison'
            elif out.startswith('yacc - 2'):
                impl = 'byacc'

        if impl in {'bison', 'win_bison'}:
            yacc_args.append('--defines=@OUTPUT1@')
            if isinstance(bin, ExternalProgram) and version_compare(bin.get_version(), '>= 3.4'):
                yacc_args.append('--color=always')
        elif impl == 'byacc':
            yacc_args.extend(['-H', '@OUTPUT1@'])
        else:
            mlog.warning('This yacc does not appear to be bison or byacc, the '
                         'POSIX specification does not require that header '
                         'output location be configurable, and may not work.',
                         fatal=False)
            yacc_args.append('-H')
        yacc_args.extend(['-o', '@OUTPUT0@', '@INPUT@'])
        return YaccGenerator(name, bin, kwargs['native'], T.cast('ImmutableListProtocol[str]', yacc_args))

    @FeatureNew('codegen.protoc', '1.14.0')
    @TypedArgs(
        'codegen.protoc',
        kw_types=[
            KwargInfo('dependency', (Dependency, NoneType), default=None),
            KwargInfo('grpc_dependency', (Dependency, NoneType), default=None),
            _IMPORT_DIRS_KW,
            KwargInfo('version', ContainerTypeInfo(list, str), default=[], listify=True),
            KwargInfo('args', ContainerTypeInfo(list, str), default=[], listify=True),
            NATIVE_KW,
            REQUIRED_KW,
            DISABLER_KW,
        ],
    )
    @apply_machine_map
    @disablerIfNotFound
    def protoc_method(self, state: ModuleState, args: T.Tuple, kwargs: FindProtocKwargs) -> ProtocGenerator:
        name = 'protoc'

        disabled, required, feature = extract_required_kwarg(kwargs, state.subproject)
        if disabled:
            mlog.log('generator protoc skipped: feature', mlog.bold(feature), 'disabled')
            return ProtocGenerator(name, NonExistingExternalProgram(name), kwargs['native'])

        bin = state.find_program(name, wanted=kwargs['version'], for_machine=kwargs['native'], required=False)
        if not bin.found() and required:
            raise MesonException.from_node(
                'Could not find a protoc binary', node=state.current_node)

        dependency = kwargs['dependency']
        import_dirs = self.interpreter.extract_incdirs(kwargs['import_dirs'])

        grpc_dependency = kwargs['grpc_dependency']
        grpc_plugin: Program | None = None
        if grpc_dependency is not None and grpc_dependency.found():
            # The plugin runs alongside protoc, on the same machine.
            grpc_plugin = state.find_program('grpc_cpp_plugin', required=False, for_machine=kwargs['native'])

        return ProtocGenerator(name, bin, kwargs['native'], kwargs['args'], dependency, import_dirs,
                               grpc_dependency, grpc_plugin)


def initialize(interpreter: Interpreter) -> CodeGenModule:
    interpreter.append_holder_map(LexGenerator, LexHolder)
    interpreter.append_holder_map(YaccGenerator, YaccHolder)
    interpreter.append_holder_map(ProtocGenerator, ProtocHolder)
    interpreter.append_holder_map(ProtocOutput, ProtocOutputHolder)
    return CodeGenModule(interpreter)
