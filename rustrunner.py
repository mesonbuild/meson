#!/usr/bin/env python3

# Copyright 2014 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This is a wrapper script to run the Rust compiler. It is needed
because:

- output file name of Rust compilation is not knowable at command
  execution time (no, --crate-name can't be used)
- need to delete old crates so nobody uses them by accident
"""

import sys, os, subprocess, glob

def delete_old_crates(target_name, target_type):
    if target_type == 'dylib':
        (base, suffix) = os.path.splitext(target_name)
        crates = glob.glob(base + '-*' + suffix)
        crates = [(os.stat(i).st_mtime, i) for i in crates]
        [os.unlink(c[1]) for c in sorted(crates)[:-1]]
    if target_type == 'lib':
        (base, suffix) = os.path.splitext(target_name)
        crates = glob.glob(base + '-*' + '.rlib') # Rust does not use .a
        crates = [(os.stat(i).st_mtime, i) for i in crates]
        [os.unlink(c[1]) for c in sorted(crates)[:-1]]

def invoke_rust(rustc_command):
    return subprocess.call(rustc_command, shell=False)

def touch_file(fname):
    try:
        os.unlink(fname)
    except FileNotFoundError:
        pass
    open(fname, 'w').close()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('This script is internal to Meson. Do not run it on its own.')
        print("%s <target name> <target type> <rustc invokation cmd line>")
        sys.exit(1)
    target_name = sys.argv[1]
    target_type = sys.argv[2]
    rustc_command = sys.argv[3:]
    retval = invoke_rust(rustc_command)
    if retval != 0:
        sys.exit(retval)
    if target_type != "bin":
        delete_old_crates(target_name, target_type)
        touch_file(target_name)


