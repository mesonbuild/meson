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

import os, stat, re
import interpreter, nodes

def shell_quote(cmdlist):
    return ["'" + x + "'" for x in cmdlist]

def ninja_quote(text):
    return text.replace(' ', '$ ')

def do_conf_file(src, dst, variables):
    data = open(src).readlines()
    regex = re.compile('@(.*?)@')
    result = []
    for line in data:
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
        result.append(line)
    open(dst, 'w').writelines(result)


class Generator():
    def __init__(self, build, interp):
        self.build = build
        self.environment = build.environment
        self.interpreter = interp
        self.processed_targets = {}

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
        dirname = os.path.join(self.environment.get_build_dir(), target.get_subdir())
        os.makedirs(dirname, exist_ok=True)
        return dirname
    
    def get_target_private_dir(self, target):
        dirname = os.path.join(self.get_target_dir(target), target.get_basename() + '.dir')
        os.makedirs(dirname, exist_ok=True)
        return dirname

    def generate_target(self, target, outfile):
        name = target.get_basename()
        if name in self.processed_targets:
            return
        self.process_target_dependencies(target, outfile)
        print('Generating target', name)
        outname = self.get_target_filename(target)
        obj_list = []
        if target.has_pch():
            self.generate_pch(target, outfile)
        for src in target.get_sources():
            obj_list.append(self.generate_single_compile(target, outfile, src))
        self.generate_link(target, outfile, outname, obj_list)
        self.generate_shlib_aliases(target, self.get_target_dir(target), outfile)
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

    def generate_basic_compiler_arguments(self, target, compiler):
        commands = []
        commands += compiler.get_exelist()
        commands += self.build.get_global_flags(compiler)
        commands += target.get_extra_args(compiler.get_language())
        commands += compiler.get_debug_flags()
        commands += compiler.get_std_warn_flags()
        commands += compiler.get_compile_only_flags()
        if isinstance(target, interpreter.SharedLibrary):
            commands += compiler.get_pic_flags()
        for dep in target.get_external_deps():
            commands += dep.get_compile_flags()
        return commands

