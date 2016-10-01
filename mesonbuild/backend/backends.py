# Copyright 2012-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, pickle, re
from .. import build
from .. import dependencies
from .. import mesonlib
from .. import compilers
import json
import subprocess
from ..mesonlib import MesonException

class InstallData():
    def __init__(self, source_dir, build_dir, prefix):
        self.source_dir = source_dir
        self.build_dir= build_dir
        self.prefix = prefix
        self.targets = []
        self.headers = []
        self.man = []
        self.data = []
        self.po_package_name = ''
        self.po = []
        self.install_scripts = []
        self.install_subdirs = []

class ExecutableSerialisation():
    def __init__(self, name, fname, cmd_args, env, is_cross, exe_wrapper,
                 workdir, extra_paths, capture):
        self.name = name
        self.fname = fname
        self.cmd_args = cmd_args
        self.env = env
        self.is_cross = is_cross
        self.exe_runner = exe_wrapper
        self.workdir = workdir
        self.extra_paths = extra_paths
        self.capture = capture

class TestSerialisation:
    def __init__(self, name, suite, fname, is_cross, exe_wrapper, is_parallel, cmd_args, env,
                 should_fail, valgrind_args, timeout, workdir, extra_paths):
        self.name = name
        self.suite = suite
        self.fname = fname
        self.is_cross = is_cross
        self.exe_runner = exe_wrapper
        self.is_parallel = is_parallel
        self.cmd_args = cmd_args
        self.env = env
        self.should_fail = should_fail
        self.valgrind_args = valgrind_args
        self.timeout = timeout
        self.workdir = workdir
        self.extra_paths = extra_paths

