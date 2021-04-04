# Copyright 2014-2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import backends
from .. import build
from .. import dependencies
from .. import mesonlib
from .. import mlog
import uuid, os, operator
import typing as T

from ..mesonlib import MesonException
from ..interpreter import Interpreter

INDENT = '\t'

class PbxItem:
    def __init__(self, value, comment = ''):
        self.value = value
        self.comment = comment

class PbxArray:
    def __init__(self):
        self.items = []

    def add_item(self, item, comment=''):
        if isinstance(item, PbxArrayItem):
            self.items.append(item)
        else:
            self.items.append(PbxArrayItem(item, comment))

    def write(self, ofile, indent_level):
        ofile.write('(\n')
        indent_level += 1
        for i in self.items:
            ofile.write(indent_level*INDENT + f'{i.value} {i.comment} ,\n')
        indent_level -= 1
        ofile.write(indent_level*INDENT + ');\n')

class PbxArrayItem:
    def __init__(self, value, comment = ''):
        self.value = value
        if comment:
            if '/*' in comment:
                self.comment = comment
            else:
                self.comment = f'/* {comment} */'
        else:
            self.comment = comment

class PbxComment:
    def __init__(self, text):
        assert('/*' not in text)
        self.text = f'/* {text} */'

    def write(self, ofile, indent_level):
        ofile.write(f'\n{self.text}\n')

class PbxDictItem:
    def __init__(self, key, value, comment = ''):
        self.key = key
        self.value = value
        if comment:
            if '/*' in comment:
                self.comment = comment
            else:
                self.comment = f'/* {comment} */'
        else:
            self.comment = comment

class PbxDict:
    def __init__(self):
        # This class is a bit weird, because we want to write PBX dicts in
        # defined order _and_ we want to write intermediate comments also in order.
        self.keys = set()
        self.items = []

    def add_item(self, key, value, comment=''):
        item = PbxDictItem(key, value, comment)
        assert(key not in self.keys)
        self.keys.add(key)
        self.items.append(item)

    def add_comment(self, comment):
        if isinstance(comment, str):
            self.items.append(PbxComment(str))
        else:
            assert(isinstance(comment, PbxComment))
            self.items.append(comment)

    def write(self, ofile, indent_level):
        ofile.write('{\n')
        indent_level += 1
        for i in self.items:
            if isinstance(i, PbxComment):
                i.write(ofile, indent_level)
            elif isinstance(i, PbxDictItem):
                if isinstance(i.value, (str, int)):
                    ofile.write(indent_level*INDENT + f'{i.key} = {i.value} {i.comment};\n')
                elif isinstance(i.value, PbxDict):
                    ofile.write(indent_level*INDENT + f'{i.key} {i.comment} = ')
                    i.value.write(ofile, indent_level)
                elif isinstance(i.value, PbxArray):
                    ofile.write(indent_level*INDENT + f'{i.key} {i.comment} = ')
                    i.value.write(ofile, indent_level)
                else:
                    raise RuntimeError('missing code')
            else:
                print(i)
                raise RuntimeError('missing code2')

        indent_level -= 1
        ofile.write(indent_level*INDENT + '}')
        if indent_level == 0:
            ofile.write('\n')
        else:
            ofile.write(';\n')

