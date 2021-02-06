#!/usr/bin/env python3

# Copyright 2016 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, importlib
from pathlib import Path
from mesonbuild import mlog
from mesonbuild.mesonlib import MesonException

# If we're run uninstalled, add the script directory to sys.path to ensure that
# we always import the correct mesonbuild modules even if PYTHONPATH is mangled
meson_exe = Path(sys.argv[0]).resolve()
if (meson_exe.parent / 'mesonbuild').is_dir():
    sys.path.insert(0, str(meson_exe.parent))

def run_script_command(script_name, script_args):
    # Map script name to module name for those that doesn't match
    script_map = {'exe': 'meson_exe',
                  'install': 'meson_install',
                  'delsuffix': 'delwithsuffix',
                  'gtkdoc': 'gtkdochelper',
                  'hotdoc': 'hotdochelper',
                  'regencheck': 'regen_checker'}
    module_name = script_map.get(script_name, script_name)

    try:
        module = importlib.import_module('mesonbuild.scripts.' + module_name)
    except ModuleNotFoundError as e:
        mlog.exception(e)
        return 1

    try:
        ret = module.run(script_args)
        print(sys.modules.keys())
        return ret
    except MesonException as e:
        mlog.error('Error in {} helper script:'.format(script_name))
        mlog.exception(e)
        return 1

if __name__ == '__main__':
    # Special handling of internal commands called from backends, they don't
    # need to go through argparse. Note that custom_target() commands that need
    # to be wrapped will go through this code, so we need to keep the number of
    # loaded python modules as low as possible in this code path.
    if len(sys.argv) >= 3 and sys.argv[1] == '--internal':
        if sys.argv[2] == 'regenerate':
            # Rewrite "meson --internal regenerate" command line to
            # "meson --reconfigure"
            sys.argv = [sys.argv[0], '--reconfigure'] + sys.argv[3:]
        else:
            sys.exit(run_script_command(sys.argv[2], sys.argv[3:]))

    from mesonbuild import mesonmain
    sys.exit(mesonmain.main())
