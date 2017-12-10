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

from mesonbuild import mesonmain, mesonlib
import sys, os, locale

def main():
    # Always resolve the command path so Ninja can find it for regen, tests, etc.
    launcher = os.path.realpath(sys.argv[0])
    return mesonmain.run(sys.argv[1:], launcher)

if __name__ == '__main__':
    sys.exit(main())
