# Copyright 2018 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os
import json
import subprocess
import shlex
from .mesonlib import meson_command
from .compilers.compilers import compiler_envvars

dump_format_version = 1

def upgrade(state_file):
    d = json.load(open(state_file, 'r'))
    version = d.get('dump_format_version', 'missing')
    if version != dump_format_version:
        sys.exit('Can not upgrade because state dump file format is not compatible: %d != %d.' % (version, dump_format_version))
    state = d['state']
    env = os.environ.copy()
    for c in state['compilers']:
        ename = compiler_envvars[c[0]]
        eval = ' '.join([shlex.quote(x) for x in c[1]])
        env[ename] = eval
    cmd_args = [state['source_root'],
                state['build_root']]
    if 'cross_file' in state:
        cmd_args += ['--cross-file', state['cross_file']]
    for o in state['options']:
        cmd_args.append('-D%s=%s' % (o[0], o[1]))
    pc = subprocess.run(meson_command + cmd_args)
    if pc.returncode != 0:
        sys.exit(1) # The output from above should be enough to debug any issues.

def do_upgrade(potential_builddirs):
    for bd in potential_builddirs:
        state_file = os.path.join(bd, 'meson-private', 'upgrade-state.json')
        corefile = os.path.join(bd, 'meson-private', 'coredata.dat')
        corefile_bak = corefile + '~'
        if os.path.exists(state_file):
            was_success = False
            try:
                os.replace(corefile, corefile_bak)
                upgrade(state_file)
                was_success = True
            finally:
                if not was_success:
                    try:
                        os.replace(corefile_bak, corefile)
                    except Exception as e:
                        print('Could not restore original state: %s\nYou probably need to wipe the builddir' % str(e))
            return
    sys.exit('Could not find upgrade state file. Can not upgrade')

def build_opt_array(environment):
    options = []
    for optclass in environment.coredata.get_all_option_classes():
        for k, v in optclass.items():
            options.append((k, str(v.value)))
    return options

def build_compiler_array(build):
    result = []
    # Only native ones, cross compilers come from the cross file.
    for k, v in build.compilers.items():
        result.append((k, v.exelist))
    return result

def build_state_dict(environment, build):
    result = {}
    result['source_root'] = environment.get_source_dir()
    result['build_root'] = environment.get_build_dir()
    if environment.coredata.cross_file:
        result['cross_file'] = environment.coredata.cross_file
    result['options'] = build_opt_array(environment)
    result['compilers'] = build_compiler_array(build)
    return result

def create_dump_dict(environment, build):
    s = {}
    s['dump_format_version'] = dump_format_version
    s['state'] = build_state_dict(environment, build)
    return s
