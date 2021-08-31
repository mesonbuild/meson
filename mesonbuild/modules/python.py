# Copyright 2018 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import shutil
import typing as T

from pathlib import Path
from .. import mesonlib
from ..mesonlib import MachineChoice, MesonException
from . import ExtensionModule
from ..interpreterbase import (
    noPosargs, noKwargs, permittedKwargs,
    InvalidArguments,
    FeatureNew, FeatureNewKwargs, disablerIfNotFound
)
from ..interpreter import ExternalProgramHolder, extract_required_kwarg, permitted_dependency_kwargs
from ..build import known_shmod_kwargs
from .. import mlog
from ..environment import detect_cpu_family
from ..dependencies import DependencyMethods, PkgConfigDependency, NotFoundDependency, SystemDependency
from ..programs import ExternalProgram, NonExistingExternalProgram

mod_kwargs = {'subdir'}
mod_kwargs.update(known_shmod_kwargs)
mod_kwargs -= {'name_prefix', 'name_suffix'}

class PythonDependency(SystemDependency):

    def __init__(self, python_holder, environment, kwargs):
        super().__init__('python', environment, kwargs)
        self.name = 'python'
        self.static = kwargs.get('static', False)
        self.embed = kwargs.get('embed', False)
        self.version = python_holder.version
        self.platform = python_holder.platform
        self.pkgdep = None
        self.variables = python_holder.variables
        self.paths = python_holder.paths
        self.link_libpython = python_holder.link_libpython
        self.info: T.Optional[T.Dict[str, str]] = None
        if mesonlib.version_compare(self.version, '>= 3.0'):
            self.major_version = 3
        else:
            self.major_version = 2

        # We first try to find the necessary python variables using pkgconfig
        if DependencyMethods.PKGCONFIG in self.methods and not python_holder.is_pypy:
            pkg_version = self.variables.get('LDVERSION') or self.version
            pkg_libdir = self.variables.get('LIBPC')
            pkg_embed = '-embed' if self.embed and mesonlib.version_compare(self.version, '>=3.8') else ''
            pkg_name = f'python-{pkg_version}{pkg_embed}'

            # If python-X.Y.pc exists in LIBPC, we will try to use it
            if pkg_libdir is not None and Path(os.path.join(pkg_libdir, f'{pkg_name}.pc')).is_file():
                old_pkg_libdir = os.environ.get('PKG_CONFIG_LIBDIR')
                old_pkg_path = os.environ.get('PKG_CONFIG_PATH')

                os.environ.pop('PKG_CONFIG_PATH', None)

                if pkg_libdir:
                    os.environ['PKG_CONFIG_LIBDIR'] = pkg_libdir

                try:
                    self.pkgdep = PkgConfigDependency(pkg_name, environment, kwargs)
                    mlog.debug(f'Found "{pkg_name}" via pkgconfig lookup in LIBPC ({pkg_libdir})')
                    py_lookup_method = 'pkgconfig'
                except MesonException as e:
                    mlog.debug(f'"{pkg_name}" could not be found in LIBPC ({pkg_libdir})')
                    mlog.debug(e)

                if old_pkg_path is not None:
                    os.environ['PKG_CONFIG_PATH'] = old_pkg_path

                if old_pkg_libdir is not None:
                    os.environ['PKG_CONFIG_LIBDIR'] = old_pkg_libdir
                else:
                    os.environ.pop('PKG_CONFIG_LIBDIR', None)
            else:
                mlog.debug(f'"{pkg_name}" could not be found in LIBPC ({pkg_libdir}), this is likely due to a relocated python installation')

            # If lookup via LIBPC failed, try to use fallback PKG_CONFIG_LIBDIR/PKG_CONFIG_PATH mechanisms
            if self.pkgdep is None or not self.pkgdep.found():
                try:
                    self.pkgdep = PkgConfigDependency(pkg_name, environment, kwargs)
                    mlog.debug(f'Found "{pkg_name}" via fallback pkgconfig lookup in PKG_CONFIG_LIBDIR/PKG_CONFIG_PATH')
                    py_lookup_method = 'pkgconfig-fallback'
                except MesonException as e:
                    mlog.debug(f'"{pkg_name}" could not be found via fallback pkgconfig lookup in PKG_CONFIG_LIBDIR/PKG_CONFIG_PATH')
                    mlog.debug(e)

        if self.pkgdep and self.pkgdep.found():
            self.compile_args = self.pkgdep.get_compile_args()
            self.link_args = self.pkgdep.get_link_args()
            self.is_found = True
            self.pcdep = self.pkgdep
        else:
            self.pkgdep = None

            # Finally, try to find python via SYSCONFIG as a final measure
            if DependencyMethods.SYSCONFIG in self.methods:
                if mesonlib.is_windows():
                    self._find_libpy_windows(environment)
                else:
                    self._find_libpy(python_holder, environment)
                if self.is_found:
                    mlog.debug(f'Found "python-{self.version}" via SYSCONFIG module')
                    py_lookup_method = 'sysconfig'

        if self.is_found:
            mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.green(f'YES ({py_lookup_method})'))
        else:
            mlog.log('Dependency', mlog.bold(self.name), 'found:', mlog.red('NO'))

    def _find_libpy(self, python_holder, environment):
        if python_holder.is_pypy:
            if self.major_version == 3:
                libname = 'pypy3-c'
            else:
                libname = 'pypy-c'
            libdir = os.path.join(self.variables.get('base'), 'bin')
            libdirs = [libdir]
        else:
            libname = f'python{self.version}'
            if 'DEBUG_EXT' in self.variables:
                libname += self.variables['DEBUG_EXT']
            if 'ABIFLAGS' in self.variables:
                libname += self.variables['ABIFLAGS']
            libdirs = []

        largs = self.clib_compiler.find_library(libname, environment, libdirs)
        if largs is not None:
            self.link_args = largs

        self.is_found = largs is not None or self.link_libpython

        inc_paths = mesonlib.OrderedSet([
            self.variables.get('INCLUDEPY'),
            self.paths.get('include'),
            self.paths.get('platinclude')])

        self.compile_args += ['-I' + path for path in inc_paths if path]

    def get_windows_python_arch(self):
        if self.platform == 'mingw':
            pycc = self.variables.get('CC')
            if pycc.startswith('x86_64'):
                return '64'
            elif pycc.startswith(('i686', 'i386')):
                return '32'
            else:
                mlog.log('MinGW Python built with unknown CC {!r}, please file'
                         'a bug'.format(pycc))
                return None
        elif self.platform == 'win32':
            return '32'
        elif self.platform in ('win64', 'win-amd64'):
            return '64'
        mlog.log(f'Unknown Windows Python platform {self.platform!r}')
        return None

    def get_windows_link_args(self):
        if self.platform.startswith('win'):
            vernum = self.variables.get('py_version_nodot')
            if self.static:
                libpath = Path('libs') / f'libpython{vernum}.a'
            else:
                comp = self.get_compiler()
                if comp.id == "gcc":
                    libpath = f'python{vernum}.dll'
                else:
                    libpath = Path('libs') / f'python{vernum}.lib'
            lib = Path(self.variables.get('base')) / libpath
        elif self.platform == 'mingw':
            if self.static:
                libname = self.variables.get('LIBRARY')
            else:
                libname = self.variables.get('LDLIBRARY')
            lib = Path(self.variables.get('LIBDIR')) / libname
        if not lib.exists():
            mlog.log('Could not find Python3 library {!r}'.format(str(lib)))
            return None
        return [str(lib)]

    def _find_libpy_windows(self, env):
        '''
        Find python3 libraries on Windows and also verify that the arch matches
        what we are building for.
        '''
        pyarch = self.get_windows_python_arch()
        if pyarch is None:
            self.is_found = False
            return
        arch = detect_cpu_family(env.coredata.compilers.host)
        if arch == 'x86':
            arch = '32'
        elif arch == 'x86_64':
            arch = '64'
        else:
            # We can't cross-compile Python 3 dependencies on Windows yet
            mlog.log(f'Unknown architecture {arch!r} for',
                     mlog.bold(self.name))
            self.is_found = False
            return
        # Pyarch ends in '32' or '64'
        if arch != pyarch:
            mlog.log('Need', mlog.bold(self.name), 'for {}-bit, but '
                     'found {}-bit'.format(arch, pyarch))
            self.is_found = False
            return
        # This can fail if the library is not found
        largs = self.get_windows_link_args()
        if largs is None:
            self.is_found = False
            return
        self.link_args = largs
        # Compile args
        inc_paths = mesonlib.OrderedSet([
            self.variables.get('INCLUDEPY'),
            self.paths.get('include'),
            self.paths.get('platinclude')])

        self.compile_args += ['-I' + path for path in inc_paths if path]

        # https://sourceforge.net/p/mingw-w64/mailman/message/30504611/
        if pyarch == '64' and self.major_version == 2:
            self.compile_args += ['-DMS_WIN64']

        self.is_found = True

    @staticmethod
    def get_methods():
        if mesonlib.is_windows():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.SYSCONFIG]
        elif mesonlib.is_osx():
            return [DependencyMethods.PKGCONFIG, DependencyMethods.EXTRAFRAMEWORK]
        else:
            return [DependencyMethods.PKGCONFIG, DependencyMethods.SYSCONFIG]

    def get_pkgconfig_variable(self, variable_name, kwargs):
        if self.pkgdep:
            return self.pkgdep.get_pkgconfig_variable(variable_name, kwargs)
        else:
            return super().get_pkgconfig_variable(variable_name, kwargs)


