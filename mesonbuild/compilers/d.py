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

from ..mesonlib import EnvironmentException, version_compare, is_windows, is_osx

from .compilers import (
    CompilerType,
    d_dmd_buildtype_args,
    d_gdc_buildtype_args,
    d_ldc_buildtype_args,
    get_gcc_soname_args,
    gnu_color_args,
    gnu_optimization_args,
    clike_debug_args,
    Compiler,
    CompilerArgs,
)

d_feature_args = {'gcc':  {'unittest': '-funittest',
                           'version': '-fversion',
                           'import_dir': '-J'
                           },
                  'llvm': {'unittest': '-unittest',
                           'version': '-d-version',
                           'import_dir': '-J'
                           },
                  'dmd':  {'unittest': '-unittest',
                           'version': '-version',
                           'import_dir': '-J'
                           }
                  }

ldc_optimization_args = {'0': [],
                         'g': [],
                         '1': ['-O1'],
                         '2': ['-O2'],
                         '3': ['-O3'],
                         's': ['-Os'],
                         }

dmd_optimization_args = {'0': [],
                         'g': [],
                         '1': ['-O'],
                         '2': ['-O'],
                         '3': ['-O'],
                         's': ['-O'],
                         }

class DCompiler(Compiler):
    mscrt_args = {
        'none': ['-mscrtlib='],
        'md': ['-mscrtlib=msvcrt'],
        'mdd': ['-mscrtlib=msvcrtd'],
        'mt': ['-mscrtlib=libcmt'],
        'mtd': ['-mscrtlib=libcmtd'],
    }

    def __init__(self, exelist, version, is_cross, arch, **kwargs):
        self.language = 'd'
        super().__init__(exelist, version, **kwargs)
        self.id = 'unknown'
        self.is_cross = is_cross
        self.arch = arch

    def sanity_check(self, work_dir, environment):
        source_name = os.path.join(work_dir, 'sanity.d')
        output_name = os.path.join(work_dir, 'dtest')
        with open(source_name, 'w') as ofile:
            ofile.write('''void main() { }''')
        pc = subprocess.Popen(self.exelist + self.get_output_args(output_name) + self.get_target_arch_args() + [source_name], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('D compiler %s can not compile programs.' % self.name_string())
        if subprocess.call(output_name) != 0:
            raise EnvironmentException('Executables created by D compiler %s are not runnable.' % self.name_string())

    def needs_static_linker(self):
        return True

    def name_string(self):
        return ' '.join(self.exelist)

    def get_exelist(self):
        return self.exelist

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_output_args(self, target):
        return ['-of=' + target]

    def get_linker_output_args(self, target):
        return ['-of=' + target]

    def get_include_args(self, path, is_system):
        return ['-I=' + path]

    def get_warn_args(self, level):
        return ['-wi']

    def get_werror_args(self):
        return ['-w']

    def get_dependency_gen_args(self, outtarget, outfile):
        # DMD and LDC does not currently return Makefile-compatible dependency info.
        return []

    def get_linker_search_args(self, dirname):
        # -L is recognized as "add this to the search path" by the linker,
        # while the compiler recognizes it as "pass to linker".
        return ['-Wl,-L' + dirname]

    def get_coverage_args(self):
        return ['-cov']

    def get_preprocess_only_args(self):
        return ['-E']

    def get_compile_only_args(self):
        return ['-c']

    def depfile_for_object(self, objfile):
        return objfile + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self):
        return 'deps'

    def get_pic_args(self):
        if is_windows():
            return []
        return ['-fPIC']

    def get_std_shared_lib_link_args(self):
        return ['-shared']

    def get_soname_args(self, *args):
        # FIXME: Make this work for cross-compiling
        if is_windows():
            return []
        elif is_osx():
            soname_args = get_gcc_soname_args(CompilerType.GCC_OSX, *args)
            if soname_args:
                return ['-Wl,' + ','.join(soname_args)]
            return []

        return get_gcc_soname_args(CompilerType.GCC_STANDARD, *args)

    def get_feature_args(self, kwargs, build_to_src):
        res = []
        if 'unittest' in kwargs:
            unittest = kwargs.pop('unittest')
            unittest_arg = d_feature_args[self.id]['unittest']
            if not unittest_arg:
                raise EnvironmentException('D compiler %s does not support the "unittest" feature.' % self.name_string())
            if unittest:
                res.append(unittest_arg)

        if 'versions' in kwargs:
            versions = kwargs.pop('versions')
            if not isinstance(versions, list):
                versions = [versions]

            version_arg = d_feature_args[self.id]['version']
            if not version_arg:
                raise EnvironmentException('D compiler %s does not support the "feature versions" feature.' % self.name_string())
            for v in versions:
                res.append('{0}={1}'.format(version_arg, v))

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

    def get_buildtype_linker_args(self, buildtype):
        if buildtype != 'plain':
            return self.get_target_arch_args()
        return []

    def get_std_exe_link_args(self):
        return []

    def gen_import_library_args(self, implibname):
        return ['-Wl,--out-implib=' + implibname]

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
        if is_windows():
            return []

        # This method is to be used by LDC and DMD.
        # GDC can deal with the verbatim flags.
        if not rpath_paths and not install_rpath:
            return []
        paths = ':'.join([os.path.join(build_dir, p) for p in rpath_paths])
        if build_rpath != '':
            paths += ':' + build_rpath
        if len(paths) < len(install_rpath):
            padding = 'X' * (len(install_rpath) - len(paths))
            if not paths:
                paths = padding
            else:
                paths = paths + ':' + padding
        return ['-Wl,-rpath,{}'.format(paths)]

    def _get_compiler_check_args(self, env, extra_args, dependencies, mode='compile'):
        if extra_args is None:
            extra_args = []
        elif isinstance(extra_args, str):
            extra_args = [extra_args]
        if dependencies is None:
            dependencies = []
        elif not isinstance(dependencies, list):
            dependencies = [dependencies]
        # Collect compiler arguments
        args = CompilerArgs(self)
        for d in dependencies:
            # Add compile flags needed by dependencies
            args += d.get_compile_args()
            if mode == 'link':
                # Add link flags needed to find dependencies
                args += d.get_link_args()

        if mode == 'compile':
            # Add DFLAGS from the env
            args += env.coredata.get_external_args(self.language)
        elif mode == 'link':
            # Add LDFLAGS from the env
            args += env.coredata.get_external_link_args(self.language)
        # extra_args must override all other arguments, so we add them last
        args += extra_args
        return args

    def compiles(self, code, env, extra_args=None, dependencies=None, mode='compile'):
        args = self._get_compiler_check_args(env, extra_args, dependencies, mode)

        with self.compile(code, args, mode) as p:
            return p.returncode == 0

    def has_multi_arguments(self, args, env):
        return self.compiles('int i;\n', env, extra_args=args)

    def get_target_arch_args(self):
        # LDC2 on Windows targets to current OS architecture, but
        # it should follow the target specified by the MSVC toolchain.
        if is_windows():
            if self.arch == 'x86_64':
                return ['-m64']
            return ['-m32']
        return []

    @classmethod
    def translate_args_to_nongnu(cls, args):
        dcargs = []
        # Translate common arguments to flags the LDC/DMD compilers
        # can understand.
        # The flags might have been added by pkg-config files,
        # and are therefore out of the user's control.
        for arg in args:
            # Translate OS specific arguments first.
            osargs = []
            if is_windows():
                osargs = cls.translate_arg_to_windows(arg)
            elif is_osx():
                osargs = cls.translate_arg_to_osx(arg)
            if osargs:
                dcargs.extend(osargs)
                continue

            # Translate common D arguments here.
            if arg == '-pthread':
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
            elif arg.startswith('-L'):
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

            dcargs.append(arg)

        return dcargs

    @classmethod
    def translate_arg_to_windows(cls, arg):
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
    def translate_arg_to_osx(cls, arg):
        args = []
        if arg.startswith('-install_name'):
            args.append('-L=' + arg)
        return args

    def get_debug_args(self, is_debug):
        return clike_debug_args[is_debug]

    def get_crt_args(self, crt_val, buildtype):
        if not is_windows():
            return []

        if crt_val in self.mscrt_args:
            return self.mscrt_args[crt_val]
        assert(crt_val == 'from_buildtype')

        # Match what build type flags used to do.
        if buildtype == 'plain':
            return []
        elif buildtype == 'debug':
            return self.mscrt_args['mdd']
        elif buildtype == 'debugoptimized':
            return self.mscrt_args['md']
        elif buildtype == 'release':
            return self.mscrt_args['md']
        elif buildtype == 'minsize':
            return self.mscrt_args['md']
        else:
            assert(buildtype == 'custom')
            raise EnvironmentException('Requested C runtime based on buildtype, but buildtype is "custom".')

    def get_crt_compile_args(self, crt_val, buildtype):
        return []

    def get_crt_link_args(self, crt_val, buildtype):
        return []

    def thread_link_flags(self, env):
        return ['-pthread']

