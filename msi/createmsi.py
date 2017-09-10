#!/usr/bin/env python3

# Copyright 2017 The Meson development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os, subprocess, shutil, uuid
from glob import glob
import platform
import xml.etree.ElementTree as ET

sys.path.append(os.getcwd())
from mesonbuild import coredata

def gen_guid():
    return str(uuid.uuid4()).upper()

class Node:
    def __init__(self, dirs, files):
        assert(isinstance(dirs, list))
        assert(isinstance(files, list))
        self.dirs = dirs
        self.files = files

class PackageGenerator:

    def __init__(self):
        self.product_name = 'Meson Build System'
        self.manufacturer = 'The Meson Development Team'
        self.version = coredata.version.replace('dev', '')
        self.guid = 'DF5B3ECA-4A31-43E3-8CE4-97FC8A97212E'
        self.update_guid = '141527EE-E28A-4D14-97A4-92E6075D28B2'
        self.main_xml = 'meson.wxs'
        self.main_o = 'meson.wixobj'
        self.bytesize = '32' if '32' in platform.architecture()[0] else '64'
        self.final_output = 'meson-%s-%s.msi' % (self.version, self.bytesize)
        self.staging_dir = 'dist'
        if self.bytesize == '64':
            self.platform_str = 'Platform="x64"'
            self.progfile_dir = 'ProgramFiles64Folder'
            self.component_platform = 'Win64="yes"'
        else:
            self.platform_str = ''
            self.progfile_dir = 'ProgramFilesFolder'
            self.component_platform = ''

    def build_dist(self):
        if os.path.exists(self.staging_dir):
            shutil.rmtree(self.staging_dir)
        modules = [os.path.splitext(os.path.split(x)[1])[0] for x in glob(os.path.join('mesonbuild/modules/*'))]
        modules = ['mesonbuild.modules.' + x for x in modules if not x.startswith('_')]
        modulestr = ','.join(modules)
        subprocess.check_call(['c:\\Python\python.exe',
                               'c:\\Python\Scripts\\cxfreeze',
                               '--target-dir',
                               self.staging_dir,
                               '--include-modules',
                               modulestr,
                               'meson.py'])
        shutil.copy(shutil.which('ninja'), self.staging_dir)
        if not os.path.exists(os.path.join(self.staging_dir, 'meson.exe')):
            sys.exit('Meson exe missing from staging dir.')
        if not os.path.exists(os.path.join(self.staging_dir, 'ninja.exe')):
            sys.exit('Ninja exe missing from staging dir.')


    def generate_files(self):
        self.root = ET.Element('Wix', {'xmlns': 'http://schemas.microsoft.com/wix/2006/wi'})
        product = ET.SubElement(self.root, 'Product', {
            'Name': self.product_name,
            'Manufacturer': 'The Meson Development Team',
            'Id': self.guid,
            'UpgradeCode': self.update_guid,
            'Language': '1033',
            'Codepage':  '1252',
            'Version': self.version,
            })

        ET.SubElement(product, 'Package',  {
            'Id': '*',
            'Keywords': 'Installer',
            'Description': 'Meson %s installer' % self.version,
            'Comments': 'Meson is a high performance build system',
            'Manufacturer': 'The Meson Development Team',
            'InstallerVersion': '100',
            'Languages': '1033',
            'Compressed': 'yes',
            'SummaryCodepage': '1252',
            })
        ET.SubElement(product, 'Media', {
            'Id': '1',
            'Cabinet': 'meson.cab',
            'EmbedCab': 'yes',
            })
        targetdir = ET.SubElement(product, 'Directory', {
            'Id': 'TARGETDIR',
            'Name': 'SourceDir',
            })
        progfiledir = ET.SubElement(targetdir, 'Directory', {
            'Id' : self.progfile_dir,
            })
        installdir = ET.SubElement(progfiledir, 'Directory', {
            'Id': 'INSTALLDIR',
            'Name': 'Meson'})

        ET.SubElement(product, 'Property', {
            'Id': 'WIXUI_INSTALLDIR',
            'Value': 'INSTALLDIR',
            })
        ET.SubElement(product, 'UIRef', {
            'Id': 'WixUI_InstallDir',
            })
        assert(os.path.isdir(self.staging_dir))
        nodes = {}
        for root, dirs, files in os.walk(self.staging_dir):
            cur_node = Node(dirs, files)
            nodes[root] = cur_node
        self.component_num = 0
        self.create_xml(nodes, self.staging_dir, installdir)
        feature = ET.SubElement(product, 'Feature', {
            'Id': 'DefaultFeature',
            'Level': '1',
            })
        
        for i in range(self.component_num):
            ET.SubElement(feature, 'ComponentRef', {
                'Id': 'ApplicationFiles%d' % i,
                })
        ET.ElementTree(self.root).write(self.main_xml, encoding='utf-8',xml_declaration=True)

    def create_xml(self, nodes, current_dir, parent_xml_node):
        cur_node = nodes[current_dir]
        if cur_node.files:
            comp_xml_node = ET.SubElement(parent_xml_node, 'Component', {
                'Id': 'ApplicationFiles%d' % self.component_num,
                'Guid': gen_guid(),
                })
            if self.bytesize == 64:
                comp_xml_node.set('Win64', 'yes')
            if self.component_num == 0:
                ET.SubElement(comp_xml_node, 'Environment', {
                    'Id': 'Environment',
                    'Name': 'PATH',
                    'Part': 'last',
                    'System': 'yes',
                    'Action': 'set',
                    'Value': '[INSTALLDIR]',
                })
            self.component_num += 1
            for f in cur_node.files:
                file_source = os.path.join(current_dir, f).replace('\\', '\\\\')
                file_id = os.path.join(current_dir, f).replace('\\', '_').replace('#', '_').replace('-', '_')
                ET.SubElement(comp_xml_node, 'File', {
                    'Id': file_id,
                    'Name': f,
                    'Source': os.path.join(current_dir, f),
                    })

        for dirname in cur_node.dirs:
            dir_id = os.path.join(current_dir, dirname).replace('\\', '_').replace('/', '_')
            dir_node = ET.SubElement(parent_xml_node, 'Directory', {
                'Id': dir_id,
                'Name': dirname,
                })
            self.create_xml(nodes, os.path.join(current_dir, dirname), dir_node)

    def build_package(self):
        wixdir = 'c:\\Program Files\\Wix Toolset v3.11\\bin'
        if not os.path.isdir(wixdir):
            wixdir = 'c:\\Program Files (x86)\\Wix Toolset v3.11\\bin'
        subprocess.check_call([os.path.join(wixdir, 'candle'), self.main_xml])
        subprocess.check_call([os.path.join(wixdir, 'light'),
                               '-ext', 'WixUIExtension',
                               '-cultures:en-us',
                               '-dWixUILicenseRtf=msi\\License.rtf',
                               '-out', self.final_output,
                               self.main_o])

if __name__ == '__main__':
    if not os.path.exists('meson.py'):
        sys.exit(print('Run me in the top level source dir.'))

    p = PackageGenerator()
    p.build_dist()
    p.generate_files()
    p.build_package()
