# Copyright 2012 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mparser
import os, sys, re, pickle, uuid
import environment, mlog
from meson_install import InstallData
from build import InvalidArguments
import build
import shutil
from coredata import MesonException

if environment.is_windows():
    quote_char = '"'
    execute_wrapper = 'cmd /c'
else:
    quote_char = "'"
    execute_wrapper = ''

def ninja_quote(text):
    return text.replace(' ', '$ ').replace(':', '$:')

def do_replacement(regex, line, confdata):
    match = re.search(regex, line)
    while match:
        varname = match.group(1)
        if varname in confdata.keys():
            var = confdata.get(varname)
            if isinstance(var, str):
                pass
            elif isinstance(var, mparser.StringNode):
                var = var.value
            elif isinstance(var, int):
                var = str(var)
            else:
                raise RuntimeError('Tried to replace a variable with something other than a string or int.')
        else:
            var = ''
        line = line.replace('@' + varname + '@', var)
        match = re.search(regex, line)
    return line

def do_mesondefine(line, confdata):
    arr = line.split()
    if len(arr) != 2:
        raise build.InvalidArguments('#mesondefine does not contain exactly two tokens: %s', line.strip())
    varname = arr[1]
    try:
        v = confdata.get(varname)
    except KeyError:
        return '/* undef %s */\n' % varname
    if isinstance(v, mparser.BooleanNode):
        v = v.value
    if isinstance(v, bool):
        if v:
            return '#define %s\n' % varname
        else:
            return '#undef %s\n' % varname
    elif isinstance(v, int):
        return '#define %s %d\n' % (varname, v)
    elif isinstance(v, str):
        return '#define %s %s\n' % (varname, v)
    else:
        raise build.InvalidArguments('#mesondefine argument "%s" is of unknown type.' % varname)

def replace_if_different(dst, dst_tmp):
    # If contents are identical, don't touch the file to prevent
    # unnecessary rebuilds.
    try:
        if open(dst, 'r').read() == open(dst_tmp, 'r').read():
            os.unlink(dst_tmp)
            return
    except FileNotFoundError:
        pass
    os.replace(dst_tmp, dst)

def do_conf_file(src, dst, confdata):
    data = open(src).readlines()
    regex = re.compile('@(.*?)@')
    result = []
    for line in data:
        if line.startswith('#mesondefine'):
            line = do_mesondefine(line, confdata)
        else:
            line = do_replacement(regex, line, confdata)
        result.append(line)
    dst_tmp = dst + '~'
    open(dst_tmp, 'w').writelines(result)
    replace_if_different(dst, dst_tmp)

class TestSerialisation:
    def __init__(self, name, fname, is_cross, exe_wrapper, is_parallel, cmd_args, env):
        self.name = name
        self.fname = fname
        self.is_cross = is_cross
        self.exe_runner = exe_wrapper
        self.is_parallel = is_parallel
        self.cmd_args = cmd_args
        self.env = env

# This class contains the basic functionality that is needed by all backends.
# Feel free to move stuff in and out of it as you see fit.
class Backend():
    def __init__(self, build, interp):
        self.build = build
        self.environment = build.environment
        self.interpreter = interp
        self.processed_targets = {}
        self.dep_rules = {}
        self.build_to_src = os.path.relpath(self.environment.get_source_dir(),
                                            self.environment.get_build_dir())

    def get_compiler_for_lang(self, lang):
        for i in self.build.compilers:
            if i.language == lang:
                return i
        raise RuntimeError('No compiler for language ' + lang)

    def get_compiler_for_source(self, src):
        for i in self.build.compilers:
            if i.can_compile(src):
                return i
        raise RuntimeError('No specified compiler can handle file ' + src)

    def get_target_filename(self, target):
        targetdir = self.get_target_dir(target)
        filename = os.path.join(targetdir, target.get_filename())
        return filename

    def get_target_dir(self, target):
        dirname = target.get_subdir()
        os.makedirs(os.path.join(self.environment.get_build_dir(), dirname), exist_ok=True)
        return dirname
    
    def get_target_private_dir(self, target):
        dirname = os.path.join(self.get_target_dir(target), target.get_basename() + '.dir')
        os.makedirs(os.path.join(self.environment.get_build_dir(), dirname), exist_ok=True)
        return dirname

    def generate_unity_files(self, target, unity_src):
        langlist = {}
        abs_files = []
        result = []
        for src in unity_src:
            comp = self.get_compiler_for_source(src)
            language = comp.get_language()
            suffix = '.' + comp.get_default_suffix()
            if language not in langlist:
                outfilename = os.path.join(self.get_target_private_dir(target), target.name + '-unity' + suffix)
                outfileabs = os.path.join(self.environment.get_build_dir(), outfilename)
                outfileabs_tmp = outfileabs + '.tmp'
                abs_files.append(outfileabs)
                outfile = open(outfileabs_tmp, 'w')
                langlist[language] = outfile
                result.append(outfilename)
            ofile = langlist[language]
            ofile.write('#include<%s>\n' % src)
        [x.close() for x in langlist.values()]
        [replace_if_different(x, x + '.tmp') for x in abs_files]
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

    def generate_target(self, target, outfile):
        name = target.get_basename()
        if name in self.processed_targets:
            return
        if isinstance(target, build.Jar):
            self.generate_jar_target(target, outfile)
            return
        # The following deals with C/C++ compilation.
        (gen_src_deps, gen_other_deps) = self.process_dep_gens(outfile, target)
        self.process_target_dependencies(target, outfile)
        self.generate_custom_generator_rules(target, outfile)
        outname = self.get_target_filename(target)
        obj_list = []
        use_pch = self.environment.coredata.use_pch
        is_unity = self.environment.coredata.unity
        if use_pch and target.has_pch():
            self.generate_pch(target, outfile)
        header_deps = gen_other_deps
        unity_src = []
        unity_deps = [] # Generated sources that must be built before compiling a Unity target.
        for genlist in target.get_generated_sources():
            for src in genlist.get_outfilelist():
                if not self.environment.is_header(src):
                    if is_unity:
                        if '/' in src:
                            rel_src = src
                        else:
                            rel_src = os.path.join(self.get_target_private_dir(target), src)
                        unity_deps.append(rel_src)
                        abs_src = os.path.join(self.environment.get_build_dir(), rel_src)
                        unity_src.append(abs_src)
                    else:
                        obj_list.append(self.generate_single_compile(target, outfile, src, True))
                else:
                    header_deps.append(src)
        src_list = []
        for src in gen_src_deps:
                src_list.append(src)
                if is_unity:
                    unity_src.append(src)
                else:
                    obj_list.append(self.generate_single_compile(target, outfile, src, True))
        for src in target.get_sources():
            if not self.environment.is_header(src):
                src_list.append(src)
                if is_unity:
                    abs_src = os.path.join(self.environment.get_source_dir(),
                                           target.get_subdir(), src)
                    unity_src.append(abs_src)
                else:
                    obj_list.append(self.generate_single_compile(target, outfile, src, False, header_deps))
        obj_list += self.flatten_object_list(target)
        if is_unity:
            for src in self.generate_unity_files(target, unity_src):
                obj_list.append(self.generate_single_compile(target, outfile, src, True, unity_deps + header_deps))
        linker = self.determine_linker(target, src_list)
        elem = self.generate_link(target, outfile, outname, obj_list, linker)
        self.generate_shlib_aliases(target, self.get_target_dir(target), outfile, elem)
        self.processed_targets[name] = True

    def generate_jar_target(self, target, outfile):
        fname = target.get_filename()
        subdir = target.get_subdir()
        outname_rel = os.path.join(subdir, fname)
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
            class_list.append(self.generate_single_java_compile(subdir, src, target, compiler, outfile))
        jar_rule = 'java_LINKER'
        commands = [c+m+e+f]
        if e != '':
            commands.append(main_class)
        commands.append(self.get_target_filename(target))
        commands += ['-C', self.get_target_private_dir(target)]
        commands += class_list
        elem = NinjaBuildElement(outname_rel, jar_rule, [])
        elem.add_dep([os.path.join(self.get_target_private_dir(target), i) for i in class_list])
        elem.add_item('FLAGS', commands)
        elem.write(outfile)

    def generate_single_java_compile(self, subdir, src, target, compiler, outfile):
        buildtype = self.environment.coredata.buildtype
        args = []
        if buildtype == 'debug':
            args += compiler.get_debug_flags()
        args += compiler.get_output_flags(self.get_target_private_dir(target))
        rel_src = os.path.join(self.build_to_src, subdir, src)
        plain_class_path = src[:-4] + 'class'
        rel_obj = os.path.join(self.get_target_private_dir(target), plain_class_path)
        element = NinjaBuildElement(rel_obj,
                    compiler.get_language() + '_COMPILER', rel_src)
        element.add_item('FLAGS', args)
        element.write(outfile)
        return plain_class_path

    def determine_linker(self, target, src):
        if isinstance(target, build.StaticLibrary):
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
        return self.build.compilers[0]

    def determine_ext_objs(self, extobj, proj_dir_to_build_root=''):
        result = []
        targetdir = self.get_target_private_dir(extobj.target)
        suffix = '.' + self.environment.get_object_suffix()
        for osrc in extobj.srclist:
            if not self.source_suffix_in_objs:
                osrc = '.'.join(osrc.split('.')[:-1])
            objname = os.path.join(proj_dir_to_build_root,
                                   targetdir, os.path.basename(osrc) + suffix)
            result.append(objname)
        return result

    def process_target_dependencies(self, target, outfile):
        for t in target.get_dependencies():
            tname = t.get_basename()
            if not tname in self.processed_targets:
                self.generate_target(t, outfile)

    def get_pch_include_args(self, compiler, target):
        args = []
        pchpath = self.get_target_private_dir(target)
        includearg = compiler.get_include_arg(pchpath)
        for lang in ['c', 'cpp']:
            p = target.get_pch(lang)
            if len(p) == 0:
                continue
            if compiler.can_compile(p[-1]):
                header = p[0]
                args += compiler.get_pch_use_args(pchpath, header)
        if len(args) > 0:
            args = [includearg] + args
        return args

    def generate_basic_compiler_flags(self, target, compiler):
        commands = []
        commands += compiler.get_always_flags()
        commands += self.build.get_global_flags(compiler)
        commands += target.get_extra_args(compiler.get_language())
        if self.environment.coredata.buildtype != 'plain':
            commands += compiler.get_debug_flags()
            commands += compiler.get_std_warn_flags()
        if self.environment.coredata.buildtype == 'optimized':
            commands += compiler.get_std_opt_flags()
        if self.environment.coredata.coverage:
            commands += compiler.get_coverage_flags()
        if isinstance(target, build.SharedLibrary):
            commands += compiler.get_pic_flags()
        for dep in target.get_external_deps():
            commands += dep.get_compile_flags()
            if isinstance(target, build.Executable):
                commands += dep.get_exe_flags()

        return commands

    def build_target_link_arguments(self, compiler, deps):
        args = []
        for d in deps:
            if not isinstance(d, build.StaticLibrary) and\
            not isinstance(d, build.SharedLibrary):
                raise RuntimeError('Tried to link with a non-library target "%s".' % d.get_basename())
            fname = self.get_target_filename(d)
            if compiler.id == 'msvc':
                if fname.endswith('dll'):
                    fname = fname[:-3] + 'lib'
            args.append(fname)
        return args

    def generate_configure_files(self):
        for cf in self.build.get_configure_files():
            infile = os.path.join(self.environment.get_source_dir(),
                                  cf.get_subdir(),
                                  cf.get_source_name())
            outdir = os.path.join(self.environment.get_build_dir(),
                                   cf.get_subdir())
            os.makedirs(outdir, exist_ok=True)
            outfile = os.path.join(outdir, cf.get_target_name())
            confdata = cf.get_configuration_data()
            do_conf_file(infile, outfile, confdata)

    def write_test_file(self, datafile):
        arr = []
        for t in self.build.get_tests():
            fname = os.path.join(self.environment.get_build_dir(), self.get_target_filename(t.get_exe()))
            is_cross = self.environment.is_cross_build()
            if is_cross:
                exe_wrapper = self.environment.cross_info.get('exe_wrapper', None)
            else:
                exe_wrapper = None
            ts = TestSerialisation(t.get_name(), fname, is_cross, exe_wrapper,
                                   t.is_parallel, t.cmd_args, t.env)
            arr.append(ts)
        pickle.dump(arr, datafile)

    def generate_pkgconfig_files(self):
        for p in self.build.pkgconfig_gens:
            outdir = self.environment.scratch_dir
            fname = os.path.join(outdir, p.filebase + '.pc')
            ofile = open(fname, 'w')
            ofile.write('prefix=%s\n' % self.environment.get_coredata().prefix)
            ofile.write('libdir=${prefix}/%s\n' % self.environment.get_coredata().libdir)
            ofile.write('includedir=${prefix}/%s\n\n' % self.environment.get_coredata().includedir)
            ofile.write('Name: %s\n' % p.name)
            if len(p.description) > 0:
                ofile.write('Description: %s\n' % p.description)
            if len(p.version) > 0:
                ofile.write('Version: %s\n' % p.version)
            ofile.write('Libs: -L${libdir} ')
            for l in p.libraries:
                ofile.write('-l%s ' % l.name)
            ofile.write('\n')
            ofile.write('CFlags: ')
            for h in p.subdirs:
                if h == '.':
                    h = ''
                ofile.write(os.path.join('-I${includedir}', h))
                ofile.write(' ')
            ofile.write('\n')

