# Copyright 2020 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pathlib
import pickle
import re
import typing as T

import_re = re.compile('\w*import ([a-zA-Z0-9]+);')
export_re = re.compile('\w*export module ([a-zA-Z0-9]+);')

class DependencyScanner:
    def __init__(self, pickle_file, outfile, sources):
        with open(pickle_file, 'rb') as pf:
            self.target_data = pickle.load(pf)
        self.outfile = outfile
        self.sources = sources
        self.provided_by = {}
        self.exports = {}
        self.needs = {}
        self.sources_with_exports = []
    
    def scan_file(self, fname):
        for line in pathlib.Path(fname).read_text().split('\n'):
            import_match = import_re.match(line)
            export_match = export_re.match(line)
            if import_match:
                needed = import_match.group(1)
                if fname in self.needs:
                    self.needs[fname].append(needed)
                else:
                    self.needs[fname] = [needed]
            if export_match:
                exported_module = export_match.group(1)
                if exported_module in self.provided_by:
                    raise RuntimeError('Multiple files provide module {}.'.format(exported_module))
                self.sources_with_exports.append(fname)
                self.provided_by[exported_module] = fname
                self.exports[fname] = exported_module

    def objname_for(self, src):
        return self.target_data.source2object[src]

    def ifcname_for(self, src):
        return '{}.ifc'.format(self.exports[src])

    def scan(self):
        for s in self.sources:
            self.scan_file(s)
        with open(self.outfile, 'w') as ofile:
            ofile.write('ninja_dyndep_version = 1\n')
            for src in self.sources:
                objfilename = self.objname_for(src)
                if src in self.sources_with_exports:
                    ifc_entry = '| ' + self.ifcname_for(src)
                else:
                    ifc_entry = ''
                if src in self.needs:
                    # FIXME, handle all sources, not just the first one
                    modname = self.needs[src][0]
                    provider_src = self.provided_by[modname]
                    provider_ifc = self.ifcname_for(provider_src)
                    mod_dep = '| ' + provider_ifc
                else:
                    mod_dep = ''
                ofile.write('build {} {}: dyndep {}\n'.format(objfilename,
                                                              ifc_entry,
                                                              mod_dep))
        return 0

def run(args: T.List[str]) -> int:
    pickle_file = args[0]
    outfile = args[1]
    sources = args[2:]
    scanner = DependencyScanner(pickle_file, outfile, sources)
    return scanner.scan()
