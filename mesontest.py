#!/usr/bin/env python3

# Copyright 2016-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# A tool to run tests in many different ways.

from mesonbuild import mesonmain
import sys

if __name__ == '__main__':
    print('Warning: This executable is deprecated. Use "meson test" instead.',
          file=sys.stderr)
    sys.exit(mesonmain.run(['test'] + sys.argv[1:]))
