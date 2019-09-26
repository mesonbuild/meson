# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json, os, sys, subprocess

def scan_file(src):
    moddeps = []
    for line in open(src):
        if line.startswith('import '):
            line = line.strip()
            modnum = line.split('M')[-1][:-1]
            d = 'src{}.ixx'.format(modnum)
            if d not in moddeps:
                moddeps.append(d)
    return moddeps

def scan_deps():
    compdb = json.load(open('compile_commands.json'))
    src2obj = {}
    name2path = {}
    mmap = {}
    obj_deps = {} # AWFUL HACK! Should put the dep on the generated ifc file instead but can't because of Ninja limitation of one output per rule if you need dep files as well.
    for o in compdb:
        full_srcname = o['file']
        srcname = os.path.split(full_srcname)[1]
        objname = o['output']
        assert(srcname.endswith('.ixx') or srcname.endswith('.cpp'))
        src2obj[srcname] = objname
        name2path[srcname] = full_srcname
    for o in compdb:
        full_srcname = o['file']
        objname = o['output']
        srcname = os.path.split(full_srcname)[1]
        mod_deps = scan_file(full_srcname)
        obj_deps[objname] = [src2obj[x] for x in mod_deps]
    #for k, v in obj_deps.items():
    #    print(k, '=>', v)
    return obj_deps

def rewrite_ninja(obj_deps):
    ifilename = 'build.ninja.hackbak'
    ofilename = 'build.ninja'
    ofile = open(ofilename, 'w')
    for line in open(ifilename):
        if line.startswith('build '):
            line = line.strip()
            out, deps = line.split(':', 1)
            out_obj = out.split(' ', 1)[1]
            dep_objs = obj_deps.get(out_obj, [])
            if len(dep_objs) > 0:
                deps += ' | ' + ' '.join(dep_objs)
            line = out + ':' + deps + '\n'
        ofile.write(line)

def run(args):
    print('Scanning and rewriting Ninja file.')
    obj_deps = scan_deps()
    rewrite_ninja(obj_deps)
    sys.exit(subprocess.run(['ninja', 'all']).returncode)

