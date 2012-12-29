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

class EnvironmentException(Exception):
    def __init(self, text):
        Exception.__init__(self, text)

def detect_c_compiler(execmd):
    exelist = execmd.split()
    p = subprocess.Popen(exelist + ['--version'], stdout=subprocess.PIPE)
    (out, err) = p.communicate()
    out = out.decode()
    if (out.startswith('cc ') or out.startswith('gcc')) and \
        'Free Software Foundation' in out:
        return GnuCCompiler(exelist)
    raise EnvironmentException('Unknown compiler "' + execmd + '"')

class CCompiler():
    def __init__(self, exelist):
        if type(exelist) == type(''):
            self.exelist = [exelist]
        elif type(exelist) == type([]):
            self.exelist = exelist
        else:
            raise TypeError('Unknown argument to CCompiler')

    def get_exelist(self):
        return self.exelist

    def get_compile_only_flags(self):
        return ['-c']

    def get_output_flags(self):
        return ['-o']

    def get_debug_flags(self):
        return ['-g']

    def can_compile(self, filename):
        suffix = filename.split('.')[-1]
        if suffix == 'c' or suffix == 'h':
            return True
        return False
    
    def name_string(self):
        return ' '.join(self.exelist)
    
    def sanity_check(self, work_dir):
        source_name = os.path.join(work_dir, 'sanitycheck.c')
        binary_name = os.path.join(work_dir, 'sanitycheck')
        ofile = open(source_name, 'w')
        ofile.write('int main(int argc, char **argv) { return 0; }\n')
        ofile.close()
        pc = subprocess.Popen(self.exelist + [source_name, '-o', binary_name])
        pc.wait()
        if pc.returncode != 0:
            raise RuntimeError('Compiler %s can not compile programs.' % self.name_string())
        pe = subprocess.Popen(binary_name)
        pe.wait()
        if pe.returncode != 0:
            raise RuntimeError('Executables created by compiler %s are not runnable.' % self.name_string())

class GnuCCompiler(CCompiler):
    std_warn_flags = ['-Wall', '-Winvalid-pch']
    std_opt_flags = ['-O2']
    
    def __init__(self, exelist):
        CCompiler.__init__(self, exelist)

    def get_std_warn_flags(self):
        return GnuCCompiler.std_warn_flags

    def get_std_opt_flags(self):
        return GnuCCompiler.std_opt_flags

def shell_quote(cmdlist):
    return ["'" + x + "'" for x in cmdlist]

def test_cmd_line_building():
    src_file = 'file.c'
    dst_file = 'file.o'
    gnuc = detect_c_compiler('/usr/bin/cc')
    cmds = gnuc.get_exelist()
    cmds += gnuc.get_std_warn_flags()
    cmds += gnuc.get_compile_only_flags()
    cmds.append(src_file)
    cmds += gnuc.get_output_flags()
    cmds.append(dst_file)
    cmd_line = ' '.join(shell_quote(cmds))
    print(cmd_line)

class Environment():
    def __init__(self, source_dir, build_dir):
        self.source_dir = source_dir
        self.build_dir = build_dir

        self.default_c = ['cc']
        self.default_cxx = ['c++']

        self.exe_suffix = ''
        self.shared_lib_suffix = 'so'
        self.shared_lib_prefix = 'lib'
        self.static_lib_suffix = 'a'
        self.static_lib_prefix = 'lib'
        self.object_suffix = 'o'

    def get_c_compiler(self):
        evar = 'CC'
        if evar in os.environ:
            return os.environ[evar].split()
        return self.default_c

    def get_cxx_compiler(self):
        evar = 'CXX'
        if evar in os.environ:
            return os.environ[evar].split()
        return self.default_cxx

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

class PkgConfigDependency():
    pkgconfig_found = False
    
    def __init__(self, name):
        if not PkgConfigDependency.pkgconfig_found:
            self.check_pkgconfig()

        p = subprocess.Popen(['pkg-config', '--modversion', name], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        (out, err) = p.communicate()
        if p.returncode != 0:
            raise RuntimeError('Dependency %s not known to pkg-config.' % name)
        self.modversion = out.decode().strip()
        p = subprocess.Popen(['pkg-config', '--cflags', name], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        (out, err) = p.communicate()
        if p.returncode != 0:
            raise RuntimeError('Could not generate cflags for %s.' % name)
        self.cflags = out.decode().split()
        
        p = subprocess.Popen(['pkg-config', '--libs', name], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        (out, err) = p.communicate()
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
        (out, err) = p.communicate()
        if p.returncode != 0:
            raise RuntimeError('Pkg-config not found.')
        print('Found pkg-config version %s\n', out.strip())
        PkgConfigDependency.pkgconfig_found = True

def find_external_dependency(self, name):
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
