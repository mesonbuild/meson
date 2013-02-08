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
DT_NEEDED = 1
DT_RPATH = 15
DT_STRTAB = 5
DT_SONAME = 14

class DynamicEntry():
    def __init__(self, ifile):
        self.d_tag = struct.unpack('Q', ifile.read(8))[0];
        self.val = struct.unpack('Q', ifile.read(8))[0];

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
        self.bf = open(bfile, 'r+b')
        self.parse_header()
        self.parse_sections()
        self.parse_dynamic()

    def parse_header(self):
        self.e_ident = struct.unpack('16s', self.bf.read(16))[0]
        if self.e_ident[1:4] != b'ELF':
            print('File "%s" is not an ELF file.' % self.bfile)
            sys.exit(0)
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
            if x == b'':
                raise RuntimeError('Tried to read past the end of the file')
        return b''.join(arr)

    def find_section(self, target_name):
        section_names = self.sections[self.e_shstrndx]
        for i in self.sections:
            self.bf.seek(section_names.sh_offset + i.sh_name)
            name = self.read_str()
            if name == target_name:
                return i

    def parse_dynamic(self):
        sec = self.find_section(b'.dynamic')
        self.dynamic = []
        self.bf.seek(sec.sh_offset)
        while True:
            e = DynamicEntry(self.bf)
            self.dynamic.append(e)
            if e.d_tag == 0:
                break

    def print_section_names(self):
        section_names = self.sections[self.e_shstrndx]
        for i in self.sections:
            self.bf.seek(section_names.sh_offset + i.sh_name)
            name = self.read_str()
            print(name.decode())

    def print_soname(self):
        soname = None
        strtab = None
        for i in self.dynamic:
            if i.d_tag == DT_SONAME:
                soname = i
            if i.d_tag == DT_STRTAB:
                strtab = i
        self.bf.seek(strtab.val + soname.val)
        print(self.read_str())

    def print_deps(self):
        sec = self.find_section(b'.dynstr')
        deps = []
        for i in self.dynamic:
            if i.d_tag == DT_NEEDED:
                deps.append(i)
        for i in deps:
            offset = sec.sh_offset + i.val
            self.bf.seek(offset)
            name = self.read_str()
            print(name)

    def fix_deps(self, prefix):
        sec = self.find_section(b'.dynstr')
        deps = []
        for i in self.dynamic:
            if i.d_tag == DT_NEEDED:
                deps.append(i)
        for i in deps:
            offset = sec.sh_offset + i.val
            self.bf.seek(offset)
            name = self.read_str()
            if name.startswith(prefix):
                basename = name.split(b'/')[-1]
                padding = b'\0'*(len(name) - len(basename))
                newname = basename + padding
                assert(len(newname) == len(name))
                self.bf.seek(offset)
                self.bf.write(newname)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('This application converts absolute dep paths to relative ones.')
        print('Don\'t run this unless you know what you are doing.')
        print('%s: <binary file> <prefix>' % sys.argv[0])
        exit(1)
    e = Elf(sys.argv[1])
    prefix = sys.argv[2]
    #e.print_deps()
    e.fix_deps(prefix.encode())
