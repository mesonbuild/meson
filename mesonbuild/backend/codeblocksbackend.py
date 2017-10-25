# Copyright 2014-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shutil
import xml.dom.minidom
import xml.etree.ElementTree as ET

from . import backends
from .ninjabackend import NinjaBackend
from ..mesonlib import MesonException
from .. import build, mlog

class CodeBlocksBackend(backends.Backend):
    def __init__(self, build):
        super().__init__(build)
        self.ninja = NinjaBackend(build)

    def generate(self, interp):
        self.ninja.generate(interp)
        self.ninja_bin = shutil.which(self.ninja.ninja_command)
        self.interpreter = interp
        self.target_system = self.interpreter.builtin['target_machine'].system_method(None, None)

        cbp_filename = os.path.join(self.environment.get_build_dir(), self.build.project_name + '.cbp')
        self.gen_cbp(cbp_filename)

    BUILD_OPTION_STATIC_LIBRARY = 2
    BUILD_OPTION_SHARED_LIBRARY = 3
    BUILD_OPTION_COMMANDS_ONLY = 4

    def gen_cbp(self, ofname):
        mlog.debug('Generating cbp %s.' % ofname)
        root_el = ET.Element('CodeBlocks_project_file')

        ET.SubElement(root_el, 'FileVersion', {'major': str(self.CBP_VERSION_MAJOR), 'minor': str(self.CBP_VERSION_MINOR)})
        project_el = ET.SubElement(root_el, 'Project')
        ET.SubElement(project_el, 'Option', {'title': self.build.project_name})
        ET.SubElement(project_el, 'Option', {'makefile_is_custom': '1'})

        compiler_ids = set(t.id for t in self.build.compilers.values())
        if len(compiler_ids) != 1:
            MesonException('A project can only have one compiler')
        compiler_id = compiler_ids.pop()
        ET.SubElement(project_el, 'Option', {'compiler': compiler_id})
        ET.SubElement(project_el, 'Option', {'virtualFolders': ''})

        build_el = ET.SubElement(project_el, 'Build')
        target_all_el = ET.SubElement(build_el, 'Target', {'title': 'all'})
        ET.SubElement(target_all_el, 'Option', {'working_dir': self.environment.build_dir})
        ET.SubElement(target_all_el, 'Option', {'type': str(self.BUILD_OPTION_COMMANDS_ONLY)})

        target_all_commands = ET.SubElement(target_all_el, 'MakeCommands')
        ET.SubElement(target_all_commands, 'Build', {'command': '"{}" -v all'.format(self.ninja_bin)})
        ET.SubElement(target_all_commands, 'CompileFile', {'command': '"{}" -v "$file"'.format(self.ninja_bin)})
        ET.SubElement(target_all_commands, 'Clean', {'command': '"{}" -v clean'.format(self.ninja_bin)})
        ET.SubElement(target_all_commands, 'DistClean', {'command': '"{}" -f "$makefile" -v clean'.format(self.ninja_bin)})

        for target in self.build.targets.values():
            if isinstance(target, build.CustomTarget):
                continue
            output_dir = os.path.join(self.environment.build_dir, target.subdir)
            output = os.path.join(output_dir, target.filename)
            target_el = ET.SubElement(build_el, 'Target', {'title': target.name})
            ET.SubElement(target_el, 'Option', {'output': output, 'prefix_auto': '0', 'extension_auto': '0'})
            ET.SubElement(target_el, 'Option', {'working_dir': output_dir})
            ET.SubElement(target_el, 'Option', {'object_output': './'})
            if isinstance(target, build.Executable):
                option = 1
            elif isinstance(target, build.StaticLibrary):
                option = 2
            elif isinstance(target, build.SharedLibrary):
                option = 3
            else:
                option = 4
            ET.SubElement(target_el, 'Option', {'type': str(option)})
            ET.SubElement(target_el, 'Option', {'compiler': compiler_id})

            target_compiler_el = ET.SubElement(target_el, 'Compiler')
            args = set()
            for global_args in self.build.global_args.values():
                args = args.union(global_args)
            for target_args in target.extra_args.values():
                args = args.union(target_args)
            for arg in args:
                ET.SubElement(target_compiler_el, 'Add', {'option': arg})

            include_dirs = set()
            for external_dep in target.external_deps:
                try:
                    include_dirs.add(external_dep.incdir)
                except AttributeError:
                    pass
            for include_dir in include_dirs:
                ET.SubElement(target_compiler_el, 'Add', {'directory': include_dir})

            target_make = ET.SubElement(target_el, 'MakeCommands')
            ET.SubElement(target_make, 'Build', {'command': '"{}" -v {}'.format(self.ninja_bin, os.path.join(target.subdir, target.filename))})
            ET.SubElement(target_make, 'CompileFile', {'command': '"{}" -v "$file"'.format(self.ninja_bin)})
            ET.SubElement(target_make, 'Clean', {'command': '"{}" -v clean'.format(self.ninja_bin)})
            ET.SubElement(target_make, 'DistClean', {'command': '"{}" -v clean'.format(self.ninja_bin)})

        for target in self.build.targets.values():
            if isinstance(target, build.CustomTarget):
                continue
            output_dir = os.path.join(self.environment.build_dir, target.subdir)
            for source in target.sources:
                filename = os.path.join(output_dir, source.relative_name())
                unit_el = ET.SubElement(project_el, 'Unit', {'filename': filename})
                ET.SubElement(unit_el, 'Option', {'targets': target.name})

        self._prettyprint_xml(ET.ElementTree(root_el), ofname)

    def _prettyprint_xml(self, tree, ofname):
        tree.write(ofname, encoding='utf-8', xml_declaration=True)
        # ElementTree can not do prettyprinting so do it manually
        doc = xml.dom.minidom.parse(ofname)
        with open(ofname, 'w') as of:
            of.write(doc.toprettyxml())

    CBP_VERSION_MAJOR = 1
    CBP_VERSION_MINOR = 6