class NinjaGenerator(Generator):

    def __init__(self, build, interp):
        Generator.__init__(self, build, interp)
        self.ninja_filename = 'build.ninja'

    def generate(self):
        outfilename = os.path.join(self.environment.get_build_dir(), self.ninja_filename)
        outfile = open(outfilename, 'w')
        outfile.write('# This is the build file for project "%s"\n' % self.build.get_project())
        outfile.write('# It is autogenerated. Do not edit by hand.\n\n')
        self.generate_rules(outfile)
        outfile.write('# Build rules for targets\n\n')
        [self.generate_target(t, outfile) for t in self.build.get_targets().values()]
        outfile.write('# Suffix\n\n')
        self.generate_ending(outfile)

    def generate_rules(self, outfile):
        outfile.write('# Rules for compiling.\n\n')
        self.generate_compile_rules(outfile)
        outfile.write('# Rules for linking.\n\n')
        self.generate_static_link_rules(outfile)
        self.generate_dynamic_link_rules(outfile)

    def generate_static_link_rules(self, outfile):
        static_linker = self.build.static_linker
        rule = 'rule STATIC_LINKER\n'
        command = ' command = %s %s $out $LINK_FLAGS $in\n' % \
        (' '.join(static_linker.get_exelist()),\
         ' '.join(static_linker.get_std_link_flags()))
        description = ' description = Static linking library $out\n\n'
        outfile.write(rule)
        outfile.write(command)
        outfile.write(description)

    def generate_dynamic_link_rules(self, outfile):
        for compiler in self.build.compilers:
            langname = compiler.get_language()
            rule = 'rule %s_LINKER\n' % langname
            command = ' command = %s $FLAGS $LINK_FLAGS %s $out %s $in\n' % \
            (' '.join(compiler.get_exelist()),\
             ' '.join(compiler.get_output_flags()),\
             ' '.join(compiler.get_compile_only_flags()))
            description = ' description = Linking target $out'
            outfile.write(rule)
            outfile.write(command)
            outfile.write(description)
            outfile.write('\n')
        outfile.write('\n')

    def generate_compile_rules(self, outfile):
        for compiler in self.build.compilers:
            langname = compiler.get_language()
            rule = 'rule %s_COMPILER\n' % langname
            command = ' command = %s $FLAGS %s $out %s $in\n' % \
            (' '.join(compiler.get_exelist()),\
             ' '.join(compiler.get_output_flags()),\
             ' '.join(compiler.get_compile_only_flags()))
            description = ' description = Compiling %s object $out' % langname
            outfile.write(rule)
            outfile.write(command)
            outfile.write(description)
            outfile.write('\n')
        outfile.write('\n')

    def generate_single_compile(self, target, outfile, src):
        compiler = self.get_compiler_for_source(src)
        commands = self.generate_basic_compiler_arguments(target, compiler)
        abs_src = os.path.join(self.environment.get_source_dir(), target.get_source_subdir(), src)
        abs_obj = os.path.join(self.get_target_private_dir(target), src)
        abs_obj += '.' + self.environment.get_object_suffix()
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
        commands.append(abs_src)
        compiler_name = '%s_COMPILER' % compiler.get_language()
        build = 'build %s: %s %s\n' % (abs_obj, compiler_name, abs_src)
        flags = ' FLAGS = %s\n\n' % ' '.join([ninja_quote(t) for t in commands])
        outfile.write(build)
        outfile.write(flags)
    
    def generate_link(self, target, outfile, outname, obj_list):
        pass

    def generate_shlib_aliases(self, target, outdir, outfile):
        pass

    def generate_ending(self, outfile):
        build = 'build all: phony %s\n' % ' '.join(self.build.get_targets().keys())
        default = 'default all\n\n'
        outfile.write(build)
        outfile.write(default)

