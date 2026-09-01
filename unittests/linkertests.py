# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson development team

from pathlib import Path
from unittest import mock, SkipTest
import os
import shutil
import subprocess
import tempfile
import unittest

from mesonbuild.compilers.compilers import ManyInOneLinkerOptionStyle
from mesonbuild.compilers.detect import detect_c_compiler
from mesonbuild.linkers import linkers
from mesonbuild.mesonlib import MachineChoice, is_linux

from run_tests import get_fake_env

from .baseplatformtests import BasePlatformTests


class LinkerTests(unittest.TestCase):

    def test_gnuld_rpath_link_version_gate(self):
        env = get_fake_env()
        env.machines.host.system = 'linux'
        target = mock.Mock()
        target.determine_rpath_dirs.return_value = ('lib',)
        target.install_rpath = ''
        target.build_rpath = ''
        build_dir = os.path.join(os.sep, 'build')
        rpath_link = f'-Wl,-rpath-link,{os.path.join(build_dir, "lib")}'

        cases = (
            ('bfd', linkers.GnuBFDDynamicLinker, '2.27', True),
            ('bfd', linkers.GnuBFDDynamicLinker, '2.28', True),
            ('gold', linkers.GnuGoldDynamicLinker, '2.27', True),
            ('gold', linkers.GnuGoldDynamicLinker, '2.28', False),
        )
        for name, linker_cls, version, expected in cases:
            with self.subTest(linker=name, version=version):
                linker = linker_cls(
                    [], env, MachineChoice.HOST,
                    ManyInOneLinkerOptionStyle('-Wl,', ','), [], version=version)
                args, _ = linker.build_rpath_args(build_dir, 'app', target)
                if expected:
                    self.assertIn(rpath_link, args)
                else:
                    self.assertNotIn(rpath_link, args)


class BfdLinkerTests(BasePlatformTests):

    def test_rpath_link_transitive_dependency(self):
        if not is_linux():
            raise SkipTest('GNU ld.bfd transitive rpath test requires Linux')
        if shutil.which('ld.bfd') is None:
            raise SkipTest('ld.bfd not found')

        cc = detect_c_compiler(get_fake_env(), MachineChoice.HOST)
        if cc.id not in {'gcc', 'clang'} or not cc.use_linker_args('bfd', ''):
            raise SkipTest(f'{cc.id} cannot select ld.bfd for this test')

        testdir = os.path.join(self.unit_test_dir, '140 rpath link bfd')
        with tempfile.TemporaryDirectory() as hostile_dir:
            hostile_src = Path(hostile_dir, 'a.c')
            hostile_src.write_text('int incompatible_a(void) { return 0; }\n', encoding='utf-8')
            hostile_lib = Path(hostile_dir, 'liba.so.1')
            subprocess.check_call(
                cc.get_exelist(ccache=False) + [
                    '-shared', '-fPIC', '-Wl,-soname,liba.so.1',
                    str(hostile_src), '-o', str(hostile_lib),
                ])

            env = {
                'CC_LD': 'bfd',
                'LD_LIBRARY_PATH': hostile_dir,
            }
            self.init(testdir, override_envvars=env)
            compiler_info = self.introspect('--compilers')['host']['c']
            if compiler_info['linker_id'] != 'ld.bfd':
                raise SkipTest(f"configured linker is {compiler_info['linker_id']}, not ld.bfd")
            self.build(override_envvars=env)
