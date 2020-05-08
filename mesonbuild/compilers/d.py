# Copyright 2012-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os.path, subprocess
import typing as T

from ..mesonlib import (
    EnvironmentException, MachineChoice, version_compare,
)

from ..arglist import CompilerArgs
from .compilers import (
    d_dmd_buildtype_args,
    d_gdc_buildtype_args,
    d_ldc_buildtype_args,
    clike_debug_args,
    Compiler,
)
from .mixins.gnu import GnuCompiler

if T.TYPE_CHECKING:
    from .compilers import Compiler as CompilerMixinBase
    from ..dependencies import Dependency, ExternalProgram
    from ..envconfig import MachineInfo
    from ..environment import Environment
    from ..linkers import DynamicLinker
else:
    CompilerMixinBase = object

d_feature_args = {'gcc':  {'unittest': '-funittest',
                           'debug': '-fdebug',
                           'version': '-fversion',
                           'import_dir': '-J'
                           },
                  'llvm': {'unittest': '-unittest',
                           'debug': '-d-debug',
                           'version': '-d-version',
                           'import_dir': '-J'
                           },
                  'dmd':  {'unittest': '-unittest',
                           'debug': '-debug',
                           'version': '-version',
                           'import_dir': '-J'
                           }
                  }  # type: T.Dict[str, T.Dict[str, str]]

ldc_optimization_args = {'0': [],
                         'g': [],
                         '1': ['-O1'],
                         '2': ['-O2'],
                         '3': ['-O3'],
                         's': ['-Os'],
                         }  # type: T.Dict[str, T.List[str]]

dmd_optimization_args = {'0': [],
                         'g': [],
                         '1': ['-O'],
                         '2': ['-O'],
                         '3': ['-O'],
                         's': ['-O'],
                         }  # type: T.Dict[str, T.List[str]]