# This class contains the basic functionality that is needed by all backends.
# Feel free to move stuff in and out of it as you see fit.
class Backend():
    def __init__(self, build):
        self.build = build
        self.environment = build.environment
        self.processed_targets = {}
        self.build_to_src = os.path.relpath(self.environment.get_source_dir(),
                                            self.environment.get_build_dir())
        for t in self.build.targets:
            priv_dirname = self.get_target_private_dir_abs(t)
            os.makedirs(priv_dirname, exist_ok=True)

    def get_compiler_for_lang(self, lang):
        for i in self.build.compilers:
            if i.language == lang:
                return i
        raise RuntimeError('No compiler for language ' + lang)

    def get_compiler_for_source(self, src, is_cross):
        comp = self.build.cross_compilers if is_cross else self.build.compilers
        for i in comp:
            if i.can_compile(src):
                return i
        if isinstance(src, mesonlib.File):
            src = src.fname
        raise RuntimeError('No specified compiler can handle file ' + src)

    def get_target_filename(self, target):
        assert(isinstance(target, (build.BuildTarget, build.CustomTarget)))
        targetdir = self.get_target_dir(target)
        fname = target.get_filename()
        if isinstance(fname, list):
            # FIXME FIXME FIXME: build.CustomTarget has multiple output files
            # and get_filename() returns them all
            fname = fname[0]
        filename = os.path.join(targetdir, fname)
        return filename

    def get_target_filename_abs(self, target):
        return os.path.join(self.environment.get_build_dir(), self.get_target_filename(target))

    def get_target_filename_for_linking(self, target):
        # On some platforms (msvc for instance), the file that is used for
        # dynamic linking is not the same as the dynamic library itself. This
        # file is called an import library, and we want to link against that.
        # On all other platforms, we link to the library directly.
        if isinstance(target, build.SharedLibrary):
            link_lib = target.get_import_filename() or target.get_filename()
            return os.path.join(self.get_target_dir(target), link_lib)
        elif isinstance(target, build.StaticLibrary):
            return os.path.join(self.get_target_dir(target), target.get_filename())
        raise AssertionError('BUG: Tried to link to something that\'s not a library')

    def get_target_debug_filename(self, target):
        fname = target.get_debug_filename()
        if not fname:
            raise AssertionError("BUG: Tried to generate debug filename when it doesn't exist")
        return os.path.join(self.get_target_dir(target), fname)

    def get_target_dir(self, target):
        if self.environment.coredata.get_builtin_option('layout') == 'mirror':
            dirname = target.get_subdir()
        else:
            dirname = 'meson-out'
        return dirname

    def get_target_private_dir(self, target):
        dirname = os.path.join(self.get_target_dir(target), target.get_basename() + target.type_suffix())
        return dirname

    def get_target_private_dir_abs(self, target):
        dirname = os.path.join(self.environment.get_build_dir(), self.get_target_private_dir(target))
        return dirname

    def generate_unity_files(self, target, unity_src):
        langlist = {}
        abs_files = []
        result = []

        def init_language_file(language, suffix):
            outfilename = os.path.join(self.get_target_private_dir_abs(target),
                                       target.name + '-unity' + suffix)
            outfileabs = os.path.join(self.environment.get_build_dir(),
                                      outfilename)
            outfileabs_tmp = outfileabs + '.tmp'
            abs_files.append(outfileabs)
            outfileabs_tmp_dir = os.path.dirname(outfileabs_tmp)
            if not os.path.exists(outfileabs_tmp_dir):
                os.makedirs(outfileabs_tmp_dir)
            result.append(outfilename)
            return open(outfileabs_tmp, 'w')

        try:
            for src in unity_src:
                comp = self.get_compiler_for_source(src, target.is_cross)
                language = comp.get_language()
                try:
                    ofile = langlist[language]
                except KeyError:
                    suffix = '.' + comp.get_default_suffix()
                    ofile = langlist[language] = init_language_file(language,
                                                                    suffix)
                ofile.write('#include<%s>\n' % src)
        finally:
            for x in langlist.values():
                x.close()
        [mesonlib.replace_if_different(x, x + '.tmp') for x in abs_files]
        return result

    def relpath(self, todir, fromdir):
        return os.path.relpath(os.path.join('dummyprefixdir', todir),\
                               os.path.join('dummyprefixdir', fromdir))

    def flatten_object_list(self, target, proj_dir_to_build_root=''):
        obj_list = []
        for obj in target.get_objects():
            if isinstance(obj, str):
                o = os.path.join(proj_dir_to_build_root,
                                 self.build_to_src, target.get_subdir(), obj)
                obj_list.append(o)
            elif isinstance(obj, build.ExtractedObjects):
                obj_list += self.determine_ext_objs(obj, proj_dir_to_build_root)
            else:
                raise MesonException('Unknown data type in object list.')
        return obj_list

    def serialise_executable(self, exe, cmd_args, workdir, env={},
                             capture=None):
        import uuid
        # Can't just use exe.name here; it will likely be run more than once
        if isinstance(exe, (dependencies.ExternalProgram,
                            build.BuildTarget, build.CustomTarget)):
            basename = exe.name
        else:
            basename = os.path.basename(exe)
        scratch_file = 'meson_exe_{0}_{1}.dat'.format(basename,
                                                      str(uuid.uuid4())[:8])
        exe_data = os.path.join(self.environment.get_scratch_dir(), scratch_file)
        with open(exe_data, 'wb') as f:
            if isinstance(exe, dependencies.ExternalProgram):
                exe_fullpath = exe.fullpath
            elif isinstance(exe, (build.BuildTarget, build.CustomTarget)):
                exe_fullpath = [self.get_target_filename_abs(exe)]
            else:
                exe_fullpath = [exe]
            is_cross = self.environment.is_cross_build() and \
                self.environment.cross_info.need_cross_compiler() and \
                self.environment.cross_info.need_exe_wrapper()
            if is_cross:
                exe_wrapper = self.environment.cross_info.config['binaries'].get('exe_wrapper', None)
            else:
                exe_wrapper = None
            if mesonlib.is_windows():
                extra_paths = self.determine_windows_extra_paths(exe)
            else:
                extra_paths = []
            es = ExecutableSerialisation(basename, exe_fullpath, cmd_args, env,
                                         is_cross, exe_wrapper, workdir,
                                         extra_paths, capture)
            pickle.dump(es, f)
        return exe_data

    def serialise_tests(self):
        test_data = os.path.join(self.environment.get_scratch_dir(), 'meson_test_setup.dat')
        with open(test_data, 'wb') as datafile:
            self.write_test_file(datafile)
        benchmark_data = os.path.join(self.environment.get_scratch_dir(), 'meson_benchmark_setup.dat')
        with open(benchmark_data, 'wb') as datafile:
            self.write_benchmark_file(datafile)
        return (test_data, benchmark_data)

    def determine_linker(self, target, src):
        if isinstance(target, build.StaticLibrary):
            if self.build.static_cross_linker is not None:
                return self.build.static_cross_linker
            else:
                return self.build.static_linker
        if len(self.build.compilers) == 1:
            return self.build.compilers[0]
        # Currently a bit naive. C++ must
        # be linked with a C++ compiler, but
        # otherwise we don't care. This will
        # become trickier if and when Fortran
        # and the like become supported.
        cpp = None
        for c in self.build.compilers:
            if c.get_language() == 'cpp':
                cpp = c
                break
        if cpp is not None:
            for s in src:
                if c.can_compile(s):
                    return cpp
        for c in self.build.compilers:
            if c.get_language() == 'vala':
                continue
            for s in src:
                if c.can_compile(s):
                    return c
        raise RuntimeError('Unreachable code')

    def object_filename_from_source(self, target, source):
        return source.fname.replace('/', '_').replace('\\', '_') + '.' + self.environment.get_object_suffix()

    def determine_ext_objs(self, extobj, proj_dir_to_build_root=''):
        result = []
        targetdir = self.get_target_private_dir(extobj.target)
        for osrc in extobj.srclist:
            # If extracting in a subproject, the subproject
            # name gets duplicated in the file name.
            pathsegs = osrc.subdir.split(os.sep)
            if pathsegs[0] == 'subprojects':
                pathsegs = pathsegs[2:]
            fixedpath = os.sep.join(pathsegs)
            objname = os.path.join(proj_dir_to_build_root, targetdir,
                                   self.object_filename_from_source(extobj.target, osrc))
            result.append(objname)
        return result

    def get_pch_include_args(self, compiler, target):
        args = []
        pchpath = self.get_target_private_dir(target)
        includeargs = compiler.get_include_args(pchpath, False)
        for lang in ['c', 'cpp']:
            p = target.get_pch(lang)
            if len(p) == 0:
                continue
            if compiler.can_compile(p[-1]):
                header = p[0]
                args += compiler.get_pch_use_args(pchpath, header)
        if len(args) > 0:
            args = includeargs + args
        return args

    @staticmethod
    def escape_extra_args(compiler, args):
        # No extra escaping/quoting needed when not running on Windows
        if not mesonlib.is_windows():
            return args
        extra_args = []
        # Compiler-specific escaping is needed for -D args but not for any others
        if compiler.get_id() == 'msvc':
            # MSVC needs escaping when a -D argument ends in \ or \"
            for arg in args:
                if arg.startswith('-D') or arg.startswith('/D'):
                    # Without extra escaping for these two, the next character
                    # gets eaten
                    if arg.endswith('\\'):
                        arg += '\\'
                    elif arg.endswith('\\"'):
                        arg = arg[:-2] + '\\\\"'
                extra_args.append(arg)
        else:
            # MinGW GCC needs all backslashes in defines to be doubly-escaped
            # FIXME: Not sure about Cygwin or Clang
            for arg in args:
                if arg.startswith('-D') or arg.startswith('/D'):
                    arg = arg.replace('\\', '\\\\')
                extra_args.append(arg)
        return extra_args

    def generate_basic_compiler_args(self, target, compiler):
        commands = []
        commands += self.get_cross_stdlib_args(target, compiler)
        commands += compiler.get_always_args()
        commands += compiler.get_warn_args(self.environment.coredata.get_builtin_option('warning_level'))
        commands += compiler.get_option_compile_args(self.environment.coredata.compiler_options)
        commands += self.build.get_global_args(compiler)
        commands += self.environment.coredata.external_args[compiler.get_language()]
        commands += self.escape_extra_args(compiler, target.get_extra_args(compiler.get_language()))
        commands += compiler.get_buildtype_args(self.environment.coredata.get_builtin_option('buildtype'))
        if self.environment.coredata.get_builtin_option('werror'):
            commands += compiler.get_werror_args()
        if isinstance(target, build.SharedLibrary):
            commands += compiler.get_pic_args()
        for dep in target.get_external_deps():
            # Cflags required by external deps might have UNIX-specific flags,
            # so filter them out if needed
            commands += compiler.unix_compile_flags_to_native(dep.get_compile_args())
            if isinstance(target, build.Executable):
                commands += dep.get_exe_args()

        # Fortran requires extra include directives.
        if compiler.language == 'fortran':
            for lt in target.link_targets:
                priv_dir = os.path.join(self.get_target_dir(lt), lt.get_basename() + lt.type_suffix())
                incflag = compiler.get_include_args(priv_dir, False)
                commands += incflag
        return commands

    def build_target_link_arguments(self, compiler, deps):
        args = []
        for d in deps:
            if not isinstance(d, (build.StaticLibrary, build.SharedLibrary)):
                raise RuntimeError('Tried to link with a non-library target "%s".' % d.get_basename())
            if isinstance(compiler, compilers.LLVMDCompiler):
                args.extend(['-L', self.get_target_filename_for_linking(d)])
            else:
                args.append(self.get_target_filename_for_linking(d))
            # If you have executable e that links to shared lib s1 that links to shared library s2
            # you have to specify s2 as well as s1 when linking e even if e does not directly use
            # s2. Gcc handles this case fine but Clang does not for some reason. Thus we need to
            # explictly specify all libraries every time.
            args += self.build_target_link_arguments(compiler, d.get_dependencies())
        return args

    def determine_windows_extra_paths(self, target):
        '''On Windows there is no such thing as an rpath.
        We must determine all locations of DLLs that this exe
        links to and return them so they can be used in unit
        tests.'''
        if not isinstance(target, build.Executable):
            return []
        prospectives = target.get_transitive_link_deps()
        result = []
        for ld in prospectives:
            if ld == '' or ld == '.':
                continue
            dirseg = os.path.join(self.environment.get_build_dir(), self.get_target_dir(ld))
            if dirseg not in result:
                result.append(dirseg)
        return result

    def write_benchmark_file(self, datafile):
        self.write_test_serialisation(self.build.get_benchmarks(), datafile)

    def write_test_file(self, datafile):
        self.write_test_serialisation(self.build.get_tests(), datafile)

    def write_test_serialisation(self, tests, datafile):
        arr = []
        for t in tests:
            exe = t.get_exe()
            if isinstance(exe, dependencies.ExternalProgram):
                fname = exe.fullpath
            else:
                fname = [os.path.join(self.environment.get_build_dir(), self.get_target_filename(t.get_exe()))]
            is_cross = self.environment.is_cross_build() and \
                self.environment.cross_info.need_cross_compiler() and \
                self.environment.cross_info.need_exe_wrapper()
            if is_cross:
                exe_wrapper = self.environment.cross_info.config['binaries'].get('exe_wrapper', None)
            else:
                exe_wrapper = None
            if mesonlib.is_windows():
                extra_paths = self.determine_windows_extra_paths(exe)
            else:
                extra_paths = []
            cmd_args = []
            for a in t.cmd_args:
                if isinstance(a, mesonlib.File):
                    a = os.path.join(self.environment.get_build_dir(), a.rel_to_builddir(self.build_to_src))
                cmd_args.append(a)
            ts = TestSerialisation(t.get_name(), t.suite, fname, is_cross, exe_wrapper,
                                   t.is_parallel, cmd_args, t.env, t.should_fail, t.valgrind_args,
                                   t.timeout, t.workdir, extra_paths)
            arr.append(ts)
        pickle.dump(arr, datafile)


    def generate_depmf_install(self, d):
        if self.build.dep_manifest_name is None:
            return
        ifilename = os.path.join(self.environment.get_build_dir(), 'depmf.json')
        ofilename = os.path.join(self.environment.get_prefix(), self.build.dep_manifest_name)
        mfobj = {'type': 'dependency manifest',
                 'version': '1.0'}
        mfobj['projects'] = self.build.dep_manifest
        with open(ifilename, 'w') as f:
            f.write(json.dumps(mfobj))
        d.data.append([ifilename, ofilename])

    def get_regen_filelist(self):
        '''List of all files whose alteration means that the build
        definition needs to be regenerated.'''
        deps = [os.path.join(self.build_to_src, df) \
                for df in self.interpreter.get_build_def_files()]
        if self.environment.is_cross_build():
            deps.append(os.path.join(self.build_to_src,
                                     self.environment.coredata.cross_file))
        deps.append('meson-private/coredata.dat')
        if os.path.exists(os.path.join(self.environment.get_source_dir(), 'meson_options.txt')):
            deps.append(os.path.join(self.build_to_src, 'meson_options.txt'))
        for sp in self.build.subprojects.keys():
            fname = os.path.join(self.environment.get_source_dir(), sp, 'meson_options.txt')
            if os.path.isfile(fname):
                deps.append(os.path.join(self.build_to_src, sp, 'meson_options.txt'))
        return deps

    def exe_object_to_cmd_array(self, exe):
        if self.environment.is_cross_build() and \
           self.environment.cross_info.need_exe_wrapper() and \
           isinstance(exe, build.BuildTarget) and exe.is_cross:
            if 'exe_wrapper' not in self.environment.cross_info.config['binaries']:
                s = 'Can not use target %s as a generator because it is cross-built\n'
                s += 'and no exe wrapper is defined. You might want to set it to native instead.'
                s = s % exe.name
                raise MesonException(s)
        if isinstance(exe, build.BuildTarget):
            exe_arr = [os.path.join(self.environment.get_build_dir(), self.get_target_filename(exe))]
        else:
            exe_arr = exe.get_command()
        return exe_arr

    def replace_extra_args(self, args, genlist):
        final_args = []
        for a in args:
            if a == '@EXTRA_ARGS@':
                final_args += genlist.get_extra_args()
            else:
                final_args.append(a)
        return final_args

    def replace_outputs(self, args, private_dir, output_list):
        newargs = []
        regex = re.compile('@OUTPUT(\d+)@')
        for arg in args:
            m = regex.search(arg)
            while m is not None:
                index = int(m.group(1))
                src = '@OUTPUT%d@' % index
                arg = arg.replace(src, os.path.join(private_dir, output_list[index]))
                m = regex.search(arg)
            newargs.append(arg)
        return newargs

    def get_custom_target_provided_libraries(self, target):
        libs = []
        for t in target.get_generated_sources():
            if not isinstance(t, build.CustomTarget):
                continue
            for f in t.output:
                if self.environment.is_library(f):
                    libs.append(os.path.join(self.get_target_dir(t), f))
        return libs

    def eval_custom_target_command(self, target, absolute_paths=False):
        if not absolute_paths:
            ofilenames = [os.path.join(self.get_target_dir(target), i) for i in target.output]
        else:
            ofilenames = [os.path.join(self.environment.get_build_dir(), self.get_target_dir(target), i) \
                          for i in target.output]
        srcs = []
        outdir = self.get_target_dir(target)
        # Many external programs fail on empty arguments.
        if outdir == '':
            outdir = '.'
        if absolute_paths:
            outdir = os.path.join(self.environment.get_build_dir(), outdir)
        for i in target.sources:
            if hasattr(i, 'held_object'):
                i = i.held_object
            if isinstance(i, str):
                fname = [os.path.join(self.build_to_src, target.subdir, i)]
            elif isinstance(i, (build.BuildTarget, build.CustomTarget)):
                fname = [self.get_target_filename(i)]
            elif isinstance(i, build.GeneratedList):
                fname = [os.path.join(self.get_target_private_dir(target), p) for p in i.get_outfilelist()]
            else:
                fname = [i.rel_to_builddir(self.build_to_src)]
            if absolute_paths:
                fname =[os.path.join(self.environment.get_build_dir(), f) for f in fname]
            srcs += fname
        cmd = []
        for i in target.command:
            if isinstance(i, build.Executable):
                cmd += self.exe_object_to_cmd_array(i)
                continue
            elif isinstance(i, build.CustomTarget):
                # GIR scanner will attempt to execute this binary but
                # it assumes that it is in path, so always give it a full path.
                tmp = i.get_filename()[0]
                i = os.path.join(self.get_target_dir(i), tmp)
            elif isinstance(i, mesonlib.File):
                i = i.rel_to_builddir(self.build_to_src)
                if absolute_paths:
                    i = os.path.join(self.environment.get_build_dir(), i)
            # FIXME: str types are blindly added and ignore the 'absolute_paths' argument
            elif not isinstance(i, str):
                err_msg = 'Argument {0} is of unknown type {1}'
                raise RuntimeError(err_msg.format(str(i), str(type(i))))
            for (j, src) in enumerate(srcs):
                i = i.replace('@INPUT%d@' % j, src)
            for (j, res) in enumerate(ofilenames):
                i = i.replace('@OUTPUT%d@' % j, res)
            if i == '@INPUT@':
                cmd += srcs
            elif i == '@OUTPUT@':
                cmd += ofilenames
            else:
                if '@OUTDIR@' in i:
                    i = i.replace('@OUTDIR@', outdir)
                elif '@DEPFILE@' in i:
                    if target.depfile is None:
                        raise MesonException('Custom target %s has @DEPFILE@ but no depfile keyword argument.' % target.name)
                    if absolute_paths:
                        dfilename = os.path.join(self.get_target_private_dir_abs(target), target.depfile)
                    else:
                        dfilename = os.path.join(self.get_target_private_dir(target), target.depfile)
                    i = i.replace('@DEPFILE@', dfilename)
                elif '@PRIVATE_OUTDIR_' in i:
                    match = re.search('@PRIVATE_OUTDIR_(ABS_)?([-a-zA-Z0-9.@:]*)@', i)
                    source = match.group(0)
                    if match.group(1) is None and not absolute_paths:
                        lead_dir = ''
                    else:
                        lead_dir = self.environment.get_build_dir()
                    i = i.replace(source,
                                  os.path.join(lead_dir,
                                               outdir))
                cmd.append(i)
        # This should not be necessary but removing it breaks
        # building GStreamer on Windows. The underlying issue
        # is problems with quoting backslashes on Windows
        # which is the seventh circle of hell. The downside is
        # that this breaks custom targets whose command lines
        # have backslashes. If you try to fix this be sure to
        # check that it does not break GST.
        #
        # The bug causes file paths such as c:\foo to get escaped
        # into c:\\foo.
        #
        # Unfortunately we have not been able to come up with an
        # isolated test case for this so unless you manage to come up
        # with one, the only way is to test the building with Gst's
        # setup. Note this in your MR or ping us and we will get it
        # fixed.
        #
        # https://github.com/mesonbuild/meson/pull/737
        cmd = [i.replace('\\', '/') for i in cmd]
        return (srcs, ofilenames, cmd)

    def run_postconf_scripts(self):
        env = {'MESON_SOURCE_ROOT' : self.environment.get_source_dir(),
               'MESON_BUILD_ROOT' : self.environment.get_build_dir()
              }
        child_env = os.environ.copy()
        child_env.update(env)

        for s in self.build.postconf_scripts:
            cmd = s['exe'].get_command() + s['args']
            subprocess.check_call(cmd, env=child_env)

    # Subprojects of subprojects may cause the same dep args to be used
    # multiple times. Remove duplicates here. Note that we can't dedup
    # libraries based on name alone, because "-lfoo -lbar -lfoo" is 
    # a completely valid (though pathological) sequence and removing the
    # latter may fail. Usually only applies to static libs, though.
    def dedup_arguments(self, commands):
        includes = {}
        final_commands = []
        previous = '-fsuch_arguments=woof'
        for c in commands:
            if c.startswith(('-I', '-L', '/LIBPATH')):
                if c in includes:
                    continue
                includes[c] = True
            if previous == c:
                continue
            previous = c
            final_commands.append(c)
        return final_commands
                                                  
