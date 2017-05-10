# Copyright 2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mesonbuild import environment

import sys, os, subprocess, re

def coverage(source_root, build_root, log_dir):
    (gcovr_exe, lcov_exe, genhtml_exe) = environment.find_coverage_tools()
    if gcovr_exe:
        subprocess.check_call([gcovr_exe,
                               '-x',
                               '-r', source_root,
                               '-o', os.path.join(log_dir, 'coverage.xml'),
                               ])
        subprocess.check_call([gcovr_exe,
                               '-r', source_root,
                               '-o', os.path.join(log_dir, 'coverage.txt'),
                               ])
    if lcov_exe and genhtml_exe:
        htmloutdir = os.path.join(log_dir, 'coveragereport')
        covinfo = os.path.join(log_dir, 'coverage.info')
        lcov_command = [lcov_exe,
                        '--directory', build_root,
                        '--capture',
                        '--output-file', covinfo,
                        '--no-checksum',
                        '--rc', 'lcov_branch_coverage=1',
                        ]
        genhtml_command = [genhtml_exe,
                           '--prefix', build_root,
                           '--output-directory', htmloutdir,
                           '--title', 'Code coverage',
                           '--legend',
                           '--show-details',
                           '--branch-coverage',
                           covinfo]
        subprocess.check_call(lcov_command)
        subprocess.check_call(genhtml_command)
    return 0

def run(args):
    if not os.path.isfile('build.ninja'):
        print('Coverage currently only works with the Ninja backend.')
        return 1
    source_root, build_root, log_dir = args[:]
    return coverage(source_root, build_root, log_dir)

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))