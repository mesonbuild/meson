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

def need_regen(regeninfo, regen_timestamp):
    for i in regeninfo.depfiles:
        curfile = os.path.join(regeninfo.build_dir, i)
        curtime = os.stat(curfile).st_mtime
        if curtime > regen_timestamp:
            return True
    # The timestamp file gets automatically deleted by MSBuild during a 'Clean' build.
    # We must make sure to recreate it, even if we do not regenerate the solution.
    # Otherwise, Visual Studio will always consider the REGEN project out of date.
    print("Everything is up-to-date, regeneration of build files is not needed.")
    from ..backend.vs2010backend import Vs2010Backend
    Vs2010Backend.touch_regen_timestamp(regeninfo.build_dir)
    return False

def regen(regeninfo, meson_command, backend):
    cmd = meson_command + ['--internal',
                           'regenerate',
                           regeninfo.build_dir,
                           regeninfo.source_dir,
                           '--backend=' + backend]
    subprocess.check_call(cmd)

def run(args):
    private_dir = args[0]
    dumpfile = os.path.join(private_dir, 'regeninfo.dump')
    coredata = os.path.join(private_dir, 'coredata.dat')
    with open(dumpfile, 'rb') as f:
        regeninfo = pickle.load(f)
    with open(coredata, 'rb') as f:
        coredata = pickle.load(f)
    backend = coredata.get_builtin_option('backend')
    regen_timestamp = os.stat(dumpfile).st_mtime
    if need_regen(regeninfo, regen_timestamp):
        regen(regeninfo, coredata.meson_command, backend)
    sys.exit(0)

if __name__ == '__main__':
    run(sys.argv[1:])
