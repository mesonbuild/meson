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
'''
    This script is for generating MSI packages
    for Windows users.
'''
import subprocess
import shutil
import uuid
import sys
import os
from glob import glob
import platform
import xml.etree.ElementTree as ET

sys.path.append(os.getcwd())
from mesonbuild import coredata

def gen_guid():
    '''
       Generate guid
    '''
    return str(uuid.uuid4()).upper()

class Node:
    '''
       Node to hold path and directory values
    '''

    def __init__(self, dirs, files):
        self.check_dirs(dirs)
        self.check_files(files)
        self.dirs = dirs
        self.files = files

    @staticmethod
    def check_dirs(dirs):
        '''
           Check to see if directory is instance of list
        '''
        assert isinstance(dirs, list)

    @staticmethod
    def check_files(files):
        '''
           Check to see if files is instance of list
        '''
        assert isinstance(files, list)


class PackageGenerator:
    '''
       Package generator for MSI pacakges
    '''

    def __init__(self):
        self.product_name = 'Meson Build System'
        self.manufacturer = 'The Meson Development Team'
        self.version = coredata.version.replace('dev', '')
        self.root = None
        self.guid = '*'
        self.update_guid = '141527EE-E28A-4D14-97A4-92E6075D28B2'
        self.main_xml = 'meson.wxs'
        self.main_o = 'meson.wixobj'
        self.bytesize = 32 if '32' in platform.architecture()[0] else 64
        self.final_output = 'meson-{}-{}.msi'.format(self.version, self.bytesize)
        self.staging_dirs = ['dist', 'dist2']
        if self.bytesize == 64:
            self.progfile_dir = 'ProgramFiles64Folder'
            redist_glob = 'C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Community\\VC\\Redist\\MSVC\\*\\MergeModules\\Microsoft_VC142_CRT_x64.msm'
        else:
            self.progfile_dir = 'ProgramFilesFolder'
            redist_glob = 'C:\\Program Files*\\Microsoft Visual Studio\\2019\\Community\\VC\\Redist\\MSVC\\*\\MergeModules\\Microsoft_VC142_CRT_x86.msm'
        trials = glob(redist_glob)
        if len(trials) != 1:
            sys.exit('Could not find unique MSM setup:' + '\n'.join(trials))
        self.redist_path = trials[0]
        self.component_num = 0
        self.feature_properties = {
            self.staging_dirs[0]: {
                'Id': 'MainProgram',
                'Title': 'Meson',
                'Description': 'Meson executables',
                'Level': '1',
                'Absent': 'disallow',
            },
            self.staging_dirs[1]: {
                'Id': 'NinjaProgram',
                'Title': 'Ninja',
                'Description': 'Ninja build tool',
                'Level': '1',
            }
        }
        self.feature_components = {}
        for s_d in self.staging_dirs:
            self.feature_components[s_d] = []

    @staticmethod
    def get_all_modules_from_dir(dirname):
        '''
           Get all modules required for Meson build MSI package
           from directories.
        '''
        modname = os.path.basename(dirname)
        modules = [os.path.splitext(os.path.split(x)[1])[0] for x in glob(os.path.join(dirname, '*'))]
        modules = ['mesonbuild.' + modname + '.' + x for x in modules if not x.startswith('_')]
        return modules

    @staticmethod
    def get_more_modules():
        '''
           Getter for missing Modules.
           Python packagers want to be minimal and only copy the things
           that they can see that being used. They are blind to many things.
        '''
        return ['distutils.archive_util',
                'distutils.cmd',
                'distutils.config',
                'distutils.core',
                'distutils.debug',
                'distutils.dep_util',
                'distutils.dir_util',
                'distutils.dist',
                'distutils.errors',
                'distutils.extension',
                'distutils.fancy_getopt',
                'distutils.file_util',
                'distutils.spawn',
                'distutils.util',
                'distutils.version',
                'distutils.command.build_ext',
                'distutils.command.build',
                ]

    def build_dist(self):
        '''
           Build dist file from PyInstaller info
        '''
        for sdir in self.staging_dirs:
            if os.path.exists(sdir):
                shutil.rmtree(sdir)
        main_stage, ninja_stage = self.staging_dirs
        dep_data_dir = 'mesonbuild/dependencies/data'
        cmake_data_dir = 'mesonbuild/cmake/data'
        modules = self.get_all_modules_from_dir('mesonbuild/modules')
        modules += self.get_all_modules_from_dir('mesonbuild/scripts')
        modules += self.get_more_modules()

        pyinstaller = shutil.which('pyinstaller')
        if not pyinstaller:
            print("ERROR: This script requires pyinstaller.")
            sys.exit(1)

        pyinstaller_tmpdir = 'pyinst-tmp'
        if os.path.exists(pyinstaller_tmpdir):
            shutil.rmtree(pyinstaller_tmpdir)
        pyinst_cmd = [pyinstaller,
                      '--clean',
                      '--distpath',
                      pyinstaller_tmpdir]
        for m in modules:
            pyinst_cmd += ['--hidden-import', m]
        pyinst_cmd += ['meson.py']
        subprocess.check_call(pyinst_cmd)
        shutil.move(pyinstaller_tmpdir + '/meson', main_stage)
        shutil.copytree(dep_data_dir, main_stage + '/mesonbuild/dependencies/data')
        shutil.copytree(cmake_data_dir, main_stage + '/mesonbuild/cmake/data')
        if not os.path.exists(os.path.join(main_stage, 'meson.exe')):
            sys.exit('Meson exe missing from staging dir.')
        os.mkdir(ninja_stage)
        shutil.copy(shutil.which('ninja'), ninja_stage)
        if not os.path.exists(os.path.join(ninja_stage, 'ninja.exe')):
            sys.exit('Ninja exe missing from staging dir.')

    def generate_files(self):
        '''
           Generate package files for MSI installer package
        '''
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

        package = ET.SubElement(product, 'Package', {
            'Id': '*',
            'Keywords': 'Installer',
            'Description': 'Meson {} installer'.format(self.version),
            'Comments': 'Meson is a high performance build system',
            'Manufacturer': 'The Meson Development Team',
            'InstallerVersion': '500',
            'Languages': '1033',
            'Compressed': 'yes',
            'SummaryCodepage': '1252',
        })

        ET.SubElement(product, 'MajorUpgrade',
                      {'DowngradeErrorMessage': 'A newer version of Meson is already installed.'})

        if self.bytesize == 64:
            package.set('Platform', 'x64')
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
            'Id': self.progfile_dir,
        })
        installdir = ET.SubElement(progfiledir, 'Directory', {
            'Id': 'INSTALLDIR',
            'Name': 'Meson',
        })
        ET.SubElement(installdir, 'Merge', {
            'Id': 'VCRedist',
            'SourceFile': self.redist_path,
            'DiskId': '1',
            'Language': '0',
        })

        ET.SubElement(product, 'Property', {
            'Id': 'WIXUI_INSTALLDIR',
            'Value': 'INSTALLDIR',
        })
        ET.SubElement(product, 'UIRef', {
            'Id': 'WixUI_FeatureTree',
        })
        for s_d in self.staging_dirs:
            assert os.path.isdir(s_d)
        top_feature = ET.SubElement(product, 'Feature', {
            'Id': 'Complete',
            'Title': 'Meson ' + self.version,
            'Description': 'The complete package',
            'Display': 'expand',
            'Level': '1',
            'ConfigurableDirectory': 'INSTALLDIR',
        })
        for s_d in self.staging_dirs:
            nodes = {}
            for root, dirs, files in os.walk(s_d):
                cur_node = Node(dirs, files)
                nodes[root] = cur_node
            self.create_xml(nodes, s_d, installdir, s_d)
            self.build_features(top_feature, s_d)
        vcredist_feature = ET.SubElement(top_feature, 'Feature', {
            'Id': 'VCRedist',
            'Title': 'Visual C++ runtime',
            'AllowAdvertise': 'no',
            'Display': 'hidden',
            'Level': '1',
        })
        ET.SubElement(vcredist_feature, 'MergeRef', {'Id': 'VCRedist'})
        ET.ElementTree(self.root).write(self.main_xml, encoding='utf-8', xml_declaration=True)
        # ElementTree can not do prettyprinting so do it manually
        import xml.dom.minidom
        doc = xml.dom.minidom.parse(self.main_xml)
        with open(self.main_xml, 'w') as open_file:
            open_file.write(doc.toprettyxml())

    def build_features(self, top_feature, staging_dir):
        '''
           Generate build features
        '''
        feature = ET.SubElement(top_feature, 'Feature', self.feature_properties[staging_dir])
        for component_id in self.feature_components[staging_dir]:
            ET.SubElement(feature, 'ComponentRef', {
                'Id': component_id,
            })

    def create_xml(self, nodes, current_dir, parent_xml_node, staging_dir):
        '''
           Create XML file
        '''
        cur_node = nodes[current_dir]
        if cur_node.files:
            component_id = 'ApplicationFiles{}'.format(self.component_num)
            comp_xml_node = ET.SubElement(parent_xml_node, 'Component', {
                'Id': component_id,
                'Guid': gen_guid(),
            })
            self.feature_components[staging_dir].append(component_id)
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
            for f_node in cur_node.files:
                file_id = os.path.join(current_dir, f_node).replace('\\', '_').replace('#', '_').replace('-', '_')
                ET.SubElement(comp_xml_node, 'File', {
                    'Id': file_id,
                    'Name': f_node,
                    'Source': os.path.join(current_dir, f_node),
                })

        for dirname in cur_node.dirs:
            dir_id = os.path.join(current_dir, dirname).replace('\\', '_').replace('/', '_')
            dir_node = ET.SubElement(parent_xml_node, 'Directory', {
                'Id': dir_id,
                'Name': dirname,
            })
            self.create_xml(nodes, os.path.join(current_dir, dirname), dir_node, staging_dir)

    def build_package(self):
        '''
           Generate the Meson build MSI package.
        '''
        wixdir = 'c:\\Program Files\\Wix Toolset v3.11\\bin'
        if not os.path.isdir(wixdir):
            wixdir = 'c:\\Program Files (x86)\\Wix Toolset v3.11\\bin'
        if not os.path.isdir(wixdir):
            print("ERROR: This script requires WIX")
            sys.exit(1)
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
    subprocess.check_call(['pip', 'install', '--upgrade', 'pyinstaller'])

    p = PackageGenerator()
    p.build_dist()
    p.generate_files()
    p.build_package()
