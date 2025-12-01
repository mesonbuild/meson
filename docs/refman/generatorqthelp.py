# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Meson development team

from .model import ReferenceManual
from .generatormd import GeneratorMD, _ROOT_BASENAME

import xml.etree.ElementTree as ET
import subprocess
import os
import shutil
from pathlib import Path

from mesonbuild import mlog

# TODO: version number
_NAMESPACE = 'com.mesonbuild.meson.1.0'
_NAMESPACE_ID = 'Mesonbuild'
_FILTER_NAME = 'Meson 1.0'
_FILTER_ATTR_NAME = 'meson'
_FILTER_ATTR_VER = '1.0'
_VIRTUAL_FOLDER = 'doc'

class GeneratorQtHelp(GeneratorMD):
    def __init__(self, manual: ReferenceManual, sitemap_out: Path, sitemap_in: Path,
                 link_def_out: Path, enable_modules: bool, qhelpgenerator: Path) -> None:
        super().__init__(manual, sitemap_out, sitemap_in, link_def_out, enable_modules)
        #self.out_dir /= "qthelp"

        # Qt Help Project data
        self.qhp_data = ET.TreeBuilder()

        self.qhelpgenerator = qhelpgenerator

    def generate(self) -> None:
        super().generate()

        mlog.log('Generating Qt Help Project file...')
        with mlog.nested():
            self._build_qhp_tree()
            qhp_tree = ET.ElementTree(self.qhp_data.close())
            with open('Meson.qhp', 'wb+') as qhp_file:
                qhp_tree.write(qhp_file, encoding='utf-8', xml_declaration=True)

        mlog.log('Generating Qt Compressed Help file...')
        with mlog.nested():
            self._generate_qch()

    def _get_doc_title(self, md: Path) -> str:
        if not md.exists() or not md.is_file():
            return ''

        with open(md, 'r') as doc:
            for line in doc:
                if line.startswith('# '):
                    return line[len('# '):-1]
                elif line.startswith('title: '):
                    return line[len('title: '):-1]

        return ''

    def _find_doc_path(self, name: str) -> Path:
        filename = name + '.md'
        out = self.out_dir / filename
        if out.exists():
            return out

        out = Path(__file__).resolve().parent.parent / 'markdown' / filename
        if out.exists():
            return out

        return Path('')

    def _build_table_of_contents(self) -> None:
        self.qhp_data.start('toc', {})
        with open(self.sitemap_in, 'r') as sitemap:
            level = -1
            for line in sitemap:
                line = line[:-1]

                newlevel = line.count('\t', 0)
                if newlevel <= level:
                    for _ in range(level - newlevel + 1):
                        self.qhp_data.end('section')
                level = newlevel

                if line == '':
                    # EOF
                    break

                if line == 'index.md':
                    mlog.log('Added top-level section')
                    self.qhp_data.start('section', {'title': 'Meson documentation', 'ref': 'index.html'})
                    continue

                doc = line[level:-3] # Trimmed markdown filename without extension
                md = self._find_doc_path(doc)
                title = self._get_doc_title(md)
                if title == '':
                    continue

                mlog.log('Added section', doc)
                self.qhp_data.start('section', {'title': title, 'ref': doc + '.html'})

        self.qhp_data.end('toc')

    def _build_keywords(self) -> None:
        self.qhp_data.start('keywords', {})

        for f in self.functions:
            mlog.log('Added keyword for function', f.name)
            self.qhp_data.start('keyword', {
                'name': f.name,
                'id': f.name,
                'ref': f'{_ROOT_BASENAME}_functions.html#{f.name}',
            })
            self.qhp_data.end('keyword')

        self.qhp_data.end('keywords')

    def _build_qhp_tree(self) -> None:
        def build_small_tag(tag: str, data: str) -> None:
            '''
            Build a tag that only has text and no attributes
            '''
            self.qhp_data.start(tag, {})
            self.qhp_data.data(data)
            self.qhp_data.end(tag)

        self.qhp_data.start('QtHelpProject', {'version': '1.0'})

        build_small_tag('namespace', _NAMESPACE)
        build_small_tag('virtualFolder', _VIRTUAL_FOLDER)

        self.qhp_data.start('customFilter', {'name': _FILTER_NAME})
        build_small_tag('filterAttribute', _FILTER_ATTR_NAME)
        build_small_tag('filterAttribute', _FILTER_ATTR_VER)
        self.qhp_data.end('customFilter')

        self.qhp_data.start('filterSection', {'name': _FILTER_NAME})
        build_small_tag('filterAttribute', _FILTER_ATTR_NAME)
        build_small_tag('filterAttribute', _FILTER_ATTR_VER)

        self._build_table_of_contents()
        self._build_keywords()

        self.qhp_data.start('files', {})
        build_small_tag('file', '*.html')
        build_small_tag('file', 'assets/css/*.css')
        self.qhp_data.end('files')

        self.qhp_data.end('filterSection')

        self.qhp_data.end('QtHelpProject')

    def _generate_qch(self):
        subprocess.run([self.qhelpgenerator, 'Meson.qhp', '-o', 'Meson.qch'], cwd=self.out_dir)
