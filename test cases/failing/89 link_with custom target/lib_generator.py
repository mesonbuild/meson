#!/usr/bin/env python3

# Mimic a binary that generates a static library

import os
import subprocess
import sys

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(sys.argv[0], 'compiler input_file output_file')
        sys.exit(1)
    compiler = sys.argv[1]
    ifile = sys.argv[2]
    ofile = sys.argv[3]
    tmp = ifile + '.o'
    if compiler.endswith('cl'):
        subprocess.check_call([compiler, '/nologo', '/MDd', '/Fo' + tmp, '/c', ifile])
        subprocess.check_call(['lib', '/nologo', '/OUT:' + ofile, tmp])
    else:
        subprocess.check_call([compiler, '-c', ifile, '-o', tmp])
        subprocess.check_call(['ar', 'csr', ofile, tmp])

os.unlink(tmp)
