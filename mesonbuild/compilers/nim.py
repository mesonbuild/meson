import os.path, subprocess
from ..mesonlib import EnvironmentException, version_compare

from .compilers import (
    GCC_STANDARD,
    nim_buildtype_args,
    Compiler,
    CompilerArgs
)

class NimCompiler(Compiler):
    def __init__(self, exelist, version):
        self.language = 'nim'
        super().__init__(exelist, version)
        self.id = 'nim'
    
    def sanity_check(self, work_dir, environment):
        source_name = os.path.join(work_dir, 'sanity.nim')
        output_name = os.path.join(work_dir, 'nimtest')
        with open(source_name, 'w') as ofile:
            pass
        pc = subprocess.Popen(self.exelist + ['c'] + self.get_output_args(output_name) + [source_name], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Nim compiler can not compile programs.')
        if subprocess.call(output_name) != 0:
            raise EnvironmentException("Executables created by Nim compiler are not runnable.")
    
    def get_output_args(self, target):
        return ['--out:' + target]

    def get_outdir_args(self, outdir):
        return ['--nimcache:{}'.format(os.path.join(outdir, 'nimcache'))]
    def needs_static_linker(self):
        return False

    def name_string(self):
        return ' '.join(self.exelist)
        
    def get_compile_only_args(self):
        return ['-c']
    
    def get_dependency_gen_args(self, outtarget, outfile):
        return []

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_linker_output_args(self, outputname):
        return []

    def get_buildtype_args(self, buildtype):
        return nim_buildtype_args[buildtype]

    def get_always_args(self):
        return ['c',]

    def get_warn_args(self, warninglevel):
        return []

    def get_compiler_shared_lib_args(self):
        return ['--app:lib']
    
    def get_compiler_static_lib_args(self):
        return ['--app:staticlib']
        
        


    