# Copyright 2014-2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, sys
import pickle
import re

from mesonbuild import compilers
from mesonbuild.build import BuildTarget
from mesonbuild.mesonlib import File
from . import backends
from .. import build
from .. import dependencies
from .. import mlog
import xml.etree.ElementTree as ET
import xml.dom.minidom
from ..mesonlib import MesonException
from ..environment import Environment

def split_o_flags_args(args):
    """
    Splits any /O args and returns them. Does not take care of flags overriding
    previous ones. Skips non-O flag arguments.

    ['/Ox', '/Ob1'] returns ['/Ox', '/Ob1']
    ['/Oxj', '/MP'] returns ['/Ox', '/Oj']
    """
    o_flags = []
    for arg in args:
        if not arg.startswith('/O'):
            continue
        flags = list(arg[2:])
        # Assume that this one can't be clumped with the others since it takes
        # an argument itself
        if 'b' in flags:
            o_flags.append(arg)
        else:
            o_flags += ['/O' + f for f in flags]
    return o_flags

class RegenInfo():
    def __init__(self, source_dir, build_dir, depfiles):
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.depfiles = depfiles

class Vs2010Backend(backends.Backend):
    def __init__(self, build):
        super().__init__(build)
        self.project_file_version = '10.0.30319.1'
        self.sources_conflicts = {}
        self.platform_toolset = None
        self.vs_version = '2010'

    def object_filename_from_source(self, target, source):
        basename = os.path.basename(source.fname)
        filename_without_extension = '.'.join(basename.split('.')[:-1])
        if basename in self.sources_conflicts[target.get_id()]:
            # If there are multiple source files with the same basename, we must resolve the conflict
            # by giving each a unique object output file.
            filename_without_extension = '.'.join(source.fname.split('.')[:-1]).replace('/', '_').replace('\\', '_')
        return filename_without_extension + '.' + self.environment.get_object_suffix()

    def resolve_source_conflicts(self):
        for name, target in self.build.targets.items():
            if not isinstance(target, BuildTarget):
                continue
            conflicts = {}
            for s in target.get_sources():
                if hasattr(s, 'held_object'):
                    s = s.held_object
                if not isinstance(s, File):
                    continue
                basename = os.path.basename(s.fname)
                conflicting_sources = conflicts.get(basename, None)
                if conflicting_sources is None:
                    conflicting_sources = []
                    conflicts[basename] = conflicting_sources
                conflicting_sources.append(s)
            self.sources_conflicts[target.get_id()] = {name: src_conflicts for name, src_conflicts in conflicts.items()
                                                       if len(src_conflicts) > 1}

    def generate_custom_generator_commands(self, target, parent_node):
        generator_output_files = []
        commands = []
        inputs = []
        outputs = []
        custom_target_include_dirs = []
        custom_target_output_files = []
        target_private_dir = self.relpath(self.get_target_private_dir(target), self.get_target_dir(target))
        down = self.target_to_build_root(target)
        for genlist in target.get_generated_sources():
            if isinstance(genlist, build.CustomTarget):
                for i in genlist.output:
                    # Path to the generated source from the current vcxproj dir via the build root
                    ipath = os.path.join(down, self.get_target_dir(genlist), i)
                    custom_target_output_files.append(ipath)
                idir = self.relpath(self.get_target_dir(genlist), self.get_target_dir(target))
                if idir not in custom_target_include_dirs:
                    custom_target_include_dirs.append(idir)
            else:
                generator = genlist.get_generator()
                exe = generator.get_exe()
                infilelist = genlist.get_infilelist()
                outfilelist = genlist.get_outfilelist()
                exe_arr = self.exe_object_to_cmd_array(exe)
                base_args = generator.get_arglist()
                for i in range(len(infilelist)):
                    if len(infilelist) == len(outfilelist):
                        sole_output = os.path.join(target_private_dir, outfilelist[i])
                    else:
                        sole_output = ''
                    curfile = infilelist[i]
                    infilename = os.path.join(self.environment.get_source_dir(), curfile)
                    outfiles_rel = genlist.get_outputs_for(curfile)
                    outfiles = [os.path.join(target_private_dir, of) for of in outfiles_rel]
                    generator_output_files += outfiles
                    args = [x.replace("@INPUT@", infilename).replace('@OUTPUT@', sole_output)\
                            for x in base_args]
                    args = self.replace_outputs(args, target_private_dir, outfiles_rel)
                    args = [x.replace("@SOURCE_DIR@", self.environment.get_source_dir()).replace("@BUILD_DIR@", target_private_dir)
                            for x in args]
                    fullcmd = exe_arr + self.replace_extra_args(args, genlist)
                    commands.append(' '.join(self.special_quote(fullcmd)))
                    inputs.append(infilename)
                    outputs.extend(outfiles)
        if len(commands) > 0:
            idgroup = ET.SubElement(parent_node, 'ItemDefinitionGroup')
            cbs = ET.SubElement(idgroup, 'CustomBuildStep')
            ET.SubElement(cbs, 'Command').text = '\r\n'.join(commands)
            ET.SubElement(cbs, 'Inputs').text = ";".join(inputs)
            ET.SubElement(cbs, 'Outputs').text = ';'.join(outputs)
            ET.SubElement(cbs, 'Message').text = 'Generating custom sources.'
            pg = ET.SubElement(parent_node, 'PropertyGroup')
            ET.SubElement(pg, 'CustomBuildBeforeTargets').text = 'ClCompile'
        return generator_output_files, custom_target_output_files, custom_target_include_dirs

    def generate(self, interp):
        self.resolve_source_conflicts()
        self.interpreter = interp
        target_machine = self.interpreter.builtin['target_machine'].cpu_family_method(None, None)
        if target_machine.endswith('64'):
            # amd64 or x86_64
            self.platform = 'x64'
        elif target_machine == 'x86':
            # x86
            self.platform = 'Win32'
        elif 'arm' in target_machine.lower():
            self.platform = 'ARM'
        else:
            raise MesonException('Unsupported Visual Studio platform: ' + target_machine)
        self.buildtype = self.environment.coredata.get_builtin_option('buildtype')
        sln_filename = os.path.join(self.environment.get_build_dir(), self.build.project_name + '.sln')
        projlist = self.generate_projects()
        self.gen_testproj('RUN_TESTS', os.path.join(self.environment.get_build_dir(), 'RUN_TESTS.vcxproj'))
        self.gen_regenproj('REGEN', os.path.join(self.environment.get_build_dir(), 'REGEN.vcxproj'))
        self.generate_solution(sln_filename, projlist)
        self.generate_regen_info()
        Vs2010Backend.touch_regen_timestamp(self.environment.get_build_dir())

    @staticmethod
    def get_regen_stampfile(build_dir):
        return os.path.join(os.path.join(build_dir, Environment.private_dir), 'regen.stamp')

    @staticmethod
    def touch_regen_timestamp(build_dir):
        with open(Vs2010Backend.get_regen_stampfile(build_dir), 'w'):
            pass

    def generate_regen_info(self):
        deps = self.get_regen_filelist()
        regeninfo = RegenInfo(self.environment.get_source_dir(),
                              self.environment.get_build_dir(),
                              deps)
        filename = os.path.join(self.environment.get_scratch_dir(),
                                'regeninfo.dump')
        with open(filename, 'wb') as f:
            pickle.dump(regeninfo, f)

    def get_obj_target_deps(self, obj_list):
        result = {}
        for o in obj_list:
            if isinstance(o, build.ExtractedObjects):
                result[o.target.get_id()] = True
        return result.keys()

    def determine_deps(self, p):
        all_deps = {}
        target = self.build.targets[p[0]]
        if isinstance(target, build.CustomTarget):
            for d in target.get_target_dependencies():
                all_deps[d.get_id()] = True
            return all_deps
        if isinstance(target, build.RunTarget):
            for d in [target.command] + target.args:
                if isinstance(d, build.BuildTarget):
                    all_deps[d.get_id()] = True
                return all_deps
        for ldep in target.link_targets:
            all_deps[ldep.get_id()] = True
        for objdep in self.get_obj_target_deps(target.objects):
            all_deps[objdep] = True
        for gendep in target.generated:
            if isinstance(gendep, build.CustomTarget):
                all_deps[gendep.get_id()] = True
            else:
                gen_exe = gendep.generator.get_exe()
                if isinstance(gen_exe, build.Executable):
                    all_deps[gen_exe.get_id()] = True
        return all_deps

    def generate_solution(self, sln_filename, projlist):
        with open(sln_filename, 'w') as ofile:
            ofile.write('Microsoft Visual Studio Solution File, Format '
                        'Version 11.00\n')
            ofile.write('# Visual Studio ' + self.vs_version + '\n')
            prj_templ = prj_line = 'Project("{%s}") = "%s", "%s", "{%s}"\n'
            for p in projlist:
                prj_line = prj_templ % (self.environment.coredata.guid,
                                        p[0], p[1], p[2])
                ofile.write(prj_line)
                all_deps = self.determine_deps(p)
                ofile.write('\tProjectSection(ProjectDependencies) = '
                            'postProject\n')
                regen_guid = self.environment.coredata.regen_guid
                ofile.write('\t\t{%s} = {%s}\n' % (regen_guid, regen_guid))
                for dep in all_deps.keys():
                    guid = self.environment.coredata.target_guids[dep]
                    ofile.write('\t\t{%s} = {%s}\n' % (guid, guid))
                ofile.write('EndProjectSection\n')
                ofile.write('EndProject\n')
            test_line = prj_templ % (self.environment.coredata.guid,
                                     'RUN_TESTS', 'RUN_TESTS.vcxproj',
                                     self.environment.coredata.test_guid)
            ofile.write(test_line)
            ofile.write('EndProject\n')
            regen_line = prj_templ % (self.environment.coredata.guid,
                                      'REGEN', 'REGEN.vcxproj',
                                      self.environment.coredata.regen_guid)
            ofile.write(regen_line)
            ofile.write('EndProject\n')
            ofile.write('Global\n')
            ofile.write('\tGlobalSection(SolutionConfigurationPlatforms) = '
                        'preSolution\n')
            ofile.write('\t\t%s|%s = %s|%s\n' %
                        (self.buildtype, self.platform, self.buildtype,
                         self.platform))
            ofile.write('\tEndGlobalSection\n')
            ofile.write('\tGlobalSection(ProjectConfigurationPlatforms) = '
                        'postSolution\n')
            ofile.write('\t\t{%s}.%s|%s.ActiveCfg = %s|%s\n' % 
                        (self.environment.coredata.regen_guid, self.buildtype,
                         self.platform, self.buildtype, self.platform))
            ofile.write('\t\t{%s}.%s|%s.Build.0 = %s|%s\n' %
                        (self.environment.coredata.regen_guid, self.buildtype,
                         self.platform, self.buildtype, self.platform))
            for p in projlist:
                ofile.write('\t\t{%s}.%s|%s.ActiveCfg = %s|%s\n' %
                            (p[2], self.buildtype, self.platform,
                             self.buildtype, self.platform))
                if not isinstance(self.build.targets[p[0]], build.RunTarget):
                    ofile.write('\t\t{%s}.%s|%s.Build.0 = %s|%s\n' %
                                (p[2], self.buildtype, self.platform,
                                 self.buildtype, self.platform))
            ofile.write('\t\t{%s}.%s|%s.ActiveCfg = %s|%s\n' %
                        (self.environment.coredata.test_guid, self.buildtype,
                         self.platform, self.buildtype, self.platform))
            ofile.write('\tEndGlobalSection\n')
            ofile.write('\tGlobalSection(SolutionProperties) = preSolution\n')
            ofile.write('\t\tHideSolutionNode = FALSE\n')
            ofile.write('\tEndGlobalSection\n')
            ofile.write('EndGlobal\n')

    def generate_projects(self):
        projlist = []
        comp = None
        for l, c in self.environment.coredata.compilers.items():
            if l == 'c' or l == 'cpp':
                comp = c
                break
        if comp is None:
            raise RuntimeError('C and C++ compilers missing.')
        for name, target in self.build.targets.items():
            outdir = os.path.join(self.environment.get_build_dir(), self.get_target_dir(target))
            fname = name + '.vcxproj'
            relname = os.path.join(target.subdir, fname)
            projfile = os.path.join(outdir, fname)
            uuid = self.environment.coredata.target_guids[name]
            self.gen_vcxproj(target, projfile, uuid, comp)
            projlist.append((name, relname, uuid))
        return projlist

    def split_sources(self, srclist):
        sources = []
        headers = []
        objects = []
        languages = []
        for i in srclist:
            if self.environment.is_header(i):
                headers.append(i)
            elif self.environment.is_object(i):
                objects.append(i)
            elif self.environment.is_source(i):
                sources.append(i)
                lang = self.lang_from_source_file(i)
                if lang not in languages:
                    languages.append(lang)
            elif self.environment.is_library(i):
                pass
            else:
                # Everything that is not an object or source file is considered a header.
                headers.append(i)
        return (sources, headers, objects, languages)

    def target_to_build_root(self, target):
        if target.subdir == '':
            return ''

        directories = os.path.normpath(target.subdir).split(os.sep)
        return os.sep.join(['..']*len(directories))

    def special_quote(self, arr):
        return ['&quot;%s&quot;' % i for i in arr]

    def create_basic_crap(self, target):
        project_name = target.name
        root = ET.Element('Project', {'DefaultTargets' : "Build",
                                      'ToolsVersion' : '4.0',
                                      'xmlns' : 'http://schemas.microsoft.com/developer/msbuild/2003'})
        confitems = ET.SubElement(root, 'ItemGroup', {'Label' : 'ProjectConfigurations'})
        prjconf = ET.SubElement(confitems, 'ProjectConfiguration',
                                {'Include' : self.buildtype + '|' + self.platform})
        p = ET.SubElement(prjconf, 'Configuration')
        p.text= self.buildtype
        pl = ET.SubElement(prjconf, 'Platform')
        pl.text = self.platform
        globalgroup = ET.SubElement(root, 'PropertyGroup', Label='Globals')
        guidelem = ET.SubElement(globalgroup, 'ProjectGuid')
        guidelem.text = self.environment.coredata.test_guid
        kw = ET.SubElement(globalgroup, 'Keyword')
        kw.text = self.platform + 'Proj'
        p = ET.SubElement(globalgroup, 'Platform')
        p.text= self.platform
        pname= ET.SubElement(globalgroup, 'ProjectName')
        pname.text = project_name
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.Default.props')
        type_config = ET.SubElement(root, 'PropertyGroup', Label='Configuration')
        ET.SubElement(type_config, 'ConfigurationType')
        ET.SubElement(type_config, 'CharacterSet').text = 'MultiByte'
        ET.SubElement(type_config, 'UseOfMfc').text = 'false'
        if self.platform_toolset:
            ET.SubElement(type_config, 'PlatformToolset').text = self.platform_toolset
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.props')
        direlem = ET.SubElement(root, 'PropertyGroup')
        fver = ET.SubElement(direlem, '_ProjectFileVersion')
        fver.text = self.project_file_version
        outdir = ET.SubElement(direlem, 'OutDir')
        outdir.text = '.\\'
        intdir = ET.SubElement(direlem, 'IntDir')
        intdir.text = target.get_id() + '\\'
        tname = ET.SubElement(direlem, 'TargetName')
        tname.text = target.name
        return root

    def gen_run_target_vcxproj(self, target, ofname, guid):
        root = self.create_basic_crap(target)
        action = ET.SubElement(root, 'ItemDefinitionGroup')
        customstep = ET.SubElement(action, 'PostBuildEvent')
        cmd_raw = [target.command] + target.args
        cmd = [sys.executable, os.path.join(self.environment.get_script_dir(), 'commandrunner.py'),
               self.environment.get_build_dir(), self.environment.get_source_dir(),
               self.get_target_dir(target)]
        for i in cmd_raw:
            if isinstance(i, build.BuildTarget):
                cmd.append(os.path.join(self.environment.get_build_dir(), self.get_target_filename(i)))
            elif isinstance(i, dependencies.ExternalProgram):
                cmd += i.fullpath
            else:
                cmd.append(i)
        cmd_templ = '''"%s" '''*len(cmd)
        ET.SubElement(customstep, 'Command').text = cmd_templ % tuple(cmd)
        ET.SubElement(customstep, 'Message').text = 'Running custom command.'
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.targets')
        tree = ET.ElementTree(root)
        tree.write(ofname, encoding='utf-8', xml_declaration=True)

    def gen_custom_target_vcxproj(self, target, ofname, guid):
        root = self.create_basic_crap(target)
        action = ET.SubElement(root, 'ItemDefinitionGroup')
        customstep = ET.SubElement(action, 'CustomBuildStep')
        (srcs, ofilenames, cmd) = self.eval_custom_target_command(target, True)
        cmd_templ = '''"%s" '''*len(cmd)
        ET.SubElement(customstep, 'Command').text = cmd_templ % tuple(cmd)
        ET.SubElement(customstep, 'Outputs').text = ';'.join(ofilenames)
        ET.SubElement(customstep, 'Inputs').text = ';'.join(srcs)
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.targets')
        tree = ET.ElementTree(root)
        tree.write(ofname, encoding='utf-8', xml_declaration=True)

    @classmethod
    def lang_from_source_file(cls, src):
        ext = src.split('.')[-1]
        if ext in compilers.c_suffixes:
            return 'c'
        if ext in compilers.cpp_suffixes:
            return 'cpp'
        raise MesonException('Could not guess language from source file %s.' % src)

    def add_pch(self, inc_cl, proj_to_src_dir, pch_sources, source_file):
        if len(pch_sources) <= 1:
            # We only need per file precompiled headers if we have more than 1 language.
            return
        lang = Vs2010Backend.lang_from_source_file(source_file)
        header = os.path.join(proj_to_src_dir, pch_sources[lang][0])
        pch_file = ET.SubElement(inc_cl, 'PrecompiledHeaderFile')
        pch_file.text = header
        pch_include = ET.SubElement(inc_cl, 'ForcedIncludeFiles')
        pch_include.text = header + ';%(ForcedIncludeFiles)'
        pch_out = ET.SubElement(inc_cl, 'PrecompiledHeaderOutputFile')
        pch_out.text = '$(IntDir)$(TargetName)-%s.pch' % lang

    def add_additional_options(self, source_file, parent_node, extra_args, has_additional_options_set):
        if has_additional_options_set:
            # We only need per file options if they were not set per project.
            return
        lang = Vs2010Backend.lang_from_source_file(source_file)
        ET.SubElement(parent_node, "AdditionalOptions").text = ' '.join(extra_args[lang]) + ' %(AdditionalOptions)'

    @staticmethod
    def has_objects(objects, additional_objects, generated_objects):
        # Ignore generated objects, those are automatically used by MSBuild for VS2010, because they are part of
        # the CustomBuildStep Outputs.
        return len(objects) + len(additional_objects) > 0

    @staticmethod
    def add_generated_objects(node, generated_objects):
        # Do not add generated objects to project file. Those are automatically used by MSBuild for VS2010, because
        # they are part of the CustomBuildStep Outputs.
        return

    @staticmethod
    def escape_preprocessor_define(define):
        # See: https://msdn.microsoft.com/en-us/library/bb383819.aspx
        table = str.maketrans({'%': '%25', '$': '%24', '@': '%40',
            "'": '%27', ';': '%3B', '?': '%3F', '*': '%2A',
            # We need to escape backslash because it'll be un-escaped by
            # Windows during process creation when it parses the arguments
            # Basically, this converts `\` to `\\`.
            '\\': '\\\\'})
        return define.translate(table)

    @staticmethod
    def escape_additional_option(option):
        # See: https://msdn.microsoft.com/en-us/library/bb383819.aspx
        table = str.maketrans({'%': '%25', '$': '%24', '@': '%40',
            "'": '%27', ';': '%3B', '?': '%3F', '*': '%2A', ' ': '%20',})
        option = option.translate(table)
        # Since we're surrounding the option with ", if it ends in \ that will
        # escape the " when the process arguments are parsed and the starting
        # " will not terminate. So we escape it if that's the case.  I'm not
        # kidding, this is how escaping works for process args on Windows.
        if option.endswith('\\'):
            option += '\\'
        return '"{}"'.format(option)

    @staticmethod
    def split_link_args(args):
        """
        Split a list of link arguments into three lists:
        * library search paths
        * library filenames (or paths)
        * other link arguments
        """
        lpaths = []
        libs = []
        other = []
        for arg in args:
            if arg.startswith('/LIBPATH:'):
                lpath = arg[9:]
                # De-dup library search paths by removing older entries when
                # a new one is found. This is necessary because unlike other
                # search paths such as the include path, the library is
                # searched for in the newest (right-most) search path first.
                if lpath in lpaths:
                    lpaths.remove(lpath)
                lpaths.append(lpath)
            # It's ok if we miss libraries with non-standard extensions here.
            # They will go into the general link arguments.
            elif arg.endswith('.lib') or arg.endswith('.a'):
                # De-dup
                if arg not in libs:
                    libs.append(arg)
            else:
                other.append(arg)
        return (lpaths, libs, other)

    def gen_vcxproj(self, target, ofname, guid, compiler):
        mlog.debug('Generating vcxproj %s.' % target.name)
        entrypoint = 'WinMainCRTStartup'
        subsystem = 'Windows'
        if isinstance(target, build.Executable):
            conftype = 'Application'
            if not target.gui_app:
                subsystem = 'Console'
                entrypoint = 'mainCRTStartup'
        elif isinstance(target, build.StaticLibrary):
            conftype = 'StaticLibrary'
        elif isinstance(target, build.SharedLibrary):
            conftype = 'DynamicLibrary'
            entrypoint = '_DllMainCrtStartup'
        elif isinstance(target, build.CustomTarget):
            return self.gen_custom_target_vcxproj(target, ofname, guid)
        elif isinstance(target, build.RunTarget):
            return self.gen_run_target_vcxproj(target, ofname, guid)
        else:
            raise MesonException('Unknown target type for %s' % target.get_basename())
        # Prefix to use to access the build root from the vcxproj dir
        down = self.target_to_build_root(target)
        # Prefix to use to access the source tree's root from the vcxproj dir
        proj_to_src_root = os.path.join(down, self.build_to_src)
        # Prefix to use to access the source tree's subdir from the vcxproj dir
        proj_to_src_dir = os.path.join(proj_to_src_root, target.subdir)
        (sources, headers, objects, languages) = self.split_sources(target.sources)
        buildtype_args = compiler.get_buildtype_args(self.buildtype)
        buildtype_link_args = compiler.get_buildtype_linker_args(self.buildtype)
        project_name = target.name
        target_name = target.name
        root = ET.Element('Project', {'DefaultTargets' : "Build",
                                      'ToolsVersion' : '4.0',
                                      'xmlns' : 'http://schemas.microsoft.com/developer/msbuild/2003'})
        confitems = ET.SubElement(root, 'ItemGroup', {'Label' : 'ProjectConfigurations'})
        prjconf = ET.SubElement(confitems, 'ProjectConfiguration',
                                {'Include' : self.buildtype + '|' + self.platform})
        p = ET.SubElement(prjconf, 'Configuration')
        p.text= self.buildtype
        pl = ET.SubElement(prjconf, 'Platform')
        pl.text = self.platform
        # Globals
        globalgroup = ET.SubElement(root, 'PropertyGroup', Label='Globals')
        guidelem = ET.SubElement(globalgroup, 'ProjectGuid')
        guidelem.text = guid
        kw = ET.SubElement(globalgroup, 'Keyword')
        kw.text = self.platform + 'Proj'
        ns = ET.SubElement(globalgroup, 'RootNamespace')
        ns.text = target_name
        p = ET.SubElement(globalgroup, 'Platform')
        p.text= self.platform
        pname= ET.SubElement(globalgroup, 'ProjectName')
        pname.text = project_name
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.Default.props')
        # Start configuration
        type_config = ET.SubElement(root, 'PropertyGroup', Label='Configuration')
        ET.SubElement(type_config, 'ConfigurationType').text = conftype
        ET.SubElement(type_config, 'CharacterSet').text = 'MultiByte'
        if self.platform_toolset:
            ET.SubElement(type_config, 'PlatformToolset').text = self.platform_toolset
        # FIXME: Meson's LTO support needs to be integrated here
        ET.SubElement(type_config, 'WholeProgramOptimization').text = 'false'
        # Let VS auto-set the RTC level
        ET.SubElement(type_config, 'BasicRuntimeChecks').text = 'Default'
        o_flags = split_o_flags_args(buildtype_args)
        if '/Oi' in o_flags:
            ET.SubElement(type_config, 'IntrinsicFunctions').text = 'true'
        if '/Ob1' in o_flags:
            ET.SubElement(type_config, 'InlineFunctionExpansion').text = 'OnlyExplicitInline'
        elif '/Ob2' in o_flags:
            ET.SubElement(type_config, 'InlineFunctionExpansion').text = 'AnySuitable'
        # Size-preserving flags
        if '/Os' in o_flags:
            ET.SubElement(type_config, 'FavorSizeOrSpeed').text = 'Size'
        else:
            ET.SubElement(type_config, 'FavorSizeOrSpeed').text = 'Speed'
        # Incremental linking increases code size
        if '/INCREMENTAL:NO' in buildtype_link_args:
            ET.SubElement(type_config, 'LinkIncremental').text = 'false'
        # CRT type; debug or release
        if '/MDd' in buildtype_args:
            ET.SubElement(type_config, 'UseDebugLibraries').text = 'true'
            ET.SubElement(type_config, 'RuntimeLibrary').text = 'MultiThreadedDebugDLL'
        else:
            ET.SubElement(type_config, 'UseDebugLibraries').text = 'false'
            ET.SubElement(type_config, 'RuntimeLibrary').text = 'MultiThreadedDLL'
        # Debug format
        if '/ZI' in buildtype_args:
            ET.SubElement(type_config, 'DebugInformationFormat').text = 'EditAndContinue'
        elif '/Zi' in buildtype_args:
            ET.SubElement(type_config, 'DebugInformationFormat').text = 'ProgramDatabase'
        elif '/Z7' in buildtype_args:
            ET.SubElement(type_config, 'DebugInformationFormat').text = 'OldStyle'
        # Generate Debug info
        if '/DEBUG' in buildtype_link_args:
            ET.SubElement(type_config, 'GenerateDebugInformation').text = 'true'
        # Runtime checks
        if '/RTC1' in buildtype_args:
            ET.SubElement(type_config, 'BasicRuntimeChecks').text = 'EnableFastChecks'
        elif '/RTCu' in buildtype_args:
            ET.SubElement(type_config, 'BasicRuntimeChecks').text = 'UninitializedLocalUsageCheck'
        elif '/RTCs' in buildtype_args:
            ET.SubElement(type_config, 'BasicRuntimeChecks').text = 'StackFrameRuntimeCheck'
        # Optimization flags
        if '/Ox' in o_flags:
            ET.SubElement(type_config, 'Optimization').text = 'Full'
        elif '/O2' in o_flags:
            ET.SubElement(type_config, 'Optimization').text = 'MaxSpeed'
        elif '/O1' in o_flags:
            ET.SubElement(type_config, 'Optimization').text = 'MinSpace'
        elif '/Od' in o_flags:
            ET.SubElement(type_config, 'Optimization').text = 'Disabled'
        # Warning level
        warning_level = self.environment.coredata.get_builtin_option('warning_level')
        ET.SubElement(type_config, 'WarningLevel').text = 'Level' + warning_level
        # End configuration
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.props')
        generated_files, custom_target_output_files, generated_files_include_dirs = self.generate_custom_generator_commands(target, root)
        (gen_src, gen_hdrs, gen_objs, gen_langs) = self.split_sources(generated_files)
        (custom_src, custom_hdrs, custom_objs, custom_langs) = self.split_sources(custom_target_output_files)
        gen_src += custom_src
        gen_hdrs += custom_hdrs
        gen_langs += custom_langs
        # Project information
        direlem = ET.SubElement(root, 'PropertyGroup')
        fver = ET.SubElement(direlem, '_ProjectFileVersion')
        fver.text = self.project_file_version
        outdir = ET.SubElement(direlem, 'OutDir')
        outdir.text = '.\\'
        intdir = ET.SubElement(direlem, 'IntDir')
        intdir.text = target.get_id() + '\\'
        tfilename = os.path.splitext(target.get_filename())
        ET.SubElement(direlem, 'TargetName').text = tfilename[0]
        ET.SubElement(direlem, 'TargetExt').text = tfilename[1]

        # Build information
        compiles = ET.SubElement(root, 'ItemDefinitionGroup')
        clconf = ET.SubElement(compiles, 'ClCompile')
        inc_dirs = ['.', self.relpath(self.get_target_private_dir(target), self.get_target_dir(target)),
                    proj_to_src_dir] + generated_files_include_dirs

        extra_args = {'c': [], 'cpp': []}
        for l, args in self.environment.coredata.external_args.items():
            if l in extra_args:
                extra_args[l] += args
        for l, args in self.build.global_args.items():
            if l in extra_args:
                extra_args[l] += args
        for l, args in target.extra_args.items():
            if l in extra_args:
                extra_args[l] += compiler.unix_compile_flags_to_native(args)
        # FIXME all the internal flags of VS (optimization etc) are represented
        # by their own XML elements. In theory we should split all flags to those
        # that have an XML element and those that don't and serialise them
        # properly. This is a crapton of work for no real gain, so just dump them
        # here.
        general_args = compiler.get_option_compile_args(self.environment.coredata.compiler_options)
        for d in target.get_external_deps():
            # Cflags required by external deps might have UNIX-specific flags,
            # so filter them out if needed
            d_compile_args = compiler.unix_compile_flags_to_native(d.get_compile_args())
            for arg in d_compile_args:
                if arg.startswith('-I') or arg.startswith('/I'):
                    inc_dir = arg[2:]
                    # De-dup
                    if inc_dir not in inc_dirs:
                        inc_dirs.append(inc_dir)
                else:
                    general_args.append(arg)

        defines = []
        # Split preprocessor defines and include directories out of the list of
        # all extra arguments. The rest go into %(AdditionalOptions).
        for l, args in extra_args.items():
            extra_args[l] = []
            for arg in args:
                if arg.startswith('-D') or arg.startswith('/D'):
                    define = self.escape_preprocessor_define(arg[2:])
                    # De-dup
                    if define not in defines:
                        defines.append(define)
                elif arg.startswith('-I') or arg.startswith('/I'):
                    inc_dir = arg[2:]
                    # De-dup
                    if inc_dir not in inc_dirs:
                        inc_dirs.append(inc_dir)
                else:
                    extra_args[l].append(self.escape_additional_option(arg))

        languages += gen_langs
        has_language_specific_args = any(l != extra_args['c'] for l in extra_args.values())
        additional_options_set = False
        if not has_language_specific_args or len(languages) == 1:
            if len(languages) == 0:
                extra_args = []
            else:
                extra_args = extra_args[languages[0]]
            extra_args = general_args + extra_args
            if len(extra_args) > 0:
                extra_args.append('%(AdditionalOptions)')
                ET.SubElement(clconf, "AdditionalOptions").text = ' '.join(extra_args)
            additional_options_set = True

        for d in target.include_dirs:
            for i in d.incdirs:
                curdir = os.path.join(d.curdir, i)
                inc_dirs.append(self.relpath(curdir, target.subdir)) # build dir
                inc_dirs.append(os.path.join(proj_to_src_root, curdir)) # src dir
            for i in d.get_extra_build_dirs():
                curdir = os.path.join(d.curdir, i)
                inc_dirs.append(self.relpath(curdir, target.subdir))  # build dir

        inc_dirs.append('%(AdditionalIncludeDirectories)')
        ET.SubElement(clconf, 'AdditionalIncludeDirectories').text = ';'.join(inc_dirs)
        ET.SubElement(clconf, 'PreprocessorDefinitions').text = ';'.join(defines)
        rebuild = ET.SubElement(clconf, 'MinimalRebuild')
        rebuild.text = 'true'
        funclink = ET.SubElement(clconf, 'FunctionLevelLinking')
        funclink.text = 'true'
        pch_node = ET.SubElement(clconf, 'PrecompiledHeader')
        pch_sources = {}
        for lang in ['c', 'cpp']:
            pch = target.get_pch(lang)
            if len(pch) == 0:
                continue
            pch_node.text = 'Use'
            pch_sources[lang] = [pch[0], pch[1], lang]
        if len(pch_sources) == 1:
            # If there is only 1 language with precompiled headers, we can use it for the entire project, which
            # is cleaner than specifying it for each source file.
            pch_source = list(pch_sources.values())[0]
            header = os.path.join(proj_to_src_dir, pch_source[0])
            pch_file = ET.SubElement(clconf, 'PrecompiledHeaderFile')
            pch_file.text = header
            pch_include = ET.SubElement(clconf, 'ForcedIncludeFiles')
            pch_include.text = header + ';%(ForcedIncludeFiles)'
            pch_out = ET.SubElement(clconf, 'PrecompiledHeaderOutputFile')
            pch_out.text = '$(IntDir)$(TargetName)-%s.pch' % pch_source[2]

        resourcecompile = ET.SubElement(compiles, 'ResourceCompile')
        ET.SubElement(resourcecompile, 'PreprocessorDefinitions')
        link = ET.SubElement(compiles, 'Link')
        # Put all language args here, too.
        extra_link_args = compiler.get_option_link_args(self.environment.coredata.compiler_options)
        # FIXME: Can these buildtype linker args be added as tags in the
        # vcxproj file (similar to buildtype compiler args) instead of in
        # AdditionalOptions?
        extra_link_args += compiler.get_buildtype_linker_args(self.buildtype)
        for l in self.environment.coredata.external_link_args.values():
            extra_link_args += l
        if not isinstance(target, build.StaticLibrary):
            extra_link_args += target.link_args
            # External deps must be last because target link libraries may depend on them.
            for dep in target.get_external_deps():
                extra_link_args += dep.get_link_args()
            for d in target.get_dependencies():
                if isinstance(d, build.StaticLibrary):
                    for dep in d.get_external_deps():
                        extra_link_args += dep.get_link_args()
        extra_link_args = compiler.unix_link_flags_to_native(extra_link_args)
        (additional_libpaths, additional_links, extra_link_args) = self.split_link_args(extra_link_args)
        if len(extra_link_args) > 0:
            extra_link_args.append('%(AdditionalOptions)')
            ET.SubElement(link, "AdditionalOptions").text = ' '.join(extra_link_args)
        if len(additional_libpaths) > 0:
            additional_libpaths.insert(0, '%(AdditionalLibraryDirectories)')
            ET.SubElement(link, 'AdditionalLibraryDirectories').text = ';'.join(additional_libpaths)

        # Add more libraries to be linked if needed
        for t in target.get_dependencies():
            lobj = self.build.targets[t.get_id()]
            linkname = os.path.join(down, self.get_target_filename_for_linking(lobj))
            additional_links.append(linkname)
        for lib in self.get_custom_target_provided_libraries(target):
            additional_links.append(self.relpath(lib, self.get_target_dir(target)))
        additional_objects = []
        for o in self.flatten_object_list(target, down):
            assert(isinstance(o, str))
            additional_objects.append(o)
        for o in custom_objs:
            additional_objects.append(self.relpath(o, self.get_target_dir(target)))
        if len(additional_links) > 0:
            additional_links.append('%(AdditionalDependencies)')
            ET.SubElement(link, 'AdditionalDependencies').text = ';'.join(additional_links)
        ofile = ET.SubElement(link, 'OutputFile')
        ofile.text = '$(OutDir)%s' % target.get_filename()
        subsys = ET.SubElement(link, 'SubSystem')
        subsys.text = subsystem
        if isinstance(target, build.SharedLibrary):
            # DLLs built with MSVC always have an import library except when
            # they're data-only DLLs, but we don't support those yet.
            ET.SubElement(link, 'ImportLibrary').text = target.get_import_filename()
            # Add module definitions file, if provided
            if target.vs_module_defs:
                relpath = os.path.join(down, target.vs_module_defs.rel_to_builddir(self.build_to_src))
                ET.SubElement(link, 'ModuleDefinitionFile').text = relpath
        if '/ZI' in buildtype_args or '/Zi' in buildtype_args:
            pdb = ET.SubElement(link, 'ProgramDataBaseFileName')
            pdb.text = '$(OutDir}%s.pdb' % target_name
        if isinstance(target, build.Executable):
            ET.SubElement(link, 'EntryPointSymbol').text = entrypoint
        targetmachine = ET.SubElement(link, 'TargetMachine')
        targetplatform = self.platform.lower()
        if targetplatform == 'win32':
            targetmachine.text = 'MachineX86'
        elif targetplatform == 'x64':
            targetmachine.text = 'MachineX64'
        elif targetplatform == 'arm':
            targetmachine.text = 'MachineARM'
        else:
            raise MesonException('Unsupported Visual Studio target machine: ' + targetmachine)

        extra_files = target.extra_files
        if len(headers) + len(gen_hdrs) + len(extra_files) > 0:
            inc_hdrs = ET.SubElement(root, 'ItemGroup')
            for h in headers:
                relpath = os.path.join(down, h.rel_to_builddir(self.build_to_src))
                ET.SubElement(inc_hdrs, 'CLInclude', Include=relpath)
            for h in gen_hdrs:
                ET.SubElement(inc_hdrs, 'CLInclude', Include=h)
            for h in target.extra_files:
                relpath = os.path.join(proj_to_src_dir, h)
                ET.SubElement(inc_hdrs, 'CLInclude', Include=relpath)

        if len(sources) + len(gen_src) + len(pch_sources) > 0:
            inc_src = ET.SubElement(root, 'ItemGroup')
            for s in sources:
                relpath = os.path.join(down, s.rel_to_builddir(self.build_to_src))
                inc_cl = ET.SubElement(inc_src, 'CLCompile', Include=relpath)
                self.add_pch(inc_cl, proj_to_src_dir, pch_sources, s)
                self.add_additional_options(s, inc_cl, extra_args, additional_options_set)
                basename = os.path.basename(s.fname)
                if basename in self.sources_conflicts[target.get_id()]:
                    ET.SubElement(inc_cl, 'ObjectFileName').text = "$(IntDir)" + self.object_filename_from_source(target, s)
            for s in gen_src:
                inc_cl = ET.SubElement(inc_src, 'CLCompile', Include=s)
                self.add_pch(inc_cl, proj_to_src_dir, pch_sources, s)
                self.add_additional_options(s, inc_cl, extra_args, additional_options_set)
            for lang in pch_sources:
                header, impl, suffix = pch_sources[lang]
                relpath = os.path.join(proj_to_src_dir, impl)
                inc_cl = ET.SubElement(inc_src, 'CLCompile', Include=relpath)
                pch = ET.SubElement(inc_cl, 'PrecompiledHeader')
                pch.text = 'Create'
                pch_out = ET.SubElement(inc_cl, 'PrecompiledHeaderOutputFile')
                pch_out.text = '$(IntDir)$(TargetName)-%s.pch' % suffix
                pch_file = ET.SubElement(inc_cl, 'PrecompiledHeaderFile')
                # MSBuild searches for the header relative from the implementation, so we have to use
                # just the file name instead of the relative path to the file.
                pch_file.text = os.path.split(header)[1]
                self.add_additional_options(impl, inc_cl, extra_args, additional_options_set)

        if self.has_objects(objects, additional_objects, gen_objs):
            inc_objs = ET.SubElement(root, 'ItemGroup')
            for s in objects:
                relpath = os.path.join(down, s.rel_to_builddir(self.build_to_src))
                ET.SubElement(inc_objs, 'Object', Include=relpath)
            for s in additional_objects:
                ET.SubElement(inc_objs, 'Object', Include=s)
            self.add_generated_objects(inc_objs, gen_objs)

        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.targets')
        # Reference the regen target.
        ig = ET.SubElement(root, 'ItemGroup')
        pref = ET.SubElement(ig, 'ProjectReference', Include=os.path.join(self.environment.get_build_dir(), 'REGEN.vcxproj'))
        ET.SubElement(pref, 'Project').text = self.environment.coredata.regen_guid
        tree = ET.ElementTree(root)
        tree.write(ofname, encoding='utf-8', xml_declaration=True)
        # ElementTree can not do prettyprinting so do it manually
        doc = xml.dom.minidom.parse(ofname)
        with open(ofname, 'w') as of:
            of.write(doc.toprettyxml())
        # World of horror! Python insists on not quoting quotes and
        # fixing the escaped &quot; into &amp;quot; whereas MSVS
        # requires quoted but not fixed elements. Enter horrible hack.
        with open(ofname, 'r') as of:
            txt = of.read()
        with open(ofname, 'w') as of:
            of.write(txt.replace('&amp;quot;', '&quot;'))

    def gen_regenproj(self, project_name, ofname):
        root = ET.Element('Project', {'DefaultTargets': 'Build',
                                      'ToolsVersion' : '4.0',
                                      'xmlns' : 'http://schemas.microsoft.com/developer/msbuild/2003'})
        confitems = ET.SubElement(root, 'ItemGroup', {'Label' : 'ProjectConfigurations'})
        prjconf = ET.SubElement(confitems, 'ProjectConfiguration', 
                                {'Include' : self.buildtype + '|' + self.platform})
        p = ET.SubElement(prjconf, 'Configuration')
        p.text= self.buildtype
        pl = ET.SubElement(prjconf, 'Platform')
        pl.text = self.platform
        globalgroup = ET.SubElement(root, 'PropertyGroup', Label='Globals')
        guidelem = ET.SubElement(globalgroup, 'ProjectGuid')
        guidelem.text = self.environment.coredata.test_guid
        kw = ET.SubElement(globalgroup, 'Keyword')
        kw.text = self.platform + 'Proj'
        p = ET.SubElement(globalgroup, 'Platform')
        p.text = self.platform
        pname= ET.SubElement(globalgroup, 'ProjectName')
        pname.text = project_name
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.Default.props')
        type_config = ET.SubElement(root, 'PropertyGroup', Label='Configuration')
        ET.SubElement(type_config, 'ConfigurationType').text = "Utility"
        ET.SubElement(type_config, 'CharacterSet').text = 'MultiByte'
        ET.SubElement(type_config, 'UseOfMfc').text = 'false'
        if self.platform_toolset:
            ET.SubElement(type_config, 'PlatformToolset').text = self.platform_toolset
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.props')
        direlem = ET.SubElement(root, 'PropertyGroup')
        fver = ET.SubElement(direlem, '_ProjectFileVersion')
        fver.text = self.project_file_version
        outdir = ET.SubElement(direlem, 'OutDir')
        outdir.text = '.\\'
        intdir = ET.SubElement(direlem, 'IntDir')
        intdir.text = 'regen-temp\\'
        tname = ET.SubElement(direlem, 'TargetName')
        tname.text = project_name

        action = ET.SubElement(root, 'ItemDefinitionGroup')
        midl = ET.SubElement(action, 'Midl')
        ET.SubElement(midl, "AdditionalIncludeDirectories").text = '%(AdditionalIncludeDirectories)'
        ET.SubElement(midl, "OutputDirectory").text = '$(IntDir)'
        ET.SubElement(midl, 'HeaderFileName').text = '%(Filename).h'
        ET.SubElement(midl, 'TypeLibraryName').text = '%(Filename).tlb'
        ET.SubElement(midl, 'InterfaceIdentifierFilename').text = '%(Filename)_i.c'
        ET.SubElement(midl, 'ProxyFileName').text = '%(Filename)_p.c'
        regen_command = [sys.executable,
                         self.environment.get_build_command(),
                         '--internal',
                         'regencheck']
        private_dir = self.environment.get_scratch_dir()
        cmd_templ = '''setlocal
"%s" "%s"
if %%errorlevel%% neq 0 goto :cmEnd
:cmEnd
endlocal & call :cmErrorLevel %%errorlevel%% & goto :cmDone
:cmErrorLevel
exit /b %%1
:cmDone
if %%errorlevel%% neq 0 goto :VCEnd'''
        igroup = ET.SubElement(root, 'ItemGroup')
        rulefile = os.path.join(self.environment.get_scratch_dir(), 'regen.rule')
        if not os.path.exists(rulefile):
            with open(rulefile, 'w') as f:
                f.write("# Meson regen file.")
        custombuild = ET.SubElement(igroup, 'CustomBuild', Include=rulefile)
        message = ET.SubElement(custombuild, 'Message')
        message.text = 'Checking whether solution needs to be regenerated.'
        ET.SubElement(custombuild, 'Command').text = cmd_templ % \
            ('" "'.join(regen_command), private_dir)
        ET.SubElement(custombuild, 'Outputs').text = Vs2010Backend.get_regen_stampfile(self.environment.get_build_dir())
        deps = self.get_regen_filelist()
        ET.SubElement(custombuild, 'AdditionalInputs').text = ';'.join(deps)
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.targets')
        ET.SubElement(root, 'ImportGroup', Label='ExtensionTargets')
        tree = ET.ElementTree(root)
        tree.write(ofname, encoding='utf-8', xml_declaration=True)

    def gen_testproj(self, target_name, ofname):
        project_name = target_name
        root = ET.Element('Project', {'DefaultTargets' : "Build",
                                      'ToolsVersion' : '4.0',
                                      'xmlns' : 'http://schemas.microsoft.com/developer/msbuild/2003'})
        confitems = ET.SubElement(root, 'ItemGroup', {'Label' : 'ProjectConfigurations'})
        prjconf = ET.SubElement(confitems, 'ProjectConfiguration',
                                {'Include' : self.buildtype + '|' + self.platform})
        p = ET.SubElement(prjconf, 'Configuration')
        p.text= self.buildtype
        pl = ET.SubElement(prjconf, 'Platform')
        pl.text = self.platform
        globalgroup = ET.SubElement(root, 'PropertyGroup', Label='Globals')
        guidelem = ET.SubElement(globalgroup, 'ProjectGuid')
        guidelem.text = self.environment.coredata.test_guid
        kw = ET.SubElement(globalgroup, 'Keyword')
        kw.text = self.platform + 'Proj'
        p = ET.SubElement(globalgroup, 'Platform')
        p.text= self.platform
        pname= ET.SubElement(globalgroup, 'ProjectName')
        pname.text = project_name
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.Default.props')
        type_config = ET.SubElement(root, 'PropertyGroup', Label='Configuration')
        ET.SubElement(type_config, 'ConfigurationType')
        ET.SubElement(type_config, 'CharacterSet').text = 'MultiByte'
        ET.SubElement(type_config, 'UseOfMfc').text = 'false'
        if self.platform_toolset:
            ET.SubElement(type_config, 'PlatformToolset').text = self.platform_toolset
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.props')
        direlem = ET.SubElement(root, 'PropertyGroup')
        fver = ET.SubElement(direlem, '_ProjectFileVersion')
        fver.text = self.project_file_version
        outdir = ET.SubElement(direlem, 'OutDir')
        outdir.text = '.\\'
        intdir = ET.SubElement(direlem, 'IntDir')
        intdir.text = 'test-temp\\'
        tname = ET.SubElement(direlem, 'TargetName')
        tname.text = target_name

        action = ET.SubElement(root, 'ItemDefinitionGroup')
        midl = ET.SubElement(action, 'Midl')
        ET.SubElement(midl, "AdditionalIncludeDirectories").text = '%(AdditionalIncludeDirectories)'
        ET.SubElement(midl, "OutputDirectory").text = '$(IntDir)'
        ET.SubElement(midl, 'HeaderFileName').text = '%(Filename).h'
        ET.SubElement(midl, 'TypeLibraryName').text = '%(Filename).tlb'
        ET.SubElement(midl, 'InterfaceIdentifierFilename').text = '%(Filename)_i.c'
        ET.SubElement(midl, 'ProxyFileName').text = '%(Filename)_p.c'
        postbuild = ET.SubElement(action, 'PostBuildEvent')
        ET.SubElement(postbuild, 'Message')
        test_command = [sys.executable,
                        self.environment.get_build_command(),
                        '--internal',
                        'test']
        cmd_templ = '''setlocal
"%s" "%s"
if %%errorlevel%% neq 0 goto :cmEnd
:cmEnd
endlocal & call :cmErrorLevel %%errorlevel%% & goto :cmDone
:cmErrorLevel
exit /b %%1
:cmDone
if %%errorlevel%% neq 0 goto :VCEnd'''
        test_data = self.serialise_tests()[0]
        ET.SubElement(postbuild, 'Command').text =\
            cmd_templ % ('" "'.join(test_command), test_data)
        ET.SubElement(root, 'Import', Project='$(VCTargetsPath)\Microsoft.Cpp.targets')
        tree = ET.ElementTree(root)
        tree.write(ofname, encoding='utf-8', xml_declaration=True)
        # ElementTree can not do prettyprinting so do it manually
        #doc = xml.dom.minidom.parse(ofname)
        #open(ofname, 'w').write(doc.toprettyxml())
