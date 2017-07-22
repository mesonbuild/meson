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

sys.path.append(os.getcwd())
from mesonbuild import coredata

xml_templ = '''<?xml version='1.0' encoding='windows-1252'?>
<Wix xmlns='http://schemas.microsoft.com/wix/2006/wi'>
  <Product Name='Meson Build System' Manufacturer='The Meson Development Team'
           Id='%s' 
           UpgradeCode='%s'
           Language='1033' Codepage='1252' Version='%s'>
    <Package Id='*' Keywords='Installer' Description="Meson %s installer"
             Comments='Meson is a high performance build system' Manufacturer='Meson development team'
             InstallerVersion='100' Languages='1033' Compressed='yes' SummaryCodepage='1252' />

    <Media Id="1" Cabinet="meson.cab" EmbedCab="yes" />

    <Directory Id='TARGETDIR' Name='SourceDir'>
      <Directory Id="ProgramFilesFolder">
        <Directory Id="INSTALLDIR" Name="Meson">
'''

xml_footer_templ = '''
        </Directory>
      </Directory>
    </Directory>

    <Feature Id="DefaultFeature" Level="1">
%s
    </Feature>

  <Property Id="WIXUI_INSTALLDIR" Value="INSTALLDIR" />
  <UIRef Id="WixUI_InstallDir" />

  </Product>
</Wix>
'''

file_templ = '''<File Id='%s' Name='%s' DiskId='1' Source='%s'  />
'''

comp_ref_templ = '''<ComponentRef Id="%s" />
'''

path_addition_xml = '''<Environment Id="Environment" Name="PATH" Part="last" System="yes" Action="set" Value="[INSTALLDIR]"/>
'''


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
        self.version = coredata.version.replace('dev', '')
        self.guid = 'DF5B3ECA-4A31-43E3-8CE4-97FC8A97212E'
        self.update_guid = '141527EE-E28A-4D14-97A4-92E6075D28B2'
        self.main_xml = 'Meson.wxs'
        self.main_o = 'Meson.wixobj'
        self.bytesize = '32' if '32' in platform.architecture()[0] else '64'
        self.final_output = 'meson-%s-%s.msi' % (self.version, self.bytesize)
        self.staging_dir = 'dist'

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
        assert(os.path.isdir(self.staging_dir))
        comp_ref_xml = ''
        nodes = {}
        with open(self.main_xml, 'w') as ofile:
            for root, dirs, files in os.walk(self.staging_dir):
                cur_node = Node(dirs, files)
                nodes[root] = cur_node
            ofile.write(xml_templ % (self.guid, self.update_guid, self.version, self.version))
            self.component_num = 0
            self.create_xml(nodes, ofile, self.staging_dir)
            for i in range(self.component_num):
                comp_ref_xml += comp_ref_templ % ('ApplicationFiles%d' % i)
            ofile.write(xml_footer_templ % comp_ref_xml)

    def create_xml(self, nodes, ofile, root):
        cur_node = nodes[root]
        if cur_node.files:
            ofile.write("<Component Id='ApplicationFiles%d' Guid='%s'>\n" % (self.component_num, gen_guid()))
            if self.component_num == 0:
                ofile.write(path_addition_xml)
            self.component_num += 1
            for f in cur_node.files:
                file_source = os.path.join(root, f).replace('\\', '\\\\')
                file_id = os.path.join(root, f).replace('\\', '_').replace('#', '_').replace('-', '_')
                ofile.write(file_templ % (file_id, f, file_source))
            ofile.write('</Component>\n')

        for dirname in cur_node.dirs:
            dir_id = os.path.join(root, dirname).replace('\\', '_').replace('/', '_')
            ofile.write('''<Directory Id="%s" Name="%s">\n''' % (dir_id, dirname))
            self.create_xml(nodes, ofile, os.path.join(root, dirname))
            ofile.write('</Directory>\n')


    def build_package(self):
        subprocess.check_call(['c:\\Program Files\\Wix Toolset v3.11\\bin\candle', self.main_xml])
        subprocess.check_call(['c:\\Program Files\\Wix Toolset v3.11\\bin\light',
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