class GnuDCompiler(DCompiler):
    def __init__(self, exelist, version, is_cross, arch, **kwargs):
        DCompiler.__init__(self, exelist, version, is_cross, arch, **kwargs)
        self.id = 'gcc'
        default_warn_args = ['-Wall', '-Wdeprecated']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}
        self.base_options = ['b_colorout', 'b_sanitize', 'b_staticpic', 'b_vscrt']

        self._has_color_support = version_compare(self.version, '>=4.9')
        # dependencies were implemented before, but broken - support was fixed in GCC 7.1+
        # (and some backported versions)
        self._has_deps_support = version_compare(self.version, '>=7.1')

    def get_colorout_args(self, colortype):
        if self._has_color_support:
            return gnu_color_args[colortype][:]
        return []

    def get_dependency_gen_args(self, outtarget, outfile):
        if not self._has_deps_support:
            return []
        return ['-MD', '-MQ', outtarget, '-MF', outfile]

    def get_output_args(self, target):
        return ['-o', target]

    def get_linker_output_args(self, target):
        return ['-o', target]

    def get_include_args(self, path, is_system):
        return ['-I' + path]

    def get_warn_args(self, level):
        return self.warn_args[level]

    def get_werror_args(self):
        return ['-Werror']

    def get_linker_search_args(self, dirname):
        return ['-L' + dirname]

    def get_coverage_args(self):
        return []

    def get_buildtype_args(self, buildtype):
        return d_gdc_buildtype_args[buildtype]

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
        return self.build_unix_rpath_args(build_dir, from_dir, rpath_paths, build_rpath, install_rpath)

    def get_optimization_args(self, optimization_level):
        return gnu_optimization_args[optimization_level]

