# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Meson development team

from .generatormd import GeneratorMD

from .model import (
    ReferenceManual,
    #Function,
    #Method,
    #Object,
    #ObjectType,
    #Type,
    #DataTypeInfo,
    #ArgBase,
    #PosArg,
    #VarArgs,
    #Kwarg,
)

import xml.etree.ElementTree as ET
#import typing as T
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
    def __init__(self, manual: ReferenceManual, sitemap_out: Path, sitemap_in: Path, link_def_out: Path, enable_modules: bool) -> None:
        super().__init__(manual, sitemap_out, sitemap_in, link_def_out, enable_modules)
        #self.out_dir /= "qthelp"

        # Qt Help Project data
        self.qhp_data = ET.TreeBuilder()

    def _build_table_of_contents(self) -> None:
        self.qhp_data.start('toc', {})
        with open(self.sitemap_in, 'r') as sitemap:
            level = -1
            line: str
            while True:
                line = sitemap.readline()

                newlevel = line.count('\t', 0)
                if newlevel <= level:
                    for _ in range(level - newlevel + 1):
                        self.qhp_data.end('section')
                level = newlevel

                if line == '':
                    # EOF
                    break

                doc = line[level:-4] # Trimmed markdown filename without extension
                mlog.log('Adding section', doc)
                self.qhp_data.start('section', {'title': doc, 'ref': doc + '.html'})

        self.qhp_data.end('toc')

    def _build_qhp_tree(self) -> None:
        def build_small_tag(builder: ET.TreeBuilder, tag: str, data: str):
            '''
            Build a tag that only has text and no attributes
            '''
            builder.start(tag, {})
            builder.data(data)
            builder.end(tag)

        self.qhp_data.start('QtHelpProject', {'version': '1.0'})

        build_small_tag(self.qhp_data, 'namespace', _NAMESPACE)
        build_small_tag(self.qhp_data, 'virtualFolder', _VIRTUAL_FOLDER)

        self.qhp_data.start('customFilter', {'name': _FILTER_NAME})
        build_small_tag(self.qhp_data, 'filterAttribute', _FILTER_ATTR_NAME)
        build_small_tag(self.qhp_data, 'filterAttribute', _FILTER_ATTR_VER)
        self.qhp_data.end('customFilter')

        self.qhp_data.start('filterSection', {'name': _FILTER_NAME})
        build_small_tag(self.qhp_data, 'filterAttribute', _FILTER_ATTR_NAME)
        build_small_tag(self.qhp_data, 'filterAttribute', _FILTER_ATTR_VER)

        self._build_table_of_contents()

        self.qhp_data.start('files', {})
        build_small_tag(self.qhp_data, 'file', '*.html')
        self.qhp_data.end('files')

        self.qhp_data.end('filterSection')

        self.qhp_data.end('QtHelpProject')

    def generate(self):
        super().generate()

        mlog.log('Generating QtHelp file...')
        with mlog.nested():
            self._build_qhp_tree()
            qhp_tree = ET.ElementTree(self.qhp_data.close())
            with open("Meson.qhp", "wb+") as qhp_file:
                qhp_tree.write(qhp_file, encoding='utf-8', xml_declaration=True)
