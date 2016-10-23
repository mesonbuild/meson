#!/usr/bin/env python3

import sys, os

ifile = sys.argv[1]
ofile = sys.argv[2]

with open(ifile, 'r') as f:
    resname = f.readline().strip()

templ = 'const char %s[] = "%s";\n'
with open(ofile, 'w') as f:
    f.write(templ % (resname, resname))
