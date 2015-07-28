# Copyright 2012-2014 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess, os.path
import tempfile
import mesonlib
import mlog
from coredata import MesonException

"""This file contains the data files of all compilers Meson knows
about. To support a new compiler, add its information below.
Also add corresponding autodetection code in environment.py."""

header_suffixes = ['h', 'hh', 'hpp', 'hxx', 'H', 'moc', 'vapi']
cpp_suffixes = ['cc', 'cpp', 'cxx', 'h', 'hh', 'hpp', 'hxx', 'c++']
c_suffixes = ['c']
clike_suffixes = c_suffixes + cpp_suffixes
obj_suffixes = ['o', 'obj']

def is_header(fname):
    if hasattr(fname, 'fname'):
        fname = fname.fname
    suffix = fname.split('.')[-1]
    return suffix in header_suffixes

def is_source(fname):
    if hasattr(fname, 'fname'):
        fname = fname.fname
    suffix = fname.split('.')[-1]
    return suffix in clike_suffixes

def is_object(fname):
    if hasattr(fname, 'fname'):
        fname = fname.fname
    suffix = fname.split('.')[-1]
    return suffix in obj_suffixes

gnulike_buildtype_args = {'plain' : [],
                          'debug' : ['-g'],
                          'debugoptimized' : ['-O2', '-g'],
                          'release' : ['-O3']}

msvc_buildtype_args = {'plain' : [],
                       'debug' : ["/MDd", "/Zi", "/Ob0", "/Od", "/RTC1"],
                       'debugoptimized' : ["/MD", "/Zi", "/O2", "/Ob1", "/D"],
                       'release' : ["/MD", "/O2", "/Ob2"]}

gnulike_buildtype_linker_args = {}

if mesonlib.is_osx():
    gnulike_buildtype_linker_args.update({'plain' : [],
                                          'debug' : [],
                                          'debugoptimized' : [],
                                          'release' : [],
                                         })
else:
    gnulike_buildtype_linker_args.update({'plain' : [],
                                          'debug' : [],
                                          'debugoptimized' : [],
                                          'release' : ['-Wl,-O1'],
                                         })

msvc_buildtype_linker_args = {'plain' : [],
                              'debug' : [],
                              'debugoptimized' : [],
                              'release' : []}

java_buildtype_args = {'plain' : [],
                       'debug' : ['-g'],
                       'debugoptimized' : ['-g'],
                       'release' : []}

rust_buildtype_args = {'plain' : [],
                       'debug' : ['-g'],
                       'debugoptimized' : ['-g', '--opt-level', '2'],
                       'release' : ['--opt-level', '3']}

mono_buildtype_args = {'plain' : [],
                       'debug' : ['-debug'],
                       'debugoptimized': ['-debug', '-optimize+'],
                       'release' : ['-optimize+']}

def build_unix_rpath_args(build_dir, rpath_paths, install_rpath):
        if len(rpath_paths) == 0 and len(install_rpath) == 0:
            return []
        paths = ':'.join([os.path.join(build_dir, p) for p in rpath_paths])
        if len(paths) < len(install_rpath):
            padding = 'X'*(len(install_rpath) - len(paths))
            if len(paths) == 0:
                paths = padding
            else:
                paths = paths + ':' + padding
        return ['-Wl,-rpath,' + paths]

