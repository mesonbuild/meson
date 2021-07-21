import os

from .. import mesonlib
from .. import dependencies
from .. import build
from .. import mlog

from ..mesonlib import MachineChoice, OptionKey
from ..programs import OverrideProgram, ExternalProgram
from ..interpreterbase import (MesonInterpreterObject, FeatureNewKwargs, FeatureNew, FeatureDeprecated,
                               typed_pos_args, permittedKwargs, noArgsFlattening, noPosargs, noKwargs,
                               MesonVersionString, InterpreterException)

from .interpreterobjects import (ExecutableHolder, ExternalProgramHolder,
                                 CustomTargetHolder, CustomTargetIndexHolder,
                                 EnvironmentVariablesObject)

import typing as T

if T.TYPE_CHECKING:
    from .interpreter import Interpreter

class MesonMain(MesonInterpreterObject):
    def __init__(self, build: 'build.Build', interpreter: 'Interpreter'):
        super().__init__(subproject=interpreter.subproject)
        self.build = build
        self.interpreter = interpreter
        self.methods.update({'get_compiler': self.get_compiler_method,
                             'is_cross_build': self.is_cross_build_method,
                             'has_exe_wrapper': self.has_exe_wrapper_method,
                             'can_run_host_binaries': self.can_run_host_binaries_method,
                             'is_unity': self.is_unity_method,
                             'is_subproject': self.is_subproject_method,
                             'current_source_dir': self.current_source_dir_method,
                             'current_build_dir': self.current_build_dir_method,
                             'source_root': self.source_root_method,
                             'build_root': self.build_root_method,
                             'project_source_root': self.project_source_root_method,
                             'project_build_root': self.project_build_root_method,
                             'global_source_root': self.global_source_root_method,
                             'global_build_root': self.global_build_root_method,
                             'add_install_script': self.add_install_script_method,
                             'add_postconf_script': self.add_postconf_script_method,
                             'add_dist_script': self.add_dist_script_method,
                             'install_dependency_manifest': self.install_dependency_manifest_method,
                             'override_dependency': self.override_dependency_method,
                             'override_find_program': self.override_find_program_method,
                             'project_version': self.project_version_method,
                             'project_license': self.project_license_method,
                             'version': self.version_method,
                             'project_name': self.project_name_method,
                             'get_cross_property': self.get_cross_property_method,
                             'get_external_property': self.get_external_property_method,
                             'has_external_property': self.has_external_property_method,
                             'backend': self.backend_method,
                             'add_devenv': self.add_devenv_method,
                             })

    def _find_source_script(self, prog: T.Union[str, mesonlib.File, build.Executable, ExternalProgram], args):

        if isinstance(prog, (build.Executable, ExternalProgram)):
            return self.interpreter.backend.get_executable_serialisation([prog] + args)
        found = self.interpreter.func_find_program({}, prog, {})
        es = self.interpreter.backend.get_executable_serialisation([found] + args)
        es.subproject = self.interpreter.subproject
        return es

    def _process_script_args(
            self, name: str, args: T.List[T.Union[
                str, mesonlib.File, CustomTargetHolder,
                CustomTargetIndexHolder,
                ExternalProgramHolder, ExecutableHolder,
            ]], allow_built: bool = False) -> T.List[str]:
        script_args = []  # T.List[str]
        new = False
        for a in args:
            if isinstance(a, str):
                script_args.append(a)
            elif isinstance(a, mesonlib.File):
                new = True
                script_args.append(a.rel_to_builddir(self.interpreter.environment.source_dir))
            elif isinstance(a, (build.BuildTarget, build.CustomTarget, build.CustomTargetIndex)):
                if not allow_built:
                    raise InterpreterException(f'Arguments to {name} cannot be built')
                new = True
                script_args.extend([os.path.join(a.get_subdir(), o) for o in a.get_outputs()])

                # This feels really hacky, but I'm not sure how else to fix
                # this without completely rewriting install script handling.
                # This is complicated by the fact that the install target
                # depends on all.
                if isinstance(a, build.CustomTargetIndex):
                    a.target.build_by_default = True
                else:
                    a.build_by_default = True
            elif isinstance(a, ExternalProgram):
                script_args.extend(a.command)
                new = True
            else:
                raise InterpreterException(
                   f'Arguments to {name} must be strings, Files, or CustomTargets, '
                    'Indexes of CustomTargets')
        if new:
            FeatureNew.single_use(
                f'Calling "{name}" with File, CustomTaget, Index of CustomTarget, '
                'Executable, or ExternalProgram',
                '0.55.0', self.interpreter.subproject)
        return script_args

    @FeatureNewKwargs('add_install_script', '0.57.0', ['skip_if_destdir'])
    @permittedKwargs({'skip_if_destdir'})
    def add_install_script_method(self, args: 'T.Tuple[T.Union[str, mesonlib.File, ExecutableHolder], T.Union[str, mesonlib.File, CustomTargetHolder, CustomTargetIndexHolder], ...]', kwargs):
        if len(args) < 1:
            raise InterpreterException('add_install_script takes one or more arguments')
        if isinstance(args[0], mesonlib.File):
            FeatureNew.single_use('Passing file object to script parameter of add_install_script',
                                  '0.57.0', self.interpreter.subproject)
        skip_if_destdir = kwargs.get('skip_if_destdir', False)
        if not isinstance(skip_if_destdir, bool):
            raise InterpreterException('skip_if_destdir keyword argument must be boolean')
        script_args = self._process_script_args('add_install_script', args[1:], allow_built=True)
        script = self._find_source_script(args[0], script_args)
        script.skip_if_destdir = skip_if_destdir
        self.build.install_scripts.append(script)

    @permittedKwargs(set())
    def add_postconf_script_method(self, args, kwargs):
        if len(args) < 1:
            raise InterpreterException('add_postconf_script takes one or more arguments')
        if isinstance(args[0], mesonlib.File):
            FeatureNew.single_use('Passing file object to script parameter of add_postconf_script',
                                  '0.57.0', self.interpreter.subproject)
        script_args = self._process_script_args('add_postconf_script', args[1:], allow_built=True)
        script = self._find_source_script(args[0], script_args)
        self.build.postconf_scripts.append(script)

    @permittedKwargs(set())
    def add_dist_script_method(self, args, kwargs):
        if len(args) < 1:
            raise InterpreterException('add_dist_script takes one or more arguments')
        if len(args) > 1:
            FeatureNew.single_use('Calling "add_dist_script" with multiple arguments',
                                  '0.49.0', self.interpreter.subproject)
        if isinstance(args[0], mesonlib.File):
            FeatureNew.single_use('Passing file object to script parameter of add_dist_script',
                                  '0.57.0', self.interpreter.subproject)
        if self.interpreter.subproject != '':
            FeatureNew.single_use('Calling "add_dist_script" in a subproject',
                                  '0.58.0', self.interpreter.subproject)
        script_args = self._process_script_args('add_dist_script', args[1:], allow_built=True)
        script = self._find_source_script(args[0], script_args)
        self.build.dist_scripts.append(script)

    @noPosargs
    @permittedKwargs({})
    def current_source_dir_method(self, args, kwargs):
        src = self.interpreter.environment.source_dir
        sub = self.interpreter.subdir
        if sub == '':
            return src
        return os.path.join(src, sub)

    @noPosargs
    @permittedKwargs({})
    def current_build_dir_method(self, args, kwargs):
        src = self.interpreter.environment.build_dir
        sub = self.interpreter.subdir
        if sub == '':
            return src
        return os.path.join(src, sub)

    @noPosargs
    @permittedKwargs({})
    def backend_method(self, args, kwargs):
        return self.interpreter.backend.name

    @noPosargs
    @permittedKwargs({})
    @FeatureDeprecated('meson.source_root', '0.56.0', 'use meson.project_source_root() or meson.global_source_root() instead.')
    def source_root_method(self, args, kwargs):
        return self.interpreter.environment.source_dir

    @noPosargs
    @permittedKwargs({})
    @FeatureDeprecated('meson.build_root', '0.56.0', 'use meson.project_build_root() or meson.global_build_root() instead.')
    def build_root_method(self, args, kwargs):
        return self.interpreter.environment.build_dir

    @noPosargs
    @permittedKwargs({})
    @FeatureNew('meson.project_source_root', '0.56.0')
    def project_source_root_method(self, args, kwargs):
        src = self.interpreter.environment.source_dir
        sub = self.interpreter.root_subdir
        if sub == '':
            return src
        return os.path.join(src, sub)

    @noPosargs
    @permittedKwargs({})
    @FeatureNew('meson.project_build_root', '0.56.0')
    def project_build_root_method(self, args, kwargs):
        src = self.interpreter.environment.build_dir
        sub = self.interpreter.root_subdir
        if sub == '':
            return src
        return os.path.join(src, sub)

    @noPosargs
    @noKwargs
    @FeatureNew('meson.global_source_root', '0.58.0')
    def global_source_root_method(self, args, kwargs):
        return self.interpreter.environment.source_dir

    @noPosargs
    @noKwargs
    @FeatureNew('meson.global_build_root', '0.58.0')
    def global_build_root_method(self, args, kwargs):
        return self.interpreter.environment.build_dir

    @noPosargs
    @permittedKwargs({})
    @FeatureDeprecated('meson.has_exe_wrapper', '0.55.0', 'use meson.can_run_host_binaries instead.')
    def has_exe_wrapper_method(self, args: T.Tuple[object, ...], kwargs: T.Dict[str, object]) -> bool:
        return self.can_run_host_binaries_impl(args, kwargs)

    @noPosargs
    @permittedKwargs({})
    @FeatureNew('meson.can_run_host_binaries', '0.55.0')
    def can_run_host_binaries_method(self, args: T.Tuple[object, ...], kwargs: T.Dict[str, object]) -> bool:
        return self.can_run_host_binaries_impl(args, kwargs)

    def can_run_host_binaries_impl(self, args, kwargs):
        if (self.is_cross_build_method(None, None) and
                self.build.environment.need_exe_wrapper()):
            if self.build.environment.exe_wrapper is None:
                return False
        # We return True when exe_wrap is defined, when it's not needed, and
        # when we're compiling natively. The last two are semantically confusing.
        # Need to revisit this.
        return True

    @noPosargs
    @permittedKwargs({})
    def is_cross_build_method(self, args, kwargs):
        return self.build.environment.is_cross_build()

    @permittedKwargs({'native'})
    def get_compiler_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('get_compiler_method must have one and only one argument.')
        cname = args[0]
        for_machine = self.interpreter.machine_from_native_kwarg(kwargs)
        clist = self.interpreter.coredata.compilers[for_machine]
        if cname in clist:
            return clist[cname]
        raise InterpreterException(f'Tried to access compiler for language "{cname}", not specified for {for_machine.get_lower_case_name()} machine.')

    @noPosargs
    @permittedKwargs({})
    def is_unity_method(self, args, kwargs):
        optval = self.interpreter.environment.coredata.get_option(OptionKey('unity'))
        if optval == 'on' or (optval == 'subprojects' and self.interpreter.is_subproject()):
            return True
        return False

    @noPosargs
    @permittedKwargs({})
    def is_subproject_method(self, args, kwargs):
        return self.interpreter.is_subproject()

    @permittedKwargs({})
    def install_dependency_manifest_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Must specify manifest install file name')
        if not isinstance(args[0], str):
            raise InterpreterException('Argument must be a string.')
        self.build.dep_manifest_name = args[0]

    @FeatureNew('meson.override_find_program', '0.46.0')
    @permittedKwargs({})
    def override_find_program_method(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('Override needs two arguments')
        name, exe = args
        if not isinstance(name, str):
            raise InterpreterException('First argument must be a string')
        if isinstance(exe, mesonlib.File):
            abspath = exe.absolute_path(self.interpreter.environment.source_dir,
                                        self.interpreter.environment.build_dir)
            if not os.path.exists(abspath):
                raise InterpreterException('Tried to override %s with a file that does not exist.' % name)
            exe = OverrideProgram(name, abspath)
        if not isinstance(exe, (ExternalProgram, build.Executable)):
            raise InterpreterException('Second argument must be an external program or executable.')
        self.interpreter.add_find_program_override(name, exe)

    @FeatureNew('meson.override_dependency', '0.54.0')
    @permittedKwargs({'native'})
    def override_dependency_method(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('Override needs two arguments')
        name = args[0]
        dep = args[1]
        if not isinstance(name, str) or not name:
            raise InterpreterException('First argument must be a string and cannot be empty')
        if not isinstance(dep, dependencies.Dependency):
            raise InterpreterException('Second argument must be a dependency object')
        identifier = dependencies.get_dep_identifier(name, kwargs)
        for_machine = self.interpreter.machine_from_native_kwarg(kwargs)
        override = self.build.dependency_overrides[for_machine].get(identifier)
        if override:
            m = 'Tried to override dependency {!r} which has already been resolved or overridden at {}'
            location = mlog.get_error_location_string(override.node.filename, override.node.lineno)
            raise InterpreterException(m.format(name, location))
        self.build.dependency_overrides[for_machine][identifier] = \
            build.DependencyOverride(dep, self.interpreter.current_node)

    @noPosargs
    @permittedKwargs({})
    def project_version_method(self, args, kwargs):
        return self.build.dep_manifest[self.interpreter.active_projectname]['version']

    @FeatureNew('meson.project_license()', '0.45.0')
    @noPosargs
    @permittedKwargs({})
    def project_license_method(self, args, kwargs):
        return self.build.dep_manifest[self.interpreter.active_projectname]['license']

    @noPosargs
    @permittedKwargs({})
    def version_method(self, args, kwargs):
        return MesonVersionString(self.interpreter.coredata.version)

    @noPosargs
    @permittedKwargs({})
    def project_name_method(self, args, kwargs):
        return self.interpreter.active_projectname

    def __get_external_property_impl(self, propname: str, fallback: T.Optional[object], machine: MachineChoice) -> object:
        """Shared implementation for get_cross_property and get_external_property."""
        try:
            return self.interpreter.environment.properties[machine][propname]
        except KeyError:
            if fallback is not None:
                return fallback
            raise InterpreterException(f'Unknown property for {machine.get_lower_case_name()} machine: {propname}')

    @noArgsFlattening
    @permittedKwargs({})
    @FeatureDeprecated('meson.get_cross_property', '0.58.0', 'Use meson.get_external_property() instead')
    @typed_pos_args('meson.get_cross_property', str, optargs=[object])
    def get_cross_property_method(self, args: T.Tuple[str, T.Optional[object]], kwargs: T.Dict[str, T.Any]) -> object:
        propname, fallback = args
        return self.__get_external_property_impl(propname, fallback, MachineChoice.HOST)

    @noArgsFlattening
    @permittedKwargs({'native'})
    @FeatureNew('meson.get_external_property', '0.54.0')
    @typed_pos_args('meson.get_external_property', str, optargs=[object])
    def get_external_property_method(self, args: T.Tuple[str, T.Optional[object]], kwargs: T.Dict[str, T.Any]) -> object:
        propname, fallback = args
        machine = self.interpreter.machine_from_native_kwarg(kwargs)
        return self.__get_external_property_impl(propname, fallback, machine)


    @permittedKwargs({'native'})
    @FeatureNew('meson.has_external_property', '0.58.0')
    @typed_pos_args('meson.has_external_property', str)
    def has_external_property_method(self, args: T.Tuple[str], kwargs: T.Dict[str, T.Any]) -> str:
        prop_name = args[0]
        for_machine = self.interpreter.machine_from_native_kwarg(kwargs)
        return prop_name in self.interpreter.environment.properties[for_machine]

    @FeatureNew('add_devenv', '0.58.0')
    @noKwargs
    @typed_pos_args('add_devenv', (str, list, dict, EnvironmentVariablesObject))
    def add_devenv_method(self, args: T.Union[str, list, dict, EnvironmentVariablesObject], kwargs: T.Dict[str, T.Any]) -> None:
        env = args[0]
        if isinstance(env, (str, list, dict)):
            env = EnvironmentVariablesObject(env)
        self.build.devenv.append(env.vars)
