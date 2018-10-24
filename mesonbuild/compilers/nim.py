import os.path
import subprocess
from ..mesonlib import EnvironmentException, Popen_safe, mlog
from ..mesonlib import get_compiler_for_source

from .compilers import (
    nim_buildtype_args,
    Compiler
)


class NimCompiler(Compiler):

    def __init__(self, exelist, version):
        self.language = 'nim'
        super().__init__(exelist, version)
        self.id = 'nim'
        self.is_cross = False

    def sanity_check(self, work_dir, environment):
        source_name = os.path.join(work_dir, 'sanity.nim')
        output_name = os.path.join(work_dir, 'nimtest')
        code = '' # blank files are valid nim
        args = self.exelist + ['c']
        args  = self.get_cross_extra_flags(environment, link=False)
        args += self.get_output_args(output_name)
        args += self.get_outdir_args(work_dir)
        with open(source_name, 'w'):
            pass
        
        mlog.debug('Running compile:')
        mlog.debug('Working directory: ', work_dir)
        mlog.debug('Command line: ', ' '.join(args), '\n')
        pc, stdo, stde  = Popen_safe(
            self.exelist + ['c'] + args + [source_name], cwd=work_dir)
        pc.wait()
        mlog.debug('Compiler stdout:\n', stdo)
        mlog.debug('Compiler stderr:\n', stde)
        if pc.returncode != 0:
            raise EnvironmentException(
                'Nim compiler can not compile programs.')
        if subprocess.call(output_name) != 0:
            raise EnvironmentException(
                "Executables created by Nim compiler are not runnable.")

    def get_output_args(self, target):
        return ['--out:' + target]

    def get_nimcache_dir(self, outdir):
        return os.path.join(outdir, 'nimcache')

    def get_outdir_args(self, outdir):
        return ['--nimcache:{}'.format(self.get_nimcache_dir(outdir))]

    def needs_static_linker(self):
        return False

    def name_string(self):
        return ' '.join(self.exelist)

    def get_compile_only_args(self):
        return ['--compileOnly']

    def get_dependency_gen_args(self):
        return ['--genDeps']

    def get_linker_exelist(self):
        return self.exelist[:]

    def get_linker_output_args(self, outputname):
        return []

    def get_buildtype_args(self, buildtype):
        return nim_buildtype_args[buildtype]

    def get_always_args(self):
        return ['c', '--verbosity:0']

    def get_warn_args(self, warninglevel):
        return []

    def get_compiler_shared_lib_args(self):
        return ['--app:lib']

    def get_compiler_static_lib_args(self):
        return ['--app:staticlib']
