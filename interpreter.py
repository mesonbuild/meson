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
import nodes
import environment
import coredata
import dependencies
import mlog
import os, sys, platform, copy, subprocess, shutil

class InterpreterException(coredata.MesonException):
    pass

class InvalidCode(InterpreterException):
    pass

class InvalidArguments(InterpreterException):
    pass

class InterpreterObject():
    def __init__(self):
        self.methods = {}

    def method_call(self, method_name, args, kwargs):
        if method_name in self.methods:
            return self.methods[method_name](args, kwargs)
        raise InvalidCode('Unknown method "%s" in object.' % method_name)

class TryRunResultHolder(InterpreterObject):
    def __init__(self, res):
        super().__init__()
        self.res = res
        self.methods.update({'returncode' : self.returncode_method,
                             'compiled' : self.compiled_method,
                             'stdout' : self.stdout_method,
                             'stderr' : self.stderr_method,
                             })
        
    def returncode_method(self, args, kwargs):
        return self.res.returncode
    
    def compiled_method(self, args, kwargs):
        return self.res.compiled
    
    def stdout_method(self, args, kwargs):
        return self.res.stdout
    
    def stderr_method(self, args, kwargs):
        return self.res.stderr

class RunProcess(InterpreterObject):

    def __init__(self, command_array, curdir):
        super().__init__()
        pc = self.run_command(command_array, curdir)
        (stdout, stderr) = pc.communicate()
        self.returncode = pc.returncode
        self.stdout = stdout.decode()
        self.stderr = stderr.decode()
        self.methods.update({'returncode' : self.returncode_method,
                             'stdout' : self.stdout_method,
                             'stderr' : self.stderr_method,
                             })
        
    def run_command(self, command_array, curdir):
        cmd_name = command_array[0]
        try:
            return subprocess.Popen(command_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            pass
        # Was not a command, is a program in path?
        exe = shutil.which(cmd_name)
        if exe is not None:
            command_array = [exe] + command_array[1:]
            return subprocess.Popen(command_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # No? Maybe it is a script in the source tree.
        fullpath = os.path.join(curdir, cmd_name)
        command_array = [fullpath] + command_array[1:]
        try:
            return subprocess.Popen(command_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            raise InterpreterException('Could not execute command "%s".' % cmd_name)

    def returncode_method(self, args, kwargs):
        return self.returncode

    def stdout_method(self, args, kwargs):
        return self.stdout

    def stderr_method(self, args, kwargs):
        return self.stderr

class ConfigurationData(InterpreterObject):
    def __init__(self):
        super().__init__()
        self.used = False # These objects become immutable after use in configure_file.
        self.values = {}
        self.methods.update({'set': self.set_method,
                             'set10': self.set10_method,
                             })

    def is_used(self):
        return self.used

    def mark_used(self):
        self.used = True

    def validate_args(self, args):
        if len(args) != 2:
            raise InterpreterException("Configuration set requires 2 arguments.")
        if self.used:
            raise InterpreterException("Can not set values on configuration object that has been used.")
        name = args[0]
        val = args[1]
        if not isinstance(name, str):
            raise InterpreterException("First argument to set must be a string.")
        return (name, val)

    def set_method(self, args, kwargs):
        (name, val) = self.validate_args(args)
        self.values[name] = val

    def set10_method(self, args, kwargs):
        (name, val) = self.validate_args(args)
        if val:
            self.values[name] = 1
        else:
            self.values[name] = 0

    def get(self, name):
        return self.values[name]

    def keys(self):
        return self.values.keys()

# Interpreter objects can not be pickled so we must have
# these wrappers.

class ExternalProgramHolder(InterpreterObject):
    def __init__(self, ep):
        InterpreterObject.__init__(self)
        self.ep = ep
        self.methods.update({'found': self.found_method})

    def found_method(self, args, kwargs):
        return self.found()

    def found(self):
        return self.ep.found()

    def get_command(self):
        return self.ep.fullpath

    def get_name(self):
        return self.ep.name

class ExternalLibraryHolder(InterpreterObject):
    def __init__(self, el):
        InterpreterObject.__init__(self)
        self.el = el
        self.methods.update({'found': self.found_method})

    def found(self):
        return self.el.found()

    def found_method(self, args, kwargs):
        return self.found()

    def get_filename(self):
        return self.el.fullpath

    def get_name(self):
        return self.el.name
    
    def get_compile_flags(self):
        return self.el.get_compile_flags()
    
    def get_link_flags(self):
        return self.el.get_link_flags()
    
    def get_exe_flags(self):
        return self.el.get_exe_flags()

class Generator(InterpreterObject):

    def __init__(self, args, kwargs):
        InterpreterObject.__init__(self)
        if len(args) != 1:
            raise InvalidArguments('Generator requires one and only one positional argument')
        if not isinstance(args[0], Executable) and \
           not isinstance(args[0], ExternalProgramHolder):
            raise InvalidArguments('First generator argument must be an executable object.')
        self.exe = args[0]
        self.methods.update({'process' : self.process_method})
        self.process_kwargs(kwargs)
    
    def get_exe(self):
        return self.exe

    def process_kwargs(self, kwargs):
        if 'arguments' not in kwargs:
            raise InvalidArguments('Generator must have "arguments" keyword argument.')
        args = kwargs['arguments']
        if isinstance(args, str):
            args = [args]
        if not isinstance(args, list):
            raise InvalidArguments('"Arguments" keyword argument must be a string or a list of strings.')
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('A non-string object in "arguments" keyword argument.')
        self.arglist = args
        
        if 'outputs' not in kwargs:
            raise InvalidArguments('Generator must have "outputs" keyword argument.')
        outputs = kwargs['outputs']
        if not isinstance(outputs, list):
            outputs = [outputs]
        for rule in outputs:
            if not isinstance(rule, str):
                raise InvalidArguments('"outputs" may only contain strings.')
            if not '@BASENAME@' in rule and not '@PLAINNAME@' in rule:
                raise InvalidArguments('"outputs" must contain @BASENAME@ or @PLAINNAME@.')
            if '/' in rule or '\\' in rule:
                raise InvalidArguments('"outputs" must not contain a directory separator.')
        self.outputs = outputs

    def get_base_outnames(self, inname):
        plainname = os.path.split(inname)[1]
        basename = plainname.split('.')[0]
        return [x.replace('@BASENAME@', basename).replace('@PLAINNAME@', plainname) for x in self.outputs]

    def process_method(self, args, kwargs):
        if len(kwargs) > 0:
            raise InvalidArguments('Process does not take keyword arguments.')
        if isinstance(args, str):
            args = [args]
        if not isinstance(args, list):
            raise InvalidArguments('Argument to "process" must be a string or a list of strings.')
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('A non-string object in "process" arguments.')
        gl = GeneratedList(self)
        [gl.add_file(a) for a in args]
        return gl

    def get_arglist(self):
        return self.arglist

class GeneratedList(InterpreterObject):
    def __init__(self, generator):
        InterpreterObject.__init__(self)
        self.generator = generator
        self.infilelist = []
        self.outfilelist = []
        self.outmap = {}

    def add_file(self, newfile):
        self.infilelist.append(newfile)
        outfiles = self.generator.get_base_outnames(newfile)
        self.outfilelist += outfiles
        self.outmap[newfile] = outfiles

    def get_infilelist(self):
        return self.infilelist

    def get_outfilelist(self):
        return self.outfilelist

    def get_outputs_for(self, filename):
        return self.outmap[filename]

    def get_generator(self):
        return self.generator

class Build(InterpreterObject):
    def __init__(self):
        InterpreterObject.__init__(self)
        self.methods.update({'name' : self.get_name_method,
                             })

    def get_name_method(self, args, kwargs):
        return platform.system().lower()

# This currently returns data for the current environment.
# It should return info for the target host.
class Host(InterpreterObject):
    def __init__(self, envir):
        InterpreterObject.__init__(self)
        self.environment = envir
        self.methods.update({'pointer_size' : self.get_ptrsize_method,
                             'name' : self.get_name_method,
                             'is_big_endian' : self.is_big_endian_method,
                             })
    # Is this needed any more since we have proper compiler
    # based tests? Consider removing it.
    def get_ptrsize_method(self, args, kwargs):
        if sys.maxsize > 2**32:
            return 64
        return 32

    def get_name_method(self, args, kwargs):
        if self.environment.is_cross_build():
            return self.environment.cross_info.get('name')
        return platform.system().lower()
    
    def is_big_endian_method(self, args, kwargs):
        return sys.byteorder != 'little'

class IncludeDirs(InterpreterObject):
    def __init__(self, curdir, dirs, kwargs):
        InterpreterObject.__init__(self)
        self.curdir = curdir
        self.incdirs = dirs
        # Fixme: check that the directories actually exist.
        # Also that they don't contain ".." or somesuch.
        if len(kwargs) > 0:
            raise InvalidCode('Includedirs function does not take keyword arguments.')

    def get_curdir(self):
        return self.curdir

    def get_incdirs(self):
        return self.incdirs

class Headers(InterpreterObject):

    def __init__(self, sources, kwargs):
        InterpreterObject.__init__(self)
        self.sources = sources
        self.subdir = kwargs.get('subdir', '')

    def set_subdir(self, subdir):
        self.subdir = subdir

    def get_subdir(self):
        return self.subdir
    
    def get_sources(self):
        return self.sources

class Data(InterpreterObject):
    
    def __init__(self, subdir, sources, kwargs):
        InterpreterObject.__init__(self)
        self.subdir = subdir
        self.sources = sources
        kwsource = kwargs.get('sources', [])
        if not isinstance(kwsource, list):
            kwsource = [kwsource]
        self.sources += kwsource

    def get_subdir(self):
        return self.subdir

    def get_sources(self):
        return self.sources

class ConfigureFile(InterpreterObject):
    
    def __init__(self, subdir, sourcename, targetname, configuration_data):
        InterpreterObject.__init__(self)
        self.subdir = subdir
        self.sourcename = sourcename
        self.targetname = targetname
        self.configuration_data = configuration_data

    def get_configuration_data(self):
        return self.configuration_data

    def get_sources(self):
        return self.sources
    
    def get_subdir(self):
        return self.subdir

    def get_source_name(self):
        return self.sourcename

    def get_target_name(self):
        return self.targetname

class Man(InterpreterObject):

    def __init__(self, sources, kwargs):
        InterpreterObject.__init__(self)
        self.sources = sources
        self.validate_sources()
        if len(kwargs) > 0:
            raise InvalidArguments('Man function takes no keyword arguments.')
        
    def validate_sources(self):
        for s in self.sources:
            num = int(s.split('.')[-1])
            if num < 1 or num > 8:
                raise InvalidArguments('Man file must have a file extension of a number between 1 and 8')

    def get_sources(self):
        return self.sources

class BuildTarget(InterpreterObject):

    def __init__(self, name, subdir, sources, kwargs):
        InterpreterObject.__init__(self)
        self.name = name
        self.subdir = subdir
        self.sources = []
        self.external_deps = []
        self.include_dirs = []
        self.link_targets = []
        self.filename = 'no_name'
        self.need_install = False
        self.pch = {}
        self.extra_args = {}
        self.generated = []
        self.process_sourcelist(sources)
        self.process_kwargs(kwargs)
        if len(self.sources) == 0 and len(self.generated) == 0:
            raise InvalidArguments('Build target %s has no sources.' % name)
    
    def process_sourcelist(self, sources):
        if not isinstance(sources, list):
            sources = [sources]
        for s in sources:
            if isinstance(s, str):
                self.sources.append(s)
            elif isinstance(s, GeneratedList):
                self.generated.append(s)
            else:
                raise InvalidArguments('Bad source in target %s.' % self.name)

    def get_original_kwargs(self):
        return self.kwargs

    def process_kwargs(self, kwargs):
        self.kwargs = copy.copy(kwargs)
        kwargs.get('modules', [])
        self.need_install = kwargs.get('install', self.need_install)
        llist = kwargs.get('link_with', [])
        if not isinstance(llist, list):
            llist = [llist]
        for linktarget in llist:
            self.link(linktarget)
        c_pchlist = kwargs.get('c_pch', [])
        if not isinstance(c_pchlist, list):
            c_pchlist = [c_pchlist]
        self.add_pch('c', c_pchlist)
        cpp_pchlist = kwargs.get('cpp_pch', [])
        if not isinstance(cpp_pchlist, list):
            cpp_pchlist = [cpp_pchlist]
        self.add_pch('cpp', cpp_pchlist)
        clist = kwargs.get('c_args', [])
        if not isinstance(clist, list):
            clist = [clist]
        self.add_compiler_args('c', clist)
        cpplist = kwargs.get('cpp_args', [])
        if not isinstance(cpplist, list):
            cpplist = [cpplist]
        self.add_compiler_args('cpp', cpplist)
        if 'version' in kwargs:
            self.set_version(kwargs['version'])
        if 'soversion' in kwargs:
            self.set_soversion(kwargs['soversion'])
        inclist = kwargs.get('include_dirs', [])
        if not isinstance(inclist, list):
            inclist = [inclist]
        self.add_include_dirs(inclist)
        deplist = kwargs.get('deps', [])
        if not isinstance(deplist, list):
            deplist = [deplist]
        self.add_external_deps(deplist)

    def get_subdir(self):
        return self.subdir

    def get_filename(self):
        return self.filename

    def get_extra_args(self, language):
        return self.extra_args.get(language, [])

    def get_dependencies(self):
        return self.link_targets

    def get_basename(self):
        return self.name

    def get_source_subdir(self):
        return self.subdir

    def get_sources(self):
        return self.sources

    def get_generated_sources(self):
        return self.generated

    def should_install(self):
        return self.need_install

    def has_pch(self):
        return len(self.pch) > 0

    def get_pch(self, language):
        try:
            return self.pch[language]
        except KeyError:
            return[]

    def get_include_dirs(self):
        return self.include_dirs

    def add_external_deps(self, deps):
        for dep in deps:
            if not isinstance(dep, dependencies.Dependency) and\
               not isinstance(dep, ExternalLibraryHolder):
                raise InvalidArguments('Argument is not an external dependency')
            self.external_deps.append(dep)
            if isinstance(dep, dependencies.Dependency):
                self.process_sourcelist(dep.get_sources())

    def get_external_deps(self):
        return self.external_deps

    def add_dep(self, args):
        [self.add_external_dep(dep) for dep in args]

    def link(self, target):
        if not isinstance(target, StaticLibrary) and \
        not isinstance(target, SharedLibrary):
            raise InvalidArguments('Link target is not library.')
        self.link_targets.append(target)

    def set_generated(self, genlist):
        for g in genlist:
            if not(isinstance(g, GeneratedList)):
                raise InvalidArguments('Generated source argument is not the output of a generator.')
            self.generated.append(g)

    def add_pch(self, language, pchlist):
        if len(pchlist) == 0:
            return
        if len(pchlist) == 2:
            if environment.is_header(pchlist[0]):
                if not environment.is_source(pchlist[1]):
                    raise InterpreterException('PCH definition must contain one header and at most one source.')
            elif environment.is_source(pchlist[0]):
                if not environment.is_header(pchlist[1]):
                    raise InterpreterException('PCH definition must contain one header and at most one source.')
                pchlist = [pchlist[1], pchlist[0]]
            else:
                raise InterpreterException('PCH argument %s is of unknown type.' % pchlist[0])
        elif len(pchlist) > 2:
            raise InterpreterException('PCH definition may have a maximum of 2 files.')
        self.pch[language] = pchlist

    def add_include_dirs(self, args):
        for a in args:
            if not isinstance(a, IncludeDirs):
                raise InvalidArguments('Include directory to be added is not an include directory object.')
        self.include_dirs += args

    def add_compiler_args(self, language, flags):
        for a in flags:
            if not isinstance(a, str):
                raise InvalidArguments('A non-string passed to compiler args.')
        if language in self.extra_args:
            self.extra_args[language] += flags
        else:
            self.extra_args[language] = flags

    def get_aliaslist(self):
        return []

class Executable(BuildTarget):
    def __init__(self, name, subdir, sources, environment, kwargs):
        BuildTarget.__init__(self, name, subdir, sources, kwargs)
        suffix = environment.get_exe_suffix()
        if suffix != '':
            self.filename = self.name + '.' + suffix
        else:
            self.filename = self.name

class StaticLibrary(BuildTarget):
    def __init__(self, name, subdir, sources, environment, kwargs):
        BuildTarget.__init__(self, name, subdir, sources, kwargs)
        prefix = environment.get_static_lib_prefix()
        suffix = environment.get_static_lib_suffix()
        self.filename = prefix + self.name + '.' + suffix

class SharedLibrary(BuildTarget):
    def __init__(self, name, subdir, sources, environment, kwargs):
        self.version = None
        self.soversion = None
        BuildTarget.__init__(self, name, subdir, sources, kwargs)
        self.prefix = environment.get_shared_lib_prefix()
        self.suffix = environment.get_shared_lib_suffix()

    def get_shbase(self):
        return self.prefix + self.name + '.' + self.suffix

    def get_filename(self):
        fname = self.get_shbase()
        if self.version is None:
            return fname
        else:
            return fname + '.' + self.version

    def set_version(self, version):
        if isinstance(version, nodes.StringStatement):
            version = version.get_value()
        if not isinstance(version, str):
            print(version)
            raise InvalidArguments('Shared library version is not a string.')
        self.version = version

    def set_soversion(self, version):
        if isinstance(version, nodes.StringStatement) or isinstance(version, nodes.IntStatement):
            version = version.get_value()
        if isinstance(version, int):
            version = str(version)
        if not isinstance(version, str):
            raise InvalidArguments('Shared library soversion is not a string or integer.')
        self.soversion = version

    def get_aliaslist(self):
        aliases = []
        if self.soversion is not None:
            aliases.append(self.get_shbase() + '.' + self.soversion)
        if self.version is not None:
            aliases.append(self.get_shbase())
        return aliases

class Test(InterpreterObject):
    def __init__(self, name, exe):
        InterpreterObject.__init__(self)
        self.name = name
        self.exe = exe
        
    def get_exe(self):
        return self.exe
    
    def get_name(self):
        return self.name

class CompilerHolder(InterpreterObject):
    def __init__(self, compiler, env):
        InterpreterObject.__init__(self)
        self.compiler = compiler
        self.environment = env
        self.methods.update({'compiles': self.compiles_method,
                             'get_id': self.get_id_method,
                             'sizeof': self.sizeof_method,
                             'has_header': self.has_header_method,
                             'run' : self.run_method,
                             'has_function' : self.has_function_method,
                             'has_member' : self.has_member_method,
                             'alignment' : self.alignment_method,
                             })

    def alignment_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Alignment method takes exactly one positional argument.')
        typename = args[0]
        if not isinstance(typename, str):
            raise InterpreterException('First argument is not a string.')
        result = self.compiler.alignment(typename)
        mlog.log('Checking for alignment of "', mlog.bold(typename), '": ', result, sep='')
        return result

    def run_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Run method takes exactly one positional argument.')
        code = args[0]
        if isinstance(code, nodes.StringStatement):
            code = code.get_value()
        testname = kwargs.get('name', '')
        if not isinstance(testname, str):
            raise InterpreterException('Testname argument must be a string.')
        if not isinstance(code, str):
            raise InterpreterException('First argument is not a string.')
        result = self.compiler.run(code)
        if len(testname) > 0:
            if not result.compiled:
                h = mlog.red('DID NOT COMPILE')
            elif result.returncode == 0:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO (%d)' % result.returncode)
            mlog.log('Checking if "', mlog.bold(testname), '" runs : ', h, sep='')
        return TryRunResultHolder(result)

    def get_id_method(self, args, kwargs):
        return self.compiler.get_id()

    def has_member_method(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('Has_member takes exactly two arguments.')
        typename = args[0]
        if not isinstance(typename, str):
            raise InterpreterException('Name of type must be a string.')
        membername = args[1]
        if not isinstance(membername, str):
            raise InterpreterException('Name of member must be a string.')
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_function must be a string.')
        had = self.compiler.has_member(typename, membername, prefix)
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking whether type "', mlog.bold(typename), 
                 '" has member "', mlog.bold(membername), '": ', hadtxt, sep='')
        return had

    def has_function_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Has_function takes exactly one argument.')
        funcname = args[0]
        if not isinstance(funcname, str):
            raise InterpreterException('Argument to has_function must be a string.')
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_function must be a string.')
        had = self.compiler.has_function(funcname, prefix, self.environment)
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking for function "', mlog.bold(funcname), '": ', hadtxt, sep='')
        return had

    def sizeof_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Sizeof takes exactly one argument.')
        element = args[0]
        if not isinstance(element, str):
            raise InterpreterException('Argument to sizeof must be a string.')
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of sizeof must be a string.')
        esize = self.compiler.sizeof(element, prefix, self.environment)
        mlog.log('Checking for size of "%s": %d' % (element, esize))
        return esize

    def compiles_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('compiles method takes exactly one argument.')
        string = args[0]
        testname = kwargs.get('name', '')
        if not isinstance(testname, str):
            raise InterpreterException('Testname argument must be a string.')
        if isinstance(string, nodes.StringStatement):
            string = string.value
        if not isinstance(string, str):
            raise InterpreterException('Argument to compiles() must be a string')
        result = self.compiler.compiles(string)
        if len(testname) > 0:
            if result:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO')
            mlog.log('Checking if "', mlog.bold(testname), '" compiles : ', h, sep='')
        return result

    def has_header_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('has_header method takes exactly one argument.')
        string = args[0]
        if isinstance(string, nodes.StringStatement):
            string = string.value
        if not isinstance(string, str):
            raise InterpreterException('Argument to has_header() must be a string')
        haz = self.compiler.has_header(string)
        if haz:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log('Has header "%s":' % string, h)
        return haz

class MesonMain(InterpreterObject):
    def __init__(self, build):
        InterpreterObject.__init__(self)
        self.build = build
        self.methods.update({'get_compiler': self.get_compiler_method})

    def get_compiler_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('get_compiler_method must have one and only one argument.')
        cname = args[0]
        for c in self.build.compilers:
            if c.get_language() == cname:
                return CompilerHolder(c, self.build.environment)
        raise InterpreterException('Tried to access compiler for unspecified language "%s".' % cname)
        

class Interpreter():

    def __init__(self, build):
        self.build = build
        code = open(os.path.join(build.environment.get_source_dir(),\
                                 environment.build_filename)).read()
        if len(code.strip()) == 0:
            raise InvalidCode('Builder file is empty.')
        assert(isinstance(code, str))
        try:
            self.ast = mparser.build_ast(code)
        except coredata.MesonException as me:
            me.file = environment.build_filename
            raise me
        self.sanity_check_ast()
        self.variables = {}
        self.builtin = {}
        self.builtin['build'] = Build()
        self.builtin['host'] = Host(build.environment)
        self.builtin['meson'] = MesonMain(build)
        self.environment = build.environment
        self.build_func_dict()
        self.build_def_files = [environment.build_filename]
        self.coredata = self.environment.get_coredata()
        self.subdir = ''
        self.generators = []
        self.visited_subdirs = {}

    def build_func_dict(self):
        self.funcs = {'project' : self.func_project, 
                      'message' : self.func_message,
                      'error' : self.func_error,
                      'executable': self.func_executable,
                      'dependency' : self.func_dependency,
                      'static_library' : self.func_static_lib,
                      'shared_library' : self.func_shared_lib,
                      'generator' : self.func_generator,
                      'test' : self.func_test,
                      'headers' : self.func_headers,
                      'man' : self.func_man,
                      'subdir' : self.func_subdir,
                      'data' : self.func_data,
                      'configure_file' : self.func_configure_file,
                      'include_directories' : self.func_include_directories,
                      'add_global_arguments' : self.func_add_global_arguments,
                      'find_program' : self.func_find_program,
                      'find_library' : self.func_find_library,
                      'configuration_data' : self.func_configuration_data,
                      'run_command' : self.func_run_command,
                      }

    def get_build_def_files(self):
        return self.build_def_files

    def get_variables(self):
        return self.variables

    def sanity_check_ast(self):
        if not isinstance(self.ast, nodes.CodeBlock):
            raise InvalidCode('AST is of invalid type. Possibly a bug in the parser.')
        if len(self.ast.get_statements()) == 0:
            raise InvalidCode('No statements in code.')
        first = self.ast.get_statements()[0]
        if not isinstance(first, nodes.FunctionCall) or first.get_function_name() != 'project':
            raise InvalidCode('First statement must be a call to project')

    def run(self):
        self.evaluate_codeblock(self.ast)

    def evaluate_codeblock(self, node):
        if node is None:
            return
        if not isinstance(node, nodes.CodeBlock):
            print(node)
            e = InvalidCode('Tried to execute a non-codeblock. Possibly a bug in the parser.')
            e.lineno = node.lineno()
            raise e
        statements = node.get_statements()
        i = 0
        while i < len(statements):
            cur = statements[i]
            try:
                self.evaluate_statement(cur)
            except Exception as e:
                e.lineno = cur.lineno()
                e.file = os.path.join(self.subdir, 'meson.build')
                raise e
            i += 1 # In THE FUTURE jump over blocks and stuff.

    def get_variable(self, varname):
        if varname in self.builtin:
            return self.builtin[varname]
        if varname in self.variables:
            return self.variables[varname]
        raise InvalidCode('Unknown variable "%s".' % varname)

    def set_variable(self, varname, variable):
        if varname in self.builtin:
            raise InvalidCode('Tried to overwrite internal variable "%s"' % varname)
        self.variables[varname] = variable

    def evaluate_statement(self, cur):
        if isinstance(cur, nodes.FunctionCall):
            return self.function_call(cur)
        elif isinstance(cur, nodes.Assignment):
            return self.assignment(cur)
        elif isinstance(cur, nodes.MethodCall):
            return self.method_call(cur)
        elif isinstance(cur, nodes.StringStatement):
            return cur
        elif isinstance(cur, nodes.BoolStatement):
            return cur
        elif isinstance(cur, nodes.IfStatement):
            return self.evaluate_if(cur)
        elif isinstance(cur, nodes.AtomStatement):
            return self.get_variable(cur.get_value())
        elif isinstance(cur, nodes.Comparison):
            return self.evaluate_comparison(cur)
        elif isinstance(cur, nodes.ArrayStatement):
            return self.evaluate_arraystatement(cur)
        elif isinstance(cur, nodes.IntStatement):
            return cur
        elif isinstance(cur, nodes.AndStatement):
            return self.evaluate_andstatement(cur)
        elif isinstance(cur, nodes.OrStatement):
            return self.evaluate_orstatement(cur)
        elif isinstance(cur, nodes.NotStatement):
            return self.evaluate_notstatement(cur)
        else:
            raise InvalidCode("Unknown statement.")

    def validate_arguments(self, args, argcount, arg_types):
        if argcount is not None:
            if argcount != len(args):
                raise InvalidArguments('Expected %d arguments, got %d',
                                       argcount, len(args))
        for i in range(min(len(args), len(arg_types))):
            wanted = arg_types[i]
            actual = args[i]
            if wanted != None:
                if not isinstance(actual, wanted):
                    raise InvalidArguments('Incorrect argument type.')
                
    def func_run_command(self, node, args, kwargs):
        for i in args:
            if not isinstance(i, str):
                raise InterpreterObject('Run_command arguments must be strings.')
        return RunProcess(args, os.path.join(self.environment.source_dir, self.subdir))

    def func_configuration_data(self, node, args, kwargs):
        if len(args) != 0:
            raise InterpreterException('configuration_data takes no arguments')
        return ConfigurationData()

    def func_project(self, node, args, kwargs):
        if len(args)< 2:
            raise InvalidArguments('Not enough arguments to project(). Needs at least the project name and one language')
        if len(kwargs) > 0:
            raise InvalidArguments('Project() does not take keyword arguments.')
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        if self.build.project is not None:
            raise InvalidCode('Second call to project().')
        self.build.project = args[0]
        mlog.log('Project name is "', mlog.bold(self.build.project), '".', sep='')
        self.add_languages(node, args[1:])

    def func_message(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        mlog.log(mlog.bold('Message:'), args[0])

    def func_error(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        raise InterpreterException('Error encountered: ' + args[0])

    def add_languages(self, node, args):
        for lang in args:
            if lang in self.coredata.compilers:
                comp = self.coredata.compilers[lang]
            else:
                if lang.lower() == 'c':
                    comp = self.environment.detect_c_compiler()
                elif lang.lower() == 'cpp':
                    comp = self.environment.detect_cpp_compiler()
                elif lang.lower() == 'objc':
                    comp = self.environment.detect_objc_compiler()
                elif lang.lower() == 'objcpp':
                    comp = self.environment.detect_objcpp_compiler()
                else:
                    raise InvalidCode('Tried to use unknown language "%s".' % lang)
                comp.sanity_check(self.environment.get_scratch_dir())
                self.coredata.compilers[lang] = comp
            mlog.log('Using %s compiler "' % lang, mlog.bold(' '.join(comp.get_exelist())), '". (%s)' % comp.id, sep='')
            self.build.add_compiler(comp)

    def func_find_program(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        required = kwargs.get('required', True)
        if not isinstance(required, bool):
            raise InvalidArguments('"required" argument must be a boolean.')
        exename = args[0]
        if exename in self.coredata.ext_progs and\
           self.coredata.ext_progs[exename].found():
            return ExternalProgramHolder(self.coredata.ext_progs[exename])
        extprog = dependencies.ExternalProgram(exename)
        progobj = ExternalProgramHolder(extprog)
        self.coredata.ext_progs[exename] = extprog
        if required and not progobj.found():
            raise InvalidArguments('Program "%s" not found.' % exename)
        return progobj

    def func_find_library(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        required = kwargs.get('required', True)
        if not isinstance(required, bool):
            raise InvalidArguments('"required" argument must be a boolean.')
        libname = args[0]
        if libname in self.coredata.ext_libs and\
           self.coredata.ext_libs[libname].found():
            return ExternalLibraryHolder(self.coredata.ext_libs[libname])
        result = self.environment.find_library(libname)
        extlib = dependencies.ExternalLibrary(libname, result)
        libobj = ExternalLibraryHolder(extlib)
        self.coredata.ext_libs[libname] = extlib
        if required and not libobj.found():
            raise InvalidArguments('External library "%s" not found.' % libname)
        return libobj

    def func_dependency(self, node, args, kwargs):
        self.validate_arguments(args, 1, [str])
        name = args[0]
        identifier = dependencies.get_dep_identifier(name, kwargs)
        if identifier in self.coredata.deps:
            dep = self.coredata.deps[identifier]
        else:
            dep = dependencies.Dependency() # Returns always false for dep.found()
        if not dep.found():
            dep = dependencies.find_external_dependency(name, kwargs)
        self.coredata.deps[identifier] = dep
        return dep

    def func_executable(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, Executable)

    def func_static_lib(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, StaticLibrary)

    def func_shared_lib(self, node, args, kwargs):
        return self.build_target(node, args, kwargs, SharedLibrary)

    def func_generator(self, node, args, kwargs):
        gen = Generator(args, kwargs)
        self.generators.append(gen)
        return gen

    def func_test(self, node, args, kwargs):
        self.validate_arguments(args, 2, [str, Executable])
        t = Test(args[0], args[1])
        self.build.tests.append(t)
        mlog.debug('Adding test "', mlog.bold(args[0]), '".', sep='')

    def func_headers(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        h = Headers(args, kwargs)
        self.build.headers.append(h)
        return h
    
    def func_man(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        m = Man(args, kwargs)
        self.build.man.append(m)
        return m
    
    def func_subdir(self, node, args, kwargs):
        if len(kwargs) > 0:
            raise InvalidArguments('subdir command takes no keyword arguments.')
        self.validate_arguments(args, 1, [str])
        prev_subdir = self.subdir
        subdir = os.path.join(prev_subdir, args[0])
        if subdir in self.visited_subdirs:
            raise InvalidArguments('Tried to enter directory "%s", which has already been visited.'\
                                   % subdir)
        self.visited_subdirs[subdir] = True
        self.subdir = subdir
        buildfilename = os.path.join(self.subdir, environment.build_filename)
        self.build_def_files.append(buildfilename)
        absname = os.path.join(self.environment.get_source_dir(), buildfilename)
        if not os.path.isfile(absname):
            raise InterpreterException('Nonexistant build def file %s.' % buildfilename)
        code = open(absname).read()
        assert(isinstance(code, str))
        try:
            codeblock = mparser.build_ast(code)
        except coredata.MesonException as me:
            me.file = buildfilename
            raise me
        mlog.log('Going to subdirectory "%s".' % self.subdir)
        self.evaluate_codeblock(codeblock)
        self.subdir = prev_subdir

    def func_data(self, node, args, kwargs):
        if len(args ) < 1:
            raise InvalidArguments('Data function must have at least one argument: the subdirectory.')
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        data = Data(args[0], args[1:], kwargs)
        self.build.data.append(data)
        return data
    
    def func_configure_file(self, node, args, kwargs):
        if len(args) > 0:
            raise InterpreterException("configure_file takes only keyword arguments.")
        if not 'input' in kwargs:
            raise InterpreterException('Required keyword argument "input" not defined.')
        if not 'output' in kwargs:
            raise InterpreterException('Required keyword argument "output" not defined.')
        if not 'configuration' in kwargs:
            raise InterpreterException('Required keyword argument "configuration" not defined.')
        inputfile = kwargs['input']
        output = kwargs['output']
        conf = kwargs['configuration']
        if not isinstance(conf, ConfigurationData):
            raise InterpreterException('Argument "configuration" is not of type configuration_data')

        conffile = os.path.join(self.subdir, inputfile)
        self.build_def_files.append(conffile)
        c = ConfigureFile(self.subdir, inputfile, output, conf)
        self.build.configure_files.append(c)
        conf.mark_used()

    def func_include_directories(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        i = IncludeDirs(self.subdir, args, kwargs)
        return i

    def func_add_global_arguments(self, node, args, kwargs):
        for a in args:
            if not isinstance(a, str):
                raise InvalidArguments('Argument %s is not a string.' % str(a))
        if len(self.build.get_targets()) > 0:
            raise InvalidCode('Global flags can not be set once any build target is defined.')
        if not 'language' in kwargs:
            raise InvalidCode('Missing language definition in add_global_arguments')
        lang = kwargs['language'].lower()
        if lang in self.build.global_args:
            self.build.global_args[lang] += args
        else:
            self.build.global_args[lang] = args

    def flatten(self, args):
        if isinstance(args, nodes.StringStatement):
            return args.get_value()
        if isinstance(args, str):
            return args
        result = []
        for a in args:
            if isinstance(a, list):
                rest = self.flatten(a)
                result = result + rest
            elif isinstance(a, nodes.StringStatement):
                result.append(a.get_value())
            else:
                result.append(a)
        return result

    def build_target(self, node, args, kwargs, targetclass):
        args = self.flatten(args)
        name = args[0]
        sources = args[1:]
        if name in coredata.forbidden_target_names:
            raise InvalidArguments('Target name "%s" is reserved for Meson\'s internal use. Please rename.'\
                                   % name)
        try:
            kw_src = self.flatten(kwargs['sources'])
            if not isinstance(kw_src, list):
                kw_src = [kw_src]
        except KeyError:
            kw_src = []
        sources += kw_src
        if name in self.build.targets:
            raise InvalidCode('Tried to create target "%s", but a target of that name already exists.' % name)
        self.check_sources_exist(os.path.join(self.environment.source_dir, self.subdir), sources)
        l = targetclass(name, self.subdir, sources, self.environment, kwargs)
        self.build.targets[name] = l
        mlog.log('Creating build target "', mlog.bold(name), '" with %d files.' % len(sources), sep='')
        return l

    def check_sources_exist(self, subdir, sources):
        for s in sources:
            if not isinstance(s, str):
                continue # This means a generated source and they always exist.
            fname = os.path.join(subdir, s)
            if not os.path.isfile(fname):
                raise InterpreterException('Tried to add non-existing source %s.' % s)
        
    def function_call(self, node):
        func_name = node.get_function_name()
        (posargs, kwargs) = self.reduce_arguments(node.arguments)
        if func_name in self.funcs:
            return self.funcs[func_name](node, posargs, kwargs)
        else:
            raise InvalidCode('Unknown function "%s".' % func_name)

    def is_assignable(self, value):
        if isinstance(value, InterpreterObject) or \
            isinstance(value, dependencies.Dependency) or\
            isinstance(value, str) or\
            isinstance(value, int) or \
            isinstance(value, list):
            return True
        return False
    
    def assignment(self, node):
        var_name = node.var_name
        if not isinstance(var_name, nodes.AtomExpression):
            raise InvalidArguments('Tried to assign value to a non-variable.')
        var_name = var_name.get_value()
        value = self.evaluate_statement(node.value)
        if value is None:
            raise InvalidCode('Can not assign None to variable.')
        value = self.to_native(value)
        if not self.is_assignable(value):
            raise InvalidCode('Tried to assign an invalid value to variable.')
        self.set_variable(var_name, value)
        return value

    def reduce_single(self, arg):
        if isinstance(arg, nodes.AtomExpression) or isinstance(arg, nodes.AtomStatement):
            return self.get_variable(arg.value)
        elif isinstance(arg, str):
            return arg
        elif isinstance(arg, nodes.StringExpression) or isinstance(arg, nodes.StringStatement):
            return arg.get_value()
        elif isinstance(arg, nodes.FunctionCall):
            return self.function_call(arg)
        elif isinstance(arg, nodes.MethodCall):
            return self.method_call(arg)
        elif isinstance(arg, nodes.BoolStatement) or isinstance(arg, nodes.BoolExpression):
            return arg.get_value()
        elif isinstance(arg, nodes.ArrayStatement):
            return [self.reduce_single(curarg) for curarg in arg.args.arguments]
        elif isinstance(arg, nodes.IntStatement):
            return arg.get_value()
        else:
            raise InvalidCode('Irreducible argument.')

    def reduce_arguments(self, args):
        assert(isinstance(args, nodes.Arguments))
        if args.incorrect_order():
            raise InvalidArguments('All keyword arguments must be after positional arguments.')
        reduced_pos = [self.reduce_single(arg) for arg in args.arguments]
        reduced_kw = {}
        for key in args.kwargs.keys():
            if not isinstance(key, str):
                raise InvalidArguments('Keyword argument name is not a string.')
            a = args.kwargs[key]
            reduced_kw[key] = self.reduce_single(a)
        return (reduced_pos, reduced_kw)
    
    def string_method_call(self, obj, method_name, args):
        if method_name == 'strip':
            return self.to_native(obj).strip()
        if method_name == 'format':
            return self.format_string(obj, args)
        raise InterpreterException('Unknown method "%s" for a string.' % method_name)

    def to_native(self, arg):
        if isinstance(arg, nodes.StringStatement) or \
           isinstance(arg, nodes.IntStatement) or \
           isinstance(arg, nodes.BoolStatement):
            return arg.get_value()
        return arg

    def format_string(self, templ, args):
        templ = self.to_native(templ)
        if isinstance(args, nodes.Arguments):
            args = args.arguments
        for (i, arg) in enumerate(args):
            arg = self.to_native(self.reduce_single(arg))
            if isinstance(arg, bool): # Python boolean is upper case.
                arg = str(arg).lower()
            templ = templ.replace('@{}@'.format(i), str(arg))
        return templ

    def method_call(self, node):
        invokable = node.invokable
        if isinstance(invokable, nodes.AtomStatement):
            object_name = invokable.get_value()
            obj = self.get_variable(object_name)
        else:
            obj = self.evaluate_statement(invokable)
        method_name = node.method_name.get_value()
        args = node.arguments
        if isinstance(obj, nodes.StringStatement):
            obj = obj.get_value()
        if isinstance(obj, str):
            return self.string_method_call(obj, method_name, args)
        if not isinstance(obj, InterpreterObject):
            raise InvalidArguments('Variable "%s" is not callable.' % object_name)
        (args, kwargs) = self.reduce_arguments(args)
        return obj.method_call(method_name, args, kwargs)
    
    def evaluate_if(self, node):
        result = self.evaluate_statement(node.clause)
        cond = None
        if isinstance(result, nodes.BoolExpression) or \
           isinstance(result, nodes.BoolStatement):
            cond = result.get_value()
        if isinstance(result, bool):
            cond = result
        if cond is not None:
            if cond:
                self.evaluate_codeblock(node.trueblock)
            else:
                block = node.falseblock
                if isinstance(block, nodes.IfStatement):
                    self.evaluate_if(block)
                else:
                    self.evaluate_codeblock(block)
        else:
            raise InvalidCode('If clause does not evaluate to true or false.')

    def is_elementary_type(self, v):
        if isinstance(v, int) or isinstance(v, str) or isinstance(v, bool):
            return True
        return False

    def evaluate_comparison(self, node):
        v1 = self.evaluate_statement(node.get_first())
        v2 = self.evaluate_statement(node.get_second())
        if self.is_elementary_type(v1):
            val1 = v1
        else:
            val1 = v1.get_value()
        if self.is_elementary_type(v2):
            val2 = v2
        else:
            val2 = v2.get_value()
        if type(val1) != type(val2):
            raise InterpreterException('Comparison of different types %s and %s.' %
                                       (str(type(val1)), str(type(val2))))
        if node.get_ctype() == '==':
            return val1 == val2
        elif node.get_ctype() == '!=':
            return val1 != val2
        else:
            raise InvalidCode('You broke me.')

    def evaluate_andstatement(self, cur):
        l = self.evaluate_statement(cur.left)
        if isinstance(l, nodes.BoolStatement):
            l = l.get_value()
        if not isinstance(l, bool):
            raise InterpreterException('First argument to "and" is not a boolean.')
        if not l:
            return False
        r = self.evaluate_statement(cur.right)
        if isinstance(r, nodes.BoolStatement):
            r = r.get_value()
        if not isinstance(r, bool):
            raise InterpreterException('Second argument to "and" is not a boolean.')
        return r

    def evaluate_orstatement(self, cur):
        l = self.evaluate_statement(cur.left)
        if isinstance(l, nodes.BoolStatement):
            l = l.get_value()
        if not isinstance(l, bool):
            raise InterpreterException('First argument to "or" is not a boolean.')
        if l:
            return True
        r = self.evaluate_statement(cur.right)
        if isinstance(r, nodes.BoolStatement):
            r = r.get_value()
        if not isinstance(r, bool):
            raise InterpreterException('Second argument to "or" is not a boolean.')
        return r
    
    def evaluate_notstatement(self, cur):
        v = self.evaluate_statement(cur.val)
        if isinstance(v, nodes.BoolStatement):
            v = v.get_value()
        if not isinstance(v, bool):
            raise InterpreterException('Argument to "not" is not a boolean.')
        return not v

    def evaluate_arraystatement(self, cur):
        (arguments, kwargs) = self.reduce_arguments(cur.get_args())
        if len(kwargs) > 0:
            raise InvalidCode('Keyword arguments are invalid in array construction.')
        return arguments
