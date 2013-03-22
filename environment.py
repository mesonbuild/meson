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

import subprocess, os.path, platform
import coredata
from glob import glob

build_filename = 'meson.build'

class EnvironmentException(Exception):
    def __init(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class CCompiler():
    def __init__(self, exelist):
        if type(exelist) == type(''):
            self.exelist = [exelist]
        elif type(exelist) == type([]):
            self.exelist = exelist
        else:
            raise TypeError('Unknown argument to CCompiler')
        self.language = 'c'

    def get_dependency_gen_flags(self, outtarget, outfile):
        return ['-MMD', '-MT', outtarget, '-MF', outfile]

    def get_depfile_suffix(self):
        return 'd'

    def get_language(self):
        return self.language

    def get_exelist(self):
        return self.exelist

    def get_compile_only_flags(self):
        return ['-c']

    def get_output_flags(self):
        return ['-o']

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
    
    def sanity_check(self, work_dir):
        source_name = os.path.join(work_dir, 'sanitycheckc.c')
        binary_name = os.path.join(work_dir, 'sanitycheckc')
        ofile = open(source_name, 'w')
        ofile.write('int main(int argc, char **argv) { int class=0; return class; }\n')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise RuntimeError('Compiler %s can not compile programs.' % self.name_string())
        pe = subprocess.Popen(binary_name)
        pe.wait()
        if pe.returncode != 0:
            raise RuntimeError('Executables created by C compiler %s are not runnable.' % self.name_string())

class CXXCompiler(CCompiler):
    def __init__(self, exelist):
        CCompiler.__init__(self, exelist)
        self.language = 'cxx'

    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        if suffix == 'cc' or suffix == 'cpp' or suffix == 'cxx' or \
            suffix == 'hh' or suffix == 'hpp' or suffix == 'hxx':
            return True
        return False

    def sanity_check(self, work_dir):
        source_name = os.path.join(work_dir, 'sanitycheckcxx.cc')
        binary_name = os.path.join(work_dir, 'sanitycheckcxx')
        ofile = open(source_name, 'w')
        ofile.write('class breakCCompiler;int main(int argc, char **argv) { return 0; }\n')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise RuntimeError('Compiler %s can not compile programs.' % self.name_string())
        pe = subprocess.Popen(binary_name)
        pe.wait()
        if pe.returncode != 0:
            raise RuntimeError('Executables created by C++ compiler %s are not runnable.' % self.name_string())

class GnuCCompiler(CCompiler):
    std_warn_flags = ['-Wall', '-Winvalid-pch']
    std_opt_flags = ['-O2']

    def __init__(self, exelist):
        CCompiler.__init__(self, exelist)

    def get_std_warn_flags(self):
        return GnuCCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return GnuCCompiler.std_opt_flags

    def get_pch_suffix(self):
        return 'gch'

class ClangCCompiler(CCompiler):
    std_warn_flags = ['-Wall', '-Winvalid-pch']
    std_opt_flags = ['-O2']

    def __init__(self, exelist):
        CCompiler.__init__(self, exelist)

    def get_std_warn_flags(self):
        return ClangCCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return ClangCCompiler.std_opt_flags

    def get_pch_suffix(self):
        return 'pch'

class GnuCXXCompiler(CXXCompiler):
    std_warn_flags = ['-Wall', '-Winvalid-pch']
    std_opt_flags = ['-O2']
    
    def __init__(self, exelist):
        CXXCompiler.__init__(self, exelist)

    def get_std_warn_flags(self):
        return GnuCXXCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return GnuCXXCompiler.std_opt_flags

    def get_pch_suffix(self):
        return 'gch'

class ClangCXXCompiler(CXXCompiler):
    std_warn_flags = ['-Wall', '-Winvalid-pch']
    std_opt_flags = ['-O2']

    def __init__(self, exelist):
        CXXCompiler.__init__(self, exelist)

    def get_std_warn_flags(self):
        return ClangCXXCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return ClangCXXCompiler.std_opt_flags

    def get_pch_suffix(self):
        return 'pch'

class ArLinker():
    std_flags = ['csr']

    def __init__(self, exelist):
        self.exelist = exelist
        
    def get_exelist(self):
        return self.exelist
    
    def get_std_link_flags(self):
        return self.std_flags

    def get_output_flags(self):
        return []

    def get_coverage_link_flags(self):
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

def is_windows():
    return platform.system().lower() == 'windows'

header_suffixes = ['h', 'hh', 'hpp', 'hxx', 'H']

class Environment():
    private_dir = 'meson-private'
    coredata_file = os.path.join(private_dir, 'coredata.dat')

    def __init__(self, source_dir, build_dir, main_script_file, options):
        assert(os.path.isabs(main_script_file))
        assert(not os.path.islink(main_script_file))
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.meson_script_file = main_script_file
        self.scratch_dir = os.path.join(build_dir, Environment.private_dir)
        os.makedirs(self.scratch_dir, exist_ok=True)

        try:
            cdf = os.path.join(self.get_build_dir(), Environment.coredata_file)
            self.coredata = coredata.load(cdf)
        except IOError:
            self.coredata = coredata.CoreData(options)

        self.default_c = ['cc']
        self.default_cxx = ['c++']
        self.default_static_linker = ['ar']

        if is_windows():
            self.exe_suffix = 'exe'
            self.shared_lib_suffix = 'dll'
            self.shared_lib_prefix = ''
            self.static_lib_suffix = 'lib'
            self.static_lib_prefix = ''
            self.object_suffix = 'obj'
        else:
            self.exe_suffix = ''
            if is_osx():
                self.shared_lib_suffix = 'dylib'
            else:
                self.shared_lib_suffix = 'so'
            self.shared_lib_prefix = 'lib'
            self.static_lib_suffix = 'a'
            self.static_lib_prefix = 'lib'
            self.object_suffix = 'o'

    def generating_finished(self):
        cdf = os.path.join(self.get_build_dir(), Environment.coredata_file)
        coredata.save(self.coredata, cdf)

    def get_script_dir(self):
        return os.path.dirname(self.meson_script_file)

    def get_coredata(self):
        return self.coredata

    def get_build_command(self):
        return self.meson_script_file

    def get_c_compiler_exelist(self):
        ccachelist = self.detect_ccache()
        evar = 'CC'
        if evar in os.environ:
            return os.environ[evar].split()
        return ccachelist + self.default_c

    def is_header(self, fname):
        suffix = fname.split('.')[-1]
        return suffix in header_suffixes

    def detect_c_compiler(self):
        exelist = self.get_c_compiler_exelist()
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute C compiler "%s"' % ' '.join(exelist))
        out = p.communicate()[0]
        out = out.decode()
        if (out.startswith('cc ') or out.startswith('gcc')) and \
            'Free Software Foundation' in out:
            return GnuCCompiler(exelist)
        if 'apple' in out and 'Free Software Foundation' in out:
            return GnuCCompiler(exelist)
        if (out.startswith('clang')):
            return ClangCCompiler(exelist)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')

    def get_scratch_dir(self):
        return self.scratch_dir

    def get_depfixer(self):
        path = os.path.split(__file__)[0]
        return os.path.join(path, 'depfixer.py')

    def detect_cxx_compiler(self):
        exelist = self.get_cxx_compiler_exelist()
        try:
            p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE)
        except OSError:
            raise EnvironmentException('Could not execute C++ compiler "%s"' % ' '.join(exelist))
        out = p.communicate()[0]
        out = out.decode()
        if (out.startswith('c++ ') or out.startswith('g++')) and \
            'Free Software Foundation' in out:
            return GnuCXXCompiler(exelist)
        if 'apple' in out and 'Free Software Foundation' in out:
            return GnuCXXCompiler(exelist)
        if out.startswith('clang'):
            return ClangCXXCompiler(exelist)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')
    
    def detect_static_linker(self):
        exelist = self.get_static_linker_exelist()
        p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()
        out = out.decode()
        err = err.decode()
        if p.returncode == 0:
            return ArLinker(exelist)
        if p.returncode == 1 and err.startswith('usage'): # OSX
            return ArLinker(exelist)
        raise EnvironmentException('Unknown static linker "' + ' '.join(exelist) + '"')

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

    def get_cxx_compiler_exelist(self):
        ccachelist = self.detect_ccache()
        evar = 'CXX'
        if evar in os.environ:
            return os.environ[evar].split()
        return ccachelist + self.default_cxx
    
    def get_static_linker_exelist(self):
        evar = 'AR'
        if evar in os.environ:
            return os.environ[evar].split()
        return self.default_static_linker

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
        if is_windows():
            return ['C:/mingw/lib'] # Fixme
        if is_osx():
            return ['/usr/lib'] # Fix me as well.
        unixdirs = ['/usr/lib', '/lib']
        plat = subprocess.check_output(['uname', '-m']).decode().strip()
        unixdirs += glob('/usr/lib/' + plat + '*')
        unixdirs.append('/usr/local/lib')
        return unixdirs

