#!/usr/bin/env python3


# Copyright 2012-2013 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import xml.etree.ElementTree as ET

def runtest(ofname):
    buildtype = 'Debug'
    platform = "Win32"
    root = ET.Element('Project', {'DefaultTargets' : "Build",
                                  'ToolsVersion' : '4.0',
                                  'xmlns' : 'http://schemas.microsoft.com/developer/msbuild/2003'})
    confitems = ET.Element('ItemGroup', {'Label' : 'ProjectConfigurations'})
    prjconf = ET.SubElement(confitems, 'ProjectConfiguration', {'Include' : 'Debug|Win32'})
    p = ET.SubElement(prjconf, 'Configuration')
    p.text= buildtype
    pl = ET.SubElement(prjconf, 'Platform')
    pl.text = platform
    root.append(confitems)
    tree = ET.ElementTree(root)
    tree.write(ofname, encoding='utf-8', xml_declaration=True)

if __name__ == '__main__':
    runtest('sample.vcxproj')
