#!/usr/bin/python3

# Mimic a binary that generates an object file (e.g. windres).

import sys, shutil, subprocess

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(sys.argv[0], 'input_file output_file')
        sys.exit(1)
    ifile = sys.argv[1]
    ofile = sys.argv[2]
    if shutil.which('cl'):
        cmd = ['cl', '/nologo', '/Fo'+ofile, '/c', ifile]
    else:
        cmd = ['cc', '-c', ifile, '-o', ofile]
    sys.exit(subprocess.call(cmd))

