from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
import typing as T

from . import sln, vcxproj
from .. import NewExtensionModule, ModuleInfo, ModuleObject
from ...backend.ninjabackend import NinjaBackend
from ...build import AliasTarget, BuildTarget, CustomTarget, CustomTargetIndex, Target, StructuredSources, GeneratedList
from ...import compilers
from ...dependencies import InternalDependency
from ...interpreter.type_checking import NoneType
from ...interpreterbase import noPosargs, typed_pos_args, typed_kwargs, KwargInfo, ContainerTypeInfo
from ...mesonlib import File, MesonException, OptionKey

if T.TYPE_CHECKING:
    from .. import ModuleState
    from ...interpreter import Interpreter
    from ...mesonlib import FileOrString


@dataclass
class BuildParameters:

    macros: T.List[str] = field(default_factory=list)
    include_directories: T.List[str] = field(default_factory=list)
    additional_options: T.List[str] = field(default_factory=list)
    search_paths: T.List[str] = field(default_factory=list)

    @staticmethod
    def from_parameters(params: T.List[str], source_root: Path, build_root: Path) -> BuildParameters:
        r = BuildParameters()
        for p in params:
            if p.startswith('-I'):
                incl = Path(p[2:])
                if not incl.is_absolute():
                    if (source_root / incl).is_dir():
                        incl = source_root / incl
                    elif (build_root / incl).is_dir():
                        incl = build_root / incl
                r.include_directories.append(str(incl))
            elif p.startswith(('-D', '/D')):
                r.macros.append(p[2:])
            else:
                r.additional_options.append(p)
        return r

    def __iadd__(self, other: BuildParameters) -> BuildParameters:
        self.macros.extend(other.macros)
        self.include_directories.extend(other.include_directories)
        self.additional_options.extend(other.additional_options)
        return self

    def asdict(self) -> T.Any:  # use Any, otherwise dataclass ctor is confused...
        return dict((field.name, getattr(self, field.name)) for field in fields(self))


def _resolve_output_dir(state: ModuleState, output_dir: T.Optional[str]) -> Path:
    output_path = Path(state.environment.get_build_dir(), state.build_to_src)
    if output_dir:
        output_dir_path = Path(output_dir)
        if output_dir_path.is_absolute():
            output_path = output_dir_path
        else:
            output_path /= output_dir_path
    return output_path


def to_project_dict(projects: T.Any) -> T.Dict[str, T.List[VisualStudioProject]]:
    if isinstance(projects, VisualStudioProject):
        return {'': [projects]}
    elif isinstance(projects, list):
        return {'': projects}
    elif isinstance(projects, dict):
        for k, p in projects.items():
            if isinstance(p, VisualStudioProject):
                projects[k] = [p]
        return projects
    raise MesonException('Invalid projects parameter')


class VisualStudioProject(ModuleObject):
    def __init__(self, name: str, source_dir: Path, config: vcxproj.ConfigurationData, subdir: str,
                 known_configurations: T.Optional[T.List[str]], known_architectures: T.Optional[T.List[str]]):
        super().__init__()

        self.config = config
        self.project = vcxproj.VcxProj(name, source_dir, subdir)
        self.known_configurations = known_configurations
        self.known_architectures = known_architectures

        self.methods.update({
            'generate': self.func_generate
        })

    def _resolve(self, state: ModuleState, file: FileOrString) -> str:
        if isinstance(file, File):
            return file.absolute_path(state.source_root, state.environment.get_build_dir())
        return file

    def add_sources(self, state: ModuleState, sources: T.Iterable[T.Union[FileOrString, CustomTarget, CustomTargetIndex, StructuredSources, GeneratedList]]) -> None:
        source_paths: T.List[str] = []
        for source in sources:
            if isinstance(source, StructuredSources):
                self.add_sources(state, source.as_list())
            elif isinstance(source, GeneratedList):
                source_paths.extend(source.get_outputs())
            elif isinstance(source, (CustomTarget, CustomTargetIndex)):
                raise MesonException.from_node(
                    'CustomTarget dependencies are currently not supported for visualstudio projects', node=state.current_node)
            else:
                source_paths.append(self._resolve(state, source))
        self.project.add_sources(source_paths)

    def add_headers(self, state: ModuleState, headers: T.Iterable[FileOrString]) -> None:
        header_paths = [self._resolve(state, f) for f in headers]
        self.project.add_headers(header_paths)

    def add_extra_files(self, state: ModuleState, extra_files: T.Iterable[FileOrString]) -> None:
        extra_file_paths = [self._resolve(state, f) for f in extra_files]
        self.project.add_extra_files(extra_file_paths)

    @noPosargs
    @typed_kwargs('visualstudio.project.generate',
                  KwargInfo('output_dir', (str, NoneType))
                  )
    def func_generate(self, state: ModuleState, args: T.Tuple, kwargs: dict) -> None:
        output_path = _resolve_output_dir(state, kwargs['output_dir'])
        self.project.generate(output_path, self.config, self.known_configurations, self.known_architectures)


