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


import sys, os, re

class Converter():
    def __init__(self, root):
        self.project_root = root

    def readlines(self, file, continuator):
        line = file.readline()
        while line != '':
            line = line.rstrip()
            while line.endswith(continuator):
                line = line[:-1] + file.readline().rstrip()
            yield line
            line = file.readline()

    def convert(self, subdir=None):
        if subdir is None:
            subdir = self.project_root
        try:
            ifile = open(os.path.join(subdir, 'Makefile.am'))
        except FileNotFoundError:
            print('Makefile.am not found in subdir', subdir)
            return
        ofile = open(os.path.join(subdir, 'meson.build'), 'w')
        if subdir == self.project_root:
            self.process_autoconf(ofile, subdir)
        for line in self.readlines(ifile, '\\'):
            items = line.strip().split()
            if len(items) == 0:
                ofile.write('\n')
                continue
            if items[0] == 'SUBDIRS':
                for i in items[2:]:
                    if i != '.':
                        ofile.write("subdir('%s')\n" % i)
                        self.convert(os.path.join(subdir, i))
            elif items[0].endswith('_SOURCES'):
                self.convert_target(ofile, items)
            else:
                ofile.write("# %s\n" % line)

    def convert_target(self, ofile, items):
        if items[0].endswith('la_SOURCES'):
            func = 'shared_library'
            tname = "'%s'" % items[0][:-11]
        elif items[0].endswith('a_SOURCES'):
            func = 'static_library'
            tname = "'%s'" % items[0][:-10]
        else:
            func = 'executable'
            tname = "'%s'" % items[0][:-8]
        sources = [tname]
        for s in items[2:]:
            if s.startswith('$(') and s.endswith(')'):
                s = s[2:-1]
            else:
                s = "'%s'" % s
            sources.append(s)
        ofile.write('%s(%s)\n' % (func, ',\n'.join(sources)))

    def process_autoconf(self, ofile, subdir):
        ifile = open(os.path.join(subdir, 'configure.ac'))
        languages = []
        name = 'undetected'
        outlines = []
        for line in self.readlines(ifile, ','):
            line = line.strip()
            if line == 'AC_PROG_CC':
                languages.append("'c'")
            elif line == 'AC_PROG_CXX':
                languages.append("'cpp'")
            elif line.startswith('AC_INIT'):
                line = line[8:]
                if line[0] == '[':
                    name = line.split(']')[0][1:]
                else:
                    name = line.split()[0]
            elif line.startswith('#'):
                outlines.append(line + '\n')
            elif line.startswith('PKG_CHECK_MODULES'):
                rest = line.split('(', 1)[-1].strip()
                pkgstanza = rest.split()[1:]
                for i in pkgstanza:
                    i = i.strip()
                    dep = None
                    if '=' in i:
                        continue
                    if i.startswith('['):
                        dep = i[1:]
                    elif re.match('[a-zA-Z]', i):
                        dep = i
                    if dep is not None:
                        outlines.append("%s_dep = dependency('%s')\n" % (dep, dep))
            else:
                outlines.append('# %s\n' % line)
        ofile.write("project(%s)\n" % ', '.join(["'%s'" % name] + languages))
        ofile.writelines(outlines)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(sys.argv[0], '<Autotools project root>')
        sys.exit(1)
    c = Converter(sys.argv[1])
    c.convert()
