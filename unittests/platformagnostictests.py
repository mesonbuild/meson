# Copyright 2021 The Meson development team

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
from unittest import skipIf

from .baseplatformtests import BasePlatformTests
from .helpers import is_ci
from mesonbuild.mesonlib import is_linux

@skipIf(is_ci() and not is_linux(), "Run only on fast platforms")
class PlatformAgnosticTests(BasePlatformTests):
    '''
    Tests that does not need to run on all platforms during CI
    '''

    def test_relative_find_program(self):
        '''
        Tests that find_program() with a relative path does not find the program
        in current workdir.
        '''
        testdir = os.path.join(self.unit_test_dir, '99 relative find program')
        self.init(testdir, workdir=testdir)
