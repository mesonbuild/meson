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

import subprocess, os.path

builder_filename = 'builder.txt'

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

header_suffixes = ['h', 'hh', 'hpp', 'hxx', 'H']

class Environment():
    def __init__(self, source_dir, build_dir, options):
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.options = options
        self.scratch_dir = os.path.join(build_dir, 'builder-private')
        os.makedirs(self.scratch_dir, exist_ok=True)

        self.default_c = ['cc']
        self.default_cxx = ['c++']
        self.default_static_linker = ['ar']

        self.exe_suffix = ''
        self.shared_lib_suffix = 'so'
        self.shared_lib_prefix = 'lib'
        self.static_lib_suffix = 'a'
        self.static_lib_prefix = 'lib'
        self.object_suffix = 'o'

    def get_c_compiler_exelist(self):
        evar = 'CC'
        if evar in os.environ:
            return os.environ[evar].split()
        return self.default_c
    
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
        if out.startswith('clang'):
            return ClangCXXCompiler(exelist)
        raise EnvironmentException('Unknown compiler "' + ' '.join(exelist) + '"')
    
    def detect_static_linker(self):
        exelist = self.get_static_linker_exelist()
        p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE)
        out = p.communicate()[0]
        out = out.decode()
        if p.returncode == 0:
            return ArLinker(exelist)
        raise EnvironmentException('Unknown static linker "' + ' '.join(exelist) + '"')

    def get_cxx_compiler_exelist(self):
        evar = 'CXX'
        if evar in os.environ:
            return os.environ[evar].split()
        return self.default_cxx
    
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
        return self.options.prefix

    def get_libdir(self):
        return self.options.libdir

    def get_bindir(self):
        return self.options.bindir

    def get_includedir(self):
        return self.options.includedir

    def get_mandir(self):
        return self.options.mandir

    def get_datadir(self):
        return self.options.datadir

class Dependency():
    def __init__(self):
        pass

    def get_compile_flags(self):
        return []

    def get_link_flags(self):
        return []

# This should be an InterpreterObject. Fix it.

class PkgConfigDependency(Dependency):
    pkgconfig_found = False
    
    def __init__(self, name):
        Dependency.__init__(self)
        if not PkgConfigDependency.pkgconfig_found:
            self.check_pkgconfig()

        p = subprocess.Popen(['pkg-config', '--modversion', name], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        out = p.communicate()[0]
        if p.returncode != 0:
            raise RuntimeError('Dependency %s not known to pkg-config.' % name)
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

# Fixme, move to environment.
def find_external_dependency(name, kwargs):
    # Add detectors for non-pkg-config deps (e.g. Boost) etc here.
    return PkgConfigDependency(name)

def test_pkg_config():
    name = 'gtk+-3.0'
    dep = PkgConfigDependency(name)
    print(dep.get_modversion())
    print(dep.get_compile_flags())
    print(dep.get_link_flags())
    
if __name__ == '__main__':
    #test_cmd_line_building()
    test_pkg_config()
