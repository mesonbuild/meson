#!/usr/bin/python3 -tt

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

import os, sys, re, pickle
import interpreter, nodes
import environment
from meson_install import InstallData

if environment.is_windows():
    quote_char = '"'
    execute_wrapper = 'cmd /c'
else:
    quote_char = "'"
    execute_wrapper = ''

def ninja_quote(text):
    return text.replace(' ', '$ ')

def do_replacement(regex, line, variables):
    match = re.search(regex, line)
    while match:
        varname = match.group(1)
        if varname in variables:
            var = variables[varname]
            if isinstance(var, str):
                pass
            elif isinstance(var, nodes.StringStatement):
                var = var.get_value()
            else:
                raise RuntimeError('Tried to replace a variable with something other than a string.')
        else:
            var = ''
        line = line.replace('@' + varname + '@', var)
        match = re.search(regex, line)
    return line

def do_mesondefine(line, variables):
    arr = line.split()
    if len(arr) != 2:
        raise interpreter.InvalidArguments('#mesondefine does not contain exactly two tokens.')
    varname = arr[1]
    v = variables.get(varname, False)
    if isinstance(v, bool):
        value= v
    elif isinstance(v, nodes.BoolStatement):
        value = v.get_value()
    else:
        raise interpreter.InvalidArguments('#mesondefine argument "%s" is not boolean.' % varname)
    if value:
        return '#define %s\n' % varname
    return '/* undef %s */\n' % varname

def do_conf_file(src, dst, variables):
    data = open(src).readlines()
    regex = re.compile('@(.*?)@')
    result = []
    for line in data:
        if line.startswith('#mesondefine'):
            line = do_mesondefine(line, variables)
        else:
            line = do_replacement(regex, line, variables)
        result.append(line)
    dst_tmp = dst + '~'
    open(dst_tmp, 'w').writelines(result)
    # If contents are identical, don't touch the file to prevent
    # unnecessary rebuilds.
    try:
        if open(dst, 'r').read() == open(dst_tmp, 'r').read():
            return
    except FileNotFoundError:
        pass
    os.replace(dst_tmp, dst)

# It may seem a bit silly that this Backend class exists on its own
# rather than being a part of NinjaBackend, which is the only class
# that uses Backend. The point is that common functionality
# that will be used in XCode, Visual Studio etc will be in
# this one. Once work on that code starts the exact division
# of labor between the classes is determined.
class Backend():
    def __init__(self, build, interp):
        self.build = build
        self.environment = build.environment
        self.interpreter = interp
        self.processed_targets = {}
        self.build_to_src = os.path.relpath(self.environment.get_source_dir(),
                                            self.environment.get_build_dir())

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

    def generate_target(self, target, outfile):
        name = target.get_basename()
        if name in self.processed_targets:
            return
        self.process_target_dependencies(target, outfile)
        print('Generating target', name)
        self.generate_custom_generator_rules(target, outfile)
        outname = self.get_target_filename(target)
        obj_list = []
        if target.has_pch():
            self.generate_pch(target, outfile)
        header_deps = []
        for genlist in target.get_generated_sources():
            for src in genlist.get_outfilelist():
                if not self.environment.is_header(src):
                    obj_list.append(self.generate_single_compile(target, outfile, src, True))
                else:
                    header_deps.append(src)
        for src in target.get_sources():
            if not self.environment.is_header(src):
                obj_list.append(self.generate_single_compile(target, outfile, src, False, header_deps))
        elem = self.generate_link(target, outfile, outname, obj_list)
        self.generate_shlib_aliases(target, self.get_target_dir(target), outfile, elem)
        self.processed_targets[name] = True

    def process_target_dependencies(self, target, outfile):
        for t in target.get_dependencies():
            tname = t.get_basename()
            if not tname in self.processed_targets:
                self.generate_target(t, outfile)

    def get_pch_include_args(self, compiler, target):
        args = []
        pchpath = self.get_target_private_dir(target)
        includearg = compiler.get_include_arg(pchpath)
        for p in target.get_pch():
            if compiler.can_compile(p):
                args.append('-include')
                args.append(os.path.split(p)[-1])
        if len(args) > 0:
            args = [includearg] + args
        return args

    def generate_basic_compiler_flags(self, target, compiler):
        commands = []
        commands += self.build.get_global_flags(compiler)
        commands += target.get_extra_args(compiler.get_language())
        if self.environment.coredata.buildtype != 'plain':
            commands += compiler.get_debug_flags()
            commands += compiler.get_std_warn_flags()
        if self.environment.coredata.buildtype == 'optimized':
            commands += compiler.get_std_opt_flags()
        if self.environment.coredata.coverage:
            commands += compiler.get_coverage_flags()
        if isinstance(target, interpreter.SharedLibrary):
            commands += compiler.get_pic_flags()
        for dep in target.get_external_deps():
            commands += dep.get_compile_flags()
        return commands

    def build_target_link_arguments(self, deps):
        args = []
        for d in deps:
            if not isinstance(d, interpreter.StaticLibrary) and\
            not isinstance(d, interpreter.SharedLibrary):
                raise RuntimeError('Tried to link with a non-library target "%s".' % d.get_basename())
            fname = self.get_target_filename(d)
            fname = './' + fname # Hack to make ldd find the library.
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
            do_conf_file(infile, outfile, self.interpreter.get_variables())

