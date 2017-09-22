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

# This class contains the basic functionality needed to run any interpreter
# or an interpreter-based tool.

# This tool is used to manipulate an existing Meson build definition.
#
# - add a file to a target
# - remove files from a target
# - move targets
# - reindent?

from mesonbuild import mesonmain
import sys

if __name__ == '__main__':
    print('Warning: This executable is deprecated. Use "meson rewrite" instead.',
          file=sys.stderr)
    sys.exit(mesonmain.run(['rewrite'] + sys.argv[1:]))
