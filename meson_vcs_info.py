#!/usr/bin/env python3

# Copyright 2013-2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os, shutil, shlex, subprocess
import backends

def update_vcs_info(vcs_cmd, vcs_dir, vcs_info_file):
    """Update the string in the vcs_info_file with the stdout of vcs_cmd executed in vcs_dir."""

    cmd = shlex.split(vcs_cmd)
    # Is the command an executable in path or maybe a script in the source tree?
    cmd[0] = shutil.which(cmd[0]) or os.path.join(vcs_dir, cmd[0])

    try:
        info = subprocess.check_output(cmd, cwd=vcs_dir)
    except FileNotFoundError:
        print('Could not execute command "%s".' % ' '.join(cmd))
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print('Failed to get repository information from %s.\n' % vcs_dir)
        sys.exit(e.returncode)

    info = info.strip()

    if (not os.path.exists(vcs_info_file)) or (open(vcs_info_file, 'rb').read() != info):
        open(vcs_info_file, 'wb').write(info)


def configure_vcs_info(vcs_info_file, config_var_name, input_file, output_file):
    """Configure the input_file by replacing the variable config_var_name with the contents of the vcs_info_file and save it as output_file."""

    info = open(vcs_info_file).read()
    backends.do_conf_file(input_file, output_file, {config_var_name : info})


if __name__ == '__main__':
    if not len(sys.argv) in [5,6]:
        print('Version Control Systems helper script for Meson. Do not run on your own, mmm\'kay?')
        print('%s update <vcs_cmd> <vcs_dir> <vcs_info_file>' % sys.argv[0])
        print('%s configure <vcs_info_file> <config_var_name> <input_file> <output_file>' % sys.argv[0])
        sys.exit(1)

    if sys.argv[1] == 'update':
        update_vcs_info( *sys.argv[2:5] )
    elif sys.argv[1] == 'configure':
        configure_vcs_info( *sys.argv[2:6] )