class Dependency():
    def __init__(self):
        pass

    def get_compile_flags(self):
        return []

    def get_link_flags(self):
        return []

    def found(self):
        return False

# This should be an InterpreterObject. Fix it.

class PkgConfigDependency(Dependency):
    pkgconfig_found = False
    
    def __init__(self, name, required):
        Dependency.__init__(self)
        if not PkgConfigDependency.pkgconfig_found:
            self.check_pkgconfig()

        self.is_found = False
        p = subprocess.Popen(['pkg-config', '--modversion', name], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        out = p.communicate()[0]
        if p.returncode != 0:
            if required:
                raise EnvironmentException('Required dependency %s not found.' % name)
            self.modversion = 'none'
            self.cflags = []
            self.libs = []
        else:
            self.is_found = True
            self.modversion = out.decode().strip()
            p = subprocess.Popen(['pkg-config', '--cflags', name], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out = p.communicate()[0]
            if p.returncode != 0:
                raise RuntimeError('Could not generate cflags for %s.' % name)
            self.cflags = out.decode().split()

            p = subprocess.Popen(['pkg-config', '--libs', name], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out = p.communicate()[0]
            if p.returncode != 0:
                raise RuntimeError('Could not generate libs for %s.' % name)
            self.libs = out.decode().split()

    def get_modversion(self):
        return self.modversion

    def get_compile_flags(self):
        return self.cflags

    def get_link_flags(self):
        return self.libs

    def check_pkgconfig(self):
        p = subprocess.Popen(['pkg-config', '--version'], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out = p.communicate()[0]
        if p.returncode != 0:
            raise RuntimeError('Pkg-config executable not found.')
        print('Found pkg-config version %s.' % out.decode().strip())
        PkgConfigDependency.pkgconfig_found = True

    def found(self):
        return self.is_found

class ExternalProgram():
    def __init__(self, name, fullpath=None):
        self.name = name
        self.fullpath = fullpath

    def found(self):
        return self.fullpath is not None

    def get_command(self):
        return self.fullpath

    def get_name(self):
        return self.name

class ExternalLibrary(Dependency):
    def __init__(self, name, fullpath=None):
        Dependency.__init__(self)
        self.name = name
        self.fullpath = fullpath

    def found(self):
        return self.fullpath is not None

    def get_name(self):
        return self.name
    
    def get_link_flags(self):
        if self.found():
            return [self.fullpath]
        return []

def find_external_dependency(name, kwargs):
    required = kwargs.get('required', False)
    return PkgConfigDependency(name, required)

def test_pkg_config():
    name = 'gtk+-3.0'
    dep = PkgConfigDependency(name)
    print(dep.get_modversion())
    print(dep.get_compile_flags())
    print(dep.get_link_flags())
    
if __name__ == '__main__':
    #test_cmd_line_building()
    test_pkg_config()
