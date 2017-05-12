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

import os
import sys

from mesonbuild.coredata import version

if sys.version_info[0] < 3:
    print('Tried to install with Python 2, Meson only supports Python 3.')
    sys.exit(1)

# We need to support Python installations that have nothing but the basic
# Python installation. Use setuptools when possible and fall back to
# plain distutils when setuptools is not available.
try:
    from setuptools import setup
    from setuptools.command.install_scripts import install_scripts as orig
except ImportError:
    from distutils.core import setup
    from distutils.command.install_scripts import install_scripts as orig

class install_scripts(orig):
    def run(self):
        if sys.platform == 'win32':
            super().run()
            return

        if not self.skip_build:
            self.run_command('build_scripts')
        self.outfiles = []
        if not self.dry_run:
            self.mkpath(self.install_dir)

        # We want the files to be installed without a suffix on Unix
        for infile in self.get_inputs():
            infile = os.path.basename(infile)
            in_built = os.path.join(self.build_dir, infile)
            in_stripped = infile[:-3] if infile.endswith('.py') else infile
            outfile = os.path.join(self.install_dir, in_stripped)
            # NOTE: Mode is preserved by default
            self.copy_file(in_built, outfile)
            self.outfiles.append(outfile)

setup(name='meson',
      version=version,
      description='A high performance build system',
      author='Jussi Pakkanen',
      author_email='jpakkane@gmail.com',
      url='http://mesonbuild.com',
      license=' Apache License, Version 2.0',
      packages=['mesonbuild',
                'mesonbuild.dependencies',
                'mesonbuild.modules',
                'mesonbuild.scripts',
                'mesonbuild.backend',
                'mesonbuild.wrap'],
      scripts=['meson.py',
               'mesonconf.py',
               'mesontest.py',
               'mesonintrospect.py',
               'wraptool.py'],
      cmdclass={'install_scripts': install_scripts},
      data_files=[('share/man/man1', ['man/meson.1',
                                      'man/mesonconf.1',
                                      'man/mesonintrospect.1',
                                      'man/mesontest.1',
                                      'man/wraptool.1'])],
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