class NinjaBuildElement():
    def __init__(self, outfilenames, rule, infilenames):
        if isinstance(outfilenames, str):
            self.outfilenames = [outfilenames]
        else:
            self.outfilenames = outfilenames
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
        Backend.__init__(self, build, interp)
        self.ninja_filename = 'build.ninja'

    def generate(self):
        outfilename = os.path.join(self.environment.get_build_dir(), self.ninja_filename)
        tempfilename = outfilename + '~'
        outfile = open(tempfilename, 'w')
        self.generate_configure_files()
        outfile.write('# This is the build file for project "%s"\n' % self.build.get_project())
        outfile.write('# It is autogenerated by the Meson build system.\n')
        outfile.write('# Do not edit by hand.\n\n')
        self.generate_rules(outfile)
        outfile.write('# Build rules for targets\n\n')
        [self.generate_target(t, outfile) for t in self.build.get_targets().values()]
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

    def generate_coverage_rules(self, outfile):
        (gcovr_exe, lcov_exe, genhtml_exe) = environment.find_coverage_tools()
        added_rule = False
        if gcovr_exe:
            added_rule = True
            elem = NinjaBuildElement('coverage-xml', 'CUSTOM_COMMAND', '')
            elem.add_item('COMMAND', [gcovr_exe, '-x', '-r', self.environment.get_build_dir(),\
                                      '-o', 'coverage.xml'])
            elem.add_item('DESC', 'Generating XML coverage report.')
            elem.write(outfile)
            elem = NinjaBuildElement('coverage-text', 'CUSTOM_COMMAND', '')
            elem.add_item('COMMAND', [gcovr_exe, '-r', self.environment.get_build_dir(),\
                                      '-o', 'coverage.txt'])
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
                       '--output-directory', 'coveragereport', '--title', 'Code coverage',\
                       '--legend', '--show-details', 'coverage.info']
            elem.add_item('COMMAND', command)
            elem.add_item('DESC', 'Generating HTML coverage report.')
            elem.write(outfile)
        if not added_rule:
            print('Warning: coverage requested but neither gcovr nor lcov/genhtml found.')

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
        elem.write(outfile)
        
        self.generate_target_install(d)
        self.generate_header_install(d)
        self.generate_man_install(d)
        self.generate_data_install(d)
        ofile = open(install_data_file, 'wb')
        pickle.dump(d, ofile)

    def generate_target_install(self, d):
        libdir = self.environment.get_libdir()
        bindir = self.environment.get_bindir()

        should_strip = self.environment.coredata.strip
        for t in self.build.get_targets().values():
            if t.should_install():
                if isinstance(t, interpreter.Executable):
                    outdir = bindir
                else:
                    outdir = libdir
                i = [self.get_target_filename(t), outdir, t.get_aliaslist(), should_strip]
                d.targets.append(i)

    def generate_header_install(self, d):
        incroot = self.environment.get_includedir()
        headers = self.build.get_headers()

        for h in headers:
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
                subdir = 'man' + num
                srcabs = os.path.join(self.environment.get_source_dir(), f)
                dstabs = os.path.join(manroot, 
                                      os.path.join(subdir, f + '.gz'))
                i = [srcabs, dstabs]
                d.man.append(i)

    def generate_data_install(self, d):
        dataroot = self.environment.get_datadir()
        data = self.build.get_data()
        for de in data:
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

        datafile = open(test_data, 'w')
        for t in self.build.get_tests():
            datafile.write(self.get_target_filename(t.get_exe()) + '\n')
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
                outfile.write(' command = %s\n' % command)
                desc = rule.description.replace('@INFILE@', '$in')
                outfile.write(' description = %s\n' % desc)
            outfile.write('\n')

    def generate_rules(self, outfile):
        outfile.write('# Rules for compiling.\n\n')
        self.generate_compile_rules(outfile)
        outfile.write('# Rules for linking.\n\n')
        self.generate_static_link_rules(outfile)
        self.generate_dynamic_link_rules(outfile)
        self.generate_dep_gen_rules(outfile)
        outfile.write('# Other rules\n\n')
        outfile.write('rule CUSTOM_COMMAND\n')
        outfile.write(' command = $COMMAND\n')
        outfile.write(' description = $DESC\n')
        outfile.write(' restat = 1\n\n')
        outfile.write('rule REGENERATE_BUILD\n')
        c = (sys.executable,
             ninja_quote(self.environment.get_build_command()),
             ninja_quote(self.environment.get_source_dir()),
             ninja_quote(self.environment.get_build_dir()))
        outfile.write(" command = '%s' '%s' '%s' '%s' --backend ninja\n" % c)
        outfile.write(' description = Regenerating build files\n')
        outfile.write(' generator = 1\n\n')

    def generate_static_link_rules(self, outfile):
        static_linker = self.build.static_linker
        rule = 'rule STATIC_LINKER\n'
        command = ' command = %s  $LINK_FLAGS $out $in\n' % \
        ' '.join(static_linker.get_exelist())
        description = ' description = Static linking library $out\n\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)

    def generate_dynamic_link_rules(self, outfile):
        for compiler in self.build.compilers:
            langname = compiler.get_language()
            rule = 'rule %s_LINKER\n' % langname
            command = ' command = %s %s $FLAGS  %s $out $in $LINK_FLAGS $aliasing\n' % \
            (execute_wrapper,
             ' '.join(compiler.get_exelist()),\
             ' '.join(compiler.get_output_flags()))
            description = ' description = Linking target $out'
            outfile.write(rule)
            outfile.write(command)
            outfile.write(description)
            outfile.write('\n')
        outfile.write('\n')

    def generate_compile_rules(self, outfile):
        qstr = quote_char + "%s" + quote_char
        for compiler in self.build.compilers:
            langname = compiler.get_language()
            rule = 'rule %s_COMPILER\n' % langname
            depflags = compiler.get_dependency_gen_flags('$out', '$DEPFILE')
            command = " command = %s $FLAGS %s %s $out %s $in\n" % \
            (' '.join(compiler.get_exelist()),\
             ' '.join([qstr % d for d in depflags]),\
             ' '.join(compiler.get_output_flags()),\
             ' '.join(compiler.get_compile_only_flags()))
            description = ' description = Compiling %s object $out\n' % langname
            dep = ' depfile = $DEPFILE\n'
            outfile.write(rule)
            outfile.write(command)
            outfile.write(dep)
            outfile.write(description)
            outfile.write('\n')
        outfile.write('\n')

    def generate_custom_generator_rules(self, target, outfile):
        for genlist in target.get_generated_sources():
            generator = genlist.get_generator()
            exe = generator.get_exe()
            infilelist = genlist.get_infilelist()
            outfilelist = genlist.get_outfilelist()
            if len(infilelist) != len(outfilelist):
                raise RuntimeError('Internal data structures broken.')
            if isinstance(exe, interpreter.BuildTarget):
                exe_file = os.path.join(self.environment.get_build_dir(), self.get_target_filename(exe))
            else:
                exe_file = exe.get_command()
            base_args = generator.get_arglist()
            for i in range(len(infilelist)):
                infilename = os.path.join(self.build_to_src, infilelist[i])
                outfilename = os.path.join(self.get_target_private_dir(target), outfilelist[i])
                args = [x.replace("@INPUT@", infilename).replace('@OUTPUT@', outfilename)\
                        for x in base_args]
                cmdlist = [exe_file] + args
                elem = NinjaBuildElement(outfilename, 'CUSTOM_COMMAND', infilename)
                elem.add_item('DESC', 'Generating $out')
                if isinstance(exe, interpreter.BuildTarget):
                    elem.add_dep(self.get_target_filename(exe))
                elem.add_item('COMMAND', cmdlist)
                elem.write(outfile)

    def generate_single_compile(self, target, outfile, src, is_generated=False, header_deps=[]):
        compiler = self.get_compiler_for_source(src)
        commands = self.generate_basic_compiler_flags(target, compiler)
        commands.append(compiler.get_include_arg(self.get_target_private_dir(target)))
        if is_generated:
            rel_src = os.path.join(self.get_target_private_dir(target), src)
        else:
            rel_src = os.path.join(self.build_to_src, target.get_source_subdir(), src)
        if os.path.isabs(src):
            src_filename = os.path.basename(src)
        else:
            src_filename = src
        rel_obj = os.path.join(self.get_target_private_dir(target), src_filename)
        rel_obj += '.' + self.environment.get_object_suffix()
        dep_file = rel_obj + '.' + compiler.get_depfile_suffix()
        pchlist = target.get_pch()
        if len(pchlist) == 0:
            pch_dep = []
        else:
            arr = []
            for pch in pchlist:
                i = os.path.join(self.get_target_private_dir(target),
                                  os.path.split(pch)[-1] + '.' + compiler.get_pch_suffix())
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
        commands += self.get_pch_include_args(compiler, target)
        compiler_name = '%s_COMPILER' % compiler.get_language()

        element = NinjaBuildElement(rel_obj, compiler_name, rel_src)
        if len(header_deps) > 0:
            element.add_dep([os.path.join(self.get_target_private_dir(target), d) for d in header_deps])
        element.add_orderdep(pch_dep)
        element.add_item('DEPFILE', dep_file)
        element.add_item('FLAGS', commands)
        element.write(outfile)
        return rel_obj

    def generate_pch(self, target, outfile):
        for pch in target.get_pch():
            if '/' not in pch:
                raise interpreter.InvalidArguments('Precompiled header of "%s" must not be in the same direcotory as source, please put it in a subdirectory.' % target.get_basename())
            compiler = self.get_compiler_for_source(pch)
            commands = []
            commands += self.generate_basic_compiler_flags(target, compiler)
            src = os.path.join(self.build_to_src, target.get_source_subdir(), pch)
            dst = os.path.join(self.get_target_private_dir(target),
                                  os.path.split(pch)[-1] + '.' + compiler.get_pch_suffix())
            dep = dst + '.' + compiler.get_depfile_suffix()
            elem = NinjaBuildElement(dst, compiler.get_language() + '_COMPILER', src)
            elem.add_item('FLAGS', commands)
            elem.add_item('DEPFILE', dep)
            elem.write(outfile)

    def generate_link(self, target, outfile, outname, obj_list):
        if isinstance(target, interpreter.StaticLibrary):
            linker = self.build.static_linker
            linker_base = 'STATIC'
        else:
            linker = self.build.compilers[0]
            linker_base = linker.get_language() # Fixme.
        linker_rule = linker_base + '_LINKER'
        commands = []
        if isinstance(target, interpreter.Executable):
            commands += linker.get_std_exe_link_flags()
        elif isinstance(target, interpreter.SharedLibrary):
            commands += linker.get_std_shared_lib_link_flags()
            commands += linker.get_pic_flags()
        elif isinstance(target, interpreter.StaticLibrary):
            commands += linker.get_std_link_flags()
        else:
            raise RuntimeError('Unknown build target type.')
        for dep in target.get_external_deps():
            commands += dep.get_link_flags()
        dependencies = target.get_dependencies()
        commands += self.build_target_link_arguments(dependencies)
        if self.environment.coredata.coverage:
            commands += linker.get_coverage_link_flags()
        dep_targets = [self.get_target_filename(t) for t in dependencies]
        elem = NinjaBuildElement(outname, linker_rule, obj_list)
        elem.add_dep(dep_targets)
        elem.add_item('LINK_FLAGS', commands)
        return elem

    def generate_shlib_aliases(self, target, outdir, outfile, elem):
        basename = target.get_filename()
        aliases = target.get_aliaslist()
        aliascmd = []
        for alias in aliases:
            aliasfile = os.path.join(outdir, alias)
            cmd = ["&&", 'ln', '-s', '-f', basename, aliasfile]
            aliascmd += cmd
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

    def generate_ending(self, outfile):
        targetlist = [self.get_target_filename(t) for t in self.build.get_targets().values()]
        elem = NinjaBuildElement('all', 'phony', targetlist)
        elem.write(outfile)

        default = 'default all\n\n'
        outfile.write(default)

        elem = NinjaBuildElement('clean', 'CUSTOM_COMMAND', '')
        elem.add_item('COMMAND', ['ninja', '-t', 'clean'])
        elem.add_item('description', 'Cleaning')
        if self.environment.coredata.coverage:
            self.generate_gcov_clean(outfile)
            elem.add_dep('clean-gcda')
            elem.add_dep('clean-gcno')
        elem.write(outfile)

        deps = [os.path.join(self.build_to_src, df) \
                for df in self.interpreter.get_build_def_files()]
        elem = NinjaBuildElement('build.ninja', 'REGENERATE_BUILD', deps)
        elem.write(outfile)

        elem = NinjaBuildElement(deps, 'phony', '')
        elem.write(outfile)
