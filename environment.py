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

import subprocess, os.path, platform, re
import coredata
from glob import glob
import tempfile
from coredata import MesonException

build_filename = 'meson.build'

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

gnulike_buildtype_args = {'plain' : [],
                           'debug' : ['-g'],
                           'debugoptimized' : ['-O2', '-g'],
                           'release' : ['-O3'],
                           }

msvc_buildtype_args = {'plain' : [],
                        'debug' : ["/MDd", "/Zi", "/Ob0", "/Od", "/RTC1"],
                        'debugoptimized' : ["/MD", "/Zi", "/O2", "/Ob1", "/D"],
                        'release' : ["/MD", "/O2", "/Ob2"]}

gnulike_buildtype_linker_args = {'plain' : [],
                                  'debug' : [],
                                  'debugoptimized' : [],
                                  'release' : ['-Wl,-O1'],
                                  }

msvc_buildtype_linker_args = {'plain' : [],
                               'debug' : [],
                               'debugoptimized' : [],
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

    def get_soname_args(self, shlib_name, path):
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

    def get_debug_args(self):
        return ['-g']

    def get_coverage_args(self):
        return ['--coverage']

    def get_coverage_link_args(self):
        return ['-lgcov']

    def get_werror_args(self):
        return ['-Werror']

    def get_std_exe_link_args(self):
        return []

    def get_include_arg(self, path):
        return '-I' + path

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
        suflen = len(self.default_suffix)
        (fd, srcname) = tempfile.mkstemp(suffix='.'+self.default_suffix)
        os.close(fd)
        ofile = open(srcname, 'w')
        ofile.write(code)
        ofile.close()
        commands = self.get_exelist()
        commands += self.get_compile_only_args()
        commands.append(srcname)
        p = subprocess.Popen(commands, cwd=os.path.split(srcname)[0], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.communicate()
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
        p = subprocess.Popen(commands, cwd=os.path.split(srcname)[0], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.communicate()
        os.remove(srcname)
        if p.returncode != 0:
            return RunResult(False)
        if self.is_cross:
            cmdlist = self.exe_wrapper + [exename]
        else:
            cmdlist = exename
        pe = subprocess.Popen(cmdlist, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (so, se) = pe.communicate()
        os.remove(exename)
        return RunResult(True, pe.returncode, so.decode(), se.decode())

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
            val = env.cross_info.get(varname)
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
            val = env.cross_info.get(varname)
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
            val = env.cross_info.get(varname)
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

    def get_soname_args(self, shlib_name, path):
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

    def get_debug_args(self):
        return ['-g']

    def get_coverage_args(self):
        return []

    def get_coverage_link_args(self):
        return []

    def get_std_exe_link_args(self):
        return []

    def get_include_arg(self, path):
        return ''

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

    def get_soname_args(self, shlib_name, path):
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

    def get_debug_args(self):
        return ['-g']

    def get_coverage_args(self):
        return []

    def get_coverage_link_args(self):
        return []

    def get_std_exe_link_args(self):
        return []

    def get_include_arg(self, path):
        return ''

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
        obj = 'valatest.c'
        source_name = os.path.join(work_dir, src)
        ofile = open(source_name, 'w')
        ofile.write('''class SanityCheck : Object {
}
''')
        ofile.close()
        pc = subprocess.Popen(self.exelist + ['-C', '-o', obj, src], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Vala compiler %s can not compile programs.' % self.name_string())

    def can_compile(self, fname):
        return fname.endswith('.vala')

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
    always_args = ['/nologo', '/showIncludes']

    def __init__(self, exelist, version, is_cross, exe_wrap):
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        self.id = 'msvc'

    def get_always_args(self):
        return VisualStudioCCompiler.always_args

    def get_std_warn_args(self):
        return VisualStudioCCompiler.std_warn_args

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

    def get_debug_args(self):
        return ['/D_DEBUG', '/Zi', '/MDd', '/Ob0', '/RTC1']

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
        return ['/Yc' + header, '/Fp' + pchname]

    def sanity_check(self, work_dir):
        source_name = os.path.join(work_dir, 'sanitycheckc.c')
        binary_name = os.path.join(work_dir, 'sanitycheckc')
        ofile = open(source_name, 'w')
        ofile.write('int main(int argc, char **argv) { return 0; }\n')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '/Fe' + binary_name],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Compiler %s can not compile programs.' % self.name_string())
        pe = subprocess.Popen(binary_name)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by C++ compiler %s are not runnable.' % self.name_string())

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
        source_name = os.path.join(work_dir, 'sanitycheckcpp.cpp')
        binary_name = os.path.join(work_dir, 'sanitycheckcpp')
        ofile = open(source_name, 'w')
        ofile.write('class BreakPlainC;int main(int argc, char **argv) { return 0; }\n')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '/Fe' + binary_name],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Compiler %s can not compile programs.' % self.name_string())
        pe = subprocess.Popen(binary_name)
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
        raise RuntimeError('Not impelented yet.')

class GnuCCompiler(CCompiler):
    std_warn_args = ['-Wall', '-Winvalid-pch']

    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrapper=None):
        CCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        self.id = 'gcc'
        self.gcc_type = gcc_type

    def get_always_args(self):
        return ['-pipe']

    def get_std_warn_args(self):
        return GnuCCompiler.std_warn_args

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

class GnuObjCCompiler(ObjCCompiler):
    std_warn_args = ['-Wall', '-Winvalid-pch']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        ObjCCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        self.id = 'gcc'

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
    std_warn_args = ['-Wall', '-Winvalid-pch']
    std_opt_args = ['-O2']

    def __init__(self, exelist, version, is_cross, exe_wrapper=None):
        ObjCCompiler.__init__(self, exelist, version, is_cross, exe_wrapper)
        self.id = 'gcc'

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
    std_warn_args = ['-Wall', '-Winvalid-pch']

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

class GnuCPPCompiler(CPPCompiler):
    std_warn_args = ['-Wall', '-Winvalid-pch']
    # may need to separate the latter to extra_debug_args or something
    std_debug_args = ['-g']

    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrap):
        CPPCompiler.__init__(self, exelist, version, is_cross, exe_wrap)
        self.id = 'gcc'
        self.gcc_type = gcc_type

    def get_always_args(self):
        return ['-pipe']

    def get_debug_args(self):
        return GnuCPPCompiler.std_debug_args

    def get_std_warn_args(self):
        return GnuCPPCompiler.std_warn_args

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return gnulike_buildtype_linker_args[buildtype]

    def get_pch_suffix(self):
        return 'gch'

    def get_soname_args(self, shlib_name, path, soversion):
        return get_gcc_soname_args(self.gcc_type, shlib_name, path, soversion)

class ClangCPPCompiler(CPPCompiler):
    std_warn_args = ['-Wall', '-Winvalid-pch']

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

class GnuFortranCompiler():
    std_warn_args = ['-Wall']

    def __init__(self, exelist, version, gcc_type, is_cross, exe_wrapper=None):
        super().__init__()
        self.exelist = exelist
        self.version = version
        self.gcc_type = gcc_type
        self.is_cross = is_cross
        self.exe_wrapper = exe_wrapper
        self.id = 'gcc'
        self.language = 'fortran'

    def get_id(self):
        return self.id

    def get_exelist(self):
        return self.exelist

    def get_language(self):
        return self.language

    def needs_static_linker(self):
        return True

    def sanity_check(self, work_dir):
        source_name = os.path.join(work_dir, 'sanitycheckf.f95')
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
        return GnuFortranCompiler.std_warn_args

    def get_buildtype_args(self, buildtype):
        return gnulike_buildtype_args[buildtype]

    def get_buildtype_linker_args(self, buildtype):
        return gnulike_buildtype_linker_args[buildtype]

    def split_shlib_to_parts(self, fname):
        return (os.path.split(fname)[0], fname)

    def get_soname_args(self, shlib_name, path, soversion):
        return get_gcc_soname_args(self.gcc_type, shlib_name, path, soversion)

    def get_dependency_gen_args(self, outtarget, outfile):
        return ['-cpp', '-MMD', '-MQ', outtarget]

    def get_output_args(self, target):
        return ['-o', target]

    def get_compile_only_args(self):
        return ['-c']

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_linker_output_args(self, outputname):
        return ['-o', outputname]

    def can_compile(self, src):
        suffix = os.path.splitext(src)[1].lower()
        if suffix == '.f' or suffix == '.f95':
            return True
        return False

    def get_include_arg(self, path):
        return '-I' + path

    def get_depfile_suffix(self):
        return 'd'

    def get_std_exe_link_args(self):
        return []

    def build_rpath_args(self, build_dir, rpath_paths, install_rpath):
        return build_unix_rpath_args(build_dir, rpath_paths, install_rpath)

    def module_name_to_filename(self, module_name):
        return module_name.lower() + '.mod'

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

class ArLinker():
    std_args = ['csr']

    def __init__(self, exelist):
        self.exelist = exelist

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

def exe_exists(arglist):
    try:
        p = subprocess.Popen(arglist, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.communicate()
        if p.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    return False

def find_coverage_tools():
    gcovr_exe = 'gcovr'
    lcov_exe = 'lcov'
    genhtml_exe = 'genhtml'
    
    if not exe_exists([gcovr_exe, '--version']):
        gcovr_exe = None
    if not exe_exists([lcov_exe, '--version']):
        lcov_exe = None
    if not exe_exists([genhtml_exe, '--version']):
        genhtml_exe = None
    return (gcovr_exe, lcov_exe, genhtml_exe)

def find_valgrind():
    valgrind_exe = 'valgrind'
    if not exe_exists([valgrind_exe, '--version']):
        valgrind_exe = None
    return valgrind_exe

def is_osx():
    return platform.system().lower() == 'darwin'

def is_linux():
    return platform.system().lower() == 'linux'

def is_windows():
    return platform.system().lower() == 'windows'

def is_debianlike():
    try:
        open('/etc/debian_version', 'r')
        return True
    except FileNotFoundError:
        return False

def detect_ninja():
    for n in ['ninja', 'ninja-build']:
        # Plain 'ninja' or 'ninja -h' yields an error
        # code. Thanks a bunch, guys.
        try:
            p = subprocess.Popen([n, '-t', 'list'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            continue
        p.communicate()
        if p.returncode == 0:
            return n


header_suffixes = ['h', 'hh', 'hpp', 'hxx', 'H']
cpp_suffixes = ['cc', 'cpp', 'cxx', 'h', 'hh', 'hpp', 'hxx', 'c++']
c_suffixes = ['c']
clike_suffixes = c_suffixes + cpp_suffixes
obj_suffixes = ['o', 'obj']

def is_header(fname):
    suffix = fname.split('.')[-1]
    return suffix in header_suffixes

def is_source(fname):
    suffix = fname.split('.')[-1]
    return suffix in clike_suffixes

def is_object(fname):
    suffix = fname.split('.')[-1]
    return suffix in obj_suffixes

class Environment():
    private_dir = 'meson-private'
    log_dir = 'meson-logs'
    coredata_file = os.path.join(private_dir, 'coredata.dat')
    version_regex = '\d+(\.\d+)+(-[a-zA-Z0-9]+)?'
    def __init__(self, source_dir, build_dir, main_script_file, options):
        assert(os.path.isabs(main_script_file))
        assert(not os.path.islink(main_script_file))
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.meson_script_file = main_script_file
        self.scratch_dir = os.path.join(build_dir, Environment.private_dir)
        self.log_dir = os.path.join(build_dir, Environment.log_dir)
        os.makedirs(self.scratch_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        try:
            cdf = os.path.join(self.get_build_dir(), Environment.coredata_file)
            self.coredata = coredata.load(cdf)
        except FileNotFoundError:
            self.coredata = coredata.CoreData(options)
        if self.coredata.cross_file:
            self.cross_info = CrossBuildInfo(self.coredata.cross_file)
        else:
            self.cross_info = None

        # List of potential compilers.
        if is_windows():
            self.default_c = ['cl', 'cc']
            self.default_cpp = ['cl', 'c++']
        else:
            self.default_c = ['cc']
            self.default_cpp = ['c++']
        self.default_objc = ['cc']
        self.default_objcpp = ['c++']
        self.default_fortran = ['gfortran']
        self.default_static_linker = 'ar'
        self.vs_static_linker = 'lib'

        cross = self.is_cross_build()
        if (not cross and is_windows()) \
        or (cross and self.cross_info['name'] == 'windows'):
            self.exe_suffix = 'exe'
            self.import_lib_suffix = 'lib'
            self.shared_lib_suffix = 'dll'
            self.shared_lib_prefix = ''
            self.static_lib_suffix = 'lib'
            self.static_lib_prefix = ''
            self.object_suffix = 'obj'
        else:
            self.exe_suffix = ''
            if (not cross and is_osx()) or \
            (cross and self.cross_info['name'] == 'darwin'):
                self.shared_lib_suffix = 'dylib'
            else:
                self.shared_lib_suffix = 'so'
            self.shared_lib_prefix = 'lib'
            self.static_lib_suffix = 'a'
            self.static_lib_prefix = 'lib'
            self.object_suffix = 'o'
            self.import_lib_suffix = self.shared_lib_suffix

    def is_cross_build(self):
        return self.cross_info is not None

    def generating_finished(self):
        cdf = os.path.join(self.get_build_dir(), Environment.coredata_file)
        coredata.save(self.coredata, cdf)

    def get_script_dir(self):
        return os.path.dirname(self.meson_script_file)
    
    def get_log_dir(self):
        return self.log_dir

    def get_coredata(self):
        return self.coredata

    def get_build_command(self):
        return self.meson_script_file

    def is_header(self, fname):
        return is_header(fname)

    def is_source(self, fname):
        return is_source(fname)

    def is_object(self, fname):
        return is_object(fname)

    def merge_options(self, options):
        for (name, value) in options.items():
            if name not in self.coredata.user_options:
                self.coredata.user_options[name] = value
            else:
                oldval = self.coredata.user_options[name]
                if type(oldval) != type(value):
                    self.coredata.user_options[name] = value

    def detect_c_compiler(self, want_cross):
        evar = 'CC'
        if self.is_cross_build() and want_cross:
            compilers = [self.cross_info['c']]
            ccache = []
            is_cross = True
            exe_wrap = self.cross_info.get('exe_wrapper', None)
        elif evar in os.environ:
            compilers = os.environ[evar].split()
            ccache = []
            is_cross = False
            exe_wrap = None
        else:
            compilers = self.default_c
            ccache = self.detect_ccache()
            is_cross = False
            exe_wrap = None
        for compiler in compilers:
            try:
                basename = os.path.basename(compiler).lower() 
                if basename == 'cl' or basename == 'cl.exe':
                    arg = '/?'
                else:
                    arg = '--version'
                p = subprocess.Popen([compiler] + [arg], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            except OSError:
                continue
            (out, err) = p.communicate()
            out = out.decode()
            err = err.decode()
            vmatch = re.search(Environment.version_regex, out)
            if vmatch:
                version = vmatch.group(0)
            else:
                version = 'unknown version'
            if 'apple' in out and 'Free Software Foundation' in out:
                return GnuCCompiler(ccache + [compiler], version, GCC_OSX, is_cross, exe_wrap)
            if (out.startswith('cc') or 'gcc' in out) and \
                'Free Software Foundation' in out:
                return GnuCCompiler(ccache + [compiler], version, GCC_STANDARD, is_cross, exe_wrap)
            if 'clang' in out:
                return ClangCCompiler(ccache + [compiler], version, is_cross, exe_wrap)
            if 'Microsoft' in out:
                # Visual Studio prints version number to stderr but
                # everything else to stdout. Why? Lord only knows.
                version = re.search(Environment.version_regex, err).group()
                return VisualStudioCCompiler([compiler], version, is_cross, exe_wrap)
        raise EnvironmentException('Unknown compiler(s): "' + ', '.join(compilers) + '"')

    def detect_fortran_compiler(self, want_cross):
        evar = 'FC'
        if self.is_cross_build() and want_cross:
            compilers = [self.cross_info['fortran']]
            ccache = []
            is_cross = True
            exe_wrap = self.cross_info.get('exe_wrapper', None)
        elif evar in os.environ:
            compilers = os.environ[evar].split()
            ccache = []
            is_cross = False
            exe_wrap = None
        else:
            compilers = self.default_fortran
            ccache = self.detect_ccache()
            is_cross = False
            exe_wrap = None
        for compiler in compilers:
            try:
                arg = '--version'
                p = subprocess.Popen([compiler] + [arg], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            except OSError:
                continue
            (out, err) = p.communicate()
            out = out.decode()
            err = err.decode()
            vmatch = re.search(Environment.version_regex, out)
            if vmatch:
                version = vmatch.group(0)
            else:
                version = 'unknown version'
            if 'GNU Fortran' in out:
                gcc_type = GCC_STANDARD
                return GnuFortranCompiler([compiler], version, gcc_type, is_cross, exe_wrap)
        raise EnvironmentException('Unknown compiler(s): "' + ', '.join(compilers) + '"')

    def get_scratch_dir(self):
        return self.scratch_dir

    def get_depfixer(self):
        path = os.path.split(__file__)[0]
        return os.path.join(path, 'depfixer.py')

    def detect_cpp_compiler(self, want_cross):
        evar = 'CXX'
        if self.is_cross_build() and want_cross:
            compilers = [self.cross_info['cpp']]
            ccache = []
            is_cross = True
            exe_wrap = self.cross_info.get('exe_wrapper', None)
        elif evar in os.environ:
            compilers = os.environ[evar].split()
            ccache = []
            is_cross = False
            exe_wrap = None
        else:
            compilers = self.default_cpp
            ccache = self.detect_ccache()
            is_cross = False
            exe_wrap = None
        for compiler in compilers:
            basename = os.path.basename(compiler).lower() 
            if basename == 'cl' or basename == 'cl.exe':
                arg = '/?'
            else:
                arg = '--version'
            try:
                p = subprocess.Popen([compiler, arg],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            except OSError:
                continue
            (out, err) = p.communicate()
            out = out.decode()
            err = err.decode()
            vmatch = re.search(Environment.version_regex, out)
            if vmatch:
                version = vmatch.group(0)
            else:
                version = 'unknown version'
            if 'apple' in out and 'Free Software Foundation' in out:
                return GnuCPPCompiler(ccache + [compiler], version, GCC_OSX, is_cross, exe_wrap)
            if (out.startswith('c++ ') or 'g++' in out or 'GCC' in out) and \
                'Free Software Foundation' in out:
                return GnuCPPCompiler(ccache + [compiler], version, GCC_STANDARD, is_cross, exe_wrap)
            if 'clang' in out:
                return ClangCPPCompiler(ccache + [compiler], version, is_cross, exe_wrap)
            if 'Microsoft' in out:
                version = re.search(Environment.version_regex, err).group()
                return VisualStudioCPPCompiler([compiler], version, is_cross, exe_wrap)
        raise EnvironmentException('Unknown compiler(s) "' + ', '.join(compilers) + '"')

    def detect_objc_compiler(self, want_cross):
        if self.is_cross_build() and want_cross:
            exelist = [self.cross_info['objc']]
            is_cross = True
            exe_wrap = self.cross_info.get('exe_wrapper', None)
        else:
            exelist = self.get_objc_compiler_exelist()
            is_cross = False
            exe_wrap = None
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute ObjC compiler "%s"' % ' '.join(exelist))
        (out, err) = p.communicate()
        out = out.decode()
        err = err.decode()
        vmatch = re.search(Environment.version_regex, out)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if (out.startswith('cc ') or 'gcc' in out) and \
            'Free Software Foundation' in out:
            return GnuObjCCompiler(exelist, version, is_cross, exe_wrap)
        if out.startswith('Apple LLVM'):
            return ClangObjCCompiler(exelist, version, is_cross, exe_wrap)
        if 'apple' in out and 'Free Software Foundation' in out:
            return GnuObjCCompiler(exelist, version, is_cross, exe_wrap)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_objcpp_compiler(self, want_cross):
        if self.is_cross_build() and want_cross:
            exelist = [self.cross_info['objcpp']]
            is_cross = True
            exe_wrap = self.cross_info.get('exe_wrapper', None)
        else:
            exelist = self.get_objcpp_compiler_exelist()
            is_cross = False
            exe_wrap = None
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute ObjC++ compiler "%s"' % ' '.join(exelist))
        (out, err) = p.communicate()
        out = out.decode()
        err = err.decode()
        vmatch = re.search(Environment.version_regex, out)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if (out.startswith('c++ ') or out.startswith('g++')) and \
            'Free Software Foundation' in out:
            return GnuObjCPPCompiler(exelist, version, is_cross, exe_wrap)
        if out.startswith('Apple LLVM'):
            return ClangObjCPPCompiler(exelist, version, is_cross, exe_wrap)
        if 'apple' in out and 'Free Software Foundation' in out:
            return GnuObjCPPCompiler(exelist, version, is_cross, exe_wrap)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_java_compiler(self):
        exelist = ['javac']
        try:
            p = subprocess.Popen(exelist + ['-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute Java compiler "%s"' % ' '.join(exelist))
        (out, err) = p.communicate()
        out = out.decode()
        err = err.decode()
        vmatch = re.search(Environment.version_regex, err)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if 'javac' in err:
            return JavaCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_cs_compiler(self):
        exelist = ['mcs']
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute C# compiler "%s"' % ' '.join(exelist))
        (out, err) = p.communicate()
        out = out.decode()
        err = err.decode()
        vmatch = re.search(Environment.version_regex, out)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if 'Mono' in out:
            return MonoCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_vala_compiler(self):
        exelist = ['valac']
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute Vala compiler "%s"' % ' '.join(exelist))
        (out, _) = p.communicate()
        out = out.decode()
        vmatch = re.search(Environment.version_regex, out)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if 'Vala' in out:
            return ValaCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_rust_compiler(self):
        exelist = ['rustc']
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute Rust compiler "%s"' % ' '.join(exelist))
        (out, _) = p.communicate()
        out = out.decode()
        vmatch = re.search(Environment.version_regex, out)
        if vmatch:
            version = vmatch.group(0)
        else:
            version = 'unknown version'
        if 'rustc' in out:
            return RustCompiler(exelist, version)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_static_linker(self, compiler):
        if compiler.is_cross:
            linker = self.cross_info['ar']
        else:
            evar = 'AR'
            if evar in os.environ:
                linker = os.environ[evar].strip()
            if isinstance(compiler, VisualStudioCCompiler):
                linker= self.vs_static_linker
            else:
                linker = self.default_static_linker
        basename = os.path.basename(linker).lower()
        if basename == 'lib' or basename == 'lib.exe':
            arg = '/?'
        else:
            arg = '--version'
        try:
            p = subprocess.Popen([linker, arg], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute static linker "%s".' % linker)
        (out, err) = p.communicate()
        out = out.decode()
        err = err.decode()
        if '/OUT:' in out or '/OUT:' in err:
            return VisualStudioLinker([linker])
        if p.returncode == 0:
            return ArLinker([linker])
        if p.returncode == 1 and err.startswith('usage'): # OSX
            return ArLinker([linker])
        raise EnvironmentException('Unknown static linker "%s"' % linker)

    def detect_ccache(self):
        try:
            has_ccache = subprocess.call(['ccache', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            has_ccache = 1
        if has_ccache == 0:
            cmdlist = ['ccache']
        else:
            cmdlist = []
        return cmdlist

    def get_objc_compiler_exelist(self):
        ccachelist = self.detect_ccache()
        evar = 'OBJCC'
        if evar in os.environ:
            return os.environ[evar].split()
        return ccachelist + self.default_objc

    def get_objcpp_compiler_exelist(self):
        ccachelist = self.detect_ccache()
        evar = 'OBJCXX'
        if evar in os.environ:
            return os.environ[evar].split()
        return ccachelist + self.default_objcpp

    def get_source_dir(self):
        return self.source_dir

    def get_build_dir(self):
        return self.build_dir

    def get_exe_suffix(self):
        return self.exe_suffix

    # On Windows the library has suffix dll
    # but you link against a file that has suffix lib.
    def get_import_lib_suffix(self):
        return self.import_lib_suffix

    def get_shared_lib_prefix(self):
        return self.shared_lib_prefix

    def get_shared_lib_suffix(self):
        return self.shared_lib_suffix

    def get_static_lib_prefix(self):
        return self.static_lib_prefix

    def get_static_lib_suffix(self):
        return self.static_lib_suffix

    def get_object_suffix(self):
        return self.object_suffix

    def get_prefix(self):
        return self.coredata.prefix

    def get_libdir(self):
        return self.coredata.libdir

    def get_bindir(self):
        return self.coredata.bindir

    def get_includedir(self):
        return self.coredata.includedir

    def get_mandir(self):
        return self.coredata.mandir

    def get_datadir(self):
        return self.coredata.datadir

    def find_library(self, libname):
        dirs = self.get_library_dirs()
        suffixes = [self.get_shared_lib_suffix(), self.get_static_lib_suffix()]
        prefix = self.get_shared_lib_prefix()
        for d in dirs:
            for suffix in suffixes:
                trial = os.path.join(d, prefix + libname + '.' + suffix)
                if os.path.isfile(trial):
                    return trial

    def get_library_dirs(self):
        return get_library_dirs()

def get_library_dirs():
        if is_windows():
            return ['C:/mingw/lib'] # Fixme
        if is_osx():
            return ['/usr/lib'] # Fix me as well.
        # The following is probably Debian/Ubuntu specific.
        unixdirs = ['/usr/lib', '/lib']
        plat = subprocess.check_output(['uname', '-m']).decode().strip()
        # This is a terrible hack. I admit it and I'm really sorry.
        # I just don't know what the correct solution is.
        if plat == 'i686':
            plat = 'i386'
        unixdirs += glob('/usr/lib/' + plat + '*')
        if os.path.exists('/usr/lib64'):
            unixdirs.append('/usr/lib64')
        unixdirs += glob('/lib/' + plat + '*')
        if os.path.exists('/lib64'):
            unixdirs.append('/lib64')
        unixdirs += glob('/lib/' + plat + '*')
        unixdirs.append('/usr/local/lib')
        return unixdirs

def get_args_from_envvars(lang):
    if lang == 'c':
        compile_args = os.environ.get('CFLAGS', '').split()
        link_args = compile_args + os.environ.get('LDFLAGS', '').split()
        compile_args += os.environ.get('CPPFLAGS', '').split()
    elif lang == 'cpp':
        compile_args = os.environ.get('CXXFLAGS', '').split()
        link_args = compile_args + os.environ.get('LDFLAGS', '').split()
        compile_args += os.environ.get('CPPFLAGS', '').split()
    elif lang == 'fortran':
        compile_args = os.environ.get('FFLAGS', '').split()
        link_args = compile_args + os.environ.get('LDFLAGS', '').split()
    else:
        compile_args = []
        link_args = []
    return (compile_args, link_args)

class CrossBuildInfo():
    def __init__(self, filename):
        self.items = {}
        self.parse_datafile(filename)
        if not 'name' in self:
            raise EnvironmentException('Cross file must specify "name" (e.g. "linux", "darwin" or "windows".')

    def ok_type(self, i):
        return isinstance(i, str) or isinstance(i, int) or isinstance(i, bool)

    def parse_datafile(self, filename):
        # This is a bit hackish at the moment.
        for i, line in enumerate(open(filename)):
            linenum = i+1
            line = line.strip()
            if line == '':
                continue
            if '=' not in line:
                raise EnvironmentException('Malformed line in cross file %s:%d.' % (filename, linenum))
            (varname, value) = line.split('=', 1)
            varname = varname.strip()
            if ' ' in varname or '\t' in varname or "'" in varname or '"' in varname:
                raise EnvironmentException('Malformed variable name in cross file %s:%d.' % (filename, linenum))
            try:
                res = eval(value, {'true' : True, 'false' : False})
            except Exception:
                raise EnvironmentException('Malformed line in cross file %s:%d.' % (filename, linenum))
            if self.ok_type(res):
                self.items[varname] = res
            elif isinstance(res, list):
                for i in res:
                    if not self.ok_type(i):
                        raise EnvironmentException('Malformed line in cross file %s:%d.' % (filename, linenum))
                self.items[varname] = res
            else:
                raise EnvironmentException('Malformed line in cross file %s:%d.' % (filename, linenum))

    def __getitem__(self, ind):
        try:
            return self.items[ind]
        except KeyError:
            raise EnvironmentException('Cross file does not specify variable "%s".' % ind)

    def __contains__(self, item):
        return item in self.items

    def get(self, *args, **kwargs):
        return self.items.get(*args, **kwargs)