INTROSPECT_COMMAND = '''import sysconfig
import json
import sys

install_paths = sysconfig.get_paths(scheme='posix_prefix', vars={'base': '', 'platbase': '', 'installed_base': ''})

def links_against_libpython():
    from distutils.core import Distribution, Extension
    cmd = Distribution().get_command_obj('build_ext')
    cmd.ensure_finalized()
    return bool(cmd.get_libraries(Extension('dummy', [])))

print (json.dumps ({
  'variables': sysconfig.get_config_vars(),
  'paths': sysconfig.get_paths(),
  'install_paths': install_paths,
  'sys_paths': sys.path,
  'version': sysconfig.get_python_version(),
  'platform': sysconfig.get_platform(),
  'is_pypy': '__pypy__' in sys.builtin_module_names,
  'link_libpython': links_against_libpython(),
}))
'''

if T.TYPE_CHECKING:
    class PythonIntrospectionDict(TypedDict):

        install_paths: T.Dict[str, str]
        is_pypy: bool
        link_libpython: bool
        paths: T.Dict[str, str]
        platform: str
        suffix : str
        variables: T.Dict[str, str]
        version: str

class PythonExternalProgram(ExternalProgram):
    def __init__(self, name: str, command: T.Optional[T.List[str]] = None, ext_prog: T.Optional[ExternalProgram] = None):
        if ext_prog is None:
            super().__init__(name, command=command, silent=True)
        else:
            self.name = name
            self.command = ext_prog.command
            self.path = ext_prog.path
        self.info: 'PythonIntrospectionDict' = {
            'install_paths': {},
            'is_pypy': False,
            'link_libpython': False,
            'paths': {},
            'platform': 'sentinal',
            'variables': {},
            'version': '0.0',
        }

    def _check_version(self, version: str) -> bool:
        if self.name == 'python2':
            return mesonlib.version_compare(version, '< 3.0')
        elif self.name == 'python3':
            return mesonlib.version_compare(version, '>= 3.0')
        return True

    def sanity(self) -> bool:
        # Sanity check, we expect to have something that at least quacks in tune
        cmd = self.get_command() + ['-c', INTROSPECT_COMMAND]
        p, stdout, stderr = mesonlib.Popen_safe(cmd)
        try:
            info = json.loads(stdout)
        except json.JSONDecodeError:
            info = None
            mlog.debug('Could not introspect Python (%s): exit code %d' % (str(p.args), p.returncode))
            mlog.debug('Program stdout:\n')
            mlog.debug(stdout)
            mlog.debug('Program stderr:\n')
            mlog.debug(stderr)

        if info is not None and self._check_version(info['version']):
            variables = info['variables']
            info['suffix'] = variables.get('EXT_SUFFIX') or variables.get('SO') or variables.get('.so')
            self.info = T.cast('PythonIntrospectionDict', info)
            self.platlib = self._get_path('platlib')
            self.purelib = self._get_path('purelib')
            return True
        else:
            return False

    def _get_path(self, key: str) -> None:
        user_dir = str(Path.home())
        sys_paths = self.info['sys_paths']
        rel_path = self.info['install_paths'][key][1:]
        if not any(p.endswith(rel_path) for p in sys_paths if not p.startswith(user_dir)):
            # On Debian derivatives sysconfig install path is broken and is not
            # included in the locations python actually lookup.
            # See https://github.com/mesonbuild/meson/issues/8739.
            mlog.warning('Broken python installation detected. Python files',
                         'installed by Meson might not be found by python interpreter.',
                         once=True)
            if mesonlib.is_debianlike():
                rel_path = 'lib/python3/dist-packages'
        return rel_path


