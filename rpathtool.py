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

SHT_STRTAB = 3

class SectionHeader():
    def __init__(self, ifile):
#Elf64_Word
        self.sh_name = struct.unpack('I', ifile.read(4))[0];
#Elf64_Word
        self.sh_type = struct.unpack('I', ifile.read(4))[0]
#Elf64_Xword
        self.sh_flags = struct.unpack('Q', ifile.read(8))[0];
#Elf64_Addr
        self.sh_addr = struct.unpack('Q', ifile.read(8))[0];
#Elf64_Off
        self.sh_offset = struct.unpack('Q', ifile.read(8))[0]
#Elf64_Xword
        self.sh_size = struct.unpack('Q', ifile.read(8))[0];
#Elf64_Word
        self.sh_link = struct.unpack('I', ifile.read(4))[0];
#Elf64_Word
        self.sh_info = struct.unpack('I', ifile.read(4))[0];
#Elf64_Xword
        self.sh_addralign = struct.unpack('Q', ifile.read(8))[0];
#Elf64_Xword
        self.sh_entsize = struct.unpack('Q', ifile.read(8))[0];

class Elf():

    def __init__(self, bfile):
        self.bfile = bfile
        self.bf = open(bfile, 'rb')
        self.parse_header()
        self.parse_sections()

    def parse_header(self):
        self.e_ident = struct.unpack('16s', self.bf.read(16))[0]
        if self.e_ident[1:4] != b'ELF':
            raise RuntimeError('File "%s" is not an ELF file.' % self.bfile)
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

    def parse_sections(self):
        self.bf.seek(self.e_shoff)
        self.sections = []
        for i in range(self.e_shnum):
            self.sections.append(SectionHeader(self.bf))

    def read_str(self):
        arr = []
        x = self.bf.read(1)
        while x != b'\0':
            arr.append(x)
            x = self.bf.read(1)
        return b''.join(arr)

    def print_section_names(self):
        section_names = self.sections[self.e_shstrndx]
        for i in self.sections:
            self.bf.seek(section_names.sh_offset + i.sh_name)
            name = self.read_str()
            print(name.decode())

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('%s: <binary file>' % sys.argv[0])
        exit(1)
    e = Elf(sys.argv[1])
    e.print_section_names()