class EnvironmentException(MesonException):
    def __init(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class CrossNoRunException(MesonException):
    def __init(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class RunResult():
    def __init__(self, compiled, returncode=999, stdout='UNDEFINED', stderr='UNDEFINED'):
        self.compiled = compiled
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

class CCompiler():
    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        if type(exelist) == type(''):
            self.exelist = [exelist]
        elif type(exelist) == type([]):
            self.exelist = exelist
        else:
            raise TypeError('Unknown argument to CCompiler')
        self.version = version
        self.language = 'c'
        self.default_suffix = 'c'
        self.id = 'unknown'
        self.is_cross = is_cross
        if isinstance(exe_wrapper, str):
            self.exe_wrapper = [exe_wrapper]
        else:
            self.exe_wrapper = exe_wrapper

    def needs_static_linker(self):
        return True # When compiling static libraries, so yes.

    def get_always_args(self):
        return []

    def get_linker_always_args(self):
        return []

    def get_soname_args(self, shlib_name, path, soversion):
        return []

    def split_shlib_to_parts(self, fname):
        return (None, fname)

    # The default behaviour is this, override in
    # OSX and MSVC.
    def build_rpath_args(self, build_dir, rpath_paths, install_rpath):
        return build_unix_rpath_args(build_dir, rpath_paths, install_rpath)

    def get_id(self):
        return self.id

    def get_dependency_gen_args(self, outtarget, outfile):
        return ['-MMD', '-MQ', outtarget, '-MF', outfile]

    def get_depfile_suffix(self):
        return 'd'

    def get_language(self):
        return self.language

    def get_default_suffix(self):
        return self.default_suffix

    def get_exelist(self):
        return self.exelist[:]

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_compile_only_args(self):
        return ['-c']

    def get_output_args(self, target):
        return ['-o', target]

    def get_linker_output_args(self, outputname):
        return ['-o', outputname]

    def get_coverage_args(self):
        return ['--coverage']

    def get_coverage_link_args(self):
        return ['-lgcov']

    def get_werror_args(self):
        return ['-Werror']

    def get_std_exe_link_args(self):
        return []

    def get_include_args(self, path):
        return ['-I' + path]

    def get_std_shared_lib_link_args(self):
        return ['-shared']

    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        if suffix == 'c' or suffix == 'h':
            return True
        return False

    def get_pic_args(self):
        return ['-fPIC']

    def name_string(self):
        return ' '.join(self.exelist)

    def get_pch_use_args(self, pch_dir, header):
        return ['-include', os.path.split(header)[-1]]

    def get_pch_name(self, header_name):
        return os.path.split(header_name)[-1] + '.' + self.get_pch_suffix()

    def sanity_check(self, work_dir):
        source_name = os.path.join(work_dir, 'sanitycheckc.c')
        binary_name = os.path.join(work_dir, 'sanitycheckc')
        ofile = open(source_name, 'w')
        ofile.write('int main(int argc, char **argv) { int class=0; return class; }\n')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Compiler %s can not compile programs.' % self.name_string())
        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper + [binary_name]
        else:
            cmdlist = [binary_name]
        pe = subprocess.Popen(cmdlist)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by C compiler %s are not runnable.' % self.name_string())

    def has_header(self, hname):
        templ = '''#include<%s>
int someSymbolHereJustForFun;
'''
        return self.compiles(templ % hname)

    def compiles(self, code):
        mlog.debug('Running compile test:\n\n', code)
        suflen = len(self.default_suffix)
        (fd, srcname) = tempfile.mkstemp(suffix='.'+self.default_suffix)
        os.close(fd)
        ofile = open(srcname, 'w')
        ofile.write(code)
        ofile.close()
        commands = self.get_exelist()
        commands += self.get_compile_only_args()
        commands.append(srcname)
        p = subprocess.Popen(commands, cwd=os.path.split(srcname)[0], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stde, stdo) = p.communicate()
        stde = stde.decode()
        stdo = stdo.decode()
        mlog.debug('Compiler stdout:\n', stdo)
        mlog.debug('Compiler stderr:\n', stde)
        os.remove(srcname)
        try:
            trial = srcname[:-suflen] + 'o'
            os.remove(trial)
        except FileNotFoundError:
            pass
        try:
            os.remove(srcname[:-suflen] + 'obj')
        except FileNotFoundError:
            pass
        return p.returncode == 0

    def run(self, code):
        mlog.debug('Running code:\n\n', code)
        if self.is_cross and self.exe_wrapper is None:
            raise CrossNoRunException('Can not run test applications in this cross environment.')
        (fd, srcname) = tempfile.mkstemp(suffix='.'+self.default_suffix)
        os.close(fd)
        ofile = open(srcname, 'w')
        ofile.write(code)
        ofile.close()
        exename = srcname + '.exe' # Is guaranteed to be executable on every platform.
        commands = self.get_exelist()
        commands.append(srcname)
        commands += self.get_output_args(exename)
        p = subprocess.Popen(commands, cwd=os.path.split(srcname)[0], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdo, stde) = p.communicate()
        stde = stde.decode()
        stdo = stdo.decode()
        mlog.debug('Compiler stdout:\n', stdo)
        mlog.debug('Compiler stderr:\n', stde)
        os.remove(srcname)
        if p.returncode != 0:
            return RunResult(False)
        if self.is_cross:
            cmdlist = self.exe_wrapper + [exename]
        else:
            cmdlist = exename
        pe = subprocess.Popen(cmdlist, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (so, se) = pe.communicate()
        so = so.decode()
        se = se.decode()
        mlog.debug('Program stdout:\n', so)
        mlog.debug('Program stderr:\n', se)
        os.remove(exename)
        return RunResult(True, pe.returncode, so, se)

    def sizeof(self, element, prefix, env):
        templ = '''#include<stdio.h>
%s

int main(int argc, char **argv) {
    printf("%%ld\\n", (long)(sizeof(%s)));
    return 0;
};
'''
        varname = 'sizeof ' + element
        varname = varname.replace(' ', '_')
        if self.is_cross:
            val = env.cross_info.config['properties'][varname]
            if val is not None:
                if isinstance(val, int):
                    return val
                raise EnvironmentException('Cross variable {0} is not an integer.'.format(varname))
        cross_failed = False
        try:
            res = self.run(templ % (prefix, element))
        except CrossNoRunException:
            cross_failed = True
        if cross_failed:
            message = '''Can not determine size of {0} because cross compiled binaries are not runnable.
Please define the corresponding variable {1} in your cross compilation definition file.'''.format(element, varname)
            raise EnvironmentException(message)
        if not res.compiled:
            raise EnvironmentException('Could not compile sizeof test.')
        if res.returncode != 0:
            raise EnvironmentException('Could not run sizeof test binary.')
        return int(res.stdout)

    def alignment(self, typename, env):
        templ = '''#include<stdio.h>
#include<stddef.h>

struct tmp {
  char c;
  %s target;
};

int main(int argc, char **argv) {
  printf("%%d", (int)offsetof(struct tmp, target));
  return 0;
}
'''
        varname = 'alignment ' + typename
        varname = varname.replace(' ', '_')
        if self.is_cross:
            val = env.cross_info.config['properties'][varname]
            if val is not None:
                if isinstance(val, int):
                    return val
                raise EnvironmentException('Cross variable {0} is not an integer.'.format(varname))
        cross_failed = False
        try:
            res = self.run(templ % typename)
        except CrossNoRunException:
            cross_failed = True
        if cross_failed:
            message = '''Can not determine alignment of {0} because cross compiled binaries are not runnable.
Please define the corresponding variable {1} in your cross compilation definition file.'''.format(typename, varname)
            raise EnvironmentException(message)
        if not res.compiled:
            raise EnvironmentException('Could not compile alignment test.')
        if res.returncode != 0:
            raise EnvironmentException('Could not run alignment test binary.')
        align = int(res.stdout)
        if align == 0:
            raise EnvironmentException('Could not determine alignment of %s. Sorry. You might want to file a bug.' % typename)
        return align

    def has_function(self, funcname, prefix, env):
        # This fails (returns true) if funcname is a ptr or a variable.
        # The correct check is a lot more difficult.
        # Fix this to do that eventually.
        templ = '''%s
int main(int argc, char **argv) {
    void *ptr = (void*)(%s);
    return 0;
};
'''
        varname = 'has function ' + funcname
        varname = varname.replace(' ', '_')
        if self.is_cross:
            val = env.cross_info.config['properties'].get(varname, None)
            if val is not None:
                if isinstance(val, bool):
                    return val
                raise EnvironmentException('Cross variable {0} is not an boolean.'.format(varname))
        return self.compiles(templ % (prefix, funcname))

    def has_member(self, typename, membername, prefix):
        templ = '''%s
void bar() {
    %s foo;
    foo.%s;
};
'''
        return self.compiles(templ % (prefix, typename, membername))

    def has_type(self, typename, prefix):
        templ = '''%s
void bar() {
    sizeof(%s);
};
'''
        return self.compiles(templ % (prefix, typename))

    def thread_flags(self):
        return ['-pthread']

    def thread_link_flags(self):
        return ['-pthread']

class CPPCompiler(CCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap):
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        self.language = 'cpp'
        self.default_suffix = 'cpp'

    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        if suffix in cpp_suffixes:
            return True
        return False

    def sanity_check(self, work_dir):
        source_name = os.path.join(work_dir, 'sanitycheckcpp.cc')
        binary_name = os.path.join(work_dir, 'sanitycheckcpp')
        ofile = open(source_name, 'w')
        ofile.write('class breakCCompiler;int main(int argc, char **argv) { return 0; }\n')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Compiler %s can not compile programs.' % self.name_string())
        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper + [binary_name]
        else:
            cmdlist = [binary_name]
        pe = subprocess.Popen(cmdlist)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by C++ compiler %s are not runnable.' % self.name_string())

class ObjCCompiler(CCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap):
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        self.language = 'objc'
        self.default_suffix = 'm'

    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        if suffix == 'm' or suffix == 'h':
            return True
        return False

    def sanity_check(self, work_dir):
        source_name = os.path.join(work_dir, 'sanitycheckobjc.m')
        binary_name = os.path.join(work_dir, 'sanitycheckobjc')
        ofile = open(source_name, 'w')
        ofile.write('#import<stdio.h>\nint main(int argc, char **argv) { return 0; }\n')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('ObjC compiler %s can not compile programs.' % self.name_string())
        pe = subprocess.Popen(binary_name)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by ObjC compiler %s are not runnable.' % self.name_string())

class ObjCPPCompiler(CPPCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        self.language = 'objcpp'
        self.default_suffix = 'mm'

    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        if suffix == 'mm' or suffix == 'h':
            return True
        return False

    def sanity_check(self, work_dir):
        source_name = os.path.join(work_dir, 'sanitycheckobjcpp.mm')
        binary_name = os.path.join(work_dir, 'sanitycheckobjcpp')
        ofile = open(source_name, 'w')
        ofile.write('#import<stdio.h>\nclass MyClass;int main(int argc, char **argv) { return 0; }\n')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('ObjC++ compiler %s can not compile programs.' % self.name_string())
        pe = subprocess.Popen(binary_name)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by ObjC++ compiler %s are not runnable.' % self.name_string())

class MonoCompiler():
    def __init__(self, exelist, version):
        if type(exelist) == type(''):
            self.exelist = [exelist]
        elif type(exelist) == type([]):
            self.exelist = exelist
        else:
            raise TypeError('Unknown argument to Mono compiler')
        self.version = version
        self.language = 'cs'
        self.default_suffix = 'cs'
        self.id = 'mono'
        self.monorunner = 'mono'

    def get_always_args(self):
        return []

    def get_output_args(self, fname):
        return ['-out:' + fname]

    def get_linker_always_args(self):
        return []

    def get_link_args(self, fname):
        return ['-r:' + fname]

    def get_soname_args(self, shlib_name, path, soversion):
        return []

    def get_werror_args(self):
        return ['-warnaserror']

    def split_shlib_to_parts(self, fname):
        return (None, fname)

    def build_rpath_args(self, build_dir, rpath_paths, install_rpath):
        return []

    def get_id(self):
        return self.id

    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def get_language(self):
        return self.language

    def get_default_suffix(self):
        return self.default_suffix

    def get_exelist(self):
        return self.exelist[:]

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_compile_only_args(self):
        return []

    def get_linker_output_args(self, outputname):
        return []

    def get_coverage_args(self):
        return []

    def get_coverage_link_args(self):
        return []

    def get_std_exe_link_args(self):
        return []

    def get_include_args(self, path):
        return []

    def get_std_shared_lib_link_args(self):
        return []

    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        if suffix == 'cs':
            return True
        return False

    def get_pic_args(self):
        return []

    def name_string(self):
        return ' '.join(self.exelist)

    def get_pch_use_args(self, pch_dir, header):
        return []

    def get_pch_name(self, header_name):
        return ''

    def sanity_check(self, work_dir):
        src = 'sanity.cs'
        obj = 'sanity.exe'
        source_name = os.path.join(work_dir, src)
        ofile = open(source_name, 'w')
        ofile.write('''public class Sanity {
    static public void Main () {
    }
}
''')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [src], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Mono compiler %s can not compile programs.' % self.name_string())
        cmdlist = [self.monorunner, obj]
        pe = subprocess.Popen(cmdlist, cwd=work_dir)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by Mono compiler %s are not runnable.' % self.name_string())

    def needs_static_linker(self):
        return False

    def has_header(self, hname):
        raise EnvironmentException('Mono does not support header checks.')

    def compiles(self, code):
        raise EnvironmentException('Mono does not support compile checks.')

    def run(self, code):
        raise EnvironmentException('Mono does not support run checks.')

    def sizeof(self, element, prefix, env):
        raise EnvironmentException('Mono does not support sizeof checks.')

    def alignment(self, typename, env):
        raise EnvironmentException('Mono does not support alignment checks.')

    def has_function(self, funcname, prefix, env):
        raise EnvironmentException('Mono does not support function checks.')

    def get_buildtype_args(self, buildtype):
        return mono_buildtype_args[buildtype]

class JavaCompiler():
    def __init__(self, exelist, version):
        if type(exelist) == type(''):
            self.exelist = [exelist]
        elif type(exelist) == type([]):
            self.exelist = exelist
        else:
            raise TypeError('Unknown argument to JavaCompiler')
        self.version = version
        self.language = 'java'
        self.default_suffix = 'java'
        self.id = 'unknown'
        self.javarunner = 'java'

    def get_always_args(self):
        return []

    def get_linker_always_args(self):
        return []

    def get_soname_args(self, shlib_name, path, soversion):
        return []

    def get_werror_args(self):
        return ['-Werror']

    def split_shlib_to_parts(self, fname):
        return (None, fname)

    def build_rpath_args(self, build_dir, rpath_paths, install_rpath):
        return []

    def get_id(self):
        return self.id

    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def get_language(self):
        return self.language

    def get_default_suffix(self):
        return self.default_suffix

    def get_exelist(self):
        return self.exelist[:]

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_compile_only_args(self):
        return []

    def get_output_args(self, subdir):
        if subdir == '':
            subdir = './'
        return ['-d', subdir, '-s', subdir]

    def get_linker_output_args(self, outputname):
        return []

    def get_coverage_args(self):
        return []

    def get_coverage_link_args(self):
        return []

    def get_std_exe_link_args(self):
        return []

    def get_include_args(self, path):
        return []

    def get_std_shared_lib_link_args(self):
        return []

    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        if suffix == 'java':
            return True
        return False

    def get_pic_args(self):
        return []

    def name_string(self):
        return ' '.join(self.exelist)

    def get_pch_use_args(self, pch_dir, header):
        return []

    def get_pch_name(self, header_name):
        return ''

    def get_buildtype_args(self, buildtype):
        return java_buildtype_args[buildtype]

    def sanity_check(self, work_dir):
        src = 'SanityCheck.java'
        obj = 'SanityCheck'
        source_name = os.path.join(work_dir, src)
        ofile = open(source_name, 'w')
        ofile.write('''class SanityCheck {
  public static void main(String[] args) {
    int i;
  }
}
''')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [src], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Java compiler %s can not compile programs.' % self.name_string())
        cmdlist = [self.javarunner, obj]
        pe = subprocess.Popen(cmdlist, cwd=work_dir)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by Java compiler %s are not runnable.' % self.name_string())

    def needs_static_linker(self):
        return False

    def has_header(self, hname):
        raise EnvironmentException('Java does not support header checks.')

    def compiles(self, code):
        raise EnvironmentException('Java does not support compile checks.')

    def run(self, code):
        raise EnvironmentException('Java does not support run checks.')

    def sizeof(self, element, prefix, env):
        raise EnvironmentException('Java does not support sizeof checks.')

    def alignment(self, typename, env):
        raise EnvironmentException('Java does not support alignment checks.')

    def has_function(self, funcname, prefix, env):
        raise EnvironmentException('Java does not support function checks.')

class ValaCompiler():
    def __init__(self, exelist, version):
        if isinstance(exelist, str):
            self.exelist = [exelist]
        elif type(exelist) == type([]):
            self.exelist = exelist
        else:
            raise TypeError('Unknown argument to Vala compiler')
        self.version = version
        self.id = 'unknown'
        self.language = 'vala'

    def name_string(self):
        return ' '.join(self.exelist)

    def needs_static_linker(self):
        return False # Because compiles into C.

    def get_exelist(self):
        return self.exelist

    def get_werror_args(self):
        return ['--fatal-warnings']

    def get_language(self):
        return self.language

    def sanity_check(self, work_dir):
        src = 'valatest.vala'
        source_name = os.path.join(work_dir, src)
        ofile = open(source_name, 'w')
        ofile.write('''class SanityCheck : Object {
}
''')
        ofile.close()
        pc = subprocess.Popen(self.exelist + ['-C', '-c', src], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Vala compiler %s can not compile programs.' % self.name_string())

    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        return suffix in ('vala', 'vapi')

class RustCompiler():
    def __init__(self, exelist, version):
        if isinstance(exelist, str):
            self.exelist = [exelist]
        elif type(exelist) == type([]):
            self.exelist = exelist
        else:
            raise TypeError('Unknown argument to Rust compiler')
        self.version = version
        self.id = 'unknown'
        self.language = 'rust'

    def needs_static_linker(self):
        return False

    def name_string(self):
        return ' '.join(self.exelist)

    def get_exelist(self):
        return self.exelist

    def get_id(self):
        return self.id

    def get_language(self):
        return self.language

    def sanity_check(self, work_dir):
        source_name = os.path.join(work_dir, 'sanity.rs')
        output_name = os.path.join(work_dir, 'rusttest')
        ofile = open(source_name, 'w')
        ofile.write('''fn main() {
}
''')
        ofile.close()
        pc = subprocess.Popen(self.exelist + ['-o', output_name, source_name], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Rust compiler %s can not compile programs.' % self.name_string())
        if subprocess.call(output_name) != 0:
            raise EnvironmentException('Executables created by Rust compiler %s are not runnable.' % self.name_string())

    def can_compile(self, fname):
        return fname.endswith('.rs')

    def get_dependency_gen_args(self, outfile):
        return ['--dep-info', outfile]

    def get_buildtype_args(self, buildtype):
        return rust_buildtype_args[buildtype]

class VisualStudioCCompiler(CCompiler):
    std_warn_args = ['/W3']
    std_opt_args= ['/O2']
    vs2010_always_args = ['/nologo', '/showIncludes']
    vs2013_always_args = ['/nologo', '/showIncludes', '/FS']

    def __init__(self, exelist, version, is_cross, exe_wrap):
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        self.id = 'msvc'
        if int(version.split('.')[0]) > 17:
            self.always_args = VisualStudioCCompiler.vs2013_always_args
        else:
            self.always_args = VisualStudioCCompiler.vs2010_always_args

    def get_always_args(self):
        return self.always_args

    def get_std_warn_args(self):
        return self.std_warn_args

    def get_buildtype_args(self, buildtype):
        return msvc_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return msvc_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'pch'

    def get_pch_name(self, header):
        chopped = os.path.split(header)[-1].split('.')[:-1]
        chopped.append(self.get_pch_suffix())
        pchname = '.'.join(chopped)
        return pchname

    def get_pch_use_args(self, pch_dir, header):
        base = os.path.split(header)[-1]
        pchname = self.get_pch_name(header)
        return ['/FI' + base, '/Yu' + base, '/Fp' + os.path.join(pch_dir, pchname)]

    def get_compile_only_args(self):
        return ['/c']

    def get_output_args(self, target):
        if target.endswith('.exe'):
            return ['/Fe' + target]
        return ['/Fo' + target]

    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def get_linker_exelist(self):
        return ['link'] # FIXME, should have same path as compiler.

    def get_linker_always_args(self):
        return ['/nologo']

    def get_linker_output_args(self, outputname):
        return ['/OUT:' + outputname]

    def get_pic_args(self):
        return ['/LD']

    def get_std_shared_lib_link_args(self):
        return ['/DLL']

    def gen_pch_args(self, header, source, pchname):
        objname = os.path.splitext(pchname)[0] + '.obj'
        return (objname, ['/Yc' + header, '/Fp' + pchname, '/Fo' + objname ])

    def sanity_check(self, work_dir):
        source_name = 'sanitycheckc.c'
        binary_name = 'sanitycheckc'
        ofile = open(os.path.join(work_dir, source_name), 'w')
        ofile.write('int main(int argc, char **argv) { return 0; }\n')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '/Fe' + binary_name],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL,
                              cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Compiler %s can not compile programs.' % self.name_string())
        pe = subprocess.Popen(os.path.join(work_dir, binary_name))
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by C++ compiler %s are not runnable.' % self.name_string())

    def build_rpath_args(self, build_dir, rpath_paths, install_rpath):
        return []

    # FIXME, no idea what these should be.
    def thread_flags(self):
        return []

    def thread_link_flags(self):
        return []

class VisualStudioCPPCompiler(VisualStudioCCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrap):
        VisualStudioCCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        self.language = 'cpp'
        self.default_suffix = 'cpp'

    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        if suffix in cpp_suffixes:
            return True
        return False

    def sanity_check(self, work_dir):
        source_name = 'sanitycheckcpp.cpp'
        binary_name = 'sanitycheckcpp'
        ofile = open(os.path.join(work_dir, source_name), 'w')
        ofile.write('class BreakPlainC;int main(int argc, char **argv) { return 0; }\n')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '/Fe' + binary_name],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL,
                              cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Compiler %s can not compile programs.' % self.name_string())
        pe = subprocess.Popen(os.path.join(work_dir, binary_name))
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by C++ compiler %s are not runnable.' % self.name_string())

GCC_STANDARD = 0
GCC_OSX = 1
GCC_MINGW = 2

def get_gcc_soname_args(gcc_type, shlib_name, path, soversion):
    if soversion is None:
        sostr = ''
    else:
        sostr = '.' + soversion
    if gcc_type == GCC_STANDARD:
        return ['-Wl,-soname,lib%s.so%s' % (shlib_name, sostr)]
    elif gcc_type == GCC_OSX:
        return ['-install_name', os.path.join(path, 'lib' + shlib_name + '.dylib')]
    else:
        raise RuntimeError('Not implemented yet.')

class GnuCCompiler(CCompiler):
    old_warn = ['-Wall', '-pedantic', '-Winvalid-pch']
    new_warn = ['-Wall', '-Wpedantic', '-Winvalid-pch']

    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrapper=None):
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        self.id = 'gcc'
        self.gcc_type = gcc_type
        if mesonlib.version_compare(version, ">=4.9.0"):
            self.warn_args= GnuCCompiler.new_warn
        else:
            self.warn_args = GnuCCompiler.old_warn

    def get_always_args(self):
        return ['-pipe']

    def get_std_warn_args(self):
        return self.warn_args

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return gnulike_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'gch'

    def split_shlib_to_parts(self, fname):
        return (os.path.split(fname)[0], fname)

    def get_soname_args(self, shlib_name, path, soversion):
        return get_gcc_soname_args(self.gcc_type, shlib_name, path, soversion)

    def can_compile(self, filename):
        return super().can_compile(filename) or filename.split('.')[-1].lower() == 's' # Gcc can do asm, too.

class GnuObjCCompiler(ObjCCompiler):
    std_warn_args = ['-Wall', '-Wpedantic', '-Winvalid-pch']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        ObjCCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        self.id = 'gcc'
        # Not really correct, but GNU objc is only used on non-OSX non-win. File a bug
        # if this breaks your use case.
        self.gcc_type = GCC_STANDARD

    def get_std_warn_args(self):
        return GnuObjCCompiler.std_warn_args

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return gnulike_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'gch'

    def get_soname_args(self, shlib_name, path, soversion):
        return get_gcc_soname_args(self.gcc_type, shlib_name, path, soversion)

class GnuObjCPPCompiler(ObjCPPCompiler):
    std_warn_args = ['-Wall', '-Wpedantic', '-Winvalid-pch']
    std_opt_args = ['-O2']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        ObjCCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        self.id = 'gcc'
        # Not really correct, but GNU objc is only used on non-OSX non-win. File a bug
        # if this breaks your use case.
        self.gcc_type = GCC_STANDARD

    def get_std_warn_args(self):
        return GnuObjCPPCompiler.std_warn_args

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return gnulike_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'gch'

    def get_soname_args(self, shlib_name, path, soversion):
        return get_gcc_soname_args(self.gcc_type, shlib_name, path, soversion)

class ClangObjCCompiler(GnuObjCCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper)
        self.id = 'clang'

class ClangObjCPPCompiler(GnuObjCPPCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper)
        self.id = 'clang'

class ClangCCompiler(CCompiler):
    std_warn_args = ['-Wall', '-Wpedantic', '-Winvalid-pch']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        self.id = 'clang'

    def get_std_warn_args(self):
        return ClangCCompiler.std_warn_args

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return gnulike_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'pch'

    def can_compile(self, filename):
        return super().can_compile(filename) or filename.split('.')[-1].lower() == 's' # Clang can do asm, too.

    def get_pch_use_args(self, pch_dir, header):
        # Workaround for Clang bug http://llvm.org/bugs/show_bug.cgi?id=15136
        # This flag is internal to Clang (or at least not documented on the man page)
        # so it might change semantics at any time.
        return ['-include-pch', os.path.join (pch_dir, self.get_pch_name (header))]


class GnuCPPCompiler(CPPCompiler):
    new_warn = ['-Wall', '-Wpedantic', '-Winvalid-pch', '-Wnon-virtual-dtor']
    old_warn = ['-Wall', '-pedantic', '-Winvalid-pch', '-Wnon-virtual-dtor']
    # may need to separate the latter to extra_debug_args or something
    std_debug_args = ['-g']

    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrap):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        self.id = 'gcc'
        self.gcc_type = gcc_type
        if mesonlib.version_compare(version, ">=4.9.0"):
            self.warn_args= GnuCPPCompiler.new_warn
        else:
            self.warn_args = GnuCPPCompiler.old_warn

    def get_always_args(self):
        return ['-pipe']

    def get_std_warn_args(self):
        return self.warn_args

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return gnulike_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'gch'

    def get_soname_args(self, shlib_name, path, soversion):
        return get_gcc_soname_args(self.gcc_type, shlib_name, path, soversion)

class ClangCPPCompiler(CPPCompiler):
    std_warn_args = ['-Wall', '-Wpedantic', '-Winvalid-pch', '-Wnon-virtual-dtor']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        self.id = 'clang'

    def get_std_warn_args(self):
        return ClangCPPCompiler.std_warn_args

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return gnulike_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'pch'

    def get_pch_use_args(self, pch_dir, header):
        # Workaround for Clang bug http://llvm.org/bugs/show_bug.cgi?id=15136
        # This flag is internal to Clang (or at least not documented on the man page)
        # so it might change semantics at any time.
        return ['-include-pch', os.path.join (pch_dir, self.get_pch_name (header))]

class FortranCompiler():
    std_warn_args = ['-Wall']

    def __init__(self, exelist, version,is_cross, exe_wrapper=None):
        super().__init__()
        self.exelist = exelist
        self.version = version
        self.is_cross = is_cross
        self.exe_wrapper = exe_wrapper
        self.language = 'fortran'
        # Not really correct but I don't have Fortran compilers to test with. Sorry.
        self.gcc_type = GCC_STANDARD
        self.id = "IMPLEMENTATION CLASSES MUST SET THIS"

    def get_id(self):
        return self.id

    def name_string(self):
        return ' '.join(self.exelist)

    def get_exelist(self):
        return self.exelist

    def get_language(self):
        return self.language

    def needs_static_linker(self):
        return True

    def sanity_check(self, work_dir):
        source_name = os.path.join(work_dir, 'sanitycheckf.f90')
        binary_name = os.path.join(work_dir, 'sanitycheckf')
        ofile = open(source_name, 'w')
        ofile.write('''program prog
     print *, "Fortran compilation is working."
end program prog
''')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Compiler %s can not compile programs.' % self.name_string())
        if self.is_cross:
            if self.exe_wrapper is None:
                # Can't check if the binaries run so we have to assume they do
                return
            cmdlist = self.exe_wrapper + [binary_name]
        else:
            cmdlist = [binary_name]
        pe = subprocess.Popen(cmdlist, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by Fortran compiler %s are not runnable.' % self.name_string())

    def get_always_args(self):
        return ['-pipe']

    def get_linker_always_args(self):
        return []

    def get_std_warn_args(self):
        return FortranCompiler.std_warn_args

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return gnulike_buildtype_linker_args[buildtype]

    def split_shlib_to_parts(self, fname):
        return (os.path.split(fname)[0], fname)

    def get_soname_args(self, shlib_name, path, soversion):
        return get_gcc_soname_args(self.gcc_type, shlib_name, path, soversion)

    def get_dependency_gen_args(self, outtarget, outfile):
        # Disabled until this is fixed:
        # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=62162
        #return ['-cpp', '-MMD', '-MQ', outtarget]
        return []

    def get_output_args(self, target):
        return ['-o', target]

    def get_compile_only_args(self):
        return ['-c']

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_linker_output_args(self, outputname):
        return ['-o', outputname]

    def can_compile(self, src):
        if hasattr(src, 'fname'):
            src = src.fname
        suffix = os.path.splitext(src)[1].lower()
        if suffix == '.f' or suffix == '.f95' or suffix == '.f90':
            return True
        return False

    def get_include_args(self, path):
        return ['-I' + path]

    def get_module_outdir_args(self, path):
        return ['-J' + path]

    def get_depfile_suffix(self):
        return 'd'

    def get_std_exe_link_args(self):
        return []

    def build_rpath_args(self, build_dir, rpath_paths, install_rpath):
        return build_unix_rpath_args(build_dir, rpath_paths, install_rpath)

    def module_name_to_filename(self, module_name):
        return module_name.lower() + '.mod'

class GnuFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.gcc_type = gcc_type
        self.id = 'gcc'

class G95FortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'g95'

    def get_module_outdir_args(self, path):
        return ['-fmod='+path]

class SunFortranCompiler(FortranCompiler):
    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'sun'

    def get_dependency_gen_args(self, outtarget, outfile):
        return ['-fpp']

    def get_always_args(self):
        return []

    def get_std_warn_args(self):
        return []

    def get_module_outdir_args(self, path):
        return ['-moddir='+path]

class IntelFortranCompiler(FortranCompiler):
    std_warn_args = ['-warn', 'all']
    
    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'intel'
        
    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_always_args(self):
        return []

    def can_compile(self, src):
        suffix = os.path.splitext(src)[1].lower()
        if suffix == '.f' or suffix == '.f90':
            return True
        return False

    def get_std_warn_args(self):
        return IntelFortranCompiler.std_warn_args

class PathScaleFortranCompiler(FortranCompiler):
    std_warn_args = ['-fullwarn']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'pathscale'

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_always_args(self):
        return []

    def can_compile(self, src):
        suffix = os.path.splitext(src)[1].lower()
        if suffix == '.f' or suffix == '.f90' or suffix == '.f95':
            return True
        return False

    def get_std_warn_args(self):
        return PathScaleFortranCompiler.std_warn_args

class PGIFortranCompiler(FortranCompiler):
    std_warn_args = ['-Minform=inform']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'pgi'

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_always_args(self):
        return []

    def can_compile(self, src):
        suffix = os.path.splitext(src)[1].lower()
        if suffix == '.f' or suffix == '.f90' or suffix == '.f95':
            return True
        return False

    def get_std_warn_args(self):
        return PGIFortranCompiler.std_warn_args


class Open64FortranCompiler(FortranCompiler):
    std_warn_args = ['-fullwarn']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'open64'

    def get_module_outdir_args(self, path):
        return ['-module', path]

    def get_always_args(self):
        return []

    def can_compile(self, src):
        suffix = os.path.splitext(src)[1].lower()
        if suffix == '.f' or suffix == '.f90' or suffix == '.f95':
            return True
        return False

    def get_std_warn_args(self):
        return Open64FortranCompiler.std_warn_args

class NAGFortranCompiler(FortranCompiler):
    std_warn_args = []

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        super().__init__(exelist, version, is_cross, exe_wrapper=None)
        self.id = 'nagfor'

    def get_module_outdir_args(self, path):
        return ['-mdir', path]

    def get_always_args(self):
        return []

    def can_compile(self, src):
        suffix = os.path.splitext(src)[1].lower()
        if suffix == '.f' or suffix == '.f90' or suffix == '.f95':
            return True
        return False

    def get_std_warn_args(self):
        return NAGFortranCompiler.std_warn_args


class VisualStudioLinker():
    always_args = ['/NOLOGO']
    def __init__(self, exelist):
        self.exelist = exelist

    def get_exelist(self):
        return self.exelist

    def get_std_link_args(self):
        return []

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_output_args(self, target):
        return ['/OUT:' + target]

    def get_coverage_link_args(self):
        return []

    def get_always_args(self):
        return VisualStudioLinker.always_args

    def get_linker_always_args(self):
        return VisualStudioLinker.always_args

    def build_rpath_args(self, build_dir, rpath_paths, install_rpath):
        return []

    def thread_link_flags(self):
        return []

class ArLinker():
    std_args = ['csr']

    def __init__(self, exelist):
        self.exelist = exelist
        self.id = 'ar'

    def build_rpath_args(self, build_dir, rpath_paths, install_rpath):
        return []

    def get_exelist(self):
        return self.exelist

    def get_std_link_args(self):
        return self.std_args

    def get_output_args(self, target):
        return [target]

    def get_buildtype_linker_args(self, buildtype):
        return []

    def get_linker_always_args(self):
        return []

    def get_coverage_link_args(self):
        return []

    def get_always_args(self):
        return []

    def thread_link_flags(self):
        return []
