# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson development team

import os
import unittest

from mesonbuild import sbom

from .baseplatformtests import BasePlatformTests

GOLDEN = ('0a1c1a0464656d6f22060880e2cfaa062a0c0a056d65736f6e1203312e30'
          '123b0a390a13706b673a67656e657269632f61707040312e301a03617070'
          '2203312e30e2011708011213706b673a67656e657269632f61707040312e30')


class SbomEncoderTests(unittest.TestCase):

    def test_golden(self):
        doc = sbom._msg(sbom._DOC_METADATA, [
            sbom._str(sbom._META_NAME, 'demo'),
            sbom._msg(sbom._META_DATE, [sbom._int(sbom._TS_SECONDS, 1700000000)]),
            sbom._msg(sbom._META_TOOLS, [sbom._str(sbom._TOOL_NAME, 'meson'),
                                         sbom._str(sbom._TOOL_VERSION, '1.0')]),
        ]) + sbom._msg(sbom._DOC_NODE_LIST, [
            sbom._node('pkg:generic/app@1.0', 'app', '1.0', 'pkg:generic/app@1.0'),
        ])
        self.assertEqual(doc.hex(), GOLDEN)


class SbomSetupTests(BasePlatformTests):

    def _project(self):
        srcdir = self.builddir + '-src'
        os.makedirs(srcdir)
        with open(os.path.join(srcdir, 'meson.build'), 'w', encoding='utf-8') as f:
            f.write("project('demo', 'c', version: '1.0')\n"
                    "executable('app', 'app.c')\n")
        with open(os.path.join(srcdir, 'app.c'), 'w', encoding='utf-8') as f:
            f.write('int main(void) { return 0; }\n')
        return srcdir

    def test_setup_emits_sbom(self):
        srcdir = self._project()
        self.init(srcdir, extra_args=['--sbom'])
        path = os.path.join(self.builddir, 'sbom.protobom.bin')
        self.assertPathExists(path)
        with open(path, 'rb') as f:
            data = f.read()
        self.assertIn(b'demo', data)
        self.assertIn(b'app@exe', data)
        self.assertIn(b'pkg:generic/app@1.0', data)

    def test_deterministic(self):
        srcdir = self._project()
        os.environ['SOURCE_DATE_EPOCH'] = '1700000000'
        self.init(srcdir, extra_args=['--sbom'])
        path = os.path.join(self.builddir, 'sbom.protobom.bin')
        with open(path, 'rb') as f:
            first = f.read()
        self.init(srcdir, extra_args=['--sbom', '--reconfigure'])
        with open(path, 'rb') as f:
            second = f.read()
        self.assertEqual(first, second)

    def test_off_by_default(self):
        srcdir = self._project()
        self.init(srcdir)
        self.assertPathDoesNotExist(os.path.join(self.builddir, 'sbom.protobom.bin'))
