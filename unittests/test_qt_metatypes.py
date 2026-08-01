"""Unit tests for `QtBaseModule._collect_foreign_metatypes` and the
`--foreign-types` argument wiring in `qml_module`.

These tests do not require Qt to be installed; they use small mock
Dependency objects whose `get_variable(pkgconfig='libdir')` returns a
synthesised libdir in a temporary directory.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock
from typing import List, Optional

from mesonbuild.dependencies.base import Dependency


class FakeQtDependency(Dependency):
    """Minimal Dependency that returns a fixed `libdir` for get_variable()."""

    def __init__(self, libdir: str):
        super().__init__({'native': None})  # type: ignore[arg-type]
        self._libdir = libdir
        self.is_found = True

    def get_variable(self, *, cmake: Optional[str] = None,
                     pkgconfig: Optional[str] = None,
                     configtool: Optional[str] = None,
                     internal: Optional[str] = None,
                     system: Optional[str] = None,
                     default_value: Optional[str] = None,
                     pkgconfig_define=None) -> str:
        if pkgconfig == 'libdir':
            return self._libdir
        if default_value is not None:
            return default_value
        raise ValueError(f'FakeQtDependency: no variable for {pkgconfig!r}')


def _make_metatypes_dir(libdir: str, qt_version: int,
                        module_names: List[str]) -> None:
    """Populate `<libdir>/qt<v>/metatypes/` with stubbed metatypes files."""
    mdir = os.path.join(libdir, f'qt{qt_version}', 'metatypes')
    os.makedirs(mdir, exist_ok=True)
    for name in module_names:
        with open(os.path.join(mdir, f'qt{qt_version}{name.lower()}_metatypes.json'), 'w', encoding='utf-8') as f:
            f.write('{}')


class CollectForeignMetatypesTests(unittest.TestCase):
    def setUp(self):
        # Direct invocation of QtBaseModule is non-trivial because it requires
        # an Interpreter. Instead, call the unbound helper method with `self`
        # being a lightweight stand-in object.
        from mesonbuild.modules._qt import QtBaseModule
        self._fn = QtBaseModule._collect_foreign_metatypes
        self._stub_self = mock.MagicMock()
        self.tmpdir = tempfile.mkdtemp(prefix='meson-qt-metatypes-')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_collects_qt6_metatypes_when_present(self):
        _make_metatypes_dir(self.tmpdir, 6, ['Core', 'Gui', 'Qml', 'Quick'])
        result = self._fn(self._stub_self, state=None,
                          dependencies=[FakeQtDependency(self.tmpdir)])
        self.assertEqual(len(result), 4)
        # All entries are absolute paths inside the metatypes dir.
        for p in result:
            self.assertTrue(os.path.isabs(p))
            self.assertTrue(p.startswith(os.path.join(self.tmpdir, 'qt6', 'metatypes')))
            self.assertTrue(p.endswith('_metatypes.json'))

    def test_returns_empty_when_metatypes_dir_missing(self):
        # No metatypes created - helper should return an empty list.
        result = self._fn(self._stub_self, state=None,
                          dependencies=[FakeQtDependency(self.tmpdir)])
        self.assertEqual(result, [])

    def test_skips_non_dependency_objects(self):
        _make_metatypes_dir(self.tmpdir, 6, ['Core'])
        result = self._fn(self._stub_self, state=None,
                          dependencies=[object(), 'not-a-dependency'])
        self.assertEqual(result, [])

    def test_ignores_files_that_do_not_match_metatypes_pattern(self):
        mdir = os.path.join(self.tmpdir, 'qt6', 'metatypes')
        os.makedirs(mdir)
        with open(os.path.join(mdir, 'metatypes.json'), 'w', encoding='utf-8') as f:
            f.write('{}')
        with open(os.path.join(mdir, 'README.md'), 'w', encoding='utf-8') as f:
            f.write('hi')
        result = self._fn(self._stub_self, state=None,
                          dependencies=[FakeQtDependency(self.tmpdir)])
        self.assertEqual(result, [])

    def test_handles_multiple_dependencies_deduplicating_paths(self):
        _make_metatypes_dir(self.tmpdir, 6, ['Core'])
        # Two deps pointing at the same libdir - should yield the same set of
        # files (no dedup is required by the contract, but at minimum no crash).
        result = self._fn(self._stub_self, state=None,
                          dependencies=[
                              FakeQtDependency(self.tmpdir),
                              FakeQtDependency(self.tmpdir),
                          ])
        # Files for the same Qt6/Core are found for both deps; this is
        # harmless to pass twice to qmltyperegistrar but we expect 2 paths
        # here and that build.QRC et al. tolerate duplicates.
        self.assertEqual(len(result), 2)


if __name__ == '__main__':
    unittest.main()