class DmdLikeCompilerMixin(CompilerMixinBase):

    """Mixin class for DMD and LDC.

    LDC has a number of DMD like arguments, and this class allows for code
    sharing between them as makes sense.
    """

    if T.TYPE_CHECKING:
        mscrt_args = {}  # type: T.Dict[str, T.List[str]]

        def _get_target_arch_args(self) -> T.List[str]: ...

    LINKER_PREFIX = '-L='

    def get_output_args(self, outputname: str) -> T.List[str]:
        return ['-of=' + outputname]

    def get_linker_output_args(self, outputname: str) -> T.List[str]:
        return ['-of=' + outputname]

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        return ['-I=' + path]

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str],
                                               build_dir: str) -> T.List[str]:
        for idx, i in enumerate(parameter_list):
            if i[:3] == '-I=':
                parameter_list[idx] = i[:3] + os.path.normpath(os.path.join(build_dir, i[3:]))
            if i[:4] == '-L-L':
                parameter_list[idx] = i[:4] + os.path.normpath(os.path.join(build_dir, i[4:]))
            if i[:5] == '-L=-L':
                parameter_list[idx] = i[:5] + os.path.normpath(os.path.join(build_dir, i[5:]))
            if i[:6] == '-Wl,-L':
                parameter_list[idx] = i[:6] + os.path.normpath(os.path.join(build_dir, i[6:]))

        return parameter_list

    def get_warn_args(self, level: str) -> T.List[str]:
        return ['-wi']

    def get_werror_args(self) -> T.List[str]:
        return ['-w']

    def get_coverage_args(self) -> T.List[str]:
        return ['-cov']

    def get_coverage_link_args(self) -> T.List[str]:
        return []

    def get_preprocess_only_args(self) -> T.List[str]:
        return ['-E']

    def get_compile_only_args(self) -> T.List[str]:
        return ['-c']

    def get_depfile_suffix(self) -> str:
        return 'deps'

    def get_pic_args(self) -> T.List[str]:
        if self.info.is_windows():
            return []
        return ['-fPIC']

    def get_feature_args(self, kwargs: T.Dict[str, T.Any], build_to_src: str) -> T.List[str]:
        # TODO: using a TypeDict here would improve this
        res = []
        if 'unittest' in kwargs:
            unittest = kwargs.pop('unittest')
            unittest_arg = d_feature_args[self.id]['unittest']
            if not unittest_arg:
                raise EnvironmentException('D compiler %s does not support the "unittest" feature.' % self.name_string())
            if unittest:
                res.append(unittest_arg)

        if 'debug' in kwargs:
            debug_level = -1
            debugs = kwargs.pop('debug')
            if not isinstance(debugs, list):
                debugs = [debugs]

            debug_arg = d_feature_args[self.id]['debug']
            if not debug_arg:
                raise EnvironmentException('D compiler %s does not support conditional debug identifiers.' % self.name_string())

            # Parse all debug identifiers and the largest debug level identifier
            for d in debugs:
                if isinstance(d, int):
                    if d > debug_level:
                        debug_level = d
                elif isinstance(d, str) and d.isdigit():
                    if int(d) > debug_level:
                        debug_level = int(d)
                else:
                    res.append('{0}={1}'.format(debug_arg, d))

            if debug_level >= 0:
                res.append('{0}={1}'.format(debug_arg, debug_level))

        if 'versions' in kwargs:
            version_level = -1
            versions = kwargs.pop('versions')
            if not isinstance(versions, list):
                versions = [versions]

            version_arg = d_feature_args[self.id]['version']
            if not version_arg:
                raise EnvironmentException('D compiler %s does not support conditional version identifiers.' % self.name_string())

            # Parse all version identifiers and the largest version level identifier
            for v in versions:
                if isinstance(v, int):
                    if v > version_level:
                        version_level = v
                elif isinstance(v, str) and v.isdigit():
                    if int(v) > version_level:
                        version_level = int(v)
                else:
                    res.append('{0}={1}'.format(version_arg, v))

            if version_level >= 0:
                res.append('{0}={1}'.format(version_arg, version_level))

        if 'import_dirs' in kwargs:
            import_dirs = kwargs.pop('import_dirs')
            if not isinstance(import_dirs, list):
                import_dirs = [import_dirs]

            import_dir_arg = d_feature_args[self.id]['import_dir']
            if not import_dir_arg:
                raise EnvironmentException('D compiler %s does not support the "string import directories" feature.' % self.name_string())
            for idir_obj in import_dirs:
                basedir = idir_obj.get_curdir()
                for idir in idir_obj.get_incdirs():
                    # Avoid superfluous '/.' at the end of paths when d is '.'
                    if idir not in ('', '.'):
                        expdir = os.path.join(basedir, idir)
                    else:
                        expdir = basedir
                    srctreedir = os.path.join(build_to_src, expdir)
                    res.append('{0}{1}'.format(import_dir_arg, srctreedir))

        if kwargs:
            raise EnvironmentException('Unknown D compiler feature(s) selected: %s' % ', '.join(kwargs.keys()))

        return res

    def get_buildtype_linker_args(self, buildtype: str) -> T.List[str]:
        if buildtype != 'plain':
            return self._get_target_arch_args()
        return []

    def gen_import_library_args(self, implibname: str) -> T.List[str]:
        return self.linker.import_library_args(implibname)

    def build_rpath_args(self, env: 'Environment', build_dir: str, from_dir: str,
                         rpath_paths: str, build_rpath: str,
                         install_rpath: str) -> T.Tuple[T.List[str], T.Set[bytes]]:
        if self.info.is_windows():
            return ([], set())

        # GNU ld, solaris ld, and lld acting like GNU ld
        if self.linker.id.startswith('ld'):
            # The way that dmd and ldc pass rpath to gcc is different than we would
            # do directly, each argument -rpath and the value to rpath, need to be
            # split into two separate arguments both prefaced with the -L=.
            args = []
            (rpath_args, rpath_dirs_to_remove) = super().build_rpath_args(
                    env, build_dir, from_dir, rpath_paths, build_rpath, install_rpath)
            for r in rpath_args:
                if ',' in r:
                    a, b = r.split(',', maxsplit=1)
                    args.append(a)
                    args.append(self.LINKER_PREFIX + b)
                else:
                    args.append(r)
            return (args, rpath_dirs_to_remove)

        return super().build_rpath_args(
            env, build_dir, from_dir, rpath_paths, build_rpath, install_rpath)

    def _translate_args_to_nongnu(self, args: T.List[str]) -> T.List[str]:
        dcargs = []
        # Translate common arguments to flags the LDC/DMD compilers
        # can understand.
        # The flags might have been added by pkg-config files,
        # and are therefore out of the user's control.
        for arg in args:
            # Translate OS specific arguments first.
            osargs = []  # type: T.List[str]
            if self.info.is_windows():
                osargs = self.translate_arg_to_windows(arg)
            elif self.info.is_darwin():
                osargs = self._translate_arg_to_osx(arg)
            if osargs:
                dcargs.extend(osargs)
                continue

            # Translate common D arguments here.
            if arg == '-pthread':
                continue
            if arg.startswith('-fstack-protector'):
                continue
            if arg.startswith('-D'):
                continue
            if arg.startswith('-Wl,'):
                # Translate linker arguments here.
                linkargs = arg[arg.index(',') + 1:].split(',')
                for la in linkargs:
                    dcargs.append('-L=' + la.strip())
                continue
            elif arg.startswith(('-link-defaultlib', '-linker', '-link-internally', '-linkonce-templates', '-lib')):
                # these are special arguments to the LDC linker call,
                # arguments like "-link-defaultlib-shared" do *not*
                # denote a library to be linked, but change the default
                # Phobos/DRuntime linking behavior, while "-linker" sets the
                # default linker.
                dcargs.append(arg)
                continue
            elif arg.startswith('-l'):
                # translate library link flag
                dcargs.append('-L=' + arg)
                continue
            elif arg.startswith('-isystem'):
                # translate -isystem system include path
                # this flag might sometimes be added by C library Cflags via
                # pkg-config.
                # NOTE: -isystem and -I are not 100% equivalent, so this is just
                # a workaround for the most common cases.
                if arg.startswith('-isystem='):
                    dcargs.append('-I=' + arg[9:])
                else:
                    dcargs.append('-I' + arg[8:])
                continue
            elif arg.startswith('-idirafter'):
                # same as -isystem, but appends the path instead
                if arg.startswith('-idirafter='):
                    dcargs.append('-I=' + arg[11:])
                else:
                    dcargs.append('-I' + arg[10:])
                continue
            elif arg.startswith('-L/') or arg.startswith('-L./'):
                # we need to handle cases where -L is set by e.g. a pkg-config
                # setting to select a linker search path. We can however not
                # unconditionally prefix '-L' with '-L' because the user might
                # have set this flag too to do what it is intended to for this
                # compiler (pass flag through to the linker)
                # Hence, we guess here whether the flag was intended to pass
                # a linker search path.

                # Make sure static library files are passed properly to the linker.
                if arg.endswith('.a') or arg.endswith('.lib'):
                    if arg.startswith('-L='):
                        farg = arg[3:]
                    else:
                        farg = arg[2:]
                    if len(farg) > 0 and not farg.startswith('-'):
                        dcargs.append('-L=' + farg)
                        continue

                dcargs.append('-L=' + arg)
                continue
            elif not arg.startswith('-') and arg.endswith(('.a', '.lib')):
                # ensure static libraries are passed through to the linker
                dcargs.append('-L=' + arg)
                continue
            else:
                dcargs.append(arg)

        return dcargs

    @classmethod
    def translate_arg_to_windows(cls, arg: str) -> T.List[str]:
        args = []
        if arg.startswith('-Wl,'):
            # Translate linker arguments here.
            linkargs = arg[arg.index(',') + 1:].split(',')
            for la in linkargs:
                if la.startswith('--out-implib='):
                    # Import library name
                    args.append('-L=/IMPLIB:' + la[13:].strip())
        elif arg.startswith('-mscrtlib='):
            args.append(arg)
            mscrtlib = arg[10:].lower()
            if cls is LLVMDCompiler:
                # Default crt libraries for LDC2 must be excluded for other
                # selected crt options.
                if mscrtlib != 'libcmt':
                    args.append('-L=/NODEFAULTLIB:libcmt')
                    args.append('-L=/NODEFAULTLIB:libvcruntime')

                # Fixes missing definitions for printf-functions in VS2017
                if mscrtlib.startswith('msvcrt'):
                    args.append('-L=/DEFAULTLIB:legacy_stdio_definitions.lib')

        return args

    @classmethod
    def _translate_arg_to_osx(cls, arg: str) -> T.List[str]:
        args = []
        if arg.startswith('-install_name'):
            args.append('-L=' + arg)
        return args

    def get_debug_args(self, is_debug: bool) -> T.List[str]:
        ddebug_args = []
        if is_debug:
            ddebug_args = [d_feature_args[self.id]['debug']]

        return clike_debug_args[is_debug] + ddebug_args

    def _get_crt_args(self, crt_val: str, buildtype: str) -> T.List[str]:
        if not self.info.is_windows():
            return []

        if crt_val in self.mscrt_args:
            return self.mscrt_args[crt_val]
        assert(crt_val in ['from_buildtype', 'static_from_buildtype'])

        dbg = 'mdd'
        rel = 'md'
        if crt_val == 'static_from_buildtype':
            dbg = 'mtd'
            rel = 'mt'

        # Match what build type flags used to do.
        if buildtype == 'plain':
            return []
        elif buildtype == 'debug':
            return self.mscrt_args[dbg]
        elif buildtype == 'debugoptimized':
            return self.mscrt_args[rel]
        elif buildtype == 'release':
            return self.mscrt_args[rel]
        elif buildtype == 'minsize':
            return self.mscrt_args[rel]
        else:
            assert(buildtype == 'custom')
            raise EnvironmentException('Requested C runtime based on buildtype, but buildtype is "custom".')

    def get_soname_args(self, env: 'Environment', prefix: str, shlib_name: str,
                        suffix: str, soversion: str,
                        darwin_versions: T.Tuple[str, str],
                        is_shared_module: bool) -> T.List[str]:
        sargs = super().get_soname_args(env, prefix, shlib_name, suffix,
                                        soversion, darwin_versions, is_shared_module)

        # LDC and DMD actually do use a linker, but they proxy all of that with
        # their own arguments
        if self.linker.id.startswith('ld.'):
            soargs = []
            for arg in sargs:
                a, b = arg.split(',', maxsplit=1)
                soargs.append(a)
                soargs.append(self.LINKER_PREFIX + b)
            return soargs
        elif self.linker.id.startswith('ld64'):
            soargs = []
            for arg in sargs:
                if not arg.startswith(self.LINKER_PREFIX):
                    soargs.append(self.LINKER_PREFIX + arg)
                else:
                    soargs.append(arg)
            return soargs
        else:
            return sargs

    def get_allow_undefined_link_args(self) -> T.List[str]:
        args = self.linker.get_allow_undefined_args()
        if self.info.is_darwin():
            # On macOS we're passing these options to the C compiler, but
            # they're linker options and need -Wl, so clang/gcc knows what to
            # do with them. I'm assuming, but don't know for certain, that
            # ldc/dmd do some kind of mapping internally for arguments they
            # understand, but pass arguments they don't understand directly.
            args = [a.replace('-L=', '-Xcc=-Wl,') for a in args]
        return args