class NinjaBuildElement():
    def __init__(self, outfilenames, rule, infilenames):
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
        line = 'build %s: %s %s' % (' '.join([ninja_quote(i) for i in  self.outfilenames]),\
                                    self.rule,
                                    ' '.join([ninja_quote(i) for i in self.infilenames]))
        if len(self.deps) > 0:
            line += ' | ' + ' '.join([ninja_quote(x) for x in self.deps])
        if len(self.orderdeps) > 0:
            line += ' || ' + ' '.join([ninja_quote(x) for x in self.orderdeps])
        line += '\n'
        outfile.write(line)

        for e in self.elems:
            (name, elems) = e
            should_quote = True
            if name == 'DEPFILE' or name == 'DESC':
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
                newelems.append(templ % ninja_quote(i))
            line += ' '.join(newelems)
            line += '\n'
            outfile.write(line)
        outfile.write('\n')

class NinjaBackend(Backend):

    def __init__(self, build, interp):
        super().__init__(build, interp)
        self.source_suffix_in_objs = True
        self.ninja_filename = 'build.ninja'

    def generate(self):
        outfilename = os.path.join(self.environment.get_build_dir(), self.ninja_filename)
        tempfilename = outfilename + '~'
        outfile = open(tempfilename, 'w')
        self.generate_configure_files()
        self.generate_pkgconfig_files()
        outfile.write('# This is the build file for project "%s"\n' % self.build.get_project())
        outfile.write('# It is autogenerated by the Meson build system.\n')
        outfile.write('# Do not edit by hand.\n\n')
        outfile.write('ninja_required_version = 1.3.4\n\n')
        self.generate_rules(outfile)
        outfile.write('# Build rules for targets\n\n')
        [self.generate_target(t, outfile) for t in self.build.get_targets().values()]
        if len(self.build.pot) > 0:
            outfile.write('# Build rules for localisation.\n\n')
            self.generate_po(outfile)
        outfile.write('# Test rules\n\n')
        self.generate_tests(outfile)
        outfile.write('# Install rules\n\n')
        self.generate_install(outfile)
        if self.environment.coredata.coverage:
            outfile.write('# Coverage rules\n\n')
            self.generate_coverage_rules(outfile)
        outfile.write('# Suffix\n\n')
        self.generate_ending(outfile)
        # Only ovewrite the old build file after the new one has been
        # fully created.
        outfile.close()
        os.replace(tempfilename, outfilename)

    def generate_po(self, outfile):
        for p in self.build.pot:
            (packagename, languages, subdir) = p
            input_file = os.path.join(subdir, 'POTFILES')
            elem = NinjaBuildElement('pot', 'GEN_POT', [])
            elem.add_item('PACKAGENAME', packagename)
            elem.add_item('OUTFILE', packagename + '.pot')
            elem.add_item('FILELIST', os.path.join(self.environment.get_source_dir(), input_file))
            elem.add_item('OUTDIR', os.path.join(self.environment.get_source_dir(), subdir))
            elem.write(outfile)
            for l in languages:
                infile = os.path.join(self.environment.get_source_dir(), subdir, l + '.po')
                outfilename = os.path.join(subdir, l + '.gmo')
                lelem = NinjaBuildElement(outfilename, 'GEN_GMO', infile)
                lelem.add_item('INFILE', infile)
                lelem.add_item('OUTFILE', outfilename)
                lelem.write(outfile)

    def generate_coverage_rules(self, outfile):
        (gcovr_exe, lcov_exe, genhtml_exe) = environment.find_coverage_tools()
        added_rule = False
        if gcovr_exe:
            added_rule = True
            elem = NinjaBuildElement('coverage-xml', 'CUSTOM_COMMAND', '')
            elem.add_item('COMMAND', [gcovr_exe, '-x', '-r', self.environment.get_build_dir(),\
                                      '-o', os.path.join(self.environment.get_log_dir(), 'coverage.xml')])
            elem.add_item('DESC', 'Generating XML coverage report.')
            elem.write(outfile)
            elem = NinjaBuildElement('coverage-text', 'CUSTOM_COMMAND', '')
            elem.add_item('COMMAND', [gcovr_exe, '-r', self.environment.get_build_dir(),\
                                      '-o', os.path.join(self.environment.get_log_dir(), 'coverage.txt')])
            elem.add_item('DESC', 'Generating text coverage report.')
            elem.write(outfile)
        if lcov_exe and genhtml_exe:
            added_rule = True
            phony_elem = NinjaBuildElement('coverage-html', 'phony', 'coveragereport/index.html')
            phony_elem.write(outfile)

            elem = NinjaBuildElement('coveragereport/index.html', 'CUSTOM_COMMAND', '')
            command = [lcov_exe, '--directory', self.environment.get_build_dir(),\
                       '--capture', '--output-file', 'coverage.info', '--no-checksum',\
                       '&&', genhtml_exe, '--prefix', self.environment.get_build_dir(),\
                       '--output-directory', self.environment.get_log_dir(), '--title', 'Code coverage',\
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
        depfixer = os.path.join(script_root, 'depfixer.py')
        d = InstallData(self.environment.get_prefix(), depfixer, './') # Fixme
        elem = NinjaBuildElement('install', 'CUSTOM_COMMAND', '')
        elem.add_dep('all')
        elem.add_item('DESC', 'Installing files.')
        elem.add_item('COMMAND', [sys.executable, install_script, install_data_file])
        self.generate_target_install(d)
        self.generate_header_install(d)
        self.generate_man_install(d)
        self.generate_data_install(d)
        self.generate_po_install(d, elem)
        self.generate_pkgconfig_install(d)
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
                d.po.append((src_file, self.environment.coredata.localedir, lang))
                elem.add_dep(rel_src)

    def generate_target_install(self, d):
        libdir = self.environment.get_libdir()
        bindir = self.environment.get_bindir()

        should_strip = self.environment.coredata.strip
        for t in self.build.get_targets().values():
            if t.should_install():
                outdir = t.get_custom_install_dir()
                if outdir is None:
                    if isinstance(t, build.Executable):
                        outdir = bindir
                    else:
                        outdir = libdir
                i = [self.get_target_filename(t), outdir, t.get_aliaslist(), should_strip]
                d.targets.append(i)

    def generate_pkgconfig_install(self, d):
        pkgroot = os.path.join(self.environment.coredata.prefix,
                               self.environment.coredata.libdir, 'pkgconfig')

        for p in self.build.pkgconfig_gens:
            pcfile = p.filebase + '.pc'
            srcabs = os.path.join(self.environment.get_scratch_dir(),
                                  pcfile)
            dstabs = os.path.join(pkgroot, pcfile)
            i = [srcabs, dstabs]
            d.man.append(i)

    def generate_header_install(self, d):
        incroot = self.environment.get_includedir()
        headers = self.build.get_headers()

        for h in headers:
            outdir = h.get_custom_install_dir()
            if outdir is None:
                outdir = os.path.join(incroot, h.get_subdir())
            for f in h.get_sources():
                abspath = os.path.join(self.environment.get_source_dir(), f) # FIXME
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
                srcabs = os.path.join(self.environment.get_source_dir(), f)
                dstabs = os.path.join(subdir, f + '.gz')
                i = [srcabs, dstabs]
                d.man.append(i)

    def generate_data_install(self, d):
        dataroot = self.environment.get_datadir()
        data = self.build.get_data()
        for de in data:
            subdir = de.get_custom_install_dir()
            if subdir is None:
                subdir = os.path.join(dataroot, de.get_subdir())
            for f in de.get_sources():
                srcabs = os.path.join(self.environment.get_source_dir(), f)
                dstabs = os.path.join(subdir, f)
                i = [srcabs, dstabs]
                d.data.append(i)

    def generate_tests(self, outfile):
        valgrind = environment.find_valgrind()
        script_root = self.environment.get_script_dir()
        test_script = os.path.join(script_root, 'meson_test.py')
        test_data = os.path.join(self.environment.get_scratch_dir(), 'meson_test_setup.dat')
        cmd = [sys.executable, test_script, test_data]
        elem = NinjaBuildElement('test', 'CUSTOM_COMMAND', 'all')
        elem.add_item('COMMAND', cmd)
        elem.add_item('DESC', 'Running test suite.')
        elem.write(outfile)

        if valgrind:
            velem = NinjaBuildElement('test-valgrind', 'CUSTOM_COMMAND', 'all')
            velem.add_item('COMMAND', cmd + ['--wrapper=' + valgrind])
            velem.add_item('DESC', 'Running test suite under Valgrind.')
            velem.write(outfile)

        datafile = open(test_data, 'wb')
        self.write_test_file(datafile)
        datafile.close()

    def generate_dep_gen_rules(self, outfile):
        outfile.write('# Rules for external dependency generators.\n\n')
        processed = {}
        for dep in self.environment.coredata.deps.values():
            name = dep.get_name()
            if name in processed:
                continue
            processed[name] = True
            for rule in dep.get_generate_rules():
                outfile.write('rule %s\n' % rule.name)
                command = ' '.join([ninja_quote(x) for x in rule.cmd_list])
                command = command.replace('@INFILE@', '$in').replace('@OUTFILE@', '$out')
                command = command.replace('@SOURCE_ROOT@', self.environment.get_source_dir())
                command = command.replace('@BUILD_ROOT@', self.environment.get_build_dir())
                outfile.write(' command = %s\n' % command)
                desc = rule.description.replace('@INFILE@', '$in')
                outfile.write(' description = %s\n' % desc)
                if rule.src_keyword in self.dep_rules:
                    raise InvalidArguments('Multiple rules for keyword %s.' % rule.src_keyword)
                self.dep_rules[rule.src_keyword] = rule
            outfile.write('\n')

    def generate_rules(self, outfile):
        outfile.write('# Rules for compiling.\n\n')
        self.generate_compile_rules(outfile)
        outfile.write('# Rules for linking.\n\n')
        if self.environment.is_cross_build():
            self.generate_static_link_rules(True, outfile)
        self.generate_static_link_rules(False, outfile)
        self.generate_dynamic_link_rules(outfile)
        self.generate_dep_gen_rules(outfile)
        outfile.write('# Other rules\n\n')
        outfile.write('rule CUSTOM_COMMAND\n')
        outfile.write(' command = $COMMAND\n')
        outfile.write(' description = $DESC\n')
        outfile.write(' restat = 1\n\n')
        outfile.write('rule REGENERATE_BUILD\n')
        c = (quote_char + ninja_quote(sys.executable) + quote_char,
             quote_char + ninja_quote(self.environment.get_build_command())  + quote_char,
             quote_char + ninja_quote(self.environment.get_source_dir())  + quote_char,
             quote_char + ninja_quote(self.environment.get_build_dir())  + quote_char)
        outfile.write(" command = %s %s %s %s --backend ninja secret-handshake\n" % c)
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

    def generate_java_link(self, outfile):
        rule = 'rule java_LINKER\n'
        command = ' command = jar $FLAGS\n'
        description = ' description = Creating jar $out.\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)
        outfile.write('\n')

    def generate_static_link_rules(self, is_cross, outfile):
        if self.build.has_language('java'):
            if not is_cross:
                self.generate_java_link(outfile)
        if is_cross:
            static_linker = self.build.static_cross_linker
            crstr = '_CROSS'
        else:
            static_linker = self.build.static_linker
            crstr = ''
        if static_linker is None:
            return
        rule = 'rule STATIC%s_LINKER\n' % crstr
        command = ' command = %s  $LINK_FLAGS %s $in\n' % \
        (' '.join(static_linker.get_exelist()),
        ' '.join(static_linker.get_output_flags('$out')))
        description = ' description = Static linking library $out\n\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)

    def generate_dynamic_link_rules(self, outfile):
        ctypes = [(self.build.compilers, False), (self.build.cross_compilers, True)]
        for (complist, is_cross) in ctypes:
            for compiler in complist:
                langname = compiler.get_language()
                if langname == 'java':
                    continue
                crstr = ''
                if is_cross:
                    crstr = '_CROSS'
                rule = 'rule %s%s_LINKER\n' % (langname, crstr)
                command = ' command = %s %s $FLAGS  %s $in $LINK_FLAGS $aliasing\n' % \
                (execute_wrapper,
                 ' '.join(compiler.get_linker_exelist()),\
                 ' '.join(compiler.get_linker_output_flags('$out')))
                description = ' description = Linking target $out'
                outfile.write(rule)
                outfile.write(command)
                outfile.write(description)
                outfile.write('\n')
        scriptdir = self.environment.get_script_dir()
        outfile.write('\n')
        symrule = 'rule SHSYM\n'
        symcmd = ' command = "%s" "%s" "%s" "%s" $CROSS\n' % (ninja_quote(sys.executable),
                                         ninja_quote(os.path.join(scriptdir, 'symbolextractor.py')),
                                         '$in', '$out')
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
        command = ' command = %s $FLAGS $in\n' % invoc
        description = ' description = Compiling Java object $in.\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)
        outfile.write('\n')

    def generate_compile_rule_for(self, langname, compiler, qstr, is_cross, outfile):
        if langname == 'java':
            if not is_cross:
                self.generate_java_compile_rule(compiler, outfile)
            return
        if is_cross:
            crstr = '_CROSS'
        else:
            crstr = ''
        rule = 'rule %s%s_COMPILER\n' % (langname, crstr)
        depflags = compiler.get_dependency_gen_flags('$out', '$DEPFILE')
        command = " command = %s $FLAGS %s %s %s $in\n" % \
            (' '.join(compiler.get_exelist()),\
             ' '.join([qstr % d for d in depflags]),\
             ' '.join(compiler.get_output_flags('$out')),\
             ' '.join(compiler.get_compile_only_flags()))
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
        depflags = compiler.get_dependency_gen_flags('$out', '$DEPFILE')
        if compiler.get_id() == 'msvc':
            output = ''
        else:
            output = ' '.join(compiler.get_output_flags('$out'))
        command = " command = %s $FLAGS %s %s %s $in\n" % \
            (' '.join(compiler.get_exelist()),\
             ' '.join([qstr % d for d in depflags]),\
             output,\
             ' '.join(compiler.get_compile_only_flags()))
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
            for compiler in self.build.cross_compilers:
                langname = compiler.get_language()
                self.generate_compile_rule_for(langname, compiler, qstr, True, outfile)
                self.generate_pch_rule_for(langname, compiler, qstr, True, outfile)
        outfile.write('\n')

    def generate_custom_generator_rules(self, target, outfile):
        for genlist in target.get_generated_sources():
            generator = genlist.get_generator()
            exe = generator.get_exe()
            if self.environment.is_cross_build() and \
            isinstance(exe, build.BuildTarget) and exe.is_cross:
                if 'exe_wrapper'  not in self.environment.cross_info:
                    s = 'Can not use target %s as a generator because it is cross-built\n'
                    s += 'and no exe wrapper is defined. You might want to set it to native instead.'
                    s = s % exe.name
                    raise MesonException(s)
            infilelist = genlist.get_infilelist()
            outfilelist = genlist.get_outfilelist()
            if isinstance(exe, build.BuildTarget):
                exe_file = os.path.join(self.environment.get_build_dir(), self.get_target_filename(exe))
            else:
                exe_file = exe.get_command()
            base_args = generator.get_arglist()
            for i in range(len(infilelist)):
                if len(infilelist) == len(outfilelist):
                    sole_output = os.path.join(self.get_target_private_dir(target), outfilelist[i])
                else:
                    sole_output = ''
                curfile = infilelist[i]
                infilename = os.path.join(self.environment.get_source_dir(), curfile)
                outfiles = genlist.get_outputs_for(curfile)
                outfiles = [os.path.join(self.get_target_private_dir(target), of) for of in outfiles]
                args = [x.replace("@INPUT@", infilename).replace('@OUTPUT@', sole_output)\
                        for x in base_args]
                args = [x.replace("@SOURCE_DIR@", self.environment.get_source_dir()).replace("@BUILD_DIR@", self.get_target_private_dir(target))
                        for x in args]
                cmdlist = [exe_file] + args
                elem = NinjaBuildElement(outfiles, 'CUSTOM_COMMAND', infilename)
                elem.add_item('DESC', 'Generating $out')
                if isinstance(exe, build.BuildTarget):
                    elem.add_dep(self.get_target_filename(exe))
                elem.add_item('COMMAND', cmdlist)
                elem.write(outfile)

    def generate_single_compile(self, target, outfile, src, is_generated=False, header_deps=[]):
        compiler = self.get_compiler_for_source(src)
        commands = self.generate_basic_compiler_flags(target, compiler)
        commands.append(compiler.get_include_arg(self.get_target_private_dir(target)))
        if is_generated:
            if '/' in src:
                rel_src = src
            else:
                rel_src = os.path.join(self.get_target_private_dir(target), src)
        else:
            rel_src = os.path.join(self.build_to_src, target.get_source_subdir(), src)
        if os.path.isabs(src):
            src_filename = os.path.basename(src)
        else:
            src_filename = src
        obj_basename = src_filename.replace('/', '_').replace('\\', '_')
        rel_obj = os.path.join(self.get_target_private_dir(target), obj_basename)
        rel_obj += '.' + self.environment.get_object_suffix()
        dep_file = rel_obj + '.' + compiler.get_depfile_suffix()
        if self.environment.coredata.use_pch:
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
        for i in target.get_include_dirs():
            basedir = i.get_curdir()
            for d in i.get_incdirs():
                expdir =  os.path.join(basedir, d)
                fulldir = os.path.join(self.environment.get_source_dir(), expdir)
                barg = compiler.get_include_arg(expdir)
                sarg = compiler.get_include_arg(fulldir)
                commands.append(barg)
                commands.append(sarg)
        if self.environment.coredata.use_pch:
            commands += self.get_pch_include_args(compiler, target)
        crstr = ''
        if target.is_cross:
            crstr = '_CROSS'
        compiler_name = '%s%s_COMPILER' % (compiler.get_language(), crstr)

        element = NinjaBuildElement(rel_obj, compiler_name, rel_src)
        for d in header_deps:
            if not '/' in d:
                d = os.path.join(self.get_target_private_dir(target), d)
            element.add_dep(d)
        element.add_orderdep(pch_dep)
        element.add_item('DEPFILE', dep_file)
        element.add_item('FLAGS', commands)
        element.write(outfile)
        return rel_obj

    def generate_msvc_pch_command(self, target, compiler, pch):
        if len(pch) != 2:
            raise RuntimeError('MSVC requires one header and one source to produce precompiled headers.')
        header = pch[0]
        source = pch[1]
        pchname = compiler.get_pch_name(header)
        dst = os.path.join(self.get_target_private_dir(target), pchname)

        commands = []
        commands += self.generate_basic_compiler_flags(target, compiler)
        just_name = os.path.split(header)[1]
        commands += compiler.gen_pch_args(just_name, source, dst)
        
        dep = dst + '.' + compiler.get_depfile_suffix()
        return (commands, dep, dst)

    def generate_gcc_pch_command(self, target, compiler, pch):
        commands = []
        commands += self.generate_basic_compiler_flags(target, compiler)
        dst = os.path.join(self.get_target_private_dir(target),
                           os.path.split(pch)[-1] + '.' + compiler.get_pch_suffix())
        dep = dst + '.' + compiler.get_depfile_suffix()
        return (commands, dep, dst)

    def generate_pch(self, target, outfile):
        cstr = ''
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
                (commands, dep, dst) = self.generate_msvc_pch_command(target, compiler, pch)
                extradep = os.path.join(self.build_to_src, target.get_source_subdir(), pch[0])
            else:
                src = os.path.join(self.build_to_src, target.get_source_subdir(), pch[0])
                (commands, dep, dst) = self.generate_gcc_pch_command(target, compiler, pch[0])
                extradep = None
            rulename = compiler.get_language() + cstr + '_PCH'
            elem = NinjaBuildElement(dst, rulename, src)
            if extradep is not None:
                elem.add_dep(extradep)
            elem.add_item('FLAGS', commands)
            elem.add_item('DEPFILE', dep)
            elem.write(outfile)

    def generate_shsym(self, outfile, target):
        target_name = self.get_target_filename(target)
        targetdir = self.get_target_private_dir(target)
        symname = os.path.join(targetdir, target_name + '.symbols')
        elem = NinjaBuildElement(symname, 'SHSYM', target_name)
        if self.environment.is_cross_build():
            elem.add_item('CROSS', '--cross-host=' + self.environment.cross_info['name'])
        elem.write(outfile)

    def generate_link(self, target, outfile, outname, obj_list, linker):
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
        commands += linker.get_linker_always_flags()
        if isinstance(target, build.Executable):
            commands += linker.get_std_exe_link_flags()
        elif isinstance(target, build.SharedLibrary):
            commands += linker.get_std_shared_lib_link_flags()
            commands += linker.get_pic_flags()
            commands += linker.get_soname_flags(target.name, abspath)
        elif isinstance(target, build.StaticLibrary):
            commands += linker.get_std_link_flags()
        else:
            raise RuntimeError('Unknown build target type.')
        for dep in target.get_external_deps():
            commands += dep.get_link_flags()
        dependencies = target.get_dependencies()
        commands += self.build_target_link_arguments(linker, dependencies)
        commands += target.link_flags
        commands += linker.build_rpath_args(self.environment.get_build_dir(), target.get_rpaths())
        if self.environment.coredata.coverage:
            commands += linker.get_coverage_link_flags()
        dep_targets = [self.get_dependency_filename(t) for t in dependencies]
        dep_targets += [os.path.join(self.environment.source_dir,
                                     target.subdir, t) for t in target.link_depends]
        elem = NinjaBuildElement(outname, linker_rule, obj_list)
        elem.add_dep(dep_targets)
        elem.add_item('LINK_FLAGS', commands)
        return elem

    def get_dependency_filename(self, t):
        if isinstance(t, build.SharedLibrary):
            return os.path.join(self.get_target_private_dir(t), self.get_target_filename(t) + '.symbols')
        return self.get_target_filename(t)

    def generate_shlib_aliases(self, target, outdir, outfile, elem):
        basename = target.get_filename()
        aliases = target.get_aliaslist()
        aliascmd = []
        if shutil.which('ln'):
            for alias in aliases:
                aliasfile = os.path.join(outdir, alias)
                cmd = ["&&", 'ln', '-s', '-f', basename, aliasfile]
                aliascmd += cmd
        else:
            mlog.log("Library versioning disabled because host does not support symlinks.")
        elem.add_item('aliasing', aliascmd)
        elem.write(outfile)

    def generate_gcov_clean(self, outfile):
            gcno_elem = NinjaBuildElement('clean-gcno', 'CUSTOM_COMMAND', '')
            script_root = self.environment.get_script_dir()
            clean_script = os.path.join(script_root, 'delwithsuffix.py')
            gcno_elem.add_item('COMMAND', [sys.executable, clean_script, '.', 'gcno'])
            gcno_elem.add_item('description', 'Deleting gcno files')
            gcno_elem.write(outfile)

            gcda_elem = NinjaBuildElement('clean-gcda', 'CUSTOM_COMMAND', '')
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
                rule = rule.name
                elem = NinjaBuildElement(outfilename, rule, infilename)
                elem.write(outfile)
                if self.is_compilable_file(outfilename):
                    src_deps.append(outfilename)
                else:
                    other_deps.append(outfilename)
        return (src_deps, other_deps)

    def generate_cppcheck_target(self, outfile):
        cppcheck_exe = environment.find_cppcheck()
        if not cppcheck_exe:
            return
        elem = NinjaBuildElement('cppcheck', 'CUSTOM_COMMAND', [])
        elem.add_item('COMMAND', [cppcheck_exe, self.environment.get_source_dir()])
        elem.add_item('description', 'Running cppchecker')
        elem.write(outfile)

    def generate_ending(self, outfile):
        targetlist = [self.get_target_filename(t) for t in self.build.get_targets().values()]
        elem = NinjaBuildElement('all', 'phony', targetlist)
        elem.write(outfile)

        default = 'default all\n\n'
        outfile.write(default)

        ninja_command = environment.detect_ninja()
        if ninja_command is None:
            raise RuntimeError('Could not detect ninja command')
        elem = NinjaBuildElement('clean', 'CUSTOM_COMMAND', '')
        elem.add_item('COMMAND', [ninja_command, '-t', 'clean'])
        elem.add_item('description', 'Cleaning')
        if self.environment.coredata.coverage:
            self.generate_gcov_clean(outfile)
            elem.add_dep('clean-gcda')
            elem.add_dep('clean-gcno')
        elem.write(outfile)

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
        elem = NinjaBuildElement('build.ninja', 'REGENERATE_BUILD', deps)
        elem.write(outfile)

        elem = NinjaBuildElement(deps, 'phony', '')
        elem.write(outfile)

        self.generate_cppcheck_target(outfile)

import xml.etree.ElementTree as ET
import xml.dom.minidom

class Vs2010Backend(Backend):
    def __init__(self, build, interp):
        super().__init__(build, interp)
        self.project_file_version = '10.0.30319.1'
        # foo.c compiles to foo.obj, not foo.c.obj
        self.source_suffix_in_obj = False

    def generate_custom_generator_commands(self, target, parent_node):
        idgroup = ET.SubElement(parent_node, 'ItemDefinitionGroup')
        all_output_files = []
        for genlist in target.get_generated_sources():
            generator = genlist.get_generator()
            exe = generator.get_exe()
            infilelist = genlist.get_infilelist()
            outfilelist = genlist.get_outfilelist()
            if isinstance(exe, build.BuildTarget):
                exe_file = os.path.join(self.environment.get_build_dir(), self.get_target_filename(exe))
            else:
                exe_file = exe.get_command()
            base_args = generator.get_arglist()
            for i in range(len(infilelist)):
                if len(infilelist) == len(outfilelist):
                    sole_output = os.path.join(self.get_target_private_dir(target), outfilelist[i])
                else:
                    sole_output = ''
                curfile = infilelist[i]
                infilename = os.path.join(self.environment.get_source_dir(), curfile)
                outfiles = genlist.get_outputs_for(curfile)
                outfiles = [os.path.join(self.get_target_private_dir(target), of) for of in outfiles]
                all_output_files += outfiles
                args = [x.replace("@INPUT@", infilename).replace('@OUTPUT@', sole_output)\
                        for x in base_args]
                args = [x.replace("@SOURCE_DIR@", self.environment.get_source_dir()).replace("@BUILD_DIR@", self.get_target_private_dir(target))
                        for x in args]
                fullcmd = [exe_file] + args
                cbs = ET.SubElement(idgroup, 'CustomBuildStep')
                ET.SubElement(cbs, 'Command').text = ' '.join(self.special_quote(fullcmd))
                ET.SubElement(cbs, 'Inputs').text = infilename
                ET.SubElement(cbs, 'Outputs').text = ';'.join(outfiles)
                ET.SubElement(cbs, 'Message').text = 'Generating sources from %s.' % infilename
        pg = ET.SubElement(parent_node, 'PropertyGroup')
        ET.SubElement(pg, 'CustomBuildBeforeTargets').text = 'ClCompile'
        return all_output_files

    def generate(self):
        self.generate_configure_files()
        self.generate_pkgconfig_files()
        sln_filename = os.path.join(self.environment.get_build_dir(), self.build.project_name + '.sln')
        projlist = self.generate_projects()
        self.gen_testproj('RUN_TESTS', os.path.join(self.environment.get_build_dir(), 'RUN_TESTS.vcxproj'))
        self.generate_solution(sln_filename, projlist)

    def get_obj_target_deps(self, obj_list):
        result = {}
        for o in obj_list:
            if isinstance(o, build.ExtractedObjects):
                result[o.target.get_basename()] = True
        return result.keys()

    def generate_solution(self, sln_filename, projlist):
        ofile = open(sln_filename, 'w')
        ofile.write('Microsoft Visual Studio Solution File, Format Version 11.00\n')
        ofile.write('# Visual Studio 2010\n')
        prj_templ = prj_line = 'Project("{%s}") = "%s", "%s", "{%s}"\n'
        for p in projlist:
            prj_line = prj_templ % (self.environment.coredata.guid, p[0], p[1], p[2])
            ofile.write(prj_line)
            all_deps = {}
            for ldep in self.build.targets[p[0]].link_targets:
                all_deps[ldep.get_basename()] = True
            for objdep in self.get_obj_target_deps(self.build.targets[p[0]].objects):
                all_deps[objdep] = True
            for gendep in self.build.targets[p[0]].generated:
                gen_exe = gendep.generator.get_exe()
                if isinstance(gen_exe, build.Executable):
                    all_deps[gen_exe.get_basename()] = True
            if len(all_deps) > 0:
                ofile.write('\tProjectSection(ProjectDependencies) = postProject\n')
                for dep in all_deps.keys():
                    guid = self.environment.coredata.target_guids[dep]
                    ofile.write('\t\t{%s} = {%s}\n' % (guid, guid))
                ofile.write('EndProjectSection\n')
            ofile.write('EndProject\n')
        test_line = prj_templ % (self.environment.coredata.guid,
                                 'RUN_TESTS', 'RUN_TESTS.vcxproj', self.environment.coredata.test_guid)
        ofile.write(test_line)
        ofile.write('EndProject\n')
        ofile.write('Global\n')
        ofile.write('\tGlobalSection(SolutionConfigurationPlatforms) = preSolution\n')
        ofile.write('\t\tDebug|Win32 = Debug|Win32\n')
        ofile.write('\tEndGlobalSection\n')
        ofile.write('\tGlobalSection(ProjectConfigurationPlatforms) = postSolution\n')
        for p in projlist:
            ofile.write('\t\t{%s}.Debug|Win32.ActiveCfg = Debug|Win32\n' % p[2])
            ofile.write('\t\t{%s}.Debug|Win32.Build.0 = Debug|Win32\n' % p[2])
        ofile.write('\t\t{%s}.Debug|Win32.ActiveCfg = Debug|Win32\n' % self.environment.coredata.test_guid)
        ofile.write('\tEndGlobalSection\n')
        ofile.write('\tGlobalSection(SolutionProperties) = preSolution\n')
        ofile.write('\t\tHideSolutionNode = FALSE\n')
        ofile.write('\tEndGlobalSection\n')
        ofile.write('EndGlobal\n')

    def generate_projects(self):
        projlist = []
        for name, target in self.build.targets.items():
            outdir = os.path.join(self.environment.get_build_dir(), target.subdir)
            fname = name + '.vcxproj'
            relname = os.path.join(target.subdir, fname)
            projfile = os.path.join(outdir, fname)
            uuid = self.environment.coredata.target_guids[name]
            self.gen_vcxproj(target, projfile, uuid)
            projlist.append((name, relname, uuid))
        return projlist

    def split_sources(self, srclist):
        sources = []
        headers = []
        for i in srclist:
            if self.environment.is_header(i):
                headers.append(i)
            else:
                sources.append(i)
        return (sources, headers)

    def target_to_build_root(self, target):
        if target.subdir == '':
            return ''
        return '/'.join(['..']*(len(os.path.split(target.subdir))-1))

    def special_quote(self, arr):
        return ['&quot;%s&quot;' % i for i in arr]

    def gen_vcxproj(self, target, ofname, guid):
        down = self.target_to_build_root(target)
        proj_to_src_root = os.path.join(down, self.build_to_src)
        proj_to_src_dir = os.path.join(proj_to_src_root, target.subdir)
        (sources, headers) = self.split_sources(target.sources)
        entrypoint = 'WinMainCRTStartup'
        buildtype = 'Debug'
        platform = "Win32"
        project_name = target.name
        target_name = target.name
        subsystem = 'Windows'
        if isinstance(target, build.Executable):
            conftype = 'Application'
            if not target.gui_app:
                subsystem = 'Console'
                entrypoint = 'mainCRTStartup'
        elif isinstance(target, build.StaticLibrary):
            conftype = 'StaticLibrary'
        elif isinstance(target, build.SharedLibrary):
            conftype = 'DynamicLibrary'
            entrypoint = '_DllMainCrtStartup'
        else:
            raise MesonException('Unknown target type for %s' % target_name)
        root = ET.Element('Project', {'DefaultTargets' : "Build",
                        'ToolsVersion' : '4.0',
                         'xmlns' : 'http://schemas.microsoft.com/developer/msbuild/2003'})
        confitems = ET.SubElement(root, 'ItemGroup', {'Label' : 'ProjectConfigurations'})
        prjconf = ET.SubElement(confitems, 'ProjectConfiguration', {'Include' : 'Debug|Win32'})
        p = ET.SubElement(prjconf, 'Configuration')
        p.text= buildtype
        pl = ET.SubElement(prjconf, 'Platform')
        pl.text = platform
        globalgroup = ET.SubElement(root, 'PropertyGroup', Label='Globals')
        guidelem = ET.SubElement(globalgroup, 'ProjectGuid')
        guidelem.text = guid
        kw = ET.SubElement(globalgroup, 'Keyword')
        kw.text = 'Win32Proj'
        ns = ET.SubElement(globalgroup, 'RootNamespace')
        ns.text = target_name
        p = ET.SubElement(globalgroup, 'Platform')
        p.text= platform
        pname= ET.SubElement(globalgroup, 'ProjectName')
        pname.text = project_name
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.Default.props')
        type_config = ET.SubElement(root, 'PropertyGroup', Label='Configuration')
        ET.SubElement(type_config, 'ConfigurationType').text = conftype
        ET.SubElement(type_config, 'CharacterSet').text = 'MultiByte'
        ET.SubElement(type_config, 'WholeProgramOptimization').text = 'false'
        ET.SubElement(type_config, 'UseDebugLibraries').text = 'true'
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.props')
        generated_files = self.generate_custom_generator_commands(target, root)
        (gen_src, gen_hdrs) = self.split_sources(generated_files)
        direlem = ET.SubElement(root, 'PropertyGroup')
        fver = ET.SubElement(direlem, '_ProjectFileVersion')
        fver.text = self.project_file_version
        outdir = ET.SubElement(direlem, 'OutDir')
        outdir.text = '.\\'
        intdir = ET.SubElement(direlem, 'IntDir')
        intdir.text = os.path.join(self.get_target_dir(target), target.get_basename() + '.dir') + '\\'
        tname = ET.SubElement(direlem, 'TargetName')
        tname.text = target_name
        inclinc = ET.SubElement(direlem, 'LinkIncremental')
        inclinc.text = 'true'

        compiles = ET.SubElement(root, 'ItemDefinitionGroup')
        clconf = ET.SubElement(compiles, 'ClCompile')
        opt = ET.SubElement(clconf, 'Optimization')
        opt.text = 'disabled'
        inc_dirs = [proj_to_src_dir, self.get_target_private_dir(target)]
        extra_args = []
        # SUCKS, VS can not handle per-language type flags, so just use
        # them all.
        for l in self.build.global_args.values():
            for a in l:
                extra_args.append(a)
        for l in target.extra_args.values():
            for a in l:
                extra_args.append(a)
        if len(extra_args) > 0:
            extra_args.append('%(AdditionalOptions)')
            ET.SubElement(clconf, "AdditionalOptions").text = ' '.join(extra_args)
        for d in target.include_dirs:
            for i in d.incdirs:
                curdir = os.path.join(d.curdir, i)
                inc_dirs.append(self.relpath(curdir, target.subdir)) # build dir
                inc_dirs.append(os.path.join(proj_to_src_root, curdir)) # src dir
        inc_dirs.append('%(AdditionalIncludeDirectories)')
        ET.SubElement(clconf, 'AdditionalIncludeDirectories').text = ';'.join(inc_dirs)
        preproc = ET.SubElement(clconf, 'PreprocessorDefinitions')
        rebuild = ET.SubElement(clconf, 'MinimalRebuild')
        rebuild.text = 'true'
        rtlib = ET.SubElement(clconf, 'RuntimeLibrary')
        rtlib.text = 'MultiThreadedDebugDLL'
        funclink = ET.SubElement(clconf, 'FunctionLevelLinking')
        funclink.text = 'true'
        pch = ET.SubElement(clconf, 'PrecompiledHeader')
        warnings = ET.SubElement(clconf, 'WarningLevel')
        warnings.text = 'Level3'
        debinfo = ET.SubElement(clconf, 'DebugInformationFormat')
        debinfo.text = 'EditAndContinue'
        resourcecompile = ET.SubElement(compiles, 'ResourceCompile')
        ET.SubElement(resourcecompile, 'PreprocessorDefinitions')
        link = ET.SubElement(compiles, 'Link')
        additional_links = []
        for t in target.link_targets:
            lobj = self.build.targets[t.get_basename()]
            rel_path = self.relpath(lobj.subdir, target.subdir)
            linkname = os.path.join(rel_path, lobj.get_import_filename())
            additional_links.append(linkname)
        for o in self.flatten_object_list(target, down):
            assert(isinstance(o, str))
            additional_links.append(o)
        if len(additional_links) > 0:
            additional_links.append('%(AdditionalDependencies)')
            ET.SubElement(link, 'AdditionalDependencies').text = ';'.join(additional_links)
        ofile = ET.SubElement(link, 'OutputFile')
        ofile.text = '$(OutDir)%s' % target.get_filename()
        addlibdir = ET.SubElement(link, 'AdditionalLibraryDirectories')
        addlibdir.text = '%(AdditionalLibraryDirectories)'
        subsys = ET.SubElement(link, 'SubSystem')
        subsys.text = subsystem
        gendeb = ET.SubElement(link, 'GenerateDebugInformation')
        gendeb.text = 'true'
        if isinstance(target, build.SharedLibrary):
            ET.SubElement(link, 'ImportLibrary').text = target.get_import_filename()
        pdb = ET.SubElement(link, 'ProgramDataBaseFileName')
        pdb.text = '$(OutDir}%s.pdb' % target_name
        if isinstance(target, build.Executable):
            ET.SubElement(link, 'EntryPointSymbol').text = entrypoint
        targetmachine = ET.SubElement(link, 'TargetMachine')
        targetmachine.text = 'MachineX86'

        if len(headers) + len(gen_hdrs) > 0:
            inc_hdrs = ET.SubElement(root, 'ItemGroup')
            for h in headers:
                relpath = os.path.join(proj_to_src_dir, h)
                ET.SubElement(inc_hdrs, 'CLInclude', Include=relpath)
            for h in gen_hdrs:
                relpath = self.relpath(h, target.subdir)
                ET.SubElement(inc_hdrs, 'CLInclude', Include = relpath)
        if len(sources) + len(gen_src) > 0:
            inc_src = ET.SubElement(root, 'ItemGroup')
            for s in sources:
                relpath = os.path.join(proj_to_src_dir, s)
                ET.SubElement(inc_src, 'CLCompile', Include=relpath)
            for s in gen_src:
                relpath =  self.relpath(s, target.subdir)
                ET.SubElement(inc_src, 'CLCompile', Include=relpath)
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.targets')
        tree = ET.ElementTree(root)
        tree.write(ofname, encoding='utf-8', xml_declaration=True)
        # ElementTree can not do prettyprinting so do it manually
        doc = xml.dom.minidom.parse(ofname)
        open(ofname, 'w').write(doc.toprettyxml())
        # World of horror! Python insists on not quoting quotes and
        # fixing the escaped &quot; into &amp;quot; whereas MSVS
        # requires quoted but not fixed elements. Enter horrible hack.
        txt = open(ofname, 'r').read()
        open(ofname, 'w').write(txt.replace('&amp;quot;', '&quot;'))

    def gen_testproj(self, target_name, ofname):
        buildtype = 'Debug'
        platform = "Win32"
        project_name = target_name
        root = ET.Element('Project', {'DefaultTargets' : "Build",
                        'ToolsVersion' : '4.0',
                         'xmlns' : 'http://schemas.microsoft.com/developer/msbuild/2003'})
        confitems = ET.SubElement(root, 'ItemGroup', {'Label' : 'ProjectConfigurations'})
        prjconf = ET.SubElement(confitems, 'ProjectConfiguration', {'Include' : 'Debug|Win32'})
        p = ET.SubElement(prjconf, 'Configuration')
        p.text= buildtype
        pl = ET.SubElement(prjconf, 'Platform')
        pl.text = platform
        globalgroup = ET.SubElement(root, 'PropertyGroup', Label='Globals')
        guidelem = ET.SubElement(globalgroup, 'ProjectGuid')
        guidelem.text = self.environment.coredata.test_guid
        kw = ET.SubElement(globalgroup, 'Keyword')
        kw.text = 'Win32Proj'
        p = ET.SubElement(globalgroup, 'Platform')
        p.text= platform
        pname= ET.SubElement(globalgroup, 'ProjectName')
        pname.text = project_name
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.Default.props')
        type_config = ET.SubElement(root, 'PropertyGroup', Label='Configuration')
        ET.SubElement(type_config, 'ConfigurationType')
        ET.SubElement(type_config, 'CharacterSet').text = 'MultiByte'
        ET.SubElement(type_config, 'UseOfMfc').text = 'false'
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.props')
        direlem = ET.SubElement(root, 'PropertyGroup')
        fver = ET.SubElement(direlem, '_ProjectFileVersion')
        fver.text = self.project_file_version
        outdir = ET.SubElement(direlem, 'OutDir')
        outdir.text = '.\\'
        intdir = ET.SubElement(direlem, 'IntDir')
        intdir.text = 'test-temp\\'
        tname = ET.SubElement(direlem, 'TargetName')
        tname.text = target_name

        action = ET.SubElement(root, 'ItemDefinitionGroup')
        midl = ET.SubElement(action, 'Midl')
        ET.SubElement(midl, "AdditionalIncludeDirectories").text = '%(AdditionalIncludeDirectories)'
        ET.SubElement(midl, "OutputDirectory").text = '$(IntDir)'
        ET.SubElement(midl, 'HeaderFileName').text = '%(Filename).h'
        ET.SubElement(midl, 'TypeLibraryName').text = '%(Filename).tlb'
        ET.SubElement(midl, 'InterfaceIdentifierFilename').text = '%(Filename)_i.c'
        ET.SubElement(midl, 'ProxyFileName').text = '%(Filename)_p.c'
        postbuild = ET.SubElement(action, 'PostBuildEvent')
        ET.SubElement(postbuild, 'Message')
        script_root = self.environment.get_script_dir()
        test_script = os.path.join(script_root, 'meson_test.py')
        test_data = os.path.join(self.environment.get_scratch_dir(), 'meson_test_setup.dat')
        cmd_templ = '''setlocal
"%s" "%s" "%s"
if %%errorlevel%% neq 0 goto :cmEnd
:cmEnd
endlocal & call :cmErrorLevel %%errorlevel%% & goto :cmDone
:cmErrorLevel
exit /b %%1
:cmDone
if %%errorlevel%% neq 0 goto :VCEnd'''
        ET.SubElement(postbuild, 'Command').text = cmd_templ % (sys.executable, test_script, test_data)
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.targets')
        tree = ET.ElementTree(root)
        tree.write(ofname, encoding='utf-8', xml_declaration=True)
        datafile = open(test_data, 'wb')
        self.write_test_file(datafile)
        datafile.close()
        # ElementTree can not do prettyprinting so do it manually
        #doc = xml.dom.minidom.parse(ofname)
        #open(ofname, 'w').write(doc.toprettyxml())

class XCodeBackend(Backend):
    def __init__(self, build, interp):
        super().__init__(build, interp)
        self.project_uid = self.environment.coredata.guid.replace('-', '')[:24]
        self.project_conflist = self.gen_id()
        self.indent = '       '
        self.indent_level = 0
        self.xcodetypemap = {'c' : 'sourcecode.c.c', 'a' : 'archive.ar'}
        self.maingroup_id = self.gen_id()
        self.all_id = self.gen_id()
        self.all_buildconf_id = self.gen_id()
        self.buildtypes = ['debug']

    def gen_id(self):
        return str(uuid.uuid4()).upper().replace('-', '')[:24]

    def write_line(self, text):
        self.ofile.write(self.indent*self.indent_level + text)
        if not text.endswith('\n'):
            self.ofile.write('\n')

    def generate(self):
        self.generate_filemap()
        self.generate_buildmap()
        self.generate_buildstylemap()
        self.generate_build_phase_map()
        self.generate_build_configuration_map()
        self.generate_build_configurationlist_map()
        self.generate_project_configurations_map()
        self.generate_buildall_configurations_map()
        self.generate_native_target_map()
        self.generate_source_phase_map()
        self.generate_target_dependency_map()
        self.generate_pbxdep_map()
        self.generate_containerproxy_map()
        self.generate_configure_files()
        self.generate_pkgconfig_files()
        self.proj_dir = os.path.join(self.environment.get_build_dir(), self.build.project_name + '.xcodeproj')
        os.makedirs(self.proj_dir, exist_ok=True)
        self.proj_file = os.path.join(self.proj_dir, 'project.pbxproj')
        self.ofile = open(self.proj_file, 'w')
        self.generate_prefix()
        self.generate_pbx_aggregate_target()
        self.generate_pbx_build_file()
        self.generate_pbx_build_style()
        self.generate_pbx_container_item_proxy()
        self.generate_pbx_file_reference()
        self.generate_pbx_group()
        self.generate_pbx_native_target()
        self.generate_pbx_project()
        self.generate_pbx_shell_build_phase()
        self.generate_pbx_sources_build_phase()
        self.generate_pbx_target_dependency()
        self.generate_xc_build_configuration()
        self.generate_xc_configurationList()
        self.generate_suffix()

    def get_xcodetype(self, fname):
        return self.xcodetypemap[fname.split('.')[-1]]

    def generate_filemap(self):
        self.filemap = {} # Key is source file relative to src root.
        self.target_filemap = {}
        for name, t in self.build.targets.items():
            for s in t.sources:
                if isinstance(s, str):
                    self.filemap[s] = self.gen_id()
            self.target_filemap[name] = self.gen_id()

    def generate_buildmap(self):
        self.buildmap = {}
        for t in self.build.targets.values():
            for s in t.sources:
                if isinstance(s, str):
                    self.buildmap[s] = self.gen_id()

    def generate_buildstylemap(self):
        self.buildstylemap = {'debug' : self.gen_id()}

    def generate_build_phase_map(self):
        self.buildphasemap = {}
        for t in self.build.targets:
            self.buildphasemap[t] = self.gen_id()

    def generate_build_configuration_map(self):
        self.buildconfmap = {}
        for t in self.build.targets:
            bconfs = {'debug' : self.gen_id()}
            self.buildconfmap[t] = bconfs

    def generate_project_configurations_map(self):
        self.project_configurations = {'debug' : self.gen_id()}

    def generate_buildall_configurations_map(self):
        self.buildall_configurations = {'debug' : self.gen_id()}

    def generate_build_configurationlist_map(self):
        self.buildconflistmap = {}
        for t in self.build.targets:
            self.buildconflistmap[t] = self.gen_id()

    def generate_native_target_map(self):
        self.native_targets = {}
        for t in self.build.targets:
            self.native_targets[t] = self.gen_id()

    def generate_target_dependency_map(self):
        self.target_dependency_map = {}
        for tname, t in self.build.targets.items():
            for target in t.link_targets:
                self.target_dependency_map[(tname, target.basename())] = self.gen_id()

    def generate_pbxdep_map(self):
        self.pbx_dep_map = {}
        for t in self.build.targets:
            self.pbx_dep_map[t] = self.gen_id()

    def generate_containerproxy_map(self):
        self.containerproxy_map = {}
        for t in self.build.targets:
            self.containerproxy_map[t] = self.gen_id()

    def generate_source_phase_map(self):
        self.source_phase = {}
        for t in self.build.targets:
            self.source_phase[t] = self.gen_id()

    def generate_pbx_aggregate_target(self):
        self.ofile.write('\n/* Begin PBXAggregateTarget section */\n')
        self.write_line('%s /* ALL_BUILD */ = {' % self.all_id)
        self.indent_level+=1
        self.write_line('isa = PBXAggregateTarget;')
        self.write_line('buildConfigurationList = %s;' % self.all_buildconf_id)
        self.write_line('buildPhases = (')
        self.write_line(');')
        self.write_line('dependencies = (')
        self.indent_level+=1
        for t in self.build.targets:
            self.write_line('%s /* PBXTargetDependency */,' % self.pbx_dep_map[t])
        self.indent_level-=1
        self.write_line(');')
        self.write_line('name = ALL_BUILD;')
        self.write_line('productName = ALL_BUILD;')
        self.indent_level-=1
        self.write_line('};')
        self.ofile.write('/* End PBXAggregateTarget section */\n')

    def generate_pbx_build_file(self):
        self.ofile.write('\n/* Begin PBXBuildFile section */\n')
        templ = '%s /* %s */ = { isa = PBXBuildFile; fileRef = %s /* %s */; settings = { COMPILER_FLAGS = "%s"; }; };\n'
        for t in self.build.targets.values():
            for s in t.sources:
                if isinstance(s, str):
                    idval = self.buildmap[s]
                    fullpath = os.path.join(self.environment.get_source_dir(), s)
                    fileref = self.filemap[s]
                    fullpath2 = fullpath
                    compiler_flags = ''
                    self.ofile.write(templ % (idval, fullpath, fileref, fullpath2, compiler_flags))
        self.ofile.write('/* End PBXBuildFile section */\n')

    def generate_pbx_build_style(self):
        self.ofile.write('\n/* Begin PBXBuildStyle section */\n')
        for name, idval in self.buildstylemap.items():
            self.write_line('%s /* %s */ = {\n' % (idval, name))
            self.indent_level += 1
            self.write_line('isa = PBXBuildStyle;\n')
            self.write_line('buildSettings = {\n')
            self.indent_level += 1
            self.write_line('COPY_PHASE_STRIP = NO;\n')
            self.indent_level -= 1
            self.write_line('};\n')
            self.write_line('name = %s;\n' % name)
            self.indent_level -= 1
            self.write_line('};\n')
        self.ofile.write('/* End PBXBuildStyle section */\n')

    def generate_pbx_container_item_proxy(self):
        self.ofile.write('\n/* Begin PBXContainerItemProxy section */\n')
        for t in self.build.targets:
            self.write_line('%s /* PBXContainerItemProxy */ = {' % self.containerproxy_map[t])
            self.indent_level += 1
            self.write_line('isa = PBXContainerItemProxy;')
            self.write_line('containerPortal = %s /* Project object */;' % self.project_uid)
            self.write_line('proxyType = 1;')
            self.write_line('remoteGlobalIDString = %s;' % self.native_targets[t])
            self.write_line('remoteInfo = %s;' % t)
            self.indent_level-=1
            self.write_line('};')
        self.ofile.write('/* End PBXContainerItemProxy section */\n')

    def generate_pbx_file_reference(self):
        self.ofile.write('\n/* Begin PBXFileReference section */\n')
        src_templ = '%s /* %s */ = { isa = PBXFileReference; explicitFileType = "%s"; fileEncoding = 4; name = "%s"; path = "%s"; sourceTree = SOURCE_ROOT; };\n'
        for fname, idval in self.filemap.items():
            fullpath = os.path.join(self.environment.get_source_dir(), fname)
            xcodetype = self.get_xcodetype(fname)
            name = os.path.split(fname)[-1]
            path = fname
            self.ofile.write(src_templ % (idval, fullpath, xcodetype, name, path))
        target_templ = '%s /* %s */ = { isa = PBXFileReference; explicitFileType = "%s"; path = %s; refType = %d; sourceTree = BUILT_PRODUCTS_DIR; };\n'
        for tname, idval in self.target_filemap.items():
            t = self.build.targets[tname]
            fname = t.get_filename()
            reftype = 0
            if isinstance(t, build.Executable):
                typestr = 'compiled.mach-o.executable'
                path = t.get_filename()
            else:
                typestr = self.get_xcodetype(fname)
                path = '"%s"' % t.get_filename()
            self.ofile.write(target_templ % (idval, tname, typestr, path, reftype))
        self.ofile.write('/* End PBXFileReference section */\n')

    def generate_pbx_group(self):
        groupmap = {}
        target_src_map = {}
        for t in self.build.targets:
            groupmap[t] = self.gen_id()
            target_src_map[t] = self.gen_id()
        self.ofile.write('\n/* Begin PBXGroup section */\n')
        sources_id = self.gen_id()
        resources_id = self.gen_id()
        products_id = self.gen_id()
        self.write_line('%s = {' % self.maingroup_id)
        self.indent_level+=1
        self.write_line('isa = PBXGroup;')
        self.write_line('children = (')
        self.indent_level+=1
        self.write_line('%s /* Sources */,' % sources_id)
        self.write_line('%s /* Resources */,' % resources_id)
        self.write_line('%s /* Products */,' % products_id)
        self.indent_level-=1
        self.write_line(');')
        self.write_line('sourceTree = "<group>";')
        self.indent_level -= 1
        self.write_line('};')

        # Sources
        self.write_line('%s /* Sources */ = {' % sources_id)
        self.indent_level+=1
        self.write_line('isa = PBXGroup;')
        self.write_line('children = (')
        self.indent_level+=1
        for t in self.build.targets:
            self.write_line('%s /* %s */,' % (groupmap[t], t))
        self.indent_level-=1
        self.write_line(');')
        self.write_line('name = Sources;')
        self.write_line('sourcetree = "<group>";')
        self.indent_level-=1
        self.write_line('};')

        self.write_line('%s /* Resources */ = {' % resources_id)
        self.indent_level+=1
        self.write_line('isa = PBXGroup;')
        self.write_line('children = (')
        self.write_line(');')
        self.write_line('name = Resources;')
        self.write_line('sourceTree = "<group>";')
        self.indent_level-=1
        self.write_line('};')

        # Targets
        for t in self.build.targets:
            self.write_line('%s /* %s */ = {' % (groupmap[t], t))
            self.indent_level+=1
            self.write_line('isa = PBXGroup;')
            self.write_line('children = (')
            self.indent_level+=1
            self.write_line('%s /* Source files */,' % target_src_map[t])
            self.indent_level-=1
            self.write_line(');')
            self.write_line('name = %s;' % t)
            self.write_line('sourceTree = "<group>";')
            self.indent_level-=1
            self.write_line('};')
            self.write_line('%s /* Source files */ = {' % target_src_map[t])
            self.indent_level+=1
            self.write_line('isa = PBXGroup;')
            self.write_line('children = (')
            self.indent_level+=1
            for s in self.build.targets[t].sources:
                if isinstance(s, str):
                    self.write_line('%s /* %s */,' % (self.filemap[s], s))
            self.indent_level-=1
            self.write_line(');')
            self.write_line('name = "Source files";')
            self.write_line('sourceTree = "<group>";')
            self.indent_level-=1
            self.write_line('};')

        # And finally products
        self.write_line('%s /* Products */ = {' % products_id)
        self.indent_level+=1
        self.write_line('isa = PBXGroup;')
        self.write_line('children = (')
        self.indent_level+=1
        for t in self.build.targets:
            self.write_line('%s /* %s */,' % (self.target_filemap[t], t))
        self.indent_level-=1
        self.write_line(');')
        self.write_line('name = Products;')
        self.write_line('sourceTree = "<group>";')
        self.indent_level-=1
        self.write_line('};')
        self.ofile.write('/* End PBXGroup section */\n')

    def generate_pbx_native_target(self):
        self.ofile.write('\n/* Begin PBXNativeTarget section */\n')
        for tname, idval in self.native_targets.items():
            t = self.build.targets[tname]
            self.write_line('%s /* %s */ = {' % (idval, tname))
            self.indent_level+=1
            self.write_line('isa = PBXNativeTarget;')
            self.write_line('buildConfigurationList = %s /* Build configuration list for PBXNativeTarget "%s" */;'\
                            % (self.buildconflistmap[tname], tname))
            self.write_line('buildPhases = (')
            self.indent_level+=1
            self.write_line('%s /* Sources */,' % self.buildphasemap[tname])
            self.indent_level-=1
            self.write_line(');')
            self.write_line('buildRules = (')
            self.write_line(');')
            self.write_line('dependencies = (')
            self.indent_level+=1
            for t in self.build.targets[tname].link_targets:
                idval = self.target_dependency_map[(tname, idval.basename())]
                self.write_line('%s /* PBXTargetDependency */')
            self.indent_level -=1
            self.write_line(");")
            self.write_line('name = %s;' % tname)
            self.write_line('productName = %s;' % tname)
            self.write_line('productReference = %s /* %s */;' % (self.target_filemap[tname], tname))
            if isinstance(t, build.Executable):
                typestr = 'com.apple.product-type.tool'
            elif isinstance(t, build.StaticLibrary):
                typestr = 'com.apple.product-type.library.static'
            elif isinstance(t, build.SharedLibrary):
                typestr = 'com.apple.product-type.library.dynamic'
            else:
                raise MesonException('Unknown target type for %s' % tname)
            self.write_line('productType = "%s";' % typestr)
            self.indent_level-=1
            self.write_line('};')
        self.ofile.write('/* End PBXNativeTarget section */\n')

    def generate_pbx_project(self):
        self.ofile.write('\n/* Begin PBXProject section */\n')
        self.write_line('%s /* Project object */ = {' % self.project_uid)
        self.indent_level += 1
        self.write_line('isa = PBXProject;')
        self.write_line('attributes = {')
        self.indent_level += 1
        self.write_line('BuildIndependentTargetsInParallel = YES;')
        self.indent_level -= 1
        self.write_line('};')
        conftempl = 'buildConfigurationList = %s /* build configuration list for PBXProject "%s"*/;'
        self.write_line(conftempl % (self.project_conflist, self.build.project_name))
        self.write_line('buildSettings = {')
        self.write_line('};')
        self.write_line('buildStyles = (')
        self.indent_level += 1
        for name, idval in self.buildstylemap.items():
            self.write_line('%s /* %s */,' % (idval, name))
        self.indent_level -= 1
        self.write_line(');')
        self.write_line('compatibilityVersion = "Xcode 3.2";')
        self.write_line('hasScannedForEncodings = 0;')
        self.write_line('mainGroup = %s;' % self.maingroup_id)
        self.write_line('projectDirPath = "%s";' % self.build_to_src)
        self.write_line('projectRoot = "";')
        self.write_line('targets = (')
        self.indent_level += 1
        self.write_line('%s /* ALL_BUILD */,' % self.all_id)
        for t in self.build.targets:
            self.write_line('%s /* %s */,' % (self.native_targets[t], t))
        self.indent_level -= 1
        self.write_line(');')
        self.indent_level -= 1
        self.write_line('};')
        self.ofile.write('/* End PBXProject section */\n')

    def generate_pbx_shell_build_phase(self):
        self.ofile.write('\n/* Begin PBXShellScriptBuildPhase section */\n')
        self.ofile.write('/* End PBXShellScriptBuildPhase section */\n')

    def generate_pbx_sources_build_phase(self):
        self.ofile.write('\n/* Begin PBXSourcesBuildPhase section */\n')
        for name, phase_id in self.source_phase.items():
            self.write_line('%s /* Sources */ = {' % self.buildphasemap[name])
            self.indent_level+=1
            self.write_line('isa = PBXSourcesBuildPhase;')
            self.write_line('buildActionMask = 2147483647;')
            self.write_line('files = (')
            self.indent_level+=1
            for s in self.build.targets[name].sources:
                if not self.environment.is_header(s):
                    self.write_line('%s /* %s */,' % (self.buildmap[s], os.path.join(self.environment.get_source_dir(), s)))
            self.indent_level-=1
            self.write_line(');')
            self.write_line('runOnlyForDeploymentPostprocessing = 0;')
            self.indent_level-=1
            self.write_line('};')
        self.ofile.write('/* End PBXSourcesBuildPhase section */\n')

    def generate_pbx_target_dependency(self):
        self.ofile.write('\n/* Begin PBXTargetDependency section */\n')
        for t in self.build.targets:
            idval = self.pbx_dep_map[t] # VERIFY: is this correct?
            self.write_line('%s /* PBXTargetDependency */ = {' % idval)
            self.indent_level += 1
            self.write_line('isa = PBXTargetDependency;')
            self.write_line('target = %s /* %s */;' % (self.native_targets[t], t))
            self.write_line('targetProxy = %s /* PBXContainerItemProxy */;' % self.containerproxy_map[t])
            self.indent_level-=1
            self.write_line('};')
        self.ofile.write('/* End PBXTargetDependency section */\n')

    def generate_xc_build_configuration(self):
        self.ofile.write('\n/* Begin XCBuildConfiguration section */\n')
        # First the setup for the toplevel project.
        for buildtype in self.buildtypes:
            self.write_line('%s /* %s */ = {' % (self.project_configurations[buildtype], buildtype))
            self.indent_level+=1
            self.write_line('isa = XCBuildConfiguration;')
            self.write_line('buildSettings = {')
            self.indent_level+=1
            self.write_line('ARCHS = "$(ARCHS_STANDARD_32_64_BIT)";')
            self.write_line('ONLY_ACTIVE_ARCH = YES;')
            self.write_line('SDKROOT = "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.9.sdk";')
            self.write_line('SYMROOT = "%s/build";' % self.environment.get_build_dir())
            self.indent_level-=1
            self.write_line('};')
            self.write_line('name = %s;' % buildtype)
            self.indent_level-=1
            self.write_line('};')

        # Then the all target.
        for buildtype in self.buildtypes:
            self.write_line('%s /* %s */ = {' % (self.buildall_configurations[buildtype], buildtype))
            self.indent_level+=1
            self.write_line('isa = XCBuildConfiguration;')
            self.write_line('buildSettings = {')
            self.indent_level += 1
            self.write_line('COMBINE_HIDPI_IMAGES = YES;')
            self.write_line('GCC_GENERATE_DEBUGGING_SYMBOLS = NO;')
            self.write_line('GCC_INLINES_ARE_PRIVATE_EXTERN = NO;')
            self.write_line('GCC_OPTIMIZATION_LEVEL = 0;')
            self.write_line('GCC_PREPROCESSOR_DEFINITIONS = ("");')
            self.write_line('GCC_SYMBOLS_PRIVATE_EXTERN = NO;')
            self.write_line('INSTALL_PATH = "";')
            self.write_line('OTHER_CFLAGS = "  ";')
            self.write_line('OTHER_LDFLAGS = " ";')
            self.write_line('OTHER_REZFLAGS = "";')
            self.write_line('PRODUCT_NAME = ALL_BUILD;')
            self.write_line('SECTORDER_FLAGS = "";')
            self.write_line('SYMROOT = "%s";' % self.environment.get_build_dir())
            self.write_line('USE_HEADERMAP = NO;')
            self.write_line('WARNING_CFLAGS = ("-Wmost", "-Wno-four-char-constants", "-Wno-unknown-pragmas", );')
            self.indent_level-=1
            self.write_line('};')
            self.write_line('name = %s;' % buildtype)
            self.indent_level-=1
            self.write_line('};')

        # Now finally targets.
        for target_name, target in self.build.targets.items():
            for buildtype in self.buildtypes:
                valid = self.buildconfmap[target_name][buildtype]
                self.write_line('%s /* %s */ = {' % (valid, buildtype))
                self.indent_level+=1
                self.write_line('isa = XCBuildConfiguration;')
                self.write_line('buildSettings = {')
                self.indent_level += 1
                self.write_line('COMBINE_HIDPI_IMAGES = YES;')
                self.write_line('EXECUTABLE_PREFIX = "%s";' % target.prefix)
                self.write_line('EXECUTABLE_SUFFIX = "%s";' % target.suffix)
                self.write_line('GCC_GENERATE_DEBUGGING_SYMBOLS = NO;')
                self.write_line('GCC_INLINES_ARE_PRIVATE_EXTERN = NO;')
                self.write_line('GCC_OPTIMIZATION_LEVEL = 0;')
                self.write_line('GCC_PREPROCESSOR_DEFINITIONS = ("");')
                self.write_line('GCC_SYMBOLS_PRIVATE_EXTERN = NO;')
                self.write_line('INSTALL_PATH = "";')
                self.write_line('LIBRARY_SEARCH_PATHS = "";')
                self.write_line('OTHER_CFLAGS = "  ";')
                self.write_line('OTHER_LDFLAGS = " ";')
                self.write_line('OTHER_REZFLAGS = "";')
                self.write_line('PRODUCT_NAME = %s;' % target_name)
                self.write_line('SECTORDER_FLAGS = "";')
                self.write_line('SYMROOT = "%s";' % self.environment.get_build_dir())
                self.write_line('USE_HEADERMAP = NO;')
                self.write_line('WARNING_CFLAGS = ("-Wmost", "-Wno-four-char-constants", "-Wno-unknown-pragmas", );')
                self.indent_level-=1
                self.write_line('};')
                self.write_line('name = %s;' % buildtype)
                self.indent_level-=1
                self.write_line('};')
        self.ofile.write('/* End XCBuildConfiguration section */\n')

    def generate_xc_configurationList(self):
        self.ofile.write('\n/* Begin XCConfigurationList section */\n')
        self.write_line('%s /* Build configuration list for PBXProject "%s" */ = {' % (self.project_conflist, self.build.project_name))
        self.indent_level+=1
        self.write_line('isa = XCConfigurationList;')
        self.write_line('buildConfigurations = (')
        self.indent_level+=1
        for buildtype in self.buildtypes:
            self.write_line('%s /* %s */,' % (self.project_configurations[buildtype], buildtype))
        self.indent_level-=1
        self.write_line(');')
        self.write_line('defaultConfigurationIsVisible = 0;')
        self.write_line('defaultConfigurationName = debug;')
        self.indent_level-=1
        self.write_line('};')

        # Now the all target
        self.write_line('%s /* Build configuration list for PBXAggregateTarget "ALL_BUILD" */ = {' % self.all_buildconf_id)
        self.indent_level+=1
        self.write_line('isa = XCConfigurationList;')
        self.write_line('buildConfigurations = (')
        self.indent_level+=1
        for buildtype in self.buildtypes:
            self.write_line('%s /* %s */,' % (self.buildall_configurations[buildtype], buildtype))
        self.indent_level-=1
        self.write_line(');')
        self.write_line('defaultConfigurationIsVisible = 0;')
        self.write_line('defaultConfigurationName = debug;')
        self.indent_level-=1
        self.write_line('};')

        for target_name in self.build.targets:
            listid = self.buildconflistmap[target_name]
            self.write_line('%s /* Build configuration list for PBXNativeTarget "%s" */ = {' % (listid, target_name))
            self.indent_level += 1
            self.write_line('isa = XCConfigurationList;')
            self.write_line('buildConfigurations = (')
            self.indent_level += 1
            typestr = 'debug'
            idval = self.buildconfmap[target_name][typestr]
            self.write_line('%s /* %s */,' % (idval, typestr))
            self.indent_level -= 1
            self.write_line(');')
            self.write_line('defaultConfigurationIsVisible = 0;')
            self.write_line('defaultConfigurationName = %s;' % typestr)
            self.indent_level -= 1
            self.write_line('};')
        self.ofile.write('/* End XCConfigurationList section */\n')

    def generate_prefix(self):
        self.ofile.write('// !$*UTF8*$!\n{\n')
        self.indent_level += 1
        self.write_line('archiveVersion = 1;\n')
        self.write_line('classes = {\n')
        self.write_line('};\n')
        self.write_line('objectVersion = 46;\n')
        self.write_line('objects = {\n')
        self.indent_level += 1

    def generate_suffix(self):
        self.indent_level -= 1
        self.write_line('};\n')
        self.write_line('rootObject = ' + self.project_uid + ';')
        self.indent_level -= 1
        self.write_line('}\n')

