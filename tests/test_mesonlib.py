# Copyright 2015 The Meson development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import mesonlib

import unittest

class TestMesonLib(unittest.TestCase):

    def test_flatten(self):
        self.assertEqual(mesonlib.flatten(1), 1)
        self.assertEqual(mesonlib.flatten([1]), [1])
        self.assertEqual(mesonlib.flatten([1, [2]]), [1, 2])
        self.assertEqual(mesonlib.flatten([1, [2, [3]]]), [1, 2, 3])