class LLVMDCompiler(DCompiler):
    def __init__(self, exelist, version, is_cross, arch, **kwargs):
        DCompiler.__init__(self, exelist, version, is_cross, arch, **kwargs)
        self.id = 'llvm'
        self.base_options = ['b_coverage', 'b_colorout', 'b_vscrt']

    def get_colorout_args(self, colortype):
        if colortype == 'always':
            return ['-enable-color']
        return []

    def get_warn_args(self, level):
        if level == '2' or level == '3':
            return ['-wi', '-dw']
        else:
            return ['-wi']

    def get_buildtype_args(self, buildtype):
        if buildtype != 'plain':
            return self.get_target_arch_args() + d_ldc_buildtype_args[buildtype]
        return d_ldc_buildtype_args[buildtype]

    def get_pic_args(self):
        return ['-relocation-model=pic']

    def get_crt_link_args(self, crt_val, buildtype):
        return self.get_crt_args(crt_val, buildtype)

    @classmethod
    def unix_args_to_native(cls, args):
        return cls.translate_args_to_nongnu(args)

    def get_optimization_args(self, optimization_level):
        return ldc_optimization_args[optimization_level]


class DmdDCompiler(DCompiler):
    def __init__(self, exelist, version, is_cross, arch, **kwargs):
        DCompiler.__init__(self, exelist, version, is_cross, arch, **kwargs)
        self.id = 'dmd'
        self.base_options = ['b_coverage', 'b_colorout', 'b_vscrt']

    def get_colorout_args(self, colortype):
        if colortype == 'always':
            return ['-color=on']
        return []

    def get_buildtype_args(self, buildtype):
        if buildtype != 'plain':
            return self.get_target_arch_args() + d_dmd_buildtype_args[buildtype]
        return d_dmd_buildtype_args[buildtype]

    def get_std_exe_link_args(self):
        if is_windows():
            # DMD links against D runtime only when main symbol is found,
            # so these needs to be inserted when linking static D libraries.
            if self.arch == 'x86_64':
                return ['phobos64.lib']
            elif self.arch == 'x86_mscoff':
                return ['phobos32mscoff.lib']
            return ['phobos.lib']
        return []

    def get_std_shared_lib_link_args(self):
        return ['-shared', '-defaultlib=libphobos2.so']

    def get_target_arch_args(self):
        # DMD32 and DMD64 on 64-bit Windows defaults to 32-bit (OMF).
        # Force the target to 64-bit in order to stay consistent
        # across the different platforms.
        if is_windows():
            if self.arch == 'x86_64':
                return ['-m64']
            elif self.arch == 'x86_mscoff':
                return ['-m32mscoff']
            return ['-m32']
        return []

    def get_crt_compile_args(self, crt_val, buildtype):
        return self.get_crt_args(crt_val, buildtype)

    @classmethod
    def unix_args_to_native(cls, args):
        return cls.translate_args_to_nongnu(args)

    def get_optimization_args(self, optimization_level):
        return dmd_optimization_args[optimization_level]