class DCompilerArgs(CompilerArgs):
    prepend_prefixes = ('-I', '-L')
    dedup2_prefixes = ('-I', )


class DCompiler(Compiler):
    mscrt_args = {
        'none': ['-mscrtlib='],
        'md': ['-mscrtlib=msvcrt'],
        'mdd': ['-mscrtlib=msvcrtd'],
        'mt': ['-mscrtlib=libcmt'],
        'mtd': ['-mscrtlib=libcmtd'],
    }

    language = 'd'

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 info: 'MachineInfo', arch: str, *,
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None,
                 is_cross: bool = False):
        super().__init__(exelist, version, for_machine, info, linker=linker,
                         full_version=full_version, is_cross=is_cross)
        self.arch = arch
        self.exe_wrapper = exe_wrapper

    def sanity_check(self, work_dir: str, environment: 'Environment') -> None:
        source_name = os.path.join(work_dir, 'sanity.d')
        output_name = os.path.join(work_dir, 'dtest')
        with open(source_name, 'w') as ofile:
            ofile.write('''void main() { }''')
        pc = subprocess.Popen(self.exelist + self.get_output_args(output_name) + self._get_target_arch_args() + [source_name], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('D compiler %s can not compile programs.' % self.name_string())
        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper.get_command() + [output_name]
        else:
            cmdlist = [output_name]
        if subprocess.call(cmdlist) != 0:
            raise EnvironmentException('Executables created by D compiler %s are not runnable.' % self.name_string())

    def needs_static_linker(self) -> bool:
        return True

    def get_depfile_suffix(self) -> str:
        return 'deps'

    def get_pic_args(self) -> T.List[str]:
        if self.info.is_windows():
            return []
        return ['-fPIC']

    def get_feature_args(self, kwargs: T.Dict[str, T.Any], build_to_src: str) -> T.List[str]:
        # TODO: using a TypeDict here would improve this
        res = []
        if 'unittest' in kwargs:
            unittest = kwargs.pop('unittest')
            unittest_arg = d_feature_args[self.id]['unittest']
            if not unittest_arg:
                raise EnvironmentException('D compiler %s does not support the "unittest" feature.' % self.name_string())
            if unittest:
                res.append(unittest_arg)

        if 'debug' in kwargs:
            debug_level = -1
            debugs = kwargs.pop('debug')
            if not isinstance(debugs, list):
                debugs = [debugs]

            debug_arg = d_feature_args[self.id]['debug']
            if not debug_arg:
                raise EnvironmentException('D compiler %s does not support conditional debug identifiers.' % self.name_string())

            # Parse all debug identifiers and the largest debug level identifier
            for d in debugs:
                if isinstance(d, int):
                    if d > debug_level:
                        debug_level = d
                elif isinstance(d, str) and d.isdigit():
                    if int(d) > debug_level:
                        debug_level = int(d)
                else:
                    res.append('{0}={1}'.format(debug_arg, d))

            if debug_level >= 0:
                res.append('{0}={1}'.format(debug_arg, debug_level))

        if 'versions' in kwargs:
            version_level = -1
            versions = kwargs.pop('versions')
            if not isinstance(versions, list):
                versions = [versions]

            version_arg = d_feature_args[self.id]['version']
            if not version_arg:
                raise EnvironmentException('D compiler %s does not support conditional version identifiers.' % self.name_string())

            # Parse all version identifiers and the largest version level identifier
            for v in versions:
                if isinstance(v, int):
                    if v > version_level:
                        version_level = v
                elif isinstance(v, str) and v.isdigit():
                    if int(v) > version_level:
                        version_level = int(v)
                else:
                    res.append('{0}={1}'.format(version_arg, v))

            if version_level >= 0:
                res.append('{0}={1}'.format(version_arg, version_level))

        if 'import_dirs' in kwargs:
            import_dirs = kwargs.pop('import_dirs')
            if not isinstance(import_dirs, list):
                import_dirs = [import_dirs]

            import_dir_arg = d_feature_args[self.id]['import_dir']
            if not import_dir_arg:
                raise EnvironmentException('D compiler %s does not support the "string import directories" feature.' % self.name_string())
            for idir_obj in import_dirs:
                basedir = idir_obj.get_curdir()
                for idir in idir_obj.get_incdirs():
                    # Avoid superfluous '/.' at the end of paths when d is '.'
                    if idir not in ('', '.'):
                        expdir = os.path.join(basedir, idir)
                    else:
                        expdir = basedir
                    srctreedir = os.path.join(build_to_src, expdir)
                    res.append('{0}{1}'.format(import_dir_arg, srctreedir))

        if kwargs:
            raise EnvironmentException('Unknown D compiler feature(s) selected: %s' % ', '.join(kwargs.keys()))

        return res

    def get_buildtype_linker_args(self, buildtype: str) -> T.List[str]:
        if buildtype != 'plain':
            return self._get_target_arch_args()
        return []

    def compiler_args(self, args: T.Optional[T.Iterable[str]] = None) -> DCompilerArgs:
        return DCompilerArgs(self, args)

    def has_multi_arguments(self, args: T.List[str], env: 'Environment') -> T.Tuple[bool, bool]:
        return self.compiles('int i;\n', env, extra_args=args)

    def _get_target_arch_args(self) -> T.List[str]:
        # LDC2 on Windows targets to current OS architecture, but
        # it should follow the target specified by the MSVC toolchain.
        if self.info.is_windows():
            if self.arch == 'x86_64':
                return ['-m64']
            return ['-m32']
        return []

    def get_crt_compile_args(self, crt_val: str, buildtype: str) -> T.List[str]:
        return []

    def get_crt_link_args(self, crt_val: str, buildtype: str) -> T.List[str]:
        return []


class GnuDCompiler(GnuCompiler, DCompiler):

    # we mostly want DCompiler, but that gives us the Compiler.LINKER_PREFIX instead
    LINKER_PREFIX = GnuCompiler.LINKER_PREFIX

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 info: 'MachineInfo', arch: str, *,
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None,
                 is_cross: bool = False):
        DCompiler.__init__(self, exelist, version, for_machine, info, arch,
                           exe_wrapper=exe_wrapper, linker=linker,
                           full_version=full_version, is_cross=is_cross)
        GnuCompiler.__init__(self, {})
        self.id = 'gcc'
        default_warn_args = ['-Wall', '-Wdeprecated']
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}
        self.base_options = ['b_colorout', 'b_sanitize', 'b_staticpic',
                             'b_vscrt', 'b_coverage', 'b_pgo', 'b_ndebug']

        self._has_color_support = version_compare(self.version, '>=4.9')
        # dependencies were implemented before, but broken - support was fixed in GCC 7.1+
        # (and some backported versions)
        self._has_deps_support = version_compare(self.version, '>=7.1')

    def get_colorout_args(self, colortype: str) -> T.List[str]:
        if self._has_color_support:
            super().get_colorout_args(colortype)
        return []

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> T.List[str]:
        if self._has_deps_support:
            return super().get_dependency_gen_args(outtarget, outfile)
        return []

    def get_warn_args(self, level: str) -> T.List[str]:
        return self.warn_args[level]

    def get_buildtype_args(self, buildtype: str) -> T.List[str]:
        return d_gdc_buildtype_args[buildtype]

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str],
                                               build_dir: str) -> T.List[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list

    def get_allow_undefined_link_args(self) -> T.List[str]:
        return self.linker.get_allow_undefined_args()

    def get_linker_always_args(self) -> T.List[str]:
        args = super().get_linker_always_args()
        if self.info.is_windows():
            return args
        return args + ['-shared-libphobos']

    def get_disable_assert_args(self) -> T.List[str]:
        return ['-frelease']


class LLVMDCompiler(DmdLikeCompilerMixin, DCompiler):

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 info: 'MachineInfo', arch: str, *,
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None,
                 is_cross: bool = False):
        DCompiler.__init__(self, exelist, version, for_machine, info, arch,
                           exe_wrapper=exe_wrapper, linker=linker,
                           full_version=full_version, is_cross=is_cross)
        self.id = 'llvm'
        self.base_options = ['b_coverage', 'b_colorout', 'b_vscrt', 'b_ndebug']

    def get_colorout_args(self, colortype: str) -> T.List[str]:
        if colortype == 'always':
            return ['-enable-color']
        return []

    def get_warn_args(self, level: str) -> T.List[str]:
        if level in {'2', '3'}:
            return ['-wi', '-dw']
        elif level == '1':
            return ['-wi']
        return []

    def get_buildtype_args(self, buildtype: str) -> T.List[str]:
        if buildtype != 'plain':
            return self._get_target_arch_args() + d_ldc_buildtype_args[buildtype]
        return d_ldc_buildtype_args[buildtype]

    def get_pic_args(self) -> T.List[str]:
        return ['-relocation-model=pic']

    def get_crt_link_args(self, crt_val: str, buildtype: str) -> T.List[str]:
        return self._get_crt_args(crt_val, buildtype)

    def unix_args_to_native(self, args: T.List[str]) -> T.List[str]:
        return self._translate_args_to_nongnu(args)

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return ldc_optimization_args[optimization_level]

    @classmethod
    def use_linker_args(cls, linker: str) -> T.List[str]:
        return ['-linker={}'.format(linker)]

    def get_linker_always_args(self) -> T.List[str]:
        args = super().get_linker_always_args()
        if self.info.is_windows():
            return args
        return args + ['-link-defaultlib-shared']

    def get_disable_assert_args(self) -> T.List[str]:
        return ['--release']