class VisualStudioSolution(ModuleObject):

    def __init__(self, name: str, all_target: T.Union[str, Target]):
        super().__init__()
        self.name = name
        self.projects: T.List[T.Tuple[VisualStudioProject, T.Optional[str]]] = []
        if isinstance(all_target, Target):
            self.all_target = all_target.get_basename()
        else:
            self.all_target = all_target

        self.methods.update({
            'add_project': self.func_add_project,
            'generate': self.func_generate,
        })

    def add_project(self, project: VisualStudioProject, subdir: T.Optional[str] = None) -> None:
        self.projects.append((project, subdir))

    @typed_pos_args('visualstudio.solution.add_project', VisualStudioProject)
    @typed_kwargs('visualstudio.solution.add_project', KwargInfo('subdir', (str, NoneType)))
    def func_add_project(self, state: ModuleState, args: T.Tuple[VisualStudioProject], kwargs: T.Dict[str, T.Optional[str]]) -> None:
        self.add_project(args[0], kwargs['subdir'])

    @noPosargs
    @typed_kwargs('visualstudio.solution.generate',
                  KwargInfo('output_dir', (str, NoneType)),
                  KwargInfo('project_dir', (str, NoneType)),
                  )
    def func_generate(self, state: ModuleState, args: T.Any, kwargs: T.Dict[str, str]) -> None:
        if not self.projects:
            MesonException.from_node('Cannot generate solution without projects', node=state.current_node)

        output_path = _resolve_output_dir(state, kwargs['output_dir'])
        project_dir = kwargs['project_dir']
        if project_dir:
            project_path = Path(project_dir)
            if project_path.is_absolute():
                raise MesonException.from_node('project_dir must be relative', node=state.current_node)
        else:
            project_path = Path('.')

        output_path.mkdir(parents=True, exist_ok=True)
        solution = sln.SolutionFile(output_path / f'{self.name}.sln')

        has_known_configurations = True
        has_known_architectures = True
        known_configurations = set()
        known_architectures = set()
        current_configurations = set()
        for project, _ in self.projects:
            current_configurations.add(project.config.config)
            if project.known_configurations is None:
                has_known_configurations = False
            else:
                known_configurations.update(project.known_configurations)
            if project.known_architectures is None:
                has_known_architectures = False
            else:
                known_architectures.update(project.known_architectures)

        if has_known_configurations:
            solution.remove_unknown_configurations(known_configurations)
        if has_known_architectures:
            solution.remove_unknown_architectures(known_architectures)
        solution.remove_current_configurations(current_configurations)

        project_full_path = output_path / project_path

        all_project = vcxproj.VcxProj('_ALL', Path(state.source_root), subdir=None)
        for config in current_configurations:
            config_data = vcxproj.ConfigurationData(config, self.all_target, Path(state.environment.build_dir), has_output=False)
            all_project.add_config(config_data)
            all_project.generate(project_full_path, config_data, None, None)
        solution.add_project(all_project, project_path, subdir=None, build_solution_target=True)

        for project, subdir in self.projects:
            if not project.project.generated:
                project.project.generate(project_full_path,
                                         project.config,
                                         project.known_configurations,
                                         project.known_architectures)
            elif not (project_full_path / project.project.subdir / project.project.filename).exists():
                # This is in the case the project was generated in a different folder
                project.project.write(project_full_path / project.project.subdir)

            solution.add_project(project.project, project_path, subdir)

        solution.write()


