#!/usr/bin/env python3

# Mimic a binary that generates an executable file (e.g. ld).

import sys, subprocess

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(sys.argv[0], 'compiler output_file input_files')
        sys.exit(1)
    compiler = sys.argv[1]
    ifile = sys.argv[3:]
    ofile = sys.argv[2]
    if compiler.endswith('cl'):
        cmd = [compiler, '/nologo', '/EHsc', '/RTC1', '/MTd', '/Gy', '/Gd', '/Fe' + ofile] + ifile
    else:
        cmd = [compiler, '-o', ofile] + ifile
    sys.exit(subprocess.call(cmd))