class DmdDCompiler(DmdLikeCompilerMixin, DCompiler):

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 info: 'MachineInfo', arch: str, *,
                 exe_wrapper: T.Optional['ExternalProgram'] = None,
                 linker: T.Optional['DynamicLinker'] = None,
                 full_version: T.Optional[str] = None,
                 is_cross: bool = False):
        DCompiler.__init__(self, exelist, version, for_machine, info, arch,
                           exe_wrapper=exe_wrapper, linker=linker,
                           full_version=full_version, is_cross=is_cross)
        self.id = 'dmd'
        self.base_options = ['b_coverage', 'b_colorout', 'b_vscrt', 'b_ndebug']

    def get_colorout_args(self, colortype: str) -> T.List[str]:
        if colortype == 'always':
            return ['-color=on']
        return []

    def get_buildtype_args(self, buildtype: str) -> T.List[str]:
        if buildtype != 'plain':
            return self._get_target_arch_args() + d_dmd_buildtype_args[buildtype]
        return d_dmd_buildtype_args[buildtype]

    def get_std_exe_link_args(self) -> T.List[str]:
        if self.info.is_windows():
            # DMD links against D runtime only when main symbol is found,
            # so these needs to be inserted when linking static D libraries.
            if self.arch == 'x86_64':
                return ['phobos64.lib']
            elif self.arch == 'x86_mscoff':
                return ['phobos32mscoff.lib']
            return ['phobos.lib']
        return []

    def get_std_shared_lib_link_args(self) -> T.List[str]:
        libname = 'libphobos2.so'
        if self.info.is_windows():
            if self.arch == 'x86_64':
                libname = 'phobos64.lib'
            elif self.arch == 'x86_mscoff':
                libname = 'phobos32mscoff.lib'
            else:
                libname = 'phobos.lib'
        return ['-shared', '-defaultlib=' + libname]

    def _get_target_arch_args(self) -> T.List[str]:
        # DMD32 and DMD64 on 64-bit Windows defaults to 32-bit (OMF).
        # Force the target to 64-bit in order to stay consistent
        # across the different platforms.
        if self.info.is_windows():
            if self.arch == 'x86_64':
                return ['-m64']
            elif self.arch == 'x86_mscoff':
                return ['-m32mscoff']
            return ['-m32']
        return []

    def get_crt_compile_args(self, crt_val: str, buildtype: str) -> T.List[str]:
        return self._get_crt_args(crt_val, buildtype)

    def unix_args_to_native(self, args: T.List[str]) -> T.List[str]:
        return self._translate_args_to_nongnu(args)

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return dmd_optimization_args[optimization_level]

    def can_linker_accept_rsp(self) -> bool:
        return False

    def get_linker_always_args(self) -> T.List[str]:
        args = super().get_linker_always_args()
        if self.info.is_windows():
            return args
        return args + ['-defaultlib=phobos2', '-debuglib=phobos2']

    def get_disable_assert_args(self) -> T.List[str]:
        return ['-release']
