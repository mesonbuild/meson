"""Unit tests for `PythonInstallation._PythonDependencyBase.get_windows_python_arch`.

[#14475](https://github.com/mesonbuild/meson/issues/14475) reports a crash on
Windows 11 ARM64 when the host Python interpreter is 32-bit ARM, namely
``sysconfig.get_platform()`` returns ``'win-arm32'``. The default branch of
``get_windows_python_arch`` only recognised 'win32', 'win64', 'win-amd64' and
'win-arm64', so 32-bit ARM fell through to the (non-f-string) "Unknown Windows
Python platform {self.platform!r}" message and downstream ``.endswith('64')``
calls crashed.

These tests use a lightweight subclass overriding ``self.platform`` to avoid
spinning up a real Python interpreter introspection.
"""
from __future__ import annotations

import unittest

from mesonbuild.dependencies.python import _PythonDependencyBase


class _PlatformStub(_PythonDependencyBase):
    """Injects a fixed `self.platform`, bypassing interpreter introspection."""

    def __init__(self, platform: str):  # noqa: D401
        self.platform = platform
        # Avoid touching any real environment / interp setup.
        self.embed = False
        self.build_config = None
        self.version = '3.12.0'
        self.is_freethreaded = False
        self.link_libpython = False
        self.is_pypy = False
        self.variables = {}
        self.paths = {}
        self.major_version = 3
        self.compile_args: list[str] = []
        self.is_found = True


class WindowsPythonArchTests(unittest.TestCase):
    def test_win32_x86(self):
        self.assertEqual(_PlatformStub('win32').get_windows_python_arch(), 'x86')

    def test_win_amd64_x86_64(self):
        self.assertEqual(_PlatformStub('win-amd64').get_windows_python_arch(),
                         'x86_64')

    def test_win64_x86_64(self):
        self.assertEqual(_PlatformStub('win64').get_windows_python_arch(),
                         'x86_64')

    def test_win_arm64_aarch64(self):
        self.assertEqual(_PlatformStub('win-arm64').get_windows_python_arch(),
                         'aarch64')

    def test_win_arm32_arm(self):
        # Regression test for #14475:
        # `win-arm32` was previously reported as "Unknown Windows Python
        # platform 'win-arm32'" and caused a downstream crash.
        self.assertEqual(_PlatformStub('win-arm32').get_windows_python_arch(),
                         'arm')

    def test_mingw_x86_64(self):
        self.assertEqual(_PlatformStub('mingw_x86_64').get_windows_python_arch(),
                         'x86_64')

    def test_mingw_i686_x86(self):
        self.assertEqual(_PlatformStub('mingw_i686').get_windows_python_arch(),
                         'x86')

    def test_mingw_aarch64(self):
        self.assertEqual(_PlatformStub('mingw_aarch64').get_windows_python_arch(),
                         'aarch64')

    def test_unknown_platform_raises_with_fstring(self):
        # The error message used to be a literal "{var!r}" (missing f-prefix)
        # so users could not diagnose what platform meson actually saw.
        from mesonbuild.dependencies.base import DependencyException
        with self.assertRaises(DependencyException) as ctx:
            _PlatformStub('win-riscv').get_windows_python_arch()
        # The message must include the literal platform string -- the f-string
        # bug being fixed ensures {self.platform!r} is expanded.
        self.assertIn("'win-riscv'", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
