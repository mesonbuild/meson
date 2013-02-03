#!/usr/bin/python3 -tt

# Copyright 2013 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, struct

class Elf():

    def __init__(self, bfile):
        self.bf = open(bfile, 'rb')
        self.ident = struct.unpack('16s', self.bf.read(16))[0]
        if self.ident[1:4] != b'ELF':
            raise RuntimeError('File "%s" is not an ELF file.' % bfile)
        self.e_type = struct.unpack('h', self.bf.read(2))[0]
        self.e_machine = struct.unpack('h', self.bf.read(2))[0]
        self.e_version = struct.unpack('i', self.bf.read(4))[0]
        self.e_entry = struct.unpack('Q', self.bf.read(8))[0]
        self.e_phoff = struct.unpack('Q', self.bf.read(8))[0]
        self.e_shoff = struct.unpack('Q', self.bf.read(8))[0]
        self.e_flags = struct.unpack('i', self.bf.read(4))[0]
        self.e_ehsize = struct.unpack('h', self.bf.read(2))[0]
        self.e_phentsize = struct.unpack('h', self.bf.read(2))[0]
        self.e_phnum = struct.unpack('h', self.bf.read(2))[0]
        self.e_shentsize = struct.unpack('h', self.bf.read(2))[0]
        self.e_shnum = struct.unpack('h', self.bf.read(2))[0]
        self.e_shstrndx = struct.unpack('h', self.bf.read(2))[0]

def remove_rpath(bfile):
        elf = Elf(bfile)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('%s: <binary file>' % sys.argv[0])
        exit(1)
    bfile = sys.argv[1]
    remove_rpath(bfile)