class PythonInstallation(ExternalProgramHolder):
    def __init__(self, python, interpreter):
        ExternalProgramHolder.__init__(self, python, interpreter)
        info = python.info
        prefix = self.interpreter.environment.coredata.get_option(mesonlib.OptionKey('prefix'))
        self.variables = info['variables']
        self.suffix = info['suffix']
        self.paths = info['paths']
        self.platlib_install_path = os.path.join(prefix, python.platlib)
        self.purelib_install_path = os.path.join(prefix, python.purelib)
        self.version = info['version']
        self.platform = info['platform']
        self.is_pypy = info['is_pypy']
        self.link_libpython = info['link_libpython']
        self.methods.update({
            'extension_module': self.extension_module_method,
            'dependency': self.dependency_method,
            'install_sources': self.install_sources_method,
            'get_install_dir': self.get_install_dir_method,
            'language_version': self.language_version_method,
            'found': self.found_method,
            'has_path': self.has_path_method,
            'get_path': self.get_path_method,
            'has_variable': self.has_variable_method,
            'get_variable': self.get_variable_method,
            'path': self.path_method,
        })

    @permittedKwargs(mod_kwargs)
    def extension_module_method(self, args, kwargs):
        if 'install_dir' in kwargs:
            if 'subdir' in kwargs:
                raise InvalidArguments('"subdir" and "install_dir" are mutually exclusive')
        else:
            subdir = kwargs.pop('subdir', '')
            if not isinstance(subdir, str):
                raise InvalidArguments('"subdir" argument must be a string.')

            kwargs['install_dir'] = os.path.join(self.platlib_install_path, subdir)

        # On macOS and some Linux distros (Debian) distutils doesn't link
        # extensions against libpython. We call into distutils and mirror its
        # behavior. See https://github.com/mesonbuild/meson/issues/4117
        if not self.link_libpython:
            new_deps = []
            for dep in mesonlib.extract_as_list(kwargs, 'dependencies'):
                if isinstance(dep, PythonDependency):
                    dep = dep.get_partial_dependency(compile_args=True)
                new_deps.append(dep)
            kwargs['dependencies'] = new_deps

        # msys2's python3 has "-cpython-36m.dll", we have to be clever
        # FIXME: explain what the specific cleverness is here
        split, suffix = self.suffix.rsplit('.', 1)
        args[0] += split

        kwargs['name_prefix'] = ''
        kwargs['name_suffix'] = suffix

        return self.interpreter.func_shared_module(None, args, kwargs)

    @permittedKwargs(permitted_dependency_kwargs | {'embed'})
    @FeatureNewKwargs('python_installation.dependency', '0.53.0', ['embed'])
    def dependency_method(self, args, kwargs):
        if args:
            mlog.warning('python_installation.dependency() does not take any '
                         'positional arguments. It always returns a Python '
                         'dependency. This will become an error in the future.',
                         location=self.interpreter.current_node)
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject)
        if disabled:
            mlog.log('Dependency', mlog.bold('python'), 'skipped: feature', mlog.bold(feature), 'disabled')
            dep = NotFoundDependency(self.interpreter.environment)
        else:
            dep = PythonDependency(self, self.interpreter.environment, kwargs)
            if required and not dep.found():
                raise mesonlib.MesonException('Python dependency not found')
        return dep

    @permittedKwargs(['pure', 'subdir'])
    def install_sources_method(self, args, kwargs):
        pure = kwargs.pop('pure', True)
        if not isinstance(pure, bool):
            raise InvalidArguments('"pure" argument must be a boolean.')

        subdir = kwargs.pop('subdir', '')
        if not isinstance(subdir, str):
            raise InvalidArguments('"subdir" argument must be a string.')

        if pure:
            kwargs['install_dir'] = os.path.join(self.purelib_install_path, subdir)
        else:
            kwargs['install_dir'] = os.path.join(self.platlib_install_path, subdir)

        return self.interpreter.func_install_data(None, args, kwargs)

    @noPosargs
    @permittedKwargs(['pure', 'subdir'])
    def get_install_dir_method(self, args, kwargs):
        pure = kwargs.pop('pure', True)
        if not isinstance(pure, bool):
            raise InvalidArguments('"pure" argument must be a boolean.')

        subdir = kwargs.pop('subdir', '')
        if not isinstance(subdir, str):
            raise InvalidArguments('"subdir" argument must be a string.')

        if pure:
            res = os.path.join(self.purelib_install_path, subdir)
        else:
            res = os.path.join(self.platlib_install_path, subdir)

        return res

    @noPosargs
    @noKwargs
    def language_version_method(self, args, kwargs):
        return self.version

    @noKwargs
    def has_path_method(self, args, kwargs):
        if len(args) != 1:
            raise InvalidArguments('has_path takes exactly one positional argument.')
        path_name = args[0]
        if not isinstance(path_name, str):
            raise InvalidArguments('has_path argument must be a string.')

        return path_name in self.paths

    @noKwargs
    def get_path_method(self, args, kwargs):
        if len(args) not in (1, 2):
            raise InvalidArguments('get_path must have one or two arguments.')
        path_name = args[0]
        if not isinstance(path_name, str):
            raise InvalidArguments('get_path argument must be a string.')

        try:
            path = self.paths[path_name]
        except KeyError:
            if len(args) == 2:
                path = args[1]
            else:
                raise InvalidArguments(f'{path_name} is not a valid path name')

        return path

    @noKwargs
    def has_variable_method(self, args, kwargs):
        if len(args) != 1:
            raise InvalidArguments('has_variable takes exactly one positional argument.')
        var_name = args[0]
        if not isinstance(var_name, str):
            raise InvalidArguments('has_variable argument must be a string.')

        return var_name in self.variables

    @noKwargs
    def get_variable_method(self, args, kwargs):
        if len(args) not in (1, 2):
            raise InvalidArguments('get_variable must have one or two arguments.')
        var_name = args[0]
        if not isinstance(var_name, str):
            raise InvalidArguments('get_variable argument must be a string.')

        try:
            var = self.variables[var_name]
        except KeyError:
            if len(args) == 2:
                var = args[1]
            else:
                raise InvalidArguments(f'{var_name} is not a valid variable name')

        return var

    @noPosargs
    @noKwargs
    @FeatureNew('Python module path method', '0.50.0')
    def path_method(self, args, kwargs):
        return super().path_method(args, kwargs)


