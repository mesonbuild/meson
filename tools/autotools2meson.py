#!/usr/bin/python3

# Copyright 2014 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sys, os

class Converter():
    def __init__(self, root):
        self.project_root = root

    def readlines(self, file):
        line = file.readline()
        while line != '':
            line = line.rstrip()
            while line.endswith('\\'):
                line = line[:-1] + file.readline.rstrip()
            yield line
            line = file.readline()

    def convert(self, subdir=None):
        if subdir is None:
            subdir = self.project_root
        try:
            ifile = open(os.path.join(subdir, 'Makefile.am'))
        except FileNotFoundError:
            print('Makefile.am not found in subdir', subdir)
        for line in self.readlines(ifile):
            print(line)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(sys.argv[0], '<Autotools project root>')
        sys.exit(1)
    c = Converter(sys.argv[1])
    c.convert()
