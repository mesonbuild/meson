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

from mesonbuild.coredata import version

if sys.version_info < (3, 5, 0):
    print('Tried to install with an unsupported version of Python. '
          'Meson requires Python 3.5.0 or greater')
    sys.exit(1)

from setuptools import setup

# On windows, will create Scripts/meson.exe and Scripts/meson-script.py
# Other platforms will create bin/meson
entries = {'console_scripts': ['meson=mesonbuild.mesonmain:main']}
packages = ['mesonbuild',
            'mesonbuild.backend',
            'mesonbuild.compilers',
            'mesonbuild.dependencies',
            'mesonbuild.modules',
            'mesonbuild.scripts',
            'mesonbuild.wrap']
data_files = []
if sys.platform != 'win32':
    # Only useful on UNIX-like systems
    data_files = [('share/man/man1', ['man/meson.1']),
                  ('share/polkit-1/actions', ['data/com.mesonbuild.install.policy'])]

if __name__ == '__main__':
    setup(name='meson',
          version=version,
          description='A high performance build system',
          author='Jussi Pakkanen',
          author_email='jpakkane@gmail.com',
          url='http://mesonbuild.com',
          license=' Apache License, Version 2.0',
          python_requires='>=3.5',
          packages=packages,
          entry_points=entries,
          data_files=data_files,
          classifiers=['Development Status :: 5 - Production/Stable',
                       'Environment :: Console',
                       'Intended Audience :: Developers',
                       'License :: OSI Approved :: Apache Software License',
                       'Natural Language :: English',
                       'Operating System :: MacOS :: MacOS X',
                       'Operating System :: Microsoft :: Windows',
                       'Operating System :: POSIX :: BSD',
                       'Operating System :: POSIX :: Linux',
                       'Programming Language :: Python :: 3 :: Only',
                       'Topic :: Software Development :: Build Tools',
                       ],
          long_description='''Meson is a cross-platform build system designed to be both as
    fast and as user friendly as possible. It supports many languages and compilers, including
    GCC, Clang and Visual Studio. Its build definitions are written in a simple non-turing
    complete DSL.''')
