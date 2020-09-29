# Copyright 2020 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, subprocess, shlex
from .._pathlib import Path
import typing as T

from . import ExtensionModule, ModuleReturnValue
from .. import mlog, build
from ..mesonlib import (MesonException, Popen_safe, MachineChoice,
                       get_variable_regex, do_replacement)
from ..interpreterbase import InterpreterObject, InterpreterException, FeatureNew
from ..interpreterbase import stringArgs, permittedKwargs
from ..interpreter import Interpreter, DependencyHolder, InstallDir
from ..compilers.compilers import cflags_mapping, cexe_mapping
from ..dependencies.base import InternalDependency, PkgConfigDependency
from ..environment import Environment

class ExternalProject(InterpreterObject):
    def __init__(self,
                 interpreter: Interpreter,
                 subdir: str,
                 project_version: T.Dict[str, str],
                 subproject: str,
                 environment: Environment,
                 build_machine: str,
                 host_machine: str,
                 configure_command: T.List[str],
                 configure_options: T.List[str],
                 cross_configure_options: T.List[str],
                 env: build.EnvironmentVariables,
                 verbose: bool):
        InterpreterObject.__init__(self)
        self.methods.update({'dependency': self.dependency_method,
                             })

        self.interpreter = interpreter
        self.subdir = Path(subdir)
        self.project_version = project_version
        self.subproject = subproject
        self.env = environment
        self.build_machine = build_machine
        self.host_machine = host_machine
        self.configure_command = configure_command
        self.configure_options = configure_options
        self.cross_configure_options = cross_configure_options
        self.verbose = verbose
        self.user_env = env

        self.name = self.subdir.name
        self.src_dir = Path(self.env.get_source_dir(), self.subdir)
        self.build_dir = Path(self.env.get_build_dir(), self.subdir, 'build')
        self.install_dir = Path(self.env.get_build_dir(), self.subdir, 'dist')
        self.prefix = Path(self.env.coredata.get_builtin_option('prefix'))
        self.libdir = Path(self.env.coredata.get_builtin_option('libdir'))
        self.includedir = Path(self.env.coredata.get_builtin_option('includedir'))

        # On Windows if the prefix is "c:/foo" and DESTDIR is "c:/bar", `make`
        # will install files into "c:/bar/c:/foo" which is an invalid path.
        # Work around that issue by removing the drive from prefix.
        if self.prefix.drive:
            self.prefix = self.prefix.relative_to(self.prefix.drive)

        # self.prefix is an absolute path, so we cannot append it to another path.
        self.rel_prefix = self.prefix.relative_to(self.prefix.root)

        self.make = self.interpreter.find_program_impl('make')
        self.make = self.make.get_command()[0]

        self._configure()

        self.targets = self._create_targets()

    def _configure(self):
        # Assume it's the name of a script in source dir, like 'configure',
        # 'autogen.sh', etc).
        configure_path = Path(self.src_dir, self.configure_command)
        configure_prog = self.interpreter.find_program_impl(configure_path.as_posix())
        configure_cmd = configure_prog.get_command()

        d = {'PREFIX': self.prefix.as_posix(),
             'LIBDIR': self.libdir.as_posix(),
             'INCLUDEDIR': self.includedir.as_posix(),
             }
        self._validate_configure_options(d.keys())

        configure_cmd += self._format_options(self.configure_options, d)

        if self.env.is_cross_build():
            host = '{}-{}-{}'.format(self.host_machine.cpu_family,
                                     self.build_machine.system,
                                     self.host_machine.system)
            d = {'HOST': host}
            configure_cmd += self._format_options(self.cross_configure_options, d)

        # Set common env variables like CFLAGS, CC, etc.
        link_exelist = []
        link_args = []
        self.run_env = os.environ.copy()
        for lang, compiler in self.env.coredata.compilers[MachineChoice.HOST].items():
            if any(lang not in i for i in (cexe_mapping, cflags_mapping)):
                continue
            cargs = self.env.coredata.get_external_args(MachineChoice.HOST, lang)
            self.run_env[cexe_mapping[lang]] = self._quote_and_join(compiler.get_exelist())
            self.run_env[cflags_mapping[lang]] = self._quote_and_join(cargs)
            if not link_exelist:
                link_exelist = compiler.get_linker_exelist()
                link_args = self.env.coredata.get_external_link_args(MachineChoice.HOST, lang)
        if link_exelist:
            self.run_env['LD'] = self._quote_and_join(link_exelist)
        self.run_env['LDFLAGS'] = self._quote_and_join(link_args)

        self.run_env = self.user_env.get_env(self.run_env)

        PkgConfigDependency.setup_env(self.run_env, self.env, MachineChoice.HOST,
                                      Path(self.env.get_build_dir(), 'meson-uninstalled').as_posix())

        self.build_dir.mkdir(parents=True, exist_ok=True)
        self._run('configure', configure_cmd)

    def _quote_and_join(self, array: T.List[str]) -> str:
        return ' '.join([shlex.quote(i) for i in array])

    def _validate_configure_options(self, required_keys: T.List[str]):
        # Ensure the user at least try to pass basic info to the build system,
        # like the prefix, libdir, etc.
        for key in required_keys:
            key_format = '@{}@'.format(key)
            for option in self.configure_options:
                if key_format in option:
                    break
            else:
                m = 'At least one configure option must contain "{}" key'
                raise InterpreterException(m.format(key_format))

    def _format_options(self, options: T.List[str], variables: T.Dict[str, str]) -> T.List[str]:
        out = []
        missing = set()
        regex = get_variable_regex('meson')
        confdata = {k: (v, None) for k, v in variables.items()}
        for o in options:
            arg, missing_vars = do_replacement(regex, o, 'meson', confdata)
            missing.update(missing_vars)
            out.append(arg)
        if missing:
            var_list = ", ".join(map(repr, sorted(missing)))
            raise EnvironmentException(
                "Variables {} in configure options are missing.".format(var_list))
        return out

    def _run(self, step: str, command: T.List[str]):
        mlog.log('External project {}:'.format(self.name), mlog.bold(step))
        output = None if self.verbose else subprocess.DEVNULL
        p, o, e = Popen_safe(command, cwd=str(self.build_dir), env=self.run_env,
                                      stderr=subprocess.STDOUT,
                                      stdout=output)
        if p.returncode != 0:
            m = '{} step failed:\n{}'.format(step, e)
            raise MesonException(m)

    def _create_targets(self):
        cmd = self.env.get_build_command()
        cmd += ['--internal', 'externalproject',
                '--name', self.name,
                '--srcdir', self.src_dir.as_posix(),
                '--builddir', self.build_dir.as_posix(),
                '--installdir', self.install_dir.as_posix(),
                '--make', self.make,
                ]
        if self.verbose:
            cmd.append('--verbose')

        target_kwargs = {'output': '{}.stamp'.format(self.name),
                         'depfile': '{}.d'.format(self.name),
                         'command': cmd + ['@OUTPUT@', '@DEPFILE@'],
                         'console': True,
                         }
        self.target = build.CustomTarget(self.name,
                                         self.subdir.as_posix(),
                                         self.subproject,
                                         target_kwargs)

        idir = InstallDir(self.subdir.as_posix(),
                          Path('dist', self.rel_prefix).as_posix(),
                          install_dir='.',
                          install_mode=None,
                          exclude=None,
                          strip_directory=True,
                          from_source_dir=False)

        return [self.target, idir]

    @stringArgs
    @permittedKwargs({'subdir'})
    def dependency_method(self, args, kwargs):
        if len(args) != 1:
            m = 'ExternalProject.dependency takes exactly 1 positional arguments'
            raise InterpreterException(m)
        libname = args[0]

        subdir = kwargs.get('subdir', '')
        if not isinstance(subdir, str):
            m = 'ExternalProject.dependency subdir keyword argument must be string.'
            raise InterpreterException(m)

        abs_includedir = Path(self.install_dir, self.rel_prefix, self.includedir)
        if subdir:
            abs_includedir = Path(abs_includedir, subdir)
        abs_libdir = Path(self.install_dir, self.rel_prefix, self.libdir)

        version = self.project_version['version']
        incdir = []
        compile_args = ['-I{}'.format(abs_includedir)]
        link_args = ['-L{}'.format(abs_libdir), '-l{}'.format(libname)]
        libs = []
        libs_whole = []
        sources = self.target
        final_deps = []
        variables = []
        dep = InternalDependency(version, incdir, compile_args, link_args, libs,
                                 libs_whole, sources, final_deps, variables)
        return DependencyHolder(dep, self.subproject)


class ExternalProjectModule(ExtensionModule):
    @FeatureNew('External build system Module', '0.56.0')
    def __init__(self, interpreter):
        super().__init__(interpreter)

    @stringArgs
    @permittedKwargs({'configure_options', 'cross_configure_options', 'verbose', 'env'})
    def add_project(self, state, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('add_project takes exactly one positional argument')
        configure_command = args[0]
        configure_options = kwargs.get('configure_options', [])
        cross_configure_options = kwargs.get('cross_configure_options', ['--host={host}'])
        verbose = kwargs.get('verbose', False)
        env = self.interpreter.unpack_env_kwarg(kwargs)
        project = ExternalProject(self.interpreter,
                                  state.subdir,
                                  state.project_version,
                                  state.subproject,
                                  state.environment,
                                  state.build_machine,
                                  state.host_machine,
                                  configure_command,
                                  configure_options,
                                  cross_configure_options,
                                  env, verbose)
        return ModuleReturnValue(project, project.targets)


def initialize(*args, **kwargs):
    return ExternalProjectModule(*args, **kwargs)
