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

from ..mesonlib import EnvironmentException, version_compare

from .compilers import (
    GCC_STANDARD,
    d_dmd_buildtype_args,
    d_gdc_buildtype_args,
    d_ldc_buildtype_args,
    get_gcc_soname_args,
    gnu_color_args,
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

class DCompiler(Compiler):
    def __init__(self, exelist, version, is_cross, **kwargs):
        self.language = 'd'
        super().__init__(exelist, version, **kwargs)
        self.id = 'unknown'
        self.is_cross = is_cross

    def sanity_check(self, work_dir, environment):
        source_name = os.path.join(work_dir, 'sanity.d')
        output_name = os.path.join(work_dir, 'dtest')
        with open(source_name, 'w') as ofile:
            ofile.write('''void main() {
}
''')
        pc = subprocess.Popen(self.exelist + self.get_output_args(output_name) + [source_name], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('D compiler %s can not compile programs.' % self.name_string())
        if subprocess.call(output_name) != 0:
            raise EnvironmentException('Executables created by D compiler %s are not runnable.' % self.name_string())

    def needs_static_linker(self):
        return True

    def name_string(self):
        return ' '.join(self.exelist)

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_preprocess_only_args(self):
        return ['-E']

    def get_compile_only_args(self):
        return ['-c']

    def depfile_for_object(self, objfile):
        return objfile + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self):
        return 'deps'

    def get_pic_args(self):
        return ['-fPIC']

    def get_std_shared_lib_link_args(self):
        return ['-shared']

    def get_soname_args(self, prefix, shlib_name, suffix, soversion, is_shared_module):
        # FIXME: Make this work for Windows, MacOS and cross-compiling
        return get_gcc_soname_args(GCC_STANDARD, prefix, shlib_name, suffix, soversion, is_shared_module)

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
        return []

    def get_std_exe_link_args(self):
        return []

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
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
        return ['-L-rpath={}'.format(paths)]

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

    @classmethod
    def translate_args_to_nongnu(cls, args):
        dcargs = []
        # Translate common arguments to flags the LDC/DMD compilers
        # can understand.
        # The flags might have been added by pkg-config files,
        # and are therefore out of the user's control.
        for arg in args:
            if arg == '-pthread':
                continue
            if arg.startswith('-Wl,'):
                linkargs = arg[arg.index(',') + 1:].split(',')
                for la in linkargs:
                    dcargs.append('-L' + la.strip())
                continue
            elif arg.startswith('-l'):
                # translate library link flag
                dcargs.append('-L' + arg)
                continue
            elif arg.startswith('-L/') or arg.startswith('-L./'):
                # we need to handle cases where -L is set by e.g. a pkg-config
                # setting to select a linker search path. We can however not
                # unconditionally prefix '-L' with '-L' because the user might
                # have set this flag too to do what it is intended to for this
                # compiler (pass flag through to the linker)
                # Hence, we guess here whether the flag was intended to pass
                # a linker search path.
                dcargs.append('-L' + arg)
                continue
            dcargs.append(arg)

        return dcargs


class GnuDCompiler(DCompiler):
    def __init__(self, exelist, version, is_cross, **kwargs):
        DCompiler.__init__(self, exelist, version, is_cross, **kwargs)
        self.id = 'gcc'
        default_warn_args = ['-Wall', '-Wdeprecated']
        self.warn_args = {'1': default_warn_args,
                          '2': default_warn_args + ['-Wextra'],
                          '3': default_warn_args + ['-Wextra', '-Wpedantic']}
        self.base_options = ['b_colorout', 'b_sanitize', 'b_staticpic']

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

    def get_buildtype_args(self, buildtype):
        return d_gdc_buildtype_args[buildtype]

    def build_rpath_args(self, build_dir, from_dir, rpath_paths, build_rpath, install_rpath):
        return self.build_unix_rpath_args(build_dir, from_dir, rpath_paths, build_rpath, install_rpath)


class LLVMDCompiler(DCompiler):
    def __init__(self, exelist, version, is_cross, **kwargs):
        DCompiler.__init__(self, exelist, version, is_cross, **kwargs)
        self.id = 'llvm'
        self.base_options = ['b_coverage', 'b_colorout']

    def get_colorout_args(self, colortype):
        if colortype == 'always':
            return ['-enable-color']
        return []

    def get_dependency_gen_args(self, outtarget, outfile):
        # LDC using the -deps flag returns a non-Makefile dependency-info file, which
        # the backends can not use. So we disable this feature for now.
        return []

    def get_output_args(self, target):
        return ['-of', target]

    def get_linker_output_args(self, target):
        return ['-of', target]

    def get_include_args(self, path, is_system):
        return ['-I' + path]

    def get_warn_args(self, level):
        if level == '2' or level == '3':
            return ['-wi', '-dw']
        else:
            return ['-wi']

    def get_werror_args(self):
        return ['-w']

    def get_coverage_args(self):
        return ['-cov']

    def get_buildtype_args(self, buildtype):
        return d_ldc_buildtype_args[buildtype]

    def get_pic_args(self):
        return ['-relocation-model=pic']

    def get_linker_search_args(self, dirname):
        # -L is recognized as "add this to the search path" by the linker,
        # while the compiler recognizes it as "pass to linker". So, the first
        # -L is for the compiler, telling it to pass the second -L to the linker.
        return ['-L-L' + dirname]

    @classmethod
    def unix_args_to_native(cls, args):
        return cls.translate_args_to_nongnu(args)


class DmdDCompiler(DCompiler):
    def __init__(self, exelist, version, is_cross, **kwargs):
        DCompiler.__init__(self, exelist, version, is_cross, **kwargs)
        self.id = 'dmd'
        self.base_options = ['b_coverage', 'b_colorout']

    def get_colorout_args(self, colortype):
        if colortype == 'always':
            return ['-color=on']
        return []

    def get_dependency_gen_args(self, outtarget, outfile):
        # LDC using the -deps flag returns a non-Makefile dependency-info file, which
        # the backends can not use. So we disable this feature for now.
        return []

    def get_output_args(self, target):
        return ['-of' + target]

    def get_werror_args(self):
        return ['-w']

    def get_linker_output_args(self, target):
        return ['-of' + target]

    def get_include_args(self, path, is_system):
        return ['-I' + path]

    def get_warn_args(self, level):
        return ['-wi']

    def get_coverage_args(self):
        return ['-cov']

    def get_linker_search_args(self, dirname):
        # -L is recognized as "add this to the search path" by the linker,
        # while the compiler recognizes it as "pass to linker". So, the first
        # -L is for the compiler, telling it to pass the second -L to the linker.
        return ['-L-L' + dirname]

    def get_buildtype_args(self, buildtype):
        return d_dmd_buildtype_args[buildtype]

    def get_std_shared_lib_link_args(self):
        return ['-shared', '-defaultlib=libphobos2.so']

    @classmethod
    def unix_args_to_native(cls, args):
        return cls.translate_args_to_nongnu(args)
