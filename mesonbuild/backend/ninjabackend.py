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

from . import backends
from .. import environment, mesonlib
from .. import build
from .. import mlog
from .. import dependencies
from .. import compilers
from ..mesonlib import File, MesonException
from .backends import InstallData
from ..build import InvalidArguments
import os, sys, pickle, re
import subprocess, shutil

if mesonlib.is_windows():
    quote_char = '"'
    execute_wrapper = 'cmd /c'
else:
    quote_char = "'"
    execute_wrapper = ''

def ninja_quote(text):
    return text.replace(' ', '$ ').replace(':', '$:')

class RawFilename():
    def __init__(self, fname):
        self.fname = fname

    def split(self, c):
        return self.fname.split(c)

    def startswith(self, s):
        return self.fname.startswith(s)

class NinjaBuildElement():
    def __init__(self, all_outputs, outfilenames, rule, infilenames):
        if isinstance(outfilenames, str):
            self.outfilenames = [outfilenames]
        else:
            self.outfilenames = outfilenames
        assert(isinstance(rule, str))
        self.rule = rule
        if isinstance(infilenames, str):
            self.infilenames = [infilenames]
        else:
            self.infilenames = infilenames
        self.deps = []
        self.orderdeps = []
        self.elems = []
        self.all_outputs = all_outputs

    def add_dep(self, dep):
        if isinstance(dep, list):
            self.deps += dep
        else:
            self.deps.append(dep)

    def add_orderdep(self, dep):
        if isinstance(dep, list):
            self.orderdeps += dep
        else:
            self.orderdeps.append(dep)

    def add_item(self, name, elems):
        if isinstance(elems, str):
            elems = [elems]
        self.elems.append((name, elems))

    def write(self, outfile):
        self.check_outputs()
        line = 'build %s: %s %s' % (' '.join([ninja_quote(i) for i in self.outfilenames]),\
                                    self.rule,
                                    ' '.join([ninja_quote(i) for i in self.infilenames]))
        if len(self.deps) > 0:
            line += ' | ' + ' '.join([ninja_quote(x) for x in self.deps])
        if len(self.orderdeps) > 0:
            line += ' || ' + ' '.join([ninja_quote(x) for x in self.orderdeps])
        line += '\n'
        # This is the only way I could find to make this work on all
        # platforms including Windows command shell. Slash is a dir separator
        # on Windows, too, so all characters are unambiguous and, more importantly,
        # do not require quoting.
        line = line.replace('\\', '/')
        outfile.write(line)

        for e in self.elems:
            (name, elems) = e
            should_quote = True
            if name == 'DEPFILE' or name == 'DESC' or name == 'pool':
                should_quote = False
            line = ' %s = ' % name
            q_templ = quote_char + "%s" + quote_char
            noq_templ = "%s"
            newelems = []
            for i in elems:
                if not should_quote or i == '&&': # Hackety hack hack
                    templ = noq_templ
                else:
                    templ = q_templ
                i = i.replace('\\', '\\\\')
                if quote_char == '"':
                    i = i.replace('"', '\\"')
                newelems.append(templ % ninja_quote(i))
            line += ' '.join(newelems)
            line += '\n'
            outfile.write(line)
        outfile.write('\n')

    def check_outputs(self):
        for n in self.outfilenames:
            if n in self.all_outputs:
                raise MesonException('Multiple producers for Ninja target "%s". Please rename your targets.' % n)
            self.all_outputs[n] = True

