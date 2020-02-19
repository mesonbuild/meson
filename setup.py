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

import sys

if sys.version_info < (3, 5, 2):
    raise SystemExit('ERROR: Tried to install Meson with an unsupported Python version: \n{}'
                     '\nMeson requires Python 3.5.2 or greater'.format(sys.version))

from mesonbuild.coredata import version
from setuptools import setup

# On windows, will create Scripts/meson.exe and Scripts/meson-script.py
# Other platforms will create bin/meson
entries = {'console_scripts': ['meson=mesonbuild.mesonmain:main']}
packages = ['mesonbuild',
            'mesonbuild.ast',
            'mesonbuild.backend',
            'mesonbuild.cmake',
            'mesonbuild.compilers',
            'mesonbuild.compilers.mixins',
            'mesonbuild.dependencies',
            'mesonbuild.modules',
            'mesonbuild.scripts',
            'mesonbuild.templates',
            'mesonbuild.wrap']
package_data = {
    'mesonbuild.dependencies': ['data/CMakeLists.txt', 'data/CMakeListsLLVM.txt', 'data/CMakePathInfo.txt'],
    'mesonbuild.cmake': ['data/run_ctgt.py', 'data/preload.cmake'],
}
data_files = []
if sys.platform != 'win32':
    # Only useful on UNIX-like systems
    data_files = [('share/man/man1', ['man/meson.1']),
                  ('share/polkit-1/actions', ['data/com.mesonbuild.install.policy'])]

if __name__ == '__main__':
    setup(name='meson',
          version=version,
          packages=packages,
          package_data=package_data,
          entry_points=entries,
          data_files=data_files,)
