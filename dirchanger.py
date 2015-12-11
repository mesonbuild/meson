# Copyright 2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''CD into dir given as first argument and execute
the command given in the rest of the arguments.'''

import os, subprocess, sys

dirname = sys.argv[1]
command = sys.argv[2:]

os.chdir(dirname)
sys.exit(subprocess.call(command))