class NinjaBackend(backends.Backend):

    def __init__(self, build):
        super().__init__(build)
        self.ninja_filename = 'build.ninja'
        self.fortran_deps = {}
        self.all_outputs = {}

    def detect_vs_dep_prefix(self, outfile, tempfilename):
        '''VS writes its dependency in a locale dependent format.
        Detect the search prefix to use.'''
        # Of course there is another program called 'cl' on
        # some platforms. Let's just require that on Windows
        # cl points to msvc.
        if not mesonlib.is_windows() or shutil.which('cl') is None:
            return outfile
        outfile.close()
        open(os.path.join(self.environment.get_scratch_dir(), 'incdetect.c'),
              'w').write('''#include<stdio.h>
int dummy;
''')

        pc = subprocess.Popen(['cl', '/showIncludes', '/c', 'incdetect.c'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              cwd=self.environment.get_scratch_dir())

        (stdo, _) = pc.communicate()

        for line in stdo.split(b'\r\n'):
            if line.endswith(b'stdio.h'):
                matchstr = b':'.join(line.split(b':')[0:2]) + b':'
                binfile = open(tempfilename, 'ab')
                binfile.write(b'msvc_deps_prefix = ' + matchstr + b'\r\n')
                binfile.close()
                return open(tempfilename, 'a')
        raise MesonException('Could not determine vs dep dependency prefix string.')

    def generate(self, interp):
        self.interpreter = interp
        outfilename = os.path.join(self.environment.get_build_dir(), self.ninja_filename)
        tempfilename = outfilename + '~'
        outfile = open(tempfilename, 'w')
        outfile.write('# This is the build file for project "%s"\n' % self.build.get_project())
        outfile.write('# It is autogenerated by the Meson build system.\n')
        outfile.write('# Do not edit by hand.\n\n')
        outfile.write('ninja_required_version = 1.5.1\n\n')
        outfile = self.detect_vs_dep_prefix(outfile, tempfilename)
        self.generate_rules(outfile)
        self.generate_phony(outfile)
        outfile.write('# Build rules for targets\n\n')
        [self.generate_target(t, outfile) for t in self.build.get_targets().values()]
        if len(self.build.pot) > 0:
            outfile.write('# Build rules for localisation.\n\n')
            self.generate_po(outfile)
        outfile.write('# Test rules\n\n')
        self.generate_tests(outfile)
        outfile.write('# Install rules\n\n')
        self.generate_install(outfile)
        if 'b_coverage' in self.environment.coredata.base_options and \
            self.environment.coredata.base_options['b_coverage'].value:
            outfile.write('# Coverage rules\n\n')
            self.generate_coverage_rules(outfile)
        outfile.write('# Suffix\n\n')
        self.generate_ending(outfile)
        # Only ovewrite the old build file after the new one has been
        # fully created.
        outfile.close()
        os.replace(tempfilename, outfilename)
        self.generate_compdb()

    # http://clang.llvm.org/docs/JSONCompilationDatabase.html
    def generate_compdb(self):
        ninja_exe = environment.detect_ninja()
        builddir = self.environment.get_build_dir()
        jsondb = subprocess.check_output([ninja_exe, '-t', 'compdb', 'c_COMPILER', 'cpp_COMPILER'], cwd=builddir)
        open(os.path.join(builddir, 'compile_commands.json'), 'wb').write(jsondb)

    # Get all generated headers. Any source file might need them so
    # we need to add an order dependency to them.
    def get_generated_headers(self, target):
        header_deps = []
        for gensource in target.get_generated_sources():
            if isinstance(gensource, build.CustomTarget):
                continue
            for src in gensource.get_outfilelist():
                if self.environment.is_header(src):
                    header_deps.append(os.path.join(self.get_target_private_dir(target), src))
        for dep in target.link_targets:
            if isinstance(dep, (build.StaticLibrary, build.SharedLibrary)):
                header_deps += self.get_generated_headers(dep)
        return header_deps

    def generate_target(self, target, outfile):
        if isinstance(target, build.CustomTarget):
            self.generate_custom_target(target, outfile)
        if isinstance(target, build.RunTarget):
            self.generate_run_target(target, outfile)
        name = target.get_id()
        gen_src_deps = []
        if name in self.processed_targets:
            return
        if isinstance(target, build.Jar):
            self.generate_jar_target(target, outfile)
            return
        if 'rust' in self.environment.coredata.compilers.keys() and self.has_rust(target):
            self.generate_rust_target(target, outfile)
            return
        if 'cs' in self.environment.coredata.compilers.keys() and self.has_cs(target):
            self.generate_cs_target(target, outfile)
            return
        if 'vala' in self.environment.coredata.compilers.keys() and self.has_vala(target):
            vc = self.environment.coredata.compilers['vala']
            vala_output_files = self.generate_vala_compile(vc, target, outfile)
            gen_src_deps += vala_output_files
        if 'swift' in self.environment.coredata.compilers.keys() and self.has_swift(target):
            self.generate_swift_target(target, outfile)
            return
        self.scan_fortran_module_outputs(target)
        # The following deals with C/C++ compilation.
        (gen_src, gen_other_deps) = self.process_dep_gens(outfile, target)
        gen_src_deps += gen_src
        self.process_target_dependencies(target, outfile)
        self.generate_custom_generator_rules(target, outfile)
        outname = self.get_target_filename(target)
        obj_list = []
        use_pch = self.environment.coredata.base_options.get('b_pch', False)
        is_unity = self.environment.coredata.get_builtin_option('unity')
        if use_pch and target.has_pch():
            pch_objects = self.generate_pch(target, outfile)
        else:
            pch_objects = []
        header_deps = gen_other_deps
        unity_src = []
        unity_deps = [] # Generated sources that must be built before compiling a Unity target.
        header_deps += self.get_generated_headers(target)
        for gensource in target.get_generated_sources():
            if isinstance(gensource, build.CustomTarget):
                for src in gensource.output:
                    src = os.path.join(self.get_target_dir(gensource), src)
                    if self.environment.is_source(src) and not self.environment.is_header(src):
                        if is_unity:
                            unity_deps.append(os.path.join(self.environment.get_build_dir(), RawFilename(src)))
                        else:
                            obj_list.append(self.generate_single_compile(target, outfile, RawFilename(src), True,
                                                                         header_deps))
                    elif self.environment.is_object(src):
                        obj_list.append(src)
                    elif self.environment.is_library(src):
                        pass
                    else:
                        # Assume anything not specifically a source file is a header. This is because
                        # people generate files with weird suffixes (.inc, .fh) that they then include
                        # in their source files.
                        header_deps.append(RawFilename(src))
            else:
                for src in gensource.get_outfilelist():
                    if self.environment.is_object(src):
                        obj_list.append(os.path.join(self.get_target_private_dir(target), src))
                    elif not self.environment.is_header(src):
                        if is_unity:
                            if self.has_dir_part(src):
                                rel_src = src
                            else:
                                rel_src = os.path.join(self.get_target_private_dir(target), src)
                            unity_deps.append(rel_src)
                            abs_src = os.path.join(self.environment.get_build_dir(), rel_src)
                            unity_src.append(abs_src)
                        else:
                            obj_list.append(self.generate_single_compile(target, outfile, src, True,
                                                                         header_deps=header_deps))
        src_list = []
        for src in gen_src_deps:
            src_list.append(src)
            if is_unity:
                unity_src.append(os.path.join(self.environment.get_build_dir(), src))
                header_deps.append(src)
            else:
                # Generated targets are ordered deps because the must exist
                # before the sources compiling them are used. After the first
                # compile we get precise dependency info from dep files.
                # This should work in all cases. If it does not, then just
                # move them from orderdeps to proper deps.
                if self.environment.is_header(src):
                    header_deps.append(src)
                else:
                    obj_list.append(self.generate_single_compile(target, outfile, src, True, [], header_deps))
        for src in target.get_sources():
            if src.endswith('.vala'):
                continue
            if not self.environment.is_header(src):
                src_list.append(src)
                if is_unity:
                    abs_src = os.path.join(self.environment.get_build_dir(),
                                           src.rel_to_builddir(self.build_to_src))
                    unity_src.append(abs_src)
                else:
                    obj_list.append(self.generate_single_compile(target, outfile, src, False, [], header_deps))
        obj_list += self.flatten_object_list(target)
        if is_unity:
            for src in self.generate_unity_files(target, unity_src):
                obj_list.append(self.generate_single_compile(target, outfile, src, True, unity_deps + header_deps))
        linker = self.determine_linker(target, src_list)
        elem = self.generate_link(target, outfile, outname, obj_list, linker, pch_objects)
        self.generate_shlib_aliases(target, self.get_target_dir(target))
        elem.write(outfile)
        self.processed_targets[name] = True

    def process_target_dependencies(self, target, outfile):
        for t in target.get_dependencies():
            tname = t.get_basename() + t.type_suffix()
            if not tname in self.processed_targets:
                self.generate_target(t, outfile)

    def generate_custom_target(self, target, outfile):
        (srcs, ofilenames, cmd) = self.eval_custom_target_command(target)
        deps = []
        for i in target.get_dependencies():
            # FIXME, should not grab element at zero but rather expand all.
            if isinstance(i, list):
                i = i[0]
            fname = i.get_filename()
            if isinstance(fname, list):
                fname = fname[0]
            deps.append(os.path.join(self.get_target_dir(i), fname))
        if target.build_always:
            deps.append('PHONY')
        elem = NinjaBuildElement(self.all_outputs, ofilenames, 'CUSTOM_COMMAND', srcs)
        for i in target.depend_files:
            if isinstance(i, mesonlib.File):
                deps.append(i.rel_to_builddir(self.build_to_src))
            else:
                deps.append(os.path.join(self.build_to_src, i))
        elem.add_dep(deps)
        for d in target.extra_depends:
            tmp = d.get_filename()
            if not isinstance(tmp, list):
                tmp = [tmp]
            for fname in tmp:
                elem.add_dep(os.path.join(self.get_target_dir(d), fname))

        elem.add_item('COMMAND', cmd)
        elem.add_item('description', 'Generating %s with a custom command.' % target.name)
        elem.write(outfile)
        self.processed_targets[target.name + target.type_suffix()] = True

    def generate_run_target(self, target, outfile):
        runnerscript = [sys.executable, self.environment.get_build_command(), '--internal', 'commandrunner']
        deps = []
        arg_strings = []
        for i in target.args:
            if isinstance(i, str):
                arg_strings.append(i)
            elif isinstance(i, (build.BuildTarget, build.CustomTarget)):
                relfname = self.get_target_filename(i)
                deps.append(relfname)
                arg_strings.append(os.path.join(self.environment.get_build_dir(), relfname))
            else:
                mlog.debug(str(i))
                raise MesonException('Unreachable code in generate_run_target.')
        elem = NinjaBuildElement(self.all_outputs, target.name, 'CUSTOM_COMMAND', deps)
        cmd = runnerscript + [self.environment.get_source_dir(), self.environment.get_build_dir(), target.subdir]
        texe = target.command
        try:
            texe = texe.held_object
        except AttributeError:
            pass
        if isinstance(texe, build.Executable):
            abs_exe = os.path.join(self.environment.get_build_dir(), self.get_target_filename(texe))
            deps.append(self.get_target_filename(texe))
            if self.environment.is_cross_build() \
                and self.environment.cross_info.config['binaries'].get('exe_wrapper', None) is not None:
                cmd += [self.environment.cross_info.config['binaries']['exe_wrapper']]
            cmd.append(abs_exe)
        else:
            cmd.append(target.command)
        cmd += arg_strings
        elem.add_item('COMMAND', cmd)
        elem.add_item('description', 'Running external command %s.' % target.name)
        elem.add_item('pool', 'console')
        elem.write(outfile)
        self.processed_targets[target.name + target.type_suffix()] = True

    def generate_po(self, outfile):
        for p in self.build.pot:
            (packagename, languages, subdir) = p
            input_file = os.path.join(subdir, 'POTFILES')
            elem = NinjaBuildElement(self.all_outputs, 'pot', 'GEN_POT', [])
            elem.add_item('PACKAGENAME', packagename)
            elem.add_item('OUTFILE', packagename + '.pot')
            elem.add_item('FILELIST', os.path.join(self.environment.get_source_dir(), input_file))
            elem.add_item('OUTDIR', os.path.join(self.environment.get_source_dir(), subdir))
            elem.write(outfile)
            for l in languages:
                infile = os.path.join(self.environment.get_source_dir(), subdir, l + '.po')
                outfilename = os.path.join(subdir, l + '.gmo')
                lelem = NinjaBuildElement(self.all_outputs, outfilename, 'GEN_GMO', infile)
                lelem.add_item('INFILE', infile)
                lelem.add_item('OUTFILE', outfilename)
                lelem.write(outfile)

    def generate_coverage_rules(self, outfile):
        (gcovr_exe, lcov_exe, genhtml_exe) = environment.find_coverage_tools()
        added_rule = False
        if gcovr_exe:
            added_rule = True
            elem = NinjaBuildElement(self.all_outputs, 'coverage-xml', 'CUSTOM_COMMAND', '')
            elem.add_item('COMMAND', [gcovr_exe, '-x', '-r', self.environment.get_source_dir(),\
                                      '-o', os.path.join(self.environment.get_log_dir(), 'coverage.xml')])
            elem.add_item('DESC', 'Generating XML coverage report.')
            elem.write(outfile)
            elem = NinjaBuildElement(self.all_outputs, 'coverage-text', 'CUSTOM_COMMAND', '')
            elem.add_item('COMMAND', [gcovr_exe, '-r', self.environment.get_source_dir(),\
                                      '-o', os.path.join(self.environment.get_log_dir(), 'coverage.txt')])
            elem.add_item('DESC', 'Generating text coverage report.')
            elem.write(outfile)
        if lcov_exe and genhtml_exe:
            added_rule = True
            phony_elem = NinjaBuildElement(self.all_outputs, 'coverage-html', 'phony', 'coveragereport/index.html')
            phony_elem.write(outfile)

            elem = NinjaBuildElement(self.all_outputs, 'coveragereport/index.html', 'CUSTOM_COMMAND', '')
            htmloutdir = os.path.join(self.environment.get_log_dir(), 'coveragereport')
            command = [lcov_exe, '--directory', self.environment.get_build_dir(),\
                       '--capture', '--output-file', 'coverage.info', '--no-checksum',\
                       '&&', genhtml_exe, '--prefix', self.environment.get_build_dir(),\
                       '--output-directory', htmloutdir, '--title', 'Code coverage',\
                       '--legend', '--show-details', 'coverage.info']
            elem.add_item('COMMAND', command)
            elem.add_item('DESC', 'Generating HTML coverage report.')
            elem.write(outfile)
        if not added_rule:
            mlog.log(mlog.red('Warning:'), 'coverage requested but neither gcovr nor lcov/genhtml found.')

    def generate_install(self, outfile):
        script_root = self.environment.get_script_dir()
        install_script = os.path.join(script_root, 'meson_install.py')
        install_data_file = os.path.join(self.environment.get_scratch_dir(), 'install.dat')
        d = InstallData(self.environment.get_source_dir(),
                        self.environment.get_build_dir(),
                        self.environment.get_prefix())
        elem = NinjaBuildElement(self.all_outputs, 'install', 'CUSTOM_COMMAND', 'PHONY')
        elem.add_dep('all')
        elem.add_item('DESC', 'Installing files.')
        elem.add_item('COMMAND', [sys.executable, self.environment.get_build_command(), '--internal', 'install', install_data_file])
        elem.add_item('pool', 'console')
        self.generate_depmf_install(d)
        self.generate_target_install(d)
        self.generate_header_install(d)
        self.generate_man_install(d)
        self.generate_data_install(d)
        self.generate_po_install(d, elem)
        self.generate_custom_install_script(d)
        self.generate_subdir_install(d)
        elem.write(outfile)

        ofile = open(install_data_file, 'wb')
        pickle.dump(d, ofile)

    def generate_po_install(self, d, elem):
        for p in self.build.pot:
            (package_name, languages, subdir) = p
            # FIXME: assumes only one po package per source
            d.po_package_name = package_name
            for lang in languages:
                rel_src =  os.path.join(subdir, lang + '.gmo')
                src_file = os.path.join(self.environment.get_build_dir(), rel_src)
                d.po.append((src_file, self.environment.coredata.get_builtin_option('localedir'), lang))
                elem.add_dep(rel_src)

    def generate_target_install(self, d):
        libdir = self.environment.get_libdir()
        bindir = self.environment.get_bindir()

        should_strip = self.environment.coredata.get_builtin_option('strip')
        for t in self.build.get_targets().values():
            if t.should_install():
                outdir = t.get_custom_install_dir()
                if outdir is None:
                    if isinstance(t, build.Executable):
                        outdir = bindir
                    else:
                        outdir = libdir
                i = [self.get_target_filename(t), outdir, t.get_aliaslist(),\
                    should_strip, t.install_rpath]
                d.targets.append(i)

    def generate_custom_install_script(self, d):
        d.install_scripts = self.build.install_scripts

    def generate_header_install(self, d):
        incroot = self.environment.get_includedir()
        headers = self.build.get_headers()

        for h in headers:
            outdir = h.get_custom_install_dir()
            if outdir is None:
                outdir = os.path.join(incroot, h.get_install_subdir())
            for f in h.get_sources():
                abspath = os.path.join(self.environment.get_source_dir(), h.get_source_subdir(), f)
                i = [abspath, outdir]
                d.headers.append(i)

    def generate_man_install(self, d):
        manroot = self.environment.get_mandir()
        man = self.build.get_man()
        for m in man:
            for f in m.get_sources():
                num = f.split('.')[-1]
                subdir = m.get_custom_install_dir()
                if subdir is None:
                    subdir = os.path.join(manroot, 'man' + num)
                srcabs = os.path.join(self.environment.get_source_dir(), m.get_source_subdir(), f)
                dstabs = os.path.join(subdir, f + '.gz')
                i = [srcabs, dstabs]
                d.man.append(i)

    def generate_data_install(self, d):
        data = self.build.get_data()
        for de in data:
            assert(isinstance(de, build.Data))
            subdir = de.install_dir
            for f in de.sources:
                plain_f = os.path.split(f)[1]
                if de.in_sourcetree:
                    srcprefix = self.environment.get_source_dir()
                else:
                    srcprefix = self.environment.get_build_dir()
                srcabs = os.path.join(srcprefix, de.source_subdir, f)
                dstabs = os.path.join(subdir, plain_f)
                i = [srcabs, dstabs]
                d.data.append(i)

    def generate_subdir_install(self, d):
        for sd in self.build.get_install_subdirs():
            src_dir = os.path.join(self.environment.get_source_dir(), sd.source_subdir, sd.installable_subdir)
            dst_dir = os.path.join(self.environment.get_prefix(), sd.install_dir)
            d.install_subdirs.append([src_dir, dst_dir])

    def write_test_suite_targets(self, cmd, outfile):
        suites = {}
        for t in self.build.get_tests():
            for s in t.suite:
                suites[s] = True
        suites = list(suites.keys())
        suites.sort()
        for s in suites:
            if s == '':
                visible_name = 'for top level tests'
            else:
                visible_name = s
            elem = NinjaBuildElement(self.all_outputs, 'test-' + s, 'CUSTOM_COMMAND', ['all', 'PHONY'])
            elem.add_item('COMMAND', cmd + ['--suite=' + s])
            elem.add_item('DESC', 'Running test suite %s.' % visible_name)
            elem.add_item('pool', 'console')
            elem.write(outfile)

    def generate_tests(self, outfile):
        self.serialise_tests()
        valgrind = environment.find_valgrind()
        script_root = self.environment.get_script_dir()
        test_data = os.path.join(self.environment.get_scratch_dir(), 'meson_test_setup.dat')
        cmd = [ sys.executable, self.environment.get_build_command(), '--internal', 'test' ]
        if not self.environment.coredata.get_builtin_option('stdsplit'):
            cmd += ['--no-stdsplit']
        if self.environment.coredata.get_builtin_option('errorlogs'):
            cmd += ['--print-errorlogs']
        cmd += [ test_data ]
        elem = NinjaBuildElement(self.all_outputs, 'test', 'CUSTOM_COMMAND', ['all', 'PHONY'])
        elem.add_item('COMMAND', cmd)
        elem.add_item('DESC', 'Running all tests.')
        elem.add_item('pool', 'console')
        elem.write(outfile)
        self.write_test_suite_targets(cmd, outfile)

        if valgrind:
            velem = NinjaBuildElement(self.all_outputs, 'test-valgrind', 'CUSTOM_COMMAND', ['all', 'PHONY'])
            velem.add_item('COMMAND', cmd + ['--wrapper=' + valgrind])
            velem.add_item('DESC', 'Running test suite under Valgrind.')
            velem.add_item('pool', 'console')
            velem.write(outfile)

        # And then benchmarks.
        benchmark_script = os.path.join(script_root, 'meson_benchmark.py')
        benchmark_data = os.path.join(self.environment.get_scratch_dir(), 'meson_benchmark_setup.dat')
        cmd = [sys.executable, self.environment.get_build_command(), '--internal', 'benchmark', benchmark_data]
        elem = NinjaBuildElement(self.all_outputs, 'benchmark', 'CUSTOM_COMMAND', ['all', 'PHONY'])
        elem.add_item('COMMAND', cmd)
        elem.add_item('DESC', 'Running benchmark suite.')
        elem.add_item('pool', 'console')
        elem.write(outfile)

    def generate_rules(self, outfile):
        outfile.write('# Rules for compiling.\n\n')
        self.generate_compile_rules(outfile)
        outfile.write('# Rules for linking.\n\n')
        if self.environment.is_cross_build():
            self.generate_static_link_rules(True, outfile)
        self.generate_static_link_rules(False, outfile)
        self.generate_dynamic_link_rules(outfile)
        outfile.write('# Other rules\n\n')
        outfile.write('rule CUSTOM_COMMAND\n')
        outfile.write(' command = $COMMAND\n')
        outfile.write(' description = $DESC\n')
        outfile.write(' restat = 1\n\n')
        outfile.write('rule REGENERATE_BUILD\n')
        c = (quote_char + ninja_quote(sys.executable) + quote_char,
             quote_char + ninja_quote(self.environment.get_build_command())  + quote_char,
             '--internal',
             'regenerate',
             quote_char + ninja_quote(self.environment.get_source_dir())  + quote_char,
             quote_char + ninja_quote(self.environment.get_build_dir())  + quote_char)
        outfile.write(" command = %s %s %s %s %s %s --backend ninja\n" % c)
        outfile.write(' description = Regenerating build files\n')
        outfile.write(' generator = 1\n\n')
        if len(self.build.pot) > 0:
            self.generate_gettext_rules(outfile)
        outfile.write('\n')

    def generate_gettext_rules(self, outfile):
        rule = 'rule GEN_POT\n'
        command = " command = xgettext --package-name=$PACKAGENAME -p $OUTDIR -f $FILELIST -D '%s' -k_ -o $OUTFILE\n" % \
        self.environment.get_source_dir()
        desc = " description = Creating pot file for package $PACKAGENAME.\n"
        outfile.write(rule)
        outfile.write(command)
        outfile.write(desc)
        outfile.write('\n')
        rule = 'rule GEN_GMO\n'
        command = ' command = msgfmt $INFILE -o $OUTFILE\n'
        desc = ' description = Generating gmo file $OUTFILE\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(desc)
        outfile.write('\n')

    def generate_phony(self, outfile):
        outfile.write('# Phony build target, always out of date\n')
        outfile.write('build PHONY: phony\n')
        outfile.write('\n')

    def generate_jar_target(self, target, outfile):
        fname = target.get_filename()
        subdir = target.get_subdir()
        outname_rel = os.path.join(self.get_target_dir(target), fname)
        src_list = target.get_sources()
        class_list = []
        compiler = self.get_compiler_for_source(src_list[0])
        assert(compiler.get_language() == 'java')
        c = 'c'
        m = ''
        e = ''
        f = 'f'
        main_class = target.get_main_class()
        if main_class != '':
            e = 'e'
        for src in src_list:
            plain_class_path = self.generate_single_java_compile(src, target, compiler, outfile)
            class_list.append(plain_class_path)
        class_dep_list = [os.path.join(self.get_target_private_dir(target), i) for i in class_list]
        jar_rule = 'java_LINKER'
        commands = [c+m+e+f]
        if e != '':
            commands.append(main_class)
        commands.append(self.get_target_filename(target))
        for cls in class_list:
            commands += ['-C', self.get_target_private_dir(target), cls]
        elem = NinjaBuildElement(self.all_outputs, outname_rel, jar_rule, [])
        elem.add_dep(class_dep_list)
        elem.add_item('ARGS', commands)
        elem.write(outfile)

    def generate_cs_resource_tasks(self, target, outfile):
        args = []
        deps = []
        for r in target.resources:
            rel_sourcefile = os.path.join(self.build_to_src, target.subdir, r)
            if r.endswith('.resources'):
                a = '-resource:' + rel_sourcefile
            elif r.endswith('.txt') or r.endswith('.resx'):
                ofilebase = os.path.splitext(os.path.basename(r))[0] + '.resources'
                ofilename = os.path.join(self.get_target_private_dir(target), ofilebase)
                elem = NinjaBuildElement(self.all_outputs, ofilename, "CUSTOM_COMMAND", rel_sourcefile)
                elem.add_item('COMMAND', ['resgen', rel_sourcefile, ofilename])
                elem.add_item('DESC', 'Compiling resource %s.' % rel_sourcefile)
                elem.write(outfile)
                deps.append(ofilename)
                a = '-resource:' + ofilename
            else:
                raise InvalidArguments('Unknown resource file %s.' % r)
            args.append(a)
        return (args, deps)

    def generate_cs_target(self, target, outfile):
        buildtype = self.environment.coredata.get_builtin_option('buildtype')
        fname = target.get_filename()
        outname_rel = os.path.join(self.get_target_dir(target), fname)
        src_list = target.get_sources()
        compiler = self.get_compiler_for_source(src_list[0])
        assert(compiler.get_language() == 'cs')
        rel_srcs = [s.rel_to_builddir(self.build_to_src) for s in src_list]
        deps = []
        commands = target.extra_args.get('cs', [])
        commands += compiler.get_buildtype_args(buildtype)
        if isinstance(target, build.Executable):
            commands.append('-target:exe')
        elif isinstance(target, build.SharedLibrary):
            commands.append('-target:library')
        else:
            raise MesonException('Unknown C# target type.')
        (resource_args, resource_deps) = self.generate_cs_resource_tasks(target, outfile)
        commands += resource_args
        deps += resource_deps
        commands += compiler.get_output_args(outname_rel)
        for l in target.link_targets:
            lname = os.path.join(self.get_target_dir(l), l.get_filename())
            commands += compiler.get_link_args(lname)
            deps.append(lname)
        if '-g' in commands:
            outputs = [outname_rel, outname_rel + '.mdb']
        else:
            outputs = [outname_rel]
        elem = NinjaBuildElement(self.all_outputs, outputs, 'cs_COMPILER', rel_srcs)
        elem.add_dep(deps)
        elem.add_item('ARGS', commands)
        elem.write(outfile)

    def generate_single_java_compile(self, src, target, compiler, outfile):
        args = []
        args += compiler.get_buildtype_args(self.environment.coredata.get_builtin_option('buildtype'))
        args += compiler.get_output_args(self.get_target_private_dir(target))
        for i in target.include_dirs:
            for idir in i.get_incdirs():
                args += ['-sourcepath', os.path.join(self.build_to_src, i.curdir, idir)]
        rel_src = src.rel_to_builddir(self.build_to_src)
        plain_class_path = src.fname[:-4] + 'class'
        rel_obj = os.path.join(self.get_target_private_dir(target), plain_class_path)
        element = NinjaBuildElement(self.all_outputs, rel_obj, compiler.get_language() + '_COMPILER', rel_src)
        element.add_item('ARGS', args)
        element.write(outfile)
        return plain_class_path

    def generate_java_link(self, outfile):
        rule = 'rule java_LINKER\n'
        command = ' command = jar $ARGS\n'
        description = ' description = Creating jar $out.\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)
        outfile.write('\n')

    def split_vala_sources(self, sources):
        src = []
        vapi_src = []
        for s in sources:
            if s.endswith('.vapi'):
                vapi_src.append(s)
            else:
                src.append(s)
        return (src, vapi_src)

    def determine_dep_vapis(self, target):
        result = []
        for dep in target.link_targets:
            for i in dep.sources:
                if hasattr(i, 'fname'):
                    i = i.fname
                if i.endswith('vala'):
                    vapiname = os.path.splitext(os.path.split(i)[1])[0] + '.vapi'
                    fullname = os.path.join(self.get_target_dir(dep), vapiname)
                    result.append(fullname)
                    break
        return result

    def generate_vala_compile(self, compiler, target, outfile):
        """Vala is compiled into C. Set up all necessary build steps here."""
        valac = self.environment.coredata.compilers['vala']
        (src, vapi_src) = self.split_vala_sources(target.get_sources())
        vapi_src = [x.rel_to_builddir(self.build_to_src) for x in vapi_src]
        extra_dep_files = []
        vala_input_files = []
        for s in src:
            if s.endswith('.vala'):
                vala_input_files.append(s.rel_to_builddir(self.build_to_src))
        if len(src) == 0:
            raise InvalidArguments('Vala library has no Vala source files.')
        namebase = os.path.splitext(os.path.split(src[0].fname)[1])[0]
        base_h = namebase + '.h'
        base_vapi = namebase + '.vapi'
        hname = os.path.normpath(os.path.join(self.get_target_dir(target), base_h))
        vapiname = os.path.normpath(os.path.join(self.get_target_dir(target), base_vapi))

        generated_c_files = []
        outputs = [vapiname]
        args = []
        args += self.build.get_global_args(compiler)
        args += compiler.get_buildtype_args(self.environment.coredata.get_builtin_option('buildtype'))
        args += ['-d', self.get_target_private_dir(target)]
        args += ['-C']#, '-o', cname]
        if not isinstance(target, build.Executable):
            outputs.append(hname)
            args += ['-H', hname]
            args += ['--library=' + target.name]
        args += ['--vapi=' + os.path.join('..', base_vapi)]
        for src in vala_input_files:
            namebase = os.path.splitext(os.path.split(src)[1])[0] + '.c'
            full_c = os.path.join(self.get_target_private_dir(target), namebase)
            generated_c_files.append(full_c)
            outputs.append(full_c)
        if self.environment.coredata.get_builtin_option('werror'):
            args += valac.get_werror_args()
        for d in target.external_deps:
            if isinstance(d, dependencies.PkgConfigDependency):
                if d.name == 'glib-2.0' and d.version_requirement is not None \
                and d.version_requirement.startswith(('>=', '==')):
                    args += ['--target-glib', d.version_requirement[2:]]
                args += ['--pkg', d.name]
        extra_args = []

        for a in target.extra_args.get('vala', []):
            if isinstance(a, File):
                relname = a.rel_to_builddir(self.build_to_src)
                extra_dep_files.append(relname)
                extra_args.append(relname)
            else:
                extra_args.append(a)
        dependency_vapis = self.determine_dep_vapis(target)
        extra_dep_files += dependency_vapis
        args += extra_args
        args += dependency_vapis
        element = NinjaBuildElement(self.all_outputs, outputs,
                                    valac.get_language() + '_COMPILER',
                                    vala_input_files + vapi_src)
        element.add_item('ARGS', args)
        element.add_dep(extra_dep_files)
        element.write(outfile)
        return generated_c_files

    def generate_rust_target(self, target, outfile):
        rustc = self.environment.coredata.compilers['rust']
        relsrc = []
        for i in target.get_sources():
            if not rustc.can_compile(i):
                raise InvalidArguments('Rust target %s contains a non-rust source file.' % target.get_basename())
            relsrc.append(i.rel_to_builddir(self.build_to_src))
        target_name = os.path.join(target.subdir, target.get_filename())
        args = ['--crate-type']
        if isinstance(target, build.Executable):
            cratetype = 'bin'
        elif isinstance(target, build.SharedLibrary):
            cratetype = 'rlib'
        elif isinstance(target, build.StaticLibrary):
            cratetype = 'rlib'
        else:
            raise InvalidArguments('Unknown target type for rustc.')
        args.append(cratetype)
        args += rustc.get_buildtype_args(self.environment.coredata.get_builtin_option('buildtype'))
        depfile = target.name + '.d'
        args += ['--out-dir', target.subdir]
        args += ['--emit', 'dep-info', '--emit', 'link']
        orderdeps = [os.path.join(t.subdir, t.get_filename()) for t in target.link_targets]
        linkdirs = {}
        for d in target.link_targets:
            linkdirs[d.subdir] = True
        for d in linkdirs.keys():
            if d == '':
                d = '.'
            args += ['-L', d]
        element = NinjaBuildElement(self.all_outputs, target_name, 'rust_COMPILER', relsrc)
        if len(orderdeps) > 0:
            element.add_orderdep(orderdeps)
        element.add_item('ARGS', args)
        element.add_item('targetdep', depfile)
        element.add_item('cratetype', cratetype)
        element.write(outfile)

    def swift_module_file_name(self, target):
        return os.path.join(self.get_target_private_dir(target),
                            self.target_swift_modulename(target) + '.swiftmodule')

    def target_swift_modulename(self, target):
        return target.name

    def is_swift_target(self, target):
        for s in target.sources:
            if s.endswith('swift'):
                return True
        return False

    def determine_swift_dep_modules(self, target):
        result = []
        for l in target.link_targets:
            if self.is_swift_target(l):
                result.append(self.swift_module_file_name(l))
        return result

    def determine_swift_dep_dirs(self, target):
        result = []
        for l in target.link_targets:
            result.append(self.get_target_private_dir_abs(l))
        return result

    def get_swift_link_deps(self, target):
        result = []
        for l in target.link_targets:
            result.append(self.get_target_filename(l))
        return result

    def split_swift_generated_sources(self, target):
        all_srcs = []
        for genlist in target.get_generated_sources():
            if isinstance(genlist, build.CustomTarget):
                for ifile in genlist.get_filename():
                    rel = os.path.join(self.get_target_dir(genlist), ifile)
                    all_srcs.append(rel)
            else:
                for ifile in genlist.get_outfilelist():
                    rel = os.path.join(self.get_target_private_dir(target), ifile)
                    all_srcs.append(rel)
        srcs = []
        others = []
        for i in all_srcs:
            if i.endswith('.swift'):
                srcs.append(i)
            else:
                others.append(i)
        return (srcs, others)

    def generate_swift_target(self, target, outfile):
        module_name = self.target_swift_modulename(target)
        swiftc = self.environment.coredata.compilers['swift']
        abssrc = []
        abs_headers = []
        header_imports = []
        for i in target.get_sources():
            if swiftc.can_compile(i):
                relsrc = i.rel_to_builddir(self.build_to_src)
                abss = os.path.normpath(os.path.join(self.environment.get_build_dir(), relsrc))
                abssrc.append(abss)
            elif self.environment.is_header(i):
                relh = i.rel_to_builddir(self.build_to_src)
                absh = os.path.normpath(os.path.join(self.environment.get_build_dir(), relh))
                abs_headers.append(absh)
                header_imports += swiftc.get_header_import_args(absh)
            else:
                raise InvalidArguments('Swift target %s contains a non-swift source file.' % target.get_basename())
        os.makedirs(self.get_target_private_dir_abs(target), exist_ok=True)
        compile_args = swiftc.get_compile_only_args()
        compile_args += swiftc.get_module_args(module_name)
        link_args = swiftc.get_output_args(os.path.join(self.environment.get_build_dir(), self.get_target_filename(target)))
        rundir = self.get_target_private_dir(target)
        out_module_name = self.swift_module_file_name(target)
        in_module_files = self.determine_swift_dep_modules(target)
        abs_module_dirs = self.determine_swift_dep_dirs(target)
        module_includes = []
        for x in abs_module_dirs:
            module_includes += swiftc.get_include_args(x)
        link_deps = self.get_swift_link_deps(target)
        abs_link_deps = [os.path.join(self.environment.get_build_dir(), x) for x in link_deps]
        (rel_generated, _) = self.split_swift_generated_sources(target)
        abs_generated = [os.path.join(self.environment.get_build_dir(), x) for x in rel_generated]
        # We need absolute paths because swiftc needs to be invoked in a subdir
        # and this is the easiest way about it.
        objects = [] # Relative to swift invocation dir
        rel_objects = [] # Relative to build.ninja
        for i in abssrc + abs_generated:
            base = os.path.split(i)[1]
            oname = os.path.splitext(base)[0] + '.o'
            objects.append(oname)
            rel_objects.append(os.path.join(self.get_target_private_dir(target), oname))

        # Swiftc does not seem to be able to emit objects and module files in one go.
        elem = NinjaBuildElement(self.all_outputs, rel_objects,
                                 'swift_COMPILER',
                                 abssrc)
        elem.add_dep(in_module_files + rel_generated)
        elem.add_dep(abs_headers)
        elem.add_item('ARGS', compile_args + header_imports + abs_generated + module_includes)
        elem.add_item('RUNDIR', rundir)
        elem.write(outfile)
        elem = NinjaBuildElement(self.all_outputs, out_module_name,
                                 'swift_COMPILER',
                                 abssrc)
        elem.add_dep(in_module_files + rel_generated)
        elem.add_item('ARGS', compile_args + abs_generated + module_includes + swiftc.get_mod_gen_args())
        elem.add_item('RUNDIR', rundir)
        elem.write(outfile)
        if isinstance(target, build.StaticLibrary):
            elem = self.generate_link(target, outfile, self.get_target_filename(target),
                               rel_objects, self.build.static_linker)
            elem.write(outfile)
        elif isinstance(target, build.Executable):
            elem = NinjaBuildElement(self.all_outputs, self.get_target_filename(target), 'swift_COMPILER', [])
            elem.add_dep(rel_objects)
            elem.add_dep(link_deps)
            elem.add_item('ARGS', link_args + swiftc.get_std_exe_link_args() + objects + abs_link_deps)
            elem.add_item('RUNDIR', rundir)
            elem.write(outfile)
        else:
            raise MesonException('Swift supports only executable and static library targets.')

    def generate_static_link_rules(self, is_cross, outfile):
        if self.build.has_language('java'):
            if not is_cross:
                self.generate_java_link(outfile)
        if is_cross:
            if self.environment.cross_info.need_cross_compiler():
                static_linker = self.build.static_cross_linker
            else:
                static_linker = self.build.static_linker
            crstr = '_CROSS'
        else:
            static_linker = self.build.static_linker
            crstr = ''
        if static_linker is None:
            return
        rule = 'rule STATIC%s_LINKER\n' % crstr
        if mesonlib.is_windows():
            command_templ = ''' command = %s @$out.rsp
 rspfile = $out.rsp
 rspfile_content = $LINK_ARGS %s $in
'''
        else:
            command_templ = ' command = %s $LINK_ARGS %s $in\n'
        command = command_templ %\
        (' '.join(static_linker.get_exelist()),
         ' '.join(static_linker.get_output_args('$out')))
        description = ' description = Static linking library $out\n\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)

    def generate_dynamic_link_rules(self, outfile):
        ctypes = [(self.build.compilers, False)]
        if self.environment.is_cross_build():
            if self.environment.cross_info.need_cross_compiler():
                ctypes.append((self.build.cross_compilers, True))
            else:
                # Native compiler masquerades as the cross compiler.
                ctypes.append((self.build.compilers, True))
        else:
            ctypes.append((self.build.cross_compilers, True))
        for (complist, is_cross) in ctypes:
            for compiler in complist:
                langname = compiler.get_language()
                if langname == 'java' or langname == 'vala' or\
                 langname == 'rust' or langname == 'cs':
                    continue
                crstr = ''
                cross_args = []
                if is_cross:
                    crstr = '_CROSS'
                    try:
                        cross_args = self.environment.cross_info.config['properties'][langname + '_link_args']
                    except KeyError:
                        pass
                rule = 'rule %s%s_LINKER\n' % (langname, crstr)
                if mesonlib.is_windows():
                    command_template = ''' command = %s @$out.rsp
 rspfile = $out.rsp
 rspfile_content = %s $ARGS  %s $in $LINK_ARGS $aliasing
'''
                else:
                    command_template = ' command = %s %s $ARGS  %s $in $LINK_ARGS $aliasing\n'
                command = command_template % \
                (' '.join(compiler.get_linker_exelist()),\
                 ' '.join(cross_args),\
                 ' '.join(compiler.get_linker_output_args('$out')))
                description = ' description = Linking target $out'
                outfile.write(rule)
                outfile.write(command)
                outfile.write(description)
                outfile.write('\n')
        scriptdir = self.environment.get_script_dir()
        outfile.write('\n')
        symrule = 'rule SHSYM\n'
        symcmd = ' command = "%s" "%s" %s %s %s %s $CROSS\n' % (ninja_quote(sys.executable),
                                                                self.environment.get_build_command(),
                                                                '--internal',
                                                                'symbolextractor',
                                                                '$in',
                                                                '$out')
        synstat = ' restat = 1\n'
        syndesc = ' description = Generating symbol file $out.\n'
        outfile.write(symrule)
        outfile.write(symcmd)
        outfile.write(synstat)
        outfile.write(syndesc)
        outfile.write('\n')

    def generate_java_compile_rule(self, compiler, outfile):
        rule = 'rule %s_COMPILER\n' % compiler.get_language()
        invoc = ' '.join([ninja_quote(i) for i in compiler.get_exelist()])
        command = ' command = %s $ARGS $in\n' % invoc
        description = ' description = Compiling Java object $in.\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)
        outfile.write('\n')

    def generate_cs_compile_rule(self, compiler, outfile):
        rule = 'rule %s_COMPILER\n' % compiler.get_language()
        invoc = ' '.join([ninja_quote(i) for i in compiler.get_exelist()])
        command = ' command = %s $ARGS $in\n' % invoc
        description = ' description = Compiling cs target $out.\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)
        outfile.write('\n')

    def generate_vala_compile_rules(self, compiler, outfile):
        rule = 'rule %s_COMPILER\n' % compiler.get_language()
        invoc = ' '.join([ninja_quote(i) for i in compiler.get_exelist()])
        command = ' command = %s $ARGS $in\n' % invoc
        description = ' description = Compiling Vala source $in.\n'
        restat = ' restat = 1\n' # ValaC does this always to take advantage of it.
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)
        outfile.write(restat)
        outfile.write('\n')

    def generate_rust_compile_rules(self, compiler, outfile):
        rule = 'rule %s_COMPILER\n' % compiler.get_language()
        invoc = ' '.join([ninja_quote(i) for i in compiler.get_exelist()])
        command = ' command = %s $ARGS $in\n' % invoc
        description = ' description = Compiling Rust source $in.\n'
        depfile = ' depfile = $targetdep\n'

        depstyle = ' deps = gcc\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)
        outfile.write(depfile)
        outfile.write(depstyle)
        outfile.write('\n')

    def generate_swift_compile_rules(self, compiler, outfile):
        rule = 'rule %s_COMPILER\n' % compiler.get_language()
        full_exe = [sys.executable,
                    self.environment.get_build_command(),
                    '--internal',
                    'dirchanger',
                    '$RUNDIR'] + compiler.get_exelist()
        invoc = ' '.join([ninja_quote(i) for i in full_exe])
        command = ' command = %s $ARGS $in\n' % invoc
        description = ' description = Compiling Swift source $in.\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)
        outfile.write('\n')

    def generate_fortran_dep_hack(self, outfile):
        if mesonlib.is_windows():
            cmd = 'cmd /C ""'
        else:
            cmd = 'true'
        template = '''# Workaround for these issues:
# https://groups.google.com/forum/#!topic/ninja-build/j-2RfBIOd_8
# https://gcc.gnu.org/bugzilla/show_bug.cgi?id=47485
rule FORTRAN_DEP_HACK
 command = %s
 description = Dep hack
 restat = 1

'''
        outfile.write(template % cmd)

    def generate_compile_rule_for(self, langname, compiler, qstr, is_cross, outfile):
        if langname == 'java':
            if not is_cross:
                self.generate_java_compile_rule(compiler, outfile)
            return
        if langname == 'cs':
            if not is_cross:
                self.generate_cs_compile_rule(compiler, outfile)
            return
        if langname == 'vala':
            if not is_cross:
                self.generate_vala_compile_rules(compiler, outfile)
            return
        if langname == 'rust':
            if not is_cross:
                self.generate_rust_compile_rules(compiler, outfile)
            return
        if langname == 'swift':
            if not is_cross:
                self.generate_swift_compile_rules(compiler, outfile)
            return
        if langname == 'fortran':
            self.generate_fortran_dep_hack(outfile)
        if is_cross:
            crstr = '_CROSS'
        else:
            crstr = ''
        rule = 'rule %s%s_COMPILER\n' % (langname, crstr)
        depargs = compiler.get_dependency_gen_args('$out', '$DEPFILE')
        quoted_depargs = []
        for d in depargs:
            if d != '$out' and d != '$in':
                d = qstr % d
            quoted_depargs.append(d)
        cross_args = []
        if is_cross:
            try:
                cross_args = self.environment.cross_info.config['properties'][langname + '_args']
            except KeyError:
                pass
        if mesonlib.is_windows():
            command_template = ''' command = %s @$out.rsp
 rspfile = $out.rsp
 rspfile_content = %s $ARGS %s %s %s $in
'''
        else:
            command_template = ' command = %s %s $ARGS %s %s %s $in\n'
        command = command_template % \
            (' '.join(compiler.get_exelist()),\
             ' '.join(cross_args),
             ' '.join(quoted_depargs),\
             ' '.join(compiler.get_output_args('$out')),\
             ' '.join(compiler.get_compile_only_args()))
        description = ' description = Compiling %s object $out\n' % langname
        if compiler.get_id() == 'msvc':
            deps = ' deps = msvc\n'
        else:
            deps = ' deps = gcc\n'
            deps += ' depfile = $DEPFILE\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(deps)
        outfile.write(description)
        outfile.write('\n')

    def generate_pch_rule_for(self, langname, compiler, qstr, is_cross, outfile):
        if langname != 'c' and langname != 'cpp':
            return
        if is_cross:
            crstr = '_CROSS'
        else:
            crstr = ''
        rule = 'rule %s%s_PCH\n' % (langname, crstr)
        depargs = compiler.get_dependency_gen_args('$out', '$DEPFILE')
        cross_args = []
        if is_cross:
            try:
                cross_args = self.environment.cross_info.config['properties'][langname + '_args']
            except KeyError:
                pass

        quoted_depargs = []
        for d in depargs:
            if d != '$out' and d != '$in':
                d = qstr % d
            quoted_depargs.append(d)
        if compiler.get_id() == 'msvc':
            output = ''
        else:
            output = ' '.join(compiler.get_output_args('$out'))
        command = " command = %s %s $ARGS %s %s %s $in\n" % \
            (' '.join(compiler.get_exelist()),\
             ' '.join(cross_args),\
             ' '.join(quoted_depargs),\
             output,\
             ' '.join(compiler.get_compile_only_args()))
        description = ' description = Precompiling header %s\n' % '$in'
        if compiler.get_id() == 'msvc':
            deps = ' deps = msvc\n'
        else:
            deps = ' deps = gcc\n'
            deps += ' depfile = $DEPFILE\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(deps)
        outfile.write(description)
        outfile.write('\n')

    def generate_compile_rules(self, outfile):
        qstr = quote_char + "%s" + quote_char
        for compiler in self.build.compilers:
            langname = compiler.get_language()
            self.generate_compile_rule_for(langname, compiler, qstr, False, outfile)
            self.generate_pch_rule_for(langname, compiler, qstr, False, outfile)
        if self.environment.is_cross_build():
            # In case we are going a target-only build, make the native compilers
            # masquerade as cross compilers.
            if self.environment.cross_info.need_cross_compiler():
                cclist = self.build.cross_compilers
            else:
                cclist = self.build.compilers
            for compiler in cclist:
                langname = compiler.get_language()
                self.generate_compile_rule_for(langname, compiler, qstr, True, outfile)
                self.generate_pch_rule_for(langname, compiler, qstr, True, outfile)
        outfile.write('\n')

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

    def generate_custom_generator_rules(self, target, outfile):
        for genlist in target.get_generated_sources():
            if isinstance(genlist, build.CustomTarget):
                continue # Customtarget has already written its output rules
            generator = genlist.get_generator()
            exe = generator.get_exe()
            exe_arr = self.exe_object_to_cmd_array(exe)
            infilelist = genlist.get_infilelist()
            outfilelist = genlist.get_outfilelist()
            base_args = generator.get_arglist()
            extra_dependencies = [os.path.join(self.build_to_src, i) for i in genlist.extra_depends]
            for i in range(len(infilelist)):
                if len(generator.outputs) == 1:
                    sole_output = os.path.join(self.get_target_private_dir(target), outfilelist[i])
                else:
                    sole_output = ''
                curfile = infilelist[i]
                infilename = os.path.join(self.build_to_src, curfile)
                outfiles = genlist.get_outputs_for(curfile)
                outfiles = [os.path.join(self.get_target_private_dir(target), of) for of in outfiles]
                args = [x.replace("@INPUT@", infilename).replace('@OUTPUT@', sole_output)\
                        for x in base_args]
                args = self.replace_outputs(args, self.get_target_private_dir(target), outfilelist)
                # We have consumed output files, so drop them from the list of remaining outputs.
                if sole_output == '':
                    outfilelist = outfilelist[len(generator.outputs):]
                relout = self.get_target_private_dir(target)
                args = [x.replace("@SOURCE_DIR@", self.build_to_src).replace("@BUILD_DIR@", relout)
                        for x in args]
                cmdlist = exe_arr + self.replace_extra_args(args, genlist)
                elem = NinjaBuildElement(self.all_outputs, outfiles, 'CUSTOM_COMMAND', infilename)
                if len(extra_dependencies) > 0:
                    elem.add_dep(extra_dependencies)
                elem.add_item('DESC', 'Generating $out')
                if isinstance(exe, build.BuildTarget):
                    elem.add_dep(self.get_target_filename(exe))
                elem.add_item('COMMAND', cmdlist)
                elem.write(outfile)

    def scan_fortran_module_outputs(self, target):
        compiler = None
        for c in self.build.compilers:
            if c.get_language() == 'fortran':
                compiler = c
                break
        if compiler is None:
            self.fortran_deps[target.get_basename()] = {}
            return
        modre = re.compile(r"\s*module\s+(\w+)", re.IGNORECASE)
        module_files = {}
        for s in target.get_sources():
            # FIXME, does not work for generated Fortran sources,
            # but those are really rare. I hope.
            if not compiler.can_compile(s):
                continue
            for line in open(os.path.join(self.environment.get_source_dir(), s.subdir, s.fname)):
                modmatch = modre.match(line)
                if modmatch is not None:
                    modname = modmatch.group(1)
                    if modname.lower() == 'procedure': # MODULE PROCEDURE construct
                        continue
                    if modname in module_files:
                        raise InvalidArguments('Namespace collision: module %s defined in two files %s and %s.' %
                                               (modname, module_files[modname], s))
                    module_files[modname] = s
        self.fortran_deps[target.get_basename()] = module_files

    def get_fortran_deps(self, compiler, src, target):
        mod_files = []
        usere = re.compile(r"\s*use\s+(\w+)", re.IGNORECASE)
        dirname = self.get_target_private_dir(target)
        tdeps= self.fortran_deps[target.get_basename()]
        for line in open(src):
            usematch = usere.match(line)
            if usematch is not None:
                usename = usematch.group(1)
                if usename not in tdeps:
                    # The module is not provided by any source file. This is due to
                    # a) missing file/typo/etc
                    # b) using a module provided by the compiler, such as OpenMP
                    # There's no easy way to tell which is which (that I know of)
                    # so just ignore this and go on. Ideally we would print a
                    # warning message to the user but this is a common occurrance,
                    # which would lead to lots of distracting noise.
                    continue
                mod_source_file = tdeps[usename]
                # Check if a source uses a module it exports itself.
                # Potential bug if multiple targets have a file with
                # the same name.
                if mod_source_file.fname == os.path.split(src)[1]:
                    continue
                mod_name = compiler.module_name_to_filename(usematch.group(1))
                mod_files.append(os.path.join(dirname, mod_name))
        return mod_files

    def generate_single_compile(self, target, outfile, src, is_generated=False, header_deps=[], order_deps=[]):
        if(isinstance(src, str) and src.endswith('.h')):
            raise RuntimeError('Fug')
        if isinstance(src, RawFilename) and src.fname.endswith('.h'):
            raise RuntimeError('Fug')
        extra_orderdeps = []
        compiler = self.get_compiler_for_source(src)
        commands = []
        # The first thing is implicit include directories: source, build and private.
        commands += compiler.get_include_args(self.get_target_private_dir(target), False)
        commands += compilers.get_base_compile_args(self.environment.coredata.base_options,
                                                    compiler)
        curdir = target.get_subdir()
        tmppath = os.path.normpath(os.path.join(self.build_to_src, curdir))
        commands += compiler.get_include_args(tmppath, False)
        if curdir ==  '':
            curdir = '.'
        commands += compiler.get_include_args(curdir, False)
        commands += self.generate_basic_compiler_args(target, compiler)
        # -I args work differently than other ones. In them the
        # first found directory is used whereas for other flags
        # (such as -ffoo -fno-foo) the latest one is used.
        # Therefore put the internal include directories here
        # at the beginning so they override args coming from
        # e.g. pkg-config.
        for i in target.get_include_dirs():
            basedir = i.get_curdir()
            for d in i.get_incdirs():
                expdir =  os.path.join(basedir, d)
                srctreedir = os.path.join(self.build_to_src, expdir)
                bargs = compiler.get_include_args(expdir, i.is_system)
                sargs = compiler.get_include_args(srctreedir, i.is_system)
                commands += bargs
                commands += sargs
            for d in i.get_extra_build_dirs():
                commands += compiler.get_include_args(d, i.is_system)
        for d in target.external_deps:
            if d.need_threads():
                commands += compiler.thread_flags()
                break
        if isinstance(src, RawFilename):
            rel_src = src.fname
        elif is_generated:
            if self.has_dir_part(src):
                rel_src = src
            else:
                rel_src = os.path.join(self.get_target_private_dir(target), src)
                abs_src = os.path.join(self.environment.get_source_dir(), rel_src)
        else:
            if isinstance(src, File):
                rel_src = src.rel_to_builddir(self.build_to_src)
            else:
                raise build.InvalidArguments('Invalid source type.')
            abs_src = os.path.join(self.environment.get_build_dir(), rel_src)
        if isinstance(src, RawFilename):
            src_filename = src.fname
        elif isinstance(src, File):
            src_filename = src.fname
        elif os.path.isabs(src):
            src_filename = os.path.basename(src)
        else:
            src_filename = src
        obj_basename = src_filename.replace('/', '_').replace('\\', '_')
        rel_obj = os.path.join(self.get_target_private_dir(target), obj_basename)
        rel_obj += '.' + self.environment.get_object_suffix()
        dep_file = compiler.depfile_for_object(rel_obj)
        if self.environment.coredata.base_options.get('b_pch', False):
            pchlist = target.get_pch(compiler.language)
        else:
            pchlist = []
        if len(pchlist) == 0:
            pch_dep = []
        else:
            arr = []
            i = os.path.join(self.get_target_private_dir(target), compiler.get_pch_name(pchlist[0]))
            arr.append(i)
            pch_dep = arr
        custom_target_include_dirs = []
        for i in target.generated:
            if isinstance(i, build.CustomTarget):
                idir = self.get_target_dir(i)
                if idir not in custom_target_include_dirs:
                    custom_target_include_dirs.append(idir)
        for i in custom_target_include_dirs:
            commands+= compiler.get_include_args(i, False)
        if self.environment.coredata.base_options.get('b_pch', False):
            commands += self.get_pch_include_args(compiler, target)
        crstr = ''
        if target.is_cross:
            crstr = '_CROSS'
        compiler_name = '%s%s_COMPILER' % (compiler.get_language(), crstr)
        extra_deps = []
        if compiler.get_language() == 'fortran':
            extra_deps += self.get_fortran_deps(compiler, abs_src, target)
            # Dependency hack. Remove once multiple outputs in Ninja is fixed:
            # https://groups.google.com/forum/#!topic/ninja-build/j-2RfBIOd_8
            for modname, srcfile in self.fortran_deps[target.get_basename()].items():
                modfile = os.path.join(self.get_target_private_dir(target),
                                       compiler.module_name_to_filename(modname))
                if srcfile == src:
                    depelem = NinjaBuildElement(self.all_outputs, modfile, 'FORTRAN_DEP_HACK', rel_obj)
                    depelem.write(outfile)
            commands += compiler.get_module_outdir_args(self.get_target_private_dir(target))

        element = NinjaBuildElement(self.all_outputs, rel_obj, compiler_name, rel_src)
        for d in header_deps:
            if isinstance(d, RawFilename):
                d = d.fname
            elif not self.has_dir_part(d):
                d = os.path.join(self.get_target_private_dir(target), d)
            element.add_dep(d)
        for d in extra_deps:
            element.add_dep(d)
        for d in order_deps:
            if isinstance(d, RawFilename):
                d = d.fname
            elif not self.has_dir_part(d):
                d = os.path.join(self.get_target_private_dir(target), d)
            element.add_orderdep(d)
        element.add_orderdep(pch_dep)
        element.add_orderdep(extra_orderdeps)
        for i in self.get_fortran_orderdeps(target, compiler):
            element.add_orderdep(i)
        element.add_item('DEPFILE', dep_file)
        element.add_item('ARGS', commands)
        element.write(outfile)
        return rel_obj

    def has_dir_part(self, fname):
        return '/' in fname or '\\' in fname

    # Fortran is a bit weird (again). When you link against a library, just compiling a source file
    # requires the mod files that are output when single files are built. To do this right we would need to
    # scan all inputs and write out explicit deps for each file. That is stoo slow and too much effort so
    # instead just have an ordered dependendy on the library. This ensures all required mod files are created.
    # The real deps are then detected via dep file generation from the compiler. This breaks on compilers that
    # produce incorrect dep files but such is life.
    def get_fortran_orderdeps(self, target, compiler):
        if compiler.language != 'fortran':
            return []
        return [os.path.join(self.get_target_dir(lt), lt.get_filename()) for lt in target.link_targets]

    def generate_msvc_pch_command(self, target, compiler, pch):
        if len(pch) != 2:
            raise RuntimeError('MSVC requires one header and one source to produce precompiled headers.')
        header = pch[0]
        source = pch[1]
        pchname = compiler.get_pch_name(header)
        dst = os.path.join(self.get_target_private_dir(target), pchname)

        commands = []
        commands += self.generate_basic_compiler_args(target, compiler)
        just_name = os.path.split(header)[1]
        (objname, pch_args) = compiler.gen_pch_args(just_name, source, dst)
        commands += pch_args
        dep = dst + '.' + compiler.get_depfile_suffix()
        return (commands, dep, dst, [objname])

    def generate_gcc_pch_command(self, target, compiler, pch):
        commands = []
        commands += self.generate_basic_compiler_args(target, compiler)
        dst = os.path.join(self.get_target_private_dir(target),
                           os.path.split(pch)[-1] + '.' + compiler.get_pch_suffix())
        dep = dst + '.' + compiler.get_depfile_suffix()
        return (commands, dep, dst, []) # Gcc does not create an object file during pch generation.

    def generate_pch(self, target, outfile):
        cstr = ''
        pch_objects = []
        if target.is_cross:
            cstr = '_CROSS'
        for lang in ['c', 'cpp']:
            pch = target.get_pch(lang)
            if len(pch) == 0:
                continue
            if '/' not in pch[0] or '/' not in pch[-1]:
                raise build.InvalidArguments('Precompiled header of "%s" must not be in the same directory as source, please put it in a subdirectory.' % target.get_basename())
            compiler = self.get_compiler_for_lang(lang)
            if compiler.id == 'msvc':
                src = os.path.join(self.build_to_src, target.get_source_subdir(), pch[-1])
                (commands, dep, dst, objs) = self.generate_msvc_pch_command(target, compiler, pch)
                extradep = os.path.join(self.build_to_src, target.get_source_subdir(), pch[0])
            else:
                src = os.path.join(self.build_to_src, target.get_source_subdir(), pch[0])
                (commands, dep, dst, objs) = self.generate_gcc_pch_command(target, compiler, pch[0])
                extradep = None
            pch_objects += objs
            rulename = compiler.get_language() + cstr + '_PCH'
            elem = NinjaBuildElement(self.all_outputs, dst, rulename, src)
            if extradep is not None:
                elem.add_dep(extradep)
            elem.add_item('ARGS', commands)
            elem.add_item('DEPFILE', dep)
            elem.write(outfile)
        return pch_objects

    def generate_shsym(self, outfile, target):
        target_name = self.get_target_filename(target)
        targetdir = self.get_target_private_dir(target)
        symname = os.path.join(targetdir, target_name + '.symbols')
        elem = NinjaBuildElement(self.all_outputs, symname, 'SHSYM', target_name)
        if self.environment.is_cross_build() and self.environment.cross_info.need_cross_compiler():
            elem.add_item('CROSS', '--cross-host=' + self.environment.cross_info.config['host_machine']['system'])
        elem.write(outfile)

    def generate_link(self, target, outfile, outname, obj_list, linker, extra_args=[]):
        if isinstance(target, build.StaticLibrary):
            linker_base = 'STATIC'
        else:
            linker_base = linker.get_language() # Fixme.
        if isinstance(target, build.SharedLibrary):
            self.generate_shsym(outfile, target)
        crstr = ''
        if target.is_cross:
            crstr = '_CROSS'
        linker_rule = linker_base + crstr + '_LINKER'
        abspath = os.path.join(self.environment.get_build_dir(), target.subdir)
        commands = []
        commands += linker.get_linker_always_args()
        if not isinstance(target, build.StaticLibrary):
            commands += compilers.get_base_link_args(self.environment.coredata.base_options,
                                                     linker)
        commands += linker.get_buildtype_linker_args(self.environment.coredata.get_builtin_option('buildtype'))
        commands += linker.get_option_link_args(self.environment.coredata.compiler_options)
        if not(isinstance(target, build.StaticLibrary)):
            commands += self.environment.coredata.external_link_args[linker.get_language()]
        if isinstance(target, build.Executable):
            commands += linker.get_std_exe_link_args()
        elif isinstance(target, build.SharedLibrary):
            commands += linker.get_std_shared_lib_link_args()
            commands += linker.get_pic_args()
            if hasattr(target, 'soversion'):
                soversion = target.soversion
            else:
                soversion = None
            commands += linker.get_soname_args(target.name, abspath, soversion)
            if target.vs_module_defs and hasattr(linker, 'gen_vs_module_defs_args'):
                commands += linker.gen_vs_module_defs_args(target.vs_module_defs.rel_to_builddir(self.build_to_src))
        elif isinstance(target, build.StaticLibrary):
            commands += linker.get_std_link_args()
        else:
            raise RuntimeError('Unknown build target type.')
        # Link arguments of static libraries are not put in the command line of
        # the library. They are instead appended to the command line where
        # the static library is used.
        if linker_base == 'STATIC':
            dependencies = []
        else:
            dependencies = target.get_dependencies()
        commands += self.build_target_link_arguments(linker, dependencies)
        for d in target.external_deps:
            if d.need_threads():
                commands += linker.thread_link_flags()
        if not isinstance(target, build.StaticLibrary):
            commands += target.link_args
        # External deps must be last because target link libraries may depend on them.
        if not(isinstance(target, build.StaticLibrary)):
            for dep in target.get_external_deps():
                commands += dep.get_link_args()
            for d in target.get_dependencies():
                if isinstance(d, build.StaticLibrary):
                    for dep in d.get_external_deps():
                        commands += dep.get_link_args()
        commands += linker.build_rpath_args(self.environment.get_build_dir(),\
                                            self.determine_rpath_dirs(target), target.install_rpath)
        custom_target_libraries = self.get_custom_target_provided_libraries(target)
        commands += extra_args
        commands += custom_target_libraries
        commands = linker.unix_link_flags_to_native(commands)
        dep_targets = [self.get_dependency_filename(t) for t in dependencies]
        dep_targets += [os.path.join(self.environment.source_dir,
                                     target.subdir, t) for t in target.link_depends]
        elem = NinjaBuildElement(self.all_outputs, outname, linker_rule, obj_list)
        elem.add_dep(dep_targets + custom_target_libraries)
        elem.add_item('LINK_ARGS', commands)
        return elem

    def determine_rpath_dirs(self, target):
        link_deps = target.get_all_link_deps()
        result = []
        for ld in link_deps:
            prospective = self.get_target_dir(ld)
            if not prospective in result:
                result.append(prospective)
        return result

    def get_dependency_filename(self, t):
        if isinstance(t, build.SharedLibrary):
            return os.path.join(self.get_target_private_dir(t), self.get_target_filename(t) + '.symbols')
        return self.get_target_filename(t)

    def generate_shlib_aliases(self, target, outdir):
        basename = target.get_filename()
        aliases = target.get_aliaslist()
        for alias in aliases:
            aliasfile = os.path.join(self.environment.get_build_dir(), outdir, alias)
            try:
                os.remove(aliasfile)
            except Exception:
                pass
            try:
                os.symlink(basename, aliasfile)
            except NotImplementedError:
                mlog.debug("Library versioning disabled because symlinks are not supported.")
            except OSError:
                mlog.debug("Library versioning disabled because we do not have symlink creation privileges.")

    def generate_gcov_clean(self, outfile):
            gcno_elem = NinjaBuildElement(self.all_outputs, 'clean-gcno', 'CUSTOM_COMMAND', 'PHONY')
            script_root = self.environment.get_script_dir()
            clean_script = os.path.join(script_root, 'delwithsuffix.py')
            gcno_elem.add_item('COMMAND', [sys.executable, clean_script, '.', 'gcno'])
            gcno_elem.add_item('description', 'Deleting gcno files')
            gcno_elem.write(outfile)

            gcda_elem = NinjaBuildElement(self.all_outputs, 'clean-gcda', 'CUSTOM_COMMAND', 'PHONY')
            script_root = self.environment.get_script_dir()
            clean_script = os.path.join(script_root, 'delwithsuffix.py')
            gcda_elem.add_item('COMMAND', [sys.executable, clean_script, '.', 'gcda'])
            gcda_elem.add_item('description', 'Deleting gcda files')
            gcda_elem.write(outfile)

    def is_compilable_file(self, filename):
        if filename.endswith('.cpp') or\
        filename.endswith('.c') or\
        filename.endswith('.cxx') or\
        filename.endswith('.cc') or\
        filename.endswith('.C'):
            return True
        return False

    def process_dep_gens(self, outfile, target):
        src_deps = []
        other_deps = []
        for rule in self.dep_rules.values():
            srcs = target.get_original_kwargs().get(rule.src_keyword, [])
            if isinstance(srcs, str):
                srcs = [srcs]
            for src in srcs:
                plainname = os.path.split(src)[1]
                basename = plainname.split('.')[0]
                outname = rule.name_templ.replace('@BASENAME@', basename).replace('@PLAINNAME@', plainname)
                outfilename = os.path.join(self.get_target_private_dir(target), outname)
                infilename = os.path.join(self.build_to_src, target.get_source_subdir(), src)
                elem = NinjaBuildElement(self.all_outputs, outfilename, rule.name, infilename)
                elem.write(outfile)
                if self.is_compilable_file(outfilename):
                    src_deps.append(outfilename)
                else:
                    other_deps.append(outfilename)
        return (src_deps, other_deps)

    def generate_ending(self, outfile):
        targetlist = [self.get_target_filename(t) for t in self.build.get_targets().values()\
                      if not isinstance(t, build.RunTarget)]

        elem = NinjaBuildElement(self.all_outputs, 'all', 'phony', targetlist)
        elem.write(outfile)

        default = 'default all\n\n'
        outfile.write(default)

        ninja_command = environment.detect_ninja()
        if ninja_command is None:
            raise MesonException('Could not detect ninja command')
        elem = NinjaBuildElement(self.all_outputs, 'clean', 'CUSTOM_COMMAND', 'PHONY')
        elem.add_item('COMMAND', [ninja_command, '-t', 'clean'])
        elem.add_item('description', 'Cleaning')
        if 'b_coverage' in self.environment.coredata.base_options and \
           self.environment.coredata.base_options['b_coverage'].value:
            self.generate_gcov_clean(outfile)
            elem.add_dep('clean-gcda')
            elem.add_dep('clean-gcno')
        elem.write(outfile)

        deps = self.get_regen_filelist()
        elem = NinjaBuildElement(self.all_outputs, 'build.ninja', 'REGENERATE_BUILD', deps)
        elem.add_item('pool', 'console')
        elem.write(outfile)

        elem = NinjaBuildElement(self.all_outputs, deps, 'phony', '')
        elem.write(outfile)
