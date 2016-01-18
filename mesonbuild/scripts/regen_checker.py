#!/usr/bin/env python3

# Copyright 2015-2016 The Meson development team

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
import pickle, subprocess

# This could also be used for XCode.

def need_regen(regeninfo):
    sln_time = os.stat(os.path.join(regeninfo.build_dir, regeninfo.solutionfile)).st_mtime
    for i in regeninfo.depfiles:
        curfile = os.path.join(regeninfo.build_dir, i)
        curtime = os.stat(curfile).st_mtime
        if curtime > sln_time:
            return True
    return False

def regen(regeninfo):
    scriptdir = os.path.split(__file__)[0]
    mesonscript = os.path.join(scriptdir, 'meson.py')
    cmd = [sys.executable, mesonscript, regeninfo.build_dir, regeninfo.source_dir,
           '--backend=vs2010', 'secret-handshake']
    subprocess.check_call(cmd)

def run(args):
    regeninfo = pickle.load(open(os.path.join(args[0], 'regeninfo.dump'), 'rb'))
    if need_regen(regeninfo):
        regen(regeninfo)
    sys.exit(0)

if __name__ == '__main__':
    run(sys.argv[1:])
