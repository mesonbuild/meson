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

import subprocess, os.path, platform
import coredata
from glob import glob
import tempfile

build_filename = 'meson.build'

class EnvironmentException(Exception):
    def __init(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class RunResult():
    def __init__(self, compiled, returncode=999, stdout='UNDEFINED', stderr='UNDEFINED'):
        self.compiled = compiled
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

class CCompiler():
    def __init__(self, exelist, is_cross, exe_wrapper=None):
        if type(exelist) == type(''):
            self.exelist = [exelist]
        elif type(exelist) == type([]):
            self.exelist = exelist
        else:
            raise TypeError('Unknown argument to CCompiler')
        self.language = 'c'
        self.default_suffix = 'c'
        self.id = 'unknown'
        self.is_cross = is_cross
        if isinstance(exe_wrapper, str):
            self.exe_wrapper = [exe_wrapper]
        else:
            self.exe_wrapper = exe_wrapper

    def get_always_flags(self):
        return []

    def get_id(self):
        return self.id

    def get_dependency_gen_flags(self, outtarget, outfile):
        return ['-MMD', '-MT', outtarget, '-MF', outfile]

    def get_depfile_suffix(self):
        return 'd'

    def get_language(self):
        return self.language

    def get_exelist(self):
        return self.exelist[:]
    
    def get_linker_exelist(self):
        return self.exelist[:]

    def get_compile_only_flags(self):
        return ['-c']

    def get_output_flags(self, target):
        return ['-o', target]
    
    def get_linker_output_flags(self, outputname):
        return ['-o', outputname]

    def get_debug_flags(self):
        return ['-g']

    def get_coverage_flags(self):
        return ['--coverage']

    def get_coverage_link_flags(self):
        return ['-lgcov']

    def get_std_exe_link_flags(self):
        return []

    def get_include_arg(self, path):
        return '-I' + path

    def get_std_shared_lib_link_flags(self):
        return ['-shared']

    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        if suffix == 'c' or suffix == 'h':
            return True
        return False

    def get_pic_flags(self):
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
        commands += self.get_compile_only_flags()
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
            raise EnvironmentException('Can not run test applications in this cross environment.')
        (fd, srcname) = tempfile.mkstemp(suffix='.'+self.default_suffix)
        os.close(fd)
        ofile = open(srcname, 'w')
        ofile.write(code)
        ofile.close()
        exename = srcname + '.exe' # Is guaranteed to be executable on every platform.
        commands = self.get_exelist()
        commands.append(srcname)
        commands += self.get_output_flags(exename)
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

    def sizeof(self, element, prefix):
        templ = '''#include<stdio.h>
%s

int main(int argc, char **argv) {
    printf("%%ld\\n", (long)(sizeof(%s)));
    return 0;
};
'''
        res = self.run(templ % (prefix, element))
        if not res.compiled:
            raise EnvironmentException('Could not compile sizeof test.')
        if res.returncode != 0:
            raise EnvironmentException('Could not run sizeof test binary.')
        return int(res.stdout)

    def alignment(self, typename):
        # A word of warning: this algoritm may be totally incorrect.
        # However it worked for me on the cases I tried.
        # There is probably a smarter and more robust way to get this
        # information.
        templ = '''#include<stdio.h>

#define SDEF(num) struct foo##num { char pad[num]; %s x; };
#define PR(num) printf("%%d\\n", (int)sizeof(struct foo##num))
SDEF(1)
SDEF(2)
SDEF(3)
SDEF(4)
SDEF(5)
SDEF(6)
SDEF(7)
SDEF(8)
SDEF(9)
SDEF(10)
SDEF(12)
SDEF(13)
SDEF(14)
SDEF(15)
SDEF(16)
SDEF(17)

int main(int argc, char **argv) {
  PR(1);
  PR(2);
  PR(3);
  PR(4);
  PR(5);
  PR(6);
  PR(7);
  PR(8);
  PR(9);
  PR(10);
  PR(12);
  PR(13);
  PR(14);
  PR(15);
  PR(16);
  PR(17);
  return 0;
}
'''
        res = self.run(templ % typename)
        if not res.compiled:
            raise EnvironmentException('Could not compile alignment test.')
        if res.returncode != 0:
            raise EnvironmentException('Could not run alignment test binary.')
        arr = [int(x) for x in res.stdout.split()]
        for i in range(len(arr)-1):
            nxt= arr[i+1]
            cur = arr[i]
            diff = nxt - cur
            if diff > 0:
                return diff
        raise EnvironmentException('Could not determine alignment of %s. Sorry. You might want to file a bug.' % typename)

    def has_function(self, funcname, prefix):
        # This fails (returns true) if funcname is a ptr or a variable.
        # The correct check is a lot more difficult.
        # Fix this to do that eventually.
        templ = '''%s
int main(int argc, char **argv) {
    void *ptr = (void*)(%s);
    return 0;
};
'''
        res = self.run(templ % (prefix, funcname))
        return res.compiled

    def has_member(self, typename, membername, prefix):
        templ = '''%s
void bar() {
    %s foo;
    foo.%s;
};
'''
        return self.compiles(templ % (prefix, typename, membername))

class CPPCompiler(CCompiler):
    def __init__(self, exelist, is_cross, exe_wrap):
        CCompiler.__init__(self, exelist, is_cross, exe_wrap)
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
        pe = subprocess.Popen(binary_name)
        pe.wait()
        if pe.returncode != 0:
            raise EnvironmentException('Executables created by C++ compiler %s are not runnable.' % self.name_string())

class ObjCCompiler(CCompiler):
    def __init__(self, exelist):
        CCompiler.__init__(self, exelist)
        self.language = 'objc'
        self.default_suffix = 'm'
        
    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        if suffix == 'm' or suffix == 'h':
            return True
        return False

class ObjCPPCompiler(CPPCompiler):
    def __init__(self, exelist):
        CPPCompiler.__init__(self, exelist)
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

class VisualStudioCCompiler(CCompiler):
    std_warn_flags = ['/W3']
    std_opt_flags= ['/O2']
    always_flags = ['/nologo', '/showIncludes']
    
    def __init__(self, exelist):
        CCompiler.__init__(self, exelist)
        self.id = 'msvc'

    def get_always_flags(self):
        return VisualStudioCCompiler.always_flags

    def get_std_warn_flags(self):
        return VisualStudioCCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return VisualStudioCCompiler.std_opt_flags
    
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

    def get_debug_flags(self):
        return ['/D_DEBUG', '/Zi', '/MDd', '/Ob0', '/RTC1']

    def get_compile_only_flags(self):
        return ['/c']

    def get_output_flags(self, target):
        if target.endswith('.exe'):
            return ['/Fe' + target]
        return ['/Fo' + target]

    def get_dependency_gen_flags(self, outtarget, outfile):
        return []

    def get_linker_exelist(self):
        return ['link'] # FIXME, should have same path as compiler.

    def get_linker_output_flags(self, outputname):
        return ['/OUT:' + outputname]

    def get_pic_flags(self):
        return ['/LD']

    def get_std_shared_lib_link_flags(self):
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
    def __init__(self, exelist):
        VisualStudioCCompiler.__init__(self, exelist)
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

class GnuCCompiler(CCompiler):
    std_warn_flags = ['-Wall', '-Winvalid-pch']
    std_opt_flags = ['-O2']

    def __init__(self, exelist, is_cross, exe_wrapper=None):
        CCompiler.__init__(self, exelist, is_cross, exe_wrapper)
        self.id = 'gcc'

    def get_std_warn_flags(self):
        return GnuCCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return GnuCCompiler.std_opt_flags

    def get_pch_suffix(self):
        return 'gch'

class GnuObjCCompiler(ObjCCompiler):
    std_warn_flags = ['-Wall', '-Winvalid-pch']
    std_opt_flags = ['-O2']
    
    def __init__(self, exelist):
        ObjCCompiler.__init__(self, exelist)
        self.id = 'gcc'

    def get_std_warn_flags(self):
        return GnuObjCCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return GnuObjCCompiler.std_opt_flags

    def get_pch_suffix(self):
        return 'gch'

class GnuObjCPPCompiler(ObjCPPCompiler):
    std_warn_flags = ['-Wall', '-Winvalid-pch']
    std_opt_flags = ['-O2']

    def __init__(self, exelist):
        ObjCCompiler.__init__(self, exelist)
        self.id = 'gcc'

    def get_std_warn_flags(self):
        return GnuObjCPPCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return GnuObjCPPCompiler.std_opt_flags

    def get_pch_suffix(self):
        return 'gch'

class ClangCCompiler(CCompiler):
    std_warn_flags = ['-Wall', '-Winvalid-pch']
    std_opt_flags = ['-O2']

    def __init__(self, exelist):
        CCompiler.__init__(self, exelist)
        self.id = 'clang'

    def get_std_warn_flags(self):
        return ClangCCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return ClangCCompiler.std_opt_flags

    def get_pch_suffix(self):
        return 'pch'

class GnuCPPCompiler(CPPCompiler):
    std_warn_flags = ['-Wall', '-Winvalid-pch']
    std_opt_flags = ['-O2']
    
    def __init__(self, exelist, is_cross, exe_wrap):
        CPPCompiler.__init__(self, exelist, is_cross, exe_wrap)
        self.id = 'gcc'

    def get_std_warn_flags(self):
        return GnuCPPCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return GnuCPPCompiler.std_opt_flags

    def get_pch_suffix(self):
        return 'gch'

class ClangCPPCompiler(CPPCompiler):
    std_warn_flags = ['-Wall', '-Winvalid-pch']
    std_opt_flags = ['-O2']

    def __init__(self, exelist):
        CPPCompiler.__init__(self, exelist)
        self.id = 'clang'

    def get_std_warn_flags(self):
        return ClangCPPCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return ClangCPPCompiler.std_opt_flags

    def get_pch_suffix(self):
        return 'pch'

class VisualStudioLinker():
    always_flags = ['/NOLOGO']
    def __init__(self, exelist):
        self.exelist = exelist
        
    def get_exelist(self):
        return self.exelist

    def get_std_link_flags(self):
        return []

    def get_output_flags(self, target):
        return ['/OUT:' + target]

    def get_coverage_link_flags(self):
        return []

    def get_always_flags(self):
        return VisualStudioLinker.always_flags

class ArLinker():
    std_flags = ['csr']

    def __init__(self, exelist):
        self.exelist = exelist
        
    def get_exelist(self):
        return self.exelist
    
    def get_std_link_flags(self):
        return self.std_flags

    def get_output_flags(self, target):
        return [target]

    def get_coverage_link_flags(self):
        return []

    def get_always_flags(self):
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

def find_cppcheck():
    cppcheck_exe = 'cppcheck'
    if not exe_exists([cppcheck_exe, '-h']):
        cppcheck_exe = None
    return cppcheck_exe

def is_osx():
    return platform.system().lower() == 'darwin'

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
cpp_suffixes = ['cc', 'cpp', 'cxx', 'hh', 'hpp', 'hxx']
c_suffixes = ['c']
clike_suffixes = c_suffixes + cpp_suffixes

def is_header(fname):
    suffix = fname.split('.')[-1]
    return suffix in header_suffixes

def is_source(fname):
    suffix = fname.split('.')[-1]
    return suffix in clike_suffixes

class Environment():
    private_dir = 'meson-private'
    log_dir = 'meson-logs'
    coredata_file = os.path.join(private_dir, 'coredata.dat')

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
        except IOError:
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
        self.default_static_linker = 'ar'
        self.vs_static_linker = 'lib'
        
        cross = self.is_cross_build()
        if (not cross and is_windows()) \
        or (cross and self.cross_info['name'] == 'windows'):
            self.exe_suffix = 'exe'
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

    def detect_c_compiler(self):
        evar = 'CC'
        if self.is_cross_build():
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
                                     stderr=subprocess.DEVNULL)
            except OSError:
                continue
            out = p.communicate()[0]
            out = out.decode()
            if (out.startswith('cc') or 'gcc' in out) and \
                'Free Software Foundation' in out:
                return GnuCCompiler(ccache + [compiler], is_cross, exe_wrap)
            if 'apple' in out and 'Free Software Foundation' in out:
                return GnuCCompiler(ccache + [compiler], is_cross, exe_wrap)
            if (out.startswith('clang')):
                return ClangCCompiler(ccache + [compiler], is_cross, exe_wrap)
            if 'Microsoft' in out:
                return VisualStudioCCompiler([compiler], is_cross, exe_wrap)
        raise EnvironmentException('Unknown compiler(s): "' + ', '.join(compilers) + '"')

    def get_scratch_dir(self):
        return self.scratch_dir

    def get_depfixer(self):
        path = os.path.split(__file__)[0]
        return os.path.join(path, 'depfixer.py')

    def detect_cpp_compiler(self):
        evar = 'CXX'
        if self.is_cross_build():
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
                                     stderr=subprocess.DEVNULL)
            except OSError:
                continue
            out = p.communicate()[0]
            out = out.decode()
            if (out.startswith('c++ ') or out.startswith('g++') or 'GCC' in out) and \
                'Free Software Foundation' in out:
                return GnuCPPCompiler(ccache + [compiler], is_cross, exe_wrap)
            if 'apple' in out and 'Free Software Foundation' in out:
                return GnuCPPCompiler(ccache + [compiler], is_cross, exe_wrap)
            if out.startswith('clang'):
                return ClangCPPCompiler(ccache + [compiler], is_cross, exe_wrap)
            if 'Microsoft' in out:
                return VisualStudioCPPCompiler([compiler], is_cross, exe_wrap)
        raise EnvironmentException('Unknown compiler(s) "' + ', '.join(compilers) + '"')

    def detect_objc_compiler(self):
        exelist = self.get_objc_compiler_exelist()
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute ObjC compiler "%s"' % ' '.join(exelist))
        out = p.communicate()[0]
        out = out.decode()
        if (out.startswith('cc ') or out.startswith('gcc')) and \
            'Free Software Foundation' in out:
            return GnuObjCCompiler(exelist)
        if 'apple' in out and 'Free Software Foundation' in out:
            return GnuObjCCompiler(exelist)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_objcpp_compiler(self):
        exelist = self.get_objcpp_compiler_exelist()
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute ObjC++ compiler "%s"' % ' '.join(exelist))
        out = p.communicate()[0]
        out = out.decode()
        if (out.startswith('c++ ') or out.startswith('g++')) and \
            'Free Software Foundation' in out:
            return GnuObjCPPCompiler(exelist)
        if 'apple' in out and 'Free Software Foundation' in out:
            return GnuObjCPPCompiler(exelist)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def detect_static_linker(self, compiler):
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
        unixdirs += glob('/lib/' + plat + '*')
        unixdirs.append('/usr/local/lib')
        return unixdirs

class CrossBuildInfo():
    def __init__(self, filename):
        self.items = {}
        self.parse_datafile(filename)
        if not 'name' in self:
            raise EnvironmentException('Cross file must specify "name".')

    def parse_datafile(self, filename):
        # This is a bit hackish at the moment.
        for linenum, line in enumerate(open(filename)):
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
                res = eval(value, {})
            except Exception:
                raise EnvironmentException('Malformed line in cross file %s:%d.' % (filename, linenum))
            if isinstance(res, str):
                self.items[varname] = res
            elif isinstance(res, list):
                for i in res:
                    if not isinstance(i, str):
                        raise EnvironmentException('Malformed line in cross file %s:%d.' % (filename, linenum))
                self.items[varname] = res
            else:
                raise EnvironmentException('Malformed line in cross file %s:%d.' % (filename, linenum))

    def __getitem__(self, ind):
        return self.items[ind]

    def __contains__(self, item):
        return item in self.items

    def get(self, *args, **kwargs):
        return self.items.get(*args, **kwargs)
