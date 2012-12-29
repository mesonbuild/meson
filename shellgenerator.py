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

import interpreter
from environment import Environment
import os, stat

class ShellGenerator():
    
    def __init__(self, code, source_dir, build_dir):
        self.code = code
        self.environment = Environment(source_dir, build_dir)
        self.interpreter = interpreter.Interpreter(code)
        self.build_filename = 'compile.sh'
    
    def generate(self):
        self.interpreter.run()
        outfilename = os.path.join(self.environment.get_build_dir(), self.build_filename)
        outfile = open(outfilename, 'w')
        outfile.write('#!/bin/sh\n')
        outfile.write('echo This is the output\n')
        outfile.close()
        os.chmod(outfilename, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC |\
                 stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

if __name__ == '__main__':
    code = """
    project('simple generator')
    language('c')
    executable('prog', 'prog.c')
    """
    os.chdir(os.path.split(__file__)[0])
    g = ShellGenerator(code, '.', 'test build area')
    g.generate()
