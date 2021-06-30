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
from pathlib import Path
import typing as T

from . import ExtensionModule, ModuleReturnValue, ModuleState, NewExtensionModule
from .. import mlog, build
from ..mesonlib import (MesonException, Popen_safe, MachineChoice,
                       get_variable_regex, do_replacement, extract_as_list)
from ..interpreterbase import InterpreterException, FeatureNew
from ..interpreterbase import permittedKwargs, typed_pos_args
from ..compilers.compilers import CFLAGS_MAPPING, CEXE_MAPPING
from ..dependencies import InternalDependency, PkgConfigDependency
from ..mesonlib import OptionKey

class ExternalProject(NewExtensionModule):
    def __init__(self,
                 state: ModuleState,
                 configure_command: str,
                 configure_options: T.List[str],
                 cross_configure_options: T.List[str],
                 env: build.EnvironmentVariables,
                 verbose: bool):
        super().__init__()
        self.methods.update({'dependency': self.dependency_method,
                             })

        self.subdir = Path(state.subdir)
        self.project_version = state.project_version
        self.subproject = state.subproject
        self.env = state.environment
        self.build_machine = state.build_machine
        self.host_machine = state.host_machine
        self.configure_command = configure_command
        self.configure_options = configure_options
        self.cross_configure_options = cross_configure_options
        self.verbose = verbose
        self.user_env = env

        self.src_dir = Path(self.env.get_source_dir(), self.subdir)
        self.build_dir = Path(self.env.get_build_dir(), self.subdir, 'build')
        self.install_dir = Path(self.env.get_build_dir(), self.subdir, 'dist')
        self.prefix = Path(self.env.coredata.get_option(OptionKey('prefix')))
        self.libdir = Path(self.env.coredata.get_option(OptionKey('libdir')))
        self.includedir = Path(self.env.coredata.get_option(OptionKey('includedir')))
        self.name = self.src_dir.name

        # On Windows if the prefix is "c:/foo" and DESTDIR is "c:/bar", `make`
        # will install files into "c:/bar/c:/foo" which is an invalid path.
        # Work around that issue by removing the drive from prefix.
        if self.prefix.drive:
            self.prefix = self.prefix.relative_to(self.prefix.drive)

        # self.prefix is an absolute path, so we cannot append it to another path.
        self.rel_prefix = self.prefix.relative_to(self.prefix.root)

        self.make = state.find_program('make')
        self.make = self.make.get_command()[0]

        self._configure(state)

        self.targets = self._create_targets()

    def _configure(self, state: ModuleState):
        # Assume it's the name of a script in source dir, like 'configure',
        # 'autogen.sh', etc).
        configure_path = Path(self.src_dir, self.configure_command)
        configure_prog = state.find_program(configure_path.as_posix())
        configure_cmd = configure_prog.get_command()

        d = [('PREFIX', '--prefix=@PREFIX@', self.prefix.as_posix()),
             ('LIBDIR', '--libdir=@PREFIX@/@LIBDIR@', self.libdir.as_posix()),
             ('INCLUDEDIR', None, self.includedir.as_posix()),
             ]
        self._validate_configure_options(d)

        configure_cmd += self._format_options(self.configure_options, d)

        if self.env.is_cross_build():
            host = '{}-{}-{}'.format(self.host_machine.cpu_family,
                                     self.build_machine.system,
                                     self.host_machine.system)
            d = [('HOST', None, host)]
            configure_cmd += self._format_options(self.cross_configure_options, d)

        # Set common env variables like CFLAGS, CC, etc.
        link_exelist = []
        link_args = []
        self.run_env = os.environ.copy()
        for lang, compiler in self.env.coredata.compilers[MachineChoice.HOST].items():
            if any(lang not in i for i in (CEXE_MAPPING, CFLAGS_MAPPING)):
                continue
            cargs = self.env.coredata.get_external_args(MachineChoice.HOST, lang)
            self.run_env[CEXE_MAPPING[lang]] = self._quote_and_join(compiler.get_exelist())
            self.run_env[CFLAGS_MAPPING[lang]] = self._quote_and_join(cargs)
            if not link_exelist:
                link_exelist = compiler.get_linker_exelist()
                link_args = self.env.coredata.get_external_link_args(MachineChoice.HOST, lang)
        if link_exelist:
            # FIXME: Do not pass linker because Meson uses CC as linker wrapper,
            # but autotools often expects the real linker (e.h. GNU ld).
            # self.run_env['LD'] = self._quote_and_join(link_exelist)
            pass
        self.run_env['LDFLAGS'] = self._quote_and_join(link_args)

        self.run_env = self.user_env.get_env(self.run_env)

        PkgConfigDependency.setup_env(self.run_env, self.env, MachineChoice.HOST,
                                      Path(self.env.get_build_dir(), 'meson-uninstalled').as_posix())

        self.build_dir.mkdir(parents=True, exist_ok=True)
        self._run('configure', configure_cmd)

    def _quote_and_join(self, array: T.List[str]) -> str:
        return ' '.join([shlex.quote(i) for i in array])

    def _validate_configure_options(self, variables: T.List[T.Tuple[str, str, str]]):
        # Ensure the user at least try to pass basic info to the build system,
        # like the prefix, libdir, etc.
        for key, default, val in variables:
            if default is None:
                continue
            key_format = f'@{key}@'
            for option in self.configure_options:
                if key_format in option:
                    break
            else:
                FeatureNew('Default configure_option', '0.57.0').use(self.subproject)
                self.configure_options.append(default)

    def _format_options(self, options: T.List[str], variables: T.List[T.Tuple[str, str, str]]) -> T.List[str]:
        out = []
        missing = set()
        regex = get_variable_regex('meson')
        confdata = {k: (v, None) for k, d, v in variables}
        for o in options:
            arg, missing_vars = do_replacement(regex, o, 'meson', confdata)
            missing.update(missing_vars)
            out.append(arg)
        if missing:
            var_list = ", ".join(map(repr, sorted(missing)))
            raise EnvironmentException(
                f"Variables {var_list} in configure options are missing.")
        return out

    def _run(self, step: str, command: T.List[str]):
        mlog.log(f'External project {self.name}:', mlog.bold(step))
        m = 'Running command ' + str(command) + ' in directory ' + str(self.build_dir) + '\n'
        log_filename = Path(mlog.log_dir, f'{self.name}-{step}.log')
        output = None
        if not self.verbose:
            output = open(log_filename, 'w', encoding='utf-8')
            output.write(m + '\n')
            output.flush()
        else:
            mlog.log(m)
        p, o, e = Popen_safe(command, cwd=str(self.build_dir), env=self.run_env,
                                      stderr=subprocess.STDOUT,
                                      stdout=output)
        if p.returncode != 0:
            m = f'{step} step returned error code {p.returncode}.'
            if not self.verbose:
                m += '\nSee logs: ' + str(log_filename)
            raise MesonException(m)

    def _create_targets(self):
        cmd = self.env.get_build_command()
        cmd += ['--internal', 'externalproject',
                '--name', self.name,
                '--srcdir', self.src_dir.as_posix(),
                '--builddir', self.build_dir.as_posix(),
                '--installdir', self.install_dir.as_posix(),
                '--logdir', mlog.log_dir,
                '--make', self.make,
                ]
        if self.verbose:
            cmd.append('--verbose')

        target_kwargs = {'output': f'{self.name}.stamp',
                         'depfile': f'{self.name}.d',
                         'command': cmd + ['@OUTPUT@', '@DEPFILE@'],
                         'console': True,
                         }
        self.target = build.CustomTarget(self.name,
                                         self.subdir.as_posix(),
                                         self.subproject,
                                         target_kwargs)

        idir = build.InstallDir(self.subdir.as_posix(),
                                Path('dist', self.rel_prefix).as_posix(),
                                install_dir='.',
                                install_mode=None,
                                exclude=None,
                                strip_directory=True,
                                from_source_dir=False,
                                subproject=self.subproject)

        return [self.target, idir]

    @permittedKwargs({'subdir'})
    @typed_pos_args('external_project.dependency', str)
    def dependency_method(self, state, args: T.Tuple[str], kwargs):
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
        compile_args = [f'-I{abs_includedir}']
        link_args = [f'-L{abs_libdir}', f'-l{libname}']
        libs = []
        libs_whole = []
        sources = self.target
        final_deps = []
        variables = []
        dep = InternalDependency(version, incdir, compile_args, link_args, libs,
                                 libs_whole, sources, final_deps, variables)
        return dep


class ExternalProjectModule(ExtensionModule):
    @FeatureNew('External build system Module', '0.56.0')
    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.methods.update({'add_project': self.add_project,
                             })

    @permittedKwargs({'configure_options', 'cross_configure_options', 'verbose', 'env'})
    @typed_pos_args('external_project_mod.add_project', str)
    def add_project(self, state: ModuleState, args: T.Tuple[str], kwargs: T.Dict[str, T.Any]):
        configure_command = args[0]
        configure_options = extract_as_list(kwargs, 'configure_options')
        cross_configure_options = extract_as_list(kwargs, 'cross_configure_options')
        if not cross_configure_options:
            cross_configure_options = ['--host=@HOST@']
        verbose = kwargs.get('verbose', False)
        env = self.interpreter.unpack_env_kwarg(kwargs)
        project = ExternalProject(state,
                                  configure_command,
                                  configure_options,
                                  cross_configure_options,
                                  env, verbose)
        return ModuleReturnValue(project, project.targets)


def initialize(*args, **kwargs):
    return ExternalProjectModule(*args, **kwargs)
