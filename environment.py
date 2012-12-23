#!/usr/bin/python3 -tt

# Copyright 2012 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess

class EnvironmentException(Exception):
    def __init(self, text):
        Exception.__init__(self, text)

def detect_c_compiler(exename):
    p = subprocess.Popen([exename, '--version'], stdout=subprocess.PIPE)
    (out, err) = p.communicate()
    out = out.decode()
    if (out.startswith('cc ') or out.startswith('gcc')) and \
        'Free Software Foundation' in out:
        return GnuCCompiler(exename)
    raise EnvironmentException('Unknown compiler ' + exename)

class CCompiler():
    def __init__(self, exename):
        self.exename = exename
        
    def get_std_warn_flags(self):
        return []

class GnuCCompiler(CCompiler):
    std_warn_flags = ['-Wall']
    def __init__(self, exename):
        CCompiler.__init__(self, exename)

    def get_std_warn_flags(self):
        return GnuCCompiler.std_warn_flags

if __name__ == '__main__':
    gnuc = detect_c_compiler('/usr/bin/cc')
    