class XCodeBackend(backends.Backend):
    def __init__(self, build: T.Optional[build.Build], interpreter: T.Optional[Interpreter]):
        super().__init__(build, interpreter)
        self.name = 'xcode'
        self.project_uid = self.environment.coredata.lang_guids['default'].replace('-', '')[:24]
        self.project_conflist = self.gen_id()
        self.indent = '\t' # Recent versions of Xcode uses tabs
        self.indent_level = 0
        self.xcodetypemap = {'c': 'sourcecode.c.c',
                             'a': 'archive.ar',
                             'cc': 'sourcecode.cpp.cpp',
                             'cxx': 'sourcecode.cpp.cpp',
                             'cpp': 'sourcecode.cpp.cpp',
                             'c++': 'sourcecode.cpp.cpp',
                             'm': 'sourcecode.c.objc',
                             'mm': 'sourcecode.cpp.objcpp',
                             'h': 'sourcecode.c.h',
                             'hpp': 'sourcecode.cpp.h',
                             'hxx': 'sourcecode.cpp.h',
                             'hh': 'sourcecode.cpp.hh',
                             'inc': 'sourcecode.c.h',
                             'dylib': 'compiled.mach-o.dylib',
                             'o': 'compiled.mach-o.objfile',
                             's': 'sourcecode.asm',
                             'asm': 'sourcecode.asm',
                             }
        self.maingroup_id = self.gen_id()
        self.all_id = self.gen_id()
        self.all_buildconf_id = self.gen_id()
        self.buildtypes = ['debug']
        self.test_id = self.gen_id()
        self.test_command_id = self.gen_id()
        self.test_buildconf_id = self.gen_id()
        self.top_level_dict = PbxDict()

    def write_pbxfile(self, top_level_dict, ofilename):
         with open(ofilename, 'w') as ofile:
             ofile.write('// !$*UTF8*$!\n')
             top_level_dict.write(ofile, 0)
             assert(self.indent_level == 0)

    def gen_id(self):
        return str(uuid.uuid4()).upper().replace('-', '')[:24]

    def get_target_dir(self, target):
        dirname = os.path.join(target.get_subdir(), self.environment.coredata.get_option(mesonlib.OptionKey('buildtype')))
        os.makedirs(os.path.join(self.environment.get_build_dir(), dirname), exist_ok=True)
        return dirname

    def target_to_build_root(self, target):
        if self.get_target_dir(target) == '':
            return ''
        directories = os.path.normpath(self.get_target_dir(target)).split(os.sep)
        return os.sep.join(['..'] * len(directories))

    def write_line(self, text):
        self.ofile.write(self.indent * self.indent_level + text)
        if not text.endswith('\n'):
            self.ofile.write('\n')

    def generate(self):
        test_data = self.serialize_tests()[0]
        self.generate_filemap()
        self.generate_buildmap()
        self.generate_buildstylemap()
        self.generate_build_phase_map()
        self.generate_build_configuration_map()
        self.generate_build_configurationlist_map()
        self.generate_project_configurations_map()
        self.generate_buildall_configurations_map()
        self.generate_test_configurations_map()
        self.generate_native_target_map()
        self.generate_native_frameworks_map()
        self.generate_source_phase_map()
        self.generate_target_dependency_map()
        self.generate_pbxdep_map()
        self.generate_containerproxy_map()
        self.proj_dir = os.path.join(self.environment.get_build_dir(), self.build.project_name + '.xcodeproj')
        os.makedirs(self.proj_dir, exist_ok=True)
        self.proj_file = os.path.join(self.proj_dir, 'project.pbxproj')
        with open(self.proj_file, 'w') as self.ofile:
            objects_dict = self.generate_prefix(self.top_level_dict)
            objects_dict.add_comment(PbxComment('Begin PBXAggregateTarget section'))
            self.generate_pbx_aggregate_target(objects_dict)
            objects_dict.add_comment(PbxComment('End PBXAggregateTarget section'))
            objects_dict.add_comment(PbxComment('Begin PBXBuildFile section'))
            self.generate_pbx_build_file(objects_dict)
            objects_dict.add_comment(PbxComment('End PBXBuildFile section'))
            objects_dict.add_comment(PbxComment('Begin PBXBuildStyle section'))
            self.generate_pbx_build_style(objects_dict)
            objects_dict.add_comment(PbxComment('End PBXBuildStyle section'))
            objects_dict.add_comment(PbxComment('Begin PBXContainerItemProxy section'))
            self.generate_pbx_container_item_proxy(objects_dict)
            objects_dict.add_comment(PbxComment('End PBXContainerItemProxy section'))
            objects_dict.add_comment(PbxComment('Begin PBXFileReference section'))
            self.generate_pbx_file_reference(objects_dict)
            objects_dict.add_comment(PbxComment('End PBXFileReference section'))
            objects_dict.add_comment(PbxComment('Begin PBXFrameworksBuildPhase section'))
            self.generate_pbx_frameworks_buildphase(objects_dict)
            objects_dict.add_comment(PbxComment('End PBXFrameworksBuildPhase section'))
            objects_dict.add_comment(PbxComment('Begin PBXGroup section'))
            self.generate_pbx_group(objects_dict)
            objects_dict.add_comment(PbxComment('End PBXGroup section'))
            objects_dict.add_comment(PbxComment('Begin PBXNativeTarget section'))
            self.generate_pbx_native_target()
            objects_dict.add_comment(PbxComment('End PBXNativeTarget section'))
            objects_dict.add_comment(PbxComment('Begin PBXProject section'))
            self.generate_pbx_project()
            objects_dict.add_comment(PbxComment('End PBXProject section'))
            objects_dict.add_comment(PbxComment('Begin PBXShellScriptBuildPhase section'))
            self.generate_pbx_shell_build_phase(test_data)
            objects_dict.add_comment(PbxComment('End PBXShellScriptBuildPhase section'))
            objects_dict.add_comment(PbxComment('Begin PBXSourcesBuildPhase section'))
            self.generate_pbx_sources_build_phase()
            objects_dict.add_comment(PbxComment('End PBXSourcesBuildPhase section'))
            objects_dict.add_comment(PbxComment('Begin PBXTargetDependency section'))
            self.generate_pbx_target_dependency()
            objects_dict.add_comment(PbxComment('End PBXTargetDependency section'))
            objects_dict.add_comment(PbxComment('Begin XCBuildPConfiguration section'))
            self.generate_xc_build_configuration()
            objects_dict.add_comment(PbxComment('End XCBuildPConfiguration section'))
            objects_dict.add_comment(PbxComment('Begin XCConfigurationList section'))
            self.generate_xc_configurationList()
            objects_dict.add_comment(PbxComment('End XCConfigurationList section'))
            self.generate_suffix(self.top_level_dict)
        self.write_pbxfile(self.top_level_dict, "temporary.pbxproj")

    def get_xcodetype(self, fname):
        xcodetype = self.xcodetypemap.get(fname.split('.')[-1].lower())
        if not xcodetype:
            xcodetype = 'sourcecode.unknown'
            mlog.warning(f'Unknown file type "{fname}" fallbacking to "{xcodetype}". Xcode project might be malformed.')
        return xcodetype

    def generate_filemap(self):
        self.filemap = {} # Key is source file relative to src root.
        self.target_filemap = {}
        for name, t in self.build.get_build_targets().items():
            for s in t.sources:
                if isinstance(s, mesonlib.File):
                    s = os.path.join(s.subdir, s.fname)
                    self.filemap[s] = self.gen_id()
            for o in t.objects:
                if isinstance(o, str):
                    o = os.path.join(t.subdir, o)
                    self.filemap[o] = self.gen_id()
            self.target_filemap[name] = self.gen_id()

    def generate_buildmap(self):
        self.buildmap = {}
        for t in self.build.get_build_targets().values():
            for s in t.sources:
                s = os.path.join(s.subdir, s.fname)
                self.buildmap[s] = self.gen_id()
            for o in t.objects:
                o = os.path.join(t.subdir, o)
                if isinstance(o, str):
                    self.buildmap[o] = self.gen_id()

    def generate_buildstylemap(self):
        self.buildstylemap = {'debug': self.gen_id()}

    def generate_build_phase_map(self):
        for tname, t in self.build.get_build_targets().items():
            # generate id for our own target-name
            t.buildphasemap = {}
            t.buildphasemap[tname] = self.gen_id()
            # each target can have it's own Frameworks/Sources/..., generate id's for those
            t.buildphasemap['Frameworks'] = self.gen_id()
            t.buildphasemap['Resources'] = self.gen_id()
            t.buildphasemap['Sources'] = self.gen_id()

    def generate_build_configuration_map(self):
        self.buildconfmap = {}
        for t in self.build.get_build_targets():
            bconfs = {'debug': self.gen_id()}
            self.buildconfmap[t] = bconfs

    def generate_project_configurations_map(self):
        self.project_configurations = {'debug': self.gen_id()}

    def generate_buildall_configurations_map(self):
        self.buildall_configurations = {'debug': self.gen_id()}

    def generate_test_configurations_map(self):
        self.test_configurations = {'debug': self.gen_id()}

    def generate_build_configurationlist_map(self):
        self.buildconflistmap = {}
        for t in self.build.get_build_targets():
            self.buildconflistmap[t] = self.gen_id()

    def generate_native_target_map(self):
        self.native_targets = {}
        for t in self.build.get_build_targets():
            self.native_targets[t] = self.gen_id()

    def generate_native_frameworks_map(self):
        self.native_frameworks = {}
        self.native_frameworks_fileref = {}
        for t in self.build.get_build_targets().values():
            for dep in t.get_external_deps():
                if isinstance(dep, dependencies.AppleFrameworks):
                    for f in dep.frameworks:
                        self.native_frameworks[f] = self.gen_id()
                        self.native_frameworks_fileref[f] = self.gen_id()

    def generate_target_dependency_map(self):
        self.target_dependency_map = {}
        for tname, t in self.build.get_build_targets().items():
            for target in t.link_targets:
                self.target_dependency_map[(tname, target.get_basename())] = self.gen_id()

    def generate_pbxdep_map(self):
        self.pbx_dep_map = {}
        for t in self.build.get_build_targets():
            self.pbx_dep_map[t] = self.gen_id()

    def generate_containerproxy_map(self):
        self.containerproxy_map = {}
        for t in self.build.get_build_targets():
            self.containerproxy_map[t] = self.gen_id()

    def generate_source_phase_map(self):
        self.source_phase = {}
        for t in self.build.get_build_targets():
            self.source_phase[t] = self.gen_id()

    def generate_pbx_aggregate_target(self, objects_dict):
        target_dependencies = list(map(lambda t: self.pbx_dep_map[t], self.build.get_build_targets()))
        aggregated_targets = []
        aggregated_targets.append((self.all_id, 'ALL_BUILD', self.all_buildconf_id, [], target_dependencies))
        aggregated_targets.append((self.test_id, 'RUN_TESTS', self.test_buildconf_id, [self.test_command_id], []))
        # Sort objects by ID before writing
        sorted_aggregated_targets = sorted(aggregated_targets, key=operator.itemgetter(0))
        self.ofile.write('\n/* Begin PBXAggregateTarget section */\n')
        for t in sorted_aggregated_targets:
            agt_dict = PbxDict()
            name = t[1]
            buildconf_id = t[2]
            build_phases = t[3]
            dependencies = t[4]
            self.write_line('{} /* {} */ = {{'.format(t[0], name))
            self.indent_level += 1
            self.write_line('isa = PBXAggregateTarget;')
            agt_dict.add_item('isa', 'PBXAggregateTarget')
            self.write_line(f'buildConfigurationList = {buildconf_id} /* Build configuration list for PBXAggregateTarget "{name}" */;')
            agt_dict.add_item('buildConfigurationList', buildconf_id)
            self.write_line('buildPhases = (')
            bp_arr = PbxArray()
            agt_dict.add_item('buildPhases', bp_arr)
            self.indent_level += 1
            for bp in build_phases:
                self.write_line('%s /* ShellScript */,' % bp)
                bp_arr.add_item(bp, 'ShellScript')
            self.indent_level -= 1
            self.write_line(');')
            self.write_line('dependencies = (')
            dep_arr = PbxArray()
            agt_dict.add_item('dependencies', dep_arr)
            self.indent_level += 1
            for td in dependencies:
                self.write_line('%s /* PBXTargetDependency */,' % td)
                dep_arr.add_item(td, 'PBXTargetDependency')
            self.indent_level -= 1
            self.write_line(');')
            self.write_line('name = %s;' % name)
            agt_dict.add_item('name', name)
            self.write_line('productName = %s;' % name)
            agt_dict.add_item('productname', name)
            self.indent_level -= 1
            self.write_line('};')
            objects_dict.add_item(t[0], agt_dict, name)
        self.ofile.write('/* End PBXAggregateTarget section */\n')

    def generate_pbx_build_file(self, objects_dict):
        self.ofile.write('\n/* Begin PBXBuildFile section */\n')
        templ = '%s /* %s */ = { isa = PBXBuildFile; fileRef = %s /* %s */; settings = { COMPILER_FLAGS = "%s"; }; };\n'
        otempl = '%s /* %s */ = { isa = PBXBuildFile; fileRef = %s /* %s */;};\n'
        ftempl = '{} /* {}.framework in Frameworks */ = {{isa = PBXBuildFile; fileRef = {} /* {}.framework */; }};\n'

        for t in self.build.get_build_targets().values():
            for dep in t.get_external_deps():
                # FIXME not ported
                if isinstance(dep, dependencies.AppleFrameworks):
                    for f in dep.frameworks:
                        self.write_line(ftempl.format(self.native_frameworks[f], f, self.native_frameworks_fileref[f], f))

            for s in t.sources:
                sdict = PbxDict()
                if isinstance(s, mesonlib.File):
                    s = os.path.join(s.subdir, s.fname)

                if isinstance(s, str):
                    s = os.path.join(t.subdir, s)
                    sdict = PbxDict()
                    idval = self.buildmap[s]
                    fullpath = os.path.join(self.environment.get_source_dir(), s)
                    fileref = self.filemap[s]
                    fullpath2 = fullpath
                    compiler_args = ''
                    self.write_line(templ % (idval, fullpath, fileref, fullpath2, compiler_args))
                    sdict.add_item('isa', 'PBXBuildFile')
                    sdict.add_item('fileRef', fileref, fullpath2)
                    settingdict = PbxDict()
                    settingdict.add_item('COMPILER_FLAGS', '"' + compiler_args + '"')
                    sdict.add_item('settings', settingdict)
                    objects_dict.add_item(idval, sdict)

            for o in t.objects:
                # FIXME, not ported
                o = os.path.join(t.subdir, o)
                idval = self.buildmap[o]
                fileref = self.filemap[o]
                fullpath = os.path.join(self.environment.get_source_dir(), o)
                fullpath2 = fullpath
                self.write_line(otempl % (idval, fullpath, fileref, fullpath2))
        self.ofile.write('/* End PBXBuildFile section */\n')

    def generate_pbx_build_style(self, objects_dict):
        # FIXME: Xcode 9 and later does not uses PBXBuildStyle and it gets removed. Maybe we can remove this part.
        self.ofile.write('\n/* Begin PBXBuildStyle section */\n')
        for name, idval in self.buildstylemap.items():
            styledict = PbxDict()
            self.write_line(f'{idval} /* {name} */ = {{\n')
            objects_dict.add_item(idval, styledict, name)
            self.indent_level += 1
            self.write_line('isa = PBXBuildStyle;\n')
            styledict.add_item('isa', 'PBXBuildStyle')
            settings_dict = PbxDict()
            self.write_line('buildSettings = {\n')
            styledict.add_item('buildSettings', settings_dict)
            self.indent_level += 1
            self.write_line('COPY_PHASE_STRIP = NO;\n')
            settings_dict.add_item('COPY_PHASE_STRIP', 'NO')
            self.indent_level -= 1
            self.write_line('};\n')
            self.write_line('name = "%s";\n' % name)
            styledict.add_item('name', name)
            self.indent_level -= 1
            self.write_line('};\n')
        self.ofile.write('/* End PBXBuildStyle section */\n')

    def generate_pbx_container_item_proxy(self, objects_dict):
        self.ofile.write('\n/* Begin PBXContainerItemProxy section */\n')
        for t in self.build.get_build_targets():
            proxy_dict = PbxDict()
            self.write_line('%s /* PBXContainerItemProxy */ = {' % self.containerproxy_map[t])
            objects_dict.add_item(self.containerproxy_map[t], proxy_dict, 'PBXContainerItemProxy')
            self.indent_level += 1
            self.write_line('isa = PBXContainerItemProxy;')
            proxy_dict.add_item('isa', 'PBXContainerItemProxy')
            self.write_line('containerPortal = %s /* Project object */;' % self.project_uid)
            proxy_dict.add_item('containerPortal', self.project_uid, 'Project object')
            self.write_line('proxyType = 1;')
            proxy_dict.add_item('proxyType', '1')
            self.write_line('remoteGlobalIDString = %s;' % self.native_targets[t])
            proxy_dict.add_item('remoteGlobalIDString', self.native_targets[t])
            self.write_line('remoteInfo = "%s";' % t)
            proxy_dict.add_item('remoteInfo', '"' + t + '"')
            self.indent_level -= 1
            self.write_line('};')
        self.ofile.write('/* End PBXContainerItemProxy section */\n')

    def generate_pbx_file_reference(self, objects_dict):
        self.ofile.write('\n/* Begin PBXFileReference section */\n')
        for t in self.build.get_build_targets().values():
            for dep in t.get_external_deps():
                if isinstance(dep, dependencies.AppleFrameworks):
                    for f in dep.frameworks:
                        # FIXME not ported
                        self.write_line('{} /* {}.framework */ = {{isa = PBXFileReference; lastKnownFileType = wrapper.framework; name = {}.framework; path = System/Library/Frameworks/{}.framework; sourceTree = SDKROOT; }};\n'.format(self.native_frameworks_fileref[f], f, f, f))
        src_templ = '%s /* %s */ = { isa = PBXFileReference; explicitFileType = "%s"; fileEncoding = 4; name = "%s"; path = "%s"; sourceTree = SOURCE_ROOT; };\n'
        for fname, idval in self.filemap.items():
            src_dict = PbxDict()
            fullpath = os.path.join(self.environment.get_source_dir(), fname)
            xcodetype = self.get_xcodetype(fname)
            name = os.path.basename(fname)
            path = fname
            objects_dict.add_item(idval, src_dict, fullpath)
            self.write_line(src_templ % (idval, fullpath, xcodetype, name, path))
            src_dict.add_item('isa', 'PBXFileReference')
            src_dict.add_item('explicitFileType', '"' + xcodetype + '"')
            src_dict.add_item('fileEncoding', '4')
            src_dict.add_item('name', '"' + name + '"')
            src_dict.add_item('path', '"' + path + '"')
            src_dict.add_item('sourceTree', 'SOURCE_ROOT')
        target_templ = '%s /* %s */ = { isa = PBXFileReference; explicitFileType = "%s"; path = %s; refType = %d; sourceTree = BUILT_PRODUCTS_DIR; };\n'
        for tname, idval in self.target_filemap.items():
            target_dict = PbxDict()
            objects_dict.add_item(idval, target_dict, tname)
            t = self.build.get_build_targets()[tname]
            fname = t.get_filename()
            reftype = 0
            if isinstance(t, build.Executable):
                typestr = 'compiled.mach-o.executable'
                path = fname
            elif isinstance(t, build.SharedLibrary):
                typestr = self.get_xcodetype('dummy.dylib')
                path = fname
            else:
                typestr = self.get_xcodetype(fname)
                path = '"%s"' % t.get_filename()
            self.write_line(target_templ % (idval, tname, typestr, path, reftype))
            target_dict.add_item('isa', 'PBXFileReference')
            target_dict.add_item('explicitFileType', '"' + typestr + '"')
            target_dict.add_item('path', path)
            target_dict.add_item('refType', reftype)
            target_dict.add_item('sourceTree', 'BUILT_PRODUCTS_DIR')
        self.ofile.write('/* End PBXFileReference section */\n')

    def generate_pbx_frameworks_buildphase(self, objects_dict):
        for t in self.build.get_build_targets().values():
            bt_dict = PbxDict()
            self.ofile.write('\n/* Begin PBXFrameworksBuildPhase section */\n')
            self.write_line('{} /* {} */ = {{\n'.format(t.buildphasemap['Frameworks'], 'Frameworks'))
            objects_dict.add_item(t.buildphasemap['Frameworks'], bt_dict, 'Frameworks')
            self.indent_level += 1
            self.write_line('isa = PBXFrameworksBuildPhase;\n')
            bt_dict.add_item('isa', 'PBXFrameworksBuildPhase')
            self.write_line('buildActionMask = %s;\n' % (2147483647))
            bt_dict.add_item('buildActionMask', 2147483647)
            self.write_line('files = (\n')
            file_list = PbxArray()
            bt_dict.add_item('files', file_list)
            self.indent_level += 1
            for dep in t.get_external_deps():
                if isinstance(dep, dependencies.AppleFrameworks):
                    for f in dep.frameworks:
                        self.write_line('{} /* {}.framework in Frameworks */,\n'.format(self.native_frameworks[f], f))
                        file_list.add_item(self.native_frameworks[f], f'{f}.framework in Frameworks')
            self.indent_level -= 1
            self.write_line(');\n')
            self.write_line('runOnlyForDeploymentPostprocessing = 0;\n')
            bt_dict.add_item('runOnlyForDeploymentPostprocessing', 0)
            self.indent_level -= 1
            self.write_line('};\n')
        self.ofile.write('/* End PBXFrameworksBuildPhase section */\n')

    def generate_pbx_group(self, objects_dict):
        groupmap = {}
        target_src_map = {}
        for t in self.build.get_build_targets():
            groupmap[t] = self.gen_id()
            target_src_map[t] = self.gen_id()
        self.ofile.write('\n/* Begin PBXGroup section */\n')
        sources_id = self.gen_id()
        resources_id = self.gen_id()
        products_id = self.gen_id()
        frameworks_id = self.gen_id()        
        self.write_line('%s = {' % self.maingroup_id)
        main_dict = PbxDict()
        objects_dict.add_item(self.maingroup_id, main_dict)
        self.indent_level += 1
        self.write_line('isa = PBXGroup;')
        main_dict.add_item('isa', 'PBXGroup')
        main_children = PbxArray()
        self.write_line('children = (')
        main_dict.add_item('children', main_children)
        self.indent_level += 1
        self.write_line('%s /* Sources */,' % sources_id)
        main_children.add_item(sources_id, 'Sources')
        self.write_line('%s /* Resources */,' % resources_id)
        main_children.add_item(resources_id, 'Resources')
        self.write_line('%s /* Products */,' % products_id)
        main_children.add_item('products_id', 'Products')
        self.write_line('%s /* Frameworks */,' % frameworks_id)
        main_children.add_item(frameworks_id, 'Frameworks')
        self.indent_level -= 1
        self.write_line(');')
        self.write_line('sourceTree = "<group>";')
        main_dict.add_item('sourceTree', '"<group>"')
        self.indent_level -= 1
        self.write_line('};')

        # Sources
        source_dict = PbxDict()
        self.write_line('%s /* Sources */ = {' % sources_id)
        objects_dict.add_item(sources_id, source_dict, 'Sources')
        self.indent_level += 1
        self.write_line('isa = PBXGroup;')
        source_dict.add_item('isa', 'PBXGroup')
        source_children = PbxArray()
        self.write_line('children = (')
        source_dict.add_item('children', source_children)
        self.indent_level += 1
        for t in self.build.get_build_targets():
            self.write_line('{} /* {} */,'.format(groupmap[t], t))
            source_children.add_item(groupmap[t], t)
        self.indent_level -= 1
        self.write_line(');')
        self.write_line('name = Sources;')
        source_dict.add_item('name', 'Sources')
        self.write_line('sourceTree = "<group>";')
        source_dict.add_item('sourceTree', '"<group>"')
        self.indent_level -= 1
        self.write_line('};')


        resource_dict = PbxDict()
        self.write_line('%s /* Resources */ = {' % resources_id)
        objects_dict.add_item(resources_id, resource_dict, 'Resources')
        self.indent_level += 1
        self.write_line('isa = PBXGroup;')
        resource_dict.add_item('isa', 'PBXGroup')
        resource_children = PbxArray()
        self.write_line('children = (')
        resource_dict.add_item('children', resource_children)
        self.write_line(');')
        self.write_line('name = Resources;')
        resource_dict.add_item('name', 'Resources')
        self.write_line('sourceTree = "<group>";')
        resource_dict.add_item('sourceTree', '"<group>"')
        self.indent_level -= 1
        self.write_line('};')

        frameworks_dict = PbxDict()
        self.write_line('%s /* Frameworks */ = {' % frameworks_id)
        objects_dict.add_item(frameworks_id, frameworks_dict, 'Frameworks')
        self.indent_level += 1
        self.write_line('isa = PBXGroup;')
        frameworks_dict.add_item('isa', 'PBXGroup')
        frameworks_children = PbxArray()
        frameworks_dict.add_item('children', frameworks_children)
        self.write_line('children = (')
        # write frameworks
        self.indent_level += 1

        for t in self.build.get_build_targets().values():
            for dep in t.get_external_deps():
                if isinstance(dep, dependencies.AppleFrameworks):
                    for f in dep.frameworks:
                        self.write_line('{} /* {}.framework */,\n'.format(self.native_frameworks_fileref[f], f))
                        frameworks_children.add_item(self.native_frameworks_fileref[f], f)

        self.indent_level -= 1
        self.write_line(');')
        self.write_line('name = Frameworks;')
        frameworks_dict.add_item('name', 'Frameworks')
        self.write_line('sourceTree = "<group>";')
        frameworks_dict.add_item('sourceTree', '"<group>"')
        self.indent_level -= 1
        self.write_line('};')

        # Targets
        for t in self.build.get_build_targets():
            target_dict = PbxDict()
            self.write_line('{} /* {} */ = {{'.format(groupmap[t], t))
            objects_dict.add_item(groupmap[t], target_dict, t)
            self.indent_level += 1
            self.write_line('isa = PBXGroup;')
            target_dict.add_item('isa', 'PBXGroup')
            target_children = PbxArray()
            target_dict.add_item('children', target_children)
            self.write_line('children = (')
            self.indent_level += 1
            self.write_line('%s /* Source files */,' % target_src_map[t])
            target_children.add_item(target_src_map[t], 'Source files')
            self.indent_level -= 1
            self.write_line(');')
            self.write_line('name = "%s";' % t)
            target_dict.add_item('name', f'"{t}"')
            self.write_line('sourceTree = "<group>";')
            target_dict.add_item('sourceTree', '"<group>"')
            self.indent_level -= 1
            self.write_line('};')
            source_files_dict = PbxDict()
            self.write_line('%s /* Source files */ = {' % target_src_map[t])
            objects_dict.add_item(target_src_map[t], source_files_dict, 'Source files')
            self.indent_level += 1
            self.write_line('isa = PBXGroup;')
            source_files_dict.add_item('isa', 'PBXGroup')
            source_file_children = PbxArray()
            self.write_line('children = (')
            source_files_dict.add_item('children', source_file_children)
            self.indent_level += 1
            for s in self.build.get_build_targets()[t].sources:
                s = os.path.join(s.subdir, s.fname)
                if isinstance(s, str):
                    self.write_line('{} /* {} */,'.format(self.filemap[s], s))
                    source_file_children.add_item(self.filemap[s], s)
            for o in self.build.get_build_targets()[t].objects:
                o = os.path.join(self.build.get_build_targets()[t].subdir, o)
                self.write_line('{} /* {} */,'.format(self.filemap[o], o))
                source_file_children.add_item(self.filemap[o], o)
            self.indent_level -= 1
            self.write_line(');')
            self.write_line('name = "Source files";')
            source_files_dict.add_item('name', '"Source files"')
            self.write_line('sourceTree = "<group>";')
            source_files_dict.add_item('sourceTree', '"<group>"')
            self.indent_level -= 1
            self.write_line('};')

        # And finally products
        product_dict = PbxDict()
        self.write_line('%s /* Products */ = {' % products_id)
        objects_dict.add_item(products_id, product_dict, 'Products')
        self.indent_level += 1
        self.write_line('isa = PBXGroup;')
        product_dict.add_item('isa', 'PBXGroup')
        self.write_line('children = (')
        product_children = PbxArray()
        product_dict.add_item('children', product_children)
        self.indent_level += 1
        for t in self.build.get_build_targets():
            self.write_line('{} /* {} */,'.format(self.target_filemap[t], t))
            product_children.add_item(self.target_filemap[t], t)
        self.indent_level -= 1
        self.write_line(');')
        self.write_line('name = Products;')
        product_dict.add_item('name', 'Products')
        self.write_line('sourceTree = "<group>";')
        product_dict.add_item('sourceTree', '"<group>"')
        self.indent_level -= 1
        self.write_line('};')
        self.ofile.write('/* End PBXGroup section */\n')

    def generate_pbx_native_target(self):
        self.ofile.write('\n/* Begin PBXNativeTarget section */\n')
        for tname, idval in self.native_targets.items():
            t = self.build.get_build_targets()[tname]
            self.write_line(f'{idval} /* {tname} */ = {{')
            self.indent_level += 1
            self.write_line('isa = PBXNativeTarget;')
            self.write_line('buildConfigurationList = %s /* Build configuration list for PBXNativeTarget "%s" */;'
                            % (self.buildconflistmap[tname], tname))
            self.write_line('buildPhases = (')
            self.indent_level += 1
            for bpname, bpval in t.buildphasemap.items():
                self.write_line(f'{bpval} /* {bpname} yyy */,')
            self.indent_level -= 1
            self.write_line(');')
            self.write_line('buildRules = (')
            self.write_line(');')
            self.write_line('dependencies = (')
            self.indent_level += 1
            for lt in self.build.get_build_targets()[tname].link_targets:
                # NOT DOCUMENTED, may need to make different links
                # to same target have different targetdependency item.
                idval = self.pbx_dep_map[lt.get_id()]
                self.write_line('%s /* PBXTargetDependency */,' % idval)
            self.indent_level -= 1
            self.write_line(");")
            self.write_line('name = "%s";' % tname)
            self.write_line('productName = "%s";' % tname)
            self.write_line('productReference = {} /* {} */;'.format(self.target_filemap[tname], tname))
            if isinstance(t, build.Executable):
                typestr = 'com.apple.product-type.tool'
            elif isinstance(t, build.StaticLibrary):
                typestr = 'com.apple.product-type.library.static'
            elif isinstance(t, build.SharedLibrary):
                typestr = 'com.apple.product-type.library.dynamic'
            else:
                raise MesonException('Unknown target type for %s' % tname)
            self.write_line('productType = "%s";' % typestr)
            self.indent_level -= 1
            self.write_line('};')
        self.ofile.write('/* End PBXNativeTarget section */\n')

    def generate_pbx_project(self):
        self.ofile.write('\n/* Begin PBXProject section */\n')
        self.write_line('%s /* Project object */ = {' % self.project_uid)
        self.indent_level += 1
        self.write_line('isa = PBXProject;')
        self.write_line('attributes = {')
        self.indent_level += 1
        self.write_line('BuildIndependentTargetsInParallel = YES;')
        self.indent_level -= 1
        self.write_line('};')
        conftempl = 'buildConfigurationList = %s /* Build configuration list for PBXProject "%s" */;'
        self.write_line(conftempl % (self.project_conflist, self.build.project_name))
        self.write_line('buildSettings = {')
        self.write_line('};')
        self.write_line('buildStyles = (')
        self.indent_level += 1
        for name, idval in self.buildstylemap.items():
            self.write_line(f'{idval} /* {name} */,')
        self.indent_level -= 1
        self.write_line(');')
        self.write_line('compatibilityVersion = "Xcode 3.2";')
        self.write_line('hasScannedForEncodings = 0;')
        self.write_line('mainGroup = %s;' % self.maingroup_id)
        self.write_line('projectDirPath = "%s";' % self.build_to_src)
        self.write_line('projectRoot = "";')
        self.write_line('targets = (')
        self.indent_level += 1
        self.write_line('%s /* ALL_BUILD */,' % self.all_id)
        self.write_line('%s /* RUN_TESTS */,' % self.test_id)
        for t in self.build.get_build_targets():
            self.write_line('{} /* {} */,'.format(self.native_targets[t], t))
        self.indent_level -= 1
        self.write_line(');')
        self.indent_level -= 1
        self.write_line('};')
        self.ofile.write('/* End PBXProject section */\n')

    def generate_pbx_shell_build_phase(self, test_data):
        self.ofile.write('\n/* Begin PBXShellScriptBuildPhase section */\n')
        self.write_line('%s /* ShellScript */ = {' % self.test_command_id)
        self.indent_level += 1
        self.write_line('isa = PBXShellScriptBuildPhase;')
        self.write_line('buildActionMask = 2147483647;')
        self.write_line('files = (')
        self.write_line(');')
        self.write_line('inputPaths = (')
        self.write_line(');')
        self.write_line('outputPaths = (')
        self.write_line(');')
        self.write_line('runOnlyForDeploymentPostprocessing = 0;')
        self.write_line('shellPath = /bin/sh;')
        cmd = mesonlib.get_meson_command() + ['test', test_data, '-C', self.environment.get_build_dir()]
        cmdstr = ' '.join(["'%s'" % i for i in cmd])
        self.write_line('shellScript = "%s";' % cmdstr)
        self.write_line('showEnvVarsInLog = 0;')
        self.indent_level -= 1
        self.write_line('};')
        self.ofile.write('/* End PBXShellScriptBuildPhase section */\n')

    def generate_pbx_sources_build_phase(self):
        self.ofile.write('\n/* Begin PBXSourcesBuildPhase section */\n')
        for name in self.source_phase.keys():
            t = self.build.get_build_targets()[name]
            self.write_line('%s /* Sources */ = {' % (t.buildphasemap[name]))
            self.indent_level += 1
            self.write_line('isa = PBXSourcesBuildPhase;')
            self.write_line('buildActionMask = 2147483647;')
            self.write_line('files = (')
            self.indent_level += 1
            for s in self.build.get_build_targets()[name].sources:
                s = os.path.join(s.subdir, s.fname)
                if not self.environment.is_header(s):
                    self.write_line('{} /* {} */,'.format(self.buildmap[s], os.path.join(self.environment.get_source_dir(), s)))
            self.indent_level -= 1
            self.write_line(');')
            self.write_line('runOnlyForDeploymentPostprocessing = 0;')
            self.indent_level -= 1
            self.write_line('};')
        self.ofile.write('/* End PBXSourcesBuildPhase section */\n')

    def generate_pbx_target_dependency(self):
        targets = []
        for t in self.build.get_build_targets():
            idval = self.pbx_dep_map[t] # VERIFY: is this correct?
            targets.append((idval, self.native_targets[t], t, self.containerproxy_map[t]))

        # Sort object by ID
        sorted_targets = sorted(targets, key=operator.itemgetter(0))
        self.ofile.write('\n/* Begin PBXTargetDependency section */\n')
        for t in sorted_targets:
            self.write_line('%s /* PBXTargetDependency */ = {' % t[0])
            self.indent_level += 1
            self.write_line('isa = PBXTargetDependency;')
            self.write_line('target = {} /* {} */;'.format(t[1], t[2]))
            self.write_line('targetProxy = %s /* PBXContainerItemProxy */;' % t[3])
            self.indent_level -= 1
            self.write_line('};')
        self.ofile.write('/* End PBXTargetDependency section */\n')

    def generate_xc_build_configuration(self):
        self.ofile.write('\n/* Begin XCBuildConfiguration section */\n')
        # First the setup for the toplevel project.
        for buildtype in self.buildtypes:
            self.write_line('{} /* {} */ = {{'.format(self.project_configurations[buildtype], buildtype))
            self.indent_level += 1
            self.write_line('isa = XCBuildConfiguration;')
            self.write_line('buildSettings = {')
            self.indent_level += 1
            self.write_line('ARCHS = "$(ARCHS_STANDARD_64_BIT)";')
            self.write_line('ONLY_ACTIVE_ARCH = YES;')
            self.write_line('SDKROOT = "macosx";')
            self.write_line('SYMROOT = "%s/build";' % self.environment.get_build_dir())
            self.indent_level -= 1
            self.write_line('};')
            self.write_line('name = "%s";' % buildtype)
            self.indent_level -= 1
            self.write_line('};')

        # Then the all target.
        for buildtype in self.buildtypes:
            self.write_line('{} /* {} */ = {{'.format(self.buildall_configurations[buildtype], buildtype))
            self.indent_level += 1
            self.write_line('isa = XCBuildConfiguration;')
            self.write_line('buildSettings = {')
            self.indent_level += 1
            self.write_line('COMBINE_HIDPI_IMAGES = YES;')
            self.write_line('GCC_GENERATE_DEBUGGING_SYMBOLS = NO;')
            self.write_line('GCC_INLINES_ARE_PRIVATE_EXTERN = NO;')
            self.write_line('GCC_OPTIMIZATION_LEVEL = 0;')
            self.write_line('GCC_PREPROCESSOR_DEFINITIONS = "";')
            self.write_line('GCC_SYMBOLS_PRIVATE_EXTERN = NO;')
            self.write_line('INSTALL_PATH = "";')
            self.write_line('OTHER_CFLAGS = "  ";')
            self.write_line('OTHER_LDFLAGS = " ";')
            self.write_line('OTHER_REZFLAGS = "";')
            self.write_line('PRODUCT_NAME = ALL_BUILD;')
            self.write_line('SECTORDER_FLAGS = "";')
            self.write_line('SYMROOT = "%s";' % self.environment.get_build_dir())
            self.write_line('USE_HEADERMAP = NO;')
            self.write_build_setting_line('WARNING_CFLAGS', ['-Wmost', '-Wno-four-char-constants', '-Wno-unknown-pragmas'])
            self.indent_level -= 1
            self.write_line('};')
            self.write_line('name = "%s";' % buildtype)
            self.indent_level -= 1
            self.write_line('};')

        # Then the test target.
        for buildtype in self.buildtypes:
            self.write_line('{} /* {} */ = {{'.format(self.test_configurations[buildtype], buildtype))
            self.indent_level += 1
            self.write_line('isa = XCBuildConfiguration;')
            self.write_line('buildSettings = {')
            self.indent_level += 1
            self.write_line('COMBINE_HIDPI_IMAGES = YES;')
            self.write_line('GCC_GENERATE_DEBUGGING_SYMBOLS = NO;')
            self.write_line('GCC_INLINES_ARE_PRIVATE_EXTERN = NO;')
            self.write_line('GCC_OPTIMIZATION_LEVEL = 0;')
            self.write_line('GCC_PREPROCESSOR_DEFINITIONS = "";')
            self.write_line('GCC_SYMBOLS_PRIVATE_EXTERN = NO;')
            self.write_line('INSTALL_PATH = "";')
            self.write_line('OTHER_CFLAGS = "  ";')
            self.write_line('OTHER_LDFLAGS = " ";')
            self.write_line('OTHER_REZFLAGS = "";')
            self.write_line('PRODUCT_NAME = RUN_TESTS;')
            self.write_line('SECTORDER_FLAGS = "";')
            self.write_line('SYMROOT = "%s";' % self.environment.get_build_dir())
            self.write_line('USE_HEADERMAP = NO;')
            self.write_build_setting_line('WARNING_CFLAGS', ['-Wmost', '-Wno-four-char-constants', '-Wno-unknown-pragmas'])
            self.indent_level -= 1
            self.write_line('};')
            self.write_line('name = "%s";' % buildtype)
            self.indent_level -= 1
            self.write_line('};')

        # Now finally targets.
        langnamemap = {'c': 'C', 'cpp': 'CPLUSPLUS', 'objc': 'OBJC', 'objcpp': 'OBJCPLUSPLUS'}
        for target_name, target in self.build.get_build_targets().items():
            for buildtype in self.buildtypes:
                dep_libs = []
                links_dylib = False
                headerdirs = []
                for d in target.include_dirs:
                    for sd in d.incdirs:
                        cd = os.path.join(d.curdir, sd)
                        headerdirs.append(os.path.join(self.environment.get_source_dir(), cd))
                        headerdirs.append(os.path.join(self.environment.get_build_dir(), cd))
                for l in target.link_targets:
                    abs_path = os.path.join(self.environment.get_build_dir(),
                                            l.subdir, buildtype, l.get_filename())
                    dep_libs.append("'%s'" % abs_path)
                    if isinstance(l, build.SharedLibrary):
                        links_dylib = True
                if links_dylib:
                    dep_libs = ['-Wl,-search_paths_first', '-Wl,-headerpad_max_install_names'] + dep_libs
                dylib_version = None
                if isinstance(target, build.SharedLibrary):
                    ldargs = ['-dynamiclib', '-Wl,-headerpad_max_install_names'] + dep_libs
                    install_path = os.path.join(self.environment.get_build_dir(), target.subdir, buildtype)
                    dylib_version = target.soversion
                else:
                    ldargs = dep_libs
                    install_path = ''
                if dylib_version is not None:
                    product_name = target.get_basename() + '.' + dylib_version
                else:
                    product_name = target.get_basename()
                ldargs += target.link_args
                linker, stdlib_args = self.determine_linker_and_stdlib_args(target)
                ldargs += self.build.get_project_link_args(linker, target.subproject, target.for_machine)
                ldargs += self.build.get_global_link_args(linker, target.for_machine)
                cargs = []
                for dep in target.get_external_deps():
                    cargs += dep.get_compile_args()
                    ldargs += dep.get_link_args()
                ldstr = ' '.join(ldargs)
                valid = self.buildconfmap[target_name][buildtype]
                langargs = {}
                for lang in self.environment.coredata.compilers[target.for_machine]:
                    if lang not in langnamemap:
                        continue
                    # Add compile args added using add_project_arguments()
                    pargs = self.build.projects_args[target.for_machine].get(target.subproject, {}).get(lang, [])
                    # Add compile args added using add_global_arguments()
                    # These override per-project arguments
                    gargs = self.build.global_args[target.for_machine].get(lang, [])
                    targs = target.get_extra_args(lang)
                    args = pargs + gargs + targs
                    if args:
                        langname = langnamemap[lang]
                        compiler = target.compilers.get(lang)
                        lang_cargs = cargs
                        if compiler and target.implicit_include_directories:
                            lang_cargs += self.get_build_dir_include_args(target, compiler)
                        langargs[langname] = args
                        langargs[langname] += lang_cargs
                symroot = os.path.join(self.environment.get_build_dir(), target.subdir)
                self.write_line(f'{valid} /* {buildtype} */ = {{')
                self.indent_level += 1
                self.write_line('isa = XCBuildConfiguration;')
                self.write_line('buildSettings = {')
                self.indent_level += 1
                self.write_line('COMBINE_HIDPI_IMAGES = YES;')
                if dylib_version is not None:
                    self.write_line('DYLIB_CURRENT_VERSION = "%s";' % dylib_version)
                self.write_line('EXECUTABLE_PREFIX = "%s";' % target.prefix)
                if target.suffix == '':
                    suffix = ''
                else:
                    suffix = '.' + target.suffix
                self.write_line('EXECUTABLE_SUFFIX = "%s";' % suffix)
                self.write_line('GCC_GENERATE_DEBUGGING_SYMBOLS = YES;')
                self.write_line('GCC_INLINES_ARE_PRIVATE_EXTERN = NO;')
                self.write_line('GCC_OPTIMIZATION_LEVEL = 0;')
                if target.has_pch:
                    # Xcode uses GCC_PREFIX_HEADER which only allows one file per target/executable. Precompiling various header files and
                    # applying a particular pch to each source file will require custom scripts (as a build phase) and build flags per each
                    # file. Since Xcode itself already discourages precompiled headers in favor of modules we don't try much harder here.
                    pchs = target.get_pch('c') + target.get_pch('cpp') + target.get_pch('objc') + target.get_pch('objcpp')
                    # Make sure to use headers (other backends require implementation files like *.c *.cpp, etc; these should not be used here)
                    pchs = [pch for pch in pchs if pch.endswith('.h') or pch.endswith('.hh') or pch.endswith('hpp')]
                    if pchs:
                        if len(pchs) > 1:
                            mlog.warning('Unsupported Xcode configuration: More than 1 precompiled header found "{}". Target "{}" might not compile correctly.'.format(str(pchs), target.name))
                        relative_pch_path = os.path.join(target.get_subdir(), pchs[0]) # Path relative to target so it can be used with "$(PROJECT_DIR)"
                        self.write_line('GCC_PRECOMPILE_PREFIX_HEADER = YES;')
                        self.write_line('GCC_PREFIX_HEADER = "$(PROJECT_DIR)/%s";' % relative_pch_path)
                self.write_line('GCC_PREPROCESSOR_DEFINITIONS = "";')
                self.write_line('GCC_SYMBOLS_PRIVATE_EXTERN = NO;')
                if headerdirs:
                    quotedh = ','.join(['"\\"%s\\""' % i for i in headerdirs])
                    self.write_line('HEADER_SEARCH_PATHS=(%s);' % quotedh)
                self.write_line('INSTALL_PATH = "%s";' % install_path)
                self.write_line('LIBRARY_SEARCH_PATHS = "";')
                if isinstance(target, build.SharedLibrary):
                    self.write_line('LIBRARY_STYLE = DYNAMIC;')
                for langname, args in langargs.items():
                    self.write_build_setting_line('OTHER_%sFLAGS' % langname, args)
                self.write_line('OTHER_LDFLAGS = "%s";' % ldstr)
                self.write_line('OTHER_REZFLAGS = "";')
                self.write_line('PRODUCT_NAME = %s;' % product_name)
                self.write_line('SECTORDER_FLAGS = "";')
                self.write_line('SYMROOT = "%s";' % symroot)
                self.write_build_setting_line('SYSTEM_HEADER_SEARCH_PATHS', [self.environment.get_build_dir()])
                self.write_line('USE_HEADERMAP = NO;')
                self.write_build_setting_line('WARNING_CFLAGS', ['-Wmost', '-Wno-four-char-constants', '-Wno-unknown-pragmas'])
                self.indent_level -= 1
                self.write_line('};')
                self.write_line('name = %s;' % buildtype)
                self.indent_level -= 1
                self.write_line('};')
        self.ofile.write('/* End XCBuildConfiguration section */\n')

    def generate_xc_configurationList(self):
        # FIXME: sort items
        self.ofile.write('\n/* Begin XCConfigurationList section */\n')
        self.write_line(f'{self.project_conflist} /* Build configuration list for PBXProject "{self.build.project_name}" */ = {{')
        self.indent_level += 1
        self.write_line('isa = XCConfigurationList;')
        self.write_line('buildConfigurations = (')
        self.indent_level += 1
        for buildtype in self.buildtypes:
            self.write_line('{} /* {} */,'.format(self.project_configurations[buildtype], buildtype))
        self.indent_level -= 1
        self.write_line(');')
        self.write_line('defaultConfigurationIsVisible = 0;')
        self.write_line('defaultConfigurationName = debug;')
        self.indent_level -= 1
        self.write_line('};')

        # Now the all target
        self.write_line('%s /* Build configuration list for PBXAggregateTarget "ALL_BUILD" */ = {' % self.all_buildconf_id)
        self.indent_level += 1
        self.write_line('isa = XCConfigurationList;')
        self.write_line('buildConfigurations = (')
        self.indent_level += 1
        for buildtype in self.buildtypes:
            self.write_line('{} /* {} */,'.format(self.buildall_configurations[buildtype], buildtype))
        self.indent_level -= 1
        self.write_line(');')
        self.write_line('defaultConfigurationIsVisible = 0;')
        self.write_line('defaultConfigurationName = debug;')
        self.indent_level -= 1
        self.write_line('};')

        # Test target
        self.write_line('%s /* Build configuration list for PBXAggregateTarget "ALL_BUILD" */ = {' % self.test_buildconf_id)
        self.indent_level += 1
        self.write_line('isa = XCConfigurationList;')
        self.write_line('buildConfigurations = (')
        self.indent_level += 1
        for buildtype in self.buildtypes:
            self.write_line('{} /* {} */,'.format(self.test_configurations[buildtype], buildtype))
        self.indent_level -= 1
        self.write_line(');')
        self.write_line('defaultConfigurationIsVisible = 0;')
        self.write_line('defaultConfigurationName = debug;')
        self.indent_level -= 1
        self.write_line('};')

        for target_name in self.build.get_build_targets():
            listid = self.buildconflistmap[target_name]
            self.write_line(f'{listid} /* Build configuration list for PBXNativeTarget "{target_name}" */ = {{')
            self.indent_level += 1
            self.write_line('isa = XCConfigurationList;')
            self.write_line('buildConfigurations = (')
            self.indent_level += 1
            typestr = 'debug'
            idval = self.buildconfmap[target_name][typestr]
            self.write_line(f'{idval} /* {typestr} */,')
            self.indent_level -= 1
            self.write_line(');')
            self.write_line('defaultConfigurationIsVisible = 0;')
            self.write_line('defaultConfigurationName = %s;' % typestr)
            self.indent_level -= 1
            self.write_line('};')
        self.ofile.write('/* End XCConfigurationList section */\n')

    def write_build_setting_line(self, flag_name, flag_values, explicit=False):
        if flag_values:
            if len(flag_values) == 1:
                value = flag_values[0]
                if (' ' in value):
                    # If path contains spaces surround it with double colon
                    self.write_line(f'{flag_name} = "\\"{value}\\"";')
                else:
                    self.write_line(f'{flag_name} = "{value}";')
            else:
                self.write_line('%s = (' % flag_name)
                self.indent_level += 1
                for value in flag_values:
                    if (' ' in value):
                        # If path contains spaces surround it with double colon
                        self.write_line('"\\"%s\\"",' % value)
                    else:
                        self.write_line('"%s",' % value)
                self.indent_level -= 1
                self.write_line(');')
        else:
            if explicit:
                self.write_line('%s = "";' % flag_name)

    def generate_prefix(self, pbxdict):
        self.ofile.write('// !$*UTF8*$!\n{\n')
        self.indent_level += 1
        self.write_line('archiveVersion = 1;\n')
        pbxdict.add_item('archiveVersion', '1')
        self.write_line('classes = {\n')
        self.write_line('};\n')
        pbxdict.add_item('classes', PbxDict())
        self.write_line('objectVersion = 46;\n')
        pbxdict.add_item('objectVersion', '46')
        self.write_line('objects = {\n')
        objects_dict = PbxDict()
        pbxdict.add_item('objects', objects_dict)
        
        self.indent_level += 1
        return objects_dict

    def generate_suffix(self, pbxdict):
        self.indent_level -= 1
        self.write_line('};\n')
        self.write_line('rootObject = ' + self.project_uid + ' /* Project object */;')
        pbxdict.add_item('rootObject', self.project_uid, 'Project object')
        self.indent_level -= 1
        self.write_line('}\n')
