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

from . import ExtensionModule, ModuleReturnValue
from .. import mlog, build
from ..mesonlib import MesonException, Popen_safe, OrderedSet, is_windows, MachineChoice
from ..interpreterbase import InterpreterObject, InterpreterException, FeatureNew
from ..interpreterbase import noKwargs, noPosargs, stringArgs, permittedKwargs
from ..interpreter import DependencyHolder, InstallDir
from ..compilers.compilers import cflags_mapping, cexe_mapping
from ..dependencies.base import InternalDependency, DependencyException, PkgConfigDependency

class ExternalProject(InterpreterObject):
    def __init__(self, subdir, project_version, subproject, environment, build_machine, host_machine,
                 configure_command, configure_options, configure_cross_options,
                 verbose):
        InterpreterObject.__init__(self)
        self.methods.update({'dependency': self.dependency_method,
                             })

        self.subdir = subdir
        self.project_version = project_version
        self.subproject = subproject
        self.env = environment
        self.build_machine = build_machine
        self.host_machine = host_machine
        self.configure_command = configure_command
        self.configure_options = configure_options
        self.configure_cross_options = configure_cross_options
        self.verbose = verbose

        self.name = os.path.basename(self.subdir)
        self.src_dir = os.path.join(self.env.get_source_dir(), self.subdir)
        self.build_dir = os.path.join(self.env.get_build_dir(), self.subdir, 'build')
        self.install_dir = os.path.join(self.env.get_build_dir(), self.subdir, 'dist')
        self.prefix = self.env.coredata.get_builtin_option('prefix')
        self.libdir = self.env.coredata.get_builtin_option('libdir')
        self.includedir = self.env.coredata.get_builtin_option('includedir')

        # self.prefix is an absolute path, so we cannot use it in
        # os.path.join(something, self.prefix). On Windows 'c:/some/path' is
        # first split into ('c:', '/some/path') and then we keep only
        # 'some/path'.
        self.rel_prefix = os.path.splitdrive(self.prefix)[1][1:]

        self._configure()

    def _configure(self):
        if not os.path.exists(self.build_dir):
            os.makedirs(self.build_dir)

        # Assume it's the name of a script in source dir, like 'configure',
        # 'autogen.sh', etc).
        configure_cmd = [os.path.join(self.src_dir, self.configure_command)]

        d = {'prefix': self.prefix,
             'libdir': self.libdir,
             'includedir': self.includedir,
             }
        self._validate_configure_options(d.keys())
        configure_cmd += [arg.format(**d) for arg in self.configure_options]

        if self.env.is_cross_build():
            host = '{}-{}-{}'.format(self.host_machine.cpu_family,
                                     self.build_machine.system,
                                     self.host_machine.system)
            d = {'host': host}
            configure_cmd += [arg.format(**d) for arg in self.configure_cross_options]

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
        PkgConfigDependency.setup_env(self.run_env, self.env, MachineChoice.HOST,
                                      os.path.join(self.env.get_build_dir(), 'meson-uninstalled'))
        self._run('configure', configure_cmd)

    def _quote_and_join(self, array):
        return ' '.join([shlex.quote(i) for i in array])

    def _validate_configure_options(self, required_keys):
        # Ensure the user at least try to pass basic info to the build system,
        # like the prefix, libdir, etc.
        for key in required_keys:
            key_format = '{%s}' % key
            for option in self.configure_options:
                if key_format in option:
                    break
            else:
                m = 'At least one configure option must contain "{}" key'
                raise InterpreterException(m.format(key_format))

    def _run(self, step, command):
        mlog.log('External project {}:'.format(self.name), mlog.bold(step))
        if is_windows():
            command = ['sh', '-c', self._quote_and_join(command)]
        output = None if self.verbose else subprocess.DEVNULL
        p, o, e = Popen_safe(command, cwd=self.build_dir, env=self.run_env,
                                      stderr=subprocess.STDOUT,
                                      stdout=output)
        if p.returncode != 0:
            m = '{} step failed:\n{}'.format(step, e)
            raise MesonException(m)

    def _get_targets(self):
        cmd = self.env.get_build_command()
        cmd += ['--internal', 'externalproject',
                '--name', self.name,
                '--srcdir', self.src_dir,
                '--builddir', self.build_dir,
                '--installdir', self.install_dir,
                ]
        if self.verbose:
            cmd.append('--verbose')

        target_kwargs = {'output': '{}.stamp'.format(self.name),
                         'depfile': '{}.d'.format(self.name),
                         'command': cmd + ['@OUTPUT@', '@DEPFILE@'],
                         'console': True,
                         }
        self.target = build.CustomTarget(self.name,
                                         self.subdir,
                                         self.subproject,
                                         target_kwargs)

        idir = InstallDir(self.subdir,
                          os.path.join('dist', self.rel_prefix),
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

        abs_includedir = os.path.join(self.install_dir, self.rel_prefix, self.includedir)
        if subdir:
            abs_includedir = os.path.join(abs_includedir, subdir)
        abs_libdir = os.path.join(self.install_dir, self.rel_prefix, self.libdir)

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
    @FeatureNew('External build system Module', '0.55.0')
    def __init__(self, interpreter):
        super().__init__(interpreter)

    @stringArgs
    @permittedKwargs({'options', 'cross_options', 'verbose'})
    def add_project(self, state, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('add_project takes exactly one positional argument')
        configure_command = args[0]
        configure_options = kwargs.get('options', [])
        configure_cross_options = kwargs.get('cross_options', ['--host={host}'])
        verbose = kwargs.get('verbose', False)
        project = ExternalProject(state.subdir,
                                  state.project_version,
                                  state.subproject,
                                  state.environment,
                                  state.build_machine,
                                  state.host_machine,
                                  configure_command,
                                  configure_options,
                                  configure_cross_options,
                                  verbose)
        targets = project._get_targets()
        return ModuleReturnValue(project, targets)


def initialize(*args, **kwargs):
    return ExternalProjectModule(*args, **kwargs)