class VisualStudioModule(NewExtensionModule):

    INFO = ModuleInfo('visualstudio', '1.0.99', unstable=True)

    def __init__(self) -> None:
        super().__init__()
        self.methods.update({
            'project': self.func_project,
            'solution': self.func_solution,
        })

    def _get_build_params(self, state: ModuleState, target: BuildTarget, compiler: compilers.Compiler) -> T.List[str]:
        # This is ugly, but introspection data is not available at this point...
        # Otherwise, I would do something like: state.backend.get_introspection_data(target.get_id(), target)

        backend = T.cast(NinjaBackend, state.backend)

        params = compiler.compiler_args()
        params += compilers.get_base_compile_args(target.get_options(), compiler)
        if state.environment.coredata.options.get(OptionKey('b_pch')):
            params += state.backend.get_pch_include_args(compiler, target)
        params += backend.generate_basic_compiler_args(target, compiler)
        for i in reversed(target.get_include_dirs()):
            basedir = i.get_curdir()
            for d in reversed(i.get_incdirs()):
                (_, includeargs) = backend.generate_inc_dir(compiler, d, basedir, i.is_system)
                params += includeargs
            for d in i.get_extra_build_dirs():
                params += compiler.get_include_args(d, i.is_system)
        params += state.backend.escape_extra_args(target.get_extra_args(compiler.get_language()))
        if target.implicit_include_directories:
            params += state.backend.get_source_dir_include_args(target, compiler)
            params += state.backend.get_build_dir_include_args(target, compiler)
        params += compiler.get_include_args(backend.get_target_private_dir(target), False)
        return list(params)

    def _get_meson_files(self, state: ModuleState, target_source_dir: Path) -> T.List[str]:
        result = []
        # TODO: expose buildfiles...
        for filename in state._interpreter.processed_buildfiles:
            if filename.startswith(str(target_source_dir)):
                result.append(filename)
        return result

    def _build_target_project(self, state: ModuleState, target: BuildTarget, name: str, config: vcxproj.Configuration, kwargs: T.Dict[str, T.Any]) -> VisualStudioProject:
        root_source_dir: Path = Path(state.source_root)
        target_source_dir: Path = root_source_dir / target.get_subdir()
        root_build_dir: Path = Path(state.environment.get_build_dir())
        output: str = (Path(target.subdir) / target.get_filename()).as_posix()  # ninja target

        toolset = None
        build_parameters = BuildParameters()
        for compiler in target.compilers.values():
            if compiler.id == 'msvc':
                version = compiler.version.split('.')
                if version[0] == '19':
                    toolset = 'v14' + version[1][0]
                else:
                    toolset = 'v' + str(int(version[0])-6) + version[1][0]

            build_parameters += BuildParameters.from_parameters(
                self._get_build_params(state, target, compiler), root_source_dir, root_build_dir)

        if target.get_typename() in {'executable'}:
            build_parameters.search_paths = state.backend.determine_windows_extra_paths(target, [])

        config_data = vcxproj.ConfigurationData(config, output, root_build_dir, toolset, **build_parameters.asdict())

        sources = kwargs.pop('sources')
        headers = kwargs.pop('headers')
        extra_files = kwargs.pop('extra_files')

        project = VisualStudioProject(name, target_source_dir, config_data, **kwargs)
        project.add_extra_files(state, target.extra_files)
        module_defs = getattr(target, 'vs_module_defs', None)
        if module_defs:
            project.add_extra_files(state, [module_defs])
        project.add_extra_files(state, self._get_meson_files(state, target_source_dir))
        project.add_extra_files(state, extra_files)
        project.add_headers(state, headers)
        project.add_sources(state, target.get_sources())
        project.add_sources(state, sources)

        return project

    def _internal_dependency_project(self, state: ModuleState, dep: T.Optional[InternalDependency],
                                     config: vcxproj.Configuration, kwargs: T.Dict[str, T.Any]) -> VisualStudioProject:
        name: str = kwargs.pop('name')
        if not name:
            raise MesonException.from_node(
                'name keyword is required for project build from dependeny object', node=state.current_node)

        root_source_dir: Path = Path(state.source_root)
        project_source_dir: Path = root_source_dir / state.subdir  # we assume dependency root is current subdir
        root_build_dir: Path = Path(state.environment.get_build_dir())

        params = state.global_args.get('cpp', [])  # FIXME: I assume language is cpp...
        params.extend(state.project_args.get('cpp', []))
        if dep:
            params.extend(dep.get_all_compile_args())

        build_parameters = BuildParameters.from_parameters(params, root_source_dir, root_build_dir)
        config_data = vcxproj.ConfigurationData(config, None, root_build_dir, None, has_output=False, **build_parameters.asdict())

        sources = kwargs.pop('sources')
        headers = kwargs.pop('headers')
        extra_files = kwargs.pop('extra_files')

        project = VisualStudioProject(name, project_source_dir, config_data, **kwargs)
        project.add_extra_files(state, extra_files)
        project.add_extra_files(state, self._get_meson_files(state, project_source_dir))
        project.add_headers(state, headers)
        if dep:
            project.add_sources(state, dep.get_sources())
        project.add_sources(state, sources)

        return project

    # TODO: allow RunTargets
    @typed_pos_args('visualstudio.project', optargs=[(BuildTarget, AliasTarget, InternalDependency)])
    @typed_kwargs('visualstudio.project',
                  KwargInfo('name', (str, NoneType)),
                  KwargInfo('config', (str, NoneType)),
                  KwargInfo('subdir', (str, NoneType)),
                  KwargInfo('sources', ContainerTypeInfo(list, (str, File)), listify=True, default=[]),
                  KwargInfo('headers', ContainerTypeInfo(list, (str, File)), listify=True, default=[]),
                  KwargInfo('extra_files', ContainerTypeInfo(list, (str, File)), listify=True, default=[]),
                  KwargInfo('known_configurations', (ContainerTypeInfo(list, str), NoneType)),
                  KwargInfo('known_architectures', (ContainerTypeInfo(list, str), NoneType))
                  )
    def func_project(self, state: ModuleState, args: T.Tuple[T.Union[BuildTarget, AliasTarget, InternalDependency, None]], kwargs: T.Dict[str, T.Any]) -> VisualStudioProject:

        if not state.backend or state.backend.name != 'ninja':
            raise MesonException.from_node(
                'visualstudio module is only compatible with ninja backend.', node=state.current_node)

        config_name: str = kwargs.pop('config') or state.environment.coredata.options[OptionKey('buildtype')].value

        known_configurations: T.Optional[T.List[str]] = kwargs['known_configurations']
        if known_configurations and config_name not in known_configurations:
            raise MesonException.from_node(f'{config_name} must be in known_configurations', node=state.current_node)

        arch: str = state.host_machine.cpu_family
        if arch == 'x86_64':
            arch = 'x64'
        elif arch == 'x86':
            arch = 'Win32'

        known_architectures: T.Optional[T.List[str]] = kwargs['known_architectures']
        if known_architectures and arch not in known_architectures:
            raise MesonException.from_node(f'{arch} must be in known_architectures', node=state.current_node)

        is_debug: bool = state.environment.coredata.options[OptionKey('b_ndebug')].value == 'true'

        config = vcxproj.Configuration(config_name, arch, is_debug)

        if isinstance(args[0], (NoneType, InternalDependency)):
            return self._internal_dependency_project(state, args[0], config, kwargs)

        name: str = kwargs.pop('name') or args[0].get_basename()
        if isinstance(args[0], AliasTarget):
            target = args[0].get_dependencies()[0]
            if isinstance(target, CustomTarget):
                raise MesonException.from_node(
                    'CustomTarget dependency is presently not supported', node=state.current_node)
        else:
            target = args[0]

        return self._build_target_project(state, target, name, config, kwargs)

    @typed_pos_args('visualstudio.solution', str)
    @typed_kwargs('visualstudio.solution',
                  KwargInfo('projects', (ContainerTypeInfo(dict, (list, VisualStudioProject)),
                                         ContainerTypeInfo(list, VisualStudioProject),
                                         VisualStudioProject), convertor=to_project_dict, default={}),
                  KwargInfo('all', (BuildTarget, AliasTarget, str), default='all')
                  )
    def func_solution(self, state: ModuleState, args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> VisualStudioSolution:
        sol = VisualStudioSolution(args[0], kwargs['all'])
        for key, projects in kwargs['projects'].items():
            for project in projects:
                sol.add_project(project, key)
        return sol


def initialize(_interpreter: Interpreter) -> VisualStudioModule:
    return VisualStudioModule()
