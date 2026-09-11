# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson development team

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .baseplatformtests import BasePlatformTests
from mesonbuild.cargo.toml import load_toml


@unittest.skipIf(sys.version_info < (3, 11), 'check-platforms feature requires Python 3.11 or newer')
class CheckPlatformsTests(BasePlatformTests):
    def setUp(self) -> None:
        super().setUp()
        self.src_root = Path(__file__).resolve().parent.parent
        self.hermetic_test_dir = self.src_root / 'test cases/unit/hermetic'

    def test_android_checkplatforms(self) -> None:
        # This test outputs verifies output.toml has the compiler failures we expect
        # from the Android r29 NDK toolchain.
        with tempfile.TemporaryDirectory() as output_dir:
            test_dir = self.hermetic_test_dir / 'basic'
            output_file = Path(output_dir) / 'output.toml'
            command = self.meson_command + [
                'check-platforms',
                'test',
                'basic_soong',
                '--project-dir',
                str(test_dir),
                '--output',
                str(output_file),
            ]

            p = subprocess.run(command, capture_output=True, encoding='utf-8', text=True)
            if p.returncode != 0:
                print('STDOUT:')
                print(p.stdout)
                print('STDERR:')
                print(p.stderr)

            self.assertEqual(p.returncode, 0)
            self.assertTrue(output_file.exists(), 'Output TOML file was not generated')

            data = load_toml(str(output_file))
            self.assertIn('platform', data)
            platforms = data['platform']
            self.assertIsInstance(platforms, list)
            self.assertGreater(len(platforms), 0)

            android_platform = None
            for platform in platforms:
                if platform.get('name') == 'android_arm64':
                    android_platform = platform
                    break
            self.assertIsNotNone(android_platform, 'android_arm64 platform not found in output')

            self.assertIn('machine_info', android_platform)
            minfo = android_platform['machine_info']
            self.assertEqual(minfo['cpu_family'], 'aarch64')
            self.assertEqual(minfo['cpu'], 'aarch64')
            self.assertEqual(minfo['system'], 'android')
            self.assertEqual(minfo['endian'], 'little')

            self.assertIn('c', android_platform)
            c_info = android_platform['c']
            self.assertEqual(c_info['compiler_id'], 'clang')
            self.assertIn('version', c_info)

            self.assertIn('check_header', c_info)
            self.assertIn('fails', c_info['check_header'])
            self.assertTrue(c_info['check_header']['fails'].get('pthread_np.h'))

            self.assertIn('has_header_symbol', c_info)
            self.assertIn('fails', c_info['has_header_symbol'])
            self.assertTrue(c_info['has_header_symbol']['fails'].get('errno.h', {}).get('program_invocation_name'))

            self.assertIn('has_function', c_info)
            self.assertIn('fails', c_info['has_function'])
            self.assertTrue(c_info['has_function']['fails'].get('qsort_s'))

            self.assertIn('has_function_attribute', c_info)
            self.assertIn('fails', c_info['has_function_attribute'])
            self.assertTrue(c_info['has_function_attribute']['fails'].get('optimize'))

            self.assertIn('cpp', android_platform)
            cpp_info = android_platform['cpp']
            self.assertEqual(cpp_info['compiler_id'], 'clang')

            self.assertIn('links', cpp_info)
            self.assertIn('fails', cpp_info['links'])
            self.assertTrue(cpp_info['links']['fails'].get('BSD qsort_r'))
