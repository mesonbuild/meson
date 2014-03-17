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
import xml.dom.minidom

def runtest(ofname):
    buildtype = 'Debug'
    platform = "Win32"
    project_name = 'prog'
    target_name = 'prog'
    subsystem = 'console'
    project_file_version = '10.0.30319.1'
    guid = '{4A8C542D-A4C3-AC4A-A85A-E2A893CCB716}'
    root = ET.Element('Project', {'DefaultTargets' : "Build",
                                  'ToolsVersion' : '4.0',
                                  'xmlns' : 'http://schemas.microsoft.com/developer/msbuild/2003'})
    confitems = ET.SubElement(root, 'ItemGroup', {'Label' : 'ProjectConfigurations'})
    prjconf = ET.SubElement(confitems, 'ProjectConfiguration', {'Include' : 'Debug|Win32'})
    p = ET.SubElement(prjconf, 'Configuration')
    p.text= buildtype
    pl = ET.SubElement(prjconf, 'Platform')
    pl.text = platform
    globalgroup = ET.SubElement(root, 'PropertyGroups', Label='Globals')
    guidelem = ET.SubElement(globalgroup, 'ProjectGUID')
    guidelem.text = guid
    kw = ET.SubElement(globalgroup, 'Keyword')
    kw.text = 'Win32Proj'
    p = ET.SubElement(globalgroup, 'Platform')
    p.text= platform
    pname= ET.SubElement(globalgroup, 'ProjectName')
    pname.text = project_name
    ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.Default.props')
    direlem = ET.SubElement(root, 'PropertyGroup')
    fver = ET.SubElement(direlem, '_ProjectFileVersion')
    fver.text = project_file_version
    outdir = ET.SubElement(direlem, 'OutDir')
    outdir.text = './'
    intdir = ET.SubElement(direlem, 'IntDir')
    intdir.text = 'obj'
    tname = ET.SubElement(direlem, 'TargetName')
    tname.text = target_name
    inclinc = ET.SubElement(direlem, 'LinkIncremental')
    inclinc.text = 'true'

    compiles = ET.SubElement(root, 'ItemDefinitionGroup')
    clconf = ET.SubElement(compiles, 'ClCompile')
    opt = ET.SubElement(clconf, 'Optimization')
    opt.text = 'disabled'
    preproc = ET.SubElement(clconf, 'PreprocessorDefinitions')
    rebuild = ET.SubElement(clconf, 'MinimalRebuild')
    rebuild.text = 'true'
    rtlib = ET.SubElement(clconf, 'RuntimeLibrary')
    rtlib.text = 'MultiThreadedDebugDLL'
    funclink = ET.SubElement(clconf, 'FunctionLevelLinking')
    funclink.text = 'true'
    pch = ET.SubElement(clconf, 'PrecompiledHeader')
    warnings = ET.SubElement(clconf, 'WarningLevel')
    warnings.text = 'Level3'
    debinfo = ET.SubElement(clconf, 'DebugInformationFormat')
    debinfo.text = 'EditAndContinue'
    resourcecompile = ET.SubElement(compiles, 'ResourceCompile')
    respreproc = ET.SubElement(resourcecompile, 'PreprocessorDefinitions')
    link = ET.SubElement(compiles, 'Link')
    ofile = ET.SubElement(link, 'OutputFile')
    ofile.text = '$(OutDir)prog.exe'
    addlibdir = ET.SubElement(link, 'AdditionalLibraryDirectories')
    addlibdir.text = '%(AdditionalLibraryDirectories)'
    subsys = ET.SubElement(link, 'SubSystem')
    subsys.text = subsystem
    gendeb = ET.SubElement(link, 'GenerateDebugInformation')
    gendeb.text = 'true'
    pdb = ET.SubElement(link, 'ProgramDataBaseFileName')
    pdb.text = '$(OutDir}prog.pdb'
    entrypoint = ET.SubElement(link, 'EntryPointSymbol')
    entrypoint.text = 'mainCRTStartup'
    targetmachine = ET.SubElement(link, 'TargetMachine')
    targetmachine.text = 'MachineX86'

    inc_files = ET.SubElement(root, 'ItemGroup')
    ET.SubElement(inc_files, 'CLInclude', Include='prog.h')
    inc_src = ET.SubElement(root, 'ItemGroup')
    ET.SubElement(inc_src, 'ClCompile', Include='prog.cpp')

    tree = ET.ElementTree(root)
    tree.write(ofname, encoding='utf-8', xml_declaration=True)
    # ElementTree can not do prettyprinting so do it manually
    doc = xml.dom.minidom.parse(ofname)
    open(ofname, 'w').write(doc.toprettyxml())

if __name__ == '__main__':
    runtest('sample.vcxproj')