class PythonModule(ExtensionModule):

    @FeatureNew('Python Module', '0.46.0')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.methods.update({
            'find_installation': self.find_installation,
        })

    # https://www.python.org/dev/peps/pep-0397/
    def _get_win_pythonpath(self, name_or_path):
        if name_or_path not in ['python2', 'python3']:
            return None
        if not shutil.which('py'):
            # program not installed, return without an exception
            return None
        ver = {'python2': '-2', 'python3': '-3'}[name_or_path]
        cmd = ['py', ver, '-c', "import sysconfig; print(sysconfig.get_config_var('BINDIR'))"]
        _, stdout, _ = mesonlib.Popen_safe(cmd)
        directory = stdout.strip()
        if os.path.exists(directory):
            return os.path.join(directory, 'python')
        else:
            return None


    @FeatureNewKwargs('python.find_installation', '0.49.0', ['disabler'])
    @FeatureNewKwargs('python.find_installation', '0.51.0', ['modules'])
    @disablerIfNotFound
    @permittedKwargs({'required', 'modules'})
    def find_installation(self, state, args, kwargs):
        feature_check = FeatureNew('Passing "feature" option to find_installation', '0.48.0')
        disabled, required, feature = extract_required_kwarg(kwargs, state.subproject, feature_check)
        want_modules = mesonlib.extract_as_list(kwargs, 'modules')  # type: T.List[str]
        found_modules = []    # type: T.List[str]
        missing_modules = []  # type: T.List[str]
        fallback = args[0] if args else ''
        display_name = fallback or 'python'

        if len(args) > 1:
            raise InvalidArguments('find_installation takes zero or one positional argument.')

        name_or_path = state.environment.lookup_binary_entry(MachineChoice.HOST, 'python')
        if name_or_path is None and args:
            name_or_path = fallback
            if not isinstance(name_or_path, str):
                raise InvalidArguments('find_installation argument must be a string.')

        if disabled:
            mlog.log('Program', name_or_path or 'python', 'found:', mlog.red('NO'), '(disabled by:', mlog.bold(feature), ')')
            return NonExistingExternalProgram()

        if not name_or_path:
            python = PythonExternalProgram('python3', mesonlib.python_command)
        else:
            tmp_python = ExternalProgram.from_entry(display_name, name_or_path)
            python = PythonExternalProgram(display_name, ext_prog=tmp_python)

            if not python.found() and mesonlib.is_windows():
                pythonpath = self._get_win_pythonpath(name_or_path)
                if pythonpath is not None:
                    name_or_path = pythonpath
                    python = PythonExternalProgram(name_or_path)

            # Last ditch effort, python2 or python3 can be named python
            # on various platforms, let's not give up just yet, if an executable
            # named python is available and has a compatible version, let's use
            # it
            if not python.found() and name_or_path in ['python2', 'python3']:
                python = PythonExternalProgram('python')

        if python.found() and want_modules:
            for mod in want_modules:
                p, out, err = mesonlib.Popen_safe(
                    python.command +
                    ['-c', f'import {mod}'])
                if p.returncode != 0:
                    missing_modules.append(mod)
                else:
                    found_modules.append(mod)

        msg = ['Program', python.name]
        if want_modules:
            msg.append('({})'.format(', '.join(want_modules)))
        msg.append('found:')
        if python.found() and not missing_modules:
            msg.extend([mlog.green('YES'), '({})'.format(' '.join(python.command))])
        else:
            msg.append(mlog.red('NO'))
        if found_modules:
            msg.append('modules:')
            msg.append(', '.join(found_modules))

        mlog.log(*msg)

        if not python.found():
            if required:
                raise mesonlib.MesonException('{} not found'.format(name_or_path or 'python'))
            return NonExistingExternalProgram()
        elif missing_modules:
            if required:
                raise mesonlib.MesonException('{} is missing modules: {}'.format(name_or_path or 'python', ', '.join(missing_modules)))
            return NonExistingExternalProgram()
        else:
            sane = python.sanity()

            if sane:
                return python
            else:
                if required:
                    raise mesonlib.MesonException(f'{python} is not a valid python or it is missing distutils')
                return NonExistingExternalProgram()

        raise mesonlib.MesonBugException('Unreachable code was reached (PythonModule.find_installation).')


def initialize(*args, **kwargs):
    mod = PythonModule(*args, **kwargs)
    mod.interpreter.append_holder_map(PythonExternalProgram, PythonInstallation)
    return mod