class ShellGenerator(Generator):
    def __init__(self, build, interp):
        Generator.__init__(self, build, interp)
        self.build_filename = 'compile.sh'
        self.test_filename = 'run_tests.sh'
        self.install_filename = 'install.sh'

    def generate(self):
        self.generate_compile_script()
        self.generate_test_script()
        self.generate_install_script()

    def create_shfile(self, outfilename, message):
        outfile = open(outfilename, 'w')
        outfile.write('#!/bin/sh\n\n')
        outfile.write(message)
        cdcmd = ['cd', self.environment.get_build_dir()]
        outfile.write(' '.join(shell_quote(cdcmd)) + '\n')
        os.chmod(outfilename, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC |\
                 stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return outfile

    def generate_compile_script(self):
        outfilename = os.path.join(self.environment.get_build_dir(), self.build_filename)
        message = """echo This is an autogenerated shell script build file for project \\"%s\\"
echo This is experimental and most likely will not work!
""" % self.build.get_project()
        outfile = self.create_shfile(outfilename, message)
        self.generate_commands(outfile)
        outfile.close()

    def generate_test_script(self):
        outfilename = os.path.join(self.environment.get_build_dir(), self.test_filename)
        message = """echo This is an autogenerated test script for project \\"%s\\"
echo This is experimental and most likely will not work!
echo Run compile.sh before this or bad things will happen.
""" % self.build.get_project()
        outfile = self.create_shfile(outfilename, message)
        self.generate_tests(outfile)
        outfile.close()

    def generate_install_script(self):
        outfilename = os.path.join(self.environment.get_build_dir(), self.install_filename)
        message = """echo This is an autogenerated install script for project \\"%s\\"
echo This is experimental and most likely will not work!
echo Run compile.sh before this or bad things will happen.
""" % self.build.get_project()
        outfile = self.create_shfile(outfilename, message)
        self.generate_configure_files()
        self.generate_target_install(outfile)
        self.generate_header_install(outfile)
        self.generate_man_install(outfile)
        self.generate_data_install(outfile)
        outfile.close()
    
    def make_subdir(self, outfile, dir):
        cmdlist = ['mkdir', '-p', dir]
        outfile.write(' '.join(shell_quote(cmdlist)) + ' || exit\n')
        
    def copy_file(self, outfile, filename, outdir):
        cpcommand = ['cp', filename, outdir]
        cpcommand = ' '.join(shell_quote(cpcommand)) + ' || exit\n'
        outfile.write(cpcommand)

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

    def generate_data_install(self, outfile):
        prefix = self.environment.get_prefix()
        dataroot = os.path.join(prefix, self.environment.get_datadir())
        data = self.build.get_data()
        if len(data) != 0:
            outfile.write('\necho Installing data files.\n')
        else:
            outfile.write('\necho This project has no data files to install.\n')
        for d in data:
            subdir = os.path.join(dataroot, d.get_subdir())
            absdir = os.path.join(self.environment.get_prefix(), subdir)
            for f in d.get_sources():
                self.make_subdir(outfile, absdir)
                srcabs = os.path.join(self.environment.get_source_dir(), f)
                dstabs = os.path.join(absdir, f)
                self.copy_file(outfile, srcabs, dstabs)

    def generate_man_install(self, outfile):
        prefix = self.environment.get_prefix()
        manroot = os.path.join(prefix, self.environment.get_mandir())
        man = self.build.get_man()
        if len(man) != 0:
            outfile.write('\necho Installing man pages.\n')
        else:
            outfile.write('\necho This project has no man pages to install.\n')
        for m in man:
            for f in m.get_sources():
                num = f.split('.')[-1]
                subdir = 'man' + num
                absdir = os.path.join(manroot, subdir)
                self.make_subdir(outfile, absdir)
                srcabs = os.path.join(self.environment.get_source_dir(), f)
                dstabs = os.path.join(manroot, 
                                      os.path.join(subdir, f + '.gz'))
                cmd = "gzip < '%s' > '%s' || exit\n" % (srcabs, dstabs)
                outfile.write(cmd)

    def generate_header_install(self, outfile):
        prefix = self.environment.get_prefix()
        incroot = os.path.join(prefix, self.environment.get_includedir())
        headers = self.build.get_headers()
        if len(headers) != 0:
            outfile.write('\necho Installing headers.\n')
        else:
            outfile.write('\necho This project has no headers to install.\n')
        for h in headers:
            outdir = os.path.join(incroot, h.get_subdir())
            self.make_subdir(outfile, outdir)
            for f in h.get_sources():
                abspath = os.path.join(self.environment.get_source_dir(), f) # FIXME
                self.copy_file(outfile, abspath, outdir)

    def generate_target_install(self, outfile):
        prefix = self.environment.get_prefix()
        libdir = os.path.join(prefix, self.environment.get_libdir())
        bindir = os.path.join(prefix, self.environment.get_bindir())
        self.make_subdir(outfile, libdir)
        self.make_subdir(outfile, bindir)
        if len(self.build.get_targets()) != 0:
            outfile.write('\necho Installing targets.\n')
        else:
            outfile.write('\necho This project has no targets to install.\n')
        for tmp in self.build.get_targets().items():
            (name, t) = tmp
            if t.should_install():
                if isinstance(t, interpreter.Executable):
                    outdir = bindir
                else:
                    outdir = libdir
                outfile.write('echo Installing "%s".\n' % name)
                self.copy_file(outfile, self.get_target_filename(t), outdir)
                self.generate_shlib_aliases(t, outdir, outfile)
                self.fix_deps(outfile, t, outdir)

    def fix_deps(self, outfile, target, outdir):
        if isinstance(target, interpreter.StaticLibrary):
            return
        depfixer = self.environment.get_depfixer()
        fname = os.path.join(outdir, target.get_filename())
        cmds = [depfixer, fname, self.environment.get_build_dir()]
        outfile.write(' '.join(shell_quote(cmds)) + ' || exit\n')

    def generate_tests(self, outfile):
        for t in self.build.get_tests():
            cmds = []
            cmds.append(self.get_target_filename(t.get_exe()))
            outfile.write('echo Running test \\"%s\\".\n' % t.get_name())
            outfile.write(' '.join(shell_quote(cmds)) + ' || exit\n')


    def generate_single_compile(self, target, outfile, src):
        compiler = self.get_compiler_for_source(src)
        commands = self.generate_basic_compiler_arguments(target, compiler)
        abs_src = os.path.join(self.environment.get_source_dir(), target.get_source_subdir(), src)
        abs_obj = os.path.join(self.get_target_private_dir(target), src)
        abs_obj += '.' + self.environment.get_object_suffix()
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
        commands.append(abs_src)
        commands += compiler.get_output_flags()
        commands.append(abs_obj)
        quoted = shell_quote(commands)
        outfile.write('\necho Compiling \\"%s\\"\n' % src)
        outfile.write(' '.join(quoted) + ' || exit\n')
        return abs_obj

    def build_target_link_arguments(self, deps):
        args = []
        for d in deps:
            if not isinstance(d, interpreter.StaticLibrary) and\
            not isinstance(d, interpreter.SharedLibrary):
                raise RuntimeError('Tried to link with a non-library target "%s".' % d.get_basename())
            args.append(self.get_target_filename(d))
        return args

    def generate_link(self, target, outfile, outname, obj_list):
        if isinstance(target, interpreter.StaticLibrary):
            linker = self.build.static_linker
        else:
            linker = self.build.compilers[0] # Fixme.
        commands = []
        commands += linker.get_exelist()
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
        commands += linker.get_output_flags()
        commands.append(outname)
        commands += obj_list
        commands += self.build_target_link_arguments(target.get_dependencies())
        quoted = shell_quote(commands)
        outfile.write('\necho Linking \\"%s\\".\n' % target.get_basename())
        outfile.write(' '.join(quoted) + ' || exit\n')

    def generate_commands(self, outfile):
        for i in self.build.get_targets().items():
            target = i[1]
            self.generate_target(target, outfile)


    def generate_pch(self, target, outfile):
        print('Generating pch for "%s"' % target.get_basename())
        for pch in target.get_pch():
            if '/' not in pch:
                raise interpreter.InvalidArguments('Precompiled header of "%s" must not be in the same direcotory as source, please put it in a subdirectory.' % target.get_basename())
            compiler = self.get_compiler_for_source(pch)
            commands = self.generate_basic_compiler_arguments(target, compiler)
            srcabs = os.path.join(self.environment.get_source_dir(), target.get_source_subdir(), pch)
            dstabs = os.path.join(self.environment.get_build_dir(),
                                   self.get_target_private_dir(target),
                                   os.path.split(pch)[-1] + '.' + compiler.get_pch_suffix())
            commands.append(srcabs)
            commands += compiler.get_output_flags()
            commands.append(dstabs)
            quoted = shell_quote(commands)
            outfile.write('\necho Generating pch \\"%s\\".\n' % pch)
            outfile.write(' '.join(quoted) + ' || exit\n')

    def generate_shlib_aliases(self, target, outdir, outfile):
        basename = target.get_filename()
        aliases = target.get_aliaslist()
        for alias in aliases:
            aliasfile = os.path.join(outdir, alias)
            cmd = ['ln', '-s', '-f', basename, aliasfile]
            outfile.write(' '.join(shell_quote(cmd)) + '|| exit\n')

if __name__ == '__main__':
    code = """
    project('simple generator')
    language('c')
    executable('prog', 'prog.c', 'dep.c')
    """
    import environment
    os.chdir(os.path.split(__file__)[0])
    envir = environment.Environment('.', 'work area')
    intpr = interpreter.Interpreter(code, envir)
    g = ShellGenerator(intpr, envir)
    g.generate()
